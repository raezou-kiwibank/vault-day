# Copyright @ 2026 Thought Machine Group Limited. All rights reserved.
# standard libs
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
from dateutil.relativedelta import relativedelta

# features
# inception sdk
from inception_sdk.test_framework import endtoend
from inception_sdk.vault.core_api import (
    AccountV2Status,
    CreateOptions,
    CustomerAccountRequestBody,
)

# e2e
import tests.deposit.temporal_features.cooling_off_period.e2e.accounts as accounts
import tests.deposit.temporal_features.cooling_off_period.e2e.parameters as parameters
import tests.deposit.temporal_features.cooling_off_period.smart_contract as smart_contract

# tests
from tests.common.test_denomination import DEFAULT_DENOMINATION

UTC = ZoneInfo("UTC")
SMART_CONTRACT = "tests/deposit/temporal_features/cooling_off_period/smart_contract.py"


@pytest.mark.e2e
class CoolingOffPeriodE2ETest(endtoend.AcceleratedEnd2EndTest):
    @classmethod
    def setUpClass(cls):
        endtoend.testhandle.CONTRACTS = {
            "COOLING_OFF_PERIOD_SC": {
                "path": str(Path(SMART_CONTRACT)),
                "template_params": {},
            },
        }
        endtoend.testhandle.TSIDE_TO_INTERNAL_ACCOUNT_ID = accounts.internal_accounts_tside
        endtoend.testhandle.PARAMETER_RESOURCE_DIRS = [
            str(Path("src/feature_library/common/parameter_resource_defs")),
            str(Path("src/feature_library/deposit/temporal_features/parameter_resource_defs")),
        ]
        super().setUpClass()

    def test_cooling_off_period_withdrawal_logic(self):
        endtoend.standard_setup()
        endtoend.testhandle.use_kafka = True
        opening_date = datetime(2026, 1, 1, tzinfo=UTC)
        # cooling off period is 5 days -> ends 2026-01-06 00:00:00
        cooling_off_period_end = opening_date + relativedelta(days=5)

        customer_id = endtoend.core_api_helper.create_customer()
        customer_account = endtoend.contracts_helper.create_account_v2(
            product_id="COOLING_OFF_PERIOD_SC",
            account=CustomerAccountRequestBody(
                status=AccountV2Status.ACCOUNT_STATUS_OPEN,
                stakeholder_ids=[customer_id],
                activation_timestamp=opening_date,
            ),
            create_options=CreateOptions(
                parameter_values=parameters.parameter_values,
            ),
        )

        # 1. Full withdrawal within cooling off period (Day 1)
        # Deposit 100
        endtoend.postings_helper.inbound_hard_settlement(
            amount="100.00",
            denomination=DEFAULT_DENOMINATION,
            instruction_details={"description": "Initial deposit"},
            account_id=customer_account.id,
            internal_account_id=accounts.INTERNAL_ACCOUNT,
            value_datetime=opening_date + relativedelta(hours=1),
        )

        # Full withdrawal (should NOT send notification)
        full_withdrawal_id = endtoend.postings_helper.outbound_hard_settlement(
            amount="100.00",
            denomination=DEFAULT_DENOMINATION,
            instruction_details={"description": "Full withdrawal within cooling off period"},
            account_id=customer_account.id,
            internal_account_id=accounts.INTERNAL_ACCOUNT,
            value_datetime=opening_date + relativedelta(days=1),
        )
        pib = endtoend.postings_helper.get_posting_batch(full_withdrawal_id)
        self.assertEqual(pib["status"], "POSTING_INSTRUCTION_BATCH_STATUS_ACCEPTED")

        # 2. Partial withdrawal within cooling off period (Day 2)
        # Deposit 100 again
        endtoend.postings_helper.inbound_hard_settlement(
            amount="100.00",
            denomination=DEFAULT_DENOMINATION,
            instruction_details={"description": "Second deposit"},
            account_id=customer_account.id,
            internal_account_id=accounts.INTERNAL_ACCOUNT,
            value_datetime=opening_date + relativedelta(days=2),
        )

        # Partial withdrawal (should send notification)
        partial_withdrawal_id = endtoend.postings_helper.outbound_hard_settlement(
            amount="50.00",
            denomination=DEFAULT_DENOMINATION,
            instruction_details={"description": "Partial withdrawal within cooling off period"},
            account_id=customer_account.id,
            internal_account_id=accounts.INTERNAL_ACCOUNT,
            value_datetime=opening_date + relativedelta(days=2, hours=1),
        )
        pib = endtoend.postings_helper.get_posting_batch(partial_withdrawal_id)
        self.assertEqual(pib["status"], "POSTING_INSTRUCTION_BATCH_STATUS_ACCEPTED")

        endtoend.contracts_helper.wait_for_contract_notification(
            notification_type=smart_contract.WITHDRAWAL_SUBJECT_TO_FEES,
            notification_details={"account_id": customer_account.id},
            resource_id=customer_account.id,
            resource_type=endtoend.contracts_helper.ContractNotificationResourceType.RESOURCE_ACCOUNT,
        )

        # 3. Full withdrawal outside cooling off period (Day 7)
        # Remaining balance is 50. Withdraw 50.
        full_withdrawal_outside_id = endtoend.postings_helper.outbound_hard_settlement(
            amount="50.00",
            denomination=DEFAULT_DENOMINATION,
            instruction_details={"description": "Full withdrawal outside cooling off period"},
            account_id=customer_account.id,
            internal_account_id=accounts.INTERNAL_ACCOUNT,
            value_datetime=opening_date + relativedelta(days=7),
        )
        pib = endtoend.postings_helper.get_posting_batch(full_withdrawal_outside_id)
        self.assertEqual(pib["status"], "POSTING_INSTRUCTION_BATCH_STATUS_ACCEPTED")

        endtoend.contracts_helper.wait_for_contract_notification(
            notification_type=smart_contract.WITHDRAWAL_SUBJECT_TO_FEES,
            notification_details={"account_id": customer_account.id},
            resource_id=customer_account.id,
            resource_type=endtoend.contracts_helper.ContractNotificationResourceType.RESOURCE_ACCOUNT,
        )
