# Copyright @ 2021 - 2024 Thought Machine Group Limited. All rights reserved.
# standard libs
import logging
import os
import time
import uuid
from datetime import datetime
from decimal import Decimal
from json import dumps
from typing import Any, Sequence
from zoneinfo import ZoneInfo

# third party
from confluent_kafka import Producer
from typing_extensions import deprecated

# inception sdk
import inception_sdk.test_framework.endtoend as endtoend
import inception_sdk.vault.core_api as core_api
from inception_sdk.test_framework.endtoend.contracts_helper import DUMMY_CONTRA
from inception_sdk.test_framework.endtoend.helper import send_request
from inception_sdk.test_framework.endtoend.kafka_helper import (
    kafka_only_helper,
    produce_message,
    wait_for_messages,
)
from inception_sdk.vault.postings.posting_classes import (
    AuthorisationAdjustment,
    CustomInstruction,
    InboundAuthorisation,
    InboundHardSettlement,
    Instruction,
    MigrationPostingInstructionBatchRequest,
    OutboundAuthorisation,
    OutboundHardSettlement,
    Posting,
    PostingInstruction,
    PostingInstructionBatch,
    PostingInstructionBatchRequest,
    Release,
    Settlement,
    Transfer,
)

UTC = ZoneInfo("UTC")
log = logging.getLogger(__name__)
logging.basicConfig(
    level=os.environ.get("LOGLEVEL", "INFO"),
    format="%(asctime)s.%(msecs)03d - %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


POSTING_PHASES = [
    "POSTING_PHASE_COMMITTED",
    "POSTING_PHASE_PENDING_OUTGOING",
    "POSTING_PHASE_PENDING_INCOMING",
]


MIGRATIONS_POSTINGS_REQUESTS_TOPIC = "vault.migrations.postings.requests"
MIGRATIONS_POSTINGS_RESPONSES_TOPIC = "vault.migrations.postings.responses"
POSTINGS_API_REQUEST_TOPIC = "vault.core.postings.requests.v1"
POSTINGS_API_RESPONSE_TOPIC = "integration.inception.sdk.postings.responses"

POSTINGS_API_CLIENT_ID = "InceptionSDKE2EPostingsAPIClient"

INSTRUCTIONS_WITH_INTERNAL_ACCOUNT_ID_FIELD = {
    "inbound_hard_settlement",
    "outbound_hard_settlement",
    "inbound_authorisation",
    "outbound_authorisation",
}

DEFAULT_ADVICE = False
DEFAULT_DENOMINATION = "GBP"


def create_posting_instruction_batch(
    posting_instruction_batch: core_api.PostingInstructionBatch,
    dry_run: bool = False,
    shard_key: str = "",
    expected_status: core_api.PostingInstructionBatchStatus = (
        core_api.PostingInstructionBatchStatus.ACCEPTED
    ),
) -> core_api.CreatePostingInstructionBatchResponse:
    """
    Creates and returns a Posting Instruction Batch after submitting a
    CreatePostingInstructionBatchRequest to the Synchronous Postings API.

    :param posting_instruction_batch: The PIB to be created.
    :param dry_run: If true, no PostingInstructionBatch will be created and no
            PostingInstructionBatchCreatedEvent will be published to the event topic.
    :param shard_key: Optional key used as a best-effort lock to prevent
        CreatePostingInstructionBatchRequest with the same shard_key from racing each other.
    :param expected_status: PIB status expected from creation.
    :return: Created PIB.
    """
    posting_instruction_batch = _map_to_e2e_internal_accounts_for_posting_instruction_batch(
        posting_instruction_batch
    )

    response = endtoend.core_api_helper.create_posting_instruction_batch(
        request=core_api.CreatePostingInstructionBatchRequest(
            request_id=str(uuid.uuid4()),
            dry_run=dry_run,
            posting_instruction_batch=posting_instruction_batch,
            shard_key=shard_key,
        )
    )
    if response.posting_instruction_batch.status != expected_status:
        raise Exception(
            f"Posting Instruction Batch {response.posting_instruction_batch.id} in unexpected "
            f"status {response.posting_instruction_batch.status}"
        )
    return response


def list_posting_instruction_batches(
    page_size: int,
    page_token: str | None = None,
    order_by_direction: core_api.OrderByDirection = core_api.OrderByDirection.DESC,
    account_ids: list[str] | None = None,
    client_batch_ids: list[str] | None = None,
    payment_device_tokens: list[str] | None = None,
    client_transaction_ids: list[str] | None = None,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
) -> core_api.ListPostingInstructionBatchesResponse:
    """
    Lists and filters posting instruction batches.

    :param page_size: The maximum number of results to retrieve.
    :param page_token: Optional token of the page to retrieve results from.
    :param order_by_direction: Optional direction to order results in, by `value_timestamp`.
        Defaults to descending order.
    :param account_ids: Optional list of accounts IDs to filter PIBs by.
    :param client_batch_ids: Optional list of client batch IDs to filter PIBs by.
    :param payment_device_tokens: Optional list of payment device tokens to filter PIBs by.
    :param client_transaction_ids: Optional list of client transaction IDs to filter PIBs by.
    :param start_time: Optional datetime representing the earliest PIB creation to be returned
        (inclusive).
    :param end_time: Optional datetime representing the latest PIB creation to be returned
        (exclusive).
    :return: List of filtered PIBs.
    """
    response = endtoend.core_api_helper.list_posting_instruction_batches(
        request=core_api.ListPostingInstructionBatchesRequest(
            page_size=page_size,
            page_token=page_token,
            order_by_direction=order_by_direction,
            account_ids=account_ids,
            client_batch_ids=client_batch_ids,
            payment_device_tokens=payment_device_tokens,
            client_transaction_ids=client_transaction_ids,
            start_time=start_time,
            end_time=end_time,
        )
    )
    return response


def batch_get_posting_instruction_batches(
    ids: list[str],
) -> core_api.BatchGetPostingInstructionBatchesResponse:
    """
    Retrieves a set of Posting Instruction Batches by their IDs.

    :param ids: A list of Posting Instruction Batch IDs to retrieve.
    :return: Map of requested IDs to CommittedPostingInstructionBatch objects.
    """
    response = endtoend.core_api_helper.batch_get_posting_instruction_batches(
        request=core_api.BatchGetPostingInstructionBatchesRequest(ids=ids)
    )
    return response


@deprecated(
    """
    asyncCreate is deprecated as of Vault 5.4,
    use synchronous `create_posting_instruction_batch` instead
"""
)
def create_posting_async_operation(pib: dict[str, dict]) -> str:
    """
    Sends an asynchronous posting request and returns the asynchronous operation ID. Note, the
    latter should not to be confused with the ID of the posting instruction batch as these are
    different.
    :param pib: posting instruction batch
    :return: asynchronous operation ID
    """
    post_body = {
        "request_id": uuid.uuid4().hex,
        "posting_instruction_batch": pib,
    }
    resp = send_request(
        "post", "/v1/posting-instruction-batches:asyncCreate", data=dumps(post_body)
    )

    return resp["id"]


@deprecated(
    """
    creating async postings is deprecated as of Vault 5.4,
    use synchronous postings instead.
"""
)
def wait_until_async_operation_is_done(
    async_id: str, pib: dict[str, dict], timeout: int = 5
) -> str:
    """
    Retrieves the results of an asynchronous posting request when it is marked as done, returning
    the posting instruction batch ID. Also includes a timeout facility to wait for the response.
    :param async_id: asynchronous id of the original request
    :param pib: posting instruction batch
    :param timeout: number of iterations to query for the result, with a 1 second sleep after each
    iteration
    :return: posting instruction batch ID
    """
    get_body = {"ids": async_id}
    for _ in range(timeout):
        resp = send_request(
            "get",
            "/v1/posting-instruction-batches/async-operations:batchGet",
            params=get_body,
        )

        if (
            resp["async_operations"][async_id]["done"] is True
            and "response" in resp["async_operations"][async_id]
        ):
            return resp["async_operations"][async_id]["response"]["id"]
        elif (
            resp["async_operations"][async_id]["done"] is True
            and "error" in resp["async_operations"][async_id]
        ):
            errorstr = str(resp["async_operations"][async_id]["error"])
            pibstr = str(pib)
            raise Exception(
                f"wait_until_async_operation_is_done got an error, "
                f"async_id: {async_id}, pib: {pibstr}, error: {errorstr}"
            )

        time.sleep(1)

    raise TimeoutError(
        f"{datetime.utcnow()} - "
        "Posting never got accepted or created. Is it formatted correctly?\n"
        "Posting Instruction Batch:\n{}Async Id:\n{}".format(pib, async_id)
    )


def get_posting_batch(pib_id: str) -> Any:
    """
    Sends a request to retrieve a posting batch.
    :param pib_id: posting instruction batch ID
    :return: posting instruction batch
    """
    return send_request("get", f"/v1/posting-instruction-batches/{pib_id}", {})


def send_and_wait_for_posting_instruction_batch(
    pib_request: PostingInstructionBatchRequest | MigrationPostingInstructionBatchRequest,
    timeout: int | None = None,
) -> str:
    """
    Sends and waits for a posting response, dynamically routing to either the new synchronous
    helper (create_posting_instruction_batch) or the legacy async helper
    (send_and_wait_for_asynchronous_postings) depending on the --use_sync_postings CLI flag.

    :param pib_request: posting instruction batch request.
    :param timeout: number of iterations to query for the result. Note that this parameter
                    only has an effect when asynchronous postings are used (i.e. when
                    `--use_sync_postings` is set to False) and is ignored in synchronous mode.
    :return: posting instruction batch ID
    """
    if endtoend.testhandle.use_sync_postings:
        if isinstance(pib_request, MigrationPostingInstructionBatchRequest):
            raise ValueError(
                "MigrationPostingInstructionBatchRequest is not supported in "
                "synchronous postings mode."
            )
        pib_dict = pib_request.posting_instruction_batch.to_dict()
        for pi in pib_dict.get("posting_instructions", []):
            if not pi.get("override"):
                # Under the legacy Kafka postings path, self.override.to_dict() returns {} if no
                # overrides are set. Stripping empty/falsy overrides allows Pydantic validation
                # to succeed.
                pi.pop("override", None)
        posting_instruction_batch = core_api.PostingInstructionBatch.model_validate(pib_dict)
        posting_instruction_batch = _map_to_e2e_internal_accounts_for_posting_instruction_batch(
            posting_instruction_batch
        )

        response = endtoend.core_api_helper.create_posting_instruction_batch(
            request=core_api.CreatePostingInstructionBatchRequest(
                request_id=pib_request.request_id,
                posting_instruction_batch=posting_instruction_batch,
            )
        )
        return response.posting_instruction_batch.id
    else:
        return send_and_wait_for_asynchronous_postings(pib_request, timeout)


@deprecated(
    "Use `send_and_wait_for_posting_instruction_batch` with `use_sync_postings=True` CLI flag instead."  # noqa: E501
)
def send_and_wait_for_asynchronous_postings(
    pib_request: PostingInstructionBatchRequest | MigrationPostingInstructionBatchRequest,
    timeout: int | None = None,
) -> str:
    """
    Sends and waits for a posting response, either via kafka topic or async endpoint operation.
    Note, when using the migration option, posting requests and responses are received on the
    dedicated migration topics (as opposed to the standard topics).
    :param pib: posting instruction batch
    :param timeout: number of iterations to query for the result, with a 1 second sleep after each
    iteration
    :param migration: an option to determine whether to send and listen on the migration or
    standard posting topics
    :return: posting instruction batch ID
    """
    pib_id = ""
    migration = isinstance(pib_request, MigrationPostingInstructionBatchRequest)
    if endtoend.testhandle.use_kafka:
        if migration:
            send_migration_postings_request(
                producer=endtoend.testhandle.kafka_producer,
                pib_request=pib_request,
            )
        else:
            create_and_produce_posting_request(
                producer=endtoend.testhandle.kafka_producer,
                pib_request=pib_request,
            )

        responses, errors = (
            wait_for_migration_posting_responses({pib_request.request_id})
            if migration
            else wait_for_posting_responses({pib_request.request_id})
        )
        if error := errors.get(pib_request.request_id):
            raise ValueError(f"Posting {pib_request.request_id=} resulted in {error=}")
        elif responses:
            pib_id = responses[0] if responses else ""
        else:
            raise ValueError(f"No response found for posting {pib_request.request_id=}")

    else:
        async_id = create_posting_async_operation(pib_request.posting_instruction_batch.to_dict())
        timeout = timeout or 5
        pib_id = wait_until_async_operation_is_done(
            async_id, pib_request.posting_instruction_batch.to_dict(), timeout
        )

    return pib_id


## Create and send a Posting Instruction Batch where Value and Booking timestamps are set at
## the Posting Instruction Batch level (deprecated).
## These helpers have been deprecated in favour of using the core_api models directly
## within the `create_posting_instruction_batch()` method.

## For `--use_sync_postings=False` (default), the PIB is created asynchronously
## via kafka topic or async endpoint operation.
## For `--use_sync_postings=True`, the PIB is created synchronously via the
## POST /v1/posting-instruction-batches endpoint.


@deprecated(
    """
    PIB-level timestamps are deprecated as of Vault 5.5.
    Use `create_posting_instruction_batch` method with core_api models.
    PI-level timestamps are settable in the PostingInstruction object.
    """
)
def inbound_hard_settlement(
    amount: Decimal | str,
    account_id: str | None = None,
    value_datetime: datetime | str | None = None,
    booking_timestamp: datetime | str | None = None,
    internal_account_id: str | None = DUMMY_CONTRA,
    denomination: str | None = DEFAULT_DENOMINATION,
    client_transaction_id: str | None = None,
    override: bool = False,
    advice: bool | None = DEFAULT_ADVICE,
    batch_details: dict[str, str] | None = None,
    instruction_details: dict[str, str] | None = None,
    client_batch_id: str | None = None,
    payment_device_token: str | None = None,
    client_id: str | None = POSTINGS_API_CLIENT_ID,
    target_account_address: str | None = None,
    asset: str | None = None,
    target_sub_account_id: str | None = None,
):
    if not account_id and not payment_device_token:
        raise NameError(
            f"{datetime.now(tz=UTC)} - "
            "Didn't pass either account_id, or a payment_device_token for payment"
        )

    if client_transaction_id is None:
        client_transaction_id = str(uuid.uuid4())
    if client_batch_id is None:
        client_batch_id = str(uuid.uuid4())

    if internal_account_id:
        internal_account_id = endtoend.testhandle.internal_account_id_to_uploaded_id.get(
            internal_account_id, internal_account_id
        )

    instruction = InboundHardSettlement(
        amount=amount,
        denomination=denomination,
        target_account_id=account_id,
        internal_account_id=internal_account_id,
        advice=advice,
        payment_device_token=payment_device_token,
        target_account_address=target_account_address,
        asset=asset,
        target_sub_account_id=target_sub_account_id,
    )

    return send_posting_instruction_batch(
        instructions=[instruction],
        value_datetime=value_datetime,
        booking_timestamp=booking_timestamp,
        client_transaction_id=client_transaction_id,
        override=override,
        instruction_details=instruction_details,
        batch_details=batch_details,
        client_batch_id=client_batch_id,
        client_id=client_id,
    )


@deprecated(
    """
    PIB-level timestamps are deprecated as of Vault 5.5.
    Use `create_posting_instruction_batch` method with core_api models.
    PI-level timestamps are settable in the PostingInstruction object.
    """
)
def outbound_hard_settlement(
    amount: Decimal | str,
    account_id: str | None = None,
    value_datetime: datetime | str | None = None,
    booking_timestamp: datetime | str | None = None,
    internal_account_id: str | None = DUMMY_CONTRA,
    denomination: str | None = DEFAULT_DENOMINATION,
    client_transaction_id: str | None = None,
    override: bool = False,
    advice: bool | None = DEFAULT_ADVICE,
    batch_details: dict[str, str] | None = None,
    instruction_details: dict[str, str] | None = None,
    client_batch_id: str | None = None,
    payment_device_token: str | None = None,
    client_id: str | None = POSTINGS_API_CLIENT_ID,
    target_account_address: str | None = None,
    asset: str | None = None,
    target_sub_account_id: str | None = None,
):
    if not account_id and not payment_device_token:
        raise NameError(
            f"{datetime.now(tz=UTC)} - "
            "Didn't pass either account_id, or a payment_device_token for payment"
        )

    if client_transaction_id is None:
        client_transaction_id = str(uuid.uuid4())
    if client_batch_id is None:
        client_batch_id = str(uuid.uuid4())

    if internal_account_id:
        internal_account_id = endtoend.testhandle.internal_account_id_to_uploaded_id.get(
            internal_account_id, internal_account_id
        )

    instruction = OutboundHardSettlement(
        amount=amount,
        denomination=denomination,
        target_account_id=account_id,
        internal_account_id=internal_account_id,
        advice=advice,
        payment_device_token=payment_device_token,
        target_account_address=target_account_address,
        asset=asset,
        target_sub_account_id=target_sub_account_id,
    )

    return send_posting_instruction_batch(
        instructions=[instruction],
        value_datetime=value_datetime,
        booking_timestamp=booking_timestamp,
        client_transaction_id=client_transaction_id,
        override=override,
        instruction_details=instruction_details,
        batch_details=batch_details,
        client_batch_id=client_batch_id,
        client_id=client_id,
    )


@deprecated(
    """
    PIB-level timestamps are deprecated as of Vault 5.5.
    Use `create_posting_instruction_batch` method with core_api models.
    PI-level timestamps are settable in the PostingInstruction object.
    """
)
def outbound_auth(
    amount: Decimal | str,
    account_id: str | None = None,
    value_datetime: datetime | str | None = None,
    booking_timestamp: datetime | str | None = None,
    internal_account_id: str | None = DUMMY_CONTRA,
    denomination: str | None = DEFAULT_DENOMINATION,
    client_transaction_id: str | None = None,
    advice: bool | None = DEFAULT_ADVICE,
    batch_details: dict[str, str] | None = None,
    instruction_details: dict[str, str] | None = None,
    client_batch_id: str | None = None,
    payment_device_token: str | None = None,
    client_id: str | None = POSTINGS_API_CLIENT_ID,
    target_account_address: str | None = None,
    asset: str | None = None,
    target_sub_account_id: str | None = None,
):
    if not account_id and not payment_device_token:
        raise NameError(
            f"{datetime.now(tz=UTC)} - "
            "Didn't pass either account_id, or a payment_device_token for payment"
        )

    if client_transaction_id is None:
        client_transaction_id = str(uuid.uuid4())
    if client_batch_id is None:
        client_batch_id = str(uuid.uuid4())

    if internal_account_id:
        internal_account_id = endtoend.testhandle.internal_account_id_to_uploaded_id.get(
            internal_account_id, internal_account_id
        )

    instruction = OutboundAuthorisation(
        amount=amount,
        denomination=denomination,
        target_account_id=account_id,
        internal_account_id=internal_account_id,
        advice=advice,
        payment_device_token=payment_device_token,
        target_account_address=target_account_address,
        asset=asset,
        target_sub_account_id=target_sub_account_id,
    )

    return send_posting_instruction_batch(
        instructions=[instruction],
        value_datetime=value_datetime,
        booking_timestamp=booking_timestamp,
        client_transaction_id=client_transaction_id,
        instruction_details=instruction_details,
        batch_details=batch_details,
        client_batch_id=client_batch_id,
        client_id=client_id,
    )


@deprecated(
    """
    PIB-level timestamps are deprecated as of Vault 5.5.
    Use `create_posting_instruction_batch` method with core_api models.
    PI-level timestamps are settable in the PostingInstruction object.
    """
)
def inbound_auth(
    amount: Decimal | str,
    account_id: str | None = None,
    value_datetime: datetime | str | None = None,
    booking_timestamp: datetime | str | None = None,
    internal_account_id: str | None = DUMMY_CONTRA,
    denomination: str | None = DEFAULT_DENOMINATION,
    client_transaction_id: str | None = None,
    advice: bool | None = DEFAULT_ADVICE,
    batch_details: dict[str, str] | None = None,
    instruction_details: dict[str, str] | None = None,
    client_batch_id: str | None = None,
    payment_device_token: str | None = None,
    client_id: str | None = POSTINGS_API_CLIENT_ID,
    target_account_address: str | None = None,
    asset: str | None = None,
    target_sub_account_id: str | None = None,
):
    if not account_id and not payment_device_token:
        raise NameError(
            f"{datetime.now(tz=UTC)} - "
            "Didn't pass either account_id, or a payment_device_token for payment"
        )

    if client_transaction_id is None:
        client_transaction_id = str(uuid.uuid4())
    if client_batch_id is None:
        client_batch_id = str(uuid.uuid4())

    if internal_account_id:
        internal_account_id = endtoend.testhandle.internal_account_id_to_uploaded_id.get(
            internal_account_id, internal_account_id
        )

    instruction = InboundAuthorisation(
        amount=amount,
        denomination=denomination,
        target_account_id=account_id,
        internal_account_id=internal_account_id,
        advice=advice,
        payment_device_token=payment_device_token,
        target_account_address=target_account_address,
        asset=asset,
        target_sub_account_id=target_sub_account_id,
    )

    return send_posting_instruction_batch(
        instructions=[instruction],
        value_datetime=value_datetime,
        booking_timestamp=booking_timestamp,
        client_transaction_id=client_transaction_id,
        instruction_details=instruction_details,
        batch_details=batch_details,
        client_batch_id=client_batch_id,
        client_id=client_id,
    )


@deprecated(
    """
    PIB-level timestamps are deprecated as of Vault 5.5.
    Use `create_posting_instruction_batch` method with core_api models.
    PI-level timestamps are settable in the PostingInstruction object.
    """
)
def auth_adjustment(
    client_transaction_id: str,
    amount: Decimal | str | None = None,
    replacement_amount: Decimal | str | None = None,
    request_id: str | None = None,
    value_datetime: datetime | str | None = None,
    booking_timestamp: datetime | str | None = None,
    instruction_details: dict[str, str] | None = None,
    client_batch_id: str | None = None,
    client_id: str | None = None,
):
    instruction = AuthorisationAdjustment(
        amount=amount,
        replacement_amount=replacement_amount,
    )

    return send_posting_instruction_batch(
        [instruction],
        request_id=request_id,
        value_datetime=value_datetime,
        booking_timestamp=booking_timestamp,
        client_transaction_id=client_transaction_id,
        instruction_details=instruction_details,
        client_batch_id=client_batch_id,
        client_id=client_id,
    )


@deprecated(
    """
    PIB-level timestamps are deprecated as of Vault 5.5.
    Use `create_posting_instruction_batch` method with core_api models.
    PI-level timestamps are settable in the PostingInstruction object.
    """
)
def settlement(
    amount: Decimal | str,
    client_transaction_id: str,
    request_id: str | None = None,
    value_datetime: datetime | str | None = None,
    booking_timestamp: datetime | str | None = None,
    final=False,
    instruction_details: dict[str, str] | None = None,
    client_batch_id: str | None = None,
    batch_details: dict[str, str] | None = None,
    client_id: str | None = None,
):
    instruction = Settlement(amount=amount, final=final)

    return send_posting_instruction_batch(
        [instruction],
        request_id=request_id,
        value_datetime=value_datetime,
        booking_timestamp=booking_timestamp,
        client_transaction_id=client_transaction_id,
        instruction_details=instruction_details,
        client_batch_id=client_batch_id,
        batch_details=batch_details,
        client_id=client_id,
    )


@deprecated(
    """
    PIB-level timestamps are deprecated as of Vault 5.5.
    Use `create_posting_instruction_batch` method with core_api models.
    PI-level timestamps are settable in the PostingInstruction object.
    """
)
def create_release_event(
    client_transaction_id: str,
    request_id: str | None = None,
    value_datetime: datetime | str | None = None,
    booking_timestamp: datetime | str | None = None,
    instruction_details: dict[str, str] | None = None,
    client_batch_id: str | None = None,
    batch_details: dict[str, str] | None = None,
    client_id: str | None = None,
):
    instruction = Release()

    return send_posting_instruction_batch(
        [instruction],
        request_id=request_id,
        value_datetime=value_datetime,
        booking_timestamp=booking_timestamp,
        client_transaction_id=client_transaction_id,
        instruction_details=instruction_details,
        client_batch_id=client_batch_id,
        batch_details=batch_details,
        client_id=client_id,
    )


@deprecated(
    """
    PIB-level timestamps are deprecated as of Vault 5.5.
    Use `create_posting_instruction_batch` method with core_api models.
    PI-level timestamps are settable in the PostingInstruction object.
    """
)
def create_transfer(
    amount: Decimal | str,
    debtor_target_account_id: str,
    creditor_target_account_id: str,
    request_id: str | None = None,
    value_datetime: datetime | str | None = None,
    booking_timestamp: datetime | str | None = None,
    denomination: str | None = None,
    client_transaction_id: str | None = None,
    instruction_details: dict[str, str] | None = None,
    client_batch_id: str | None = None,
    client_id: str | None = None,
    debtor_target_sub_account_id: str | None = None,
    creditor_target_sub_account_id: str | None = None,
    debtor_target_account_address: str | None = None,
    creditor_target_account_address: str | None = None,
):
    if debtor_target_sub_account_id is not None and debtor_target_account_address is None:
        debtor_target_account_address = "DEFAULT"
    if creditor_target_sub_account_id is not None and creditor_target_account_address is None:
        creditor_target_account_address = "DEFAULT"

    instruction = Transfer(
        amount=amount,
        debtor_target_account_id=debtor_target_account_id,
        creditor_target_account_id=creditor_target_account_id,
        denomination=denomination,
        debtor_target_sub_account_id=debtor_target_sub_account_id,
        creditor_target_sub_account_id=creditor_target_sub_account_id,
        debtor_target_account_address=debtor_target_account_address,
        creditor_target_account_address=creditor_target_account_address,
    )

    return send_posting_instruction_batch(
        [instruction],
        request_id=request_id,
        value_datetime=value_datetime,
        booking_timestamp=booking_timestamp,
        client_transaction_id=client_transaction_id,
        instruction_details=instruction_details,
        client_batch_id=client_batch_id,
        client_id=client_id,
    )


@deprecated("Use `create_posting_instruction_batch` method with core_api models.")
def create_posting(
    account_id,
    amount,
    denomination,
    asset,
    account_address,
    phase,
    credit,
    sub_account_id="",
):
    return Posting(
        account_id,
        amount,
        credit,
        denomination,
        asset,
        account_address,
        phase,
        sub_account_id=sub_account_id,
    )


@deprecated(
    """
    PIB-level timestamps are deprecated as of Vault 5.5.
    Use `create_posting_instruction_batch` method with core_api models.
    PI-level timestamps are settable in the PostingInstruction object.
    """
)
def create_custom_instruction(
    postings: Sequence[Posting],
    request_id: str | None = None,
    value_datetime: datetime | str | None = None,
    booking_timestamp: datetime | str | None = None,
    client_transaction_id: str | None = None,
    batch_details: dict[str, str] | None = None,
    instruction_details: dict[str, str] | None = None,
    client_batch_id: str | None = None,
    client_id: str | None = None,
):
    instruction = CustomInstruction(postings=postings)

    return send_posting_instruction_batch(
        [instruction],
        request_id=request_id,
        value_datetime=value_datetime,
        booking_timestamp=booking_timestamp,
        client_transaction_id=client_transaction_id,
        batch_details=batch_details,
        instruction_details=instruction_details,
        client_batch_id=client_batch_id,
        client_id=client_id,
    )


@deprecated(
    """
    PIB-level timestamps are deprecated as of Vault 5.5.
    Use `create_posting_instruction_batch` method with core_api models.
    PI-level timestamps are settable in the PostingInstruction object.
    """
)
def send_posting_instruction_batch(
    instructions: Sequence[Instruction],
    request_id: str | None = None,
    value_datetime: datetime | str | None = None,
    booking_timestamp: datetime | str | None = None,
    client_transaction_id: str | None = None,
    override: bool = False,
    batch_details: dict[str, str] | None = None,
    instruction_details: dict[str, str] | None = None,
    client_batch_id: str | None = None,
    timeout: int | None = None,
    client_id: str | None = None,
):
    request_id = str(uuid.uuid4()) if request_id is None else request_id
    return send_and_wait_for_posting_instruction_batch(
        pib_request=PostingInstructionBatchRequest(
            request_id=request_id,
            posting_instruction_batch=PostingInstructionBatch(
                posting_instructions=[
                    PostingInstruction(
                        instruction=p,
                        client_transaction_id=client_transaction_id,
                        instruction_details=instruction_details,
                        override=override,
                    )
                    for p in instructions
                ],
                value_timestamp=value_datetime,
                booking_timestamp=booking_timestamp,
                client_batch_id=client_batch_id,
                client_id=client_id,
                batch_details=batch_details,
            ),
        ),
        timeout=timeout,
    )


class BatchCompletionRecorder(object):
    def __init__(self, pib_ids: list[str] | None = None, migration: bool = False) -> None:
        self.pib_ids = pib_ids or []
        self.errored_responses: dict[str, dict[str, str]] = {}
        self.migration = migration

    def __call__(self, event_msg) -> Any:
        """
        When a postings batch is completed we simply record the id.
        """
        pib = event_msg["posting_instruction_batch"] if self.migration else event_msg
        if error := pib.get("error", {}):
            # no PIB is actually created so event "id", which is output-only and normally PIB id
            # is meaningless
            self.errored_responses[pib["create_request_id"]] = error
        else:
            self.pib_ids.append(pib["id"])


@kafka_only_helper
def wait_for_posting_responses(
    request_ids: set[str],
    statuses: set[str] | None = None,
    timeout: int = 0,
) -> tuple[list[str], dict[str, dict[str, str]]]:
    """
    Waits for a posting response on a kafka topic, with the ability to filter for select statuses
    desired. Note, when using the migration option, ensure postings are sent to the migration topic
    (as opposed to the standard topic).
    :param request_ids: list of request ID's
    :param statuses: list of statuses to match against in the posting responses
    :param migration: an option to determine whether to listen on the migration or standard posting
    response
    :param timeout: a maximum time to wait between receiving matched messages from the consumer (0
    for no timeout)
    :return: a list of committed posting instruction batch ids (could be accepted or rejected) and a
    dict of errored posting instruction batch create_request_id to the error received
    """
    consumer = endtoend.testhandle.kafka_consumers[POSTINGS_API_RESPONSE_TOPIC]
    batch_completion_recorder = BatchCompletionRecorder()

    def matcher(event_msg, unique_message_ids):
        event_id = event_msg.get("create_request_id")
        event_response_id = event_msg.get("id", None)
        if event_id in unique_message_ids and (not statuses or event_msg["status"] in statuses):
            return event_id, event_response_id, True

        return "", event_response_id, False

    log.debug(f"Waiting for {len(request_ids)} postings to commit")

    wait_for_messages(
        consumer,
        matcher=matcher,
        callback=batch_completion_recorder,
        unique_message_ids={request_id: None for request_id in request_ids},
        inter_message_timeout=30,
        matched_message_timeout=timeout,
    )

    log.debug("All postings committed")

    return batch_completion_recorder.pib_ids, batch_completion_recorder.errored_responses


@kafka_only_helper
def wait_for_migration_posting_responses(
    request_ids: set[str],
    statuses: set[str] | None = None,
    timeout: int = 0,
) -> tuple[list[str], dict[str, dict[str, str]]]:
    """
    Waits for a posting response on a kafka topic, with the ability to filter for select statuses
    desired. Note, when using the migration option, ensure postings are sent to the migration topic
    (as opposed to the standard topic).
    :param request_ids: list of request ID's
    :param statuses: list of statuses to match against in the posting responses
    :param timeout: a maximum time to wait between receiving matched messages from the consumer (0
    for no timeout)
    :return: a list of committed migration posting instruction batch ids (could be accepted or
    rejected) and a dict of errored posting instruction batch create_request_id to the error
    received.
    """
    consumer = endtoend.testhandle.kafka_consumers[MIGRATIONS_POSTINGS_RESPONSES_TOPIC]
    batch_completion_recorder = BatchCompletionRecorder(migration=True)

    def matcher(event_msg, unique_message_ids):
        pib = event_msg.get("posting_instruction_batch")
        event_id = pib.get("create_request_id")
        event_response_id = pib.get("id")
        if event_id in unique_message_ids and (not statuses or pib["status"] in statuses):
            return event_id, event_response_id, True

        return "", event_response_id, False

    log.debug(f"Waiting for migration {len(request_ids)} postings to commit")

    wait_for_messages(
        consumer,
        matcher=matcher,
        callback=batch_completion_recorder,
        unique_message_ids={request_id: None for request_id in request_ids},
        inter_message_timeout=30,
        matched_message_timeout=timeout,
    )

    log.debug("All migration postings committed")

    return batch_completion_recorder.pib_ids, batch_completion_recorder.errored_responses


@kafka_only_helper
def create_and_produce_posting_request(
    producer: Producer,
    pib_request: PostingInstructionBatchRequest,
) -> str:
    """
    For a given PIB request, sends it to the relevant Kafka producer topic.
    :param producer: Kafka producer to use
    :param pib_request: the posting instruction batch request
    """
    produce_message(
        producer=producer,
        topic=POSTINGS_API_REQUEST_TOPIC,
        message=dumps(pib_request.to_dict()),
    )
    producer.flush()
    return pib_request.request_id


@kafka_only_helper
def send_migration_postings_request(
    producer: Producer,
    pib_request: MigrationPostingInstructionBatchRequest,
) -> None:
    """
    For a given postings migration PIB request, sends it to the relevant Kafka producer topic.
    relevant Kafka topic.
    :param producer: Kafka producer to use
    :param pib_request: the posting instruction batch to include in the request
    """
    # We use account_id as key to reduce the risk of postings racing against each other
    # This has no functional impact, but does reduce the amount of potential backdating
    # Note: postings on same partition can still race against each other
    # due to PP design
    produce_message(
        producer=producer,
        topic=MIGRATIONS_POSTINGS_REQUESTS_TOPIC,
        message=dumps(pib_request.to_dict()),
        key=pib_request.target_account_id,
    )
    producer.flush()


@deprecated("Use the `create_posting_instruction_batch` method and core_api models")
def generate_instruction(
    amount: Decimal | str,
    is_inbound: bool,
    is_auth: bool,
    denomination: str | None = None,
    target_account_id: str | None = None,
    internal_account_id: str | None = None,
    advice: bool | None = None,
    payment_device_token: str | None = None,
    target_account_address: str | None = None,
    asset: str | None = None,
) -> InboundHardSettlement | OutboundHardSettlement | InboundAuthorisation | OutboundAuthorisation:
    """
    Helper function that returns the posting instruction with internal_account_id defined
    param amount: string representation of the amount to be sent
    param denomination: denomination in which the money should be sent
    param target_account_id: account to which the money should be sent
    param internal_account_id: internal account to be used (default DUMMY_CONTRA)
    param advice: if true, the amount will be authorised regardless of balance check
    param payment_device_token: payment_device_token to which the money should be sent
    param is_inbound: determines if inbound or outbound posting
    param is_auth: determines if authorisation or hard settlement
    param target_account_address: account address to which the money should be sent
    param asset: asset type of the financial movement
    """

    internal_account_id = internal_account_id or DUMMY_CONTRA

    internal_account_id = endtoend.testhandle.internal_account_id_to_uploaded_id[
        internal_account_id
    ]

    if is_inbound:
        posting = InboundAuthorisation if is_auth else InboundHardSettlement
    else:
        posting = OutboundAuthorisation if is_auth else OutboundHardSettlement

    return posting(  # type: ignore [return-value]
        amount=amount,
        denomination=denomination,
        target_account_id=target_account_id,
        internal_account_id=internal_account_id,
        advice=advice,
        payment_device_token=payment_device_token,
        target_account_address=target_account_address,
        asset=asset,
    )


def _map_to_e2e_internal_accounts_for_posting_instruction_batch(
    posting_instruction_batch: core_api.PostingInstructionBatch,
) -> core_api.PostingInstructionBatch:
    """
    Update any `internal_account_id`s in applicable instruction types to use the e2e mapped version

    This handles all cases of field in the instructions which *could* be internal account IDs.
    - for IHS/OHS/IA/OA, only the `internal_account_id` can contain an internal account ID.
    - for Transfers, the `creditor_target_account` and `debtor_target_account` field can contain
      internal account IDs in their `account_id` attribute.
    - for CustomInstructions, any of the `Posting` objects could have an internal account ID in the
      `account_id` field.


    AuthorisationAdjustments, Releases and Settlements cannot set their own internal_account fields,
    hence these do not need to be handled.

    Internal account IDs cannot clash with customer account IDs so it is safe to do the replacement
    on any field which *might* contain an internal account ID.

    :param posting_instruction_batch: the PostingInstructionBatch to be instructed
    :return: the PostingInstructionBatch containing the updated instructions
    """

    updated_posting_instructions: list[core_api.PostingInstruction] = []
    for posting_instruction in posting_instruction_batch.posting_instructions:

        for instruction_type in INSTRUCTIONS_WITH_INTERNAL_ACCOUNT_ID_FIELD:
            if instruction := getattr(posting_instruction, instruction_type, None):
                # Set the internal_account_id to the uploaded e2e value if it exists in the
                # map, else set it to the same value to leave it unchanged
                instruction.internal_account_id = (
                    endtoend.testhandle.internal_account_id_to_uploaded_id.get(
                        instruction.internal_account_id, instruction.internal_account_id
                    )
                )

                # Update the posting instruction with the instruction containing the mapped values
                setattr(posting_instruction, instruction_type, instruction)
                break

        if instruction := getattr(posting_instruction, "transfer", None):
            # Set the creditor_target_account and debtor_target_account account_ids to the uploaded
            # e2e value if it exists in the map, else set it to the same value to leave it unchanged
            instruction.creditor_target_account = core_api.TargetAccount(
                account_id=endtoend.testhandle.internal_account_id_to_uploaded_id.get(
                    instruction.creditor_target_account.account_id,
                    instruction.creditor_target_account.account_id,
                )
            )
            instruction.debtor_target_account = core_api.TargetAccount(
                account_id=endtoend.testhandle.internal_account_id_to_uploaded_id.get(
                    instruction.debtor_target_account.account_id,
                    instruction.debtor_target_account.account_id,
                )
            )
            # Update the posting instruction with the instruction containing the mapped values
            setattr(posting_instruction, "transfer", instruction)

        elif instruction := getattr(posting_instruction, "custom_instruction", None):
            updated_postings: list[core_api.Posting] = []
            for posting in instruction.postings:
                # For each posting, set the account_id to the uploaded e2e value if it exists in the
                # map, else set it to the same value to leave it unchanged
                posting.account_id = endtoend.testhandle.internal_account_id_to_uploaded_id.get(
                    posting.account_id, posting.account_id
                )
                updated_postings.append(posting)
            instruction.postings = updated_postings
            # Update the posting instruction with the instruction containing the mapped values
            setattr(posting_instruction, "custom_instruction", instruction)

        updated_posting_instructions.append(posting_instruction)

    posting_instruction_batch.posting_instructions = updated_posting_instructions
    return posting_instruction_batch
