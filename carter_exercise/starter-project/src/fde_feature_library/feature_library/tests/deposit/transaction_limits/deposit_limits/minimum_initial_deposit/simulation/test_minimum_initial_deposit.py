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
import tests.deposit.transaction_limits.deposit_limits.minimum_initial_deposit.simulation.accounts as accounts  # noqa: E501
import tests.deposit.transaction_limits.deposit_limits.minimum_initial_deposit.simulation.dimensions as dimensions  # noqa: E501
import tests.deposit.transaction_limits.deposit_limits.minimum_initial_deposit.simulation.parameters as parameters  # noqa: E501
import tests.deposit.transaction_limits.deposit_limits.minimum_initial_deposit.smart_contract as smart_contract  # noqa: E501

log = logging.getLogger(
    "inception_sdk.test_framework.contracts.simulation.vault_caller.sim_test_request_logger"
)
handler = logging.FileHandler("/tmp/req.json", mode="w")  # whatever path the user wants to put
log.propagate = False  # comment this out if you do not want printing to stdout
log.addHandler(handler)
log.setLevel(logging.DEBUG)
handler.setLevel(logging.DEBUG)

SMART_CONTRACT = Path(
    "tests/deposit/transaction_limits/deposit_limits/minimum_initial_deposit/smart_contract.py"
)


class MinimumInitialDepositBaseTest(SimulationTestCase):
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


class CurrentAccountDenominationTest(MinimumInitialDepositBaseTest):
    @pytest.mark.sim
    def test_at_minimum_initial_deposit(self):
        """"""
        start = self.default_simulation_start_datetime
        end = start + relativedelta(minutes=2)

        sub_tests = [
            SubTest(
                description="Credit at minimum initial deposit.",
                events=[
                    create_inbound_hard_settlement_instruction(
                        amount="20",
                        event_datetime=start + relativedelta(minutes=1),
                        target_account_id=accounts.CUSTOMER_ACCOUNT,
                        internal_account_id=accounts.DUMMY_INTERNAL_ACCOUNT,
                        denomination=dimensions.DEFAULT_DENOMINATION,
                        instruction_details={
                            "event": "DEPOSIT",
                            "description": "Deposit amount at the minimum initial deposit.",
                        },
                    )
                ],
                expected_balances_at_ts={
                    start + relativedelta(minutes=1): {
                        accounts.CUSTOMER_ACCOUNT: [
                            (dimensions.DEFAULT, Decimal(20)),
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
    def test_below_minimum_initial_deposit(self):
        """"""
        start = self.default_simulation_start_datetime
        end = start + relativedelta(minutes=2)
        denomination: str = parameters.DEFAULT_DENOMINATION
        min_initial_deposit: Decimal = parameters.default_parameter_values[  # ty: ignore[possibly-missing-attribute]
            smart_contract.minimum_initial_deposit.MIN_INITIAL_DEPOSIT_PARAM.id
        ].decimal_value

        sub_tests = [
            SubTest(
                description="Credit below minimum initial deposit.",
                events=[
                    create_inbound_hard_settlement_instruction(
                        amount="19.99",
                        event_datetime=start + relativedelta(minutes=1),
                        target_account_id=accounts.CUSTOMER_ACCOUNT,
                        internal_account_id=accounts.DUMMY_INTERNAL_ACCOUNT,
                        denomination=dimensions.DEFAULT_DENOMINATION,
                        instruction_details={
                            "event": "DEPOSIT",
                            "description": "Attempt to deposit amount less than the minimum "
                            "initial deposit.",
                        },
                    )
                ],
                expected_balances_at_ts={
                    start + relativedelta(minutes=1): {
                        accounts.CUSTOMER_ACCOUNT: [(dimensions.DEFAULT, Decimal(0))]
                    }
                },
                expected_posting_rejections=[
                    ExpectedRejection(
                        timestamp=start + relativedelta(minutes=1),
                        rejection_type="AgainstTermsAndConditions",
                        rejection_reason=(
                            f"Transaction amount 19.99 {denomination} is less than the "
                            f"minimum initial deposit amount {min_initial_deposit:0.2f} "
                            f"{denomination}."
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
    def test_above_minimum_initial_deposit(self):
        """"""
        start = self.default_simulation_start_datetime
        end = start + relativedelta(minutes=2)

        sub_tests = [
            SubTest(
                description="Credit above minimum initial deposit.",
                events=[
                    create_inbound_hard_settlement_instruction(
                        amount="20.01",
                        event_datetime=start + relativedelta(minutes=1),
                        target_account_id=accounts.CUSTOMER_ACCOUNT,
                        internal_account_id=accounts.DUMMY_INTERNAL_ACCOUNT,
                        denomination=dimensions.DEFAULT_DENOMINATION,
                        instruction_details={
                            "event": "DEPOSIT",
                            "description": "Deposit amount above the minimum initial deposit.",
                        },
                    ),
                    create_inbound_hard_settlement_instruction(
                        amount="19.99",
                        event_datetime=start + relativedelta(minutes=2),
                        target_account_id=accounts.CUSTOMER_ACCOUNT,
                        internal_account_id=accounts.DUMMY_INTERNAL_ACCOUNT,
                        denomination=dimensions.DEFAULT_DENOMINATION,
                        instruction_details={
                            "event": "DEPOSIT",
                            "description": "Deposit subsequent amount less than the minimum initial"
                            " deposit.",
                        },
                    ),
                ],
                expected_balances_at_ts={
                    start + relativedelta(minutes=1): {
                        accounts.CUSTOMER_ACCOUNT: [(dimensions.DEFAULT, Decimal("20.01"))]
                    },
                    start + relativedelta(minutes=2): {
                        accounts.CUSTOMER_ACCOUNT: [(dimensions.DEFAULT, Decimal(40))]
                    },
                },
            ),
        ]

        test_scenario = self.get_simulation_test_scenario(
            start=start,
            end=end,
            sub_tests=sub_tests,
        )
        self.run_test_scenario(test_scenario)
