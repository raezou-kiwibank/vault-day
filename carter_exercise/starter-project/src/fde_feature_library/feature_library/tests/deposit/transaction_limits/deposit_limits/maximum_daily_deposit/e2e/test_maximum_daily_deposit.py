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
from tests.deposit.transaction_limits.deposit_limits.maximum_daily_deposit.e2e import (
    accounts,
    dimensions,
    parameters,
)

UTC = ZoneInfo("UTC")

default_start_date = datetime(2026, 1, 1, tzinfo=UTC)


class MaximumDailyDepositLimitTest(endtoend.End2Endtest):
    def setUp(self):
        endtoend.testhandle.CONTRACTS = {
            accounts.CUSTOMER_ACCOUNT: {
                "path": str(
                    Path(
                        "tests/deposit/transaction_limits/deposit_limits/maximum_daily_deposit/smart_contract.py"  # noqa: E501
                    )
                ),
                "template_params": {},
            }
        }
        endtoend.testhandle.TSIDE_TO_INTERNAL_ACCOUNT_ID = accounts.internal_accounts_tside
        endtoend.testhandle.PARAMETER_RESOURCE_DIRS = [
            str(Path("src/feature_library/common/parameter_resource_defs")),
            str(
                Path(
                    "src/feature_library/deposit/transaction_limits/deposit_limits/parameter_resource_defs"  # noqa: E501
                )
            ),
        ]
        super().setUp()

    @pytest.mark.e2e
    def test_maximum_daily_deposit_limit(self):
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

        # Credit under limit
        deposit_amount_1 = Decimal(50)
        pib_id = endtoend.postings_helper.inbound_hard_settlement(
            amount=deposit_amount_1,
            account_id=customer_account.id,
            value_datetime=opening_date,
            denomination=DEFAULT_DENOMINATION,
            instruction_details={
                "event": "DEPOSIT",
                "description": "Credit under limit",
            },
        )
        pib = endtoend.postings_helper.get_posting_batch(pib_id=pib_id)
        self.assertEqual(pib["status"], "POSTING_INSTRUCTION_BATCH_STATUS_ACCEPTED")

        endtoend.balances_helper.wait_for_account_balances(
            account_id=customer_account.id,
            expected_balances=[
                (dimensions.DEFAULT, str(deposit_amount_1)),
            ],
        )

        # Credit reaching exactly the limit for the day
        deposit_amount_2 = Decimal(50)
        pib_id = endtoend.postings_helper.inbound_hard_settlement(
            amount=deposit_amount_2,
            account_id=customer_account.id,
            value_datetime=opening_date + relativedelta(minutes=30),
            denomination=DEFAULT_DENOMINATION,
            instruction_details={
                "event": "DEPOSIT",
                "description": "Credit reaching exactly the limit for the day",
            },
        )
        pib = endtoend.postings_helper.get_posting_batch(pib_id=pib_id)
        self.assertEqual(pib["status"], "POSTING_INSTRUCTION_BATCH_STATUS_ACCEPTED")

        endtoend.balances_helper.wait_for_account_balances(
            account_id=customer_account.id,
            expected_balances=[
                (dimensions.DEFAULT, str(deposit_amount_1 + deposit_amount_2)),
            ],
        )

        # Credit over limit for the day
        deposit_amount_3 = Decimal("0.01")
        pib_id = endtoend.postings_helper.inbound_hard_settlement(
            amount=deposit_amount_3,
            account_id=customer_account.id,
            value_datetime=opening_date + relativedelta(hours=1),
            denomination=DEFAULT_DENOMINATION,
            instruction_details={
                "event": "DEPOSIT",
                "description": "Credit over limit for the day",
            },
        )
        pib = endtoend.postings_helper.get_posting_batch(pib_id=pib_id)
        self.assertEqual(pib["status"], "POSTING_INSTRUCTION_BATCH_STATUS_REJECTED")

        # Credit on next day resets the limit
        deposit_amount_4 = Decimal(50)
        pib_id = endtoend.postings_helper.inbound_hard_settlement(
            amount=deposit_amount_4,
            account_id=customer_account.id,
            value_datetime=opening_date + relativedelta(days=1),
            denomination=DEFAULT_DENOMINATION,
            instruction_details={
                "event": "DEPOSIT",
                "description": "Credit on next day resets the limit",
            },
        )
        pib = endtoend.postings_helper.get_posting_batch(pib_id=pib_id)
        self.assertEqual(pib["status"], "POSTING_INSTRUCTION_BATCH_STATUS_ACCEPTED")

        endtoend.balances_helper.wait_for_account_balances(
            account_id=customer_account.id,
            expected_balances=[
                (dimensions.DEFAULT, str(deposit_amount_1 + deposit_amount_2 + deposit_amount_4)),
            ],
        )
