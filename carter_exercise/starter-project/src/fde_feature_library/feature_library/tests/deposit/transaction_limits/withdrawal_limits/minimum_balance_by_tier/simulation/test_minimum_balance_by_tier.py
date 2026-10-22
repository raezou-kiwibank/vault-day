from datetime import datetime
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
from dateutil.relativedelta import relativedelta

from inception_sdk.test_framework.contracts.simulation.data_objects.data_objects import (
    AccountConfig,
    ContractConfig,
    ExpectedRejection,
    SimulationTestScenario,
    SubTest,
)
from inception_sdk.test_framework.contracts.simulation.helper import (
    create_inbound_hard_settlement_instruction,
    create_outbound_hard_settlement_instruction,
)
from inception_sdk.test_framework.contracts.simulation.utils import SimulationTestCase

import tests.deposit.transaction_limits.withdrawal_limits.minimum_balance_by_tier.simulation.accounts as accounts  # noqa: E501
import tests.deposit.transaction_limits.withdrawal_limits.minimum_balance_by_tier.simulation.dimensions as dimensions  # noqa: E501
import tests.deposit.transaction_limits.withdrawal_limits.minimum_balance_by_tier.simulation.parameters as parameters  # noqa: E501

SMART_CONTRACT = Path(
    "tests/deposit/transaction_limits/withdrawal_limits/minimum_balance_by_tier/simulation/smart_contract.py"  # noqa: E501
)


class MinimumBalanceByTierBaseTest(SimulationTestCase):
    parameter_resource_dirs = [
        str(Path("src/feature_library/common/parameter_resource_defs")),
        str(
            Path(
                "src/feature_library/deposit/transaction_limits/withdrawal_limits/parameter_resource_defs"  # noqa: E501
            )
        ),
    ]
    contract_filepaths = [str(SMART_CONTRACT)]
    internal_accounts = accounts.default_internal_accounts
    parameter_values = parameters.default_parameter_values
    default_simulation_start_datetime = datetime(year=2026, month=1, day=1, tzinfo=ZoneInfo("UTC"))

    @classmethod
    def setUpClass(cls):
        cls.contract_filepath = str(SMART_CONTRACT)
        super().setUpClass()

    def get_simulation_test_scenario(
        self,
        start,
        end,
        sub_tests,
        parameter_values=None,
        internal_accounts=None,
        debug=False,
    ):
        contract_config = ContractConfig(
            contract_content=self.smart_contract_path_to_content[self.contract_filepath],
            template_params={},
            account_configs=[
                AccountConfig(
                    account_id_base=accounts.CUSTOMER_ACCOUNT,
                    parameter_values=parameter_values or self.parameter_values,
                    permitted_denominations=[parameters.DEFAULT_DENOMINATION],
                )
            ],
        )
        return SimulationTestScenario(
            start=start,
            end=end,
            sub_tests=sub_tests,
            contract_config=contract_config,
            internal_accounts=self.internal_accounts or internal_accounts,
            debug=debug,
            use_v1_accounts=False,
        )


class MinimumBalanceByTierTest(MinimumBalanceByTierBaseTest):
    @pytest.mark.sim
    def test_withdrawal_above_min_balance(self):
        start = self.default_simulation_start_datetime
        end = start + relativedelta(minutes=2)

        sub_tests = [
            SubTest(
                description="Fund account",
                events=[
                    create_inbound_hard_settlement_instruction(
                        amount="200",
                        event_datetime=start,
                        target_account_id=accounts.CUSTOMER_ACCOUNT,
                        internal_account_id=accounts.DUMMY_INTERNAL_ACCOUNT,
                        denomination=dimensions.DEFAULT_DENOMINATION,
                    )
                ],
                expected_balances_at_ts={
                    start: {
                        accounts.CUSTOMER_ACCOUNT: [
                            (dimensions.DEFAULT, Decimal("200")),
                        ]
                    }
                },
            ),
            SubTest(
                description="Withdraw leaving balance at 50 (exactly minimum balance for UPPER_TIER)",  # noqa: E501
                events=[
                    create_outbound_hard_settlement_instruction(
                        amount="150",
                        event_datetime=start + relativedelta(minutes=1),
                        target_account_id=accounts.CUSTOMER_ACCOUNT,
                        internal_account_id=accounts.DUMMY_INTERNAL_ACCOUNT,
                        denomination=dimensions.DEFAULT_DENOMINATION,
                    )
                ],
                expected_balances_at_ts={
                    start + relativedelta(minutes=1): {
                        accounts.CUSTOMER_ACCOUNT: [
                            (dimensions.DEFAULT, Decimal("50")),
                        ]
                    }
                },
            ),
        ]

        test_scenario = self.get_simulation_test_scenario(
            start=start,
            end=end,
            sub_tests=sub_tests,
        )
        self.run_test_scenario(test_scenario)

    @pytest.mark.sim
    def test_withdrawal_falls_below_min_balance(self):
        start = self.default_simulation_start_datetime
        end = start + relativedelta(minutes=2)

        denomination: str = parameters.DEFAULT_DENOMINATION

        sub_tests = [
            SubTest(
                description="Fund account",
                events=[
                    create_inbound_hard_settlement_instruction(
                        amount="200",
                        event_datetime=start,
                        target_account_id=accounts.CUSTOMER_ACCOUNT,
                        internal_account_id=accounts.DUMMY_INTERNAL_ACCOUNT,
                        denomination=dimensions.DEFAULT_DENOMINATION,
                    )
                ],
                expected_balances_at_ts={
                    start: {
                        accounts.CUSTOMER_ACCOUNT: [
                            (dimensions.DEFAULT, Decimal("200")),
                        ]
                    }
                },
            ),
            SubTest(
                description="Withdraw 150.01, falling below minimum balance of 50",
                events=[
                    create_outbound_hard_settlement_instruction(
                        amount="150.01",
                        event_datetime=start + relativedelta(minutes=1),
                        target_account_id=accounts.CUSTOMER_ACCOUNT,
                        internal_account_id=accounts.DUMMY_INTERNAL_ACCOUNT,
                        denomination=dimensions.DEFAULT_DENOMINATION,
                    )
                ],
                expected_balances_at_ts={
                    start + relativedelta(minutes=1): {
                        accounts.CUSTOMER_ACCOUNT: [
                            (dimensions.DEFAULT, Decimal("200")),
                        ]
                    }
                },
                expected_posting_rejections=[
                    ExpectedRejection(
                        timestamp=start + relativedelta(minutes=1),
                        rejection_type="AgainstTermsAndConditions",
                        rejection_reason=(
                            f"Transaction amount -150.01 {denomination} will result in the "
                            f"account balance falling below the minimum permitted "
                            f"of 50 {denomination}."
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
