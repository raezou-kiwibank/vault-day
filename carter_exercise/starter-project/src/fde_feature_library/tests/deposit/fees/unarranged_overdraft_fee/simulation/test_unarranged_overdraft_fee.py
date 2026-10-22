# standard libs
import logging
from datetime import datetime
from decimal import Decimal
from pathlib import Path

import pytest
from dateutil.relativedelta import relativedelta

from feature_library.deposit.fees.unarranged_overdraft_fee import (
    UNARRANGED_OVERDRAFT_FEE_CAP_PARAM,
    UNARRANGED_OVERDRAFT_FEE_PARAM,
)

from inception_sdk.test_framework.contracts.simulation.data_objects.data_objects import (
    AccountConfig,
    ContractConfig,
    SimulationTestScenario,
    SubTest,
)
from inception_sdk.test_framework.contracts.simulation.helper import (
    create_outbound_hard_settlement_instruction,
)
from inception_sdk.test_framework.contracts.simulation.utils import SimulationTestCase

import tests.deposit.fees.unarranged_overdraft_fee.simulation.accounts as accounts
import tests.deposit.fees.unarranged_overdraft_fee.simulation.dimensions as dimensions
import tests.deposit.fees.unarranged_overdraft_fee.simulation.parameters as parameters
from tests.sim_utils import UTC

SMART_CONTRACT = Path("tests/deposit/fees/unarranged_overdraft_fee/simulation/smart_contract.py")

log = logging.getLogger(
    "inception_sdk.test_framework.contracts.simulation.vault_caller.sim_test_request_logger"
)
handler = logging.FileHandler("/tmp/req.json", mode="w")
log.propagate = False
log.addHandler(handler)
log.setLevel(logging.DEBUG)
handler.setLevel(logging.DEBUG)


class UnarrangedOverdraftFeeBaseTest(SimulationTestCase):
    parameter_resource_dirs = [
        str(Path("src/feature_library/common/parameter_resource_defs")),
        str(Path("src/feature_library/deposit/fees/parameter_resource_defs")),
    ]
    contract_filepaths = [str(SMART_CONTRACT)]
    internal_accounts = accounts.default_internal_accounts
    parameter_values = parameters.default_parameter_values
    default_simulation_start_datetime = datetime(year=2026, month=1, day=1, tzinfo=UTC)

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


class UnarrangedOverdraftFeeTest(UnarrangedOverdraftFeeBaseTest):
    @pytest.mark.sim
    def test_fee_applied_when_in_unarranged_overdraft(self):
        start = self.default_simulation_start_datetime
        end = start + relativedelta(months=1, days=1)

        withdrawal_amount = Decimal(150)
        fee = parameters.default_parameter_values[UNARRANGED_OVERDRAFT_FEE_PARAM.id].decimal_value
        thirty_days_fees = 30 * fee
        fee_cap = parameters.default_parameter_values[
            UNARRANGED_OVERDRAFT_FEE_CAP_PARAM.id
        ].decimal_value
        total_fees: Decimal = min(thirty_days_fees, fee_cap)
        self.assertEqual(total_fees, Decimal(30))
        sub_tests = [
            SubTest(
                description="Withdraw 150 to enter unarranged overdraft (-150 balance)",
                events=[
                    create_outbound_hard_settlement_instruction(
                        amount=str(withdrawal_amount),
                        event_datetime=start + relativedelta(seconds=1),
                        target_account_id=accounts.CUSTOMER_ACCOUNT,
                        internal_account_id=accounts.DUMMY_INTERNAL_ACCOUNT,
                        denomination=dimensions.DEFAULT_DENOMINATION,
                        instruction_details={
                            "event": "WITHDRAWAL",
                            "description": f"Withdraw {withdrawal_amount} GBP.",
                        },
                    )
                ],
                expected_balances_at_ts={
                    start + relativedelta(seconds=1): {
                        accounts.CUSTOMER_ACCOUNT: [
                            (dimensions.DEFAULT, -withdrawal_amount),
                        ]
                    }
                },
            ),
            SubTest(
                description="Fee is accrued daily and applied at the start of the next month",
                events=[],
                expected_balances_at_ts={
                    # Checking balance just after month-end application
                    # 31 days in Jan * 5.00 = 155.00
                    # But wait, cap is 30.00.
                    # So fee application should only be 30.00
                    start + relativedelta(months=1, seconds=1): {
                        accounts.CUSTOMER_ACCOUNT: [
                            (dimensions.DEFAULT, -withdrawal_amount - total_fees),
                            (dimensions.OVERDRAFT_FEE, Decimal(0)),
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
