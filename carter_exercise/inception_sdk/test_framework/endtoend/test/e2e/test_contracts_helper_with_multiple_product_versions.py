# standard libs
import uuid
from decimal import Decimal

# inception sdk
import inception_sdk.test_framework.endtoend as endtoend
import inception_sdk.vault.core_api as core_api
from inception_sdk.test_framework.endtoend.helper import TestProduct, TestProductVersion
from inception_sdk.vault.core_api import AccountV2Status, AccountV2TSide, CustomerAccountRequestBody

# GIVEN: A products defined with .PRODUCTS schema
# This triggers standard_setup_with_multiple_product_versions in setUpClass
PATH_DIR = "inception_sdk/test_framework/endtoend/test/e2e/input/template"
PRODUCT_VERSION_ID = "product_version_id_1"
endtoend.testhandle.PRODUCTS = [
    TestProduct(
        product_id="product_id_1",
        product_versions=[
            TestProductVersion(
                product_version_id=PRODUCT_VERSION_ID,
                path=PATH_DIR + "/contract_template.py",
                supported_denominations=["XYZ"],
                adjustments_versioning_policy=core_api.AdjustmentsVersioningPolicy.LATEST,
            ),
        ],
    ),
]


class TestCreateAccountsV2WithProductVersionID(endtoend.End2Endtest):
    """Tests creating a customer account with new handler using product_version_id and an
    internal account via the /v2/accounts endpoint, and proves it by sending a posting between
    an internal account and a customer account.
    """

    def test_create_accounts_v2(self):
        # GIVEN product version pv1
        internal_account_id = str(uuid.uuid4())[:-6]
        t_side = AccountV2TSide.T_SIDE_ASSET

        endtoend.testhandle.TSIDE_TO_INTERNAL_ACCOUNT_ID |= {t_side: [internal_account_id]}
        # GIVEN internal account ia1
        endtoend.contracts_helper.create_required_internal_accounts(
            endtoend.testhandle.TSIDE_TO_INTERNAL_ACCOUNT_ID
        )

        self.assertIn(internal_account_id, endtoend.testhandle.internal_account_id_to_uploaded_id)
        # GIVEN customer c1
        customer = endtoend.core_api_helper.create_customer()

        # WHEN creating a customer account through handler with product version pv1
        customer_account_v2 = endtoend.contracts_helper.create_account_v2(
            product_version_id=PRODUCT_VERSION_ID,
            account=CustomerAccountRequestBody(
                id=str(uuid.uuid4()),
                status=AccountV2Status.ACCOUNT_STATUS_OPEN,
                stakeholder_ids=[customer],
            ),
        )
        # WHEN when sending a posting instruction
        pib_id = endtoend.postings_helper.inbound_hard_settlement(
            amount=Decimal(1),
            account_id=customer_account_v2.id,
            internal_account_id=internal_account_id,
        )

        # THEN posting status accepted
        pib = endtoend.postings_helper.get_posting_batch(pib_id=pib_id)
        self.assertEqual(pib["status"], "POSTING_INSTRUCTION_BATCH_STATUS_ACCEPTED")
