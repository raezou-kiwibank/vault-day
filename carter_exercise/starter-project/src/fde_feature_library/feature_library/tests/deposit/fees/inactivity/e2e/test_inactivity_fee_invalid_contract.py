# Copyright @ 2026 Thought Machine Group Limited. All rights reserved.
# standard libs
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

# library
import feature_library.deposit.fees.inactivity_fee as inactivity_fee

# inception sdk
from inception_sdk.test_framework import endtoend
from inception_sdk.vault.core_api import (
    AccountV2Status,
    CreateOptions,
    CustomerAccountRequestBody,
)

from tests.deposit.fees.inactivity.e2e import accounts, parameters

UTC = ZoneInfo("UTC")

default_start_date = datetime(2026, 1, 1, tzinfo=UTC)


class InactivityFeeScheduleTest(endtoend.AcceleratedEnd2EndTest):
    def setUp(self):
        endtoend.testhandle.CONTRACTS = {
            accounts.CUSTOMER_ACCOUNT: {
                "path": str(Path("tests/deposit/fees/inactivity/invalid_smart_contract.py")),
                "template_params": {},
            }
        }
        endtoend.testhandle.TSIDE_TO_INTERNAL_ACCOUNT_ID = accounts.internal_accounts_tside
        endtoend.testhandle.PARAMETER_RESOURCE_DIRS = [
            str(Path("src/feature_library/common/parameter_resource_defs")),
            str(Path("src/feature_library/deposit/fees/parameter_resource_defs")),
        ]
        super().setUp()

    @endtoend.AcceleratedEnd2EndTest.Decorators.control_schedules(
        {
            accounts.CUSTOMER_ACCOUNT: [
                inactivity_fee.APPLICATION_EVENT,
            ]
        }
    )
    @pytest.mark.accelerated_e2e
    def test_schedule_failure(self):
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
        job = endtoend.schedule_helper.trigger_next_schedule_job(
            resource_id=customer_account.id,
            resource_type=endtoend.schedule_helper.ResourceType.ACCOUNT,
            schedule_name=inactivity_fee.APPLICATION_EVENT,
            effective_date=datetime(
                year=2026, month=1, day=1, hour=23, minute=59, second=59, tzinfo=UTC
            ),
        )
        self.assertIsNotNone(job)
        endtoend.schedule_helper.wait_for_schedule_job(
            job=job,  # type: ignore
            initial_wait=40,
            job_statuses=["JOB_STATUS_FAILED"],
        )
        jobs = endtoend.core_api_helper.get_jobs(job.schedule_id)  # ty: ignore[possibly-missing-attribute]
        self.assertEqual(len(jobs), 1)
        failed_job = next(iter(jobs))
        self.assertTrue(
            "Rejection(message='The following parameters are missing: missing_denomination',"
            " reason_code=RejectionReason.AGAINST_TNC)" in failed_job["metadata"]["error_trace"]
        )
