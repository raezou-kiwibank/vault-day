# standard libs
import logging
import os
import uuid
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import ANY
from zoneinfo import ZoneInfo

# third party
from semantic_version import Version

# inception sdk
import inception_sdk.test_framework.endtoend as endtoend
import inception_sdk.vault.core_api as core_api

log = logging.getLogger(__name__)
logging.basicConfig(
    level=os.environ.get("LOGLEVEL", "INFO"),
    format="%(asctime)s.%(msecs)03d - %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
UTC = ZoneInfo("UTC")
TEST_CONTRACT = "test_contract"
TEST_LIST_PRODUCT_VERSION_CONTRACT = "test_list_product_version_contract"
TEST_ACCOUNT_ATTRIBUTE_CONTRACT = "test_account_attribute_contract"
endtoend.testhandle.CONTRACTS = {
    TEST_CONTRACT: {
        "path": "inception_sdk/test_framework/endtoend/test/e2e/input/template/"
        "contract_template.py",
        "template_params": {},
    },
    TEST_LIST_PRODUCT_VERSION_CONTRACT: {
        "path": "inception_sdk/test_framework/endtoend/test/e2e/input/template/"
        "params_simple_template.py",
        "template_params": {"my_string_param": "foo"},
    },
    TEST_ACCOUNT_ATTRIBUTE_CONTRACT: {
        "path": "inception_sdk/test_framework/common/test/input/"
        "account_attribute_value_contract.py",
        "template_params": {},
    },
}


@endtoend.skipForVaultVersionLessThan(Version("5.0.0"))
class TestProcessingGroup(endtoend.End2Endtest):
    def test_get_processing_group(self):
        # DEFAULT processing group is always present and cannot be deleted - we may choose to
        # use a test-specific group when multiple processing groups are supported
        processing_group = endtoend.core_api_helper.get_processing_group("DEFAULT")
        self.assertEqual(
            processing_group,
            core_api.ProcessingGroup.model_construct(
                id="DEFAULT",
                # Can't assert on any of these fields as they're subject to change.
                status=ANY,
                create_timestamp=ANY,
                timezone=ANY,
                update_timestamp=ANY,
                minimum_observation_timestamp=ANY,
            ),
        )

    def test_list_processing_groups(self):
        processing_groups = endtoend.core_api_helper.list_processing_groups()
        # PGs are sorted by last update time desc, so we have to re-order by create time
        # to get a stable sort that we can deterministically assert against
        ordered_groups = sorted(processing_groups, key=lambda x: x.create_timestamp)
        self.assertEqual(
            ordered_groups[0],
            core_api.ProcessingGroup.model_construct(
                id="DEFAULT",
                # Can't assert on any of these fields as they're subject to change.
                status=ANY,
                create_timestamp=ANY,
                timezone=ANY,
                update_timestamp=ANY,
                minimum_observation_timestamp=ANY,
            ),
        )


@endtoend.skipForVaultVersionLessThan(Version("5.9.0"))
class TestBatchGetProductVersions(endtoend.End2Endtest):
    def test_batch_get_product_versions(self):
        product_version_id = endtoend.testhandle.contract_pid_to_uploaded_product_version_id[
            TEST_CONTRACT
        ]
        request = core_api.BatchGetProductVersionsRequest(
            ids=[product_version_id],
            view=core_api.ProductVersionView.BASIC,
        )
        response = endtoend.core_api_helper.batch_get_product_versions(request)
        self.assertIn(product_version_id, response.product_versions)
        self.assertEqual(
            response.product_versions[product_version_id].id,
            product_version_id,
        )

    def test_batch_get_product_versions_with_include_code(self):
        product_version_id = endtoend.testhandle.contract_pid_to_uploaded_product_version_id[
            TEST_CONTRACT
        ]
        request = core_api.BatchGetProductVersionsRequest(
            ids=[product_version_id],
            view=core_api.ProductVersionView.INCLUDE_CODE,
        )
        response = endtoend.core_api_helper.batch_get_product_versions(request)
        self.assertIn(product_version_id, response.product_versions)
        product_version = response.product_versions[product_version_id]
        self.assertEqual(product_version.id, product_version_id)
        self.assertIsNotNone(product_version.code)


@endtoend.skipForVaultVersionLessThan(Version("5.4.0"))
class TestSyncPostingsAPI(endtoend.End2Endtest):
    def test_create_and_list_posting_instruction_batch(self):
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
        client_transaction_id = str(uuid.uuid4())
        create_request = core_api.CreatePostingInstructionBatchRequest(
            request_id=str(uuid.uuid4()),
            posting_instruction_batch=core_api.PostingInstructionBatch(
                client_id="client-id",
                client_batch_id="client-batch-id",
                batch_details={"key": "value"},
                posting_instructions=[
                    core_api.PostingInstruction(
                        client_transaction_id=client_transaction_id,
                        transfer=core_api.Transfer(
                            amount=Decimal(1),
                            debtor_target_account=core_api.TargetAccount(account_id=account1.id),
                            creditor_target_account=core_api.TargetAccount(account_id=account2.id),
                            denomination="GBP",
                        ),
                    ),
                ],
            ),
        )
        create_resp = endtoend.core_api_helper.create_posting_instruction_batch(create_request)
        self.assertIsNotNone(create_resp)
        self.assertEqual(
            create_resp.posting_instruction_batch.status,
            core_api.PostingInstructionBatchStatus.ACCEPTED,
        )
        self.assertIn(
            core_api.Balance.model_construct(
                account_id=account2.id,
                account_address="DEFAULT",
                phase=core_api.PostingPhase.COMMITTED,
                asset="COMMERCIAL_BANK_MONEY",
                denomination="GBP",
                posting_instruction_batch_id=ANY,
                value_time=ANY,
                amount=Decimal("1"),
                total_debit=Decimal("0"),
                total_credit=Decimal("1"),
                id=ANY,
            ),
            create_resp.balances,
        )
        self.assertIn(
            core_api.Balance.model_construct(
                account_id=account1.id,
                account_address="DEFAULT",
                phase=core_api.PostingPhase.COMMITTED,
                asset="COMMERCIAL_BANK_MONEY",
                denomination="GBP",
                posting_instruction_batch_id=ANY,
                value_time=ANY,
                amount=Decimal("-1"),
                total_debit=Decimal("1"),
                total_credit=Decimal("0"),
                id=ANY,
            ),
            create_resp.balances,
        )
        if endtoend.testhandle.vault_version >= Version("5.7.0"):
            # only two account affected
            self.assertEqual(2, len(create_resp.live_balances))
            account_id_to_balances = {
                live_balance.account_id: live_balance for live_balance in create_resp.live_balances
            }
            self.assertIn(
                core_api.BalanceV2.model_construct(
                    account_id=account1.id,
                    account_address="DEFAULT",
                    phase=core_api.PostingPhase.COMMITTED,
                    asset="COMMERCIAL_BANK_MONEY",
                    denomination="GBP",
                    timestamp=ANY,
                    amount=Decimal("-1"),
                    total_debit=Decimal("1"),
                    total_credit=Decimal("0"),
                ),
                account_id_to_balances[account1.id].value_balances,
            )
            self.assertIn(
                core_api.BalanceV2.model_construct(
                    account_id=account2.id,
                    account_address="DEFAULT",
                    phase=core_api.PostingPhase.COMMITTED,
                    asset="COMMERCIAL_BANK_MONEY",
                    denomination="GBP",
                    timestamp=ANY,
                    amount=Decimal("1"),
                    total_debit=Decimal("0"),
                    total_credit=Decimal("1"),
                ),
                account_id_to_balances[account2.id].value_balances,
            )
            self.assertIn(
                core_api.BalanceV2.model_construct(
                    account_id=account1.id,
                    account_address="DEFAULT",
                    phase=core_api.PostingPhase.COMMITTED,
                    asset="COMMERCIAL_BANK_MONEY",
                    denomination="GBP",
                    timestamp=ANY,
                    amount=Decimal("-1"),
                    total_debit=Decimal("1"),
                    total_credit=Decimal("0"),
                ),
                account_id_to_balances[account1.id].booking_balances,
            )
            self.assertIn(
                core_api.BalanceV2.model_construct(
                    account_id=account2.id,
                    account_address="DEFAULT",
                    phase=core_api.PostingPhase.COMMITTED,
                    asset="COMMERCIAL_BANK_MONEY",
                    denomination="GBP",
                    timestamp=ANY,
                    amount=Decimal("1"),
                    total_debit=Decimal("0"),
                    total_credit=Decimal("1"),
                ),
                account_id_to_balances[account2.id].booking_balances,
            )
        else:
            self.assertIsNone(create_resp.live_balances)

        list_request = core_api.ListPostingInstructionBatchesRequest(
            page_size=1,
            client_transaction_ids=[client_transaction_id],
        )

        # List PIBs is eventually consistent - see docs for more information
        list_resp = endtoend.helper.retry_call(
            func=endtoend.core_api_helper.list_posting_instruction_batches,
            f_args=[list_request],
            result_wrapper=lambda x: len(x.posting_instruction_batches),
            expected_result=1,
        )
        self.assertEqual(len(list_resp.posting_instruction_batches[0].posting_instructions), 1)
        self.assertEqual(
            len(
                list_resp.posting_instruction_batches[0].posting_instructions[0].committed_postings
            ),
            2,
        )
        self.assertEqual(
            list_resp.posting_instruction_batches[0].posting_instructions[0].client_transaction_id,
            client_transaction_id,
        )

    def test_list_posting_instruction_batches_is_empty(self):
        request = core_api.ListPostingInstructionBatchesRequest(
            page_size=1,
            order_by_direction=core_api.OrderByDirection.ASC,
            account_ids=["acc-id"],
        )
        resp = endtoend.core_api_helper.list_posting_instruction_batches(request)
        self.assertEqual(
            resp,
            core_api.ListPostingInstructionBatchesResponse.model_construct(
                posting_instruction_batches=[],
                previous_page_token="",
                next_page_token="",
            ),
        )


@endtoend.skipForVaultVersionLessThan(Version("5.5.0"))
class TestFutureDatedPostings(endtoend.End2Endtest):
    def test_successful_fdp_creation(self):
        customer = endtoend.core_api_helper.create_customer()
        account = endtoend.contracts_helper.create_account_v2(
            product_id=TEST_CONTRACT,
            account=core_api.CustomerAccountRequestBody(
                status=core_api.AccountV2Status.ACCOUNT_STATUS_OPEN,
                stakeholder_ids=[customer],
            ),
        )
        internal_account_id = endtoend.testhandle.internal_account_id_to_uploaded_id["DUMMY_CONTRA"]

        inbound_hard = core_api.PostingInstruction(
            client_transaction_id=str(uuid.uuid4()),
            inbound_hard_settlement=core_api.InboundHardSettlement(
                amount=Decimal(1),
                target_account=core_api.TargetAccount(account_id=account.id),
                denomination="GBP",
                internal_account_id=internal_account_id,
            ),
            value_timestamp=datetime.now(UTC) + timedelta(days=1),
            booking_timestamp=datetime.now(UTC) + timedelta(days=1, hours=1),
        )
        outbound_hard = core_api.PostingInstruction(
            client_transaction_id=str(uuid.uuid4()),
            outbound_hard_settlement=core_api.OutboundHardSettlement(
                amount=Decimal(1),
                target_account=core_api.TargetAccount(account_id=account.id),
                denomination="GBP",
                internal_account_id=internal_account_id,
            ),
            value_timestamp=datetime.now(UTC) + timedelta(days=1, hours=1),
            booking_timestamp=datetime.now(UTC) + timedelta(days=1, hours=2),
        )

        request = core_api.CreatePostingInstructionBatchRequest(
            request_id=str(uuid.uuid4()),
            posting_instruction_batch=core_api.PostingInstructionBatch(
                client_id="client-id",
                client_batch_id="client-batch-id",
                batch_details={"key": "value"},
                posting_instructions=[
                    inbound_hard,
                    outbound_hard,
                ],
            ),
        )
        resp = endtoend.core_api_helper.create_posting_instruction_batch(request)
        self.assertIsNotNone(resp)
        self.assertEqual(
            resp.posting_instruction_batch.status, "POSTING_INSTRUCTION_BATCH_STATUS_ACCEPTED"
        )


@endtoend.skipForVaultVersionLessThan(Version("5.7.0"))
class TestBalancesV2(endtoend.End2Endtest):
    def test_list_balances_live(self):
        customer = endtoend.core_api_helper.create_customer()
        account1 = endtoend.contracts_helper.create_account_v2(
            product_id=TEST_CONTRACT,
            account=core_api.CustomerAccountRequestBody(
                status=core_api.AccountV2Status.ACCOUNT_STATUS_OPEN,
                stakeholder_ids=[customer],
            ),
        )
        internal_account_id = endtoend.testhandle.internal_account_id_to_uploaded_id["DUMMY_CONTRA"]

        client_transaction_id = str(uuid.uuid4())
        create_request = core_api.CreatePostingInstructionBatchRequest(
            request_id=str(uuid.uuid4()),
            posting_instruction_batch=core_api.PostingInstructionBatch(
                client_id="client-id",
                client_batch_id="client-batch-id",
                batch_details={"key": "value"},
                posting_instructions=[
                    core_api.PostingInstruction(
                        client_transaction_id=client_transaction_id,
                        outbound_hard_settlement=core_api.OutboundHardSettlement(
                            amount=Decimal("1"),
                            denomination="GBP",
                            internal_account_id=internal_account_id,
                            target_account=core_api.TargetAccount(account_id=account1.id),
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

        list_request = core_api.ListBalancesLiveRequest(
            account_id=account1.id,
            page_size=10,
        )
        list_resp = endtoend.core_api_helper.list_balances_live(list_request)
        # We expect 3 phases to be returned for the account
        self.assertEqual(len(list_resp.balances), 3)
        expected_balances = core_api.LiveBalanceV2(
            account_id=account1.id,
            account_address="DEFAULT",
            phase=core_api.PostingPhase.COMMITTED,
            asset="COMMERCIAL_BANK_MONEY",
            denomination="GBP",
            amount=Decimal("-1"),
            total_debit=Decimal("1"),
            total_credit=Decimal("0"),
        )

        self.assertIn(expected_balances, list_resp.balances)

    def test_list_balances_live_is_empty(self):
        request = core_api.ListBalancesLiveRequest(
            page_size=1,
            account_id="random-acc-id",
        )
        resp = endtoend.core_api_helper.list_balances_live(request)
        self.assertEqual(
            resp,
            core_api.ListBalancesLiveResponse.model_construct(
                balances=[],
                previous_page_token="",
                next_page_token="",
            ),
        )

    def test_list_balances_end(self):
        customer = endtoend.core_api_helper.create_customer()
        account1 = endtoend.contracts_helper.create_account_v2(
            product_id=TEST_CONTRACT,
            account=core_api.CustomerAccountRequestBody(
                status=core_api.AccountV2Status.ACCOUNT_STATUS_OPEN,
                stakeholder_ids=[customer],
            ),
        )
        internal_account_id = endtoend.testhandle.internal_account_id_to_uploaded_id["DUMMY_CONTRA"]
        client_transaction_id = str(uuid.uuid4())

        # ideally we would future-date one posting to show we get the non-None timestamp, but we
        # need to future-date the posting sufficiently to avoid flakes and that would then require
        # our teardown to support zeroing out future-dated postings
        create_request = core_api.CreatePostingInstructionBatchRequest(
            request_id=str(uuid.uuid4()),
            posting_instruction_batch=core_api.PostingInstructionBatch(
                client_id="client-id",
                client_batch_id="client-batch-id",
                batch_details={"key": "value"},
                posting_instructions=[
                    core_api.PostingInstruction(
                        client_transaction_id=client_transaction_id,
                        outbound_hard_settlement=core_api.OutboundHardSettlement(
                            amount=Decimal("1"),
                            denomination="GBP",
                            internal_account_id=internal_account_id,
                            target_account=core_api.TargetAccount(account_id=account1.id),
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

        list_request = core_api.ListBalancesEndRequest(
            account_id=account1.id,
            page_size=10,
        )
        list_resp = endtoend.core_api_helper.list_balances_end(list_request)
        # We expect 3 phases to be returned for the account
        expected_balances = [
            core_api.EndBalanceV2(
                account_id=account1.id,
                account_address="DEFAULT",
                phase=core_api.PostingPhase.COMMITTED,
                asset="COMMERCIAL_BANK_MONEY",
                denomination="GBP",
                timestamp=None,
                amount=Decimal("-1"),
                total_debit=Decimal("1"),
                total_credit=Decimal("0"),
            ),
            core_api.EndBalanceV2(
                account_id=account1.id,
                account_address="DEFAULT",
                phase=core_api.PostingPhase.PENDING_INCOMING,
                asset="COMMERCIAL_BANK_MONEY",
                denomination="GBP",
                timestamp=None,
                amount=Decimal("0"),
                total_debit=Decimal("0"),
                total_credit=Decimal("0"),
            ),
            core_api.EndBalanceV2(
                account_id=account1.id,
                account_address="DEFAULT",
                phase=core_api.PostingPhase.PENDING_OUTGOING,
                asset="COMMERCIAL_BANK_MONEY",
                denomination="GBP",
                timestamp=None,
                amount=Decimal("0"),
                total_debit=Decimal("0"),
                total_credit=Decimal("0"),
            ),
        ]
        self.assertListEqual(expected_balances, list_resp.balances)

    def test_list_balances_end_is_empty(self):
        request = core_api.ListBalancesEndRequest(
            page_size=1,
            account_id="random-acc-id",
        )
        resp = endtoend.core_api_helper.list_balances_end(request)
        self.assertEqual(
            resp,
            core_api.ListBalancesEndResponse.model_construct(
                balances=[],
                snapshot_timestamp=ANY,
                previous_page_token="",
                next_page_token="",
            ),
        )

    def test_list_balances_series(self):
        customer = endtoend.core_api_helper.create_customer()
        account1 = endtoend.contracts_helper.create_account_v2(
            product_id=TEST_CONTRACT,
            account=core_api.CustomerAccountRequestBody(
                status=core_api.AccountV2Status.ACCOUNT_STATUS_OPEN,
                stakeholder_ids=[customer],
            ),
        )
        internal_account_id = endtoend.testhandle.internal_account_id_to_uploaded_id["DUMMY_CONTRA"]
        client_transaction_id = str(uuid.uuid4())
        create_request = core_api.CreatePostingInstructionBatchRequest(
            request_id=str(uuid.uuid4()),
            posting_instruction_batch=core_api.PostingInstructionBatch(
                client_id="client-id",
                client_batch_id="client-batch-id",
                batch_details={"key": "value"},
                posting_instructions=[
                    core_api.PostingInstruction(
                        client_transaction_id=client_transaction_id,
                        outbound_hard_settlement=core_api.OutboundHardSettlement(
                            amount=Decimal("1"),
                            denomination="GBP",
                            internal_account_id=internal_account_id,
                            target_account=core_api.TargetAccount(account_id=account1.id),
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

        list_request = core_api.ListBalancesSeriesRequest(
            account_id=account1.id,
            start_timestamp=datetime.now(UTC) - timedelta(days=1),
            end_timestamp=datetime.now(UTC),
            page_size=10,
        )
        list_resp = endtoend.core_api_helper.list_balances_series(list_request)
        self.assertGreater(len(list_resp.balances), 0)
        expected_balances = core_api.BalanceV2.model_construct(
            account_id=account1.id,
            account_address="DEFAULT",
            phase=core_api.PostingPhase.COMMITTED,
            asset="COMMERCIAL_BANK_MONEY",
            denomination="GBP",
            timestamp=ANY,
            amount=Decimal("-1"),
            total_debit=Decimal("1"),
            total_credit=Decimal("0"),
        )

        self.assertIn(expected_balances, list_resp.balances)


@endtoend.skipForVaultVersionLessThan(Version("5.9.0"))
class TestListProductVersions(endtoend.End2Endtest):
    def test_list_product_versions_with_view_basic(self):
        # GIVEN product p1 with id "test_contract"
        # GIVEN product version pv1 associate to product p1
        product_version_id = endtoend.testhandle.contract_pid_to_uploaded_product_version_id[
            TEST_LIST_PRODUCT_VERSION_CONTRACT
        ]
        product_id = endtoend.testhandle.contract_pid_to_uploaded_pid[
            TEST_LIST_PRODUCT_VERSION_CONTRACT
        ]

        # WHEN a request to fetch all product versions with product id "test_contract"
        # WHEN view is set to basic
        request = core_api.ListProductVersionsRequestBody(
            product_id=product_id,
            view=core_api.ProductVersionView.BASIC,
            page_size=2,
            page_token=None,
        )

        # THEN we should receive a single product version pv1 excluding tags,
        # contract parameters and source code
        response = endtoend.core_api_helper.list_product_versions(
            request=request,
        )
        self.assertEqual(len(response.product_versions), 1)

        product_version = response.product_versions[0]
        self.assertEqual(product_version.id, product_version_id)
        self.assertEqual(product_version.tags, [])
        self.assertEqual(product_version.params, [])
        self.assertEqual(product_version.code, "")

    def test_list_product_versions_with_view_include_params(self):
        # GIVEN product p1 with id "test_list_product_version_contract"
        # GIVEN product version pv1 associate to product p1
        product_version_id = endtoend.testhandle.contract_pid_to_uploaded_product_version_id[
            TEST_LIST_PRODUCT_VERSION_CONTRACT
        ]
        product_id = endtoend.testhandle.contract_pid_to_uploaded_pid[
            TEST_LIST_PRODUCT_VERSION_CONTRACT
        ]

        # WHEN a request to fetch all product versions with
        # product id "test_list_product_version_contract"
        # WHEN view is set to include parameters
        request = core_api.ListProductVersionsRequestBody(
            product_id=product_id,
            view=core_api.ProductVersionView.INCLUDE_PARAMETERS,
            page_size=2,
            page_token=None,
        )

        # THEN we should receive a single product version pv1 including
        # tags and contract parameters associated with product version
        # but excluding source code
        response = endtoend.core_api_helper.list_product_versions(
            request=request,
        )
        self.assertEqual(len(response.product_versions), 1)

        product_version = response.product_versions[0]
        self.assertEqual(product_version.id, product_version_id)
        self.assertEqual(product_version.tags, [])
        self.assertIsNotNone(product_version.params)
        if product_version.params:
            # because mypy complains about typing can be None
            self.assertEqual(len(product_version.params), 1)
        self.assertEqual(product_version.code, "")

    def test_list_product_versions_with_view_include_code(self):
        # GIVEN product p1 with id "test_list_product_version_contract"
        # GIVEN product version pv1 associate to product p1
        product_version_id = endtoend.testhandle.contract_pid_to_uploaded_product_version_id[
            TEST_LIST_PRODUCT_VERSION_CONTRACT
        ]
        product_id = endtoend.testhandle.contract_pid_to_uploaded_pid[
            TEST_LIST_PRODUCT_VERSION_CONTRACT
        ]

        # WHEN a request to fetch all product versions with
        # product id "test_list_product_version_contract"
        # WHEN view is set to include code
        request = core_api.ListProductVersionsRequestBody(
            product_id=product_id,
            view=core_api.ProductVersionView.INCLUDE_CODE,
            page_size=2,
            page_token=None,
        )

        # THEN we should receive a single product version pv1 including tags,
        # contract parameters and source code
        response = endtoend.core_api_helper.list_product_versions(
            request=request,
        )
        self.assertEqual(len(response.product_versions), 1)

        product_version = response.product_versions[0]
        self.assertEqual(product_version.id, product_version_id)
        self.assertEqual(product_version.tags, [])
        self.assertIsNotNone(product_version.params)
        if product_version.params:
            # because mypy complains about typing can be None
            self.assertEqual(len(product_version.params), 1)
        self.assertTrue(len(product_version.code) > 0)


class UpdateProductVersionParams(endtoend.End2Endtest):
    def test_add_product_version_params(self):
        # GIVEN product version pv1 with param p1 with name n1, effective time t1, value v1
        # GIVEN new value v2
        # GIVEN effective time t2
        product_version_id = endtoend.testhandle.contract_pid_to_uploaded_product_version_id[
            TEST_LIST_PRODUCT_VERSION_CONTRACT
        ]
        new_value = "bar"
        future_timestamp = datetime.now(UTC) + timedelta(days=1)

        # WHEN a request to update p1 with value v2 at effective time t2
        request = core_api.UpdateProductVersionParamsRequestBody(
            product_version_id=product_version_id,
            request_id=str(uuid.uuid4()),
            items_to_add=[
                core_api.UpdateProductVersionParams(
                    name="my_string_param",
                    value=new_value,
                    effective_timestamp=future_timestamp,
                )
            ],
            items_to_remove=[],
        )

        endtoend.core_api_helper.update_product_version_params(
            request=request,
        )

        # THEN pv1 with param p1 has new value v2 at effective time t2
        ts_resp = endtoend.core_api_helper.list_product_version_timeseries(product_version_id)

        # Find the specific entry for future timestamp
        self.assertEqual(len(ts_resp.product_version_param_timeseries), 1)
        actual_param = ts_resp.product_version_param_timeseries[0]
        self.assertEqual(actual_param.param_name, "my_string_param")

        future_param_entry = next(
            (v for v in actual_param.values if v.effective_from_timestamp == future_timestamp),
        )

        self.assertIsNotNone(future_param_entry, "could not find future param entry")
        self.assertEqual(future_param_entry.value, new_value)

    def test_updates_product_version_params(self):
        # GIVEN product version pv1 with param p1 with name n1, future dated effective time t1,
        # value v1
        # GIVEN updated value v2
        product_version_id = endtoend.testhandle.contract_pid_to_uploaded_product_version_id[
            TEST_LIST_PRODUCT_VERSION_CONTRACT
        ]
        # we can only update future values so we create one first before updating
        original_value = "bar"
        updated_value = "baz"
        future_timestamp = datetime.now(UTC) + timedelta(days=1)
        request_create = core_api.UpdateProductVersionParamsRequestBody(
            product_version_id=product_version_id,
            request_id=str(uuid.uuid4()),
            items_to_add=[
                core_api.UpdateProductVersionParams(
                    name="my_string_param",
                    value=original_value,
                    effective_timestamp=future_timestamp,
                )
            ],
            items_to_remove=[],
        )
        endtoend.core_api_helper.update_product_version_params(
            request=request_create,
        )
        # WHEN a request to UPDATE p1 with value v2 at future dated effective time t1
        request_update = core_api.UpdateProductVersionParamsRequestBody(
            product_version_id=product_version_id,
            request_id=str(uuid.uuid4()),
            items_to_add=[
                core_api.UpdateProductVersionParams(
                    name="my_string_param",
                    value=updated_value,
                    effective_timestamp=future_timestamp,
                )
            ],
            items_to_remove=[
                core_api.UpdateProductVersionParams(
                    name="my_string_param",
                    effective_timestamp=future_timestamp,
                )
            ],
        )
        endtoend.core_api_helper.update_product_version_params(
            request=request_update,
        )

        # THEN pv1 with param p1 having updated value v2 at effective time t1
        ts_resp = endtoend.core_api_helper.list_product_version_timeseries(product_version_id)

        # Find the specific entry for future timestamp
        self.assertEqual(len(ts_resp.product_version_param_timeseries), 1)
        actual_param = ts_resp.product_version_param_timeseries[0]
        self.assertEqual(actual_param.param_name, "my_string_param")

        future_param_entry = next(
            (v for v in actual_param.values if v.effective_from_timestamp == future_timestamp),
        )

        self.assertIsNotNone(future_param_entry, "could not find future param entry")
        self.assertEqual(future_param_entry.value, updated_value)

    def test_removes_product_version_params(self):
        # GIVEN product version pv1 with param p1 with name n1, future dated effective time t1,
        # value v1
        # We can only remove future values so we create one first before updating
        product_version_id = endtoend.testhandle.contract_pid_to_uploaded_product_version_id[
            TEST_LIST_PRODUCT_VERSION_CONTRACT
        ]
        original_value = "bar"
        future_timestamp = datetime.now(UTC) + timedelta(days=1)
        request_create = core_api.UpdateProductVersionParamsRequestBody(
            product_version_id=product_version_id,
            request_id=str(uuid.uuid4()),
            items_to_add=[
                core_api.UpdateProductVersionParams(
                    name="my_string_param",
                    value=original_value,
                    effective_timestamp=future_timestamp,
                )
            ],
            items_to_remove=[],
        )
        endtoend.core_api_helper.update_product_version_params(
            request=request_create,
        )
        # WHEN a request to REMOVE value v1 for param p1 at future dated effective time t1
        request_remove = core_api.UpdateProductVersionParamsRequestBody(
            product_version_id=product_version_id,
            request_id=str(uuid.uuid4()),
            items_to_add=[],
            items_to_remove=[
                core_api.UpdateProductVersionParams(
                    name="my_string_param",
                    effective_timestamp=future_timestamp,
                )
            ],
        )
        endtoend.core_api_helper.update_product_version_params(
            request=request_remove,
        )

        # THEN pv1 with param p1 no longer has value v1 at effective time t1
        ts_resp = endtoend.core_api_helper.list_product_version_timeseries(product_version_id)

        # Find the specific entry for future timestamp
        self.assertEqual(len(ts_resp.product_version_param_timeseries), 1)
        actual_param = ts_resp.product_version_param_timeseries[0]
        self.assertEqual(actual_param.param_name, "my_string_param")

        future_param_entry = next(
            (v for v in actual_param.values if v.effective_from_timestamp == future_timestamp),
            None,
        )

        # Verify entry is removed
        self.assertIsNone(future_param_entry, "param value was not removed from timeseries")


@endtoend.skipForVaultVersionLessThan(Version("5.4.0"))
class TestListAccountAttributes(endtoend.End2Endtest):
    def test_list_account_attributes(self):
        effective_timestamp = datetime(2025, 1, 1, tzinfo=UTC)
        datetime_attribute_value = datetime(2025, 2, 2, tzinfo=UTC)

        customer = endtoend.core_api_helper.create_customer()
        account1 = endtoend.contracts_helper.create_account_v2(
            product_id=TEST_ACCOUNT_ATTRIBUTE_CONTRACT,
            account=core_api.CustomerAccountRequestBody(
                status=core_api.AccountV2Status.ACCOUNT_STATUS_OPEN,
                stakeholder_ids=[customer],
            ),
        )
        account_attribute_values_response = endtoend.core_api_helper.list_account_attributes(
            request=core_api.ListAccountAttributeValuesRequest(
                account_ids=[account1.id],
                attribute_names=[
                    "string_attribute",
                    "decimal_attribute",
                    "date_time_attribute",
                ],
                effective_timestamps=[effective_timestamp],
                page_size=100,
            )
        )

        self.assertEqual(
            account_attribute_values_response.account_attribute_values,
            [
                core_api.AccountAttributeValue(
                    account_id=account1.id,
                    attribute_name="date_time_attribute",
                    effective_timestamp=effective_timestamp,
                    value=core_api.AttributeValue(
                        date_time_value=core_api.AttributeDateTimeValue(
                            value=datetime_attribute_value
                        )
                    ),
                ),
                core_api.AccountAttributeValue(
                    account_id=account1.id,
                    attribute_name="decimal_attribute",
                    effective_timestamp=effective_timestamp,
                    value=core_api.AttributeValue(
                        decimal_value=core_api.AttributeDecimalValue(value=Decimal("1234"))
                    ),
                ),
                core_api.AccountAttributeValue(
                    account_id=account1.id,
                    attribute_name="string_attribute",
                    effective_timestamp=effective_timestamp,
                    value=core_api.AttributeValue(
                        string_value=core_api.AttributeStringValue(value="string_attribute_value")
                    ),
                ),
            ],
        )
