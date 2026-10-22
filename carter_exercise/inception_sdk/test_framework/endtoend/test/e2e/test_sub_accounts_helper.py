# Copyright @ 2026 Thought Machine Group Limited. All rights reserved.
# standard libs
import uuid
from datetime import datetime
from zoneinfo import ZoneInfo

# third party
from semantic_version import Version

# inception sdk
import inception_sdk.test_framework.endtoend as endtoend
import inception_sdk.vault.core_api as core_api

UTC = ZoneInfo("UTC")
TEST_SUB_ACC_CONTRACT = "test_sub_acc_contract"
endtoend.testhandle.CONTRACTS = {
    TEST_SUB_ACC_CONTRACT: {
        "path": "inception_sdk/test_framework/endtoend/test/e2e/input/template/"
        "sub_account_template.py",
        "template_params": {},
    }
}
OPENING_TIMESTAMP = datetime(2026, 1, 1, tzinfo=UTC)
SUB_ACCOUNT_TYPE_SPEND = "SPEND"
SUB_ACCOUNT_NAME = "example spending pot"


@endtoend.skipForMissingExtension(required_extensions=[core_api.VaultCoreExtension.SUB_ACCOUNTS])
@endtoend.skipForVaultVersionLessThan(Version("5.11.0"))
class TestCreateSubAccountViaCreateOptions(endtoend.End2Endtest):
    def test_list_and_batch_get_sub_accounts_created_on_account_open(self):
        endtoend.standard_setup()

        customer = endtoend.core_api_helper.create_customer()
        account = endtoend.contracts_helper.create_account_v2(
            product_id=TEST_SUB_ACC_CONTRACT,
            account=core_api.CustomerAccountRequestBody(
                status=core_api.AccountV2Status.ACCOUNT_STATUS_OPEN,
                stakeholder_ids=[customer],
                activation_timestamp=OPENING_TIMESTAMP,
            ),
            create_options=core_api.CreateOptions(
                sub_accounts=[
                    core_api.CreateSubAccountRequest(
                        sub_account=core_api.SubAccountCreateSubAccount(
                            type=SUB_ACCOUNT_TYPE_SPEND,
                            name=SUB_ACCOUNT_NAME,
                            details={"example detail": "example value"},
                            status=core_api.SubAccountStatus.SUB_ACCOUNT_STATUS_OPEN,
                        )
                    )
                ]
            ),
        )

        self.assertEqual(account.status, core_api.AccountV2Status.ACCOUNT_STATUS_OPEN)
        account_id = account.id

        # 1. List sub accounts passing in the account_id
        list_resp = endtoend.sub_accounts_helper.list_all_sub_accounts(
            account_id=account_id,
        )
        self.assertEqual(len(list_resp), 1)
        listed_sub_account = list_resp[0]
        self.assertEqual(listed_sub_account.account_id, account_id)
        self.assertEqual(listed_sub_account.type, SUB_ACCOUNT_TYPE_SPEND)
        self.assertEqual(listed_sub_account.name, SUB_ACCOUNT_NAME)

        # 2. Batch get sub accounts
        sub_account_id = listed_sub_account.id
        self.assertIsNotNone(sub_account_id)
        batch_resp = endtoend.sub_accounts_helper.batch_get_sub_accounts(
            core_api.BatchGetSubAccountsRequest(ids=[sub_account_id])
        )
        self.assertIn(sub_account_id, batch_resp.sub_accounts)
        fetched_sub_account = batch_resp.sub_accounts[sub_account_id]
        self.assertEqual(fetched_sub_account.account_id, account_id)
        self.assertEqual(fetched_sub_account.type, SUB_ACCOUNT_TYPE_SPEND)
        self.assertEqual(fetched_sub_account.name, SUB_ACCOUNT_NAME)


@endtoend.skipForMissingExtension(required_extensions=[core_api.VaultCoreExtension.SUB_ACCOUNTS])
@endtoend.skipForVaultVersionLessThan(Version("5.11.0"))
class TestCreateSubAccountIndependently(endtoend.End2Endtest):
    def test_create_sub_account_independently(self):
        endtoend.standard_setup()

        customer = endtoend.core_api_helper.create_customer()
        account = endtoend.contracts_helper.create_account_v2(
            product_id=TEST_SUB_ACC_CONTRACT,
            account=core_api.CustomerAccountRequestBody(
                status=core_api.AccountV2Status.ACCOUNT_STATUS_OPEN,
                stakeholder_ids=[customer],
                activation_timestamp=OPENING_TIMESTAMP,
            ),
        )

        self.assertEqual(account.status, core_api.AccountV2Status.ACCOUNT_STATUS_OPEN)
        account_id = account.id

        # Create Sub-Account independently.
        sub_account_id = str(uuid.uuid4())
        created_sub_account = endtoend.sub_accounts_helper.create_sub_account(
            request=core_api.CreateSubAccountRequest(
                request_id=str(uuid.uuid4()),
                sub_account=core_api.SubAccountCreateSubAccount(
                    id=sub_account_id,
                    type=SUB_ACCOUNT_TYPE_SPEND,
                    name=SUB_ACCOUNT_NAME,
                    status=core_api.SubAccountStatus.SUB_ACCOUNT_STATUS_OPEN,
                    account_id=account_id,
                ),
            )
        )

        self.assertIsNotNone(created_sub_account.activation_timestamp)
        self.assertEqual(created_sub_account.id, sub_account_id)
        self.assertEqual(created_sub_account.account_id, account_id)
        self.assertEqual(created_sub_account.type, SUB_ACCOUNT_TYPE_SPEND)
        self.assertEqual(created_sub_account.name, SUB_ACCOUNT_NAME)
        self.assertEqual(
            created_sub_account.status, core_api.SubAccountStatus.SUB_ACCOUNT_STATUS_OPEN
        )


