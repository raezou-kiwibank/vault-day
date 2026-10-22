# standard libs
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

# third party
import pytest
from dateutil.relativedelta import relativedelta
from parameterized import parameterized

# features
import feature_library.deposit.temporal_features.deposit_period as deposit_period

# inception sdk
from inception_sdk.test_framework.contracts.simulation.data_objects.data_objects import (
    AccountConfig,
    ContractConfig,
    ContractNotificationResourceType,
    ExpectedContractNotification,
    ExpectedRejection,
    ExpectedSchedule,
    SimulationTestScenario,
    SubTest,
)
from inception_sdk.test_framework.contracts.simulation.helper import (
    create_inbound_hard_settlement_instruction,
)
from inception_sdk.test_framework.contracts.simulation.utils import SimulationTestCase
from inception_sdk.vault.core_api import EnumerationParameterValue

import tests.deposit.temporal_features.deposit_period.simulation.accounts as accounts
import tests.deposit.temporal_features.deposit_period.simulation.dimensions as dimensions
import tests.deposit.temporal_features.deposit_period.simulation.parameters as parameters
from tests.common.test_denomination import DEFAULT_DENOMINATION
from tests.sim_utils import create_update_pgtz_instruction, timezones

SMART_CONTRACT = Path("tests/deposit/temporal_features/deposit_period/smart_contract.py")
UTC = ZoneInfo("UTC")


