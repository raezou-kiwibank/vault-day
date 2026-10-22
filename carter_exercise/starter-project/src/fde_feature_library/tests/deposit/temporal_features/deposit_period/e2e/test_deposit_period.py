# Copyright @ 2026 Thought Machine Group Limited. All rights reserved.
# standard libs
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

# library
import feature_library.deposit.temporal_features.deposit_period as deposit_period

# inception sdk
from inception_sdk.test_framework import endtoend
from inception_sdk.vault.core_api import (
    AccountV2Status,
    CreateOptions,
    CustomerAccountRequestBody,
)

from tests.deposit.temporal_features.deposit_period.e2e import accounts, parameters

UTC = ZoneInfo("UTC")

default_start_date = datetime(2026, 1, 1, tzinfo=UTC)


class DepositPeriodTest(endtoend.AcceleratedEnd2EndTest):
    @classmethod
    def setUpClass(cls):
        endtoend.testhandle.CONTRACTS = {
            accounts.DEPOSIT_PERIOD_CUSTOMER_ACCOUNT: {
                "path": str(
                    Path("tests/deposit/temporal_features/deposit_period/smart_contract.py")
                ),
                "template_params": {},
            },
        }
        endtoend.testhandle.TSIDE_TO_INTERNAL_ACCOUNT_ID = accounts.internal_accounts_tside
        endtoend.testhandle.PARAMETER_RESOURCE_DIRS = [
            str(Path("src/feature_library/deposit/temporal_features/parameter_resource_defs")),
            str(Path("src/feature_library/common/parameter_resource_defs")),
        ]
        super().setUpClass()

    @endtoend.AcceleratedEnd2EndTest.Decorators.control_schedules(
        {
            accounts.DEPOSIT_PERIOD_CUSTOMER_ACCOUNT: [
                deposit_period.DEPOSIT_PERIOD_END_EVENT,
            ]
        }
    )
    @pytest.mark.accelerated_e2e
    def test_deposit_period_end_schedule(self):
        endtoend.standard_setup()
        endtoend.testhandle.use_kafka = False
        opening_date = default_start_date
        customer_id = endtoend.core_api_helper.create_customer()
        customer_account = endtoend.contracts_helper.create_account_v2(
            product_id=accounts.DEPOSIT_PERIOD_CUSTOMER_ACCOUNT,
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

        # Deposit period is 7 days. End datetime is Jan 8th 00:00:00.
        # We trigger the job at that time.
        job = endtoend.schedule_helper.trigger_next_schedule_job(
            resource_id=customer_account.id,
            resource_type=endtoend.schedule_helper.ResourceType.ACCOUNT,
            schedule_name=deposit_period.DEPOSIT_PERIOD_END_EVENT,
            effective_date=datetime(
                year=2026, month=1, day=8, hour=0, minute=0, second=0, tzinfo=UTC
            ),
        )
        self.assertIsNotNone(job)
        endtoend.schedule_helper.wait_for_schedule_job(
            job=job,  # type: ignore
            initial_wait=40,
            job_statuses=["JOB_STATUS_SUCCEEDED"],
        )

    @pytest.mark.accelerated_e2e
    def test_rejection_after_deposit_period(self):
        endtoend.standard_setup()
        opening_date = default_start_date
        customer_id = endtoend.core_api_helper.create_customer()
        customer_account = endtoend.contracts_helper.create_account_v2(
            product_id=accounts.DEPOSIT_PERIOD_CUSTOMER_ACCOUNT,
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

        # Deposit within period (e.g. Day 2) should be accepted
        allowed_posting_id = endtoend.postings_helper.inbound_hard_settlement(
            amount="100",
            account_id=customer_account.id,
            value_datetime=datetime(2026, 1, 2, hour=12, tzinfo=UTC),
        )
        allowed_pib = endtoend.postings_helper.get_posting_batch(allowed_posting_id)
        self.assertEqual(allowed_pib["status"], "POSTING_INSTRUCTION_BATCH_STATUS_ACCEPTED")

        # Deposit after period (7 days) should be rejected
        # Activation is Jan 1st, so Jan 9th is definitely after.
        posting_id = endtoend.postings_helper.inbound_hard_settlement(
            amount="100",
            account_id=customer_account.id,
            value_datetime=datetime(2026, 1, 9, hour=12, tzinfo=UTC),
        )
        piv = endtoend.postings_helper.get_posting_batch(posting_id)
        self.assertEqual(piv["status"], "POSTING_INSTRUCTION_BATCH_STATUS_REJECTED")
        self.assertTrue(
            "No deposits are allowed after the deposit period end datetime."
            in piv["posting_instructions"][0]["contract_violations"][0]["reason"]
        )
