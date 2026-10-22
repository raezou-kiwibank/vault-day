# standard libs
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
from dateutil.relativedelta import relativedelta

# features
import feature_library.lending.addresses as lending_addresses
import feature_library.lending.repayments.late_repayment as late_repayment

# inception sdk
from inception_sdk.test_framework import endtoend
from inception_sdk.vault.core_api import (
    AccountV2Status,
    CreateOptions,
    CustomerAccountRequestBody,
)

# e2e
import tests.lending.repayments.late_repayment.e2e.accounts as accounts
import tests.lending.repayments.late_repayment.e2e.parameters as parameters
from tests.common.test_denomination import DEFAULT_DENOMINATION

UTC = ZoneInfo("UTC")

VERTICAL_SC = "tests/lending/repayments/late_repayment/late_repayment_vertical_sc.py"
HORIZONTAL_SC = "tests/lending/repayments/late_repayment/late_repayment_horizontal_sc.py"


class LateRepaymentE2ETest(endtoend.AcceleratedEnd2EndTest):
    @classmethod
    def setUpClass(cls):
        endtoend.testhandle.CONTRACTS = {
            "VERTICAL_SC": {
                "path": str(Path(VERTICAL_SC)),
                "template_params": {},
            },
            "HORIZONTAL_SC": {
                "path": str(Path(HORIZONTAL_SC)),
                "template_params": {},
            },
        }
        endtoend.testhandle.TSIDE_TO_INTERNAL_ACCOUNT_ID = accounts.internal_accounts_tside
        endtoend.testhandle.PARAMETER_RESOURCE_DIRS = [
            str(Path("src/feature_library/common/parameter_resource_defs")),
            str(Path("src/feature_library/lending/repayments/parameter_resource_defs")),
        ]
        super().setUpClass()

    @endtoend.AcceleratedEnd2EndTest.Decorators.control_schedules(
        {
            "VERTICAL_SC": [
                late_repayment.CHECK_LATE_REPAYMENT_EVENT,
            ]
        }
    )
    @pytest.mark.accelerated_e2e
    def test_vertical_hierarchy_late_repayment_fee_applied(self):
        endtoend.standard_setup()
        endtoend.testhandle.use_kafka = False
        opening_date = datetime(2026, 1, 1, tzinfo=UTC)

        customer_id = endtoend.core_api_helper.create_customer()
        customer_account = endtoend.contracts_helper.create_account_v2(
            product_id="VERTICAL_SC",
            account=CustomerAccountRequestBody(
                status=AccountV2Status.ACCOUNT_STATUS_OPEN,
                stakeholder_ids=[customer_id],
                activation_timestamp=opening_date,
            ),
            create_options=CreateOptions(
                parameter_values=parameters.parameter_values,
            ),
        )
        self.assertEqual("ACCOUNT_STATUS_OPEN", customer_account.status)

        # Setup overdue balance
        endtoend.postings_helper.outbound_hard_settlement(
            amount="100",
            denomination=DEFAULT_DENOMINATION,
            instruction_details={"description": "Setup overdue balance"},
            account_id=customer_account.id,
            internal_account_id=accounts.DEPOSIT_ACCOUNT,
            target_account_address=lending_addresses.PRINCIPAL_OVERDUE,
            value_datetime=opening_date + relativedelta(hours=12),
        )

        # Trigger late repayment check
        job = endtoend.schedule_helper.trigger_next_schedule_job(
            resource_id=customer_account.id,
            resource_type=endtoend.schedule_helper.ResourceType.ACCOUNT,
            schedule_name=late_repayment.CHECK_LATE_REPAYMENT_EVENT,
            effective_date=datetime(2026, 1, 1, 23, 59, 59, tzinfo=UTC),
        )
        self.assertIsNotNone(job)
        endtoend.schedule_helper.wait_for_schedule_job(
            job=job,  # type: ignore
            initial_wait=40,
            job_statuses=["JOB_STATUS_SUCCEEDED"],
        )

        # Verify fee was charged (25.00)
        endtoend.balances_helper.wait_for_account_balances(
            account_id=customer_account.id,
            expected_balances=[
                (
                    endtoend.balances_helper.BalanceDimensions(
                        address=lending_addresses.PENALTIES,
                        denomination=DEFAULT_DENOMINATION,
                    ),
                    "25",
                )
            ],
        )

    @endtoend.AcceleratedEnd2EndTest.Decorators.control_schedules(
        {
            "HORIZONTAL_SC": [
                late_repayment.CHECK_LATE_REPAYMENT_EVENT,
            ]
        }
    )
    @pytest.mark.accelerated_e2e
    def test_horizontal_hierarchy_late_repayment_fee_applied(self):
        endtoend.standard_setup()
        endtoend.testhandle.use_kafka = False
        opening_date = datetime(2026, 1, 1, tzinfo=UTC)

        customer_id = endtoend.core_api_helper.create_customer()
        customer_account = endtoend.contracts_helper.create_account_v2(
            product_id="HORIZONTAL_SC",
            account=CustomerAccountRequestBody(
                status=AccountV2Status.ACCOUNT_STATUS_OPEN,
                stakeholder_ids=[customer_id],
                activation_timestamp=opening_date,
            ),
            create_options=CreateOptions(
                parameter_values=parameters.parameter_values,
            ),
        )
        self.assertEqual("ACCOUNT_STATUS_OPEN", customer_account.status)

        # Setup overdue balance on a backdated horizontal address
        principal_overdue_20251228 = f"{lending_addresses.PRINCIPAL_OVERDUE}_20251228"
        endtoend.postings_helper.outbound_hard_settlement(
            amount="100",
            denomination=DEFAULT_DENOMINATION,
            instruction_details={"description": "Setup overdue balance"},
            account_id=customer_account.id,
            internal_account_id=accounts.DEPOSIT_ACCOUNT,
            target_account_address=principal_overdue_20251228,
            value_datetime=opening_date + relativedelta(hours=12),
        )

        # Trigger late repayment check
        job = endtoend.schedule_helper.trigger_next_schedule_job(
            resource_id=customer_account.id,
            resource_type=endtoend.schedule_helper.ResourceType.ACCOUNT,
            schedule_name=late_repayment.CHECK_LATE_REPAYMENT_EVENT,
            effective_date=datetime(2026, 1, 1, 23, 59, 59, tzinfo=UTC),
        )
        self.assertIsNotNone(job)
        endtoend.schedule_helper.wait_for_schedule_job(
            job=job,  # type: ignore
            initial_wait=40,
            job_statuses=["JOB_STATUS_SUCCEEDED"],
        )

        # Verify fee was charged
        endtoend.balances_helper.wait_for_account_balances(
            account_id=customer_account.id,
            expected_balances=[
                (
                    endtoend.balances_helper.BalanceDimensions(
                        address=lending_addresses.PENALTIES,
                        denomination=DEFAULT_DENOMINATION,
                    ),
                    "25",
                )
            ],
        )

    @endtoend.AcceleratedEnd2EndTest.Decorators.control_schedules(
        {
            "VERTICAL_SC": [
                late_repayment.CHECK_LATE_REPAYMENT_EVENT,
            ]
        }
    )
    @pytest.mark.accelerated_e2e
    def test_late_repayment_fee_not_applied_when_no_overdue(self):
        endtoend.standard_setup()
        endtoend.testhandle.use_kafka = False
        opening_date = datetime(2026, 1, 1, tzinfo=UTC)

        customer_id = endtoend.core_api_helper.create_customer()
        customer_account = endtoend.contracts_helper.create_account_v2(
            product_id="VERTICAL_SC",
            account=CustomerAccountRequestBody(
                status=AccountV2Status.ACCOUNT_STATUS_OPEN,
                stakeholder_ids=[customer_id],
                activation_timestamp=opening_date,
            ),
            create_options=CreateOptions(
                parameter_values=parameters.parameter_values,
            ),
        )

        # Setup ONLY DUE balance (not overdue)
        endtoend.postings_helper.outbound_hard_settlement(
            amount="100",
            denomination=DEFAULT_DENOMINATION,
            instruction_details={"description": "Setup due balance"},
            account_id=customer_account.id,
            internal_account_id=accounts.DEPOSIT_ACCOUNT,
            target_account_address=lending_addresses.PRINCIPAL_DUE,
            value_datetime=opening_date + relativedelta(hours=12),
        )

        # Trigger late repayment check
        job = endtoend.schedule_helper.trigger_next_schedule_job(
            resource_id=customer_account.id,
            resource_type=endtoend.schedule_helper.ResourceType.ACCOUNT,
            schedule_name=late_repayment.CHECK_LATE_REPAYMENT_EVENT,
            effective_date=datetime(2026, 1, 1, 23, 59, 59, tzinfo=UTC),
        )
        self.assertIsNotNone(job)
        endtoend.schedule_helper.wait_for_schedule_job(
            job=job,  # type: ignore
            initial_wait=40,
            job_statuses=["JOB_STATUS_SUCCEEDED"],
        )

        # Verify NO fee was charged
        endtoend.balances_helper.wait_for_account_balances(
            account_id=customer_account.id,
            expected_balances=[
                (
                    endtoend.balances_helper.BalanceDimensions(
                        address=lending_addresses.PENALTIES,
                        denomination=DEFAULT_DENOMINATION,
                    ),
                    "0",
                )
            ],
        )
