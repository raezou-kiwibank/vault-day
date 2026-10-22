# standard libs
import logging
import os
import uuid
from decimal import Decimal
from zoneinfo import ZoneInfo

# third party
from semantic_version import Version

# inception sdk
import inception_sdk.test_framework.endtoend as endtoend
import inception_sdk.vault.core_api as core_api
from inception_sdk.test_framework.common.balance_helpers import BalanceDimensions
from inception_sdk.test_framework.endtoend.balances import AccountBalances, NetBalance, NetBalances

log = logging.getLogger(__name__)
logging.basicConfig(
    level=os.environ.get("LOGLEVEL", "INFO"),
    format="%(asctime)s.%(msecs)03d - %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
UTC = ZoneInfo("UTC")
TEST_CONTRACT = "test_contract"
TEST_SUB_ACC_CONTRACT = "test_sub_acc_contract"
endtoend.testhandle.CONTRACTS = {
    TEST_CONTRACT: {
        "path": "inception_sdk/test_framework/endtoend/test/e2e/input/template/"
        "contract_template.py",
        "template_params": {},
    },
}


@endtoend.skipForVaultVersionLessThan(Version("5.7.0"))
class TestBalancesV2(endtoend.End2Endtest):
    def test_wait_for_expected_account_balances_v2_succeeds_when_matching_balance_event_is_consumed(
        self,
    ):
        customer = endtoend.core_api_helper.create_customer()
        account1 = endtoend.contracts_helper.create_account_v2(
            product_id=TEST_CONTRACT,
            account=core_api.CustomerAccountRequestBody(
                status=core_api.AccountV2Status.ACCOUNT_STATUS_OPEN,
                stakeholder_ids=[customer],
            ),
        )
        account2 = endtoend.contracts_helper.create_account_v2(
            product_id=TEST_CONTRACT,
            account=core_api.CustomerAccountRequestBody(
                status=core_api.AccountV2Status.ACCOUNT_STATUS_OPEN,
                stakeholder_ids=[customer],
            ),
        )
        create_request = core_api.CreatePostingInstructionBatchRequest(
            request_id=str(uuid.uuid4()),
            posting_instruction_batch=core_api.PostingInstructionBatch(
                client_id="client-id",
                client_batch_id="client-batch-id",
                batch_details={"key": "value"},
                posting_instructions=[
                    core_api.PostingInstruction(
                        client_transaction_id="txn-1",
                        custom_instruction=core_api.CustomInstruction(
                            postings=[
                                core_api.Posting(
                                    account_id=account1.id,
                                    amount="1",
                                    credit=False,
                                    denomination="GBP",
                                    phase=core_api.PostingPhase.COMMITTED,
                                    account_address="DEFAULT",
                                    asset="COMMERCIAL_BANK_MONEY",
                                    internal_account_processing_label="",
                                ),
                                core_api.Posting(
                                    account_id=account2.id,
                                    amount="1",
                                    credit=True,
                                    denomination="GBP",
                                    phase=core_api.PostingPhase.COMMITTED,
                                    account_address="DEFAULT",
                                    asset="COMMERCIAL_BANK_MONEY",
                                    internal_account_processing_label="",
                                ),
                            ],
                        ),
                    ),
                ],
            ),
        )
        create_resp = endtoend.core_api_helper.create_posting_instruction_batch(create_request)
        self.assertEqual(
            create_resp.posting_instruction_batch.status,
            core_api.PostingInstructionBatchStatus.ACCEPTED,
        )

        # This should not raise an exception
        endtoend.balances_helper.wait_for_expected_account_balances_v2(
            {
                account1.id: AccountBalances(
                    value_balances=[
                        (
                            BalanceDimensions(
                                address="DEFAULT",
                                phase="POSTING_PHASE_COMMITTED",
                                asset="COMMERCIAL_BANK_MONEY",
                                denomination="GBP",
                            ),
                            "-1",
                        )
                    ],
                    booking_balances=[
                        (
                            BalanceDimensions(
                                address="DEFAULT",
                                phase="POSTING_PHASE_COMMITTED",
                                asset="COMMERCIAL_BANK_MONEY",
                                denomination="GBP",
                            ),
                            "-1",
                        )
                    ],
                )
            }
        )

    def test_wait_for_expected_account_balances_v2_fails_when_booking_balance_does_not_match(self):
        customer = endtoend.core_api_helper.create_customer()
        account1 = endtoend.contracts_helper.create_account_v2(
            product_id=TEST_CONTRACT,
            account=core_api.CustomerAccountRequestBody(
                status=core_api.AccountV2Status.ACCOUNT_STATUS_OPEN,
                stakeholder_ids=[customer],
            ),
        )
        account2 = endtoend.contracts_helper.create_account_v2(
            product_id=TEST_CONTRACT,
            account=core_api.CustomerAccountRequestBody(
                status=core_api.AccountV2Status.ACCOUNT_STATUS_OPEN,
                stakeholder_ids=[customer],
            ),
        )
        create_request = core_api.CreatePostingInstructionBatchRequest(
            request_id=str(uuid.uuid4()),
            posting_instruction_batch=core_api.PostingInstructionBatch(
                client_id="client-id",
                client_batch_id="client-batch-id",
                batch_details={"key": "value"},
                posting_instructions=[
                    core_api.PostingInstruction(
                        client_transaction_id="txn-1",
                        custom_instruction=core_api.CustomInstruction(
                            postings=[
                                core_api.Posting(
                                    account_id=account1.id,
                                    amount="1",
                                    credit=False,
                                    denomination="GBP",
                                    phase=core_api.PostingPhase.COMMITTED,
                                    account_address="DEFAULT",
                                    asset="COMMERCIAL_BANK_MONEY",
                                    internal_account_processing_label="",
                                ),
                                core_api.Posting(
                                    account_id=account2.id,
                                    amount="1",
                                    credit=True,
                                    denomination="GBP",
                                    phase=core_api.PostingPhase.COMMITTED,
                                    account_address="DEFAULT",
                                    asset="COMMERCIAL_BANK_MONEY",
                                    internal_account_processing_label="",
                                ),
                            ],
                        ),
                    ),
                ],
            ),
        )
        create_resp = endtoend.core_api_helper.create_posting_instruction_batch(create_request)
        self.assertEqual(
            create_resp.posting_instruction_batch.status,
            core_api.PostingInstructionBatchStatus.ACCEPTED,
        )

        with self.assertRaises(Exception):
            endtoend.balances_helper.wait_for_expected_account_balances_v2(
                {
                    account1.id: AccountBalances(
                        value_balances=[
                            (
                                BalanceDimensions(
                                    address="DEFAULT",
                                    phase="POSTING_PHASE_COMMITTED",
                                    asset="COMMERCIAL_BANK_MONEY",
                                    denomination="GBP",
                                ),
                                "-1",
                            )
                        ],
                        booking_balances=[
                            (
                                BalanceDimensions(
                                    address="DEFAULT",
                                    phase="POSTING_PHASE_COMMITTED",
                                    asset="COMMERCIAL_BANK_MONEY",
                                    denomination="GBP",
                                ),
                                "100",
                            )
                        ],
                    )
                }
            )

    def test_wait_for_expected_account_balances_v2_fails_when_value_balance_does_not_match(self):
        customer = endtoend.core_api_helper.create_customer()
        account1 = endtoend.contracts_helper.create_account_v2(
            product_id=TEST_CONTRACT,
            account=core_api.CustomerAccountRequestBody(
                status=core_api.AccountV2Status.ACCOUNT_STATUS_OPEN,
                stakeholder_ids=[customer],
            ),
        )
        account2 = endtoend.contracts_helper.create_account_v2(
            product_id=TEST_CONTRACT,
            account=core_api.CustomerAccountRequestBody(
                status=core_api.AccountV2Status.ACCOUNT_STATUS_OPEN,
                stakeholder_ids=[customer],
            ),
        )
        create_request = core_api.CreatePostingInstructionBatchRequest(
            request_id=str(uuid.uuid4()),
            posting_instruction_batch=core_api.PostingInstructionBatch(
                client_id="client-id",
                client_batch_id="client-batch-id",
                batch_details={"key": "value"},
                posting_instructions=[
                    core_api.PostingInstruction(
                        client_transaction_id="txn-1",
                        custom_instruction=core_api.CustomInstruction(
                            postings=[
                                core_api.Posting(
                                    account_id=account1.id,
                                    amount="1",
                                    credit=False,
                                    denomination="GBP",
                                    phase=core_api.PostingPhase.COMMITTED,
                                    account_address="DEFAULT",
                                    asset="COMMERCIAL_BANK_MONEY",
                                    internal_account_processing_label="",
                                ),
                                core_api.Posting(
                                    account_id=account2.id,
                                    amount="1",
                                    credit=True,
                                    denomination="GBP",
                                    phase=core_api.PostingPhase.COMMITTED,
                                    account_address="DEFAULT",
                                    asset="COMMERCIAL_BANK_MONEY",
                                    internal_account_processing_label="",
                                ),
                            ],
                        ),
                    ),
                ],
            ),
        )
        create_resp = endtoend.core_api_helper.create_posting_instruction_batch(create_request)
        self.assertEqual(
            create_resp.posting_instruction_batch.status,
            core_api.PostingInstructionBatchStatus.ACCEPTED,
        )

        with self.assertRaises(Exception):
            endtoend.balances_helper.wait_for_expected_account_balances_v2(
                {
                    account1.id: AccountBalances(
                        value_balances=[
                            (
                                BalanceDimensions(
                                    address="DEFAULT",
                                    phase="POSTING_PHASE_COMMITTED",
                                    asset="COMMERCIAL_BANK_MONEY",
                                    denomination="GBP",
                                ),
                                "100",
                            )
                        ],
                        booking_balances=[
                            (
                                BalanceDimensions(
                                    address="DEFAULT",
                                    phase="POSTING_PHASE_COMMITTED",
                                    asset="COMMERCIAL_BANK_MONEY",
                                    denomination="GBP",
                                ),
                                "-1",
                            )
                        ],
                    )
                }
            )

    def test_wait_for_expected_account_balances_v2_succeeds_with_no_booking_balances_expected(self):
        customer = endtoend.core_api_helper.create_customer()
        account1 = endtoend.contracts_helper.create_account_v2(
            product_id=TEST_CONTRACT,
            account=core_api.CustomerAccountRequestBody(
                status=core_api.AccountV2Status.ACCOUNT_STATUS_OPEN,
                stakeholder_ids=[customer],
            ),
        )
        account2 = endtoend.contracts_helper.create_account_v2(
            product_id=TEST_CONTRACT,
            account=core_api.CustomerAccountRequestBody(
                status=core_api.AccountV2Status.ACCOUNT_STATUS_OPEN,
                stakeholder_ids=[customer],
            ),
        )
        create_request = core_api.CreatePostingInstructionBatchRequest(
            request_id=str(uuid.uuid4()),
            posting_instruction_batch=core_api.PostingInstructionBatch(
                client_id="client-id",
                client_batch_id="client-batch-id",
                batch_details={"key": "value"},
                posting_instructions=[
                    core_api.PostingInstruction(
                        client_transaction_id="txn-1",
                        custom_instruction=core_api.CustomInstruction(
                            postings=[
                                core_api.Posting(
                                    account_id=account1.id,
                                    amount="1",
                                    credit=False,
                                    denomination="GBP",
                                    phase=core_api.PostingPhase.COMMITTED,
                                    account_address="DEFAULT",
                                    asset="COMMERCIAL_BANK_MONEY",
                                    internal_account_processing_label="",
                                ),
                                core_api.Posting(
                                    account_id=account2.id,
                                    amount="1",
                                    credit=True,
                                    denomination="GBP",
                                    phase=core_api.PostingPhase.COMMITTED,
                                    account_address="DEFAULT",
                                    asset="COMMERCIAL_BANK_MONEY",
                                    internal_account_processing_label="",
                                ),
                            ],
                        ),
                    ),
                ],
            ),
        )
        create_resp = endtoend.core_api_helper.create_posting_instruction_batch(create_request)
        self.assertEqual(
            create_resp.posting_instruction_batch.status,
            core_api.PostingInstructionBatchStatus.ACCEPTED,
        )

        # This should not raise an exception
        endtoend.balances_helper.wait_for_expected_account_balances_v2(
            {
                account1.id: AccountBalances(
                    value_balances=[
                        (
                            BalanceDimensions(
                                address="DEFAULT",
                                phase="POSTING_PHASE_COMMITTED",
                                asset="COMMERCIAL_BANK_MONEY",
                                denomination="GBP",
                            ),
                            "-1",
                        )
                    ],
                )
            }
        )

    def test_wait_for_expected_account_balances_v2_succeeds_with_no_value_balances_expected(self):
        customer = endtoend.core_api_helper.create_customer()
        account1 = endtoend.contracts_helper.create_account_v2(
            product_id=TEST_CONTRACT,
            account=core_api.CustomerAccountRequestBody(
                status=core_api.AccountV2Status.ACCOUNT_STATUS_OPEN,
                stakeholder_ids=[customer],
            ),
        )
        account2 = endtoend.contracts_helper.create_account_v2(
            product_id=TEST_CONTRACT,
            account=core_api.CustomerAccountRequestBody(
                status=core_api.AccountV2Status.ACCOUNT_STATUS_OPEN,
                stakeholder_ids=[customer],
            ),
        )
        create_request = core_api.CreatePostingInstructionBatchRequest(
            request_id=str(uuid.uuid4()),
            posting_instruction_batch=core_api.PostingInstructionBatch(
                client_id="client-id",
                client_batch_id="client-batch-id",
                batch_details={"key": "value"},
                posting_instructions=[
                    core_api.PostingInstruction(
                        client_transaction_id="txn-1",
                        custom_instruction=core_api.CustomInstruction(
                            postings=[
                                core_api.Posting(
                                    account_id=account1.id,
                                    amount="1",
                                    credit=False,
                                    denomination="GBP",
                                    phase=core_api.PostingPhase.COMMITTED,
                                    account_address="DEFAULT",
                                    asset="COMMERCIAL_BANK_MONEY",
                                    internal_account_processing_label="",
                                ),
                                core_api.Posting(
                                    account_id=account2.id,
                                    amount="1",
                                    credit=True,
                                    denomination="GBP",
                                    phase=core_api.PostingPhase.COMMITTED,
                                    account_address="DEFAULT",
                                    asset="COMMERCIAL_BANK_MONEY",
                                    internal_account_processing_label="",
                                ),
                            ],
                        ),
                    ),
                ],
            ),
        )
        create_resp = endtoend.core_api_helper.create_posting_instruction_batch(create_request)
        self.assertEqual(
            create_resp.posting_instruction_batch.status,
            core_api.PostingInstructionBatchStatus.ACCEPTED,
        )

        # This should not raise an exception
        endtoend.balances_helper.wait_for_expected_account_balances_v2(
            {
                account1.id: AccountBalances(
                    booking_balances=[
                        (
                            BalanceDimensions(
                                address="DEFAULT",
                                phase="POSTING_PHASE_COMMITTED",
                                asset="COMMERCIAL_BANK_MONEY",
                                denomination="GBP",
                            ),
                            "-1",
                        )
                    ],
                )
            }
        )


@endtoend.skipForMissingExtension(required_extensions=[core_api.VaultCoreExtension.SUB_ACCOUNTS])
@endtoend.skipForVaultVersionLessThan(Version("5.11.0"))
class TestSubAccountBalances(endtoend.End2Endtest):
    def test_sub_account_balances(self):
        endtoend.testhandle.CONTRACTS[TEST_SUB_ACC_CONTRACT] = {
            "path": "inception_sdk/test_framework/endtoend/test/e2e/input/template/"
            "sub_account_template.py",
            "template_params": {},
        }
        endtoend.standard_setup()

        customer = endtoend.core_api_helper.create_customer()

        # Create first Account with one Sub-Account of type SPEND
        account_1 = endtoend.contracts_helper.create_account_v2(
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
                            status=core_api.SubAccountStatus.SUB_ACCOUNT_STATUS_OPEN,
                        )
                    )
                ]
            ),
        )
        self.assertEqual(account_1.status, core_api.AccountV2Status.ACCOUNT_STATUS_OPEN)

        sub_accounts_1 = endtoend.sub_accounts_helper.list_all_sub_accounts(account_id=account_1.id)
        self.assertEqual(len(sub_accounts_1), 1)
        sub_account_id_1 = sub_accounts_1[0].id
        self.assertIsNotNone(sub_account_id_1)

        # Create second Account with one Sub-Account of type SAVE
        account_2 = endtoend.contracts_helper.create_account_v2(
            product_id=TEST_SUB_ACC_CONTRACT,
            account=core_api.CustomerAccountRequestBody(
                status=core_api.AccountV2Status.ACCOUNT_STATUS_OPEN,
                stakeholder_ids=[customer],
            ),
            create_options=core_api.CreateOptions(
                sub_accounts=[
                    core_api.CreateSubAccountRequest(
                        sub_account=core_api.SubAccountCreateSubAccount(
                            type="SAVE",
                            status=core_api.SubAccountStatus.SUB_ACCOUNT_STATUS_OPEN,
                        )
                    )
                ]
            ),
        )
        self.assertEqual(account_2.status, core_api.AccountV2Status.ACCOUNT_STATUS_OPEN)

        sub_accounts_2 = endtoend.sub_accounts_helper.list_all_sub_accounts(account_id=account_2.id)
        self.assertEqual(len(sub_accounts_2), 1)
        sub_account_id_2 = sub_accounts_2[0].id
        self.assertIsNotNone(sub_account_id_2)

        # Create two postings:
        # - One between Account-1 and Sub-Account-1
        # - One between Account-2 and Sub-Account-2
        sub_account_1_posting_amount = Decimal(5)
        sub_account_2_posting_amount = Decimal(6)
        create_request = core_api.CreatePostingInstructionBatchRequest(
            request_id=str(uuid.uuid4()),
            posting_instruction_batch=core_api.PostingInstructionBatch(
                client_id="client-id",
                client_batch_id="client-batch-id",
                batch_details={"key": "value"},
                posting_instructions=[
                    core_api.PostingInstruction(
                        client_transaction_id=str(uuid.uuid4()),
                        custom_instruction=core_api.CustomInstruction(
                            postings=[
                                # Postings targeting Account-1 & Sub-Account-1
                                core_api.Posting(
                                    account_id=account_1.id,
                                    amount=str(sub_account_1_posting_amount),
                                    credit=False,
                                    denomination="GBP",
                                    phase=core_api.PostingPhase.COMMITTED,
                                    account_address="DEFAULT",
                                    asset="COMMERCIAL_BANK_MONEY",
                                    internal_account_processing_label="",
                                ),
                                core_api.Posting(
                                    account_id=account_1.id,
                                    amount=str(sub_account_1_posting_amount),
                                    credit=True,
                                    denomination="GBP",
                                    phase=core_api.PostingPhase.COMMITTED,
                                    account_address="DEFAULT",
                                    asset="COMMERCIAL_BANK_MONEY",
                                    internal_account_processing_label="",
                                    sub_account_id=sub_account_id_1,
                                ),
                                # Postings targeting Account-2 & Sub-Account-2
                                core_api.Posting(
                                    account_id=account_2.id,
                                    amount=str(sub_account_2_posting_amount),
                                    credit=False,
                                    denomination="GBP",
                                    phase=core_api.PostingPhase.COMMITTED,
                                    account_address="DEFAULT",
                                    asset="COMMERCIAL_BANK_MONEY",
                                    internal_account_processing_label="",
                                ),
                                core_api.Posting(
                                    account_id=account_2.id,
                                    amount=str(sub_account_2_posting_amount),
                                    credit=True,
                                    denomination="GBP",
                                    phase=core_api.PostingPhase.COMMITTED,
                                    account_address="DEFAULT",
                                    asset="COMMERCIAL_BANK_MONEY",
                                    internal_account_processing_label="",
                                    sub_account_id=sub_account_id_2,
                                ),
                            ],
                        ),
                    ),
                ],
            ),
        )
        create_resp = endtoend.core_api_helper.create_posting_instruction_batch(create_request)
        self.assertEqual(
            create_resp.posting_instruction_batch.status,
            core_api.PostingInstructionBatchStatus.ACCEPTED,
        )

        # Expect four balances for each Account:
        # - Two Value Balances, one for the Account and one for the Sub-Account.
        # - Two Booking Balances, one for the Account and one for the Sub-Account.
        account_1_value_balances = [
            NetBalance(
                account_id=account_1.id,
                account_address="DEFAULT",
                phase=core_api.PostingPhase.COMMITTED,
                asset="COMMERCIAL_BANK_MONEY",
                denomination="GBP",
                amount=-sub_account_1_posting_amount,
            ),
            NetBalance(
                account_id=account_1.id,
                sub_account_id=sub_account_id_1,
                account_address="DEFAULT",
                phase=core_api.PostingPhase.COMMITTED,
                asset="COMMERCIAL_BANK_MONEY",
                denomination="GBP",
                amount=sub_account_1_posting_amount,
            ),
        ]
        account_1_booking_balances = [
            NetBalance(
                account_id=account_1.id,
                account_address="DEFAULT",
                phase=core_api.PostingPhase.COMMITTED,
                asset="COMMERCIAL_BANK_MONEY",
                denomination="GBP",
                amount=-sub_account_1_posting_amount,
            ),
            NetBalance(
                account_id=account_1.id,
                sub_account_id=sub_account_id_1,
                account_address="DEFAULT",
                phase=core_api.PostingPhase.COMMITTED,
                asset="COMMERCIAL_BANK_MONEY",
                denomination="GBP",
                amount=sub_account_1_posting_amount,
            ),
        ]

        account_2_value_balances = [
            NetBalance(
                account_id=account_2.id,
                account_address="DEFAULT",
                phase=core_api.PostingPhase.COMMITTED,
                asset="COMMERCIAL_BANK_MONEY",
                denomination="GBP",
                amount=-sub_account_2_posting_amount,
            ),
            NetBalance(
                account_id=account_2.id,
                sub_account_id=sub_account_id_2,
                account_address="DEFAULT",
                phase=core_api.PostingPhase.COMMITTED,
                asset="COMMERCIAL_BANK_MONEY",
                denomination="GBP",
                amount=sub_account_2_posting_amount,
            ),
        ]
        account_2_booking_balances = [
            NetBalance(
                account_id=account_2.id,
                account_address="DEFAULT",
                phase=core_api.PostingPhase.COMMITTED,
                asset="COMMERCIAL_BANK_MONEY",
                denomination="GBP",
                amount=-sub_account_2_posting_amount,
            ),
            NetBalance(
                account_id=account_2.id,
                sub_account_id=sub_account_id_2,
                account_address="DEFAULT",
                phase=core_api.PostingPhase.COMMITTED,
                asset="COMMERCIAL_BANK_MONEY",
                denomination="GBP",
                amount=sub_account_2_posting_amount,
            ),
        ]

        endtoend.balances_helper.wait_for_live_net_balances(
            expected_balances=NetBalances(
                value_net_balances=[*account_1_value_balances, *account_2_value_balances],
                booking_net_balances=[*account_1_booking_balances, *account_2_booking_balances],
            ),
        )
