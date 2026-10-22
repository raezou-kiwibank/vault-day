# Copyright @ 2026 Thought Machine Group Limited. All rights reserved.
# standard libs
import json
from datetime import datetime
from unittest import TestCase
from unittest.mock import ANY, MagicMock, PropertyMock, patch, sentinel
from zoneinfo import ZoneInfo

# inception sdk
import inception_sdk.test_framework.endtoend as endtoend
import inception_sdk.vault.core_api as core_api
from inception_sdk.common.test.mocks.kafka import MockConsumer, MockMessage
from inception_sdk.test_framework.endtoend import sub_accounts_helper

SUB_ACCOUNT_CREATED_EVENT_OPENING = json.dumps(
    {
        "event_id": "created_event_opening",
        "timestamp": "2026-01-01T00:00:00.000002Z",
        "change_id": 0,
        "sub_account_created": {
            "sub_account": {
                "id": "sub_account_1",
                "type": "SPEND",
                "name": "spending pot",
                "details": {"example detail": "example value"},
                "activation_timestamp": "2026-01-01T00:00:00.000000Z",
                "create_timestamp": "2026-01-01T00:00:00.000001Z",
                "update_timestamp": "2026-01-01T00:00:00.000001Z",
                "status": "SUB_ACCOUNT_STATUS_OPENING",
                "account_id": "account_1",
                "close_timestamp": None,
            }
        },
    }
)

SUB_ACCOUNT_UPDATED_EVENT_CANCELLED = json.dumps(
    {
        "event_id": "updated_event_cancelled",
        "timestamp": "2026-01-02T00:00:00.000002Z",
        "change_id": 1,
        "sub_account_updated": {
            "sub_account": {
                "id": "sub_account_1",
                "type": "SPEND",
                "name": "example spending pot",
                "details": {"example detail": "example value"},
                "activation_timestamp": "2026-01-01T00:00:00.000000Z",
                "create_timestamp": "2026-01-01T00:00:00.000001Z",
                "update_timestamp": "2026-01-02T00:00:00.000001Z",
                "status": "SUB_ACCOUNT_STATUS_CANCELLED",
                "account_id": "account_1",
                "close_timestamp": None,
            },
            "update_mask": {"paths": ["status", "update_timestamp"]},
            "error": None,
        },
    }
)


SUB_ACCOUNT_UPDATED_EVENT_OPEN = json.dumps(
    {
        "event_id": "updated_event_open",
        "timestamp": "2026-01-02T00:00:00.000002Z",
        "change_id": 1,
        "sub_account_updated": {
            "sub_account": {
                "id": "sub_account_1",
                "type": "SPEND",
                "name": "example spending pot",
                "details": {"example detail": "example value"},
                "activation_timestamp": "2026-01-01T00:00:00.000000Z",
                "create_timestamp": "2026-01-01T00:00:00.000001Z",
                "update_timestamp": "2026-01-02T00:00:00.000001Z",
                "status": "SUB_ACCOUNT_STATUS_OPEN",
                "account_id": "account_1",
                "close_timestamp": None,
            },
            "update_mask": {"paths": ["status", "update_timestamp"]},
            "error": None,
        },
    }
)

SUB_ACCOUNT_UPDATED_EVENT_CLOSED = json.dumps(
    {
        "event_id": "updated_event_closed",
        "timestamp": "2026-01-03T00:00:00.000002Z",
        "change_id": 3,
        "sub_account_updated": {
            "sub_account": {
                "id": "sub_account_1",
                "type": "SPEND",
                "name": "example spending pot",
                "details": {"example detail": "example value"},
                "activation_timestamp": "2026-01-01T00:00:00.000000Z",
                "create_timestamp": "2026-01-01T00:00:00.000001Z",
                "update_timestamp": "2026-01-03T00:00:00.000001Z",
                "status": "SUB_ACCOUNT_STATUS_CLOSED",
                "account_id": "account_1",
                "close_timestamp": "2026-01-03T00:00:00.000001Z",
            }
        },
        "update_mask": {"paths": ["status", "update_timestamp", "close_timestamp"]},
        "error": None,
    }
)

SUB_ACCOUNT_UNRELATED_EVENT = json.dumps(
    {
        "event_id": "unrelated_event",
        "timestamp": "2026-01-01T00:00:00.000002Z",
        "change_id": 0,
        "some_other_event": {},
    }
)


