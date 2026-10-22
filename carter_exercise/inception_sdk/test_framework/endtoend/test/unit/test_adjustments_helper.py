# standard libs
import json
from unittest import TestCase
from unittest.mock import ANY, MagicMock, PropertyMock, patch, sentinel

# inception sdk
import inception_sdk.test_framework.endtoend as endtoend
import inception_sdk.vault.core_api as core_api
from inception_sdk.common.python.file_utils import load_file_contents
from inception_sdk.common.test.mocks.kafka import MockConsumer, MockMessage
from inception_sdk.test_framework.endtoend import adjustments_helper
from inception_sdk.vault.core_api import (
    AdjustmentError,
    AdjustmentsRetryRequest,
    BulkRetryAdjustmentsRequest,
    BulkRetryAdjustmentsResponse,
    ErrorCode,
    ListAdjustmentsRequest,
)

adjustment_event_input_path = "inception_sdk/test_framework/endtoend/test/unit/input/"
CREATED_EVENT_NO_ADJUSTMENT_REQUIRED = load_file_contents(
    f"{adjustment_event_input_path}/adjustment_created_event_no_adjustment_required.json"
)
CREATED_EVENT_RUNNING = load_file_contents(
    f"{adjustment_event_input_path}/adjustment_created_event_running.json"
)
UPDATED_EVENT_COMPLETED = load_file_contents(
    f"{adjustment_event_input_path}/adjustment_updated_event_completed.json"
)


@patch.object(endtoend.core_api_helper, "list_all")
class ListAllAdjustmentsTest(TestCase):
    def test_list_all_adjustments_with_account_ids(self, mock_list_all: MagicMock):
        mock_list_all.return_value = [sentinel.adjustment_1, sentinel.adjustment_2]
        response = adjustments_helper.list_all_adjustments(account_ids=["id1", "id2", "id3"])

        self.assertEqual(response, [sentinel.adjustment_1, sentinel.adjustment_2])
        mock_list_all.assert_called_once_with(
            list_api_call=endtoend.core_api_helper.list_adjustments,
            request=ListAdjustmentsRequest(
                page_size=100, account_ids=["id1", "id2", "id3"], schedule_job_ids=None
            ),
            element_retriever=ANY,
        )

    def test_list_all_adjustments_with_schedule_job_ids(self, mock_list_all: MagicMock):
        mock_list_all.return_value = [sentinel.adjustment_1, sentinel.adjustment_2]
        response = adjustments_helper.list_all_adjustments(schedule_job_ids=["id1", "id2", "id3"])

        self.assertEqual(response, [sentinel.adjustment_1, sentinel.adjustment_2])
        mock_list_all.assert_called_once_with(
            list_api_call=endtoend.core_api_helper.list_adjustments,
            request=ListAdjustmentsRequest(
                page_size=100, account_ids=None, schedule_job_ids=["id1", "id2", "id3"]
            ),
            element_retriever=ANY,
        )


