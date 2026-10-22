# standard libs
import json
from datetime import datetime
from decimal import Decimal
from unittest import TestCase
from unittest.mock import ANY, MagicMock, Mock, PropertyMock, patch, sentinel
from zoneinfo import ZoneInfo

# inception sdk
import inception_sdk.test_framework.endtoend as endtoend
import inception_sdk.vault.core_api as core_api
from inception_sdk.common.python.file_utils import load_file_contents
from inception_sdk.test_framework.endtoend import postings_helper
from inception_sdk.vault.core_api import (
    CommittedPostingInstructionBatch,
    CreatePostingInstructionBatchResponse,
    ListPostingInstructionBatchesResponse,
    PostingInstructionBatch,
    PostingInstructionBatchError,
    PostingInstructionBatchErrorType,
    PostingInstructionBatchStatus,
)
from inception_sdk.vault.postings.posting_classes import (
    MigrationPostingInstructionBatchRequest,
    PostingInstructionBatchRequest,
)

UTC = ZoneInfo("UTC")

ERROR_RESPONSE = json.loads(
    load_file_contents(
        "inception_sdk/test_framework/endtoend/test/unit/input/pib_response_errored.json"
    )
)
ERROR_MIGRATION_RESPONSE = json.loads(
    load_file_contents(
        "inception_sdk/test_framework/endtoend/test/unit/input/pib_migration_response_errored.json"
    )
)
ACCEPTED_RESPONSE = json.loads(
    load_file_contents(
        "inception_sdk/test_framework/endtoend/test/unit/input/pib_response_accepted.json"
    )
)
ACCEPTED_MIGRATION_RESPONSE = json.loads(
    load_file_contents(
        "inception_sdk/test_framework/endtoend/test/unit/input/pib_migration_response_accepted.json"  # noqa: E501
    )
)


def fail(self: TestCase):
    def trigger_test_failure(**kwargs):
        self.fail("This function should not be called in this test.")

    return trigger_test_failure


@patch.object(endtoend.core_api_helper, "create_posting_instruction_batch")
@patch.object(endtoend, "testhandle")
class SendAndWaitForPIBSyncRoutingTest(TestCase):
    def test_routing_to_sync_postings_and_returning_pib_id(
        self, mock_testhandle: Mock, mock_create_posting_instruction_batch: Mock
    ):
        pib_request = PostingInstructionBatchRequest(
            request_id="test_request_id",
            posting_instruction_batch=postings_helper.PostingInstructionBatch(
                client_id="client-id",
                client_batch_id="batch-id",
                posting_instructions=[],
            ),
        )

        expected_pib = CommittedPostingInstructionBatch(
            id="happy-pib-id",
            create_request_id="test_request_id",
            client_id="client-id",
            client_batch_id="batch-id",
            batch_details={},
            value_timestamp=None,
            booking_timestamp=None,
            status=PostingInstructionBatchStatus.ACCEPTED,
            error=None,
            insertion_timestamp=datetime.now(tz=ZoneInfo("UTC")),
            source_insertion_timestamp=datetime.now(ZoneInfo("UTC")),
            posting_instructions=[],
        )
        mock_create_posting_instruction_batch.return_value = CreatePostingInstructionBatchResponse(
            posting_instruction_batch=expected_pib, balances=[], live_balances=[]
        )

        type(mock_testhandle).use_sync_postings = PropertyMock(return_value=True)

        pib_id = postings_helper.send_and_wait_for_posting_instruction_batch(
            pib_request=pib_request
        )
        self.assertEqual(pib_id, "happy-pib-id")
        mock_create_posting_instruction_batch.assert_called_once()

    def test_routing_to_sync_postings_raises_value_error_on_migration_request(
        self, mock_testhandle: Mock, mock_create_posting_instruction_batch: Mock
    ):
        pib_request = MigrationPostingInstructionBatchRequest(
            request_id="test_request_id",
            posting_instruction_batch=sentinel.posting_instruction_batch,
            source_insert_timestamp=sentinel.source_insert_timestamp,
            account_sequence_number=0,
            target_account_id=sentinel.target_account_id,
        )

        type(mock_testhandle).use_sync_postings = PropertyMock(return_value=True)

        with self.assertRaises(ValueError) as ctx:
            postings_helper.send_and_wait_for_posting_instruction_batch(pib_request=pib_request)
        self.assertEqual(
            ctx.exception.args[0],
            "MigrationPostingInstructionBatchRequest is not supported in "
            "synchronous postings mode.",
        )