@patch.object(endtoend.core_api_helper, "list_all")
class ListAllSubAccountsTest(TestCase):
    def test_list_all_sub_accounts(self, mock_list_all: MagicMock):
        mock_list_all.return_value = [sentinel.sub_account]

        response = sub_accounts_helper.list_all_sub_accounts(
            account_id="account_1",
            status=core_api.SubAccountStatus.SUB_ACCOUNT_STATUS_OPEN,
            type="SPEND",
        )

        self.assertEqual(response, [sentinel.sub_account])
        mock_list_all.assert_called_once_with(
            list_api_call=endtoend.core_api_helper.list_sub_accounts,
            request=core_api.ListSubAccountsRequest(
                account_id="account_1",
                status=core_api.SubAccountStatus.SUB_ACCOUNT_STATUS_OPEN,
                type="SPEND",
                page_size=100,
                page_token=None,
            ),
            element_retriever=ANY,
        )


@patch.object(endtoend.helper, "send_request")
class BatchGetSubAccountsTest(TestCase):
    def test_batch_get_sub_accounts(self, mock_send_request: MagicMock):
        mock_send_request.return_value = {
            "sub_accounts": {
                "sub_account_1": {
                    "id": "sub_account_1",
                    "type": "SPEND",
                    "name": "spending pot",
                    "status": "SUB_ACCOUNT_STATUS_OPEN",
                    "account_id": "account_1",
                    "activation_timestamp": "2026-01-01T00:00:00Z",
                    "details": None,
                }
            }
        }

        request = core_api.BatchGetSubAccountsRequest(ids=["sub_account_1"])
        response = sub_accounts_helper.batch_get_sub_accounts(request)

        self.assertIn("sub_account_1", response.sub_accounts)
        self.assertEqual(response.sub_accounts["sub_account_1"].id, "sub_account_1")
        mock_send_request.assert_called_once_with(
            "get",
            "/v1/sub-accounts:batchGet",
            params=request.model_dump(),
        )


@patch.object(endtoend.helper, "send_request")
class CreateSubAccountTest(TestCase):
    def test_create_sub_account(self, mock_send_request: MagicMock):
        mock_send_request.return_value = {
            "id": "sub_account_1",
            "type": "SPEND",
            "name": "spending pot",
            "status": "SUB_ACCOUNT_STATUS_OPEN",
            "account_id": "account_1",
            "activation_timestamp": "2026-01-01T00:00:00Z",
            "details": None,
        }

        request = core_api.CreateSubAccountRequest(
            sub_account=core_api.SubAccountCreateSubAccount(
                id="sub_account_1",
                type="SPEND",
                name="spending pot",
                status=core_api.SubAccountStatus.SUB_ACCOUNT_STATUS_OPEN,
                account_id="account_1",
            )
        )

        expected = core_api.SubAccount(
            id="sub_account_1",
            type="SPEND",
            name="spending pot",
            status=core_api.SubAccountStatus.SUB_ACCOUNT_STATUS_OPEN,
            account_id="account_1",
            details=None,
            activation_timestamp=datetime(2026, 1, 1, tzinfo=ZoneInfo("UTC")),
        )
        response = sub_accounts_helper.create_sub_account(request)

        self.assertEqual(expected, response)
        mock_send_request.assert_called_once_with(
            "post",
            "/v1/sub-accounts",
            data=request.model_dump_json(),
        )


