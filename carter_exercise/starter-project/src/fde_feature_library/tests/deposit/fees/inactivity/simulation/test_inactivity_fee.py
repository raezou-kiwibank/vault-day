# standard libs
import logging
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
from dateutil.relativedelta import relativedelta

import feature_library.deposit.fees.inactivity_fee as inactivity_fee_module

from inception_sdk.test_framework.contracts.simulation.data_objects.data_objects import (
    AccountConfig,
    ContractConfig,
    SimulationTestScenario,
    SubTest,
)
from inception_sdk.test_framework.contracts.simulation.helper import (
    create_flag_definition_event,
    create_flag_event,
    create_inbound_hard_settlement_instruction,
)
from inception_sdk.test_framework.contracts.simulation.utils import SimulationTestCase
from inception_sdk.vault.core_api import (
    DecimalParameterValue,
    EnumerationParameterValue,
)

import tests.deposit.fees.inactivity.simulation.accounts as accounts
import tests.deposit.fees.inactivity.simulation.dimensions as dimensions
import tests.deposit.fees.inactivity.simulation.parameters as parameters

log = logging.getLogger(
    "inception_sdk.test_framework.contracts.simulation.vault_caller.sim_test_request_logger"
)
handler = logging.FileHandler("/tmp/req.json", mode="w")
log.propagate = False
log.addHandler(handler)
log.setLevel(logging.DEBUG)
handler.setLevel(logging.DEBUG)

SMART_CONTRACT = Path("tests/deposit/fees/inactivity/smart_contract.py")
INVALID_SMART_CONTRACT = Path("tests/deposit/fees/inactivity/invalid_smart_contract.py")


class InactivityFeeBaseTest(SimulationTestCase):
    contract_filepaths = [str(SMART_CONTRACT)]
    internal_accounts = accounts.default_internal_accounts
    parameter_values = parameters.default_parameter_values
    parameters = parameters.expected_param_resources
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
            debug=True,
            use_v1_accounts=False,
        )


