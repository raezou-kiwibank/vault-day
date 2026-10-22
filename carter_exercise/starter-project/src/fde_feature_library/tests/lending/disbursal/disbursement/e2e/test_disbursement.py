# standard libs
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

import feature_library.lending.addresses as lending_addresses

# library
# inception sdk
from inception_sdk.test_framework import endtoend
from inception_sdk.vault.core_api import (
    AccountV2Status,
    CreateOptions,
    CustomerAccountRequestBody,
)

from tests.lending.disbursal.disbursement.e2e import accounts, parameters

UTC = ZoneInfo("UTC")


class DisbursementE2ETest(endtoend.AcceleratedEnd2EndTest):
    @classmethod
    def setUpClass(cls):
        endtoend.testhandle.CONTRACTS = {
            accounts.CUSTOMER_ACCOUNT: {
                "path": str(Path("tests/lending/disbursal/disbursement/smart_contract.py")),
                "template_params": {},
            },
        }
        endtoend.testhandle.TSIDE_TO_INTERNAL_ACCOUNT_ID = accounts.internal_accounts_tside
        endtoend.testhandle.PARAMETER_RESOURCE_DIRS = [
            str(Path("src/feature_library/lending/disbursal/parameter_resource_defs")),
            str(Path("src/feature_library/lending/principal/parameter_resource_defs")),
            str(Path("src/feature_library/common/parameter_resource_defs")),
        ]
        super().setUpClass()

    @pytest.mark.accelerated_e2e
    def test_disbursement_on_activation(self):
        endtoend.standard_setup()
        endtoend.testhandle.use_kafka = False
        opening_date = datetime(2026, 1, 1, tzinfo=UTC)

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

        # verify postings occurred on activation
        # Customer account: PRINCIPAL address should be 1000
        endtoend.balances_helper.wait_for_account_balances(
            account_id=customer_account.id,
            expected_balances=[
                (
                    endtoend.balances_helper.BalanceDimensions(
                        address=lending_addresses.PRINCIPAL,
                        denomination=parameters.DEFAULT_DENOMINATION,
                    ),
                    "1000",
                )
            ],
        )