@patch.object(postings_helper, "wait_for_migration_posting_responses")
@patch.object(postings_helper, "wait_for_posting_responses")
@patch.object(postings_helper, "send_migration_postings_request")
@patch.object(postings_helper, "create_and_produce_posting_request")
@patch.object(endtoend, "testhandle")
class SendAndWaitForPIBTest(TestCase):
    def test_exception_raised_on_error_response(
        self,
        mock_testhandle: Mock,
        mock_create_and_produce_posting_request: Mock,
        mock_send_migration_postings_request: Mock,
        mock_wait_for_posting_responses: Mock,
        mock_wait_for_migration_posting_responses: Mock,
    ):
        error = ERROR_RESPONSE["error"]
        pib_request = PostingInstructionBatchRequest(
            request_id="test_request_id",
            posting_instruction_batch=sentinel.posting_instruction_batch,
        )

        type(mock_testhandle).use_sync_postings = PropertyMock(return_value=False)
        type(mock_testhandle).use_kafka = PropertyMock(return_value=True)
        mock_create_and_produce_posting_request.return_value = "test_request_id"
        mock_wait_for_posting_responses.return_value = ([], {"test_request_id": error})
        mock_send_migration_postings_request.side_effect = fail(self)
        mock_wait_for_migration_posting_responses.side_effect = fail(self)

        with self.assertRaises(ValueError) as ctx:
            postings_helper.send_and_wait_for_posting_instruction_batch(pib_request=pib_request)
        self.assertEqual(
            ctx.exception.args[0],
            f"Posting pib_request.request_id='test_request_id' resulted in {error=}",
        )

    def test_exception_raised_on_migration_error_response(
        self,
        mock_testhandle: Mock,
        mock_create_and_produce_posting_request: Mock,
        mock_send_migration_postings_request: Mock,
        mock_wait_for_posting_responses: Mock,
        mock_wait_for_migration_posting_responses: Mock,
    ):
        error = ERROR_MIGRATION_RESPONSE["posting_instruction_batch"]["error"]
        pib_request = MigrationPostingInstructionBatchRequest(
            request_id="test_request_id",
            posting_instruction_batch=sentinel.posting_instruction_batch,
            source_insert_timestamp=sentinel.source_insert_timestamp,
            account_sequence_number=0,
            target_account_id=sentinel.target_account_id,
        )

        type(mock_testhandle).use_sync_postings = PropertyMock(return_value=False)
        type(mock_testhandle).use_kafka = PropertyMock(return_value=True)
        mock_create_and_produce_posting_request.side_effect = fail(self)
        mock_wait_for_posting_responses.side_effect = fail(self)
        mock_send_migration_postings_request.return_value = "test_request_id"
        mock_wait_for_migration_posting_responses.return_value = ([], {"test_request_id": error})

        with self.assertRaises(ValueError) as ctx:
            postings_helper.send_and_wait_for_posting_instruction_batch(
                pib_request=pib_request,
            )
        self.assertEqual(
            ctx.exception.args[0],
            f"Posting pib_request.request_id='test_request_id' resulted in {error=}",
        )

    def test_exception_raised_on_missing_response(
        self,
        mock_testhandle: Mock,
        mock_create_and_produce_posting_request: Mock,
        mock_send_migration_postings_request: Mock,
        mock_wait_for_posting_responses: Mock,
        mock_wait_for_migration_posting_responses: Mock,
    ):
        pib_request = PostingInstructionBatchRequest(
            request_id="test_request_id",
            posting_instruction_batch=sentinel.posting_instruction_batch,
        )
        type(mock_testhandle).use_sync_postings = PropertyMock(return_value=False)
        type(mock_testhandle).use_kafka = PropertyMock(return_value=True)
        mock_create_and_produce_posting_request.return_value = "test_request_id"
        mock_wait_for_posting_responses.return_value = ([], {})
        mock_send_migration_postings_request.side_effect = fail(self)
        mock_wait_for_migration_posting_responses.side_effect = fail(self)

        with self.assertRaises(ValueError) as ctx:
            postings_helper.send_and_wait_for_posting_instruction_batch(pib_request=pib_request)
        self.assertEqual(
            ctx.exception.args[0],
            "No response found for posting pib_request.request_id='test_request_id'",
        )

    def test_exception_raised_on_missing_migration_response(
        self,
        mock_testhandle: Mock,
        mock_create_and_produce_posting_request: Mock,
        mock_send_migration_postings_request: Mock,
        mock_wait_for_posting_responses: Mock,
        mock_wait_for_migration_posting_responses: Mock,
    ):
        pib_request = MigrationPostingInstructionBatchRequest(
            request_id="test_request_id",
            posting_instruction_batch=sentinel.posting_instruction_batch,
            source_insert_timestamp=sentinel.source_insert_timestamp,
            account_sequence_number=0,
            target_account_id=sentinel.target_account_id,
        )
        type(mock_testhandle).use_sync_postings = PropertyMock(return_value=False)
        type(mock_testhandle).use_kafka = PropertyMock(return_value=True)
        mock_create_and_produce_posting_request.side_effect = fail(self)
        mock_wait_for_posting_responses.side_effect = fail(self)
        mock_send_migration_postings_request.return_value = "test_request_id"
        mock_wait_for_migration_posting_responses.return_value = ([], {})

        with self.assertRaises(ValueError) as ctx:
            postings_helper.send_and_wait_for_posting_instruction_batch(
                pib_request=pib_request,
            )
        self.assertEqual(
            ctx.exception.args[0],
            "No response found for posting pib_request.request_id='test_request_id'",
        )

    def test_pib_id_returned_on_successful_response(
        self,
        mock_testhandle: Mock,
        mock_create_and_produce_posting_request: Mock,
        mock_send_migration_postings_request: Mock,
        mock_wait_for_posting_responses: Mock,
        mock_wait_for_migration_posting_responses: Mock,
    ):
        expected_pib_id = ACCEPTED_RESPONSE["id"]

        pib_request = PostingInstructionBatchRequest(
            request_id="test_request_id",
            posting_instruction_batch=sentinel.posting_instruction_batch,
        )
        type(mock_testhandle).use_sync_postings = PropertyMock(return_value=False)
        type(mock_testhandle).use_kafka = PropertyMock(return_value=True)
        mock_create_and_produce_posting_request.return_value = "test_request_id"
        mock_wait_for_posting_responses.return_value = ([expected_pib_id], {})
        mock_send_migration_postings_request.side_effect = fail(self)
        mock_wait_for_migration_posting_responses.side_effect = fail(self)

        pib_id = postings_helper.send_and_wait_for_posting_instruction_batch(
            pib_request=pib_request
        )
        self.assertEqual(pib_id, expected_pib_id)

    def test_pib_id_returned_on_successful_migration_response(
        self,
        mock_testhandle: Mock,
        mock_create_and_produce_posting_request: Mock,
        mock_send_migration_postings_request: Mock,
        mock_wait_for_posting_responses: Mock,
        mock_wait_for_migration_posting_responses: Mock,
    ):
        expected_pib_id = ACCEPTED_MIGRATION_RESPONSE["posting_instruction_batch"]["id"]

        pib_request = MigrationPostingInstructionBatchRequest(
            request_id="test_request_id",
            posting_instruction_batch=sentinel.posting_instruction_batch,
            source_insert_timestamp=sentinel.source_insert_timestamp,
            account_sequence_number=0,
            target_account_id=sentinel.target_account_id,
        )
        type(mock_testhandle).use_sync_postings = PropertyMock(return_value=False)
        type(mock_testhandle).use_kafka = PropertyMock(return_value=True)
        mock_create_and_produce_posting_request.side_effect = fail(self)
        mock_wait_for_posting_responses.side_effect = fail(self)
        mock_send_migration_postings_request.return_value = "test_request_id"
        mock_wait_for_migration_posting_responses.return_value = ([expected_pib_id], {})

        pib_id = postings_helper.send_and_wait_for_posting_instruction_batch(
            pib_request=pib_request,
        )
        self.assertEqual(pib_id, expected_pib_id)


