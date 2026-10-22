# Copyright @ 2026 Thought Machine Group Limited. All rights reserved.
# standard libs
from datetime import datetime
from pathlib import Path
from uuid import uuid4
from zoneinfo import ZoneInfo

import pytest
from dateutil.relativedelta import relativedelta

# library
import feature_library.lending.interest.interest_application as interest_application

# inception sdk
from inception_sdk.test_framework import endtoend
from inception_sdk.test_framework.common.balance_helpers import BalanceDimensions
from inception_sdk.vault.core_api import (
    AccountV2Status,
    CreateOptions,
    CustomerAccountRequestBody,
)

import tests.lending.interest.interest_application.smart_contract as smart_contract
from tests.lending.interest.interest_application.e2e import accounts, parameters

UTC = ZoneInfo("UTC")

default_start_date = datetime(2026, 1, 1, tzinfo=UTC)


class InterestApplicationTest(endtoend.AcceleratedEnd2EndTest):
    @classmethod
    def setUpClass(cls):
        endtoend.testhandle.CONTRACTS = {
            accounts.INTEREST_APPLICATION_CUSTOMER_ACCOUNT: {
                "path": str(Path("tests/lending/interest/interest_application/smart_contract.py")),
                "template_params": {},
            },
        }
        endtoend.testhandle.TSIDE_TO_INTERNAL_ACCOUNT_ID = accounts.internal_accounts_tside
        endtoend.testhandle.PARAMETER_RESOURCE_DIRS = [
            str(Path("src/feature_library/lending/interest/parameter_resource_defs")),
            str(Path("src/feature_library/lending/interest/secondary/parameter_resource_defs")),
            str(Path("src/feature_library/common/parameter_resource_defs")),
        ]
        super().setUpClass()

    @endtoend.AcceleratedEnd2EndTest.Decorators.control_schedules(
        {
            accounts.INTEREST_APPLICATION_CUSTOMER_ACCOUNT: [
                smart_contract.APPLICATION_EVENT,
            ]
        }
    )
    @pytest.mark.accelerated_e2e
    def test_application_schedule_success(self):
        endtoend.standard_setup()
        endtoend.testhandle.use_kafka = False
        opening_date = default_start_date
        customer_id = endtoend.core_api_helper.create_customer()
        customer_account = endtoend.contracts_helper.create_account_v2(
            product_id=accounts.INTEREST_APPLICATION_CUSTOMER_ACCOUNT,
            account=CustomerAccountRequestBody(
                status=AccountV2Status.ACCOUNT_STATUS_OPEN,
                id=str(uuid4()),
                stakeholder_ids=[customer_id],
                activation_timestamp=opening_date,
            ),
            create_options=CreateOptions(
                parameter_values=parameters.default_parameter_values,
            ),
        )
        self.assertEqual("ACCOUNT_STATUS_OPEN", customer_account.status)

        # Fake accrual: 10.12345
        pib_id = endtoend.postings_helper.outbound_hard_settlement(
            amount="10.12345",
            denomination=parameters.DEFAULT_DENOMINATION,
            account_id=customer_account.id,
            internal_account_id=accounts.INTERNAL_ACCOUNT,
            target_account_address=interest_application.lending_addresses.ACCRUED_INTEREST_RECEIVABLE,  # noqa: E501
            value_datetime=opening_date + relativedelta(minutes=1),
        )
        pib = endtoend.postings_helper.get_posting_batch(pib_id=pib_id)
        self.assertEqual(pib["status"], "POSTING_INSTRUCTION_BATCH_STATUS_ACCEPTED")

        endtoend.balances_helper.wait_for_account_balances(
            account_id=customer_account.id,
            expected_balances=[
                (
                    BalanceDimensions(
                        address=interest_application.lending_addresses.ACCRUED_INTEREST_RECEIVABLE,
                        denomination=parameters.DEFAULT_DENOMINATION,
                    ),
                    "10.12345",
                )
            ],
        )

        # Trigger application event on Jan 28th
        job = endtoend.schedule_helper.trigger_next_schedule_job(
            resource_id=customer_account.id,
            resource_type=endtoend.schedule_helper.ResourceType.ACCOUNT,
            schedule_name=smart_contract.APPLICATION_EVENT,
            effective_date=datetime(
                year=2026, month=1, day=28, hour=0, minute=0, second=0, tzinfo=UTC
            ),
        )
        self.assertIsNotNone(job)
        endtoend.schedule_helper.wait_for_schedule_job(
            job=job,  # type: ignore
            initial_wait=40,
            job_statuses=["JOB_STATUS_SUCCEEDED"],
        )

        # After application:
        # ACCRUED_INTEREST_RECEIVABLE should be 0
        # INTEREST_DUE should be 10.12 (rounded)
        endtoend.balances_helper.wait_for_account_balances(
            account_id=customer_account.id,
            expected_balances=[
                (
                    BalanceDimensions(
                        address=interest_application.lending_addresses.ACCRUED_INTEREST_RECEIVABLE,
                        denomination=parameters.DEFAULT_DENOMINATION,
                    ),
                    "0",
                ),
                (
                    BalanceDimensions(
                        address=interest_application.lending_addresses.INTEREST_DUE,
                        denomination=parameters.DEFAULT_DENOMINATION,
                    ),
                    "10.12",
                ),
            ],
        )
