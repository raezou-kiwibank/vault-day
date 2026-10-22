# standard libs
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

# features
import feature_library.lending.addresses as lending_addresses

# inception sdk
from inception_sdk.test_framework import endtoend
from inception_sdk.vault.core_api import (
    AccountV2Status,
    CreateOptions,
    CustomerAccountRequestBody,
)

# e2e
import tests.lending.repayments.early_repayment.e2e.accounts as accounts
import tests.lending.repayments.early_repayment.e2e.parameters as parameters
from tests.common.test_denomination import DEFAULT_DENOMINATION

UTC = ZoneInfo("UTC")

VERTICAL_CONTRACT = "tests/lending/repayments/early_repayment/vertical_hierarchy_smart_contract.py"
HORIZONTAL_CONTRACT = (
    "tests/lending/repayments/early_repayment/horizontal_hierarchy_smart_contract.py"
)


class EarlyRepaymentE2ETest(endtoend.AcceleratedEnd2EndTest):
    @classmethod
    def setUpClass(cls):
        endtoend.testhandle.CONTRACTS = {
            "VERTICAL_SC": {
                "path": str(Path(VERTICAL_CONTRACT)),
                "template_params": {},
            },
            "HORIZONTAL_SC": {
                "path": str(Path(HORIZONTAL_CONTRACT)),
                "template_params": {},
            },
        }
        endtoend.testhandle.TSIDE_TO_INTERNAL_ACCOUNT_ID = accounts.internal_accounts_tside
        endtoend.testhandle.PARAMETER_RESOURCE_DIRS = [
            str(Path("src/feature_library/common/parameter_resource_defs")),
            str(Path("src/feature_library/lending/repayments/parameter_resource_defs")),
        ]
        super().setUpClass()

    @pytest.mark.accelerated_e2e
    def test_vertical_hierarchy_early_repayment(self):
        endtoend.standard_setup()
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
                parameter_values=parameters.vertical_hierarchy_parameter_values,
            ),
        )
        self.assertEqual("ACCOUNT_STATUS_OPEN", customer_account.status)

        # Disburse loan via manual posting
        endtoend.postings_helper.outbound_hard_settlement(
            amount="1000",
            denomination=DEFAULT_DENOMINATION,
            instruction_details={"description": "Disburse loan"},
            account_id=customer_account.id,
            internal_account_id=accounts.DEPOSIT_ACCOUNT,
            target_account_address=lending_addresses.PRINCIPAL,
        )

        endtoend.balances_helper.wait_for_account_balances(
            account_id=customer_account.id,
            expected_balances=[
                (
                    endtoend.balances_helper.BalanceDimensions(
                        address=lending_addresses.PRINCIPAL,
                        denomination=DEFAULT_DENOMINATION,
                    ),
                    "1000",
                )
            ],
        )

        # Full early repayment: 1000 principal + 10 flat fee = 1010
        endtoend.postings_helper.inbound_hard_settlement(
            amount="1010",
            denomination=DEFAULT_DENOMINATION,
            instruction_details={"description": "Full early repayment"},
            account_id=customer_account.id,
            internal_account_id=accounts.DEPOSIT_ACCOUNT,
        )

        # Verify fee was charged by checking customer account balance
        # -1010 repayment + 10 fee = -1000
        endtoend.balances_helper.wait_for_account_balances(
            account_id=customer_account.id,
            expected_balances=[
                (
                    endtoend.balances_helper.BalanceDimensions(
                        address="DEFAULT",
                        denomination=DEFAULT_DENOMINATION,
                    ),
                    "-1000",
                )
            ],
        )

    @pytest.mark.accelerated_e2e
    def test_horizontal_hierarchy_early_repayment(self):
        endtoend.standard_setup()
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
                parameter_values=parameters.horizontal_hierarchy_parameter_values,
            ),
        )
        self.assertEqual("ACCOUNT_STATUS_OPEN", customer_account.status)

        # Disburse loan
        endtoend.postings_helper.outbound_hard_settlement(
            amount="1000",
            denomination=DEFAULT_DENOMINATION,
            instruction_details={"description": "Disburse loan"},
            account_id=customer_account.id,
            internal_account_id=accounts.DEPOSIT_ACCOUNT,
            target_account_address=lending_addresses.PRINCIPAL,
        )

        # Full early repayment: 1000 principal + 5% fee (50) = 1050
        endtoend.postings_helper.inbound_hard_settlement(
            amount="1050",
            denomination=DEFAULT_DENOMINATION,
            instruction_details={"description": "Full early repayment"},
            account_id=customer_account.id,
            internal_account_id=accounts.DEPOSIT_ACCOUNT,
        )

        # Verify fee was charged by checking customer account balance
        # -1050 repayment + 50 fee = -1000
        endtoend.balances_helper.wait_for_account_balances(
            account_id=customer_account.id,
            expected_balances=[
                (
                    endtoend.balances_helper.BalanceDimensions(
                        address="DEFAULT",
                        denomination=DEFAULT_DENOMINATION,
                    ),
                    "-1000",
                )
            ],
        )
