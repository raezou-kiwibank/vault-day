# Copyright @ 2026 Thought Machine Group Limited. All rights reserved.
# standard libs
import logging
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

# third party
import pytest
from dateutil.relativedelta import relativedelta
from parameterized import parameterized

import feature_library.lending.addresses as lending_addresses

# features
import feature_library.lending.repayments.late_repayment as late_repayment

from inception_sdk.test_framework.common.balance_helpers import BalanceDimensions

# inception sdk
from inception_sdk.test_framework.contracts.simulation.data_objects.data_objects import (
    AccountConfig,
    ContractConfig,
    ExpectedSchedule,
    SimulationTestScenario,
    SubTest,
)
from inception_sdk.test_framework.contracts.simulation.helper import (
    create_outbound_hard_settlement_posting_instruction_event,
)
from inception_sdk.test_framework.contracts.simulation.utils import (
    SimulationTestCase,
)

import tests.lending.repayments.late_repayment.simulation.accounts as accounts
import tests.lending.repayments.late_repayment.simulation.dimensions as dimensions
import tests.lending.repayments.late_repayment.simulation.parameters as parameters
from tests.common.test_denomination import DEFAULT_DENOMINATION
from tests.sim_utils import create_update_pgtz_instruction, timezones

log = logging.getLogger(
    "inception_sdk.test_framework.contracts.simulation.vault_caller.sim_test_request_logger"
)
handler = logging.FileHandler("/tmp/req.json", mode="w")  # whatever path the user wants to put
log.propagate = False  # comment this out if you do not want printing to stdout
log.addHandler(handler)
log.setLevel(logging.DEBUG)
handler.setLevel(logging.DEBUG)

VERTICAL_SC = str(Path("tests/lending/repayments/late_repayment/late_repayment_vertical_sc.py"))
HORIZONTAL_SC = str(Path("tests/lending/repayments/late_repayment/late_repayment_horizontal_sc.py"))
UTC = ZoneInfo("UTC")


@pytest.mark.sim
class LateRepaymentSimulationTest(SimulationTestCase):
    parameter_resource_dirs = [
        "src/feature_library/common/parameter_resource_defs",
        "src/feature_library/lending/repayments/parameter_resource_defs",
    ]
    contract_filepaths = [VERTICAL_SC, HORIZONTAL_SC]
    internal_accounts = accounts.default_internal_accounts
    parameter_values = parameters.parameter_values

    def get_simulation_test_scenario(
        self,
        start,
        end,
        sub_tests,
        contract_filepath,
        parameter_values=None,
        default_tz=UTC,
    ):
        localised_sub_tests = [
            SubTest(
                description="Set the Default Processing Group Timezone",
                events=[create_update_pgtz_instruction(start, timezone=default_tz)],
            )
        ] + sub_tests

        contract_config = ContractConfig(
            contract_content=self.smart_contract_path_to_content[contract_filepath],
            template_params={},
            account_configs=[
                AccountConfig(
                    account_id_base=accounts.CUSTOMER_ACCOUNT,
                    parameter_values=parameter_values or self.parameter_values,
                    permitted_denominations=[DEFAULT_DENOMINATION],
                )
            ],
        )
        return SimulationTestScenario(
            start=start,
            end=end,
            sub_tests=localised_sub_tests,
            contract_config=contract_config,
            internal_accounts=self.internal_accounts,
            use_v1_accounts=False,
        )


