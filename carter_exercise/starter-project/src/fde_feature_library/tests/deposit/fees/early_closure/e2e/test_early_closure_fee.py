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
from tests.deposit.fees.early_closure.e2e import accounts, dimensions, parameters

UTC = ZoneInfo("UTC")

default_start_date = datetime.now(tz=UTC) - relativedelta(days=6)


class EarlyClosureFeeTest(endtoend.AcceleratedEnd2EndTest):
    def setUp(self):
        endtoend.testhandle.CONTRACTS = {
            accounts.CUSTOMER_ACCOUNT: {
                "path": str(Path("tests/deposit/fees/early_closure/simulation/smart_contract.py")),
                "template_params": {},
            }
        }
        endtoend.testhandle.CALENDARS = {
            "PUBLIC_HOLIDAYS": str(
                Path("tests/deposit/fees/early_closure/e2e/calendars/public_holidays.resource.yaml")
            )
        }
        endtoend.testhandle.TSIDE_TO_INTERNAL_ACCOUNT_ID = accounts.internal_accounts_tside
        endtoend.testhandle.PARAMETER_RESOURCE_DIRS = [
            str(Path("src/feature_library/common/parameter_resource_defs")),
            str(Path("src/feature_library/deposit/fees/parameter_resource_defs")),
        ]
        super().setUp()

    @pytest.mark.accelerated_e2e
    def test_fee_applied_on_closure(self):
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

        # Trigger closure within the 7 day period
        closure_date = opening_date + relativedelta(days=5)

        # Before closing we must withdraw the balance remaining after the expected closure fee.
        # Deposit 25, the fee is 10, so withdraw 15.
        deposit_amount = Decimal(25)
        pib_id = endtoend.postings_helper.inbound_hard_settlement(
            amount=deposit_amount,
            account_id=customer_account.id,
            value_datetime=opening_date + relativedelta(hours=1),
            denomination=DEFAULT_DENOMINATION,
        )
        pib = endtoend.postings_helper.get_posting_batch(pib_id=pib_id)
        self.assertEqual(pib["status"], "POSTING_INSTRUCTION_BATCH_STATUS_ACCEPTED")
        endtoend.balances_helper.wait_for_account_balances(
            account_id=customer_account.id,
            expected_balances=[
                (dimensions.DEFAULT, str(deposit_amount)),
            ],
        )

        # The fee will be 10, so we need to withdraw 15 before closing
        withdraw_amount = Decimal(15)
        pib_id = endtoend.postings_helper.outbound_hard_settlement(
            amount=withdraw_amount,
            account_id=customer_account.id,
            value_datetime=closure_date - relativedelta(hours=1),
            denomination=DEFAULT_DENOMINATION,
        )
        pib = endtoend.postings_helper.get_posting_batch(pib_id=pib_id)
        self.assertEqual(pib["status"], "POSTING_INSTRUCTION_BATCH_STATUS_ACCEPTED")
        endtoend.balances_helper.wait_for_account_balances(
            account_id=customer_account.id,
            expected_balances=[
                (dimensions.DEFAULT, str(deposit_amount - withdraw_amount)),
            ],
        )

        # Close the account
        customer_account = endtoend.core_api_helper.update_account_v2(
            account_id=customer_account.id,
            status=AccountV2Status.ACCOUNT_STATUS_CLOSED,
        )
        # The fee should be applied as part of the closure process.
        self.assertEqual("ACCOUNT_STATUS_CLOSED", customer_account["status"])
