# standard libs
import logging
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
from dateutil.relativedelta import relativedelta

# library
import feature_library.deposit.interest.secondary.flat_interest as flat_interest

# inception sdk
from inception_sdk.test_framework.contracts.simulation.data_objects.data_objects import (
    AccountConfig,
    ContractConfig,
    SimulationTestScenario,
    SubTest,
)
from inception_sdk.test_framework.contracts.simulation.helper import (
    create_inbound_hard_settlement_instruction,
    create_outbound_hard_settlement_instruction,
    v2_update_account_status,
)
from inception_sdk.test_framework.contracts.simulation.utils import SimulationTestCase
from inception_sdk.vault.core_api import AccountV2Status, DecimalParameterValue

import tests.deposit.interest.interest_accrual.simulation.accounts as accounts
import tests.deposit.interest.interest_accrual.simulation.dimensions as dimensions
import tests.deposit.interest.interest_accrual.simulation.parameters as parameters

log = logging.getLogger(
    "inception_sdk.test_framework.contracts.simulation.vault_caller.sim_test_request_logger"
)
handler = logging.FileHandler("/tmp/req.json", mode="w")
log.propagate = False
log.addHandler(handler)
log.setLevel(logging.DEBUG)
handler.setLevel(logging.DEBUG)

SMART_CONTRACT = str(Path("tests/deposit/interest/interest_accrual/smart_contract.py"))


class DepositInterestAccrualUtilsSimulationTest(SimulationTestCase):
    parameter_resource_dirs = [
        "src/feature_library/deposit/interest/parameter_resource_defs",
        "src/feature_library/common/parameter_resource_defs",
    ]
    contract_filepaths = [
        str(SMART_CONTRACT),
    ]
    internal_accounts = accounts.default_internal_accounts
    parameter_values = parameters.default_parameter_values
    parameters = []
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
        contract_filepath=None,
    ):
        contract_filepath = contract_filepath or self.contract_filepath

        contract_config = ContractConfig(
            contract_content=self.smart_contract_path_to_content[contract_filepath],
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

    @pytest.mark.sim
    def test_account_can_be_closed_after_accruing_interest(self):
        start = self.default_simulation_start_datetime
        end = start + relativedelta(days=2, hours=2)

        parameter_values = {
            **parameters.default_parameter_values,
            flat_interest.FIXED_INTEREST_RATE_PARAM_ID: DecimalParameterValue(
                decimal_value=Decimal("0.01")
            ),
        }

        sub_tests = [
            SubTest(
                description="Accrue interest for 1 day, withdraw capital, then deactivate",
                events=[
                    create_inbound_hard_settlement_instruction(
                        amount="1000",
                        event_datetime=start + relativedelta(minutes=1),
                        target_account_id=accounts.CUSTOMER_ACCOUNT,
                        internal_account_id=accounts.DUMMY_INTERNAL_ACCOUNT,
                        denomination=parameters.DEFAULT_DENOMINATION,
                        instruction_details={
                            "event": "DEPOSIT",
                            "description": "Initial deposit of 1000 GBP",
                        },
                    ),
                    # Withdraw the 1000 GBP on Day 2 at 00:30:00, leaving only accrued interest
                    create_outbound_hard_settlement_instruction(
                        amount="1000",
                        event_datetime=start + relativedelta(days=1, minutes=30),
                        target_account_id=accounts.CUSTOMER_ACCOUNT,
                        internal_account_id=accounts.DUMMY_INTERNAL_ACCOUNT,
                        denomination=parameters.DEFAULT_DENOMINATION,
                        instruction_details={
                            "event": "WITHDRAWAL",
                            "description": "Withdraw capital of 1000 GBP",
                        },
                    ),
                    # Deactivate account on Day 2 at 01:00:00
                    v2_update_account_status(
                        timestamp=start + relativedelta(days=1, hours=1),
                        account_id=accounts.CUSTOMER_ACCOUNT,
                        status=AccountV2Status.ACCOUNT_STATUS_CLOSED,
                    ),
                ],
                expected_balances_at_ts={
                    # Day 2 at 00:00:05 - interest accrued (1000 * 0.01 / 365 = 0.02740)
                    start + relativedelta(days=1, seconds=5): {
                        accounts.CUSTOMER_ACCOUNT: [
                            (dimensions.ACCRUED_INTEREST_PAYABLE, Decimal("0.02740")),
                            (dimensions.DEFAULT, Decimal("1000")),
                        ]
                    },
                    # Day 2 at 01:05:00 - after deactivation, accrued interest should be zeroed out
                    start + relativedelta(days=1, hours=1, minutes=5): {
                        accounts.CUSTOMER_ACCOUNT: [
                            (dimensions.ACCRUED_INTEREST_PAYABLE, Decimal("0")),
                            (dimensions.DEFAULT, Decimal("0")),
                        ]
                    },
                },
            ),
        ]

        test_scenario = self.get_simulation_test_scenario(
            start=start,
            end=end,
            sub_tests=sub_tests,
            parameter_values=parameter_values,
            debug=True,
        )
        self.run_test_scenario(test_scenario)
