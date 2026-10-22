# Copyright @ 2026 Thought Machine Group Limited. All rights reserved.
# standard libs
from datetime import datetime
from decimal import Decimal
from pathlib import Path
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
from tests.deposit.fees.withdrawal.payment_type_flat_fee.e2e import accounts, dimensions, parameters

UTC = ZoneInfo("UTC")

default_start_date = datetime(2026, 1, 1, tzinfo=UTC)


class PaymentTypeFlatFeeTest(endtoend.AcceleratedEnd2EndTest):
    def setUp(self):
        endtoend.testhandle.CONTRACTS = {
            accounts.CUSTOMER_ACCOUNT: {
                "path": str(
                    Path(
                        "tests/deposit/fees/withdrawal/payment_type_flat_fee/simulation/smart_contract.py"
                    )
                ),
                "template_params": {},
            }
        }
        endtoend.testhandle.TSIDE_TO_INTERNAL_ACCOUNT_ID = accounts.internal_accounts_tside
        endtoend.testhandle.PARAMETER_RESOURCE_DIRS = [
            str(Path("src/feature_library/common/parameter_resource_defs")),
            str(Path("src/feature_library/deposit/fees/withdrawal/parameter_resource_defs")),
        ]
        super().setUp()

    @pytest.mark.accelerated_e2e
    def test_fee_applied(self):
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

        # 1. Deposit 10000
        deposit_amount = Decimal("10000")
        pib_id = endtoend.postings_helper.inbound_hard_settlement(
            amount=deposit_amount,
            account_id=customer_account.id,
            value_datetime=opening_date + relativedelta(minutes=1),
            denomination=DEFAULT_DENOMINATION,
            instruction_details={
                "event": "DEPOSIT",
                "description": "Deposit 10,000.",
            },
        )
        pib = endtoend.postings_helper.get_posting_batch(pib_id=pib_id)
        self.assertEqual(pib["status"], "POSTING_INSTRUCTION_BATCH_STATUS_ACCEPTED")
        working_bal: Decimal = deposit_amount
        endtoend.balances_helper.wait_for_account_balances(
            account_id=customer_account.id,
            expected_balances=[
                (dimensions.DEFAULT, str(working_bal)),
            ],
        )

        # 2. Withdrawal 5000 with ATM (charge 1)
        withdrawal_amount = Decimal(5000)
        atm_fee = Decimal(1)
        pib_id = endtoend.postings_helper.outbound_hard_settlement(
            amount=withdrawal_amount,
            account_id=customer_account.id,
            value_datetime=opening_date + relativedelta(minutes=2),
            denomination=DEFAULT_DENOMINATION,
            instruction_details={
                "PAYMENT_TYPE": "ATM",
            },
        )
        pib = endtoend.postings_helper.get_posting_batch(pib_id=pib_id)
        self.assertEqual(pib["status"], "POSTING_INSTRUCTION_BATCH_STATUS_ACCEPTED")
        working_bal -= withdrawal_amount + atm_fee
        self.assertEqual(working_bal, Decimal(4999))
        endtoend.balances_helper.wait_for_account_balances(
            account_id=customer_account.id,
            expected_balances=[
                (dimensions.DEFAULT, str(working_bal)),
            ],
        )

        # 3. Withdrawal 2000 with POS (charge 0.5)
        withdrawal_amount = Decimal(2000)
        pib_id = endtoend.postings_helper.outbound_hard_settlement(
            amount=withdrawal_amount,
            account_id=customer_account.id,
            value_datetime=opening_date + relativedelta(minutes=3),
            denomination=DEFAULT_DENOMINATION,
            instruction_details={
                "PAYMENT_TYPE": "POS",
            },
        )
        pib = endtoend.postings_helper.get_posting_batch(pib_id=pib_id)
        self.assertEqual(pib["status"], "POSTING_INSTRUCTION_BATCH_STATUS_ACCEPTED")
        pos_fee = Decimal("0.5")
        working_bal -= withdrawal_amount + pos_fee
        self.assertEqual(working_bal, Decimal("2998.5"))
        endtoend.balances_helper.wait_for_account_balances(
            account_id=customer_account.id,
            expected_balances=[
                (dimensions.DEFAULT, str(working_bal)),
            ],
        )

        # 4. Withdrawal 1000 with CHEQUE (no fee)
        withdrawal_amount = Decimal(1000)
        pib_id = endtoend.postings_helper.outbound_hard_settlement(
            amount=withdrawal_amount,
            account_id=customer_account.id,
            value_datetime=opening_date + relativedelta(minutes=4),
            denomination=DEFAULT_DENOMINATION,
            instruction_details={
                "PAYMENT_TYPE": "CHEQUE",
            },
        )
        pib = endtoend.postings_helper.get_posting_batch(pib_id=pib_id)
        self.assertEqual(pib["status"], "POSTING_INSTRUCTION_BATCH_STATUS_ACCEPTED")
        working_bal -= withdrawal_amount
        self.assertEqual(working_bal, Decimal("1998.5"))
        endtoend.balances_helper.wait_for_account_balances(
            account_id=customer_account.id,
            expected_balances=[
                (dimensions.DEFAULT, str(working_bal)),
            ],
        )