@pytest.mark.sim
class VerticalHierarchyLateRepaymentTest(LateRepaymentSimulationTest):
    contract_filepaths = [VERTICAL_SC]

    @parameterized.expand(timezones)
    @pytest.mark.sim
    def test_late_repayment_fee_applied(self, default_tz: ZoneInfo):
        start = datetime(2026, 1, 1, tzinfo=default_tz)
        # Fee applied at midnight
        late_repayment_check_time = start + relativedelta(months=1)
        end = start + relativedelta(months=1, days=1)

        sub_tests = [
            SubTest(
                description="Setup overdue balance",
                events=[
                    create_outbound_hard_settlement_posting_instruction_event(
                        amount="100.00",
                        event_datetime=start + relativedelta(hours=1),
                        target_account_id=accounts.CUSTOMER_ACCOUNT,
                        internal_account_id=accounts.INTERNAL_ACCOUNT,
                        target_account_address=lending_addresses.PRINCIPAL_OVERDUE,
                        denomination=DEFAULT_DENOMINATION,
                    )
                ],
                expected_balances_at_ts={
                    start + relativedelta(hours=1): {
                        accounts.CUSTOMER_ACCOUNT: [
                            (dimensions.PRINCIPAL_OVERDUE, Decimal("100.00"))
                        ]
                    }
                },
            ),
            SubTest(
                description="Check schedule created",
                expected_schedules=[
                    ExpectedSchedule(
                        run_times=[late_repayment_check_time.astimezone(UTC)],
                        event_id=late_repayment.CHECK_LATE_REPAYMENT_EVENT,
                        account_id=accounts.CUSTOMER_ACCOUNT,
                    )
                ],
            ),
            SubTest(
                description="Late repayment fee applied at midnight",
                expected_balances_at_ts={
                    late_repayment_check_time: {
                        accounts.CUSTOMER_ACCOUNT: [
                            (dimensions.PRINCIPAL_OVERDUE, Decimal("100.00")),
                            (dimensions.PENALTIES, Decimal("25.00")),
                        ],
                        accounts.LATE_REPAYMENT_FEE_INCOME_ACCOUNT: [
                            (dimensions.LATE_REPAYMENT_FEE_INCOME, Decimal("25.00"))
                        ],
                    }
                },
            ),
        ]

        test_scenario = self.get_simulation_test_scenario(
            start=start,
            end=end,
            sub_tests=sub_tests,
            contract_filepath=VERTICAL_SC,
            default_tz=default_tz,
        )
        self.run_test_scenario(test_scenario)

    @parameterized.expand(timezones)
    @pytest.mark.sim
    def test_late_repayment_fee_not_applied_when_no_overdue(self, default_tz):
        start = datetime(2026, 1, 1, tzinfo=default_tz)
        late_repayment_check_time = start + relativedelta(months=1)
        end = start + relativedelta(months=1, days=1)

        sub_tests = [
            SubTest(
                description="Setup only due balance",
                events=[
                    create_outbound_hard_settlement_posting_instruction_event(
                        amount="100.00",
                        event_datetime=start + relativedelta(hours=1),
                        target_account_id=accounts.CUSTOMER_ACCOUNT,
                        internal_account_id=accounts.INTERNAL_ACCOUNT,
                        target_account_address=lending_addresses.PRINCIPAL_DUE,
                        denomination=DEFAULT_DENOMINATION,
                    )
                ],
            ),
            SubTest(
                description="Late repayment fee NOT applied at midnight",
                expected_balances_at_ts={
                    late_repayment_check_time: {
                        accounts.CUSTOMER_ACCOUNT: [
                            (dimensions.PRINCIPAL_DUE, Decimal("100.00")),
                            (dimensions.PENALTIES, Decimal("0.00")),
                        ],
                    }
                },
            ),
        ]

        test_scenario = self.get_simulation_test_scenario(
            start=start,
            end=end,
            sub_tests=sub_tests,
            contract_filepath=VERTICAL_SC,
            default_tz=default_tz,
        )
        self.run_test_scenario(test_scenario)


