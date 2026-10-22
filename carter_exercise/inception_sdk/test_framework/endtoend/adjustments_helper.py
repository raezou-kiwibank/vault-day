# Copyright @ 2025 Thought Machine Group Limited. All rights reserved.
# standard libs
import logging
import os
import uuid

# inception sdk
import inception_sdk.test_framework.endtoend as endtoend
import inception_sdk.vault.core_api as core_api
from inception_sdk.test_framework.endtoend.core_api_helper import (  # noqa: F401
    batch_get_adjustments,
)
from inception_sdk.test_framework.endtoend.kafka_helper import kafka_only_helper, wait_for_messages

ADJUSTMENTS_EVENT_TOPIC = "vault.core_api.v1.adjustments.adjustment.events"

TERMINAL_STATUSES = {
    core_api.AdjustmentStatus.NO_ADJUSTMENT_REQUIRED.value,
    core_api.AdjustmentStatus.ERROR.value,
    core_api.AdjustmentStatus.COMPLETED.value,
}


log = logging.getLogger(__name__)
logging.basicConfig(
    level=os.environ.get("LOGLEVEL", "INFO"),
    format="%(asctime)s.%(msecs)03d - %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


def list_all_adjustments(
    account_ids: list[str] | None = None,
    schedule_job_ids: list[str] | None = None,
) -> list[core_api.Adjustment]:
    """
    Lists and filters Adjustments using the Adjustments endpoint.


    :param account_ids: Filter Adjustments by account ID. Exclusive with
        `schedule_job_ids`; one of the two is required.
    :param schedule_job_ids: Filter Adjustments by the job ID that triggered them.
        Exclusive with `account_ids`; one of the two is required.
    :return: list of Adjustments
    """

    return endtoend.core_api_helper.list_all(
        list_api_call=endtoend.core_api_helper.list_adjustments,
        request=core_api.ListAdjustmentsRequest(
            page_size=100, account_ids=account_ids, schedule_job_ids=schedule_job_ids
        ),
        element_retriever=lambda r: [adjustment for adjustment in r.adjustments],
    )


def bulk_retry_adjustments(retry_ids: list[str]) -> core_api.BulkRetryAdjustmentsResponse:
    """
    Retries Adjustments with status of ERROR.

    :param retry_ids: list of adjustment IDs to retry.
    :returns: dict from retried IDs to errored adjustments.
    """
    retry_requests = [
        core_api.AdjustmentsRetryRequest(
            request_id=str(uuid.uuid4()),
            id=id,
        )
        for id in retry_ids
    ]

    return endtoend.core_api_helper.bulk_retry_adjustments(
        request=core_api.BulkRetryAdjustmentsRequest(
            retry_requests=retry_requests,
        )
    )


@kafka_only_helper
def wait_for_adjustment_event(
    account_id: str,
    target_status: core_api.AdjustmentStatus,
    target_resource_adjustment_count: int | None = None,
    inter_message_timeout: int = 90,
    matched_message_timeout: int = 90,
):
    """
    Listens to the `vault.core_api.v1.adjustments.adjustment.events` topic and waits until
    the provided account ID receives an adjustment event whose status equals `target_status`.
    If `target_resource_adjustment_count` is provided, the event will also be matched on this value.

    :param account_id: the account ID to listen for adjustment events.
    :param target_status: the AdjustmentStatus value to wait for.
    :param target_resource_adjustment_count: optionally match the event on
        `adjustment.resource_adjustment_count` value. This should be used to ensure matching
        on the correct Adjustment if a test scenario triggers multiple Adjustments.
    :param inter_message_timeout: maximum time to wait between receiving any messages from
        the consumer (0 for no timeout).
    :param matched_message_timeout: maximum time to wait between receiving matched messages
        from the consumer (0 for no timeout).
    :raises Exception: if the adjustment enters a terminal status (NO_ADJUSTMENT_REQUIRED,
        ERROR, or COMPLETED) different to the `target_status` if the target status is terminal.
    :raises Exception: if no matching event is found.
    """
    consumer = endtoend.testhandle.kafka_consumers[ADJUSTMENTS_EVENT_TOPIC]

    count_suffix = (
        f" with {target_resource_adjustment_count=}" if target_resource_adjustment_count else ""
    )

    def matcher(event_msg, unique_message_ids):
        event_request_id = event_msg.get("event_id")
        wrapper = event_msg.get("adjustment_created_event") or event_msg.get(
            "adjustment_updated_event"
        )
        if not wrapper:
            return "", event_request_id, False

        adjustment = wrapper.get("adjustment")
        adjusted_account_id = adjustment.get("account_id")
        if adjusted_account_id != account_id:
            return "", event_request_id, False
        count = adjustment.get("resource_adjustment_count")
        if (
            target_resource_adjustment_count is not None
            and count != target_resource_adjustment_count
        ):
            return "", event_request_id, False

        status = adjustment.get("status")
        if status in TERMINAL_STATUSES and status != target_status.value:
            raise Exception(
                f"Adjustment entered terminal status {status} "
                f"and never reached target status {target_status.value} "
                f"for {account_id=}" + count_suffix
            )

        if adjusted_account_id in unique_message_ids:
            if status == target_status.value:
                return adjusted_account_id, event_request_id, True

        return "", event_request_id, False

    log.info(
        f"Waiting for Adjustment event with target "
        f"state '{target_status.value}' for {account_id=}" + count_suffix
    )

    unmatched_events = wait_for_messages(
        consumer,
        matcher=matcher,
        callback=None,
        unique_message_ids={account_id: None},
        inter_message_timeout=inter_message_timeout,
        matched_message_timeout=matched_message_timeout,
    )

    if unmatched_events:
        raise Exception(f"Did not see {target_status.value} for {account_id=}" + count_suffix)

    log.info(
        f"Found Adjustment event with target "
        f"state '{target_status.value}' for {account_id=}" + count_suffix
    )


def get_correction_posting_instruction_batches(
    *, account_id: str, resource_adjustment_count: int | None = None
) -> list[core_api.CommittedPostingInstructionBatch]:
    """
    Retrieves the correction posting instruction batches for a given account
    and resource adjustment count.

    :param account_id: Filter Adjustments by account ID.
    :param resource_adjustment_count: Filter Adjustments by resource adjustment count.
        If not specified, will default to the latest adjustment (the one with the
        largest resource_adjustment_count).
    :return: list of correction posting instruction batches
    """
    if resource_adjustment_count is None:
        # Default to the latest adjustment if not specified (already sorted descending)
        adjustments_response = endtoend.core_api_helper.list_adjustments(
            request=core_api.ListAdjustmentsRequest(
                account_ids=[account_id],
                page_size=1,
            )
        )
        adjustments = adjustments_response.adjustments
        if not adjustments:
            raise ValueError(f"Could not find any adjustments for account_id={account_id}")
        adjustment = adjustments[0]
    else:
        adjustments = list_all_adjustments(
            account_ids=[account_id],
            schedule_job_ids=None,
        )
        if not adjustments:
            raise ValueError(f"Could not find any adjustments for account_id={account_id}")

        matching_adjustments = [
            adj for adj in adjustments if adj.resource_adjustment_count == resource_adjustment_count
        ]
        if not matching_adjustments:
            raise ValueError(
                f"Could not find adjustment with resource_adjustment_count="
                f"{resource_adjustment_count} for account_id={account_id}"
            )
        adjustment = matching_adjustments[0]

    correction_pib_ids = adjustment.correction_posting_instruction_batch_ids or []
    if not correction_pib_ids:
        return []

    pibs_response = endtoend.postings_helper.batch_get_posting_instruction_batches(
        ids=correction_pib_ids
    )
    pibs_dict = pibs_response.posting_instruction_batches
    return [pibs_dict[pib_id] for pib_id in correction_pib_ids]