class BatchCompletionRecorderTests(TestCase):
    def setUp(self):
        self.recorder = postings_helper.BatchCompletionRecorder()
        self.migration_recorder = postings_helper.BatchCompletionRecorder(migration=True)

    def test_batch_completion_recorder_records_successful_response(self):
        self.recorder(ACCEPTED_RESPONSE)
        self.assertListEqual(self.recorder.pib_ids, [ACCEPTED_RESPONSE["id"]])
        self.assertDictEqual(self.recorder.errored_responses, {})

    def test_batch_completion_recorder_records_errored_response(self):
        self.recorder(ERROR_RESPONSE)
        self.assertListEqual(self.recorder.pib_ids, [])
        self.assertDictEqual(
            self.recorder.errored_responses,
            {ERROR_RESPONSE["create_request_id"]: ERROR_RESPONSE["error"]},
        )

    def test_migration_response_successful(self):
        self.migration_recorder(ACCEPTED_MIGRATION_RESPONSE)
        self.assertListEqual(
            self.migration_recorder.pib_ids,
            [ACCEPTED_MIGRATION_RESPONSE["posting_instruction_batch"]["id"]],
        )
        self.assertDictEqual(self.migration_recorder.errored_responses, {})

    def test_migration_error_response(self):
        self.migration_recorder(ERROR_MIGRATION_RESPONSE)
        pib = ERROR_MIGRATION_RESPONSE["posting_instruction_batch"]
        self.assertListEqual(self.migration_recorder.pib_ids, [])
        self.assertDictEqual(
            self.migration_recorder.errored_responses, {pib["create_request_id"]: pib["error"]}
        )


