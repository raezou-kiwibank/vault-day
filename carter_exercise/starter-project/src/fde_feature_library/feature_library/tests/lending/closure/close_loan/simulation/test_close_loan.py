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

# features
import feature_library.lending.addresses as lending_addresses
import feature_library.lending.closure.close_loan as close_loan

from inception_sdk.test_framework.common.balance_helpers import BalanceDimensions

# inception sdk
from inception_sdk.test_framework.contracts.simulation.data_objects.data_objects import (
    AccountConfig,
    ContractConfig,
    ContractNotificationResourceType,
    ExpectedContractNotification,
    ExpectedRejection,
    SimulationTestScenario,
    SubTest,
)
from inception_sdk.test_framework.contracts.simulation.helper import (
    create_inbound_hard_settlement_posting_instruction_event,
    create_outbound_hard_settlement_posting_instruction_event,
    v2_update_account_status,
)
from inception_sdk.test_framework.contracts.simulation.utils import (
    SimulationTestCase,
)
from inception_sdk.vault.core_api import AccountV2Status

import tests.lending.closure.close_loan.simulation.accounts as accounts
import tests.lending.closure.close_loan.simulation.dimensions as dimensions
import tests.lending.closure.close_loan.simulation.parameters as parameters
from tests.common.test_denomination import DEFAULT_DENOMINATION
from tests.sim_utils import create_update_pgtz_instruction, timezones

log = logging.getLogger(
    "inception_sdk.test_framework.contracts.simulation.vault_caller.sim_test_request_logger"
)

VERTICAL_SC = str(Path("tests/lending/closure/close_loan/close_loan_vertical_sc.py"))
HORIZONTAL_SC = str(Path("tests/lending/closure/close_loan/close_loan_horizontal_sc.py"))
UTC = ZoneInfo("UTC")