@pytest.mark.sim
class DepositPeriodSimulationTest(SimulationTestCase):
    parameter_resource_dirs = [
        "src/feature_library/common/parameter_resource_defs",
        "src/feature_library/deposit/temporal_features/parameter_resource_defs",
    ]
    contract_filepaths = [str(SMART_CONTRACT)]
    internal_accounts = accounts.default_internal_accounts
    parameter_values = parameters.default_parameter_values

    def get_simulation_test_scenario(
        self,
        start,
        end,
        sub_tests,
        parameter_values=None,
        default_tz=UTC,
    ):
        localised_sub_tests: list[SubTest] = [
            SubTest(
                description="Set the Default Processing Group Timezone",
                events=[create_update_pgtz_instruction(start, timezone=default_tz)],
            )
        ] + sub_tests

        contract_config = ContractConfig(
            contract_content=self.smart_contract_path_to_content[str(SMART_CONTRACT)],
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
            debug=True,
        )

    @parameterized.expand([(tz.key, tz) for tz in timezones])
    @pytest.mark.sim
    def test_deposit_period_end_schedule(self, _, default_tz):
        start = datetime(2026, 1, 1, tzinfo=default_tz)
        # 7 days deposit period (default in parameters.py)
        # End should be 2026-01-08 00:00:00
        deposit_period_end = start + relativedelta(days=7)
        end = start + relativedelta(days=8)

        sub_tests = [
            SubTest(
                description="Check schedule created",
                expected_schedules=[
                    ExpectedSchedule(
                        run_times=[deposit_period_end.astimezone(UTC)],
                        event_id=deposit_period.DEPOSIT_PERIOD_END_EVENT,
                        account_id=accounts.CUSTOMER_ACCOUNT,
                    )
                ],
            ),
            SubTest(
                description="Check notification triggered when balance is zero",
                expected_contract_notifications=[
                    ExpectedContractNotification(
                        timestamp=deposit_period_end,
                        notification_type="DEPOSIT_PERIOD_DEPOSIT_PERIOD_END",
                        notification_details={
                            "account_id": f"{accounts.CUSTOMER_ACCOUNT}",
                            "deposit_balance": "0",
                            "deposit_period_end_datetime": str(deposit_period_end.astimezone(UTC)),
                            "reason": (
                                "Close account due to lack of deposits at the end of deposit period"
                            ),
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

    @pytest.mark.sim
    def test_rejection_after_deposit_period(self):
        default_tz = UTC
        start = datetime(2026, 1, 1, tzinfo=default_tz)
        end = start + relativedelta(days=10)

        sub_tests = [
            SubTest(
                description="Deposit within period",
                events=[
                    create_inbound_hard_settlement_instruction(
                        amount="100",
                        event_datetime=start + relativedelta(days=1),
                        target_account_id=accounts.CUSTOMER_ACCOUNT,
                        internal_account_id=accounts.DUMMY_INTERNAL_ACCOUNT,
                    )
                ],
            ),
            SubTest(
                description="Deposit after period rejected",
                events=[
                    create_inbound_hard_settlement_instruction(
                        amount="100",
                        event_datetime=start + relativedelta(days=8),
                        target_account_id=accounts.CUSTOMER_ACCOUNT,
                        internal_account_id=accounts.DUMMY_INTERNAL_ACCOUNT,
                    )
                ],
                expected_posting_rejections=[
                    ExpectedRejection(
                        timestamp=start + relativedelta(days=8),
                        rejection_type="AgainstTermsAndConditions",
                        rejection_reason=(
                            "No deposits are allowed after the deposit period end datetime."
                        ),
                        account_id=accounts.CUSTOMER_ACCOUNT,
                    )
                ],
            ),
        ]

        test_scenario = self.get_simulation_test_scenario(
            start=start,
            end=end,
            sub_tests=sub_tests,
        )
        self.run_test_scenario(test_scenario)

    @pytest.mark.sim
    def test_unlimited_allowed_deposits_within_period(self):
        default_tz = UTC
        start = datetime(2026, 1, 1, tzinfo=default_tz)
        end = start + relativedelta(days=10)

        sub_tests = [
            SubTest(
                description="First deposit within period",
                events=[
                    create_inbound_hard_settlement_instruction(
                        amount="100",
                        event_datetime=start + relativedelta(days=1),
                        target_account_id=accounts.CUSTOMER_ACCOUNT,
                        internal_account_id=accounts.DUMMY_INTERNAL_ACCOUNT,
                    )
                ],
                expected_balances_at_ts={
                    start + relativedelta(days=1): {
                        accounts.CUSTOMER_ACCOUNT: [
                            (dimensions.DEFAULT, Decimal(100)),
                        ]
                    }
                },
            ),
            SubTest(
                description="Second deposit within period",
                events=[
                    create_inbound_hard_settlement_instruction(
                        amount="100",
                        event_datetime=start + relativedelta(days=2),
                        target_account_id=accounts.CUSTOMER_ACCOUNT,
                        internal_account_id=accounts.DUMMY_INTERNAL_ACCOUNT,
                    )
                ],
                expected_balances_at_ts={
                    start + relativedelta(days=2): {
                        accounts.CUSTOMER_ACCOUNT: [
                            (dimensions.DEFAULT, Decimal(200)),
                        ]
                    }
                },
            ),
            SubTest(
                description="Third deposit within period",
                events=[
                    create_inbound_hard_settlement_instruction(
                        amount="100",
                        event_datetime=start + relativedelta(days=3),
                        target_account_id=accounts.CUSTOMER_ACCOUNT,
                        internal_account_id=accounts.DUMMY_INTERNAL_ACCOUNT,
                    )
                ],
                expected_balances_at_ts={
                    start + relativedelta(days=3): {
                        accounts.CUSTOMER_ACCOUNT: [
                            (dimensions.DEFAULT, Decimal(300)),
                        ]
                    }
                },
            ),
            SubTest(
                description="Deposit after period rejected",
                events=[
                    create_inbound_hard_settlement_instruction(
                        amount="100",
                        event_datetime=start + relativedelta(days=8),
                        target_account_id=accounts.CUSTOMER_ACCOUNT,
                        internal_account_id=accounts.DUMMY_INTERNAL_ACCOUNT,
                    )
                ],
                expected_posting_rejections=[
                    ExpectedRejection(
                        timestamp=start + relativedelta(days=8),
                        rejection_type="AgainstTermsAndConditions",
                        rejection_reason=(
                            "No deposits are allowed after the deposit period end datetime."
                        ),
                        account_id=accounts.CUSTOMER_ACCOUNT,
                    )
                ],
            ),
        ]

        test_scenario = self.get_simulation_test_scenario(
            start=start,
            end=end,
            sub_tests=sub_tests,
        )
        self.run_test_scenario(test_scenario)

    @pytest.mark.sim
    def test_single_deposit_allowed_within_period(self):
        default_tz = UTC
        start = datetime(2026, 1, 1, tzinfo=default_tz)
        end = start + relativedelta(days=10)

        parameter_values = {
            **self.parameter_values,
            deposit_period.NUMBER_OF_PERMITTED_DEPOSITS_PARAM_ID: EnumerationParameterValue(
                enumeration_value=deposit_period.SINGLE
            ),
        }

        sub_tests = [
            SubTest(
                description="First deposit within period",
                events=[
                    create_inbound_hard_settlement_instruction(
                        amount="100",
                        event_datetime=start + relativedelta(days=1),
                        target_account_id=accounts.CUSTOMER_ACCOUNT,
                        internal_account_id=accounts.DUMMY_INTERNAL_ACCOUNT,
                    )
                ],
                expected_balances_at_ts={
                    start + relativedelta(days=1): {
                        accounts.CUSTOMER_ACCOUNT: [
                            (dimensions.DEFAULT, Decimal(100)),
                        ]
                    }
                },
            ),
            SubTest(
                description="Second deposit within period",
                events=[
                    create_inbound_hard_settlement_instruction(
                        amount="100",
                        event_datetime=start + relativedelta(days=2),
                        target_account_id=accounts.CUSTOMER_ACCOUNT,
                        internal_account_id=accounts.DUMMY_INTERNAL_ACCOUNT,
                    )
                ],
                expected_balances_at_ts={
                    start + relativedelta(days=2): {
                        accounts.CUSTOMER_ACCOUNT: [
                            (dimensions.DEFAULT, Decimal(100)),
                        ]
                    }
                },
                expected_posting_rejections=[
                    ExpectedRejection(
                        timestamp=start + relativedelta(days=2),
                        rejection_type="AgainstTermsAndConditions",
                        rejection_reason=("Only a single deposit is allowed."),
                        account_id=accounts.CUSTOMER_ACCOUNT,
                    )
                ],
            ),
        ]

        test_scenario = self.get_simulation_test_scenario(
            start=start,
            end=end,
            sub_tests=sub_tests,
            parameter_values=parameter_values,
        )
        self.run_test_scenario(test_scenario)
