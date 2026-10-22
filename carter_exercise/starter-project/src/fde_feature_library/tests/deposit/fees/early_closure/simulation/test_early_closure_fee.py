# standard libs
import logging
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
from dateutil.relativedelta import relativedelta

import feature_library.deposit.fees.early_closure_fee as early_closure_fee_module

from inception_sdk.test_framework.contracts.simulation.data_objects.data_objects import (
    AccountConfig,
    ContractConfig,
    ExpectedRejection,
    SimulationTestScenario,
    SubTest,
)
from inception_sdk.test_framework.contracts.simulation.helper import (
    create_inbound_hard_settlement_instruction,
    v2_update_account_status,
)
from inception_sdk.test_framework.contracts.simulation.utils import SimulationTestCase
from inception_sdk.vault.core_api import (
    AccountV2Status,
    DecimalParameterValue,
)

# inception sdk
# library
import tests.deposit.fees.early_closure.simulation.accounts as accounts
import tests.deposit.fees.early_closure.simulation.dimensions as dimensions
import tests.deposit.fees.early_closure.simulation.parameters as parameters

log = logging.getLogger(
    "inception_sdk.test_framework.contracts.simulation.vault_caller.sim_test_request_logger"
)
handler = logging.FileHandler("/tmp/req.json", mode="w")  # whatever path the user wants to put
log.propagate = False  # comment this out if you do not want printing to stdout
log.addHandler(handler)
log.setLevel(logging.DEBUG)
handler.setLevel(logging.DEBUG)

SMART_CONTRACT = Path("tests/deposit/fees/early_closure/simulation/smart_contract.py")


class EarlyClosureFeeBaseTest(SimulationTestCase):
    parameter_resource_dirs = [
        str(Path("src/feature_library/common/parameter_resource_defs")),
        str(Path("src/feature_library/deposit/fees/parameter_resource_defs")),
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
            calendar_ids=["PUBLIC_HOLIDAYS"],
            parameters=self.parameters,
            debug=debug,
            use_v1_accounts=False,
        )


class EarlyClosureFeeTest(EarlyClosureFeeBaseTest):
    @pytest.mark.sim
    def test_early_closure_fee_applied_if_closed_within_closure_days(self):
        start = self.default_simulation_start_datetime
        end = start + relativedelta(minutes=2)
        early_closure_fee_amount: Decimal = parameters.default_parameter_values[
            early_closure_fee_module.EARLY_CLOSURE_FEE_PARAM.id
        ].decimal_value.quantize(Decimal("0.01"), ROUND_HALF_UP)  # ty: ignore[possibly-missing-attribute]
        self.assertEqual(early_closure_fee_amount, Decimal(10))
        deposit_amount = Decimal(10)
        sub_tests = [
            SubTest(
                description="Credit in a valid denomination",
                events=[
                    create_inbound_hard_settlement_instruction(
                        amount=str(deposit_amount),
                        event_datetime=start + relativedelta(minutes=1),
                        target_account_id=accounts.CUSTOMER_ACCOUNT,
                        internal_account_id=accounts.DUMMY_INTERNAL_ACCOUNT,
                        denomination=dimensions.DEFAULT_DENOMINATION,
                        instruction_details={
                            "event": "DEPOSIT",
                            "description": "Deposit 10 GBP.",
                        },
                    ),
                ],
                expected_balances_at_ts={
                    start + relativedelta(minutes=1): {
                        accounts.CUSTOMER_ACCOUNT: [
                            (dimensions.DEFAULT, deposit_amount),
                        ]
                    }
                },
            ),
            SubTest(
                description="Closure",
                events=[
                    v2_update_account_status(
                        timestamp=start + relativedelta(minutes=2),
                        account_id=accounts.CUSTOMER_ACCOUNT,
                        status=AccountV2Status.ACCOUNT_STATUS_CLOSED,
                    )
                ],
                expected_balances_at_ts={
                    start + relativedelta(minutes=2): {
                        accounts.CUSTOMER_ACCOUNT: [
                            (dimensions.DEFAULT, Decimal(0)),
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
    def test_early_closure_fee_not_applied_on_excessive_balance(self):
        start = self.default_simulation_start_datetime
        end = start + relativedelta(minutes=4)
        early_closure_fee_amount: Decimal = parameters.default_parameter_values[
            early_closure_fee_module.EARLY_CLOSURE_FEE_PARAM.id
        ].decimal_value.quantize(Decimal("0.01"), ROUND_HALF_UP)  # ty: ignore[possibly-missing-attribute]
        self.assertEqual(early_closure_fee_amount, Decimal(10))
        deposit_amount = Decimal(25)
        sub_tests = [
            SubTest(
                description="Credit in a valid denomination, exceeding the closure fee.",
                events=[
                    create_inbound_hard_settlement_instruction(
                        amount=str(deposit_amount),
                        event_datetime=start,
                        target_account_id=accounts.CUSTOMER_ACCOUNT,
                        internal_account_id=accounts.DUMMY_INTERNAL_ACCOUNT,
                        denomination=dimensions.DEFAULT_DENOMINATION,
                        instruction_details={
                            "event": "DEPOSIT",
                            "description": "Deposit 25 GBP.",
                        },
                    ),
                ],
                expected_balances_at_ts={
                    start: {
                        accounts.CUSTOMER_ACCOUNT: [
                            (dimensions.DEFAULT, deposit_amount),
                        ]
                    }
                },
            ),
            SubTest(
                description="Attempted closure fails",
                events=[
                    v2_update_account_status(
                        timestamp=start + relativedelta(minutes=1),
                        account_id=accounts.CUSTOMER_ACCOUNT,
                        status=AccountV2Status.ACCOUNT_STATUS_CLOSED,
                    )
                ],
                expected_balances_at_ts={
                    start + relativedelta(minutes=1): {
                        accounts.CUSTOMER_ACCOUNT: [
                            (dimensions.DEFAULT, Decimal(25)),
                        ]
                    }
                },
                expected_account_deactivation_rejections=[
                    ExpectedRejection(
                        timestamp=start + relativedelta(minutes=1),
                        rejection_type="AGAINST TNC",
                        rejection_reason="There are non-zero balances.",
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
    def test_early_closure_fee_not_applied_if_zero_fee(self):
        start = self.default_simulation_start_datetime
        end = start + relativedelta(minutes=2)
        parameter_values = {
            **parameters.default_parameter_values,
            early_closure_fee_module.EARLY_CLOSURE_FEE_PARAM.id: DecimalParameterValue(
                decimal_value=Decimal(0)
            ),
        }
        sub_tests = [
            SubTest(
                description="Closure",
                events=[
                    v2_update_account_status(
                        timestamp=start + relativedelta(minutes=1),
                        account_id=accounts.CUSTOMER_ACCOUNT,
                        status=AccountV2Status.ACCOUNT_STATUS_CLOSED,
                    )
                ],
                expected_balances_at_ts={
                    start + relativedelta(minutes=1): {
                        accounts.CUSTOMER_ACCOUNT: [
                            (dimensions.DEFAULT, Decimal(0)),
                        ]
                    }
                },
            ),
        ]

        test_scenario = self.get_simulation_test_scenario(
            start=start,
            end=end,
            sub_tests=sub_tests,
            parameter_values=parameter_values,
        )
        self.run_test_scenario(test_scenario)