@patch.object(postings_helper, "BatchCompletionRecorder")
@patch.object(postings_helper, "wait_for_messages")
@patch.object(endtoend, "testhandle")
class WaitForPostingResponseTest(TestCase):
    def test_wait_for_postings_returns_batch_completion_recorder_results(
        self,
        mock_testhandle: Mock,
        mock_wait_for_messages: Mock,
        mock_BatchCompletionRecorder: MagicMock,
    ):

        mock_batch_completion_recorder = mock_BatchCompletionRecorder.return_value
        mock_batch_completion_recorder.pib_ids = ["a"]
        mock_batch_completion_recorder.errored_responses = {"b": {"key": "value"}}

        type(mock_testhandle).use_kafka = PropertyMock(return_value=True)
        mock_testhandle.kafka_consumers = {
            postings_helper.POSTINGS_API_RESPONSE_TOPIC: sentinel.postings_consumer
        }

        pib_ids, errored_responses = postings_helper.wait_for_posting_responses(
            request_ids={"a", "b"}
        )

        mock_wait_for_messages.assert_called_once_with(
            sentinel.postings_consumer,
            matcher=ANY,
            callback=mock_batch_completion_recorder,
            unique_message_ids={"a": None, "b": None},
            inter_message_timeout=30,
            matched_message_timeout=0,
        )

        self.assertListEqual(pib_ids, ["a"])
        self.assertDictEqual(errored_responses, {"b": {"key": "value"}})


@patch.object(
    endtoend.postings_helper, "_map_to_e2e_internal_accounts_for_posting_instruction_batch"
)
@patch.object(endtoend.core_api_helper, "create_posting_instruction_batch")
class CreatePostingInstructionBatchTest(TestCase):
    def test_successful_creation(
        self, mock_create_batch: Mock, mock_internal_account_mapping: Mock
    ):
        pib = PostingInstructionBatch(
            client_id="client-id",
            client_batch_id="batch-id",
            posting_instructions=[],
        )
        mock_internal_account_mapping.return_value = pib

        expected_pib = CommittedPostingInstructionBatch(
            id="happy-pib-id",
            create_request_id="req-id-1",
            client_id="client-id",
            client_batch_id="batch-id",
            batch_details={},
            value_timestamp=None,
            booking_timestamp=None,
            status=PostingInstructionBatchStatus.ACCEPTED,
            error=None,
            insertion_timestamp=datetime.now(tz=UTC),
            source_insertion_timestamp=datetime.now(tz=UTC),
            posting_instructions=[],
        )
        mock_create_batch.return_value = CreatePostingInstructionBatchResponse(
            posting_instruction_batch=expected_pib, balances=[], live_balances=[]
        )

        result = postings_helper.create_posting_instruction_batch(pib)
        self.assertEqual(result.posting_instruction_batch.id, "happy-pib-id")
        self.assertEqual(
            result.posting_instruction_batch.status, PostingInstructionBatchStatus.ACCEPTED
        )
        mock_create_batch.assert_called_once()
        mock_internal_account_mapping.assert_called_once_with(pib)

    def test_raises_on_unexpected_status(
        self, mock_create_batch: Mock, mock_internal_account_mapping: Mock
    ):
        pib = PostingInstructionBatch(
            client_id="client-id",
            client_batch_id="batch-id",
            posting_instructions=[],
        )
        mock_internal_account_mapping.return_value = pib

        pib_response = CommittedPostingInstructionBatch(
            id="errored-pib-id",
            create_request_id="req-id-2",
            client_id="client-id",
            client_batch_id="batch-id",
            batch_details={},
            value_timestamp=None,
            booking_timestamp=None,
            status=PostingInstructionBatchStatus.REJECTED,
            error=PostingInstructionBatchError(
                type=PostingInstructionBatchErrorType.INVALID_ARGUMENT,
                message="nah nah mate",
            ),
            insertion_timestamp=datetime.now(tz=UTC),
            source_insertion_timestamp=datetime.now(tz=UTC),
            posting_instructions=[],
        )
        mock_create_batch.return_value = CreatePostingInstructionBatchResponse(
            posting_instruction_batch=pib_response, balances=[], live_balances=[]
        )
        with self.assertRaisesRegex(Exception, "unexpected status"):
            # expected status defaults to ACCEPTED
            postings_helper.create_posting_instruction_batch(pib)

        mock_internal_account_mapping.assert_called_once_with(pib)


