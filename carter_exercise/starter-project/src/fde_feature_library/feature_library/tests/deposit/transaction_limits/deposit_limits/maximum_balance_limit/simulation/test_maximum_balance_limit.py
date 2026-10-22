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
)
from inception_sdk.test_framework.contracts.simulation.utils import SimulationTestCase

# library
import tests.deposit.transaction_limits.deposit_limits.maximum_balance_limit.simulation.accounts as accounts  # noqa: E501
import tests.deposit.transaction_limits.deposit_limits.maximum_balance_limit.simulation.dimensions as dimensions  # noqa: E501
import tests.deposit.transaction_limits.deposit_limits.maximum_balance_limit.simulation.parameters as parameters  # noqa: E501
import tests.deposit.transaction_limits.deposit_limits.maximum_balance_limit.smart_contract as smart_contract  # noqa: E501

log = logging.getLogger(
    "inception_sdk.test_framework.contracts.simulation.vault_caller.sim_test_request_logger"
)
handler = logging.FileHandler("/tmp/req.json", mode="w")  # whatever path the user wants to put
log.propagate = False  # comment this out if you do not want printing to stdout
log.addHandler(handler)
log.setLevel(logging.DEBUG)
handler.setLevel(logging.DEBUG)

SMART_CONTRACT = Path(
    "tests/deposit/transaction_limits/deposit_limits/maximum_balance_limit/smart_contract.py"
)


class MaximumBalanceLimitBaseTest(SimulationTestCase):
    parameter_resource_dirs = [
        str(Path("src/feature_library/common/parameter_resource_defs")),
        str(
            Path(
                "src/feature_library/deposit/transaction_limits/deposit_limits/parameter_resource_defs"
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


class CurrentAccountDenominationTest(MaximumBalanceLimitBaseTest):
    @pytest.mark.sim
    def test_maximum_balance_limit(self):
        """"""
        start = self.default_simulation_start_datetime
        end = start + relativedelta(minutes=2)
        denomination: str = parameters.DEFAULT_DENOMINATION
        maximum_balance: Decimal = parameters.default_parameter_values[  # ty: ignore[possibly-missing-attribute]
            smart_contract.maximum_balance_limit.MAXIMUM_BALANCE_PARAM.id
        ].decimal_value

        sub_tests = [
            SubTest(
                description="Credit in valid denomination",
                events=[
                    create_inbound_hard_settlement_instruction(
                        amount="10",
                        event_datetime=start,
                        target_account_id=accounts.CUSTOMER_ACCOUNT,
                        internal_account_id=accounts.DUMMY_INTERNAL_ACCOUNT,
                        denomination=dimensions.DEFAULT_DENOMINATION,
                        instruction_details={
                            "event": "DEPOSIT",
                            "description": "Deposit 10 GBP, under account limit of 50 GBP.",
                        },
                    )
                ],
                expected_balances_at_ts={
                    start: {
                        accounts.CUSTOMER_ACCOUNT: [
                            (dimensions.DEFAULT, Decimal(10)),
                        ]
                    }
                },
            ),
            SubTest(
                description="Credit over limit",
                events=[
                    create_inbound_hard_settlement_instruction(
                        amount="40.01",
                        event_datetime=start + relativedelta(minutes=1),
                        target_account_id=accounts.CUSTOMER_ACCOUNT,
                        internal_account_id=accounts.DUMMY_INTERNAL_ACCOUNT,
                        denomination=dimensions.DEFAULT_DENOMINATION,
                        instruction_details={
                            "event": "DEPOSIT",
                            "description": "Attempt to deposit 40.01 GBP, over account limit of "
                            "50 GBP.",
                        },
                    )
                ],
                expected_balances_at_ts={
                    start + relativedelta(minutes=1): {
                        accounts.CUSTOMER_ACCOUNT: [(dimensions.DEFAULT, Decimal(10))]
                    }
                },
                expected_posting_rejections=[
                    ExpectedRejection(
                        timestamp=start + relativedelta(minutes=1),
                        rejection_type="AgainstTermsAndConditions",
                        rejection_reason=(
                            f"Posting would exceed maximum permitted balance {maximum_balance} "
                            f"{denomination}."
                        ),
                        account_id=accounts.CUSTOMER_ACCOUNT,
                    )
                ],
            ),
            SubTest(
                description="Credit to limit",
                events=[
                    create_inbound_hard_settlement_instruction(
                        amount="40",
                        event_datetime=start + relativedelta(minutes=2),
                        target_account_id=accounts.CUSTOMER_ACCOUNT,
                        internal_account_id=accounts.DUMMY_INTERNAL_ACCOUNT,
                        denomination=dimensions.DEFAULT_DENOMINATION,
                        instruction_details={
                            "event": "DEPOSIT",
                            "description": "Deposit 40 GBP, up to account limit of 50 GBP.",
                        },
                    )
                ],
                expected_balances_at_ts={
                    start + relativedelta(minutes=2): {
                        accounts.CUSTOMER_ACCOUNT: [(dimensions.DEFAULT, Decimal(50))]
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