@pytest.mark.sim
class CloseLoanSimulationTest(SimulationTestCase):
    parameter_resource_dirs = [
        "src/feature_library/common/parameter_resource_defs",
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
                    parameter_values=parameter_values or self.parameter_values,  # type: ignore
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
class VerticalHierarchyCloseLoanTest(CloseLoanSimulationTest):
    contract_filepaths = [VERTICAL_SC]

    @parameterized.expand(timezones)
    def test_repayment_notification_and_closure(self, default_tz: ZoneInfo):
        start = datetime(2026, 1, 1, tzinfo=default_tz)
        end = start + relativedelta(days=1)

        sub_tests = [
            SubTest(
                description="Setup debt balance",
                events=[
                    create_outbound_hard_settlement_posting_instruction_event(
                        amount="100.00",
                        event_datetime=start + relativedelta(hours=1),
                        target_account_id=accounts.CUSTOMER_ACCOUNT,
                        internal_account_id=accounts.INTERNAL_ACCOUNT,
                        target_account_address=lending_addresses.PRINCIPAL,
                        denomination=DEFAULT_DENOMINATION,
                    )
                ],
                expected_balances_at_ts={
                    start + relativedelta(hours=1): {
                        accounts.CUSTOMER_ACCOUNT: [(dimensions.PRINCIPAL, Decimal("100.00"))]
                    }
                },
            ),
            SubTest(
                description="Reject closure with outstanding debt",
                events=[
                    v2_update_account_status(
                        timestamp=start + relativedelta(hours=2),
                        account_id=accounts.CUSTOMER_ACCOUNT,
                        status=AccountV2Status.ACCOUNT_STATUS_CLOSED,
                    )
                ],
                expected_account_deactivation_rejections=[
                    ExpectedRejection(
                        timestamp=start + relativedelta(hours=2),
                        rejection_type="AGAINST TNC",
                        rejection_reason=(
                            "The loan cannot be closed until all outstanding debt is repaid"
                        ),
                        account_id=accounts.CUSTOMER_ACCOUNT,
                    )
                ],
            ),
            SubTest(
                description="Repay loan and verify notification",
                events=[
                    create_inbound_hard_settlement_posting_instruction_event(
                        amount="100.00",
                        event_datetime=start + relativedelta(hours=3),
                        target_account_id=accounts.CUSTOMER_ACCOUNT,
                        internal_account_id=accounts.INTERNAL_ACCOUNT,
                        target_account_address=lending_addresses.PRINCIPAL,
                        denomination=DEFAULT_DENOMINATION,
                    )
                ],
                expected_balances_at_ts={
                    start + relativedelta(hours=3): {
                        accounts.CUSTOMER_ACCOUNT: [(dimensions.PRINCIPAL, Decimal("0.00"))]
                    }
                },
                expected_contract_notifications=[
                    ExpectedContractNotification(
                        timestamp=start + relativedelta(hours=3),
                        notification_type=close_loan.notification_type(
                            product_name="CLOSE_LOAN_VERTICAL"
                        ),
                        notification_details={
                            "account_id": accounts.CUSTOMER_ACCOUNT,
                        },
                        resource_id=accounts.CUSTOMER_ACCOUNT,
                        resource_type=ContractNotificationResourceType.RESOURCE_ACCOUNT,
                    )
                ],
            ),
            SubTest(
                description="Deactivate account after full repayment",
                events=[
                    v2_update_account_status(
                        timestamp=start + relativedelta(hours=4),
                        account_id=accounts.CUSTOMER_ACCOUNT,
                        status=AccountV2Status.ACCOUNT_STATUS_CLOSED,
                    )
                ],
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
class HorizontalHierarchyCloseLoanTest(CloseLoanSimulationTest):
    contract_filepaths = [HORIZONTAL_SC]

    principal_overdue_20251228 = f"{lending_addresses.PRINCIPAL_OVERDUE}_20251228"

    @parameterized.expand(timezones)
    def test_repayment_notification_and_closure(self, default_tz: ZoneInfo):
        start = datetime(2026, 1, 1, tzinfo=default_tz)
        end = start + relativedelta(days=1)

        sub_tests = [
            SubTest(
                description="Setup debt balance with suffix",
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
                        amount="200.00",
                        event_datetime=start + relativedelta(hours=1),
                        target_account_id=accounts.CUSTOMER_ACCOUNT,
                        internal_account_id=accounts.INTERNAL_ACCOUNT,
                        target_account_address=lending_addresses.PRINCIPAL,
                        denomination=DEFAULT_DENOMINATION,
                    ),
                ],
                expected_balances_at_ts={
                    start + relativedelta(hours=1): {
                        accounts.CUSTOMER_ACCOUNT: [
                            (
                                BalanceDimensions(
                                    address=self.principal_overdue_20251228,
                                    denomination=DEFAULT_DENOMINATION,
                                ),
                                Decimal("100.00"),
                            ),
                            (dimensions.PRINCIPAL, Decimal("200.00")),
                        ]
                    }
                },
            ),
            SubTest(
                description="Reject closure with outstanding debt",
                events=[
                    v2_update_account_status(
                        timestamp=start + relativedelta(hours=2),
                        account_id=accounts.CUSTOMER_ACCOUNT,
                        status=AccountV2Status.ACCOUNT_STATUS_CLOSED,
                    )
                ],
                expected_account_deactivation_rejections=[
                    ExpectedRejection(
                        timestamp=start + relativedelta(hours=2),
                        rejection_type="AGAINST TNC",
                        rejection_reason=(
                            "The loan cannot be closed until all outstanding debt is repaid"
                        ),
                        account_id=accounts.CUSTOMER_ACCOUNT,
                    )
                ],
            ),
            SubTest(
                description="Repay loan and verify notification",
                events=[
                    create_inbound_hard_settlement_posting_instruction_event(
                        amount="100.00",
                        event_datetime=start + relativedelta(hours=3),
                        target_account_id=accounts.CUSTOMER_ACCOUNT,
                        internal_account_id=accounts.INTERNAL_ACCOUNT,
                        target_account_address=self.principal_overdue_20251228,
                        denomination=DEFAULT_DENOMINATION,
                    ),
                    create_inbound_hard_settlement_posting_instruction_event(
                        amount="200.00",
                        event_datetime=start + relativedelta(hours=3),
                        target_account_id=accounts.CUSTOMER_ACCOUNT,
                        internal_account_id=accounts.INTERNAL_ACCOUNT,
                        target_account_address=lending_addresses.PRINCIPAL,
                        denomination=DEFAULT_DENOMINATION,
                    ),
                ],
                expected_balances_at_ts={
                    start + relativedelta(hours=3): {
                        accounts.CUSTOMER_ACCOUNT: [
                            (
                                BalanceDimensions(
                                    address=self.principal_overdue_20251228,
                                    denomination=DEFAULT_DENOMINATION,
                                ),
                                Decimal("0.00"),
                            ),
                            (dimensions.PRINCIPAL, Decimal("0.00")),
                        ]
                    }
                },
                expected_contract_notifications=[
                    ExpectedContractNotification(
                        timestamp=start + relativedelta(hours=3),
                        notification_type=close_loan.notification_type(
                            product_name="CLOSE_LOAN_HORIZONTAL"
                        ),
                        notification_details={
                            "account_id": accounts.CUSTOMER_ACCOUNT,
                        },
                        resource_id=accounts.CUSTOMER_ACCOUNT,
                        resource_type=ContractNotificationResourceType.RESOURCE_ACCOUNT,
                    )
                ],
            ),
            SubTest(
                description="Deactivate account after full repayment",
                events=[
                    v2_update_account_status(
                        timestamp=start + relativedelta(hours=4),
                        account_id=accounts.CUSTOMER_ACCOUNT,
                        status=AccountV2Status.ACCOUNT_STATUS_CLOSED,
                    )
                ],
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
