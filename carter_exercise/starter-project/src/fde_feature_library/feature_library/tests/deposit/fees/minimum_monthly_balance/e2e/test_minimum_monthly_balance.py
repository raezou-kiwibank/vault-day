# standard libs
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
from dateutil.relativedelta import relativedelta

import feature_library.deposit.fees.minimum_monthly_balance as minimum_monthly_balance

# inception sdk
from inception_sdk.test_framework import endtoend
from inception_sdk.vault.core_api import (
    AccountV2Status,
    CreateOptions,
    CustomerAccountRequestBody,
)

from tests.common.test_denomination import DEFAULT_DENOMINATION

# library
from tests.deposit.fees.minimum_monthly_balance.e2e import accounts, dimensions, parameters

UTC = ZoneInfo("UTC")

default_start_date = datetime(2026, 1, 1, 12, tzinfo=UTC)


class MinimumMonthlyBalanceScheduleTest(endtoend.AcceleratedEnd2EndTest):
    def setUp(self):
        endtoend.testhandle.CONTRACTS = {
            accounts.CUSTOMER_ACCOUNT: {
                "path": str(
                    Path("tests/deposit/fees/minimum_monthly_balance/simulation/smart_contract.py")
                ),
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
                minimum_monthly_balance.APPLY_MINIMUM_MONTHLY_BALANCE_EVENT,
            ]
        }
    )
    @pytest.mark.accelerated_e2e
    def test_fee_applied_below_threshold(self):
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

        deposit_amount = Decimal(10)
        pib_id = endtoend.postings_helper.inbound_hard_settlement(
            amount=deposit_amount,
            account_id=customer_account.id,
            value_datetime=opening_date + relativedelta(days=1),
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

        schedule_date = opening_date + relativedelta(
            months=1, day=1, hour=0, minute=0, second=0, microsecond=0
        )
        job = endtoend.schedule_helper.trigger_next_schedule_job_and_wait(
            schedule_name=minimum_monthly_balance.APPLY_MINIMUM_MONTHLY_BALANCE_EVENT,
            account_id=customer_account.id,
            effective_date=schedule_date,
        )
        self.assertIsNotNone(job)
        endtoend.balances_helper.wait_for_account_balances(
            account_id=customer_account.id,
            expected_balances=[
                (dimensions.DEFAULT, str(Decimal(5))),
            ],
        )

    @endtoend.AcceleratedEnd2EndTest.Decorators.control_schedules(
        {
            accounts.CUSTOMER_ACCOUNT: [
                minimum_monthly_balance.APPLY_MINIMUM_MONTHLY_BALANCE_EVENT,
            ]
        }
    )
    @pytest.mark.accelerated_e2e
    def test_fee_not_applied_above_threshold(self):
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

        deposit_amount = Decimal(100)
        pib_id = endtoend.postings_helper.inbound_hard_settlement(
            amount=deposit_amount,
            account_id=customer_account.id,
            value_datetime=opening_date + relativedelta(days=1),
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

        schedule_date = opening_date + relativedelta(
            months=1, day=1, hour=0, minute=0, second=0, microsecond=0
        )
        job = endtoend.schedule_helper.trigger_next_schedule_job_and_wait(
            schedule_name=minimum_monthly_balance.APPLY_MINIMUM_MONTHLY_BALANCE_EVENT,
            account_id=customer_account.id,
            effective_date=schedule_date,
        )
        self.assertIsNotNone(job)

        endtoend.balances_helper.wait_for_account_balances(
            account_id=customer_account.id,
            expected_balances=[
                (dimensions.DEFAULT, str(deposit_amount)),
            ],
        )
