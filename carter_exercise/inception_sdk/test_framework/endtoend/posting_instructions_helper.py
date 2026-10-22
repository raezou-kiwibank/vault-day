# Copyright @ 2021 - 2025 Thought Machine Group Limited. All rights reserved.
# standard libs
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Sequence

# third party
from typing_extensions import deprecated

# inception sdk
from inception_sdk.test_framework.endtoend.postings import (
    send_and_wait_for_posting_instruction_batch,
)
from inception_sdk.vault.postings.posting_classes import (
    AuthorisationAdjustment,
    CustomInstruction,
    InboundAuthorisation,
    InboundHardSettlement,
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

## Create and send a Posting Instruction Batch where Value and Booking timestamps are set at
## the Posting Instruction level.
## These helpers have been deprecated in favour of using the core_api models directly
## within the `create_posting_instruction_batch()` method.


@deprecated("Use the `create_posting_instruction_batch` method and core_api models.")
def create_inbound_hard_settlement_posting_instruction(
    amount: Decimal | str,
    account_id: str | None = None,
    value_timestamp: datetime | str | None = None,
    booking_timestamp: datetime | str | None = None,
    internal_account_id: str | None = None,
    denomination: str | None = None,
    client_transaction_id: str | None = None,
    override: bool = False,
    advice: bool | None = None,
    instruction_details: dict[str, str] | None = None,
    payment_device_token: str | None = None,
    target_account_address: str | None = None,
    asset: str | None = None,
):
    if not account_id and not payment_device_token:
        raise NameError(
            f"{datetime.utcnow()} - "
            "Didn't pass either account_id, or a payment_device_token for payment"
        )

    return PostingInstruction(
        instruction=InboundHardSettlement(
            amount=amount,
            denomination=denomination,
            target_account_id=account_id,
            internal_account_id=internal_account_id,
            advice=advice,
            payment_device_token=payment_device_token,
            target_account_address=target_account_address,
            asset=asset,
        ),
        client_transaction_id=client_transaction_id,
        instruction_details=instruction_details,
        override=override,
        value_timestamp=value_timestamp,
        booking_timestamp=booking_timestamp,
    )


@deprecated("Use the `create_posting_instruction_batch` method and core_api models.")
def create_outbound_hard_settlement_posting_instruction(
    amount: Decimal | str,
    account_id: str | None = None,
    value_timestamp: datetime | str | None = None,
    booking_timestamp: datetime | str | None = None,
    internal_account_id: str | None = None,
    denomination: str | None = None,
    client_transaction_id: str | None = None,
    advice: bool | None = None,
    override: bool = False,
    instruction_details: dict[str, str] | None = None,
    payment_device_token: str | None = None,
    target_account_address: str | None = None,
    asset: str | None = None,
):
    if not account_id and not payment_device_token:
        raise NameError(
            f"{datetime.utcnow()} - "
            "Didn't pass either account_id, or a payment_device_token for payment"
        )

    return PostingInstruction(
        instruction=OutboundHardSettlement(
            amount=amount,
            denomination=denomination,
            target_account_id=account_id,
            internal_account_id=internal_account_id,
            advice=advice,
            payment_device_token=payment_device_token,
            target_account_address=target_account_address,
            asset=asset,
        ),
        client_transaction_id=client_transaction_id,
        instruction_details=instruction_details,
        override=override,
        value_timestamp=value_timestamp,
        booking_timestamp=booking_timestamp,
    )


@deprecated("Use the `create_posting_instruction_batch` method and core_api models.")
def create_outbound_auth_posting_instruction(
    amount: Decimal | str,
    account_id: str | None = None,
    value_timestamp: datetime | str | None = None,
    booking_timestamp: datetime | str | None = None,
    internal_account_id: str | None = None,
    denomination: str | None = None,
    client_transaction_id: str | None = None,
    advice: bool | None = None,
    instruction_details: dict[str, str] | None = None,
    payment_device_token: str | None = None,
    target_account_address: str | None = None,
    asset: str | None = None,
    override: bool = False,
):
    if not account_id and not payment_device_token:
        raise NameError(
            f"{datetime.utcnow()} - "
            "Didn't pass either account_id, or a payment_device_token for payment"
        )

    return PostingInstruction(
        instruction=OutboundAuthorisation(
            amount=amount,
            denomination=denomination,
            target_account_id=account_id,
            internal_account_id=internal_account_id,
            advice=advice,
            payment_device_token=payment_device_token,
            target_account_address=target_account_address,
            asset=asset,
        ),
        client_transaction_id=client_transaction_id,
        instruction_details=instruction_details,
        override=override,
        value_timestamp=value_timestamp,
        booking_timestamp=booking_timestamp,
    )


@deprecated("Use the `create_posting_instruction_batch` method and core_api models.")
def create_inbound_auth_posting_instruction(
    amount: Decimal | str,
    account_id: str | None = None,
    value_timestamp: datetime | str | None = None,
    booking_timestamp: datetime | str | None = None,
    internal_account_id: str | None = None,
    denomination: str | None = None,
    client_transaction_id: str | None = None,
    advice: bool | None = None,
    instruction_details: dict[str, str] | None = None,
    payment_device_token: str | None = None,
    target_account_address: str | None = None,
    asset: str | None = None,
    override: bool = False,
):
    if not account_id and not payment_device_token:
        raise NameError(
            f"{datetime.utcnow()} - "
            "Didn't pass either account_id, or a payment_device_token for payment"
        )

    return PostingInstruction(
        instruction=InboundAuthorisation(
            amount=amount,
            denomination=denomination,
            target_account_id=account_id,
            internal_account_id=internal_account_id,
            advice=advice,
            payment_device_token=payment_device_token,
            target_account_address=target_account_address,
            asset=asset,
        ),
        client_transaction_id=client_transaction_id,
        instruction_details=instruction_details,
        override=override,
        value_timestamp=value_timestamp,
        booking_timestamp=booking_timestamp,
    )


@deprecated("Use the `create_posting_instruction_batch` method and core_api models.")
def create_auth_adjustment_posting_instruction(
    client_transaction_id: str,
    amount: Decimal | str | None = None,
    replacement_amount: Decimal | str | None = None,
    value_timestamp: datetime | str | None = None,
    booking_timestamp: datetime | str | None = None,
    instruction_details: dict[str, str] | None = None,
    override: bool = False,
):
    return PostingInstruction(
        instruction=AuthorisationAdjustment(
            amount=amount,
            replacement_amount=replacement_amount,
        ),
        client_transaction_id=client_transaction_id,
        instruction_details=instruction_details,
        override=override,
        value_timestamp=value_timestamp,
        booking_timestamp=booking_timestamp,
    )


@deprecated("Use the `create_posting_instruction_batch` method and core_api models.")
def create_settlement_posting_instruction(
    amount: Decimal | str,
    client_transaction_id: str,
    value_timestamp: datetime | str | None = None,
    booking_timestamp: datetime | str | None = None,
    final=False,
    instruction_details: dict[str, str] | None = None,
    override: bool = False,
):
    return PostingInstruction(
        instruction=Settlement(amount=amount, final=final),
        client_transaction_id=client_transaction_id,
        instruction_details=instruction_details,
        override=override,
        value_timestamp=value_timestamp,
        booking_timestamp=booking_timestamp,
    )


@deprecated("Use the `create_posting_instruction_batch` method and core_api models.")
def create_release_posting_instruction(
    client_transaction_id: str,
    value_timestamp: datetime | str | None = None,
    booking_timestamp: datetime | str | None = None,
    instruction_details: dict[str, str] | None = None,
    override: bool = False,
):
    return PostingInstruction(
        instruction=Release(),
        client_transaction_id=client_transaction_id,
        instruction_details=instruction_details,
        override=override,
        value_timestamp=value_timestamp,
        booking_timestamp=booking_timestamp,
    )


@deprecated("Use the `create_posting_instruction_batch` method and core_api models.")
def create_transfer_posting_instruction(
    amount: Decimal | str,
    debtor_target_account_id: str,
    creditor_target_account_id: str,
    value_timestamp: datetime | str | None = None,
    booking_timestamp: datetime | str | None = None,
    denomination: str | None = None,
    client_transaction_id: str | None = None,
    instruction_details: dict[str, str] | None = None,
    override: bool = False,
):
    return PostingInstruction(
        instruction=Transfer(
            amount=amount,
            debtor_target_account_id=debtor_target_account_id,
            creditor_target_account_id=creditor_target_account_id,
            denomination=denomination,
        ),
        client_transaction_id=client_transaction_id,
        instruction_details=instruction_details,
        override=override,
        value_timestamp=value_timestamp,
        booking_timestamp=booking_timestamp,
    )


@deprecated("Use the `create_posting_instruction_batch` method and core_api models.")
def create_custom_instruction_posting_instruction(
    postings: Sequence[Posting],
    value_timestamp: datetime | str | None = None,
    booking_timestamp: datetime | str | None = None,
    client_transaction_id: str | None = None,
    instruction_details: dict[str, str] | None = None,
    override: bool = False,
):
    return PostingInstruction(
        instruction=CustomInstruction(postings=postings),
        client_transaction_id=client_transaction_id,
        instruction_details=instruction_details,
        override=override,
        value_timestamp=value_timestamp,
        booking_timestamp=booking_timestamp,
    )


@deprecated("Use the `create_posting_instruction_batch` method and core_api models.")
def send_and_wait_for_pib_from_posting_instructions(
    posting_instructions: Sequence[PostingInstruction],
    request_id: str | None = None,
    batch_details: dict[str, str] | None = None,
    client_batch_id: str | None = None,
    timeout: int | None = None,
    client_id: str | None = None,
):
    request_id = str(uuid.uuid4()) if request_id is None else request_id
    return send_and_wait_for_posting_instruction_batch(
        pib_request=PostingInstructionBatchRequest(
            request_id=request_id,
            posting_instruction_batch=PostingInstructionBatch(
                posting_instructions=posting_instructions,
                client_batch_id=client_batch_id,
                client_id=client_id,
                batch_details=batch_details,
            ),
        ),
        timeout=timeout,
    )
