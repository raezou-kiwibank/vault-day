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
import feature_library.deposit.temporal_features.grace_period as grace_period

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
    create_parameter_value,
)
from inception_sdk.test_framework.contracts.simulation.utils import (
    SimulationTestCase,
)
from inception_sdk.vault.core_api import DecimalParameterValue
from inception_sdk.vault.sim_api.contract_sim import CreateParameterValue

import tests.deposit.temporal_features.grace_period.simulation.accounts as accounts
import tests.deposit.temporal_features.grace_period.simulation.parameters as parameters
import tests.deposit.temporal_features.grace_period.smart_contract as smart_contract
from tests.common.test_denomination import DEFAULT_DENOMINATION
from tests.sim_utils import create_update_pgtz_instruction, timezones

log = logging.getLogger(
    "inception_sdk.test_framework.contracts.simulation.vault_caller.sim_test_request_logger"
)

SMART_CONTRACT = str(Path("tests/deposit/temporal_features/grace_period/smart_contract.py"))
UTC = ZoneInfo("UTC")


@pytest.mark.sim
class GracePeriodSimulationTest(SimulationTestCase):
    parameter_resource_dirs = [
        str(Path("src/feature_library/common/parameter_resource_defs")),
        str(Path("src/feature_library/deposit/temporal_features/parameter_resource_defs")),
        str(Path("tests/deposit/temporal_features/grace_period/parameter_resource_defs")),
    ]
    contract_filepaths = [SMART_CONTRACT]
    internal_accounts = accounts.default_internal_accounts
    parameter_values = parameters.parameter_values

    def get_simulation_test_scenario(
        self,
        start,
        end,
        sub_tests,
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
            contract_content=self.smart_contract_path_to_content[SMART_CONTRACT],
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

    @parameterized.expand(timezones)
    def test_deposit_and_withdrawal_validation(self, default_tz: ZoneInfo):
        start = datetime(2026, 1, 1, tzinfo=default_tz)
        # grace period end is 5 days from activation + midnight
        # activation is 2026-01-01 00:00:00 (effectively)
        grace_period_end = datetime(2026, 1, 6, 0, 0, 0, tzinfo=default_tz)
        end = grace_period_end + relativedelta(days=1)

        sub_tests = [
            SubTest(
                description="Deposit accepted within grace period",
                events=[
                    create_inbound_hard_settlement_posting_instruction_event(
                        amount="100.00",
                        event_datetime=start + relativedelta(days=1),
                        target_account_id=accounts.CUSTOMER_ACCOUNT,
                        internal_account_id=accounts.INTERNAL_ACCOUNT,
                        denomination=DEFAULT_DENOMINATION,
                    )
                ],
                expected_balances_at_ts={
                    start + relativedelta(days=1, hours=1): {
                        accounts.CUSTOMER_ACCOUNT: [
                            (
                                BalanceDimensions(
                                    denomination=DEFAULT_DENOMINATION,
                                ),
                                Decimal("100.00"),
                            )
                        ]
                    }
                },
            ),
            SubTest(
                description="Withdrawal accepted within grace period (not subject to fees)",
                events=[
                    create_outbound_hard_settlement_posting_instruction_event(
                        amount="50.00",
                        event_datetime=start + relativedelta(days=2),
                        target_account_id=accounts.CUSTOMER_ACCOUNT,
                        internal_account_id=accounts.INTERNAL_ACCOUNT,
                        denomination=DEFAULT_DENOMINATION,
                    )
                ],
                expected_balances_at_ts={
                    start + relativedelta(days=2, hours=1): {
                        accounts.CUSTOMER_ACCOUNT: [
                            (
                                BalanceDimensions(
                                    denomination=DEFAULT_DENOMINATION,
                                ),
                                Decimal("50.00"),
                            )
                        ]
                    }
                },
            ),
            SubTest(
                description="Deposit rejected outside grace period",
                events=[
                    create_inbound_hard_settlement_posting_instruction_event(
                        amount="100.00",
                        event_datetime=grace_period_end + relativedelta(hours=1),
                        target_account_id=accounts.CUSTOMER_ACCOUNT,
                        internal_account_id=accounts.INTERNAL_ACCOUNT,
                        denomination=DEFAULT_DENOMINATION,
                    )
                ],
                expected_posting_rejections=[
                    ExpectedRejection(
                        timestamp=grace_period_end + relativedelta(hours=1),
                        rejection_type="AgainstTermsAndConditions",
                        rejection_reason="No deposits are allowed after the grace period end",
                        account_id=accounts.CUSTOMER_ACCOUNT,
                    )
                ],
            ),
            SubTest(
                description="Withdrawal rejected outside grace period (subject to fees)",
                events=[
                    create_outbound_hard_settlement_posting_instruction_event(
                        amount="10.00",
                        event_datetime=grace_period_end + relativedelta(hours=2),
                        target_account_id=accounts.CUSTOMER_ACCOUNT,
                        internal_account_id=accounts.INTERNAL_ACCOUNT,
                        denomination=DEFAULT_DENOMINATION,
                    )
                ],
                expected_posting_rejections=[
                    ExpectedRejection(
                        timestamp=grace_period_end + relativedelta(hours=2),
                        rejection_type="AgainstTermsAndConditions",
                        rejection_reason="Withdrawal is subject to fees",
                        account_id=accounts.CUSTOMER_ACCOUNT,
                    )
                ],
            ),
        ]

        test_scenario = self.get_simulation_test_scenario(
            start=start,
            end=end,
            sub_tests=sub_tests,
            default_tz=default_tz,
        )
        self.run_test_scenario(test_scenario)

    @parameterized.expand(timezones)
    def test_parameter_change_validation(self, default_tz: ZoneInfo):
        start = datetime(2026, 1, 1, tzinfo=default_tz)
        grace_period_end = datetime(2026, 1, 6, 0, 0, 0, tzinfo=default_tz)
        end = grace_period_end + relativedelta(days=2)

        sub_tests = [
            SubTest(
                description="Parameter change accepted within grace period",
                events=[
                    create_parameter_value(
                        start + relativedelta(days=1),
                        parameter_value=CreateParameterValue(
                            parameter_id=smart_contract.TERM_PARAM_ID,
                            value=DecimalParameterValue(decimal_value=Decimal("5")),
                            account_id=accounts.CUSTOMER_ACCOUNT,
                        ),
                    ),
                ],
                expected_parameter_change_rejections=[],
            ),
            SubTest(
                description="Parameter change rejected outside grace period",
                events=[
                    create_parameter_value(
                        grace_period_end + relativedelta(days=1),
                        parameter_value=CreateParameterValue(
                            parameter_id=smart_contract.TERM_PARAM_ID,
                            value=DecimalParameterValue(decimal_value=Decimal("3")),
                            account_id=accounts.CUSTOMER_ACCOUNT,
                        ),
                    ),
                ],
                expected_parameter_change_rejections=[
                    ExpectedRejection(
                        timestamp=grace_period_end + relativedelta(days=1),
                        rejection_type="AGAINST TNC",
                        rejection_reason="Term length cannot be changed outside the grace period",
                        account_id=accounts.CUSTOMER_ACCOUNT,
                    )
                ],
            ),
        ]

        test_scenario = self.get_simulation_test_scenario(
            start=start,
            end=end,
            sub_tests=sub_tests,
            default_tz=default_tz,
        )
        self.run_test_scenario(test_scenario)

    @parameterized.expand(timezones)
    def test_closure_notification_sent_on_zero_balance(self, default_tz: ZoneInfo):
        start = datetime(2026, 1, 1, tzinfo=default_tz)
        grace_period_end = datetime(2026, 1, 6, 0, 0, 0, tzinfo=default_tz)
        end = grace_period_end + relativedelta(days=1)

        sub_tests = [
            SubTest(
                description="Notification sent at end of grace period when balance is zero",
                expected_contract_notifications=[
                    ExpectedContractNotification(
                        timestamp=grace_period_end,
                        notification_type=grace_period.notification_type(
                            product_name="grace_period"
                        ),
                        notification_details={
                            "account_id": accounts.CUSTOMER_ACCOUNT,
                            "grace_period_end_datetime": str(grace_period_end.astimezone(UTC)),
                            "reason": "Close account due to lack of funds at the end of grace period",  # noqa
                        },
                        resource_id=accounts.CUSTOMER_ACCOUNT,
                        resource_type=ContractNotificationResourceType.RESOURCE_ACCOUNT,
                    )
                ],
            ),
        ]

        test_scenario = self.get_simulation_test_scenario(
            start=start,
            end=end,
            sub_tests=sub_tests,
            default_tz=default_tz,
        )
        self.run_test_scenario(test_scenario)

    @parameterized.expand(timezones)
    def test_closure_notification_not_sent_on_non_zero_balance(self, default_tz: ZoneInfo):
        start = datetime(2026, 1, 1, tzinfo=default_tz)
        grace_period_end = datetime(2026, 1, 6, 0, 0, 0, tzinfo=default_tz)
        end = grace_period_end + relativedelta(days=1)

        sub_tests = [
            SubTest(
                description="Deposit accepted within grace period",
                events=[
                    create_inbound_hard_settlement_posting_instruction_event(
                        amount="100.00",
                        event_datetime=start + relativedelta(days=1),
                        target_account_id=accounts.CUSTOMER_ACCOUNT,
                        internal_account_id=accounts.INTERNAL_ACCOUNT,
                        denomination=DEFAULT_DENOMINATION,
                    )
                ],
            ),
            SubTest(
                description="No notification sent at end of grace period if balance non-zero",
                expected_contract_notifications=[],
            ),
        ]

        test_scenario = self.get_simulation_test_scenario(
            start=start,
            end=end,
            sub_tests=sub_tests,
            default_tz=default_tz,
        )
        self.run_test_scenario(test_scenario)
