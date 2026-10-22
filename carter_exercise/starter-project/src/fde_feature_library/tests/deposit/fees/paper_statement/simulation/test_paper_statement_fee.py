# standard libs
import logging
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
from dateutil.relativedelta import relativedelta

import feature_library.deposit.fees.paper_statement_fee as paper_statement_fee_module

from inception_sdk.test_framework.contracts.simulation.data_objects.data_objects import (
    AccountConfig,
    ContractConfig,
    SimulationTestScenario,
    SubTest,
)
from inception_sdk.test_framework.contracts.simulation.helper import (
    create_inbound_hard_settlement_instruction,
)
from inception_sdk.test_framework.contracts.simulation.utils import SimulationTestCase
from inception_sdk.vault.core_api import (
    DecimalParameterValue,
    EnumerationParameterValue,
)

import tests.deposit.fees.paper_statement.simulation.accounts as accounts
import tests.deposit.fees.paper_statement.simulation.dimensions as dimensions
import tests.deposit.fees.paper_statement.simulation.parameters as parameters

log = logging.getLogger(
    "inception_sdk.test_framework.contracts.simulation.vault_caller.sim_test_request_logger"
)
handler = logging.FileHandler("/tmp/req.json", mode="w")
log.propagate = False
log.addHandler(handler)
log.setLevel(logging.DEBUG)
handler.setLevel(logging.DEBUG)

SMART_CONTRACT = Path("tests/deposit/fees/paper_statement/smart_contract.py")


class PaperStatementFeeBaseTest(SimulationTestCase):
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
            debug=debug,
            use_v1_accounts=False,
        )


class PaperStatementFeeTest(PaperStatementFeeBaseTest):
    @pytest.mark.sim
    def test_paper_statement_fee_applied(self):
        start = self.default_simulation_start_datetime
        end = start + relativedelta(months=1, days=1)

        deposit_amount = Decimal(100)
        fee_amount = Decimal(3)

        parameter_values = {
            **parameters.default_parameter_values,
            paper_statement_fee_module.PAPER_STATEMENT_FEE_DAY_PARAM.id: DecimalParameterValue(
                decimal_value=Decimal(2)
            ),
        }

        sub_tests = [
            SubTest(
                description="Credit",
                events=[
                    create_inbound_hard_settlement_instruction(
                        amount=str(deposit_amount),
                        event_datetime=start + relativedelta(minutes=1),
                        target_account_id=accounts.CUSTOMER_ACCOUNT,
                        internal_account_id=accounts.DUMMY_INTERNAL_ACCOUNT,
                        denomination=dimensions.DEFAULT_DENOMINATION,
                        instruction_details={
                            "event": "DEPOSIT",
                            "description": f"Deposit {deposit_amount} GBP.",
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
                description="Fee is applied on day 2",
                events=[],
                expected_balances_at_ts={
                    start + relativedelta(days=1, seconds=5): {
                        accounts.CUSTOMER_ACCOUNT: [
                            (dimensions.DEFAULT, deposit_amount - fee_amount),
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

    @pytest.mark.sim
    def test_paper_statement_fee_not_applied_when_disabled(self):
        start = self.default_simulation_start_datetime
        end = start + relativedelta(months=1, days=1)

        deposit_amount = Decimal(100)

        parameter_values = {
            **parameters.default_parameter_values,
            paper_statement_fee_module.PAPER_STATEMENT_FEE_ENABLED_PARAM_ID: (
                EnumerationParameterValue(enumeration_value="False")
            ),
            paper_statement_fee_module.PAPER_STATEMENT_FEE_DAY_PARAM.id: DecimalParameterValue(
                decimal_value=Decimal(2)
            ),
        }

        sub_tests = [
            SubTest(
                description="Credit",
                events=[
                    create_inbound_hard_settlement_instruction(
                        amount=str(deposit_amount),
                        event_datetime=start + relativedelta(minutes=1),
                        target_account_id=accounts.CUSTOMER_ACCOUNT,
                        internal_account_id=accounts.DUMMY_INTERNAL_ACCOUNT,
                        denomination=dimensions.DEFAULT_DENOMINATION,
                        instruction_details={
                            "event": "DEPOSIT",
                            "description": f"Deposit {deposit_amount} GBP.",
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
                description="Fee is NOT applied on day 2",
                events=[],
                expected_balances_at_ts={
                    start + relativedelta(days=1, seconds=5): {
                        accounts.CUSTOMER_ACCOUNT: [
                            (dimensions.DEFAULT, deposit_amount),
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


class PartialPaperStatementFeeTest(PaperStatementFeeBaseTest):
    @pytest.mark.sim
    def test_partial_paper_statement_fee_applied_when_enabled_and_insufficient_balance(self):
        start = self.default_simulation_start_datetime
        end = start + relativedelta(months=1, days=1)

        deposit_amount = Decimal(1)

        parameter_values = {
            **parameters.default_parameter_values,
            paper_statement_fee_module.PAPER_STATEMENT_FEE_PARTIAL_FEE_ENABLED_PARAM_ID: (
                EnumerationParameterValue(enumeration_value="True")
            ),
            paper_statement_fee_module.PAPER_STATEMENT_FEE_DAY_PARAM.id: DecimalParameterValue(
                decimal_value=Decimal(2)
            ),
        }

        sub_tests = [
            SubTest(
                description="Credit small amount",
                events=[
                    create_inbound_hard_settlement_instruction(
                        amount=str(deposit_amount),
                        event_datetime=start + relativedelta(minutes=1),
                        target_account_id=accounts.CUSTOMER_ACCOUNT,
                        internal_account_id=accounts.DUMMY_INTERNAL_ACCOUNT,
                        denomination=dimensions.DEFAULT_DENOMINATION,
                        instruction_details={
                            "event": "DEPOSIT",
                            "description": f"Deposit {deposit_amount} GBP.",
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
                description="Partial fee is applied: 1 charged, 2 tracked on day 2",
                events=[],
                expected_balances_at_ts={
                    start + relativedelta(days=1, seconds=5): {
                        accounts.CUSTOMER_ACCOUNT: [
                            (dimensions.DEFAULT, Decimal(0)),
                            (dimensions.OUTSTANDING_PAPER_STATEMENT_FEE_TRACKER, Decimal(2)),
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
