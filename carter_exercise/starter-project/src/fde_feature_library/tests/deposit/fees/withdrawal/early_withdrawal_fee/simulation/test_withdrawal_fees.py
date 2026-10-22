# standard libs
import logging
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
from dateutil.relativedelta import relativedelta

import feature_library.deposit.fees.withdrawal.early_withdrawal_fees as early_withdrawal_fees

from inception_sdk.test_framework.contracts.simulation.data_objects.data_objects import (
    AccountConfig,
    ContractConfig,
    ContractNotificationResourceType,
    ExpectedContractNotification,
    ExpectedRejection,
    SimulationEvent,
    SimulationTestScenario,
    SubTest,
)
from inception_sdk.test_framework.contracts.simulation.helper import (
    create_calendar_event,
    create_inbound_hard_settlement_instruction,
    create_outbound_hard_settlement_instruction,
)
from inception_sdk.test_framework.contracts.simulation.utils import SimulationTestCase

# inception sdk
from inception_sdk.vault.core_api import (
    DecimalParameterValue,
    ParameterValue,
)

# library
import tests.deposit.fees.withdrawal.early_withdrawal_fee.simulation.accounts as accounts  # noqa: E501
import tests.deposit.fees.withdrawal.early_withdrawal_fee.simulation.dimensions as dimensions  # noqa: E501
import tests.deposit.fees.withdrawal.early_withdrawal_fee.simulation.parameters as parameters  # noqa: E501
import tests.deposit.fees.withdrawal.early_withdrawal_fee.smart_contract as smart_contract

log = logging.getLogger(
    "inception_sdk.test_framework.contracts.simulation.vault_caller.sim_test_request_logger"
)
handler = logging.FileHandler("/tmp/req.json", mode="w")  # whatever path the user wants to put
log.propagate = False  # comment this out if you do not want printing to stdout
log.addHandler(handler)
log.setLevel(logging.DEBUG)
handler.setLevel(logging.DEBUG)

SMART_CONTRACT = Path("tests/deposit/fees/withdrawal/early_withdrawal_fee/smart_contract.py")
UTC = ZoneInfo("UTC")


class WithdrawalFeesBaseTest(SimulationTestCase):
    contract_filepaths = [str(SMART_CONTRACT)]
    internal_accounts = accounts.default_internal_accounts
    parameter_values = parameters.default_parameter_values
    parameters = parameters.expected_param_resources
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
            calendar_ids=["PUBLIC_HOLIDAYS"],
            parameters=self.parameters,
            debug=debug,
            use_v1_accounts=False,
        )


