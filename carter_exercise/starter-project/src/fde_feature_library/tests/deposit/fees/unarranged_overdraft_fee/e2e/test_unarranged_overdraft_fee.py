# Copyright @ 2026 Thought Machine Group Limited. All rights reserved.
# standard libs
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import cast
from uuid import uuid4
from zoneinfo import ZoneInfo

import pytest
from dateutil.relativedelta import relativedelta

# library
from feature_library.deposit.fees.unarranged_overdraft_fee import (
    ACCRUAL_EVENT,
    APPLICATION_EVENT,
    UNARRANGED_OVERDRAFT_FEE_PARAM,
)

# inception sdk
from inception_sdk.test_framework import endtoend
from inception_sdk.vault.core_api import (
    AccountV2Status,
    CreateOptions,
    CustomerAccountRequestBody,
    DecimalParameterValue,
)

from tests.common.test_denomination import DEFAULT_DENOMINATION
from tests.deposit.fees.unarranged_overdraft_fee.e2e import (
    accounts,
    dimensions,
    parameters,
)

UTC = ZoneInfo("UTC")
SMART_CONTRACT = str(
    Path("tests/deposit/fees/unarranged_overdraft_fee/simulation/smart_contract.py")
)

default_start_date = datetime(2026, 1, 30, tzinfo=UTC)


class UnarrangedOverdraftFeeTest(endtoend.End2Endtest):
    def setUp(self):
        endtoend.testhandle.CONTRACTS = {
            accounts.CUSTOMER_ACCOUNT: {
                "path": SMART_CONTRACT,
                "template_params": {},
            }
        }
        endtoend.testhandle.TSIDE_TO_INTERNAL_ACCOUNT_ID = accounts.internal_accounts_tside
        endtoend.testhandle.PARAMETER_RESOURCE_DIRS = [
            str(Path("src/feature_library/common/parameter_resource_defs")),
            str(Path("src/feature_library/deposit/fees/parameter_resource_defs")),
        ]
        super().setUp()

    @pytest.mark.e2e
    def test_fee_accrued_and_applied(self):
        endtoend.standard_setup()
        endtoend.testhandle.use_kafka = False
        opening_date = default_start_date + relativedelta(hours=1)
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

        withdrawal_amount = Decimal(150)
        client_batch_id = str(uuid4())
        out_pib_id = endtoend.postings_helper.outbound_hard_settlement(
            amount=withdrawal_amount,
            account_id=customer_account.id,
            value_datetime=opening_date + relativedelta(minutes=1),
            denomination=DEFAULT_DENOMINATION,
            instruction_details={"event": "WITHDRAWAL"},
            client_batch_id=client_batch_id,
        )
        out_pib = endtoend.postings_helper.get_posting_batch(pib_id=out_pib_id)
        self.assertEqual(out_pib["status"], "POSTING_INSTRUCTION_BATCH_STATUS_ACCEPTED")

        endtoend.balances_helper.wait_for_account_balances(
            account_id=customer_account.id,
            expected_balances=[
                (dimensions.DEFAULT, str(-withdrawal_amount)),
            ],
        )

        # Trigger 1 daily accrual
        job = endtoend.schedule_helper.trigger_next_schedule_job_and_wait(
            schedule_name=ACCRUAL_EVENT,
            account_id=customer_account.id,
            effective_date=opening_date + relativedelta(days=1, hour=0, minute=0, second=1),
        )
        self.assertIsNotNone(job)

        fee: Decimal = cast(
            DecimalParameterValue,
            parameters.default_parameter_values[UNARRANGED_OVERDRAFT_FEE_PARAM.id],
        ).decimal_value

        endtoend.balances_helper.wait_for_account_balances(
            account_id=customer_account.id,
            expected_balances=[
                (dimensions.OVERDRAFT_FEE, str(-fee)),
            ],
        )

        # Trigger application schedule
        job_app = endtoend.schedule_helper.trigger_next_schedule_job_and_wait(
            schedule_name=APPLICATION_EVENT,
            account_id=customer_account.id,
            effective_date=opening_date
            + relativedelta(months=1, day=1, hour=0, minute=0, second=1),
        )
        self.assertIsNotNone(job_app)

        endtoend.balances_helper.wait_for_account_balances(
            account_id=customer_account.id,
            expected_balances=[
                (dimensions.DEFAULT, str(-withdrawal_amount - (2 * fee))),
                (dimensions.OVERDRAFT_FEE, "0"),
            ],
        )
