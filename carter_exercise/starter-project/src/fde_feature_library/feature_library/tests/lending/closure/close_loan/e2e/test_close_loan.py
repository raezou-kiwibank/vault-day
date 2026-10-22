# standard libs
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
from dateutil.relativedelta import relativedelta

# features
import feature_library.lending.addresses as lending_addresses
import feature_library.lending.closure.close_loan as close_loan

# inception sdk
from inception_sdk.test_framework import endtoend
from inception_sdk.vault.core_api import (
    AccountV2Status,
    CreateOptions,
    CustomerAccountRequestBody,
)

# e2e
import tests.lending.closure.close_loan.e2e.accounts as accounts
import tests.lending.closure.close_loan.e2e.parameters as parameters
from tests.common.test_denomination import DEFAULT_DENOMINATION

UTC = ZoneInfo("UTC")

VERTICAL_SC = "tests/lending/closure/close_loan/close_loan_vertical_sc.py"
HORIZONTAL_SC = "tests/lending/closure/close_loan/close_loan_horizontal_sc.py"


@pytest.mark.e2e
class CloseLoanE2ETest(endtoend.AcceleratedEnd2EndTest):
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
        ]
        super().setUpClass()

    def test_vertical_hierarchy_closure_rejected_then_permitted(self):
        endtoend.standard_setup()
        endtoend.testhandle.use_kafka = True
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

        # Setup debt balance
        endtoend.postings_helper.outbound_hard_settlement(
            amount="100.00",
            denomination=DEFAULT_DENOMINATION,
            instruction_details={"description": "Setup debt balance"},
            account_id=customer_account.id,
            internal_account_id=accounts.INTERNAL_ACCOUNT,
            target_account_address=lending_addresses.PRINCIPAL,
            value_datetime=opening_date + relativedelta(hours=1),
        )

        # Attempt to close account - should fail
        with self.assertRaises(Exception) as e:
            endtoend.core_api_helper.update_account_v2(
                account_id=customer_account.id,
                status=AccountV2Status.ACCOUNT_STATUS_CLOSED,
            )
        self.assertIn(
            "The loan cannot be closed until all outstanding debt is repaid",
            e.exception.response.text,
        )

        # Repay loan
        endtoend.postings_helper.inbound_hard_settlement(
            amount="100.00",
            denomination=DEFAULT_DENOMINATION,
            instruction_details={"description": "Repay loan"},
            account_id=customer_account.id,
            internal_account_id=accounts.INTERNAL_ACCOUNT,
            target_account_address=lending_addresses.PRINCIPAL,
            value_datetime=opening_date + relativedelta(hours=2),
        )

        # Verify notification was sent
        endtoend.contracts_helper.wait_for_contract_notification(
            notification_type=close_loan.notification_type(product_name="CLOSE_LOAN_VERTICAL"),
            notification_details={"account_id": customer_account.id},
            resource_id=customer_account.id,
            resource_type=endtoend.contracts_helper.ContractNotificationResourceType.RESOURCE_ACCOUNT,
        )

        # Attempt to close account - should succeed
        endtoend.core_api_helper.update_account_v2(
            account_id=customer_account.id,
            status=AccountV2Status.ACCOUNT_STATUS_CLOSED,
        )

        # Verify status is closed
        closed_account = endtoend.contracts_helper.get_account_v2(customer_account.id)
        self.assertEqual("ACCOUNT_STATUS_CLOSED", closed_account["status"])

    def test_horizontal_hierarchy_closure_rejected_then_permitted(self):
        endtoend.standard_setup()
        endtoend.testhandle.use_kafka = True
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

        # Setup debt balance
        endtoend.postings_helper.outbound_hard_settlement(
            amount="100.00",
            denomination=DEFAULT_DENOMINATION,
            instruction_details={"description": "Setup debt balance"},
            account_id=customer_account.id,
            internal_account_id=accounts.INTERNAL_ACCOUNT,
            target_account_address=lending_addresses.PRINCIPAL,
            value_datetime=opening_date + relativedelta(hours=1),
        )

        # Attempt to close account - should fail
        with self.assertRaises(Exception) as e:
            endtoend.core_api_helper.update_account_v2(
                account_id=customer_account.id,
                status=AccountV2Status.ACCOUNT_STATUS_CLOSED,
            )
        self.assertIn(
            "The loan cannot be closed until all outstanding debt is repaid",
            e.exception.response.text,
        )

        # Repay loan
        endtoend.postings_helper.inbound_hard_settlement(
            amount="100.00",
            denomination=DEFAULT_DENOMINATION,
            instruction_details={"description": "Repay loan"},
            account_id=customer_account.id,
            internal_account_id=accounts.INTERNAL_ACCOUNT,
            target_account_address=lending_addresses.PRINCIPAL,
            value_datetime=opening_date + relativedelta(hours=2),
        )

        # Verify notification was sent
        endtoend.contracts_helper.wait_for_contract_notification(
            notification_type=close_loan.notification_type(product_name="CLOSE_LOAN_HORIZONTAL"),
            notification_details={"account_id": customer_account.id},
            resource_id=customer_account.id,
            resource_type=endtoend.contracts_helper.ContractNotificationResourceType.RESOURCE_ACCOUNT,
        )

        # Attempt to close account - should succeed
        endtoend.core_api_helper.update_account_v2(
            account_id=customer_account.id,
            status=AccountV2Status.ACCOUNT_STATUS_CLOSED,
        )

        # Verify status is closed
        closed_account = endtoend.contracts_helper.get_account_v2(customer_account.id)
        self.assertEqual("ACCOUNT_STATUS_CLOSED", closed_account["status"])
