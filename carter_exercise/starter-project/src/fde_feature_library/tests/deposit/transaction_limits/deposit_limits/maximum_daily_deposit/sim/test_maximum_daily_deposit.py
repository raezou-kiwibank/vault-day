# standard libs
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import cast
from zoneinfo import ZoneInfo

import pytest
from dateutil.relativedelta import relativedelta

import feature_library.deposit.transaction_limits.deposit_limits.maximum_daily_deposit as maximum_daily_deposit  # noqa: E501

from inception_sdk.test_framework.contracts.simulation.data_objects.data_objects import (
    AccountConfig,
    ContractConfig,
    ExpectedRejection,
    SimulationTestScenario,
    SubTest,
)
from inception_sdk.test_framework.contracts.simulation.helper import (
    create_inbound_hard_settlement_instruction,
)
from inception_sdk.test_framework.contracts.simulation.utils import SimulationTestCase

# inception sdk
from inception_sdk.vault.core_api import (
    DecimalParameterValue,
)

# library
import tests.deposit.transaction_limits.deposit_limits.maximum_daily_deposit.sim.accounts as accounts  # noqa: E501
import tests.deposit.transaction_limits.deposit_limits.maximum_daily_deposit.sim.dimensions as dimensions  # noqa: E501
import tests.deposit.transaction_limits.deposit_limits.maximum_daily_deposit.sim.parameters as parameters  # noqa: E501

SMART_CONTRACT = Path(
    "tests/deposit/transaction_limits/deposit_limits/maximum_daily_deposit/smart_contract.py"
)


class MaximumDailyDepositLimitTest(SimulationTestCase):
    parameter_resource_dirs = [
        str(Path("src/feature_library/common/parameter_resource_defs")),
        str(
            Path(
                "src/feature_library/deposit/transaction_limits/deposit_limits/parameter_resource_defs"
            )
        ),  # noqa: E501
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

    @pytest.mark.sim
    def test_maximum_daily_deposit_limit(self):
        start = self.default_simulation_start_datetime
        end = start + relativedelta(days=2)
        denomination: str = parameters.DEFAULT_DENOMINATION
        maximum_deposit: Decimal = cast(
            DecimalParameterValue,
            parameters.default_parameter_values[
                maximum_daily_deposit.MAXIMUM_DAILY_DEPOSIT_PARAM.id
            ],
        ).decimal_value

        sub_tests = [
            SubTest(
                description="Credit under limit",
                events=[
                    create_inbound_hard_settlement_instruction(
                        amount="50",
                        event_datetime=start,
                        target_account_id=accounts.CUSTOMER_ACCOUNT,
                        internal_account_id=accounts.DUMMY_INTERNAL_ACCOUNT,
                        denomination=denomination,
                        instruction_details={"event": "DEPOSIT"},
                    )
                ],
                expected_balances_at_ts={
                    start: {
                        accounts.CUSTOMER_ACCOUNT: [
                            (dimensions.DEFAULT, Decimal("50")),
                        ]
                    }
                },
            ),
            SubTest(
                description="Credit reaching exactly the limit for the day",
                events=[
                    create_inbound_hard_settlement_instruction(
                        amount="50",
                        event_datetime=start + relativedelta(minutes=30),
                        target_account_id=accounts.CUSTOMER_ACCOUNT,
                        internal_account_id=accounts.DUMMY_INTERNAL_ACCOUNT,
                        denomination=denomination,
                        instruction_details={"event": "DEPOSIT"},
                    )
                ],
                expected_balances_at_ts={
                    start + relativedelta(minutes=30): {
                        accounts.CUSTOMER_ACCOUNT: [(dimensions.DEFAULT, Decimal("100"))]
                    }
                },
            ),
            SubTest(
                description="Credit over limit for the day",
                events=[
                    create_inbound_hard_settlement_instruction(
                        amount="0.01",
                        event_datetime=start + relativedelta(hours=1),
                        target_account_id=accounts.CUSTOMER_ACCOUNT,
                        internal_account_id=accounts.DUMMY_INTERNAL_ACCOUNT,
                        denomination=denomination,
                        instruction_details={"event": "DEPOSIT"},
                    )
                ],
                expected_balances_at_ts={
                    start + relativedelta(hours=1): {
                        accounts.CUSTOMER_ACCOUNT: [(dimensions.DEFAULT, Decimal("100"))]
                    }
                },
                expected_posting_rejections=[
                    ExpectedRejection(
                        timestamp=start + relativedelta(hours=1),
                        rejection_type="AgainstTermsAndConditions",
                        rejection_reason=(
                            f"Transactions would cause the maximum daily deposit limit of "
                            f"{maximum_deposit} {denomination} to be exceeded."
                        ),
                        account_id=accounts.CUSTOMER_ACCOUNT,
                    )
                ],
            ),
            SubTest(
                description="Credit on next day resets the limit",
                events=[
                    create_inbound_hard_settlement_instruction(
                        amount="50",
                        event_datetime=start + relativedelta(days=1),
                        target_account_id=accounts.CUSTOMER_ACCOUNT,
                        internal_account_id=accounts.DUMMY_INTERNAL_ACCOUNT,
                        denomination=denomination,
                        instruction_details={"event": "DEPOSIT"},
                    )
                ],
                expected_balances_at_ts={
                    start + relativedelta(days=1): {
                        accounts.CUSTOMER_ACCOUNT: [(dimensions.DEFAULT, Decimal("150"))]
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
