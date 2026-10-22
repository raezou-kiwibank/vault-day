# Copyright @ 2026 Thought Machine Group Limited. All rights reserved.
# standard libs
import logging
import os
from typing import Optional, overload

# inception sdk
import inception_sdk.test_framework.endtoend as endtoend
import inception_sdk.vault.core_api as core_api
from inception_sdk.test_framework.endtoend.core_api_helper import list_sub_accounts  # noqa: F401
from inception_sdk.test_framework.endtoend.kafka_helper import kafka_only_helper, wait_for_messages

SUB_ACCOUNTS_EVENT_TOPIC = "vault.core_api.v1.accounts.sub_account.events"

TERMINAL_SUB_ACCOUNT_STATUSES = {
    core_api.SubAccountStatus.SUB_ACCOUNT_STATUS_CANCELLED.value,
    core_api.SubAccountStatus.SUB_ACCOUNT_STATUS_CLOSED.value,
}

log = logging.getLogger(__name__)
logging.basicConfig(
    level=os.environ.get("LOGLEVEL", "INFO"),
    format="%(asctime)s.%(msecs)03d - %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


def list_all_sub_accounts(
    account_id: str,
    status: core_api.SubAccountStatus | None = None,
    type: str | None = None,
) -> list[core_api.SubAccount]:
    """
    Lists and filters Sub-Accounts using the Sub-Accounts endpoint and retrieves all pages.

    :param account_id: the parent Account ID to filter by.
    :param status: optionally filter by Sub-Account status.
    :param type: optionally filter by Sub-Account type.
    :return: list of Sub-Accounts
    """
    return endtoend.core_api_helper.list_all(
        list_api_call=endtoend.core_api_helper.list_sub_accounts,
        request=core_api.ListSubAccountsRequest(
            account_id=account_id,
            status=status,
            type=type,
            page_size=100,
            page_token=None,
        ),
        element_retriever=lambda r: [sub_account for sub_account in r.sub_accounts],
    )


def batch_get_sub_accounts(
    request: core_api.BatchGetSubAccountsRequest,
) -> core_api.BatchGetSubAccountsResponse:
    """
    Retrieves Sub-Accounts by their IDs.

    :param request: contains the filters for /v1/sub-accounts:batchGet
    :returns: dict from requested IDs to Sub-Accounts.
    """
    return endtoend.core_api_helper.batch_get_sub_accounts(request)


def create_sub_account(
    request: core_api.CreateSubAccountRequest,
) -> core_api.SubAccount:
    """
    Creates a new Sub-Account in Vault.

    :param request: the fields to create the Sub-Account with.
    :return: the newly created Sub-Account.
    """
    return core_api.SubAccount.model_validate(
        endtoend.helper.send_request(
            "post",
            "/v1/sub-accounts",
            data=request.model_dump_json(),
        )
    )


@overload
def wait_for_sub_account_event_by_status(
    *,
    sub_account_id: str,
    target_status: core_api.SubAccountStatus,
    inter_message_timeout_seconds: int = 90,
    matched_message_timeout_seconds: int = 90,
): ...


@overload
def wait_for_sub_account_event_by_status(
    *,
    account_id: str,
    target_status: core_api.SubAccountStatus,
    inter_message_timeout_seconds: int = 90,
    matched_message_timeout_seconds: int = 90,
): ...


@kafka_only_helper
def wait_for_sub_account_event_by_status(
    *,
    sub_account_id: Optional[str] = None,
    account_id: Optional[str] = None,
    target_status: core_api.SubAccountStatus,
    inter_message_timeout_seconds: int = 90,
    matched_message_timeout_seconds: int = 90,
):
    """
    Listens to the `vault.core_api.v1.accounts.sub_account.events` topic and waits
    until the provided Sub-Account ID or parent Account ID receives an event whose
    status equals `target_status`.
    Note that when calling this method multiple times to consume many Sub-Account events, the order
    in which this is called must be the same as the order in which the events are streamed out.

    :param sub_account_id: the Sub-Account ID to listen for.
    :param account_id: the parent Account ID to listen for.
    :param target_status: the expected SubAccountStatus to wait for.
    :param inter_message_timeout_seconds: maximum time to wait in seconds between receiving any
        messages from the consumer (0 for no timeout). Defaults to 90.
    :param matched_message_timeout_seconds: maximum time to wait in seconds between receiving
        matched messages from the consumer (0 for no timeout). Defaults to 90.
    """
    if sub_account_id and account_id:
        raise ValueError("Cannot provide both 'sub_account_id' and 'account_id'.")

    if sub_account_id is not None:
        identifier_str = f"{sub_account_id=}"
        unique_message_ids = {sub_account_id: None}
    elif account_id is not None:
        identifier_str = f"{account_id=}"
        unique_message_ids = {account_id: None}
    else:
        raise ValueError("Either `sub_account_id` or `account_id` must be provided.")

    consumer = endtoend.testhandle.kafka_consumers[SUB_ACCOUNTS_EVENT_TOPIC]

    def matcher(event_msg, unique_message_ids):
        """
        This will match on the:
        - `sub_account_created.sub_account.id` or `sub_account_updated.sub_account.id`
           when `sub_account_id` provided.
        - `sub_account_created.sub_account.account_id` or
          `sub_account_updated.sub_account.account_id` when `account_id` provided.
        """
        event_request_id = event_msg.get("event_id")
        wrapper = event_msg.get("sub_account_created") or event_msg.get("sub_account_updated")
        if not wrapper:
            return "", event_request_id, False

        sub_account = wrapper.get("sub_account")
        if sub_account_id is not None:
            event_sub_account_id = sub_account.get("id")
            if event_sub_account_id != sub_account_id:
                return "", event_request_id, False
        elif account_id is not None:
            event_account_id = sub_account.get("account_id")
            if event_account_id != account_id:

                return "", event_request_id, False

        status = sub_account.get("status")
        if status in TERMINAL_SUB_ACCOUNT_STATUSES and status != target_status.value:
            raise Exception(
                f"Sub-Account entered terminal status {status} "
                f"and never reached target status {target_status.value} "
                f"for {identifier_str}"
            )

        lookup_key = sub_account_id if sub_account_id is not None else account_id
        if lookup_key in unique_message_ids:
            if status == target_status.value:
                return lookup_key, event_request_id, True

        return "", event_request_id, False

    log.info(
        f"Waiting for Sub-Account event with target "
        f"state '{target_status.value}' for {identifier_str}"
    )

    unmatched_events = wait_for_messages(
        consumer,
        matcher=matcher,
        callback=None,
        unique_message_ids=unique_message_ids,
        inter_message_timeout=inter_message_timeout_seconds,
        matched_message_timeout=matched_message_timeout_seconds,
    )
    if unmatched_events:
        raise Exception(f"Did not see {target_status.value} for {identifier_str}")

    log.info(
        f"Found Sub-Account event with target "
        f"state '{target_status.value}' for {identifier_str}"
    )
