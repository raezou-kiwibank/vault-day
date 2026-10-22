# standard libs
import logging
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
from dateutil.relativedelta import relativedelta

import feature_library.lending.limits.credit_limit as credit_limit_module

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
from inception_sdk.vault.core_api import (
    DecimalParameterValue,
)

import tests.lending.limits.credit_limit.simulation.accounts as accounts
import tests.lending.limits.credit_limit.simulation.dimensions as dimensions
import tests.lending.limits.credit_limit.simulation.parameters as parameters

log = logging.getLogger(
    "inception_sdk.test_framework.contracts.simulation.vault_caller.sim_test_request_logger"
)
handler = logging.FileHandler("/tmp/req.json", mode="w")
log.propagate = False
log.addHandler(handler)
log.setLevel(logging.DEBUG)
handler.setLevel(logging.DEBUG)

SMART_CONTRACT = Path("tests/lending/limits/credit_limit/smart_contract.py")


class CreditLimitBaseTest(SimulationTestCase):
    parameter_resource_dirs = [
        str(Path("src/feature_library/common/parameter_resource_defs")),
        str(Path("src/feature_library/lending/limits/parameter_resource_defs")),
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
                    permitted_denominations=[dimensions.DEFAULT_DENOMINATION],
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
            debug=True,
            use_v1_accounts=False,
        )


class CreditLimitTest(CreditLimitBaseTest):
    @pytest.mark.sim
    def test_purchase_within_credit_limit(self):
        start = self.default_simulation_start_datetime
        end = start + relativedelta(days=1)

        purchase_amount = Decimal(1000)

        sub_tests = [
            SubTest(
                description="Purchase within limit accepted",
                events=[
                    create_outbound_hard_settlement_instruction(
                        amount=str(purchase_amount),
                        event_datetime=start + relativedelta(minutes=1),
                        target_account_id=accounts.CUSTOMER_ACCOUNT,
                        internal_account_id=accounts.DUMMY_INTERNAL_ACCOUNT,
                        denomination=dimensions.DEFAULT_DENOMINATION,
                        instruction_details={
                            "event": "PURCHASE",
                            "description": f"Purchase {purchase_amount} GBP.",
                        },
                    ),
                ],
                expected_balances_at_ts={
                    start + relativedelta(minutes=1): {
                        accounts.CUSTOMER_ACCOUNT: [
                            (dimensions.DEFAULT, purchase_amount),
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
    def test_purchase_over_credit_limit_rejected(self):
        start = self.default_simulation_start_datetime
        end = start + relativedelta(days=1)

        parameter_values = {
            **parameters.default_parameter_values,
            credit_limit_module.CREDIT_LIMIT_PARAM.id: DecimalParameterValue(
                decimal_value=Decimal(1000)
            ),
        }

        sub_tests = [
            SubTest(
                description="Purchase over limit rejected",
                events=[
                    create_outbound_hard_settlement_instruction(
                        amount=str(Decimal(1500)),
                        event_datetime=start + relativedelta(minutes=1),
                        target_account_id=accounts.CUSTOMER_ACCOUNT,
                        internal_account_id=accounts.DUMMY_INTERNAL_ACCOUNT,
                        denomination=dimensions.DEFAULT_DENOMINATION,
                        instruction_details={
                            "event": "PURCHASE",
                            "description": "Purchase 1500 GBP.",
                        },
                    ),
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
