# standard libs
import logging
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
from dateutil.relativedelta import relativedelta

# inception sdk
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

# library
import tests.deposit.transaction_limits.withdrawal_limits.maximum_daily_withdrawal.simulation.accounts as accounts  # noqa: E501
import tests.deposit.transaction_limits.withdrawal_limits.maximum_daily_withdrawal.simulation.dimensions as dimensions  # noqa: E501
import tests.deposit.transaction_limits.withdrawal_limits.maximum_daily_withdrawal.simulation.parameters as parameters  # noqa: E501
import tests.deposit.transaction_limits.withdrawal_limits.maximum_daily_withdrawal.smart_contract as smart_contract  # noqa: E501
from tests.sim_utils import ctx_id_generator

log = logging.getLogger(
    "inception_sdk.test_framework.contracts.simulation.vault_caller.sim_test_request_logger"
)
handler = logging.FileHandler("/tmp/req.json", mode="w")  # whatever path the user wants to put
log.propagate = False  # comment this out if you do not want printing to stdout
log.addHandler(handler)
log.setLevel(logging.DEBUG)
handler.setLevel(logging.DEBUG)

SMART_CONTRACT = Path(
    "tests/deposit/transaction_limits/withdrawal_limits/maximum_daily_withdrawal/smart_contract.py"
)


class MaximumDailyWithdrawalBaseTest(SimulationTestCase):
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
            parameters=self.parameters,
            debug=debug,
            use_v1_accounts=False,
        )