class InactivityFeeTest(InactivityFeeBaseTest):
    @pytest.mark.sim
    def test_inactivity_fee_applied_when_flag_active(self):
        start = self.default_simulation_start_datetime
        end = start + relativedelta(months=1, days=1)

        deposit_amount = Decimal(100)
        fee_amount = Decimal(10)

        sub_tests = [
            SubTest(
                description="Credit and apply flag",
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
                    create_flag_definition_event(
                        timestamp=start + relativedelta(minutes=2),
                        flag_definition_id="ACCOUNT_INACTIVE",
                    ),
                    create_flag_event(
                        timestamp=start + relativedelta(days=1),
                        flag_definition_id="ACCOUNT_INACTIVE",
                        account_id=accounts.CUSTOMER_ACCOUNT,
                        expiry_timestamp=start + relativedelta(years=10),
                    ),
                ],
                expected_balances_at_ts={
                    start + relativedelta(days=1): {
                        accounts.CUSTOMER_ACCOUNT: [
                            (dimensions.DEFAULT, deposit_amount),
                        ]
                    }
                },
            ),
            SubTest(
                description="Fee is applied at end of month since flag is active",
                events=[],
                expected_balances_at_ts={
                    start + relativedelta(months=1, seconds=5): {
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
        )
        self.run_test_scenario(test_scenario)

    @pytest.mark.sim
    def test_inactivity_fee_end_of_month_reschedule(self):
        start = self.default_simulation_start_datetime
        end = start + relativedelta(months=4, days=5)

        parameter_values = {
            **parameters.default_parameter_values,
            inactivity_fee_module.INACTIVITY_FEE_APPLICATION_DAY_PARAM_ID: (
                DecimalParameterValue(decimal_value=Decimal(31))
            ),
        }

        sub_tests = [
            SubTest(
                description="Credit and apply flag",
                events=[
                    create_inbound_hard_settlement_instruction(
                        amount="100",
                        event_datetime=start + relativedelta(minutes=1),
                        target_account_id=accounts.CUSTOMER_ACCOUNT,
                        internal_account_id=accounts.DUMMY_INTERNAL_ACCOUNT,
                        denomination=dimensions.DEFAULT_DENOMINATION,
                        instruction_details={
                            "event": "DEPOSIT",
                            "description": "Deposit 100 GBP.",
                        },
                    ),
                    create_flag_definition_event(
                        timestamp=start + relativedelta(minutes=2),
                        flag_definition_id="ACCOUNT_INACTIVE",
                    ),
                    create_flag_event(
                        timestamp=start + relativedelta(days=1),
                        flag_definition_id="ACCOUNT_INACTIVE",
                        account_id=accounts.CUSTOMER_ACCOUNT,
                        expiry_timestamp=start + relativedelta(years=10),
                    ),
                ],
                expected_balances_at_ts={
                    start + relativedelta(days=1): {
                        accounts.CUSTOMER_ACCOUNT: [
                            (dimensions.DEFAULT, Decimal(100)),
                        ]
                    }
                },
            ),
            SubTest(
                description="Check end of month reschedule",
                events=[],
                expected_balances_at_ts={
                    datetime(2026, 1, 31, 0, 0, 5, tzinfo=ZoneInfo("UTC")): {
                        accounts.CUSTOMER_ACCOUNT: [
                            (dimensions.DEFAULT, Decimal(90)),
                        ]
                    },
                    datetime(2026, 2, 28, 0, 0, 5, tzinfo=ZoneInfo("UTC")): {
                        accounts.CUSTOMER_ACCOUNT: [
                            (dimensions.DEFAULT, Decimal(80)),
                        ]
                    },
                    datetime(2026, 3, 31, 0, 0, 5, tzinfo=ZoneInfo("UTC")): {
                        accounts.CUSTOMER_ACCOUNT: [
                            (dimensions.DEFAULT, Decimal(70)),
                        ]
                    },
                    datetime(2026, 4, 30, 0, 0, 5, tzinfo=ZoneInfo("UTC")): {
                        accounts.CUSTOMER_ACCOUNT: [
                            (dimensions.DEFAULT, Decimal(60)),
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
        )
        self.run_test_scenario(test_scenario)

    @pytest.mark.sim
    def test_inactivity_fee_not_applied_when_no_flag(self):
        start = self.default_simulation_start_datetime
        end = start + relativedelta(months=1, days=1)

        deposit_amount = Decimal(100)

        sub_tests = [
            SubTest(
                description="Credit, no flag applied",
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
                description="Fee is NOT applied at end of month",
                events=[],
                expected_balances_at_ts={
                    start + relativedelta(months=1, seconds=5): {
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
        )
        self.run_test_scenario(test_scenario)


class PartialInactivityFeeTest(InactivityFeeBaseTest):
    @pytest.mark.sim
    def test_partial_inactivity_fee_applied_when_enabled_and_insufficient_balance(self):
        start = self.default_simulation_start_datetime
        end = start + relativedelta(months=1, days=1)

        deposit_amount = Decimal(5)

        parameter_values = {
            **parameters.default_parameter_values,
            inactivity_fee_module.INACTIVITY_FEE_PARTIAL_FEE_ENABLED_PARAM_ID: (
                EnumerationParameterValue(enumeration_value="True")
            ),
        }

        sub_tests = [
            SubTest(
                description="Credit small amount and apply flag",
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
                    create_flag_definition_event(
                        timestamp=start + relativedelta(minutes=2),
                        flag_definition_id="ACCOUNT_INACTIVE",
                    ),
                    create_flag_event(
                        timestamp=start + relativedelta(days=1),
                        flag_definition_id="ACCOUNT_INACTIVE",
                        account_id=accounts.CUSTOMER_ACCOUNT,
                        expiry_timestamp=start + relativedelta(years=10),
                    ),
                ],
                expected_balances_at_ts={
                    start + relativedelta(days=1): {
                        accounts.CUSTOMER_ACCOUNT: [
                            (dimensions.DEFAULT, deposit_amount),
                        ]
                    }
                },
            ),
            SubTest(
                description="Partial fee is applied: 5 charged, 5 tracked",
                events=[],
                expected_balances_at_ts={
                    start + relativedelta(months=1, seconds=5): {
                        accounts.CUSTOMER_ACCOUNT: [
                            (dimensions.DEFAULT, Decimal(0)),
                            (dimensions.OUTSTANDING_INACTIVITY_FEE_TRACKER, Decimal(5)),
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


class InvalidStateAssertionTest(SimulationTestCase):
    contract_filepaths = [str(INVALID_SMART_CONTRACT)]
    internal_accounts = accounts.default_internal_accounts
    parameter_values = parameters.default_parameter_values
    parameters = parameters.expected_param_resources
    default_simulation_start_datetime = datetime(year=2026, month=1, day=1, tzinfo=ZoneInfo("UTC"))

    @classmethod
    def setUpClass(cls):
        cls.contract_filepath = str(INVALID_SMART_CONTRACT)
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
            debug=True,
            use_v1_accounts=False,
        )

    @pytest.mark.sim
    def test_schedule_failure_due_to_missing_denomination_parameter(self):
        start = self.default_simulation_start_datetime
        end = start + relativedelta(months=1, days=1)

        deposit_amount = Decimal(100)

        sub_tests = [
            SubTest(
                description="Credit and apply flag",
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
                    create_flag_definition_event(
                        timestamp=start + relativedelta(minutes=2),
                        flag_definition_id="ACCOUNT_INACTIVE",
                    ),
                    create_flag_event(
                        timestamp=start + relativedelta(days=1),
                        flag_definition_id="ACCOUNT_INACTIVE",
                        account_id=accounts.CUSTOMER_ACCOUNT,
                        expiry_timestamp=start + relativedelta(years=10),
                    ),
                ],
            ),
        ]

        test_scenario = self.get_simulation_test_scenario(
            start=start,
            end=end,
            sub_tests=sub_tests,
        )
        with self.assertRaises(AssertionError) as ex:
            self.run_test_scenario(test_scenario)

        self.assertTrue(
            "Rejection(message=\\'The following parameters are missing: "
            "missing_denomination\\', reason_code=RejectionReason.AGAINST_TNC)" in str(ex.exception)
        )