@patch.object(endtoend.adjustments_helper.uuid, "uuid4")
@patch.object(endtoend.core_api_helper, "bulk_retry_adjustments")
class BulkRetryAdjustmentsTest(TestCase):
    def test_retry_successful(self, mock_bulk_retry_adjustments: MagicMock, mock_uuid4: MagicMock):
        mock_uuid4.side_effect = ["uuid_1", "uuid_2", "uuid_3"]
        mock_bulk_retry_adjustments.return_value = BulkRetryAdjustmentsResponse(errors={})
        response = adjustments_helper.bulk_retry_adjustments(retry_ids=["id1", "id2", "id3"])

        self.assertIsInstance(response, BulkRetryAdjustmentsResponse)
        self.assertDictEqual(response.errors, {})
        mock_bulk_retry_adjustments.assert_called_once_with(
            request=BulkRetryAdjustmentsRequest(
                retry_requests=[
                    AdjustmentsRetryRequest(
                        request_id="uuid_1",
                        id="id1",
                    ),
                    AdjustmentsRetryRequest(
                        request_id="uuid_2",
                        id="id2",
                    ),
                    AdjustmentsRetryRequest(
                        request_id="uuid_3",
                        id="id3",
                    ),
                ]
            )
        )

    def test_retry_adjustment_error_persists(
        self, mock_bulk_retry_adjustments: MagicMock, mock_uuid4: MagicMock
    ):
        mock_uuid4.side_effect = ["uuid_1", "uuid_2", "uuid_3"]
        mock_bulk_retry_adjustments.return_value = BulkRetryAdjustmentsResponse(
            errors={
                "id1": AdjustmentError(
                    message="something happened",
                    code=ErrorCode.FAILED_PRECONDITION,
                )
            },
        )
        response = adjustments_helper.bulk_retry_adjustments(retry_ids=["id1", "id2", "id3"])

        self.assertIsInstance(response, BulkRetryAdjustmentsResponse)
        self.assertDictEqual(
            response.errors,
            {
                "id1": AdjustmentError(
                    message="something happened", code=ErrorCode.FAILED_PRECONDITION, details=None
                ),
            },
        )
        mock_bulk_retry_adjustments.assert_called_once_with(
            request=BulkRetryAdjustmentsRequest(
                retry_requests=[
                    AdjustmentsRetryRequest(
                        request_id="uuid_1",
                        id="id1",
                    ),
                    AdjustmentsRetryRequest(
                        request_id="uuid_2",
                        id="id2",
                    ),
                    AdjustmentsRetryRequest(
                        request_id="uuid_3",
                        id="id3",
                    ),
                ]
            )
        )