@pytest.mark.sim
class HorizontalHierarchyLateRepaymentTest(LateRepaymentSimulationTest):
    contract_filepaths = [HORIZONTAL_SC]

    principal_overdue_20251228 = f"{lending_addresses.PRINCIPAL_OVERDUE}_20251228"
    interest_overdue_20251228 = f"{lending_addresses.INTEREST_OVERDUE}_20251228"
    principal_overdue_20251128 = f"{lending_addresses.PRINCIPAL_OVERDUE}_20251128"
    interest_overdue_20251128 = f"{lending_addresses.INTEREST_OVERDUE}_20251128"
    penalties_20251128 = f"{lending_addresses.PENALTIES}_20251128"

    @parameterized.expand(timezones)
    @pytest.mark.sim
    def test_late_repayment_fee_applied(self, default_tz: ZoneInfo):
        start = datetime(2026, 1, 1, tzinfo=default_tz)
        # Fee applied at midnight
        late_repayment_check_time = start + relativedelta(months=1)
        end = start + relativedelta(months=1, days=1)

        sub_tests = [
            SubTest(
                description="Setup overdue balance",
                events=[
                    create_outbound_hard_settlement_posting_instruction_event(
                        amount="100.00",
                        event_datetime=start + relativedelta(hours=1),
                        target_account_id=accounts.CUSTOMER_ACCOUNT,
                        internal_account_id=accounts.INTERNAL_ACCOUNT,
                        target_account_address=self.principal_overdue_20251228,
                        denomination=DEFAULT_DENOMINATION,
                    ),
                    create_outbound_hard_settlement_posting_instruction_event(
                        amount="100.00",
                        event_datetime=start + relativedelta(hours=1),
                        target_account_id=accounts.CUSTOMER_ACCOUNT,
                        internal_account_id=accounts.INTERNAL_ACCOUNT,
                        target_account_address=self.principal_overdue_20251128,
                        denomination=DEFAULT_DENOMINATION,
                    ),
                    create_outbound_hard_settlement_posting_instruction_event(
                        amount="100.00",
                        event_datetime=start + relativedelta(hours=1),
                        target_account_id=accounts.CUSTOMER_ACCOUNT,
                        internal_account_id=accounts.INTERNAL_ACCOUNT,
                        target_account_address=self.interest_overdue_20251228,
                        denomination=DEFAULT_DENOMINATION,
                    ),
                    create_outbound_hard_settlement_posting_instruction_event(
                        amount="100.00",
                        event_datetime=start + relativedelta(hours=1),
                        target_account_id=accounts.CUSTOMER_ACCOUNT,
                        internal_account_id=accounts.INTERNAL_ACCOUNT,
                        target_account_address=self.interest_overdue_20251128,
                        denomination=DEFAULT_DENOMINATION,
                    ),
                    create_outbound_hard_settlement_posting_instruction_event(
                        amount="100.00",
                        event_datetime=start + relativedelta(hours=1),
                        target_account_id=accounts.CUSTOMER_ACCOUNT,
                        internal_account_id=accounts.INTERNAL_ACCOUNT,
                        target_account_address=self.penalties_20251128,
                        denomination=DEFAULT_DENOMINATION,
                    ),
                ],
                expected_balances_at_ts={
                    start + relativedelta(hours=1): {
                        accounts.CUSTOMER_ACCOUNT: [
                            (
                                BalanceDimensions(
                                    address=self.principal_overdue_20251128,
                                    denomination=DEFAULT_DENOMINATION,
                                ),
                                Decimal("100"),
                            ),
                            (
                                BalanceDimensions(
                                    address=self.interest_overdue_20251228,
                                    denomination=DEFAULT_DENOMINATION,
                                ),
                                Decimal("100"),
                            ),
                            (
                                BalanceDimensions(
                                    address=self.principal_overdue_20251128,
                                    denomination=DEFAULT_DENOMINATION,
                                ),
                                Decimal("100"),
                            ),
                            (
                                BalanceDimensions(
                                    address=self.interest_overdue_20251128,
                                    denomination=DEFAULT_DENOMINATION,
                                ),
                                Decimal("100"),
                            ),
                            (
                                BalanceDimensions(
                                    address=self.penalties_20251128,
                                    denomination=DEFAULT_DENOMINATION,
                                ),
                                Decimal("100"),
                            ),
                        ]
                    }
                },
            ),
            SubTest(
                description="Check schedule created",
                expected_schedules=[
                    ExpectedSchedule(
                        run_times=[late_repayment_check_time.astimezone(UTC)],
                        event_id=late_repayment.CHECK_LATE_REPAYMENT_EVENT,
                        account_id=accounts.CUSTOMER_ACCOUNT,
                    )
                ],
            ),
            SubTest(
                description="Late repayment fee applied at midnight",
                expected_balances_at_ts={
                    late_repayment_check_time: {
                        accounts.CUSTOMER_ACCOUNT: [
                            (
                                BalanceDimensions(
                                    address=self.principal_overdue_20251128,
                                    denomination=DEFAULT_DENOMINATION,
                                ),
                                Decimal("100"),
                            ),
                            (
                                BalanceDimensions(
                                    address=self.interest_overdue_20251228,
                                    denomination=DEFAULT_DENOMINATION,
                                ),
                                Decimal("100"),
                            ),
                            (
                                BalanceDimensions(
                                    address=self.principal_overdue_20251128,
                                    denomination=DEFAULT_DENOMINATION,
                                ),
                                Decimal("100"),
                            ),
                            (
                                BalanceDimensions(
                                    address=self.interest_overdue_20251128,
                                    denomination=DEFAULT_DENOMINATION,
                                ),
                                Decimal("100"),
                            ),
                            (
                                BalanceDimensions(
                                    address=self.penalties_20251128,
                                    denomination=DEFAULT_DENOMINATION,
                                ),
                                Decimal("100"),
                            ),
                            (dimensions.PENALTIES, Decimal("25.00")),
                        ],
                        accounts.LATE_REPAYMENT_FEE_INCOME_ACCOUNT: [
                            (dimensions.LATE_REPAYMENT_FEE_INCOME, Decimal("25.00"))
                        ],
                    }
                },
            ),
        ]

        test_scenario = self.get_simulation_test_scenario(
            start=start,
            end=end,
            sub_tests=sub_tests,
            contract_filepath=HORIZONTAL_SC,
            default_tz=default_tz,
        )
        self.run_test_scenario(test_scenario)

    @parameterized.expand(timezones)
    @pytest.mark.sim
    def test_late_repayment_fee_not_applied_when_no_overdue(self, default_tz):
        start = datetime(2026, 1, 1, tzinfo=default_tz)
        late_repayment_check_time = start + relativedelta(months=1)
        end = start + relativedelta(months=1, days=1)

        sub_tests = [
            SubTest(
                description="Setup only due balance",
                events=[
                    create_outbound_hard_settlement_posting_instruction_event(
                        amount="100.00",
                        event_datetime=start + relativedelta(hours=1),
                        target_account_id=accounts.CUSTOMER_ACCOUNT,
                        internal_account_id=accounts.INTERNAL_ACCOUNT,
                        target_account_address=lending_addresses.PRINCIPAL_DUE,
                        denomination=DEFAULT_DENOMINATION,
                    )
                ],
            ),
            SubTest(
                description="Late repayment fee NOT applied at midnight",
                expected_balances_at_ts={
                    late_repayment_check_time: {
                        accounts.CUSTOMER_ACCOUNT: [
                            (dimensions.PRINCIPAL_DUE, Decimal("100.00")),
                            (dimensions.PENALTIES, Decimal("0.00")),
                        ],
                    }
                },
            ),
        ]

        test_scenario = self.get_simulation_test_scenario(
            start=start,
            end=end,
            sub_tests=sub_tests,
            contract_filepath=HORIZONTAL_SC,
            default_tz=default_tz,
        )
        self.run_test_scenario(test_scenario)