class CurrentAccountDenominationTest(MaximumDailyWithdrawalBaseTest):
    @pytest.mark.sim
    def test_maximum_daily_withdrawal(self):
        """
        Make withdrawals on two different days to show that the limit is enforced on the first
        day and reset on the second day.
        """
        ctx_id = ctx_id_generator("TX_")
        start = self.default_simulation_start_datetime
        end = start + relativedelta(days=2, hours=2)
        denomination: str = parameters.DEFAULT_DENOMINATION
        max_daily_withdrawal: Decimal = parameters.default_parameter_values[  # ty: ignore[possibly-missing-attribute]  # noqa: E501
            smart_contract.maximum_daily_withdrawal.MAX_DAILY_WITHDRAWAL_PARAM.id
        ].decimal_value
        self.assertEqual(max_daily_withdrawal, Decimal(100))

        sub_tests = [
            SubTest(
                description="Initial deposit to fund account",
                events=[
                    create_inbound_hard_settlement_instruction(
                        amount="500",
                        event_datetime=start,
                        target_account_id=accounts.CUSTOMER_ACCOUNT,
                        internal_account_id=accounts.DUMMY_INTERNAL_ACCOUNT,
                        denomination=dimensions.DEFAULT_DENOMINATION,
                        instruction_details={
                            "event": "DEPOSIT",
                            "description": "Deposit to fund the account for withdrawal tests.",
                        },
                    )
                ],
                expected_balances_at_ts={
                    start: {
                        accounts.CUSTOMER_ACCOUNT: [
                            (dimensions.DEFAULT, Decimal(500)),
                        ]
                    }
                },
            ),
            SubTest(
                description="First withdrawal, under daily limit",
                events=[
                    create_outbound_hard_settlement_instruction(
                        amount="50",
                        event_datetime=start + relativedelta(days=1, hours=1),
                        target_account_id=accounts.CUSTOMER_ACCOUNT,
                        internal_account_id=accounts.DUMMY_INTERNAL_ACCOUNT,
                        denomination=dimensions.DEFAULT_DENOMINATION,
                        client_transaction_id=next(ctx_id),
                        instruction_details={
                            "event": "WITHDRAWAL",
                            "description": "Withdrawal within the daily limit of 100 GBP.",
                        },
                    )
                ],
                expected_balances_at_ts={
                    start + relativedelta(days=1, hours=1): {
                        accounts.CUSTOMER_ACCOUNT: [(dimensions.DEFAULT, Decimal(450))]
                    }
                },
            ),
            SubTest(
                description="Second withdrawal, combined exceeds daily limit of 100",
                events=[
                    create_outbound_hard_settlement_instruction(
                        amount="50.01",
                        event_datetime=start + relativedelta(days=1, hours=2),
                        target_account_id=accounts.CUSTOMER_ACCOUNT,
                        internal_account_id=accounts.DUMMY_INTERNAL_ACCOUNT,
                        denomination=dimensions.DEFAULT_DENOMINATION,
                        client_transaction_id=next(ctx_id),
                        instruction_details={
                            "event": "WITHDRAWAL",
                            "description": "Withdrawal that would push the total daily withdrawals"
                            " over 100 GBP.",
                        },
                    )
                ],
                expected_balances_at_ts={
                    start + relativedelta(days=1, hours=2): {
                        accounts.CUSTOMER_ACCOUNT: [(dimensions.DEFAULT, Decimal(450))]
                    }
                },
                expected_posting_rejections=[
                    ExpectedRejection(
                        timestamp=start + relativedelta(days=1, hours=2),
                        rejection_type="AgainstTermsAndConditions",
                        rejection_reason=(
                            f"Transactions with a total of 100.01 {denomination} would cause the "
                            f"maximum daily withdrawal limit of {max_daily_withdrawal} "
                            f"{denomination} to be exceeded."
                        ),
                        account_id=accounts.CUSTOMER_ACCOUNT,
                    )
                ],
            ),
            SubTest(
                description="Third withdrawal, same day as second withdrawal, up to daily limit",
                events=[
                    create_outbound_hard_settlement_instruction(
                        amount="50",
                        event_datetime=start + relativedelta(days=1, hours=3),
                        target_account_id=accounts.CUSTOMER_ACCOUNT,
                        internal_account_id=accounts.DUMMY_INTERNAL_ACCOUNT,
                        denomination=dimensions.DEFAULT_DENOMINATION,
                        client_transaction_id=next(ctx_id),
                        instruction_details={
                            "event": "WITHDRAWAL",
                            "description": "Withdrawal up to the daily limit of 100 GBP.",
                        },
                    ),
                    create_inbound_hard_settlement_instruction(
                        amount="50",
                        event_datetime=start + relativedelta(days=1, hours=4),
                        target_account_id=accounts.CUSTOMER_ACCOUNT,
                        internal_account_id=accounts.DUMMY_INTERNAL_ACCOUNT,
                        denomination=dimensions.DEFAULT_DENOMINATION,
                        client_transaction_id=next(ctx_id),
                        instruction_details={
                            "event": "DEPOSIT",
                            "description": "Reverse the prior withdrawal completely to prove that "
                            "it has no effect on the withdrawal limit.",
                        },
                    ),
                    create_outbound_hard_settlement_instruction(
                        amount="0.01",
                        event_datetime=start + relativedelta(days=1, hours=5),
                        target_account_id=accounts.CUSTOMER_ACCOUNT,
                        internal_account_id=accounts.DUMMY_INTERNAL_ACCOUNT,
                        denomination=dimensions.DEFAULT_DENOMINATION,
                        client_transaction_id=next(ctx_id),
                        instruction_details={
                            "event": "WITHDRAWAL",
                            "description": "Withdrawal attempting to exceed daily limit of 100 "
                            "GBP.",
                        },
                    ),
                ],
                expected_balances_at_ts={
                    start + relativedelta(days=1, hours=5): {
                        accounts.CUSTOMER_ACCOUNT: [(dimensions.DEFAULT, Decimal(450))]
                    }
                },
                expected_posting_rejections=[
                    ExpectedRejection(
                        timestamp=start + relativedelta(days=1, hours=5),
                        rejection_type="AgainstTermsAndConditions",
                        rejection_reason=(
                            f"Transactions with a total of 100.01 {denomination} would cause the "
                            f"maximum daily withdrawal limit of {max_daily_withdrawal} "
                            f"{denomination} to be exceeded."
                        ),
                        account_id=accounts.CUSTOMER_ACCOUNT,
                    )
                ],
            ),
            SubTest(
                description="Fourth withdrawal, on a new day, under daily limit",
                events=[
                    create_outbound_hard_settlement_instruction(
                        amount="80",
                        event_datetime=start + relativedelta(days=2, hours=1),
                        target_account_id=accounts.CUSTOMER_ACCOUNT,
                        internal_account_id=accounts.DUMMY_INTERNAL_ACCOUNT,
                        denomination=dimensions.DEFAULT_DENOMINATION,
                        client_transaction_id=next(ctx_id),
                        instruction_details={
                            "event": "WITHDRAWAL",
                            "description": "Withdrawal on the next day resetting the daily limit.",
                        },
                    )
                ],
                expected_balances_at_ts={
                    start + relativedelta(days=2, hours=1): {
                        accounts.CUSTOMER_ACCOUNT: [(dimensions.DEFAULT, Decimal(370))]
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