class WaitForAdjustmentEventTest(TestCase):
    @patch.object(endtoend, "testhandle")
    def test_wait_for_adjustment_event_matches(self, mock_testhandle):
        type(mock_testhandle).kafka_consumers = PropertyMock(
            return_value={
                adjustments_helper.ADJUSTMENTS_EVENT_TOPIC: MockConsumer(
                    [MockMessage(value=CREATED_EVENT_NO_ADJUSTMENT_REQUIRED)]
                )
            }
        )

        result = adjustments_helper.wait_for_adjustment_event(
            account_id="account_id",
            target_status=core_api.AdjustmentStatus.NO_ADJUSTMENT_REQUIRED,
        )

        self.assertIsNone(result)

    @patch.object(endtoend, "testhandle")
    def test_wait_for_adjustment_event_no_match_incorrect_event_json(self, mock_testhandle):
        type(mock_testhandle).kafka_consumers = PropertyMock(
            return_value={
                adjustments_helper.ADJUSTMENTS_EVENT_TOPIC: MockConsumer(
                    [
                        MockMessage(
                            value=json.dumps(
                                {"event_id": "event_id", "adjustment_unknown_key": "value"}
                            )
                        )
                    ]
                )
            }
        )

        with self.assertRaises(Exception) as e:
            adjustments_helper.wait_for_adjustment_event(
                account_id="account_id",
                target_status=core_api.AdjustmentStatus.COMPLETED,
                # force short timeouts since mocking the events on the consumer
                inter_message_timeout=1,
                matched_message_timeout=1,
            )

        self.assertEqual(
            e.exception.args[0],
            f"Did not see {core_api.AdjustmentStatus.COMPLETED.value} for account_id='account_id'",
        )

    @patch.object(endtoend, "testhandle")
    def test_wait_for_adjustment_event_no_match_different_status(self, mock_testhandle):
        type(mock_testhandle).kafka_consumers = PropertyMock(
            return_value={
                adjustments_helper.ADJUSTMENTS_EVENT_TOPIC: MockConsumer(
                    [MockMessage(value=CREATED_EVENT_RUNNING)]
                )
            }
        )

        with self.assertRaises(Exception) as e:
            adjustments_helper.wait_for_adjustment_event(
                account_id="account_id",
                target_status=core_api.AdjustmentStatus.COMPLETED,
                # force short timeouts since mocking the events on the consumer
                inter_message_timeout=1,
                matched_message_timeout=1,
            )

        self.assertEqual(
            e.exception.args[0],
            f"Did not see {core_api.AdjustmentStatus.COMPLETED.value} for account_id='account_id'",
        )

    @patch.object(endtoend, "testhandle")
    def test_wait_for_adjustment_event_no_match_different_account_id(self, mock_testhandle):
        type(mock_testhandle).kafka_consumers = PropertyMock(
            return_value={
                adjustments_helper.ADJUSTMENTS_EVENT_TOPIC: MockConsumer(
                    [MockMessage(value=CREATED_EVENT_RUNNING)]
                )
            }
        )

        with self.assertRaises(Exception) as e:
            adjustments_helper.wait_for_adjustment_event(
                account_id="another_account_id",
                target_status=core_api.AdjustmentStatus.COMPLETED,
                # force short timeouts since mocking the events on the consumer
                inter_message_timeout=1,
                matched_message_timeout=1,
            )

        self.assertEqual(
            e.exception.args[0],
            f"Did not see {core_api.AdjustmentStatus.COMPLETED.value} for "
            "account_id='another_account_id'",
        )

    @patch.object(endtoend, "testhandle")
    def test_wait_for_adjustment_event_different_terminal_status(self, mock_testhandle):
        type(mock_testhandle).kafka_consumers = PropertyMock(
            return_value={
                adjustments_helper.ADJUSTMENTS_EVENT_TOPIC: MockConsumer(
                    [MockMessage(value=CREATED_EVENT_NO_ADJUSTMENT_REQUIRED)]
                )
            }
        )

        with self.assertRaises(Exception) as e:
            adjustments_helper.wait_for_adjustment_event(
                account_id="account_id",
                target_status=core_api.AdjustmentStatus.COMPLETED,
                # force short timeouts since mocking the events on the consumer
                inter_message_timeout=1,
                matched_message_timeout=1,
            )

        self.assertEqual(
            e.exception.args[0],
            "Adjustment entered terminal status "
            f"{core_api.AdjustmentStatus.NO_ADJUSTMENT_REQUIRED.value} and never reached target"
            f" status {core_api.AdjustmentStatus.COMPLETED.value} for account_id='account_id'",
        )

    @patch.object(endtoend, "testhandle")
    def test_wait_for_adjustment_event_with_count_matches(self, mock_testhandle):
        type(mock_testhandle).kafka_consumers = PropertyMock(
            return_value={
                adjustments_helper.ADJUSTMENTS_EVENT_TOPIC: MockConsumer(
                    [MockMessage(value=CREATED_EVENT_NO_ADJUSTMENT_REQUIRED)]
                )
            }
        )

        result = adjustments_helper.wait_for_adjustment_event(
            account_id="account_id",
            target_status=core_api.AdjustmentStatus.NO_ADJUSTMENT_REQUIRED,
            target_resource_adjustment_count=1,
        )

        self.assertIsNone(result)

    @patch.object(endtoend, "testhandle")
    def test_wait_for_adjustment_event_with_count_no_match_different_status(self, mock_testhandle):
        type(mock_testhandle).kafka_consumers = PropertyMock(
            return_value={
                adjustments_helper.ADJUSTMENTS_EVENT_TOPIC: MockConsumer(
                    [MockMessage(value=CREATED_EVENT_RUNNING)]
                )
            }
        )

        with self.assertRaises(Exception) as e:
            adjustments_helper.wait_for_adjustment_event(
                account_id="account_id",
                target_status=core_api.AdjustmentStatus.COMPLETED,
                target_resource_adjustment_count=2,
                # force short timeouts since mocking the events on the consumer
                inter_message_timeout=1,
                matched_message_timeout=1,
            )

        self.assertEqual(
            e.exception.args[0],
            f"Did not see {core_api.AdjustmentStatus.COMPLETED.value} for account_id='account_id'"
            " with target_resource_adjustment_count=2",
        )

    @patch.object(endtoend, "testhandle")
    def test_wait_for_adjustment_event_with_count_no_match_different_count(self, mock_testhandle):
        type(mock_testhandle).kafka_consumers = PropertyMock(
            return_value={
                adjustments_helper.ADJUSTMENTS_EVENT_TOPIC: MockConsumer(
                    [MockMessage(value=CREATED_EVENT_RUNNING)]
                )
            }
        )

        with self.assertRaises(Exception) as e:
            adjustments_helper.wait_for_adjustment_event(
                account_id="account_id",
                target_status=core_api.AdjustmentStatus.RUNNING,
                # the example event has resource_adjustment_count=2
                target_resource_adjustment_count=1,
                # force short timeouts since mocking the events on the consumer
                inter_message_timeout=1,
                matched_message_timeout=1,
            )

        self.assertEqual(
            e.exception.args[0],
            f"Did not see {core_api.AdjustmentStatus.RUNNING.value} for account_id='account_id'"
            " with target_resource_adjustment_count=1",
        )

    @patch.object(endtoend, "testhandle")
    def test_wait_for_adjustment_event_with_count_different_terminal_status(self, mock_testhandle):
        type(mock_testhandle).kafka_consumers = PropertyMock(
            return_value={
                adjustments_helper.ADJUSTMENTS_EVENT_TOPIC: MockConsumer(
                    [MockMessage(value=CREATED_EVENT_NO_ADJUSTMENT_REQUIRED)]
                )
            }
        )

        with self.assertRaises(Exception) as e:
            adjustments_helper.wait_for_adjustment_event(
                account_id="account_id",
                target_status=core_api.AdjustmentStatus.COMPLETED,
                target_resource_adjustment_count=1,
                # force short timeouts since mocking the events on the consumer
                inter_message_timeout=1,
                matched_message_timeout=1,
            )

        self.assertEqual(
            e.exception.args[0],
            "Adjustment entered terminal status "
            f"{core_api.AdjustmentStatus.NO_ADJUSTMENT_REQUIRED.value} and never reached target"
            f" status {core_api.AdjustmentStatus.COMPLETED.value}"
            f" for account_id='account_id' with target_resource_adjustment_count=1",
        )


