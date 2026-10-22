# Copyright @ 2026 Thought Machine Group Limited. All rights reserved.
# standard libs
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

# library
import feature_library.deposit.interest.interest_application as interest_application

# inception sdk
from inception_sdk.test_framework import endtoend
from inception_sdk.vault.core_api import (
    AccountV2Status,
    CreateOptions,
    CustomerAccountRequestBody,
)

from tests.deposit.interest.interest_application.e2e import accounts, parameters

UTC = ZoneInfo("UTC")

default_start_date = datetime(2026, 1, 1, tzinfo=UTC)


class InterestApplicationScheduleTest(endtoend.AcceleratedEnd2EndTest):
    @classmethod
    def setUpClass(cls):
        endtoend.testhandle.CONTRACTS = {
            accounts.APPLICATION_CUSTOMER_ACCOUNT: {
                "path": str(Path("tests/deposit/interest/interest_application/smart_contract.py")),
                "template_params": {},
            },
            accounts.INVALID_APPLICATION_CUSTOMER_ACCOUNT: {
                "path": str(
                    Path("tests/deposit/interest/interest_application/invalid_smart_contract.py")
                ),
                "template_params": {},
            },
        }
        endtoend.testhandle.TSIDE_TO_INTERNAL_ACCOUNT_ID = accounts.internal_accounts_tside
        endtoend.testhandle.PARAMETER_RESOURCE_DIRS = [
            str(Path("src/feature_library/deposit/interest/parameter_resource_defs")),
            str(Path("src/feature_library/common/parameter_resource_defs")),
        ]
        super().setUpClass()

    @endtoend.AcceleratedEnd2EndTest.Decorators.control_schedules(
        {
            accounts.APPLICATION_CUSTOMER_ACCOUNT: [
                interest_application.APPLICATION_EVENT,
            ]
        }
    )
    @pytest.mark.accelerated_e2e
    def test_schedule_success(self):
        endtoend.standard_setup()
        endtoend.testhandle.use_kafka = False
        opening_date = default_start_date
        customer_id = endtoend.core_api_helper.create_customer()
        customer_account = endtoend.contracts_helper.create_account_v2(
            product_id=accounts.APPLICATION_CUSTOMER_ACCOUNT,
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
            schedule_name=interest_application.APPLICATION_EVENT,
            effective_date=datetime(
                year=2026, month=2, day=1, hour=0, minute=0, second=1, tzinfo=UTC
            ),
        )
        self.assertIsNotNone(job)
        endtoend.schedule_helper.wait_for_schedule_job(
            job=job,  # type: ignore
            initial_wait=40,
            job_statuses=["JOB_STATUS_SUCCEEDED"],
        )

    @endtoend.AcceleratedEnd2EndTest.Decorators.control_schedules(
        {
            accounts.INVALID_APPLICATION_CUSTOMER_ACCOUNT: [
                interest_application.APPLICATION_EVENT,
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
            product_id=accounts.INVALID_APPLICATION_CUSTOMER_ACCOUNT,
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
            schedule_name=interest_application.APPLICATION_EVENT,
            effective_date=datetime(
                year=2026, month=2, day=1, hour=0, minute=0, second=1, tzinfo=UTC
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
