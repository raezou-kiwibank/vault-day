# Copyright @ 2026 Thought Machine Group Limited. All rights reserved.
# standard libs
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

# inception sdk
from inception_sdk.test_framework import endtoend
from inception_sdk.vault.core_api import (
    AccountV2Status,
    CreateOptions,
    CustomerAccountRequestBody,
)

from tests.common.test_denomination import DEFAULT_DENOMINATION

# library
from tests.lending.principal.e2e import accounts, parameters

UTC = ZoneInfo("UTC")

default_start_date = datetime(2026, 1, 1, tzinfo=UTC)


class MinimumLoanPrincipalE2ETest(endtoend.AcceleratedEnd2EndTest):
    @classmethod
    def setUpClass(cls):
        endtoend.testhandle.CONTRACTS = {
            accounts.CUSTOMER_ACCOUNT: {
                "path": str(Path("tests/lending/principal/minimum_loan_principal_sc.py")),
                "template_params": {},
            }
        }
        endtoend.testhandle.TSIDE_TO_INTERNAL_ACCOUNT_ID = accounts.internal_accounts_tside
        endtoend.testhandle.PARAMETER_RESOURCE_DIRS = [
            str(Path("src/feature_library/common/parameter_resource_defs")),
            str(Path("src/feature_library/lending/principal/parameter_resource_defs")),
        ]
        super().setUpClass()

    @pytest.mark.accelerated_e2e
    def test_minimum_loan_principal(self):
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
                parameter_values=parameters.minimum_loan_principal_parameters,
            ),
        )
        self.assertEqual("ACCOUNT_STATUS_OPEN", customer_account.status)

        # Loan amount above limit: 100 > 50
        loan_amount = Decimal("100")
        pib_id = endtoend.postings_helper.outbound_hard_settlement(
            amount=loan_amount,
            account_id=customer_account.id,
            internal_account_id=accounts.DUMMY_INTERNAL_ACCOUNT,
            value_datetime=opening_date,
            denomination=DEFAULT_DENOMINATION,
        )
        pib = endtoend.postings_helper.get_posting_batch(pib_id=pib_id)
        self.assertEqual(pib["status"], "POSTING_INSTRUCTION_BATCH_STATUS_ACCEPTED")

        # Loan amount below limit: 10 < 50
        loan_below_limit_amount = Decimal("10")
        pib_under_limit_id = endtoend.postings_helper.outbound_hard_settlement(
            amount=loan_below_limit_amount,
            account_id=customer_account.id,
            internal_account_id=accounts.DUMMY_INTERNAL_ACCOUNT,
            value_datetime=opening_date,
            denomination=DEFAULT_DENOMINATION,
        )
        pib_under_limit = endtoend.postings_helper.get_posting_batch(pib_id=pib_under_limit_id)
        self.assertEqual(pib_under_limit["status"], "POSTING_INSTRUCTION_BATCH_STATUS_REJECTED")
