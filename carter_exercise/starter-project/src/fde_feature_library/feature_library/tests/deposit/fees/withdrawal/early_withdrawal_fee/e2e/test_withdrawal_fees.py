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
from tests.deposit.fees.withdrawal.early_withdrawal_fee.e2e import accounts, dimensions, parameters

UTC = ZoneInfo("UTC")

default_start_date = datetime(2026, 1, 1, tzinfo=UTC)


class WithdrawalFeesTest(endtoend.End2Endtest):
    def setUp(self):
        endtoend.testhandle.CONTRACTS = {
            accounts.CUSTOMER_ACCOUNT: {
                "path": str(
                    Path("tests/deposit/fees/withdrawal/early_withdrawal_fee/smart_contract.py")
                ),
                "template_params": {},
            }
        }
        endtoend.testhandle.TSIDE_TO_INTERNAL_ACCOUNT_ID = accounts.internal_accounts_tside
        endtoend.testhandle.PARAMETER_RESOURCE_DIRS = [
            str(Path("src/feature_library/common/parameter_resource_defs")),
            str(Path("src/feature_library/deposit/fees/withdrawal/parameter_resource_defs")),
        ]
        endtoend.testhandle.CALENDARS = {
            "PUBLIC_HOLIDAYS": str(
                Path(
                    "tests/deposit/fees/withdrawal/early_withdrawal_fee/e2e/public_holidays.resource.yaml"
                )
            )
        }
        super().setUp()

    @pytest.mark.e2e
    def test_early_withdrawal_fees_covered_by_withdrawal_amount(self):
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

        deposit_amount = Decimal(100)
        pib_id = endtoend.postings_helper.inbound_hard_settlement(
            amount=deposit_amount,
            account_id=customer_account.id,
            value_datetime=opening_date,
            denomination=DEFAULT_DENOMINATION,
            instruction_details={"event": "DEPOSIT", "description": "Deposit 100 GBP."},
        )
        pib = endtoend.postings_helper.get_posting_batch(pib_id=pib_id)
        self.assertEqual(pib["status"], "POSTING_INSTRUCTION_BATCH_STATUS_ACCEPTED")

        endtoend.balances_helper.wait_for_account_balances(
            account_id=customer_account.id,
            expected_balances=[
                (dimensions.DEFAULT, str(deposit_amount)),
            ],
        )

        withdrawal_amount = Decimal(40)
        client_batch_id = str(uuid4())
        out_pib_id = endtoend.postings_helper.outbound_hard_settlement(
            amount=withdrawal_amount,
            account_id=customer_account.id,
            value_datetime=opening_date + relativedelta(minutes=1),
            denomination=DEFAULT_DENOMINATION,
            instruction_details={"event": "WITHDRAWAL", "description": "Withdraw 40 GBP."},
            client_batch_id=client_batch_id,
        )
        out_pib = endtoend.postings_helper.get_posting_batch(pib_id=out_pib_id)
        self.assertEqual(out_pib["status"], "POSTING_INSTRUCTION_BATCH_STATUS_ACCEPTED")

        endtoend.balances_helper.wait_for_account_balances(
            account_id=customer_account.id,
            expected_balances=[
                (dimensions.DEFAULT, str(deposit_amount - withdrawal_amount)),
                (dimensions.EARLY_WITHDRAWALS_TRACKER_DIMENSION, str(withdrawal_amount)),
            ],
        )

    @pytest.mark.e2e
    def test_withdrawal_blocked_on_public_holiday(self):
        endtoend.standard_setup()
        endtoend.testhandle.use_kafka = False

        opening_date = default_start_date
        endtoend.core_api_helper.create_calendar_event(
            calendar_id=endtoend.testhandle.calendar_ids_to_e2e_ids["PUBLIC_HOLIDAYS"],
            start_timestamp=opening_date,
            end_timestamp=opening_date + relativedelta(days=1),
            event_id="BANK_HOLIDAY_" + str(uuid4()),
            name="Bank Holiday",
            is_active=True,
        )

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

        deposit_amount = Decimal(100)
        pib_id = endtoend.postings_helper.inbound_hard_settlement(
            amount=deposit_amount,
            account_id=customer_account.id,
            value_datetime=opening_date,
            denomination=DEFAULT_DENOMINATION,
            instruction_details={"event": "DEPOSIT", "description": "Deposit 100 GBP."},
        )
        pib = endtoend.postings_helper.get_posting_batch(pib_id=pib_id)
        self.assertEqual(pib["status"], "POSTING_INSTRUCTION_BATCH_STATUS_ACCEPTED")

        endtoend.balances_helper.wait_for_account_balances(
            account_id=customer_account.id,
            expected_balances=[
                (dimensions.DEFAULT, str(deposit_amount)),
            ],
        )

        withdrawal_amount = Decimal(40)
        client_batch_id = str(uuid4())
        out_pib_id = endtoend.postings_helper.outbound_hard_settlement(
            amount=withdrawal_amount,
            account_id=customer_account.id,
            value_datetime=opening_date + relativedelta(minutes=1),
            denomination=DEFAULT_DENOMINATION,
            instruction_details={
                "event": "WITHDRAWAL",
                "description": "Withdraw 40 GBP.",
                "calendar_override": "False",
            },
            client_batch_id=client_batch_id,
        )
        out_pib = endtoend.postings_helper.get_posting_batch(pib_id=out_pib_id)
        self.assertEqual(out_pib["status"], "POSTING_INSTRUCTION_BATCH_STATUS_REJECTED")

    @pytest.mark.e2e
    def test_withdrawal_override_on_public_holiday(self):
        endtoend.standard_setup()
        endtoend.testhandle.use_kafka = False

        opening_date = default_start_date
        endtoend.core_api_helper.create_calendar_event(
            calendar_id=endtoend.testhandle.calendar_ids_to_e2e_ids["PUBLIC_HOLIDAYS"],
            start_timestamp=opening_date,
            end_timestamp=opening_date + relativedelta(days=1),
            event_id="BANK_HOLIDAY_" + str(uuid4()),
            name="Bank Holiday",
            is_active=True,
        )

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

        deposit_amount = Decimal(100)
        pib_id = endtoend.postings_helper.inbound_hard_settlement(
            amount=deposit_amount,
            account_id=customer_account.id,
            value_datetime=opening_date,
            denomination=DEFAULT_DENOMINATION,
            instruction_details={"event": "DEPOSIT", "description": "Deposit 100 GBP."},
        )
        pib = endtoend.postings_helper.get_posting_batch(pib_id=pib_id)
        self.assertEqual(pib["status"], "POSTING_INSTRUCTION_BATCH_STATUS_ACCEPTED")

        endtoend.balances_helper.wait_for_account_balances(
            account_id=customer_account.id,
            expected_balances=[
                (dimensions.DEFAULT, str(deposit_amount)),
            ],
        )

        withdrawal_amount = Decimal(40)
        client_batch_id = str(uuid4())
        out_pib_id = endtoend.postings_helper.outbound_hard_settlement(
            amount=withdrawal_amount,
            account_id=customer_account.id,
            value_datetime=opening_date + relativedelta(minutes=1),
            denomination=DEFAULT_DENOMINATION,
            instruction_details={
                "event": "WITHDRAWAL",
                "description": "Withdraw 40 GBP.",
                "calendar_override": "True",
            },
            client_batch_id=client_batch_id,
        )
        out_pib = endtoend.postings_helper.get_posting_batch(pib_id=out_pib_id)
        self.assertEqual(out_pib["status"], "POSTING_INSTRUCTION_BATCH_STATUS_ACCEPTED")

        endtoend.balances_helper.wait_for_account_balances(
            account_id=customer_account.id,
            expected_balances=[
                (dimensions.DEFAULT, str(deposit_amount - withdrawal_amount)),
                (dimensions.EARLY_WITHDRAWALS_TRACKER_DIMENSION, str(withdrawal_amount)),
            ],
        )
