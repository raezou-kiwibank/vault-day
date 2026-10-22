# standard libs
import uuid
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
import requests
from dateutil.relativedelta import relativedelta

# features
import feature_library.deposit.temporal_features.grace_period as grace_period

# inception sdk
from inception_sdk.test_framework import endtoend
from inception_sdk.vault.core_api import (
    AccountV2Status,
    BatchCreateParameterValueV1RequestBody,
    CreateOptions,
    CreateParameterValueV1ParameterValue,
    CustomerAccountRequestBody,
    DecimalParameterValue,
)

# e2e
import tests.deposit.temporal_features.grace_period.e2e.accounts as accounts
import tests.deposit.temporal_features.grace_period.e2e.parameters as parameters

# tests
from tests.common.test_denomination import DEFAULT_DENOMINATION

UTC = ZoneInfo("UTC")
SMART_CONTRACT = "tests/deposit/temporal_features/grace_period/smart_contract.py"


@pytest.mark.e2e
class GracePeriodE2ETest(endtoend.AcceleratedEnd2EndTest):
    @classmethod
    def setUpClass(cls):
        endtoend.testhandle.CONTRACTS = {
            "GRACE_PERIOD_SC": {
                "path": str(Path(SMART_CONTRACT)),
                "template_params": {},
            },
        }
        endtoend.testhandle.TSIDE_TO_INTERNAL_ACCOUNT_ID = accounts.internal_accounts_tside
        endtoend.testhandle.PARAMETER_RESOURCE_DIRS = [
            str(Path("src/feature_library/common/parameter_resource_defs")),
            str(Path("src/feature_library/deposit/temporal_features/parameter_resource_defs")),
            str(Path("tests/deposit/temporal_features/grace_period/parameter_resource_defs")),
        ]
        super().setUpClass()

    def test_deposit_and_parameter_change_rejections(self):
        endtoend.standard_setup()
        endtoend.testhandle.use_kafka = False
        opening_date = datetime(2026, 1, 1, tzinfo=UTC)

        customer_id = endtoend.core_api_helper.create_customer()
        customer_account = endtoend.contracts_helper.create_account_v2(
            product_id="GRACE_PERIOD_SC",
            account=CustomerAccountRequestBody(
                status=AccountV2Status.ACCOUNT_STATUS_OPEN,
                stakeholder_ids=[customer_id],
                activation_timestamp=opening_date,
            ),
            create_options=CreateOptions(
                parameter_values=parameters.parameter_values,
            ),
        )

        # Deposit accepted within grace period (Day 1)
        allowed_posting_id = endtoend.postings_helper.inbound_hard_settlement(
            amount="100.00",
            denomination=DEFAULT_DENOMINATION,
            instruction_details={"description": "Deposit within grace period"},
            account_id=customer_account.id,
            internal_account_id=accounts.INTERNAL_ACCOUNT,
            value_datetime=opening_date + relativedelta(days=1),
        )
        allowed_pib = endtoend.postings_helper.get_posting_batch(allowed_posting_id)
        self.assertEqual(allowed_pib["status"], "POSTING_INSTRUCTION_BATCH_STATUS_ACCEPTED")

        # Withdraw within grace period to avoid teardown issues (Day 2)
        # Teardown fails if balance is non-zero after grace period because withdrawals are rejected
        endtoend.postings_helper.outbound_hard_settlement(
            amount="100.00",
            denomination=DEFAULT_DENOMINATION,
            instruction_details={"description": "Withdraw within grace period"},
            account_id=customer_account.id,
            internal_account_id=accounts.INTERNAL_ACCOUNT,
            value_datetime=opening_date + relativedelta(days=2),
        )

        # Deposit rejected after grace period (Day 7, grace period is 5 days)
        # End is 2026-01-06 00:00:00 (activation is midnight)
        rejected_posting_id = endtoend.postings_helper.inbound_hard_settlement(
            amount="100.00",
            denomination=DEFAULT_DENOMINATION,
            instruction_details={"description": "Deposit after grace period"},
            account_id=customer_account.id,
            internal_account_id=accounts.INTERNAL_ACCOUNT,
            value_datetime=opening_date + relativedelta(days=7),
        )
        rejected_pib = endtoend.postings_helper.get_posting_batch(rejected_posting_id)
        self.assertEqual(rejected_pib["status"], "POSTING_INSTRUCTION_BATCH_STATUS_REJECTED")
        self.assertIn(
            "No deposits are allowed after the grace period end",
            rejected_pib["posting_instructions"][0]["contract_violations"][0]["reason"],
        )

        # Parameter change rejected after grace period (using term parameter)
        with self.assertRaises(requests.exceptions.HTTPError) as e:
            endtoend.core_api_helper.batch_create_parameter_values(
                BatchCreateParameterValueV1RequestBody(
                    request_id=str(uuid.uuid4()),
                    parameter_values=[
                        CreateParameterValueV1ParameterValue(
                            parameter_id=endtoend.testhandle.parameter_resource_id_to_uploaded_id[
                                "term"
                            ],
                            account_id=customer_account.id,
                            value=DecimalParameterValue(decimal_value=Decimal("6")),
                        )
                    ],
                )
            )
        self.assertIn(
            "Term length cannot be changed outside the grace period", e.exception.response.text
        )

    @pytest.mark.accelerated_e2e
    def test_closure_notification_on_zero_balance(self):
        endtoend.standard_setup()
        endtoend.testhandle.use_kafka = True
        opening_date = datetime(2026, 1, 1, tzinfo=UTC)
        # 5 days grace period -> ends 2026-01-06 00:00:00
        grace_period_end = opening_date + relativedelta(days=5)

        customer_id = endtoend.core_api_helper.create_customer()
        customer_account = endtoend.contracts_helper.create_account_v2(
            product_id="GRACE_PERIOD_SC",
            account=CustomerAccountRequestBody(
                status=AccountV2Status.ACCOUNT_STATUS_OPEN,
                stakeholder_ids=[customer_id],
                activation_timestamp=opening_date,
            ),
            create_options=CreateOptions(
                parameter_values=parameters.parameter_values,
            ),
        )

        # No postings -> balance is zero at end of grace period
        # The schedule runs at grace_period_end
        job = endtoend.schedule_helper.trigger_next_schedule_job(
            resource_id=customer_account.id,
            resource_type=endtoend.schedule_helper.ResourceType.ACCOUNT,
            schedule_name=grace_period.GRACE_PERIOD_END_EVENT,
            effective_date=grace_period_end,
        )
        self.assertIsNotNone(job)
        endtoend.schedule_helper.wait_for_schedule_job(
            job=job,  # type: ignore
            job_statuses=["JOB_STATUS_SUCCEEDED"],
        )

        endtoend.contracts_helper.wait_for_contract_notification(
            notification_type=grace_period.notification_type(product_name="grace_period"),
            notification_details={
                "account_id": customer_account.id,
                "grace_period_end_datetime": str(grace_period_end),
                "reason": "Close account due to lack of funds at the end of grace period",
            },
            resource_id=customer_account.id,
            resource_type=endtoend.contracts_helper.ContractNotificationResourceType.RESOURCE_ACCOUNT,
        )
