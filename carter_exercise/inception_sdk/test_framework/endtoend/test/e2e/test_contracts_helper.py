# standard libs
import logging
import os
import uuid
from decimal import Decimal
from unittest.mock import ANY
from zoneinfo import ZoneInfo

# third party
from semantic_version import Version

# inception sdk
import inception_sdk.test_framework.endtoend as endtoend
import inception_sdk.vault.core_api as core_api
from inception_sdk.test_framework.endtoend import (
    skipForMissingExtension,
    skipForVaultVersion,
    skipForVaultVersionLessThan,
)
from inception_sdk.test_framework.endtoend.contracts_helper import DUMMY_CONTRA
from inception_sdk.vault.core_api import (
    AccountV2Status,
    CreateOptions,
    CreateSubAccountRequest,
    CustomerAccountRequestBody,
    SubAccountCreateSubAccount,
    SubAccountStatus,
)

UTC = ZoneInfo("UTC")
log = logging.getLogger(__name__)
logging.basicConfig(
    level=os.environ.get("LOGLEVEL", "INFO"),
    format="%(asctime)s.%(msecs)03d - %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
TEST_CONTRACT = "test_contract"
TEST_SUB_ACC_CONTRACT = "test_sub_acc_contract"
EXPECTED_PARAMETERS_CONTRACT = "expected_parameters_contract"
endtoend.testhandle.CONTRACTS = {
    TEST_CONTRACT: {
        "path": "inception_sdk/test_framework/endtoend/test/e2e/input/template/"
        "contract_template.py",
        "template_params": {},
    },
}
endtoend.testhandle.PARAMETER_RESOURCE_DIRS = [
    "inception_sdk/test_framework/common/test/input/parameters"
]


class TestCreateAccountsV2(endtoend.End2Endtest):
    """Tests creating a customer account and an internal account via the /v2/accounts endpoint, and
    proves it by sending a posting between an internal account and a customer account.
    """

    def test_create_accounts_v2(self):
        endtoend.standard_setup()
        customer = endtoend.core_api_helper.create_customer()

        # Test v2 accounts.
        customer_account_v2 = endtoend.contracts_helper.create_account_v2(
            product_id=TEST_CONTRACT,
            account=CustomerAccountRequestBody(
                id=str(uuid.uuid4()),
                status=AccountV2Status.ACCOUNT_STATUS_OPEN,
                stakeholder_ids=[customer],
            ),
        )
        pib_id = endtoend.postings_helper.inbound_hard_settlement(
            amount=Decimal(1),
            account_id=customer_account_v2.id,
            internal_account_id=DUMMY_CONTRA,
        )
        pib = endtoend.postings_helper.get_posting_batch(pib_id=pib_id)
        self.assertEqual(pib["status"], "POSTING_INSTRUCTION_BATCH_STATUS_ACCEPTED")

    @skipForVaultVersionLessThan(Version("5.11.0"))
    @skipForMissingExtension(required_extensions=[core_api.VaultCoreExtension.SUB_ACCOUNTS])
    def test_create_accounts_v2_with_sub_accounts(self):
        endtoend.testhandle.CONTRACTS[TEST_SUB_ACC_CONTRACT] = {
            "path": "inception_sdk/test_framework/endtoend/test/e2e/input/template/"
            "sub_account_template.py",
            "template_params": {},
        }

        endtoend.standard_setup()
        customer = endtoend.core_api_helper.create_customer()

        sub_account_id_1 = str(uuid.uuid4())
        sub_account_id_2 = str(uuid.uuid4())
        sub_account_name_1 = "TestCreateAccountsV2:test_create_accounts_v2_with_sub_accounts_1"
        sub_account_name_2 = "TestCreateAccountsV2:test_create_accounts_v2_with_sub_accounts_2"
        sub_account_type = "SPEND"
        sub_accounts_to_create: list[CreateSubAccountRequest] = [
            CreateSubAccountRequest(
                sub_account=SubAccountCreateSubAccount(
                    id=sub_account_id_1,
                    type=sub_account_type,
                    name=sub_account_name_1,
                    status=SubAccountStatus.SUB_ACCOUNT_STATUS_OPEN,
                )
            ),
            CreateSubAccountRequest(
                sub_account=SubAccountCreateSubAccount(
                    id=sub_account_id_2,
                    type=sub_account_type,
                    name=sub_account_name_2,
                    status=SubAccountStatus.SUB_ACCOUNT_STATUS_OPEN,
                )
            ),
        ]

        # Open V2 Account with Sub-Account create options.
        customer_account_v2 = endtoend.contracts_helper.create_account_v2(
            product_id=TEST_SUB_ACC_CONTRACT,
            account=CustomerAccountRequestBody(
                id=str(uuid.uuid4()),
                status=AccountV2Status.ACCOUNT_STATUS_OPEN,
                stakeholder_ids=[customer],
            ),
            create_options=CreateOptions(
                sub_accounts=sub_accounts_to_create,
            ),
        )

        # List Sub-Accounts to ensure they're open.
        list_sub_accounts_response = endtoend.core_api_helper.list_sub_accounts(
            request=core_api.ListSubAccountsRequest(
                account_id=customer_account_v2.id,
                type=sub_account_type,
                page_size=10,
            ),
        )
        # Order on name to ensure consistency.
        list_sub_accounts_response.sub_accounts.sort(key=lambda sub_account: sub_account.name)

        self.assertEqual(
            list_sub_accounts_response,
            core_api.ListSubAccountsResponse.model_construct(
                previous_page_token="",
                next_page_token="",
                sub_accounts=[
                    core_api.SubAccount.model_construct(
                        id=sub_account_id_1,
                        type=sub_account_type,
                        name=sub_account_name_1,
                        details={},
                        activation_timestamp=ANY,
                        create_timestamp=ANY,
                        update_timestamp=ANY,
                        status=core_api.SubAccountStatus.SUB_ACCOUNT_STATUS_OPEN,
                        account_id=customer_account_v2.id,
                    ),
                    core_api.SubAccount.model_construct(
                        id=sub_account_id_2,
                        type=sub_account_type,
                        name=sub_account_name_2,
                        details={},
                        activation_timestamp=ANY,
                        create_timestamp=ANY,
                        update_timestamp=ANY,
                        status=core_api.SubAccountStatus.SUB_ACCOUNT_STATUS_OPEN,
                        account_id=customer_account_v2.id,
                    ),
                ],
            ),
        )

        # Close the Account.
        endtoend.core_api_helper.update_account_v2(
            account_id=customer_account_v2.id, status=AccountV2Status.ACCOUNT_STATUS_CLOSED
        )

        # List the Sub-Accounts again to ensure they're all closed.
        list_sub_accounts_response = endtoend.core_api_helper.list_sub_accounts(
            request=core_api.ListSubAccountsRequest(
                account_id=customer_account_v2.id,
                type=sub_account_type,
                page_size=10,
            ),
        )
        # Order on name to ensure consistency.
        list_sub_accounts_response.sub_accounts.sort(key=lambda sub_account: sub_account.name)
        self.assertEqual(
            list_sub_accounts_response,
            core_api.ListSubAccountsResponse.model_construct(
                previous_page_token="",
                next_page_token="",
                sub_accounts=[
                    core_api.SubAccount.model_construct(
                        id=sub_account_id_1,
                        type=sub_account_type,
                        name=sub_account_name_1,
                        details={},
                        activation_timestamp=ANY,
                        create_timestamp=ANY,
                        update_timestamp=ANY,
                        status=core_api.SubAccountStatus.SUB_ACCOUNT_STATUS_CLOSED,
                        account_id=customer_account_v2.id,
                    ),
                    core_api.SubAccount.model_construct(
                        id=sub_account_id_2,
                        type=sub_account_type,
                        name=sub_account_name_2,
                        details={},
                        activation_timestamp=ANY,
                        create_timestamp=ANY,
                        update_timestamp=ANY,
                        status=core_api.SubAccountStatus.SUB_ACCOUNT_STATUS_CLOSED,
                        account_id=customer_account_v2.id,
                    ),
                ],
            ),
        )

    @skipForVaultVersion(lambda v: v >= Version("7.0.0"))
    def test_create_account_v1_legacy_support(self):
        endtoend.standard_setup()
        self.assertIn("DUMMY_CONTRA", endtoend.testhandle.internal_account_id_to_uploaded_id)
        customer = endtoend.core_api_helper.create_customer()

        # Test v1 accounts (legacy, deprecated).
        customer_account_v1 = endtoend.contracts_helper.create_account(
            customer=customer,
            contract=TEST_CONTRACT,
        )
        pib_id = endtoend.postings_helper.inbound_hard_settlement(
            amount=Decimal(1),
            account_id=customer_account_v1["id"],
            internal_account_id="DUMMY_CONTRA",
        )
        pib = endtoend.postings_helper.get_posting_batch(pib_id=pib_id)
        self.assertEqual(pib["status"], "POSTING_INSTRUCTION_BATCH_STATUS_ACCEPTED")


class TestBatchGetProducts(endtoend.End2Endtest):

    def test_batch_get_products(self):
        response = endtoend.contracts_helper.batch_get_products(
            core_api.BatchGetProductsRequest(ids=[TEST_CONTRACT])
        )
        self.assertEquals(
            response.products[TEST_CONTRACT],
            core_api.Product.model_construct(
                id=TEST_CONTRACT,
                # randomised by the framework so can't assert
                display_name=ANY,
                is_internal=False,
                # changes on each upload so can't assert
                current_version_id=ANY,
            ),
        )