class WaitForSubAccountEventTest(TestCase):
    def test_wait_for_sub_account_event_by_status_errors_when_both_ids_provided(self):
        with self.assertRaises(ValueError) as e:
            sub_accounts_helper.wait_for_sub_account_event_by_status(
                account_id="account_1",
                sub_account_id="sub_account_1",
                target_status=core_api.SubAccountStatus.SUB_ACCOUNT_STATUS_OPENING,
            )

        self.assertEqual(
            e.exception.args[0],
            "Cannot provide both 'sub_account_id' and 'account_id'.",
        )

    def test_wait_for_sub_account_event_by_status_errors_when_no_ids_provided(self):
        with self.assertRaises(ValueError) as e:
            sub_accounts_helper.wait_for_sub_account_event_by_status(
                target_status=core_api.SubAccountStatus.SUB_ACCOUNT_STATUS_OPENING,
            )

        self.assertEqual(
            e.exception.args[0],
            "Either `sub_account_id` or `account_id` must be provided.",
        )

    @patch.object(endtoend, "testhandle")
    def test_wait_for_sub_account_event_by_status_created_matches(self, mock_testhandle):
        type(mock_testhandle).kafka_consumers = PropertyMock(
            return_value={
                sub_accounts_helper.SUB_ACCOUNTS_EVENT_TOPIC: MockConsumer(
                    [MockMessage(value=SUB_ACCOUNT_CREATED_EVENT_OPENING)]
                )
            }
        )

        result = sub_accounts_helper.wait_for_sub_account_event_by_status(
            sub_account_id="sub_account_1",
            target_status=core_api.SubAccountStatus.SUB_ACCOUNT_STATUS_OPENING,
        )

        self.assertIsNone(result)

    @patch.object(endtoend, "testhandle")
    def test_wait_for_sub_account_event_by_status_updated_matches(self, mock_testhandle):
        type(mock_testhandle).kafka_consumers = PropertyMock(
            return_value={
                sub_accounts_helper.SUB_ACCOUNTS_EVENT_TOPIC: MockConsumer(
                    [MockMessage(value=SUB_ACCOUNT_UPDATED_EVENT_CLOSED)]
                )
            }
        )

        result = sub_accounts_helper.wait_for_sub_account_event_by_status(
            sub_account_id="sub_account_1",
            target_status=core_api.SubAccountStatus.SUB_ACCOUNT_STATUS_CLOSED,
        )

        self.assertIsNone(result)

    @patch.object(endtoend, "testhandle")
    def test_wait_for_sub_account_event_by_status_no_match_different_status(self, mock_testhandle):
        type(mock_testhandle).kafka_consumers = PropertyMock(
            return_value={
                sub_accounts_helper.SUB_ACCOUNTS_EVENT_TOPIC: MockConsumer(
                    [MockMessage(value=SUB_ACCOUNT_UPDATED_EVENT_OPEN)]
                )
            }
        )

        with self.assertRaises(Exception) as e:
            sub_accounts_helper.wait_for_sub_account_event_by_status(
                sub_account_id="sub_account_1",
                target_status=core_api.SubAccountStatus.SUB_ACCOUNT_STATUS_CANCELLED,
                inter_message_timeout_seconds=1,
                matched_message_timeout_seconds=1,
            )

        self.assertEqual(
            e.exception.args[0],
            "Did not see SUB_ACCOUNT_STATUS_CANCELLED for sub_account_id='sub_account_1'",
        )

    @patch.object(endtoend, "testhandle")
    def test_wait_for_sub_account_event_by_status_no_match_different_sub_account_id(
        self, mock_testhandle
    ):
        type(mock_testhandle).kafka_consumers = PropertyMock(
            return_value={
                sub_accounts_helper.SUB_ACCOUNTS_EVENT_TOPIC: MockConsumer(
                    [MockMessage(value=SUB_ACCOUNT_CREATED_EVENT_OPENING)]
                )
            }
        )

        with self.assertRaises(Exception) as e:
            sub_accounts_helper.wait_for_sub_account_event_by_status(
                sub_account_id="sub_account_2",
                target_status=core_api.SubAccountStatus.SUB_ACCOUNT_STATUS_OPEN,
                inter_message_timeout_seconds=1,
                matched_message_timeout_seconds=1,
            )

        self.assertEqual(
            e.exception.args[0],
            "Did not see SUB_ACCOUNT_STATUS_OPEN for sub_account_id='sub_account_2'",
        )

    @patch.object(endtoend, "testhandle")
    def test_wait_for_sub_account_event_by_status_terminal_status_cancelled_error(
        self, mock_testhandle
    ):
        type(mock_testhandle).kafka_consumers = PropertyMock(
            return_value={
                sub_accounts_helper.SUB_ACCOUNTS_EVENT_TOPIC: MockConsumer(
                    [MockMessage(value=SUB_ACCOUNT_UPDATED_EVENT_CANCELLED)]
                )
            }
        )

        with self.assertRaises(Exception) as e:
            sub_accounts_helper.wait_for_sub_account_event_by_status(
                sub_account_id="sub_account_1",
                target_status=core_api.SubAccountStatus.SUB_ACCOUNT_STATUS_OPEN,
            )

        self.assertEqual(
            e.exception.args[0],
            "Sub-Account entered terminal status SUB_ACCOUNT_STATUS_CANCELLED "
            "and never reached target status SUB_ACCOUNT_STATUS_OPEN "
            "for sub_account_id='sub_account_1'",
        )

    @patch.object(endtoend, "testhandle")
    def test_wait_for_sub_account_event_by_status_terminal_status_closed_error(
        self, mock_testhandle
    ):
        type(mock_testhandle).kafka_consumers = PropertyMock(
            return_value={
                sub_accounts_helper.SUB_ACCOUNTS_EVENT_TOPIC: MockConsumer(
                    [MockMessage(value=SUB_ACCOUNT_UPDATED_EVENT_CLOSED)]
                )
            }
        )

        with self.assertRaises(Exception) as e:
            sub_accounts_helper.wait_for_sub_account_event_by_status(
                sub_account_id="sub_account_1",
                target_status=core_api.SubAccountStatus.SUB_ACCOUNT_STATUS_OPEN,
            )

        self.assertEqual(
            e.exception.args[0],
            "Sub-Account entered terminal status SUB_ACCOUNT_STATUS_CLOSED "
            "and never reached target status SUB_ACCOUNT_STATUS_OPEN "
            "for sub_account_id='sub_account_1'",
        )

    @patch.object(endtoend, "testhandle")
    def test_wait_for_sub_account_event_by_status_account_id_matches(self, mock_testhandle):
        type(mock_testhandle).kafka_consumers = PropertyMock(
            return_value={
                sub_accounts_helper.SUB_ACCOUNTS_EVENT_TOPIC: MockConsumer(
                    [MockMessage(value=SUB_ACCOUNT_CREATED_EVENT_OPENING)]
                )
            }
        )

        result = sub_accounts_helper.wait_for_sub_account_event_by_status(
            account_id="account_1",
            target_status=core_api.SubAccountStatus.SUB_ACCOUNT_STATUS_OPENING,
        )

        self.assertIsNone(result)

    @patch.object(endtoend, "testhandle")
    def test_wait_for_sub_account_event_by_status_account_id_no_match(self, mock_testhandle):
        type(mock_testhandle).kafka_consumers = PropertyMock(
            return_value={
                sub_accounts_helper.SUB_ACCOUNTS_EVENT_TOPIC: MockConsumer(
                    [MockMessage(value=SUB_ACCOUNT_CREATED_EVENT_OPENING)]
                )
            }
        )

        with self.assertRaises(Exception) as e:
            sub_accounts_helper.wait_for_sub_account_event_by_status(
                account_id="different_account_id",
                target_status=core_api.SubAccountStatus.SUB_ACCOUNT_STATUS_OPENING,
                inter_message_timeout_seconds=1,
                matched_message_timeout_seconds=1,
            )

        self.assertEqual(
            e.exception.args[0],
            "Did not see SUB_ACCOUNT_STATUS_OPENING for account_id='different_account_id'",
        )

    @patch.object(endtoend, "testhandle")
    def test_wait_for_sub_account_event_by_status_account_id_terminal_status_cancelled_error(
        self, mock_testhandle
    ):
        type(mock_testhandle).kafka_consumers = PropertyMock(
            return_value={
                sub_accounts_helper.SUB_ACCOUNTS_EVENT_TOPIC: MockConsumer(
                    [MockMessage(value=SUB_ACCOUNT_UPDATED_EVENT_CANCELLED)]
                )
            }
        )

        with self.assertRaises(Exception) as e:
            sub_accounts_helper.wait_for_sub_account_event_by_status(
                account_id="account_1",
                target_status=core_api.SubAccountStatus.SUB_ACCOUNT_STATUS_OPENING,
                inter_message_timeout_seconds=1,
                matched_message_timeout_seconds=1,
            )

        self.assertEqual(
            e.exception.args[0],
            "Sub-Account entered terminal status SUB_ACCOUNT_STATUS_CANCELLED "
            "and never reached target status SUB_ACCOUNT_STATUS_OPENING "
            "for account_id='account_1'",
        )

    @patch.object(endtoend, "testhandle")
    def test_wait_for_sub_account_event_by_status_account_id_terminal_status_closed_error(
        self, mock_testhandle
    ):
        type(mock_testhandle).kafka_consumers = PropertyMock(
            return_value={
                sub_accounts_helper.SUB_ACCOUNTS_EVENT_TOPIC: MockConsumer(
                    [MockMessage(value=SUB_ACCOUNT_UPDATED_EVENT_CLOSED)]
                )
            }
        )

        with self.assertRaises(Exception) as e:
            sub_accounts_helper.wait_for_sub_account_event_by_status(
                account_id="account_1",
                target_status=core_api.SubAccountStatus.SUB_ACCOUNT_STATUS_OPENING,
                inter_message_timeout_seconds=1,
                matched_message_timeout_seconds=1,
            )

        self.assertEqual(
            e.exception.args[0],
            "Sub-Account entered terminal status SUB_ACCOUNT_STATUS_CLOSED "
            "and never reached target status SUB_ACCOUNT_STATUS_OPENING "
            "for account_id='account_1'",
        )

    @patch.object(endtoend, "testhandle")
    def test_wait_for_sub_account_event_by_status_no_match_unrelated_event(self, mock_testhandle):
        type(mock_testhandle).kafka_consumers = PropertyMock(
            return_value={
                sub_accounts_helper.SUB_ACCOUNTS_EVENT_TOPIC: MockConsumer(
                    [MockMessage(value=SUB_ACCOUNT_UNRELATED_EVENT)]
                )
            }
        )

        with self.assertRaises(Exception) as e:
            sub_accounts_helper.wait_for_sub_account_event_by_status(
                sub_account_id="sub_account_1",
                target_status=core_api.SubAccountStatus.SUB_ACCOUNT_STATUS_OPEN,
                inter_message_timeout_seconds=1,
                matched_message_timeout_seconds=1,
            )

        self.assertEqual(
            e.exception.args[0],
            "Did not see SUB_ACCOUNT_STATUS_OPEN for sub_account_id='sub_account_1'",
        )
