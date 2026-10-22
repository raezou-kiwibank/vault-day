# standard libs
import logging
import os
import uuid
from datetime import datetime, timedelta
from decimal import Decimal
from http import HTTPStatus
from zoneinfo import ZoneInfo

# third party
import requests
from semantic_version import Version

# inception sdk
import inception_sdk.test_framework.endtoend as endtoend
import inception_sdk.vault.core_api as core_api
from inception_sdk.vault.postings.posting_classes import (
    InboundAuthorisation,
    InboundHardSettlement,
    OutboundHardSettlement,
    PostingInstruction,
    PostingInstructionBatch,
    PostingInstructionBatchRequest,
    Settlement,
)

log = logging.getLogger(__name__)
logging.basicConfig(
    level=os.environ.get("LOGLEVEL", "INFO"),
    format="%(asctime)s.%(msecs)03d - %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

TEST_CONTRACT = "test_contract"
TEST_SUB_ACC_CONTRACT = "test_sub_acc_contract"
endtoend.testhandle.CONTRACTS = {
    TEST_CONTRACT: {
        "path": "inception_sdk/test_framework/endtoend/test/e2e/input/template/"
        "contract_template.py",
        "template_params": {},
    },
}


@endtoend.skipForVaultVersionLessThan(Version("5.4.0"))
class TestPostingsSync(endtoend.End2Endtest):
    """Tests our posting error response behaviour. Contract tests don't typically trigger this
    intentionally, as it is usually a mistake on the test writer or contract writer side, so we
    do not have any consistent usage that we can rely on to flag any breaking changes.

    This tests the synchronous postings path.
    """

    @classmethod
    def setUpClass(cls):
        endtoend.testhandle.use_sync_postings = True
        super().setUpClass()

    def test_pib_response_error_handling(self):
        endtoend.standard_setup()
        cust_id = endtoend.core_api_helper.create_customer()
        account = endtoend.contracts_helper.create_account(
            customer=cust_id,
            contract=TEST_CONTRACT,
            status="ACCOUNT_STATUS_OPEN",
        )

        # This will always trigger an error as it violates Postings API validation
        with self.assertRaises(requests.exceptions.HTTPError) as ctx:
            endtoend.postings_helper.send_and_wait_for_posting_instruction_batch(
                pib_request=PostingInstructionBatchRequest(
                    request_id=str(uuid.uuid4()),
                    posting_instruction_batch=PostingInstructionBatch(
                        posting_instructions=[
                            PostingInstruction(
                                InboundAuthorisation(
                                    amount=Decimal(-1),
                                    target_account_id=account["id"],
                                    denomination="GBP",
                                    internal_account_id="DUMMY_CONTRA",
                                ),
                                client_transaction_id=str(uuid.uuid4()),
                            )
                        ],
                        client_id=endtoend.postings_helper.POSTINGS_API_CLIENT_ID,
                        client_batch_id=str(uuid.uuid4()),
                    ),
                )
            )
        self.assertEqual(ctx.exception.response.status_code, HTTPStatus.BAD_REQUEST)
        self.assertEqual(ctx.exception.response.json()["code"], "INVALID_ARGUMENT")

        pib_request = PostingInstructionBatchRequest(
            request_id=str(uuid.uuid4()),
            posting_instruction_batch=PostingInstructionBatch(
                posting_instructions=[
                    PostingInstruction(
                        InboundAuthorisation(
                            amount=Decimal(1),
                            target_account_id=account["id"],
                            denomination="GBP",
                            internal_account_id="DUMMY_CONTRA",
                        ),
                        client_transaction_id=str(uuid.uuid4()),
                    )
                ],
                client_id=endtoend.postings_helper.POSTINGS_API_CLIENT_ID,
                client_batch_id=str(uuid.uuid4()),
            ),
        )
        pib_id = endtoend.postings_helper.send_and_wait_for_posting_instruction_batch(
            pib_request=pib_request
        )
        pib = endtoend.postings_helper.get_posting_batch(pib_id=pib_id)
        self.assertEqual(pib["status"], "POSTING_INSTRUCTION_BATCH_STATUS_ACCEPTED")

        pib_request = PostingInstructionBatchRequest(
            request_id=str(uuid.uuid4()),
            posting_instruction_batch=PostingInstructionBatch(
                posting_instructions=[
                    PostingInstruction(
                        Settlement(
                            amount=Decimal(1),
                        ),
                        client_transaction_id="non-existent-cti",
                    )
                ],
                client_id=endtoend.postings_helper.POSTINGS_API_CLIENT_ID,
                client_batch_id=str(uuid.uuid4()),
            ),
        )
        pib_id = endtoend.postings_helper.send_and_wait_for_posting_instruction_batch(
            pib_request=pib_request
        )
        pib = endtoend.postings_helper.get_posting_batch(pib_id=pib_id)
        self.assertEqual(pib["status"], "POSTING_INSTRUCTION_BATCH_STATUS_REJECTED")


@endtoend.skipForVaultVersionLessThan(Version("5.5.0"))
class TestFutureDatedPostings(endtoend.End2Endtest):
    @classmethod
    def setUpClass(cls):
        # Force the framework to route all posting helper calls to use the synchronous postings
        # API (sync path)
        endtoend.testhandle.use_sync_postings = True
        super().setUpClass()

    def test_successful_fdp_creation(self):
        customer = endtoend.core_api_helper.create_customer()
        account = endtoend.contracts_helper.create_account_v2(
            product_id=TEST_CONTRACT,
            account=core_api.CustomerAccountRequestBody(
                status=core_api.AccountV2Status.ACCOUNT_STATUS_OPEN,
                stakeholder_ids=[customer],
            ),
        )
        internal_account = endtoend.contracts_helper.create_internal_account_v2(
            account_id="internal-acc-id",
            t_side=endtoend.contracts_helper.AccountV2TSide.T_SIDE_LIABILITY,
        )

        pib_request = PostingInstructionBatchRequest(
            request_id=str(uuid.uuid4()),
            posting_instruction_batch=PostingInstructionBatch(
                posting_instructions=[
                    PostingInstruction(
                        InboundHardSettlement(
                            amount=Decimal(1),
                            target_account_id=account.id,
                            denomination="GBP",
                            internal_account_id=internal_account.id,
                        ),
                        client_transaction_id=str(uuid.uuid4()),
                        value_timestamp=datetime.now(tz=ZoneInfo("UTC")) + timedelta(days=1),
                        booking_timestamp=datetime.now(tz=ZoneInfo("UTC"))
                        + timedelta(days=1, hours=1),
                    ),
                    PostingInstruction(
                        OutboundHardSettlement(
                            amount=Decimal(1),
                            target_account_id=account.id,
                            denomination="GBP",
                            internal_account_id=internal_account.id,
                        ),
                        client_transaction_id=str(uuid.uuid4()),
                        value_timestamp=datetime.now(tz=ZoneInfo("UTC"))
                        + timedelta(days=1, hours=1),
                        booking_timestamp=datetime.now(tz=ZoneInfo("UTC"))
                        + timedelta(days=1, hours=2),
                    ),
                ],
                client_id=endtoend.postings_helper.POSTINGS_API_CLIENT_ID,
                client_batch_id=str(uuid.uuid4()),
            ),
        )
        pib_id = endtoend.postings_helper.send_and_wait_for_posting_instruction_batch(
            pib_request=pib_request
        )
        pib = endtoend.postings_helper.get_posting_batch(pib_id=pib_id)
        self.assertEqual(pib["status"], "POSTING_INSTRUCTION_BATCH_STATUS_ACCEPTED")


@endtoend.skipForMissingExtension(required_extensions=[core_api.VaultCoreExtension.SUB_ACCOUNTS])
@endtoend.skipForVaultVersionLessThan(Version("5.11.0"))
class TestPostingsWithSubAccounts(endtoend.End2Endtest):
    @classmethod
    def setUpClass(cls):
        endtoend.testhandle.CONTRACTS[TEST_SUB_ACC_CONTRACT] = {
            "path": "inception_sdk/test_framework/endtoend/test/e2e/input/template/"
            "sub_account_template.py",
            "template_params": {},
        }
        endtoend.testhandle.use_sync_postings = True
        super().setUpClass()

    def test_single_leg_postings_with_sub_account(self):
        endtoend.standard_setup()
        customer = endtoend.core_api_helper.create_customer()

        # Create an account with a sub-account
        account = endtoend.contracts_helper.create_account_v2(
            product_id=TEST_SUB_ACC_CONTRACT,
            account=core_api.CustomerAccountRequestBody(
                status=core_api.AccountV2Status.ACCOUNT_STATUS_OPEN,
                stakeholder_ids=[customer],
            ),
            create_options=core_api.CreateOptions(
                sub_accounts=[
                    core_api.CreateSubAccountRequest(
                        sub_account=core_api.SubAccountCreateSubAccount(
                            type="SPEND",
                            name="spending pot",
                            status=core_api.SubAccountStatus.SUB_ACCOUNT_STATUS_OPEN,
                        )
                    )
                ]
            ),
        )
        account_id = account.id

        sub_accounts = endtoend.sub_accounts_helper.list_all_sub_accounts(account_id=account_id)
        self.assertEqual(len(sub_accounts), 1)
        sub_account_id = sub_accounts[0].id

        internal_account = endtoend.contracts_helper.create_internal_account_v2(
            account_id="internal-acc-id",
            t_side=endtoend.contracts_helper.AccountV2TSide.T_SIDE_LIABILITY,
        )

        pib_id = endtoend.postings_helper.inbound_hard_settlement(
            amount=Decimal("1.00"),
            account_id=account_id,
            denomination="GBP",
            target_sub_account_id=sub_account_id,
            internal_account_id=internal_account.id,
        )
        pib = endtoend.postings_helper.get_posting_batch(pib_id=pib_id)
        self.assertEqual(pib["status"], "POSTING_INSTRUCTION_BATCH_STATUS_ACCEPTED")

        pib_id = endtoend.postings_helper.outbound_hard_settlement(
            amount=Decimal("1.00"),
            account_id=account_id,
            denomination="GBP",
            target_sub_account_id=sub_account_id,
            internal_account_id=internal_account.id,
        )
        pib = endtoend.postings_helper.get_posting_batch(pib_id=pib_id)
        self.assertEqual(pib["status"], "POSTING_INSTRUCTION_BATCH_STATUS_ACCEPTED")

        pib_id = endtoend.postings_helper.inbound_auth(
            amount=Decimal("1.00"),
            account_id=account_id,
            denomination="GBP",
            target_sub_account_id=sub_account_id,
            target_account_address="DEFAULT",
            internal_account_id=internal_account.id,
        )
        pib = endtoend.postings_helper.get_posting_batch(pib_id=pib_id)
        self.assertEqual(pib["status"], "POSTING_INSTRUCTION_BATCH_STATUS_ACCEPTED")

        pib_id = endtoend.postings_helper.outbound_auth(
            amount=Decimal("1.00"),
            account_id=account_id,
            denomination="GBP",
            target_sub_account_id=sub_account_id,
            target_account_address="DEFAULT",
            internal_account_id=internal_account.id,
        )
        pib = endtoend.postings_helper.get_posting_batch(pib_id=pib_id)
        self.assertEqual(pib["status"], "POSTING_INSTRUCTION_BATCH_STATUS_ACCEPTED")

    def test_transfers_with_sub_accounts(self):
        endtoend.standard_setup()
        customer = endtoend.core_api_helper.create_customer()

        debtor_account = endtoend.contracts_helper.create_account_v2(
            product_id=TEST_SUB_ACC_CONTRACT,
            account=core_api.CustomerAccountRequestBody(
                status=core_api.AccountV2Status.ACCOUNT_STATUS_OPEN,
                stakeholder_ids=[customer],
            ),
            create_options=core_api.CreateOptions(
                sub_accounts=[
                    core_api.CreateSubAccountRequest(
                        sub_account=core_api.SubAccountCreateSubAccount(
                            type="SPEND",
                            name="debtor spending pot",
                            status=core_api.SubAccountStatus.SUB_ACCOUNT_STATUS_OPEN,
                        )
                    )
                ]
            ),
        )
        debtor_sub_accounts = endtoend.sub_accounts_helper.list_all_sub_accounts(
            account_id=debtor_account.id
        )
        self.assertEqual(len(debtor_sub_accounts), 1)
        debtor_sub_account_id = debtor_sub_accounts[0].id

        creditor_account = endtoend.contracts_helper.create_account_v2(
            product_id=TEST_SUB_ACC_CONTRACT,
            account=core_api.CustomerAccountRequestBody(
                status=core_api.AccountV2Status.ACCOUNT_STATUS_OPEN,
                stakeholder_ids=[customer],
            ),
            create_options=core_api.CreateOptions(
                sub_accounts=[
                    core_api.CreateSubAccountRequest(
                        sub_account=core_api.SubAccountCreateSubAccount(
                            type="SPEND",
                            name="creditor spending pot",
                            status=core_api.SubAccountStatus.SUB_ACCOUNT_STATUS_OPEN,
                        )
                    )
                ]
            ),
        )
        creditor_sub_accounts = endtoend.sub_accounts_helper.list_all_sub_accounts(
            account_id=creditor_account.id
        )
        self.assertEqual(len(creditor_sub_accounts), 1)
        creditor_sub_account_id = creditor_sub_accounts[0].id

        pib_id = endtoend.postings_helper.create_transfer(
            amount=Decimal("1.00"),
            debtor_target_account_id=debtor_account.id,
            creditor_target_account_id=creditor_account.id,
            denomination="GBP",
            debtor_target_sub_account_id=debtor_sub_account_id,
            creditor_target_sub_account_id=creditor_sub_account_id,
        )
        pib = endtoend.postings_helper.get_posting_batch(pib_id=pib_id)
        self.assertEqual(pib["status"], "POSTING_INSTRUCTION_BATCH_STATUS_ACCEPTED")