@patch.object(endtoend.core_api_helper, "list_posting_instruction_batches")
class ListPostingInstructionBatchesTest(TestCase):
    def test_successful_listing(self, mock_list_batches: Mock):
        mock_list_batches.return_value = ListPostingInstructionBatchesResponse(
            posting_instruction_batches=[], previous_page_token="", next_page_token=""
        )
        response = postings_helper.list_posting_instruction_batches(page_size=5)

        self.assertIsInstance(response, ListPostingInstructionBatchesResponse)
        self.assertEqual(response.posting_instruction_batches, [])
        mock_list_batches.assert_called_once()


class MapE2EInternalAccountIDsForPIBTest(TestCase):
    @patch.dict(
        endtoend.testhandle.internal_account_id_to_uploaded_id,
        {"internal_account_id": "e2e_internal_account_id"},
    )
    def test_map_to_e2e_internal_accounts_for_posting_instruction_batch_inbound_hard_settlement(
        self,
    ):
        input_posting_instruction_batch = core_api.PostingInstructionBatch(
            client_id="client_id",
            client_batch_id="client_batch_id",
            posting_instructions=[
                core_api.PostingInstruction(
                    client_transaction_id="client_transaction_id",
                    inbound_hard_settlement=core_api.InboundHardSettlement(
                        amount=Decimal(1),
                        target_account=core_api.TargetAccount(account_id="account_id"),
                        denomination="GBP",
                        internal_account_id="internal_account_id",
                    ),
                ),
                core_api.PostingInstruction(
                    client_transaction_id="client_transaction_id",
                    inbound_hard_settlement=core_api.InboundHardSettlement(
                        amount=Decimal(1),
                        target_account=core_api.TargetAccount(account_id="account_id"),
                        denomination="GBP",
                        internal_account_id="unmapped_internal_account_id",
                    ),
                ),
            ],
        )
        result = postings_helper._map_to_e2e_internal_accounts_for_posting_instruction_batch(
            input_posting_instruction_batch
        )
        self.assertEqual(
            result.posting_instructions[0].inbound_hard_settlement.internal_account_id,
            "e2e_internal_account_id",
        )
        self.assertEqual(
            result.posting_instructions[1].inbound_hard_settlement.internal_account_id,
            "unmapped_internal_account_id",
        )

    @patch.dict(
        endtoend.testhandle.internal_account_id_to_uploaded_id,
        {"internal_account_id": "e2e_internal_account_id"},
    )
    def test_map_to_e2e_internal_accounts_for_posting_instruction_batch_outbound_hard_settlement(
        self,
    ):
        input_posting_instruction_batch = core_api.PostingInstructionBatch(
            client_id="client_id",
            client_batch_id="client_batch_id",
            posting_instructions=[
                core_api.PostingInstruction(
                    client_transaction_id="client_transaction_id",
                    outbound_hard_settlement=core_api.OutboundHardSettlement(
                        amount=Decimal(1),
                        target_account=core_api.TargetAccount(account_id="account_id"),
                        denomination="GBP",
                        internal_account_id="internal_account_id",
                    ),
                ),
                core_api.PostingInstruction(
                    client_transaction_id="client_transaction_id",
                    outbound_hard_settlement=core_api.OutboundHardSettlement(
                        amount=Decimal(1),
                        target_account=core_api.TargetAccount(account_id="account_id"),
                        denomination="GBP",
                        internal_account_id="unmapped_internal_account_id",
                    ),
                ),
            ],
        )
        result = postings_helper._map_to_e2e_internal_accounts_for_posting_instruction_batch(
            input_posting_instruction_batch
        )

        self.assertEqual(
            result.posting_instructions[0].outbound_hard_settlement.internal_account_id,
            "e2e_internal_account_id",
        )
        self.assertEqual(
            result.posting_instructions[1].outbound_hard_settlement.internal_account_id,
            "unmapped_internal_account_id",
        )

    @patch.dict(
        endtoend.testhandle.internal_account_id_to_uploaded_id,
        {"internal_account_id": "e2e_internal_account_id"},
    )
    def test_map_to_e2e_internal_accounts_for_posting_instruction_batch_inbound_authorisation(
        self,
    ):
        input_posting_instruction_batch = core_api.PostingInstructionBatch(
            client_id="client_id",
            client_batch_id="client_batch_id",
            posting_instructions=[
                core_api.PostingInstruction(
                    client_transaction_id="client_transaction_id",
                    inbound_authorisation=core_api.InboundAuthorisation(
                        amount=Decimal(1),
                        target_account=core_api.TargetAccount(account_id="account_id"),
                        denomination="GBP",
                        internal_account_id="internal_account_id",
                    ),
                ),
                core_api.PostingInstruction(
                    client_transaction_id="client_transaction_id",
                    inbound_authorisation=core_api.InboundAuthorisation(
                        amount=Decimal(1),
                        target_account=core_api.TargetAccount(account_id="account_id"),
                        denomination="GBP",
                        internal_account_id="unmapped_internal_account_id",
                    ),
                ),
            ],
        )
        result = postings_helper._map_to_e2e_internal_accounts_for_posting_instruction_batch(
            input_posting_instruction_batch
        )

        self.assertEqual(
            result.posting_instructions[0].inbound_authorisation.internal_account_id,
            "e2e_internal_account_id",
        )
        self.assertEqual(
            result.posting_instructions[1].inbound_authorisation.internal_account_id,
            "unmapped_internal_account_id",
        )

    @patch.dict(
        endtoend.testhandle.internal_account_id_to_uploaded_id,
        {"internal_account_id": "e2e_internal_account_id"},
    )
    def test_map_to_e2e_internal_accounts_for_posting_instruction_batch_outbound_authorisation(
        self,
    ):
        input_posting_instruction_batch = core_api.PostingInstructionBatch(
            client_id="client_id",
            client_batch_id="client_batch_id",
            posting_instructions=[
                core_api.PostingInstruction(
                    client_transaction_id="client_transaction_id",
                    outbound_authorisation=core_api.OutboundAuthorisation(
                        amount=Decimal(1),
                        target_account=core_api.TargetAccount(account_id="account_id"),
                        denomination="GBP",
                        internal_account_id="internal_account_id",
                    ),
                ),
                core_api.PostingInstruction(
                    client_transaction_id="client_transaction_id",
                    outbound_authorisation=core_api.OutboundAuthorisation(
                        amount=Decimal(1),
                        target_account=core_api.TargetAccount(account_id="account_id"),
                        denomination="GBP",
                        internal_account_id="unmapped_internal_account_id",
                    ),
                ),
            ],
        )
        result = postings_helper._map_to_e2e_internal_accounts_for_posting_instruction_batch(
            input_posting_instruction_batch
        )

        self.assertEqual(
            result.posting_instructions[0].outbound_authorisation.internal_account_id,
            "e2e_internal_account_id",
        )
        self.assertEqual(
            result.posting_instructions[1].outbound_authorisation.internal_account_id,
            "unmapped_internal_account_id",
        )

    @patch.dict(
        endtoend.testhandle.internal_account_id_to_uploaded_id,
        {
            "internal_account_id_1": "e2e_internal_account_id_1",
            "internal_account_id_2": "e2e_internal_account_id_2",
        },
    )
    def test_map_to_e2e_internal_accounts_for_posting_instruction_batch_transfer(
        self,
    ):
        input_posting_instruction_batch = core_api.PostingInstructionBatch(
            client_id="client_id",
            client_batch_id="client_batch_id",
            posting_instructions=[
                core_api.PostingInstruction(
                    client_transaction_id="client_transaction_id",
                    transfer=core_api.Transfer(
                        amount=Decimal(1),
                        debtor_target_account=core_api.TargetAccount(
                            account_id="internal_account_id_1"
                        ),
                        creditor_target_account=core_api.TargetAccount(
                            account_id="internal_account_id_2"
                        ),
                        denomination="GBP",
                    ),
                ),
                core_api.PostingInstruction(
                    client_transaction_id="client_transaction_id",
                    transfer=core_api.Transfer(
                        amount=Decimal(1),
                        debtor_target_account=core_api.TargetAccount(
                            account_id="unmapped_internal_account_id_1"
                        ),
                        creditor_target_account=core_api.TargetAccount(
                            account_id="unmapped_internal_account_id_2"
                        ),
                        denomination="GBP",
                    ),
                ),
            ],
        )
        result = postings_helper._map_to_e2e_internal_accounts_for_posting_instruction_batch(
            input_posting_instruction_batch
        )

        self.assertEqual(
            result.posting_instructions[0].transfer.debtor_target_account.account_id,
            "e2e_internal_account_id_1",
        )
        self.assertEqual(
            result.posting_instructions[0].transfer.creditor_target_account.account_id,
            "e2e_internal_account_id_2",
        )
        self.assertEqual(
            result.posting_instructions[1].transfer.debtor_target_account.account_id,
            "unmapped_internal_account_id_1",
        )
        self.assertEqual(
            result.posting_instructions[1].transfer.creditor_target_account.account_id,
            "unmapped_internal_account_id_2",
        )

    @patch.dict(
        endtoend.testhandle.internal_account_id_to_uploaded_id,
        {
            "internal_account_id_1": "e2e_internal_account_id_1",
            "internal_account_id_2": "e2e_internal_account_id_2",
        },
    )
    def test_map_to_e2e_internal_accounts_for_posting_instruction_batch_custom_instruction(
        self,
    ):
        input_posting_instruction_batch = core_api.PostingInstructionBatch(
            client_id="client_id",
            client_batch_id="client_batch_id",
            posting_instructions=[
                core_api.PostingInstruction(
                    client_transaction_id="client_transaction_id",
                    custom_instruction=core_api.CustomInstruction(
                        postings=[
                            core_api.Posting(
                                account_id="account_id_1",
                                amount="1",
                                credit=False,
                                denomination="GBP",
                                phase=core_api.PostingPhase.COMMITTED,
                                account_address="DEFAULT",
                                asset="COMMERCIAL_BANK_MONEY",
                                internal_account_processing_label="",
                            ),
                            core_api.Posting(
                                account_id="internal_account_id_1",
                                amount="1",
                                credit=True,
                                denomination="GBP",
                                phase=core_api.PostingPhase.COMMITTED,
                                account_address="DEFAULT",
                                asset="COMMERCIAL_BANK_MONEY",
                                internal_account_processing_label="",
                            ),
                            core_api.Posting(
                                account_id="account_id_2",
                                amount="2",
                                credit=False,
                                denomination="GBP",
                                phase=core_api.PostingPhase.COMMITTED,
                                account_address="DEFAULT",
                                asset="COMMERCIAL_BANK_MONEY",
                                internal_account_processing_label="",
                            ),
                            core_api.Posting(
                                account_id="internal_account_id_2",
                                amount="2",
                                credit=True,
                                denomination="GBP",
                                phase=core_api.PostingPhase.COMMITTED,
                                account_address="DEFAULT",
                                asset="COMMERCIAL_BANK_MONEY",
                                internal_account_processing_label="",
                            ),
                            core_api.Posting(
                                account_id="account_id_3",
                                amount="3",
                                credit=False,
                                denomination="GBP",
                                phase=core_api.PostingPhase.COMMITTED,
                                account_address="DEFAULT",
                                asset="COMMERCIAL_BANK_MONEY",
                                internal_account_processing_label="",
                            ),
                            core_api.Posting(
                                account_id="unmapped_internal_account_id_3",
                                amount="3",
                                credit=True,
                                denomination="GBP",
                                phase=core_api.PostingPhase.COMMITTED,
                                account_address="DEFAULT",
                                asset="COMMERCIAL_BANK_MONEY",
                                internal_account_processing_label="",
                            ),
                        ],
                    ),
                )
            ],
        )
        result = postings_helper._map_to_e2e_internal_accounts_for_posting_instruction_batch(
            input_posting_instruction_batch
        )

        resulting_postings = result.posting_instructions[0].custom_instruction.postings

        self.assertEqual(len(resulting_postings), 6)
        # Assert nested posting internal account IDs are mapped
        self.assertEqual(resulting_postings[1].account_id, "e2e_internal_account_id_1")
        self.assertEqual(resulting_postings[3].account_id, "e2e_internal_account_id_2")
        self.assertEqual(resulting_postings[5].account_id, "unmapped_internal_account_id_3")