class WithdrawalFeesTest(WithdrawalFeesBaseTest):
    @pytest.mark.sim
    def test_early_withdrawal_fees_covered_by_withdrawal_amount(self):
        start = self.default_simulation_start_datetime
        end = start + relativedelta(minutes=2)
        flat_fee_amount: Decimal = parameters.default_parameter_values[
            early_withdrawal_fees.EARLY_WITHDRAWAL_FLAT_FEE_PARAM.id
        ].decimal_value.quantize(Decimal("0.01"), ROUND_HALF_UP)  # ty: ignore[possibly-missing-attribute]
        deposit_amount = Decimal(100)
        withdrawal_amount = Decimal(40)
        percentage_fee_amount: Decimal = (
            parameters.default_parameter_values[
                early_withdrawal_fees.EARLY_WITHDRAWAL_PERCENTAGE_FEE_PARAM.id
            ].decimal_value  # ty: ignore[possibly-missing-attribute]
            * withdrawal_amount
        ).quantize(Decimal("0.01"), ROUND_HALF_UP)
        self.assertEqual(flat_fee_amount, Decimal(5))
        self.assertEqual(percentage_fee_amount, Decimal(4))
        client_batch_id = "client_batch_id"
        sub_tests = [
            SubTest(
                description="Credit in a valid denomination",
                events=[
                    create_inbound_hard_settlement_instruction(
                        amount=str(deposit_amount),
                        event_datetime=start,
                        target_account_id=accounts.CUSTOMER_ACCOUNT,
                        internal_account_id=accounts.DUMMY_INTERNAL_ACCOUNT,
                        denomination=dimensions.DEFAULT_DENOMINATION,
                        instruction_details={
                            "event": "DEPOSIT",
                            "description": "Deposit 100 GBP.",
                        },
                    ),
                ],
                expected_balances_at_ts={
                    start: {
                        accounts.CUSTOMER_ACCOUNT: [
                            (dimensions.DEFAULT, Decimal(100)),
                        ]
                    }
                },
            ),
            SubTest(
                description="Withdrawal",
                events=[
                    create_outbound_hard_settlement_instruction(
                        amount=str(withdrawal_amount),
                        event_datetime=start + relativedelta(minutes=1),
                        target_account_id=accounts.CUSTOMER_ACCOUNT,
                        internal_account_id=accounts.DUMMY_INTERNAL_ACCOUNT,
                        denomination=dimensions.DEFAULT_DENOMINATION,
                        instruction_details={
                            "event": "WITHDRAWAL",
                            "description": "Withdraw 40 GBP.",
                        },
                        client_batch_id=client_batch_id,
                    )
                ],
                expected_balances_at_ts={
                    start + relativedelta(minutes=1): {
                        accounts.CUSTOMER_ACCOUNT: [
                            (dimensions.DEFAULT, Decimal(60)),
                            (dimensions.EARLY_WITHDRAWALS_TRACKER_DIMENSION, Decimal(40)),
                        ]
                    }
                },
                expected_contract_notifications=[
                    ExpectedContractNotification(
                        timestamp=start + relativedelta(minutes=1),
                        notification_type=early_withdrawal_fees.notification_type(
                            smart_contract.PRODUCT_NAME
                        ),
                        notification_details={
                            "account_id": accounts.CUSTOMER_ACCOUNT,
                            "client_batch_id": client_batch_id,
                            "denomination": dimensions.DEFAULT_DENOMINATION,
                            "flat_fee_amount": str(flat_fee_amount),
                            "percentage_fee_amount": str(percentage_fee_amount),
                            "total_fee_amount": str(flat_fee_amount + percentage_fee_amount),
                            "withdrawal_amount": str(
                                withdrawal_amount.quantize(Decimal("0.01"), ROUND_HALF_UP)
                            ),
                        },
                        resource_id=accounts.CUSTOMER_ACCOUNT,
                        resource_type=ContractNotificationResourceType.RESOURCE_ACCOUNT,
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
    def test_withdrawal_blocked_on_public_holiday(self):
        start = self.default_simulation_start_datetime
        bank_holiday_start: datetime = start
        end = start + relativedelta(minutes=2)
        deposit_amount = Decimal(100)
        withdrawal_amount = Decimal(40)
        client_batch_id = "client_batch_id"
        sub_tests = [
            SubTest(
                description="Credit in a valid denomination",
                events=[
                    create_calendar_event(
                        timestamp=start,
                        calendar_event_id="BANK_HOLIDAY",
                        calendar_id="PUBLIC_HOLIDAYS",
                        start_timestamp=bank_holiday_start,
                        end_timestamp=bank_holiday_start + relativedelta(days=1),
                    ),
                    create_inbound_hard_settlement_instruction(
                        amount=str(deposit_amount),
                        event_datetime=start,
                        target_account_id=accounts.CUSTOMER_ACCOUNT,
                        internal_account_id=accounts.DUMMY_INTERNAL_ACCOUNT,
                        denomination=dimensions.DEFAULT_DENOMINATION,
                        instruction_details={
                            "event": "DEPOSIT",
                            "description": "Deposit 100 GBP.",
                        },
                    ),
                ],
                expected_balances_at_ts={
                    start: {
                        accounts.CUSTOMER_ACCOUNT: [
                            (dimensions.DEFAULT, Decimal(100)),
                        ]
                    }
                },
            ),
            SubTest(
                description="Withdrawal",
                events=[
                    create_outbound_hard_settlement_instruction(
                        amount=str(withdrawal_amount),
                        event_datetime=start + relativedelta(minutes=1),
                        target_account_id=accounts.CUSTOMER_ACCOUNT,
                        internal_account_id=accounts.DUMMY_INTERNAL_ACCOUNT,
                        denomination=dimensions.DEFAULT_DENOMINATION,
                        instruction_details={
                            "event": "WITHDRAWAL",
                            "description": "Withdraw 40 GBP.",
                            "calendar_override": "False",
                        },
                        client_batch_id=client_batch_id,
                    )
                ],
                expected_balances_at_ts={
                    start + relativedelta(minutes=1): {
                        accounts.CUSTOMER_ACCOUNT: [
                            (dimensions.DEFAULT, Decimal(100)),
                            (dimensions.EARLY_WITHDRAWALS_TRACKER_DIMENSION, Decimal(0)),
                        ]
                    }
                },
                expected_posting_rejections=[
                    ExpectedRejection(
                        timestamp=start + relativedelta(minutes=1),
                        rejection_type="AgainstTermsAndConditions",
                        rejection_reason="Cannot withdraw on public holidays.",
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
    def test_withdrawal_override_on_public_holiday(self):
        start = self.default_simulation_start_datetime
        bank_holiday_start: datetime = start
        end = start + relativedelta(minutes=2)
        deposit_amount = Decimal(100)
        withdrawal_amount = Decimal(40)
        client_batch_id = "client_batch_id"
        sub_tests = [
            SubTest(
                description="Credit in a valid denomination",
                events=[
                    create_calendar_event(
                        timestamp=start,
                        calendar_event_id="BANK_HOLIDAY",
                        calendar_id="PUBLIC_HOLIDAYS",
                        start_timestamp=bank_holiday_start,
                        end_timestamp=bank_holiday_start + relativedelta(days=1),
                    ),
                    create_inbound_hard_settlement_instruction(
                        amount=str(deposit_amount),
                        event_datetime=start,
                        target_account_id=accounts.CUSTOMER_ACCOUNT,
                        internal_account_id=accounts.DUMMY_INTERNAL_ACCOUNT,
                        denomination=dimensions.DEFAULT_DENOMINATION,
                        instruction_details={
                            "event": "DEPOSIT",
                            "description": "Deposit 100 GBP.",
                        },
                    ),
                ],
                expected_balances_at_ts={
                    start: {
                        accounts.CUSTOMER_ACCOUNT: [
                            (dimensions.DEFAULT, Decimal(100)),
                        ]
                    }
                },
            ),
            SubTest(
                description="Withdrawal",
                events=[
                    create_outbound_hard_settlement_instruction(
                        amount=str(withdrawal_amount),
                        event_datetime=start + relativedelta(minutes=1),
                        target_account_id=accounts.CUSTOMER_ACCOUNT,
                        internal_account_id=accounts.DUMMY_INTERNAL_ACCOUNT,
                        denomination=dimensions.DEFAULT_DENOMINATION,
                        instruction_details={
                            "event": "WITHDRAWAL",
                            "description": "Withdraw 40 GBP.",
                            "calendar_override": "True",
                        },
                        client_batch_id=client_batch_id,
                    )
                ],
                expected_balances_at_ts={
                    start + relativedelta(minutes=1): {
                        accounts.CUSTOMER_ACCOUNT: [
                            (dimensions.DEFAULT, Decimal(60)),
                            (dimensions.EARLY_WITHDRAWALS_TRACKER_DIMENSION, Decimal(40)),
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
    def test_attributes(self):
        start = self.default_simulation_start_datetime
        end = start + relativedelta(minutes=1)
        max_withdrawal_percentage = Decimal("0.2")
        fee_free_percentage = Decimal("0.4")
        parameter_values: dict[str, ParameterValue] = {
            **parameters.default_parameter_values,
            smart_contract.early_withdrawal_fees.MAXIMUM_WITHDRAWAL_PERCENTAGE_LIMIT_PARAM.id: DecimalParameterValue(  # noqa: E501
                decimal_value=max_withdrawal_percentage
            ),
            smart_contract.early_withdrawal_fees.FEE_FREE_WITHDRAWAL_PERCENTAGE_LIMIT_PARAM.id: DecimalParameterValue(  # noqa: E501
                decimal_value=fee_free_percentage
            ),
        }
        deposit_amount = Decimal(100)
        max_withdrawal_limit: Decimal = (deposit_amount * max_withdrawal_percentage).quantize(
            Decimal("0.01"), ROUND_HALF_UP
        )
        fee_free_withdrawal_limit: Decimal = (deposit_amount * fee_free_percentage).quantize(
            Decimal("0.01"), ROUND_HALF_UP
        )
        sub_tests = [
            SubTest(
                description="Test attributes",
                events=[
                    create_inbound_hard_settlement_instruction(
                        amount=str(deposit_amount),
                        event_datetime=start,
                        target_account_id=accounts.CUSTOMER_ACCOUNT,
                        internal_account_id=accounts.DUMMY_INTERNAL_ACCOUNT,
                        denomination=dimensions.DEFAULT_DENOMINATION,
                        instruction_details={
                            "event": "DEPOSIT",
                            "description": f"Deposit {deposit_amount} GBP.",
                        },
                    ),
                    SimulationEvent(
                        time=start,
                        event={
                            "list_account_attribute_values": {
                                "account_ids": [accounts.CUSTOMER_ACCOUNT],
                                "attribute_names": [
                                    early_withdrawal_fees.MAXIMUM_WITHDRAWAL_LIMIT_ATTRIBUTE.name,
                                    early_withdrawal_fees.FEE_FREE_WITHDRAWAL_LIMIT_ATTRIBUTE.name,
                                ],
                            }
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
        ]

        test_scenario = self.get_simulation_test_scenario(
            start=start,
            end=end,
            sub_tests=sub_tests,
            parameter_values=parameter_values,
        )
        results = self.run_test_scenario(test_scenario)
        attribute_result = next(
            filter(lambda r: r["result"]["account_attribute_values"], results), None
        )
        self.assertIsNotNone(attribute_result)
        attribute_values = attribute_result["result"]["account_attribute_values"][  # ty: ignore[not-subscriptable]
            accounts.CUSTOMER_ACCOUNT
        ]["account_attribute_values"]
        self.assertEqual(len(attribute_values), 2)
        fee_free_withdrawal_limit_attribute = next(
            filter(
                lambda attr_val: (
                    attr_val["attribute_name"]
                    == early_withdrawal_fees.FEE_FREE_WITHDRAWAL_LIMIT_ATTRIBUTE.name
                ),
                attribute_values,
            ),
            None,
        )
        self.assertIsNotNone(fee_free_withdrawal_limit_attribute)
        max_withdrawal_limit_attribute = next(
            filter(
                lambda attr_val: (
                    attr_val["attribute_name"]
                    == early_withdrawal_fees.MAXIMUM_WITHDRAWAL_LIMIT_ATTRIBUTE.name
                ),
                attribute_values,
            ),
            None,
        )
        self.assertIsNotNone(max_withdrawal_limit_attribute)
        self.assertEqual(
            Decimal(fee_free_withdrawal_limit_attribute["value"]["decimal_value"]["value"]),  # ty: ignore[not-subscriptable]
            fee_free_withdrawal_limit,
        )
        self.assertEqual(
            Decimal(max_withdrawal_limit_attribute["value"]["decimal_value"]["value"]),  # ty: ignore[not-subscriptable]
            max_withdrawal_limit,
        )