@endtoend.skipForMissingExtension(required_extensions=[core_api.VaultCoreExtension.SUB_ACCOUNTS])
@endtoend.skipForVaultVersionLessThan(Version("5.11.0"))
class TestWaitForSubAccountEvents(endtoend.End2Endtest):
    def test_wait_for_sub_account_event_by_status_with_sub_account_id(self):
        endtoend.standard_setup()

        # First create a Sub-Account alongside an Account.
        customer = endtoend.core_api_helper.create_customer()
        sub_account_id_1 = str(uuid.uuid4())
        account = endtoend.contracts_helper.create_account_v2(
            product_id=TEST_SUB_ACC_CONTRACT,
            account=core_api.CustomerAccountRequestBody(
                status=core_api.AccountV2Status.ACCOUNT_STATUS_OPEN,
                stakeholder_ids=[customer],
                activation_timestamp=OPENING_TIMESTAMP,
            ),
            create_options=core_api.CreateOptions(
                sub_accounts=[
                    core_api.CreateSubAccountRequest(
                        sub_account=core_api.SubAccountCreateSubAccount(
                            id=sub_account_id_1,
                            type=SUB_ACCOUNT_TYPE_SPEND,
                            name=SUB_ACCOUNT_NAME,
                            details={"example detail": "example value"},
                            status=core_api.SubAccountStatus.SUB_ACCOUNT_STATUS_OPEN,
                        )
                    )
                ]
            ),
        )
        account_id = account.id

        # Next, create another Sub-Account independently.
        sub_account_id_2 = str(uuid.uuid4())
        endtoend.sub_accounts_helper.create_sub_account(
            request=core_api.CreateSubAccountRequest(
                request_id=str(uuid.uuid4()),
                sub_account=core_api.SubAccountCreateSubAccount(
                    id=sub_account_id_2,
                    type=SUB_ACCOUNT_TYPE_SPEND,
                    name=SUB_ACCOUNT_NAME,
                    status=core_api.SubAccountStatus.SUB_ACCOUNT_STATUS_OPEN,
                    account_id=account_id,
                ),
            )
        )

        # Wait on both Sub-Account events to be streamed out, listening for events for
        # the given Sub-Account IDs.
        if endtoend.testhandle.use_kafka:
            endtoend.sub_accounts_helper.wait_for_sub_account_event_by_status(
                sub_account_id=sub_account_id_1,
                target_status=core_api.SubAccountStatus.SUB_ACCOUNT_STATUS_OPEN,
            )
            endtoend.sub_accounts_helper.wait_for_sub_account_event_by_status(
                sub_account_id=sub_account_id_2,
                target_status=core_api.SubAccountStatus.SUB_ACCOUNT_STATUS_OPEN,
            )

    def test_wait_for_sub_account_event_by_status_with_account_id(self):
        endtoend.standard_setup()

        # First create a Sub-Account alongside an Account.
        customer = endtoend.core_api_helper.create_customer()
        sub_account_id_1 = str(uuid.uuid4())
        account = endtoend.contracts_helper.create_account_v2(
            product_id=TEST_SUB_ACC_CONTRACT,
            account=core_api.CustomerAccountRequestBody(
                status=core_api.AccountV2Status.ACCOUNT_STATUS_OPEN,
                stakeholder_ids=[customer],
                activation_timestamp=OPENING_TIMESTAMP,
            ),
            create_options=core_api.CreateOptions(
                sub_accounts=[
                    core_api.CreateSubAccountRequest(
                        sub_account=core_api.SubAccountCreateSubAccount(
                            id=sub_account_id_1,
                            type=SUB_ACCOUNT_TYPE_SPEND,
                            name=SUB_ACCOUNT_NAME,
                            details={"example detail": "example value"},
                            status=core_api.SubAccountStatus.SUB_ACCOUNT_STATUS_OPEN,
                        )
                    )
                ]
            ),
        )
        account_id = account.id

        # Next, create another Sub-Account independently.
        sub_account_id_2 = str(uuid.uuid4())
        endtoend.sub_accounts_helper.create_sub_account(
            request=core_api.CreateSubAccountRequest(
                request_id=str(uuid.uuid4()),
                sub_account=core_api.SubAccountCreateSubAccount(
                    id=sub_account_id_2,
                    type=SUB_ACCOUNT_TYPE_SPEND,
                    name=SUB_ACCOUNT_NAME,
                    status=core_api.SubAccountStatus.SUB_ACCOUNT_STATUS_OPEN,
                    account_id=account_id,
                ),
            )
        )

        # Wait on both Sub-Account events to be streamed out, listening for two events on
        # the parent Account ID.
        if endtoend.testhandle.use_kafka:
            endtoend.sub_accounts_helper.wait_for_sub_account_event_by_status(
                account_id=account_id,
                target_status=core_api.SubAccountStatus.SUB_ACCOUNT_STATUS_OPEN,
            )
            endtoend.sub_accounts_helper.wait_for_sub_account_event_by_status(
                account_id=account_id,
                target_status=core_api.SubAccountStatus.SUB_ACCOUNT_STATUS_OPEN,
            )