@patch.object(postings_helper, "send_posting_instruction_batch")
class PostingHelpersSubAccountFieldsTest(TestCase):
    def test_inbound_hard_settlement_with_target_sub_account_id(
        self, mock_send_posting_instruction_batch
    ):
        mock_send_posting_instruction_batch.return_value = "mock-pib-id"

        pib_id = postings_helper.inbound_hard_settlement(
            amount="1",
            account_id="acc-1",
            target_sub_account_id="sub-acc-1",
        )

        self.assertEqual(pib_id, "mock-pib-id")
        mock_send_posting_instruction_batch.assert_called_once()
        called_instructions = mock_send_posting_instruction_batch.call_args.kwargs["instructions"]
        self.assertEqual(len(called_instructions), 1)
        instruction = called_instructions[0]
        self.assertEqual(instruction.target_sub_account_id, "sub-acc-1")

    def test_outbound_hard_settlement_with_target_sub_account_id(
        self, mock_send_posting_instruction_batch
    ):
        mock_send_posting_instruction_batch.return_value = "mock-pib-id"

        pib_id = postings_helper.outbound_hard_settlement(
            amount="1",
            account_id="acc-1",
            target_sub_account_id="sub-acc-1",
        )

        self.assertEqual(pib_id, "mock-pib-id")
        mock_send_posting_instruction_batch.assert_called_once()
        called_instructions = mock_send_posting_instruction_batch.call_args.kwargs["instructions"]
        self.assertEqual(len(called_instructions), 1)
        instruction = called_instructions[0]
        self.assertEqual(instruction.target_sub_account_id, "sub-acc-1")

    def test_inbound_auth_with_target_sub_account_id(self, mock_send_posting_instruction_batch):
        mock_send_posting_instruction_batch.return_value = "mock-pib-id"

        pib_id = postings_helper.inbound_auth(
            amount="1",
            account_id="acc-1",
            target_sub_account_id="sub-acc-1",
        )

        self.assertEqual(pib_id, "mock-pib-id")
        mock_send_posting_instruction_batch.assert_called_once()
        called_instructions = mock_send_posting_instruction_batch.call_args.kwargs["instructions"]
        self.assertEqual(len(called_instructions), 1)
        instruction = called_instructions[0]
        self.assertEqual(instruction.target_sub_account_id, "sub-acc-1")

    def test_outbound_auth_with_target_sub_account_id(self, mock_send_posting_instruction_batch):
        mock_send_posting_instruction_batch.return_value = "mock-pib-id"

        pib_id = postings_helper.outbound_auth(
            amount="1",
            account_id="acc-1",
            target_sub_account_id="sub-acc-1",
        )

        self.assertEqual(pib_id, "mock-pib-id")
        mock_send_posting_instruction_batch.assert_called_once()
        called_instructions = mock_send_posting_instruction_batch.call_args.kwargs["instructions"]
        self.assertEqual(len(called_instructions), 1)
        instruction = called_instructions[0]
        self.assertEqual(instruction.target_sub_account_id, "sub-acc-1")

    def test_create_transfer_with_sub_account_ids(self, mock_send_posting_instruction_batch):
        mock_send_posting_instruction_batch.return_value = "mock-pib-id"

        postings_helper.create_transfer(
            amount="1",
            debtor_target_account_id="debtor-acc-1",
            creditor_target_account_id="creditor-acc-1",
            debtor_target_sub_account_id="debtor-sub-acc-1",
            creditor_target_sub_account_id="creditor-sub-acc-1",
        )

        mock_send_posting_instruction_batch.assert_called_once()
        called_instructions = mock_send_posting_instruction_batch.call_args.args[0]
        self.assertEqual(len(called_instructions), 1)
        instruction = called_instructions[0]
        self.assertEqual(instruction.debtor_target_sub_account_id, "debtor-sub-acc-1")
        self.assertEqual(instruction.creditor_target_sub_account_id, "creditor-sub-acc-1")
