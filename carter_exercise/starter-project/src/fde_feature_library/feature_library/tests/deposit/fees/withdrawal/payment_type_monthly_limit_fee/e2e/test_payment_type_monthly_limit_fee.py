# Copyright @ 2026 Thought Machine Group Limited. All rights reserved.
# standard libs
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from uuid import uuid4
from zoneinfo import ZoneInfo

import pytest
from dateutil.relativedelta import relativedelta

# inception sdk
from inception_sdk.test_framework import endtoend
from inception_sdk.vault.core_api import (
    AccountV2Status,
    CreateOptions,
    CustomerAccountRequestBody,
)

from tests.common.test_denomination import DEFAULT_DENOMINATION

# library
from tests.deposit.fees.withdrawal.payment_type_monthly_limit_fee.e2e import (
    accounts,
    dimensions,
    parameters,
)

UTC = ZoneInfo("UTC")
default_start_date = datetime(2026, 1, 1, tzinfo=UTC)


class PaymentTypeMonthlyLimitFeeTest(endtoend.End2Endtest):
    def setUp(self):
        endtoend.testhandle.CONTRACTS = {
            accounts.CUSTOMER_ACCOUNT: {
                "path": str(
                    Path(
                        "tests/deposit/fees/withdrawal/payment_type_monthly_limit_fee/simulation/smart_contract.py"
                    )
                ),
            }
        }
        endtoend.testhandle.TSIDE_TO_INTERNAL_ACCOUNT_ID = accounts.internal_accounts_tside
        endtoend.testhandle.PARAMETER_RESOURCE_DIRS = [
            str(Path("src/feature_library/common/parameter_resource_defs")),
            str(Path("src/feature_library/deposit/fees/withdrawal/parameter_resource_defs")),
        ]
        super().setUp()

    @pytest.mark.e2e
    def test_fee_applied_over_limit(self):
        endtoend.standard_setup()
        endtoend.testhandle.use_kafka = False
        opening_date = default_start_date
        customer_id = endtoend.core_api_helper.create_customer()
        customer_account = endtoend.contracts_helper.create_account_v2(
            product_id=accounts.CUSTOMER_ACCOUNT,
            account=CustomerAccountRequestBody(
                status=AccountV2Status.ACCOUNT_STATUS_OPEN,
                stakeholder_ids=[customer_id],
                activation_timestamp=opening_date,
            ),
            create_options=CreateOptions(
                parameter_values=parameters.default_parameter_values,
            ),
        )
        self.assertEqual("ACCOUNT_STATUS_OPEN", customer_account.status)

        deposit_amount = Decimal(10000)
        pib_id = endtoend.postings_helper.inbound_hard_settlement(
            amount=deposit_amount,
            account_id=customer_account.id,
            value_datetime=opening_date + relativedelta(minutes=1),
            denomination=DEFAULT_DENOMINATION,
            instruction_details={"event": "DEPOSIT"},
        )
        pib = endtoend.postings_helper.get_posting_batch(pib_id=pib_id)
        self.assertEqual(pib["status"], "POSTING_INSTRUCTION_BATCH_STATUS_ACCEPTED")

        endtoend.balances_helper.wait_for_account_balances(
            account_id=customer_account.id,
            expected_balances=[
                (dimensions.DEFAULT, str(deposit_amount)),
            ],
        )

        withdrawal_amount = Decimal(100)

        # 1st withdrawal
        out_pib_id_1 = endtoend.postings_helper.outbound_hard_settlement(
            amount=withdrawal_amount,
            account_id=customer_account.id,
            value_datetime=opening_date + relativedelta(minutes=2),
            denomination=DEFAULT_DENOMINATION,
            instruction_details={"PAYMENT_TYPE": "ATM"},
            client_batch_id=str(uuid4()),
        )
        out_pib_1 = endtoend.postings_helper.get_posting_batch(pib_id=out_pib_id_1)
        self.assertEqual(out_pib_1["status"], "POSTING_INSTRUCTION_BATCH_STATUS_ACCEPTED")

        endtoend.balances_helper.wait_for_account_balances(
            account_id=customer_account.id,
            expected_balances=[
                (dimensions.DEFAULT, str(deposit_amount - withdrawal_amount)),
            ],
        )

        # 2nd withdrawal
        out_pib_id_2 = endtoend.postings_helper.outbound_hard_settlement(
            amount=withdrawal_amount,
            account_id=customer_account.id,
            value_datetime=opening_date + relativedelta(minutes=3),
            denomination=DEFAULT_DENOMINATION,
            instruction_details={"PAYMENT_TYPE": "ATM"},
            client_batch_id=str(uuid4()),
        )
        out_pib_2 = endtoend.postings_helper.get_posting_batch(pib_id=out_pib_id_2)
        self.assertEqual(out_pib_2["status"], "POSTING_INSTRUCTION_BATCH_STATUS_ACCEPTED")

        endtoend.balances_helper.wait_for_account_balances(
            account_id=customer_account.id,
            expected_balances=[
                (dimensions.DEFAULT, str(deposit_amount - (withdrawal_amount * Decimal(2)))),
            ],
        )

        # 3rd withdrawal
        fee_amount = Decimal("0.50")
        out_pib_id_3 = endtoend.postings_helper.outbound_hard_settlement(
            amount=withdrawal_amount,
            account_id=customer_account.id,
            value_datetime=opening_date + relativedelta(minutes=4),
            denomination=DEFAULT_DENOMINATION,
            instruction_details={"PAYMENT_TYPE": "ATM"},
            client_batch_id=str(uuid4()),
        )
        out_pib_3 = endtoend.postings_helper.get_posting_batch(pib_id=out_pib_id_3)
        self.assertEqual(out_pib_3["status"], "POSTING_INSTRUCTION_BATCH_STATUS_ACCEPTED")

        endtoend.balances_helper.wait_for_account_balances(
            account_id=customer_account.id,
            expected_balances=[
                (
                    dimensions.DEFAULT,
                    str(deposit_amount - (withdrawal_amount * Decimal(3)) - fee_amount),
                ),
            ],
        )

    @pytest.mark.e2e
    def test_fee_not_applied_under_limit(self):
        endtoend.standard_setup()
        endtoend.testhandle.use_kafka = False
        opening_date = default_start_date
        customer_id = endtoend.core_api_helper.create_customer()
        customer_account = endtoend.contracts_helper.create_account_v2(
            product_id=accounts.CUSTOMER_ACCOUNT,
            account=CustomerAccountRequestBody(
                status=AccountV2Status.ACCOUNT_STATUS_OPEN,
                stakeholder_ids=[customer_id],
                activation_timestamp=opening_date,
            ),
            create_options=CreateOptions(
                parameter_values=parameters.default_parameter_values,
            ),
        )

        deposit_amount = Decimal(10000)
        pib_id = endtoend.postings_helper.inbound_hard_settlement(
            amount=deposit_amount,
            account_id=customer_account.id,
            value_datetime=opening_date + relativedelta(minutes=1),
            denomination=DEFAULT_DENOMINATION,
            instruction_details={"event": "DEPOSIT"},
        )
        pib = endtoend.postings_helper.get_posting_batch(pib_id=pib_id)
        self.assertEqual(pib["status"], "POSTING_INSTRUCTION_BATCH_STATUS_ACCEPTED")

        endtoend.balances_helper.wait_for_account_balances(
            account_id=customer_account.id,
            expected_balances=[
                (dimensions.DEFAULT, str(deposit_amount)),
            ],
        )

        withdrawal_amount = Decimal(100)
        client_batch_id = str(uuid4())
        out_pib_id = endtoend.postings_helper.outbound_hard_settlement(
            amount=withdrawal_amount,
            account_id=customer_account.id,
            value_datetime=opening_date + relativedelta(minutes=2),
            denomination=DEFAULT_DENOMINATION,
            instruction_details={"PAYMENT_TYPE": "ATM"},
            client_batch_id=client_batch_id,
        )
        out_pib = endtoend.postings_helper.get_posting_batch(pib_id=out_pib_id)
        self.assertEqual(out_pib["status"], "POSTING_INSTRUCTION_BATCH_STATUS_ACCEPTED")

        endtoend.balances_helper.wait_for_account_balances(
            account_id=customer_account.id,
            expected_balances=[
                (dimensions.DEFAULT, str(deposit_amount - withdrawal_amount)),
            ],
        )

    @pytest.mark.e2e
    def test_fee_not_applied_unmatched_payment_type(self):
        endtoend.standard_setup()
        endtoend.testhandle.use_kafka = False
        opening_date = default_start_date
        customer_id = endtoend.core_api_helper.create_customer()
        customer_account = endtoend.contracts_helper.create_account_v2(
            product_id=accounts.CUSTOMER_ACCOUNT,
            account=CustomerAccountRequestBody(
                status=AccountV2Status.ACCOUNT_STATUS_OPEN,
                stakeholder_ids=[customer_id],
                activation_timestamp=opening_date,
            ),
            create_options=CreateOptions(
                parameter_values=parameters.default_parameter_values,
            ),
        )

        deposit_amount = Decimal(10000)
        pib_id = endtoend.postings_helper.inbound_hard_settlement(
            amount=deposit_amount,
            account_id=customer_account.id,
            value_datetime=opening_date + relativedelta(minutes=1),
            denomination=DEFAULT_DENOMINATION,
            instruction_details={"event": "DEPOSIT"},
        )
        pib = endtoend.postings_helper.get_posting_batch(pib_id=pib_id)
        self.assertEqual(pib["status"], "POSTING_INSTRUCTION_BATCH_STATUS_ACCEPTED")

        endtoend.balances_helper.wait_for_account_balances(
            account_id=customer_account.id,
            expected_balances=[
                (dimensions.DEFAULT, str(deposit_amount)),
            ],
        )

        withdrawal_amount = Decimal(100)

        for i in range(1, 4):
            out_pib_id = endtoend.postings_helper.outbound_hard_settlement(
                amount=withdrawal_amount,
                account_id=customer_account.id,
                value_datetime=opening_date + relativedelta(minutes=i + 1),
                denomination=DEFAULT_DENOMINATION,
                instruction_details={"PAYMENT_TYPE": "POS"},
                client_batch_id=str(uuid4()),
            )
            out_pib = endtoend.postings_helper.get_posting_batch(pib_id=out_pib_id)
            self.assertEqual(out_pib["status"], "POSTING_INSTRUCTION_BATCH_STATUS_ACCEPTED")

            endtoend.balances_helper.wait_for_account_balances(
                account_id=customer_account.id,
                expected_balances=[
                    (dimensions.DEFAULT, str(deposit_amount - (withdrawal_amount * Decimal(i)))),
                ],
            )