class GetCorrectionPibsTest(TestCase):
    @patch.object(endtoend.core_api_helper, "list_adjustments")
    def test_get_correction_pibs_no_adjustments(self, mock_list_adjustments: MagicMock):
        mock_response = MagicMock()
        mock_response.adjustments = []
        mock_list_adjustments.return_value = mock_response

        with self.assertRaises(ValueError) as ctx:
            adjustments_helper.get_correction_posting_instruction_batches(account_id="account_1")
        self.assertEqual(
            str(ctx.exception),
            "Could not find any adjustments for account_id=account_1",
        )
        mock_list_adjustments.assert_called_once_with(
            request=ListAdjustmentsRequest(
                account_ids=["account_1"],
                page_size=1,
            )
        )

    @patch.object(adjustments_helper, "list_all_adjustments")
    def test_get_correction_pibs_count_mismatch(self, mock_list_all_adjustments: MagicMock):
        mock_adj_1 = MagicMock(spec=core_api.Adjustment)
        mock_adj_1.resource_adjustment_count = 1
        mock_adj_2 = MagicMock(spec=core_api.Adjustment)
        mock_adj_2.resource_adjustment_count = 2

        mock_list_all_adjustments.return_value = [mock_adj_2, mock_adj_1]

        with self.assertRaises(ValueError) as ctx:
            adjustments_helper.get_correction_posting_instruction_batches(
                account_id="account_1", resource_adjustment_count=3
            )
        self.assertEqual(
            str(ctx.exception),
            "Could not find adjustment with resource_adjustment_count=3 for account_id=account_1",
        )
        mock_list_all_adjustments.assert_called_once_with(
            account_ids=["account_1"],
            schedule_job_ids=None,
        )

    @patch.object(endtoend.core_api_helper, "list_adjustments")
    def test_get_correction_pibs_no_pib_ids(self, mock_list_adjustments: MagicMock):
        mock_adj = MagicMock(spec=core_api.Adjustment)
        mock_adj.resource_adjustment_count = 1
        mock_adj.correction_posting_instruction_batch_ids = None

        mock_response = MagicMock()
        mock_response.adjustments = [mock_adj]
        mock_list_adjustments.return_value = mock_response

        result = adjustments_helper.get_correction_posting_instruction_batches(
            account_id="account_1"
        )
        self.assertEqual(result, [])
        mock_list_adjustments.assert_called_once_with(
            request=ListAdjustmentsRequest(
                account_ids=["account_1"],
                page_size=1,
            )
        )

    @patch.object(adjustments_helper, "list_all_adjustments")
    def test_get_correction_pibs_with_count_no_adjustments(
        self, mock_list_all_adjustments: MagicMock
    ):
        mock_list_all_adjustments.return_value = []

        with self.assertRaises(ValueError) as ctx:
            adjustments_helper.get_correction_posting_instruction_batches(
                account_id="account_1", resource_adjustment_count=1
            )
        self.assertEqual(
            str(ctx.exception),
            "Could not find any adjustments for account_id=account_1",
        )
        mock_list_all_adjustments.assert_called_once_with(
            account_ids=["account_1"],
            schedule_job_ids=None,
        )

    @patch.object(endtoend.postings_helper, "batch_get_posting_instruction_batches")
    @patch.object(endtoend.core_api_helper, "list_adjustments")
    def test_get_correction_pibs_default_latest(
        self, mock_list_adjustments: MagicMock, mock_batch_get: MagicMock
    ):
        mock_adj_1 = MagicMock(spec=core_api.Adjustment)
        mock_adj_1.resource_adjustment_count = 1
        mock_adj_1.correction_posting_instruction_batch_ids = ["pib_1"]

        mock_adj_2 = MagicMock(spec=core_api.Adjustment)
        mock_adj_2.resource_adjustment_count = 2
        mock_adj_2.correction_posting_instruction_batch_ids = ["pib_2"]

        mock_response = MagicMock()
        mock_response.adjustments = [mock_adj_2, mock_adj_1]
        mock_list_adjustments.return_value = mock_response

        mock_pib_2 = sentinel.pib_2
        mock_batch_get_response = MagicMock()
        mock_batch_get_response.posting_instruction_batches = {"pib_2": mock_pib_2}
        mock_batch_get.return_value = mock_batch_get_response

        result = adjustments_helper.get_correction_posting_instruction_batches(
            account_id="account_1"
        )
        self.assertEqual(result, [mock_pib_2])
        mock_list_adjustments.assert_called_once_with(
            request=ListAdjustmentsRequest(
                account_ids=["account_1"],
                page_size=1,
            )
        )
        mock_batch_get.assert_called_once_with(ids=["pib_2"])

    @patch.object(endtoend.postings_helper, "batch_get_posting_instruction_batches")
    @patch.object(adjustments_helper, "list_all_adjustments")
    def test_get_correction_pibs_for_adjustment_count(
        self, mock_list_all_adjustments: MagicMock, mock_batch_get: MagicMock
    ):
        mock_adj_1 = MagicMock(spec=core_api.Adjustment)
        mock_adj_1.resource_adjustment_count = 1
        mock_adj_1.correction_posting_instruction_batch_ids = ["pib_a", "pib_b", "pib_c"]

        mock_adj_2 = MagicMock(spec=core_api.Adjustment)
        mock_adj_2.resource_adjustment_count = 2
        mock_adj_2.correction_posting_instruction_batch_ids = ["pib_x"]

        mock_list_all_adjustments.return_value = [mock_adj_2, mock_adj_1]

        mock_pib_a = sentinel.pib_a
        mock_pib_b = sentinel.pib_b
        mock_pib_c = sentinel.pib_c
        mock_response = MagicMock()
        mock_response.posting_instruction_batches = {
            "pib_a": mock_pib_a,
            "pib_b": mock_pib_b,
            "pib_c": mock_pib_c,
        }
        mock_batch_get.return_value = mock_response

        result = adjustments_helper.get_correction_posting_instruction_batches(
            account_id="account_1", resource_adjustment_count=1
        )
        self.assertEqual(result, [mock_pib_a, mock_pib_b, mock_pib_c])
        mock_batch_get.assert_called_once_with(ids=["pib_a", "pib_b", "pib_c"])
