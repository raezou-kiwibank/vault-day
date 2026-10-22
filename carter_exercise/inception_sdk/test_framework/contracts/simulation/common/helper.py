# Copyright @ 2020-2021 Thought Machine Group Limited. All rights reserved.
"""
This module exposes easy helper methods for sending each type
of posting instruction and settings flags with minimal effort from the test writer.
However, for posting instruction types these helper methods are kept simple and minimal on purpose,
only exposing a small subset of fields available on each posting instruction
type.
Any more complex Posting Instruction Batches should be constructed by the
test writer out of the base available objects.
"""
# standard libs
from datetime import datetime
from decimal import Decimal
from typing import Sequence

# third party
from typing_extensions import deprecated

# inception sdk
from inception_sdk.test_framework.contracts.simulation.data_objects.data_objects import (
    SimulationEvent,
)
from inception_sdk.vault.postings.posting_classes import (
    AuthorisationAdjustment,
    CustomInstruction,
    InboundAuthorisation,
    InboundHardSettlement,
    Instruction,
    OutboundAuthorisation,
    OutboundHardSettlement,
    Posting,
    PostingInstruction,
    Release,
    Settlement,
    Transfer,
)
from inception_sdk.vault.postings.postings_helper import (
    create_pib_from_posting_instructions,
    create_posting_instruction_batch,
)


## Create SimulationEvents containing a Posting Instruction Batch
## where Value and Booking timestamps are set at the Posting
## Instruction Batch level (deprecated).
@deprecated(
    """
    PIB-level timestamps are deprecated as of Vault 5.5.
    Use `create_auth_adjustment_pi_event` instead with PI-level timestamps.
    """
)
def create_auth_adjustment_event(
    value_datetime: datetime,
    amount: Decimal | str | None = None,
    replacement_amount: Decimal | str | None = None,
    client_transaction_id: str = "",
    instruction_details: dict[str, str] | None = None,
    batch_details: dict[str, str] | None = None,
    client_batch_id: str = "",
    pib_timestamp: datetime | None = None,
    booking_datetime: datetime | None = None,
) -> SimulationEvent:
    """
    Creates a SimulationEvent for a Posting Instruction Batch with an AuthorisationAdjustment
    where Value and Booking timestamps are set at the Posting Instruction Batch level.

    :param value_datetime: the datetime at which the Posting Instruction Batch
        will be applied in the simulation.
    :param amount: delta amount to be sent. Cannot be used in conjunction with `replacement_amount`.
    :param replacement_amount: new total authorised amount. Cannot be used in
        conjunction with `amount`.
    :param client_transaction_id: the ID of the client transaction this posting
        instruction is creating or mutating.
    :param instruction_details: An optional mapping containing instruction level metadata.
    :param batch_details: A dictionary containing batch level metadata.
    :param client_batch_id: An id which allows related Posting Instructions
        to be associated with each other.
    :param pib_timestamp: Optional value timestamp at which the Posting Instruction Batch
        will be applied in the simulation. If "None" defaults to value_datetime.
    :param booking_datetime: Optional timestamp at which all committed postings within the Posting
        Instruction Batch are considered to be booked.
    :return: SimulationEvent with an AuthorisationAdjustment Posting Instruction Batch.
    """

    auth_adjustment_instruction = AuthorisationAdjustment(
        amount=amount,
        replacement_amount=replacement_amount,
    )

    return create_posting_instruction_batch_event(
        instructions=[auth_adjustment_instruction],
        value_datetime=value_datetime,
        client_transaction_id=client_transaction_id,
        instruction_details=instruction_details,
        pib_timestamp=pib_timestamp,
        batch_details=batch_details,
        client_batch_id=client_batch_id,
        booking_datetime=booking_datetime,
    )


@deprecated(
    """
    PIB-level timestamps are deprecated as of Vault 5.5.
    Use `create_custom_instruction_pi_event` instead with PI-level timestamps.
    """
)
def create_custom_instruction_event(
    amount: str,
    debtor_target_account_id: str,
    creditor_target_account_id: str,
    debtor_target_account_address: str,
    creditor_target_account_address: str,
    value_datetime: datetime,
    client_transaction_id: str = "",
    denomination: str | None = None,
    instruction_details: dict[str, str] | None = None,
    batch_details: dict[str, str] | None = None,
    client_batch_id: str = "",
    pib_timestamp: datetime | None = None,
    booking_datetime: datetime | None = None,
    debtor_target_sub_account_id: str | None = None,
    creditor_target_sub_account_id: str | None = None,
) -> SimulationEvent:
    """
    Creates a SimulationEvent for a Posting Instruction Batch with a CustomInstruction
    where Value and Booking timestamps are set at the Posting Instruction Batch level.

    :param amount: string representation of the amount to be sent
    :param debtor_target_account_id: account from which the money should be debited
    :param creditor_target_account_id: account to which the money should be credited to
    :param debtor_target_account_address: address from which the money should be debited
    :param creditor_target_account_address: address to which the money should be credited to
    :param value_datetime: the datetime at which the Posting Instruction Batch
           will be applied in the simulation
    :param client_transaction_id: the ID of the client transaction this posting
        instruction is creating or mutating.
    :param denomination: the denomination the posting instruction will be in.
    :param instruction_details: An optional mapping containing instruction level metadata.
    :param batch_details: A dictionary containing batch level metadata.
    :param client_batch_id: An id which allows related Posting Instructions
        to be associated with each other.
    :param pib_timestamp: Optional value timestamp at which the Posting Instruction Batch
        will be applied in the simulation. If "None" defaults to value_datetime.
    :param booking_datetime: Optional timestamp at which all committed postings within the Posting
        Instruction Batch are considered to be booked.
    :param debtor_target_sub_account_id: Optional Sub-Account ID targeting a specific
        debtor Sub-Account.
    :param creditor_target_sub_account_id: Optional Sub-Account ID targeting a specific
        creditor Sub-Account.
    :return: SimulationEvent with an InboundHardSettlement Posting Instruction Batch.
    """
    custom_instruction = CustomInstruction(
        postings=[
            Posting(
                account_id=debtor_target_account_id,
                amount=amount,
                credit=False,
                denomination=denomination,
                account_address=debtor_target_account_address,
                sub_account_id=debtor_target_sub_account_id,
            ),
            Posting(
                account_id=creditor_target_account_id,
                amount=amount,
                credit=True,
                denomination=denomination,
                account_address=creditor_target_account_address,
                sub_account_id=creditor_target_sub_account_id,
            ),
        ]
    )
    return create_posting_instruction_batch_event(
        instructions=[custom_instruction],
        value_datetime=value_datetime,
        client_transaction_id=client_transaction_id,
        instruction_details=instruction_details,
        pib_timestamp=pib_timestamp,
        batch_details=batch_details,
        client_batch_id=client_batch_id,
        booking_datetime=booking_datetime,
    )


@deprecated(
    """
    PIB-level timestamps are deprecated as of Vault 5.5.
    Use `create_inbound_authorisation_pi_event` instead with PI-level timestamps.
    """
)
def create_inbound_authorisation_event(
    amount: str,
    value_datetime: datetime,
    denomination: str | None = None,
    client_transaction_id: str = "",
    instruction_details: dict[str, str] | None = None,
    batch_details: dict[str, str] | None = None,
    client_batch_id: str = "",
    target_account_id: str | None = None,
    internal_account_id: str | None = None,
    pib_timestamp: datetime | None = None,
    target_account_address: str | None = None,
    asset: str | None = None,
    booking_datetime: datetime | None = None,
    target_sub_account_id: str | None = None,
) -> SimulationEvent:
    """
    Creates a SimulationEvent for a Posting Instruction Batch with an InboundAuthorisation
    where Value and Booking timestamps are set at the Posting Instruction Batch level.

    :param amount: string representation of the amount to be sent.
    :param value_datetime: the datetime at which the Posting Instruction Batch
        will be applied in the simulation.
    :param denomination: the denomination the posting instruction will be in.
    :param client_transaction_id: the ID of the client transaction this posting
        instruction is creating or mutating.
    :param instruction_details: An optional mapping containing instruction level metadata.
    :param batch_details: A dictionary containing batch level metadata.
    :param client_batch_id: An id which allows related Posting Instructions
        to be associated with each other.
    :param target_account_id: Target customer account id for posting instruction
    :param internal_account_id: internal account id for posting instruction
    :param pib_timestamp: Optional value timestamp at which the Posting Instruction Batch
        will be applied in the simulation. If "None" defaults to value_datetime.
    :param target_account_address: account address to which the money should be sent
    :param asset: asset type of the financial movement
    :param booking_datetime: Optional timestamp at which all committed postings within the Posting
        Instruction Batch are considered to be booked.
    :param target_sub_account_id: Optional Sub-Account ID targeting a specific Sub-Account.
    :return: SimulationEvent with an InboundAuthorisation Posting Instruction Batch.
    """
    inbound_auth_instruction = InboundAuthorisation(
        target_account_id=target_account_id,
        internal_account_id=internal_account_id,
        amount=amount,
        denomination=denomination,
        target_account_address=target_account_address,
        asset=asset,
        target_sub_account_id=target_sub_account_id,
    )
    return create_posting_instruction_batch_event(
        instructions=[inbound_auth_instruction],
        value_datetime=value_datetime,
        client_transaction_id=client_transaction_id,
        instruction_details=instruction_details,
        pib_timestamp=pib_timestamp,
        batch_details=batch_details,
        client_batch_id=client_batch_id,
        booking_datetime=booking_datetime,
    )


@deprecated(
    """
    PIB-level timestamps are deprecated as of Vault 5.5.
    Use `create_inbound_hard_settlement_pi_event` instead with PI-level timestamps.
    """
)
def create_inbound_hard_settlement_event(
    amount: str,
    value_datetime: datetime,
    denomination: str | None = None,
    client_transaction_id: str = "",
    instruction_details: dict[str, str] | None = None,
    batch_details: dict[str, str] | None = None,
    client_batch_id: str = "",
    target_account_id: str | None = None,
    internal_account_id: str | None = None,
    pib_timestamp: datetime | None = None,
    target_account_address: str | None = None,
    asset: str | None = None,
    booking_datetime: datetime | None = None,
    target_sub_account_id: str | None = None,
) -> SimulationEvent:
    """
    Creates a SimulationEvent for a Posting Instruction Batch with an InboundHardSettlement
    where Value and Booking timestamps are set at the Posting Instruction Batch level.

    :param amount: string representation of the amount to be sent.
    :param value_datetime: the datetime at which the event will be applied in the simulation.
    :param denomination: the denomination the posting instruction will be in.
    :param client_transaction_id: the ID of the client transaction this posting
        instruction is creating or mutating.
    :param instruction_details: An optional mapping containing instruction level metadata.
    :param batch_details: A dictionary containing batch level metadata.
    :param client_batch_id: An id which allows related Posting Instructions
        to be associated with each other.
    :param target_account_id: Target customer account id for posting instruction
    :param internal_account_id: internal account id for posting instruction
    :param pib_timestamp: Optional value timestamp at which the Posting Instruction Batch
        will be applied in the simulation. If "None" defaults to value_datetime.
    :param target_account_address: account address to which the money should be sent
    :param asset: asset type of the financial movement
    :param booking_datetime: Optional timestamp at which all committed postings within the Posting
        Instruction Batch are considered to be booked.
    :param target_sub_account_id: Optional Sub-Account ID targeting a specific Sub-Account.
    :return: SimulationEvent with an InboundHardSettlement Posting Instruction Batch.
    """
    inbound_hard_settlement_instruction = InboundHardSettlement(
        target_account_id=target_account_id,
        internal_account_id=internal_account_id,
        amount=amount,
        denomination=denomination,
        target_account_address=target_account_address,
        asset=asset,
        target_sub_account_id=target_sub_account_id,
    )
    return create_posting_instruction_batch_event(
        instructions=[inbound_hard_settlement_instruction],
        value_datetime=value_datetime,
        instruction_details=instruction_details,
        client_transaction_id=client_transaction_id,
        pib_timestamp=pib_timestamp,
        batch_details=batch_details,
        client_batch_id=client_batch_id,
        booking_datetime=booking_datetime,
    )


@deprecated(
    """
    PIB-level timestamps are deprecated as of Vault 5.5.
    Use `create_outbound_authorisation_pi_event` instead with PI-level timestamps.
    """
)
def create_outbound_authorisation_event(
    amount: str,
    value_datetime: datetime,
    denomination: str | None = None,
    client_transaction_id: str = "",
    instruction_details: dict[str, str] | None = None,
    batch_details: dict[str, str] | None = None,
    client_batch_id: str = "",
    target_account_id: str | None = None,
    internal_account_id: str | None = None,
    pib_timestamp: datetime | None = None,
    target_account_address: str | None = None,
    asset: str | None = None,
    booking_datetime: datetime | None = None,
    target_sub_account_id: str | None = None,
) -> SimulationEvent:
    """
    Creates a SimulationEvent for a Posting Instruction Batch with an OutboundAuthorisation
    where Value and Booking timestamps are set at the Posting Instruction Batch level.

    :param amount: string representation of the amount to be sent.
    :param value_datetime: the datetime at which the Posting Instruction Batch
        will be applied in the simulation.
    :param denomination: the denomination the posting instruction will be in.
    :param client_transaction_id: the ID of the client transaction this posting
        instruction is creating or mutating.
    :param instruction_details: An optional mapping containing instruction level metadata.
    :param batch_details: A dictionary containing batch level metadata.
    :param client_batch_id: An id which allows related Posting Instructions
        to be associated with each other.
    :param target_account_id: Target customer account id for posting instruction
    :param internal_account_id: internal account id for posting instruction
    :param pib_timestamp: Optional value timestamp at which the Posting Instruction Batch
        will be applied in the simulation. If "None" defaults to value_datetime.
    :param target_account_address: account address to which the money should be sent
    :param asset: asset type of the financial movement
    :param booking_datetime: Optional timestamp at which all committed postings within the Posting
        Instruction Batch are considered to be booked.
    :param target_sub_account_id: Optional Sub-Account ID targeting a specific Sub-Account.
    :return: SimulationEvent with an OutboundAuthorisation Posting Instruction Batch.
    """
    outbound_auth_instruction = OutboundAuthorisation(
        target_account_id=target_account_id,
        internal_account_id=internal_account_id,
        amount=amount,
        denomination=denomination,
        target_account_address=target_account_address,
        asset=asset,
        target_sub_account_id=target_sub_account_id,
    )
    return create_posting_instruction_batch_event(
        instructions=[outbound_auth_instruction],
        value_datetime=value_datetime,
        client_transaction_id=client_transaction_id,
        instruction_details=instruction_details,
        pib_timestamp=pib_timestamp,
        batch_details=batch_details,
        client_batch_id=client_batch_id,
        booking_datetime=booking_datetime,
    )


@deprecated(
    """
    PIB-level timestamps are deprecated as of Vault 5.5.
    Use `create_outbound_hard_settlement_pi_event` instead with PI-level timestamps.
    """
)
def create_outbound_hard_settlement_event(
    amount: str,
    value_datetime: datetime,
    denomination: str | None = None,
    client_transaction_id: str = "",
    instruction_details: dict[str, str] | None = None,
    batch_details: dict[str, str] | None = None,
    client_batch_id: str = "",
    target_account_id: str | None = None,
    internal_account_id: str | None = None,
    pib_timestamp: datetime | None = None,
    advice: bool | None = None,
    target_account_address: str | None = None,
    asset: str | None = None,
    booking_datetime: datetime | None = None,
    target_sub_account_id: str | None = None,
) -> SimulationEvent:
    """
    Creates a SimulationEvent for a Posting Instruction Batch with an OutboundHardSettlement
    where Value and Booking timestamps are set at the Posting Instruction Batch level.

    :param amount: string representation of the amount to be sent.
    :param value_datetime: the datetime at which the event will be applied in the simulation.
    :param denomination: the denomination the posting instruction will be in.
    :param client_transaction_id: the ID of the client transaction this posting
        instruction is creating or mutating.
    :param instruction_details: An optional mapping containing instruction level metadata.
    :param batch_details: A dictionary containing batch level metadata.
    :param client_batch_id: An id which allows related Posting Instructions
        to be associated with each other.
    :param target_account_id: Target customer account id for posting instruction
    :param internal_account_id: internal account id for posting instruction
    :param pib_timestamp: Optional value timestamp at which the Posting Instruction Batch
        will be applied in the simulation. If "None" defaults to value_datetime.
    :param advice: if true, the amount will be authorised regardless of balance check
    :param target_account_address: account address to which the money should be sent
    :param asset: asset type of the financial movement
    :param booking_datetime: Optional timestamp at which all committed postings within the Posting
        Instruction Batch are considered to be booked.
    :param target_sub_account_id: Optional Sub-Account ID targeting a specific Sub-Account.
    :return: SimulationEvent with an OutboundHardSettlement Posting Instruction Batch.
    """
    outbound_hard_settlement_instruction = OutboundHardSettlement(
        target_account_id=target_account_id,
        internal_account_id=internal_account_id,
        amount=amount,
        denomination=denomination,
        advice=advice,
        target_account_address=target_account_address,
        asset=asset,
        target_sub_account_id=target_sub_account_id,
    )
    return create_posting_instruction_batch_event(
        instructions=[outbound_hard_settlement_instruction],
        value_datetime=value_datetime,
        instruction_details=instruction_details,
        client_transaction_id=client_transaction_id,
        pib_timestamp=pib_timestamp,
        batch_details=batch_details,
        client_batch_id=client_batch_id,
        booking_datetime=booking_datetime,
    )


@deprecated(
    """
    PIB-level timestamps are deprecated as of Vault 5.5.
    Use `create_release_pi_event` instead with PI-level timestamps.
    """
)
def create_release_event(
    client_transaction_id: str,
    value_datetime: datetime,
    instruction_details: dict[str, str] | None = None,
    batch_details: dict[str, str] | None = None,
    client_batch_id: str = "",
    pib_timestamp: datetime | None = None,
    require_pre_posting_hook_execution: bool = False,
    booking_datetime: datetime | None = None,
) -> SimulationEvent:
    """
    Creates a SimulationEvent for a Posting Instruction Batch with a Release
    where Value and Booking timestamps are set at the Posting Instruction Batch level.

    :param client_transaction_id: the ID of the client transaction this posting
        instruction is creating or mutating.
    :param value_datetime: the datetime at which the Posting Instruction Batch
        will be applied in the simulation
    :param instruction_details: An optional mapping containing instruction level metadata.
    :param batch_details: A dictionary containing batch level metadata.
    :param client_batch_id: An id which allows related Posting Instructions
        to be associated with each other.
    :param pib_timestamp: Optional value timestamp at which the Posting Instruction Batch
        will be applied in the simulation. If "None" defaults to value_datetime.
    :param require_pre_posting_hook_execution: A boolean that can ensure the pre-posting hook
        is executed when the release is processed
    :param booking_datetime: Optional timestamp at which all committed postings within the Posting
        Instruction Batch are considered to be booked.
    :return: SimulationEvent with a Release Posting Instruction Batch.
    """
    release_instruction = Release(
        require_pre_posting_hook_execution=require_pre_posting_hook_execution
    )
    return create_posting_instruction_batch_event(
        instructions=[release_instruction],
        value_datetime=value_datetime,
        pib_timestamp=pib_timestamp,
        client_transaction_id=client_transaction_id,
        instruction_details=instruction_details,
        batch_details=batch_details,
        client_batch_id=client_batch_id,
        booking_datetime=booking_datetime,
    )


@deprecated(
    """
    PIB-level timestamps are deprecated as of Vault 5.5.
    Use `create_settlement_pi_event` instead with PI-level timestamps.
    """
)
def create_settlement_event(
    amount: str,
    client_transaction_id: str,
    value_datetime: datetime,
    instruction_details: dict[str, str] | None = None,
    batch_details: dict[str, str] | None = None,
    client_batch_id: str = "",
    final: bool = False,
    pib_timestamp: datetime | None = None,
    require_pre_posting_hook_execution: bool = False,
    booking_datetime: datetime | None = None,
) -> SimulationEvent:
    """
    Creates a SimulationEvent for a Posting Instruction Batch with a Settlement
    where Value and Booking timestamps are set at the Posting Instruction Batch level.

    :param amount: string representation of the amount to be sent.
    :param client_transaction_id: the ID of the client transaction this posting
        instruction is creating or mutating.
    :param value_datetime: the datetime at which the Posting Instruction Batch
        will be applied in the simulation.
    :param instruction_details: An optional mapping containing instruction level metadata.
    :param batch_details: A dictionary containing batch level metadata.
    :param client_batch_id: An id which allows related Posting Instructions
        to be associated with each other.
    :param final: A boolean allowing further (True) or no more (False) settlements associated with
        the client_transaction_id.
    :param pib_timestamp: Optional value timestamp at which the Posting Instruction Batch
        will be applied in the simulation. If "None" defaults to value_datetime.
    :param require_pre_posting_hook_execution: A boolean that can ensure the pre-posting hook
        is executed when the settlement is processed
    :param booking_datetime: Optional timestamp at which all committed postings within the Posting
        Instruction Batch are considered to be booked.
    :return: SimulationEvent with a Settlement Posting Instruction Batch.
    """
    settlement_instruction = Settlement(
        amount=amount,
        final=final,
        require_pre_posting_hook_execution=require_pre_posting_hook_execution,
    )
    return create_posting_instruction_batch_event(
        instructions=[settlement_instruction],
        value_datetime=value_datetime,
        client_transaction_id=client_transaction_id,
        instruction_details=instruction_details,
        pib_timestamp=pib_timestamp,
        batch_details=batch_details,
        client_batch_id=client_batch_id,
        booking_datetime=booking_datetime,
    )


@deprecated(
    """
    PIB-level timestamps are deprecated as of Vault 5.5.
    Use `create_transfer_pi_event` instead with PI-level timestamps.
    """
)
def create_transfer_event(
    amount: str,
    value_datetime: datetime,
    creditor_target_account_id: str,
    debtor_target_account_id: str,
    denomination: str = "",
    client_transaction_id: str = "",
    instruction_details: dict[str, str] | None = None,
    batch_details: dict[str, str] | None = None,
    client_batch_id: str = "",
    pib_timestamp: datetime | None = None,
    booking_datetime: datetime | None = None,
    debtor_target_sub_account_id: str | None = None,
    creditor_target_sub_account_id: str | None = None,
    debtor_target_account_address: str | None = None,
    creditor_target_account_address: str | None = None,
) -> SimulationEvent:
    """
    Creates a SimulationEvent for a Posting Instruction Batch with a Transfer
    where Value and Booking timestamps are set at the Posting Instruction Batch level.

    :param amount: string representation of the amount to be sent.
    :param value_datetime: the datetime at which the event will be applied in the simulation.
    :param creditor_target_account_id: account to credit for Transfer.
    :param debtor_target_account_id: account to debit for Transfer.
    :param denomination: the denomination the posting instruction will be in.
    :param client_transaction_id: the ID of the client transaction this posting
        instruction is creating or mutating.
    :param instruction_details: An optional mapping containing instruction level metadata.
    :param batch_details: A dictionary containing batch level metadata.
    :param client_batch_id: An id which allows related Posting Instructions
        to be associated with each other.
    :param pib_timestamp: Optional value timestamp at which the Posting Instruction Batch
        will be applied in the simulation. If "None" defaults to value_datetime.
    :param booking_datetime: Optional timestamp at which all committed postings within the Posting
        Instruction Batch are considered to be booked.
    :param debtor_target_sub_account_id: Optional Sub-Account ID targeting a specific
        debtor Sub-Account.
    :param creditor_target_sub_account_id: Optional Sub-Account ID targeting a specific
        creditor Sub-Account.
    :param debtor_target_account_address: Optional address targeting a specific debtor address.
    :param creditor_target_account_address: Optional address targeting a specific creditor address.
    :return: SimulationEvent with a Transfer Posting Instruction Batch.
    """
    transfer_instruction = Transfer(
        creditor_target_account_id=creditor_target_account_id,
        debtor_target_account_id=debtor_target_account_id,
        amount=amount,
        denomination=denomination,
        debtor_target_sub_account_id=debtor_target_sub_account_id,
        creditor_target_sub_account_id=creditor_target_sub_account_id,
        debtor_target_account_address=debtor_target_account_address,
        creditor_target_account_address=creditor_target_account_address,
    )
    return create_posting_instruction_batch_event(
        instructions=[transfer_instruction],
        value_datetime=value_datetime,
        client_transaction_id=client_transaction_id,
        batch_details=batch_details,
        instruction_details=instruction_details,
        client_batch_id=client_batch_id,
        pib_timestamp=pib_timestamp,
        booking_datetime=booking_datetime,
    )


@deprecated(
    """
    PIB-level timestamps are deprecated as of Vault 5.5.
    Use `create_pib_event_from_posting_instructions` instead with PI-level timestamps.
    """
)
def create_posting_instruction_batch_event(
    instructions: list[Instruction],
    value_datetime: datetime,
    client_transaction_id: str = "",
    override: bool = False,
    batch_details: dict[str, str] | None = None,
    instruction_details: dict[str, str] | None = None,
    client_batch_id: str = "",
    client_id: str = "",
    pib_timestamp: datetime | None = None,
    booking_datetime: datetime | None = None,
) -> SimulationEvent:
    return SimulationEvent(
        value_datetime,
        create_posting_instruction_batch(
            instructions=instructions,
            value_datetime=(pib_timestamp or value_datetime).isoformat(),
            client_transaction_id=client_transaction_id,
            override=override,
            batch_details=batch_details,
            instruction_details=instruction_details,
            client_batch_id=client_batch_id,
            client_id=client_id,
            booking_timestamp=booking_datetime,
        ),
    )


## Create SimulationEvents containing a Posting Instruction Batch
## where Posting Instruction level fields can be explicitly defined.
## Value and Booking timestamps are set at the Posting Instruction level.
def create_auth_adjustment_pi_event(
    event_datetime: datetime,
    client_transaction_id: str,
    amount: Decimal | str | None = None,
    replacement_amount: Decimal | str | None = None,
    advice: bool = False,
    instruction_details: dict[str, str] | None = None,
    override: bool = False,
    value_timestamp: datetime | None = None,
    booking_timestamp: datetime | None = None,
    client_id: str = "",
    client_batch_id: str = "",
    batch_details: dict[str, str] | None = None,
) -> SimulationEvent:
    """
    Creates a SimulationEvent for a Posting Instruction Batch with an AuthorisationAdjustment
    where Posting Instruction level fields can be explicitly defined.

    :param event_datetime: the datetime at which the event will be applied in the simulation.
    :param client_transaction_id: the ID of the client transaction this posting
        instruction is creating or mutating.
    :param amount: delta amount to be sent. Cannot be used in conjunction with `replacement_amount`.
    :param replacement_amount: new total authorised amount. Cannot be used in
        conjunction with `amount`.
    :param advice: If true, the posting instruction is not applied to the ledger and does not
        affect account balances. Defaults to false.
    :param instruction_details: An optional mapping containing instruction level metadata.
    :param override: If true, allows to override certain checks for this Posting Instruction.
        Defaults to false.
    :param value_timestamp: Optional timestamp at which the Posting Instruction.
        will be applied in the simulation. Defaults to the generated insertion_timestamp.
    :param booking_timestamp: Optional timestamp at which all committed postings within the Posting
        Instruction are considered to be booked. Defaults to the generated insertion_timestamp.
    :param client_id: An id to uniquely identify a client entity across the platform.
    :param client_batch_id: An id which allows related Posting Instructions
        to be associated with each other.
    :param batch_details: A dictionary containing batch level metadata.
    :return: SimulationEvent containing a Posting Instruction Batch instructing an
        AuthorisationAdjustment.
    """

    instructions = [
        PostingInstruction(
            instruction=AuthorisationAdjustment(
                amount=amount,
                advice=advice,
                replacement_amount=replacement_amount,
            ),
            client_transaction_id=client_transaction_id,
            instruction_details=instruction_details,
            override=override,
            value_timestamp=value_timestamp,
            booking_timestamp=booking_timestamp,
        )
    ]

    return create_pib_event_from_posting_instructions(
        instructions=instructions,
        event_datetime=event_datetime,
        client_id=client_id,
        client_batch_id=client_batch_id,
        batch_details=batch_details,
    )


def create_custom_instruction_pi_event(
    event_datetime: datetime,
    amount: str,
    denomination: str,
    debtor_target_account_id: str,
    creditor_target_account_id: str,
    debtor_target_account_address: str | None = None,
    creditor_target_account_address: str | None = None,
    asset: str | None = None,
    phase: str | None = None,
    client_transaction_id: str = "",
    instruction_details: dict[str, str] | None = None,
    override: bool = False,
    value_timestamp: datetime | None = None,
    booking_timestamp: datetime | None = None,
    client_id: str = "",
    client_batch_id: str = "",
    batch_details: dict[str, str] | None = None,
    debtor_target_sub_account_id: str | None = None,
    creditor_target_sub_account_id: str | None = None,
) -> SimulationEvent:
    """
    Creates a SimulationEvent for a Posting Instruction Batch with a CustomInstruction
    where Posting Instruction level fields can be explicitly defined.

    :param event_datetime: the datetime at which the event will be applied in the simulation.
    :param amount: string representation of the amount to be sent.
    :param denomination: the denomination the posting instruction will be in.
    :param debtor_target_account_id: account from which the money should be debited.
    :param creditor_target_account_id: account to which the money should be credited to.
    :param debtor_target_account_address: Optional account address from which the money
        should be debited.
    :param creditor_target_account_address: Optional account address to which the money
        should be credited to.
    :param asset: Optional asset value of the posting.
    :param phase: refers to the stage of the posting in the transaction lifecycle.
    :param client_transaction_id: the ID of the client transaction this posting
        instruction is creating or mutating.
    :param instruction_details: An optional mapping containing instruction level metadata.
    :param override: If true, allows to override certain checks for this Posting Instruction.
        Defaults to false.
    :param value_timestamp: Optional timestamp at which the Posting Instruction.
        will be applied in the simulation. Defaults to the generated insertion_timestamp.
    :param booking_timestamp: Optional timestamp at which all committed postings within the Posting
        Instruction are considered to be booked. Defaults to the generated insertion_timestamp.
    :param client_id: An id to uniquely identify a client entity across the platform.
    :param client_batch_id: An id which allows related Posting Instructions
        to be associated with each other.
    :param batch_details: A dictionary containing batch level metadata.
    :param debtor_target_sub_account_id: Optional Sub-Account ID targeting a specific
        debtor Sub-Account.
    :param creditor_target_sub_account_id: Optional Sub-Account ID targeting a specific
        creditor Sub-Account.
    :return: SimulationEvent containing a Posting Instruction Batch instructing an
        CustomInstruction.
    """
    instructions = [
        PostingInstruction(
            instruction=CustomInstruction(
                postings=[
                    Posting(
                        account_id=debtor_target_account_id,
                        amount=amount,
                        credit=False,
                        denomination=denomination,
                        asset=asset,
                        account_address=debtor_target_account_address,
                        phase=phase,
                        sub_account_id=debtor_target_sub_account_id,
                    ),
                    Posting(
                        account_id=creditor_target_account_id,
                        amount=amount,
                        credit=True,
                        denomination=denomination,
                        asset=asset,
                        account_address=creditor_target_account_address,
                        phase=phase,
                        sub_account_id=creditor_target_sub_account_id,
                    ),
                ]
            ),
            client_transaction_id=client_transaction_id,
            instruction_details=instruction_details,
            override=override,
            value_timestamp=value_timestamp,
            booking_timestamp=booking_timestamp,
        )
    ]
    return create_pib_event_from_posting_instructions(
        instructions=instructions,
        event_datetime=event_datetime,
        client_id=client_id,
        client_batch_id=client_batch_id,
        batch_details=batch_details,
    )


def create_inbound_authorisation_pi_event(
    event_datetime: datetime,
    client_transaction_id: str,
    amount: str,
    denomination: str,
    target_account_id: str | None = None,
    internal_account_id: str | None = None,
    advice: bool | None = None,
    target_account_address: str | None = None,
    asset: str | None = None,
    instruction_details: dict[str, str] | None = None,
    override: bool = False,
    value_timestamp: datetime | None = None,
    booking_timestamp: datetime | None = None,
    client_id: str = "",
    client_batch_id: str = "",
    batch_details: dict[str, str] | None = None,
    target_sub_account_id: str | None = None,
) -> SimulationEvent:
    """
    Creates a SimulationEvent for a Posting Instruction Batch with an InboundAuthorisation
    where Posting Instruction level fields can be explicitly defined.

    :param event_datetime: the datetime at which the event will be applied in the simulation.
    :param client_transaction_id: the ID of the client transaction this posting
        instruction is creating or mutating.
    :param amount: string representation of the amount to be sent.
    :param denomination: the denomination the posting instruction will be in.
    :param target_account_id: Target customer account id for posting instruction.
    :param internal_account_id: internal account id for posting instruction.
    :param advice: If true, the posting instruction is not applied to the ledger and does not
        affect account balances. Defaults to false.
    :param target_account_address: account address to which the money should be sent.
    :param asset: asset type of the financial movement.
    :param instruction_details: An optional mapping containing instruction level metadata.
    :param override: If true, allows to override certain checks for this Posting Instruction.
        Defaults to false.
    :param value_timestamp: Optional timestamp at which the Posting Instruction.
        will be applied in the simulation. Defaults to the generated insertion_timestamp.
    :param booking_timestamp: Optional timestamp at which all committed postings within the Posting
        Instruction are considered to be booked. Defaults to the generated insertion_timestamp.
    :param client_id: An id to uniquely identify a client entity across the platform.
    :param client_batch_id: An id which allows related Posting Instructions
        to be associated with each other.
    :param batch_details: A dictionary containing batch level metadata.
    :param target_sub_account_id: Optional Sub-Account ID targeting a specific Sub-Account.
    :return: SimulationEvent containing a Posting Instruction Batch instructing an
        InboundAuthorisation.
    """
    instructions = [
        PostingInstruction(
            instruction=InboundAuthorisation(
                target_account_id=target_account_id,
                internal_account_id=internal_account_id,
                amount=amount,
                denomination=denomination,
                target_account_address=target_account_address,
                asset=asset,
                advice=advice,
                target_sub_account_id=target_sub_account_id,
            ),
            client_transaction_id=client_transaction_id,
            instruction_details=instruction_details,
            override=override,
            value_timestamp=value_timestamp,
            booking_timestamp=booking_timestamp,
        )
    ]
    return create_pib_event_from_posting_instructions(
        instructions=instructions,
        event_datetime=event_datetime,
        client_id=client_id,
        client_batch_id=client_batch_id,
        batch_details=batch_details,
    )


def create_inbound_hard_settlement_pi_event(
    event_datetime: datetime,
    amount: str,
    denomination: str,
    target_account_id: str | None = None,
    internal_account_id: str | None = None,
    advice: bool | None = None,
    target_account_address: str | None = None,
    asset: str | None = None,
    client_transaction_id: str = "",
    instruction_details: dict[str, str] | None = None,
    override: bool = False,
    value_timestamp: datetime | None = None,
    booking_timestamp: datetime | None = None,
    client_id: str = "",
    client_batch_id: str = "",
    batch_details: dict[str, str] | None = None,
    target_sub_account_id: str | None = None,
) -> SimulationEvent:
    """
    Creates a SimulationEvent for a Posting Instruction Batch with an InboundHardSettlement
    where Posting Instruction level fields can be explicitly defined.

    :param event_datetime: the datetime at which the event will be applied in the simulation.
    :param amount: string representation of the amount to be sent.
    :param denomination: the denomination the posting instruction will be in.
    :param target_account_id: Target customer account id for posting instruction.
    :param internal_account_id: internal account id for posting instruction.
    :param advice: If true, the posting instruction is not applied to the ledger and does not
        affect account balances. Defaults to false.
    :param target_account_address: account address to which the money should be sent.
    :param asset: asset type of the financial movement.
    :param client_transaction_id: the ID of the client transaction this posting
        instruction is creating or mutating.
    :param instruction_details: An optional mapping containing instruction level metadata.
    :param override: If true, allows to override certain checks for this Posting Instruction.
        Defaults to false.
    :param value_timestamp: Optional timestamp at which the Posting Instruction.
        will be applied in the simulation. Defaults to the generated insertion_timestamp.
    :param booking_timestamp: Optional timestamp at which all committed postings within the Posting
        Instruction are considered to be booked. Defaults to the generated insertion_timestamp.
    :param client_id: An id to uniquely identify a client entity across the platform.
    :param client_batch_id: An id which allows related Posting Instructions
        to be associated with each other.
    :param batch_details: A dictionary containing batch level metadata.
    :param target_sub_account_id: Optional Sub-Account ID targeting a specific Sub-Account.
    :return: SimulationEvent containing a Posting Instruction Batch instructing an
        InboundHardSettlement.
    """
    instructions = [
        PostingInstruction(
            instruction=InboundHardSettlement(
                target_account_id=target_account_id,
                internal_account_id=internal_account_id,
                amount=amount,
                denomination=denomination,
                target_account_address=target_account_address,
                asset=asset,
                advice=advice,
                target_sub_account_id=target_sub_account_id,
            ),
            client_transaction_id=client_transaction_id,
            instruction_details=instruction_details,
            override=override,
            value_timestamp=value_timestamp,
            booking_timestamp=booking_timestamp,
        )
    ]
    return create_pib_event_from_posting_instructions(
        instructions=instructions,
        event_datetime=event_datetime,
        client_id=client_id,
        client_batch_id=client_batch_id,
        batch_details=batch_details,
    )


def create_outbound_authorisation_pi_event(
    event_datetime: datetime,
    client_transaction_id: str,
    amount: str,
    denomination: str,
    target_account_id: str | None = None,
    internal_account_id: str | None = None,
    advice: bool | None = None,
    target_account_address: str | None = None,
    asset: str | None = None,
    instruction_details: dict[str, str] | None = None,
    override: bool = False,
    value_timestamp: datetime | None = None,
    booking_timestamp: datetime | None = None,
    client_id: str = "",
    client_batch_id: str = "",
    batch_details: dict[str, str] | None = None,
    target_sub_account_id: str | None = None,
) -> SimulationEvent:
    """
    Creates a SimulationEvent for a Posting Instruction Batch with an OutboundAuthorisation
    where Posting Instruction level fields can be explicitly defined.

    :param event_datetime: the datetime at which the event will be applied in the simulation.
    :param client_transaction_id: the ID of the client transaction this posting
        instruction is creating or mutating.
    :param amount: string representation of the amount to be sent.
    :param denomination: the denomination the posting instruction will be in.
    :param target_account_id: Target customer account id for posting instruction.
    :param internal_account_id: internal account id for posting instruction.
    :param advice: If true, the posting instruction is not applied to the ledger and does not
        affect account balances. Defaults to false.
    :param target_account_address: account address to which the money should be sent
    :param asset: asset type of the financial movement.
    :param instruction_details: An optional mapping containing instruction level metadata.
    :param override: If true, allows to override certain checks for this Posting Instruction.
        Defaults to false.
    :param value_timestamp: Optional timestamp at which the Posting Instruction.
        will be applied in the simulation. Defaults to the generated insertion_timestamp.
    :param booking_timestamp: Optional timestamp at which all committed postings within the Posting
        Instruction are considered to be booked. Defaults to the generated insertion_timestamp.
    :param client_id: An id to uniquely identify a client entity across the platform.
    :param client_batch_id: An id which allows related Posting Instructions
        to be associated with each other.
    :param batch_details: A dictionary containing batch level metadata.
    :param target_sub_account_id: Optional Sub-Account ID targeting a specific Sub-Account.
    :return: SimulationEvent containing a Posting Instruction Batch instructing an
        OutboundAuthorisation.
    """
    instructions = [
        PostingInstruction(
            instruction=OutboundAuthorisation(
                target_account_id=target_account_id,
                internal_account_id=internal_account_id,
                amount=amount,
                denomination=denomination,
                target_account_address=target_account_address,
                asset=asset,
                advice=advice,
                target_sub_account_id=target_sub_account_id,
            ),
            client_transaction_id=client_transaction_id,
            instruction_details=instruction_details,
            override=override,
            value_timestamp=value_timestamp,
            booking_timestamp=booking_timestamp,
        )
    ]
    return create_pib_event_from_posting_instructions(
        instructions=instructions,
        event_datetime=event_datetime,
        client_id=client_id,
        client_batch_id=client_batch_id,
        batch_details=batch_details,
    )


def create_outbound_hard_settlement_pi_event(
    event_datetime: datetime,
    amount: str,
    denomination: str,
    target_account_id: str | None = None,
    internal_account_id: str | None = None,
    advice: bool | None = None,
    target_account_address: str | None = None,
    asset: str | None = None,
    client_transaction_id: str = "",
    instruction_details: dict[str, str] | None = None,
    override: bool = False,
    value_timestamp: datetime | None = None,
    booking_timestamp: datetime | None = None,
    client_id: str = "",
    client_batch_id: str = "",
    batch_details: dict[str, str] | None = None,
    target_sub_account_id: str | None = None,
) -> SimulationEvent:
    """
    Creates a SimulationEvent for a Posting Instruction Batch with an OutboundHardSettlement
    where Posting Instruction level fields can be explicitly defined.

    :param event_datetime: the datetime at which the event will be applied in the simulation.
    :param amount: string representation of the amount to be sent.
    :param denomination: the denomination the posting instruction will be in.
    :param target_account_id: Target customer account id for posting instruction.
    :param internal_account_id: internal account id for posting instruction.
    :param advice: If true, the posting instruction is not applied to the ledger and does not
        affect account balances. Defaults to false.
    :param target_account_address: account address to which the money should be sent
    :param asset: asset type of the financial movement.
    :param client_transaction_id: the ID of the client transaction this posting
        instruction is creating or mutating.
    :param instruction_details: An optional mapping containing instruction level metadata.
    :param override: If true, allows to override certain checks for this Posting Instruction.
        Defaults to false.
    :param value_timestamp: Optional timestamp at which the Posting Instruction.
        will be applied in the simulation. Defaults to the generated insertion_timestamp.
    :param booking_timestamp: Optional timestamp at which all committed postings within the Posting
        Instruction are considered to be booked. Defaults to the generated insertion_timestamp.
    :param client_id: An id to uniquely identify a client entity across the platform.
    :param client_batch_id: An id which allows related Posting Instructions
        to be associated with each other.
    :param batch_details: A dictionary containing batch level metadata.
    :param target_sub_account_id: Optional Sub-Account ID targeting a specific Sub-Account.
    :return: SimulationEvent containing a Posting Instruction Batch instructing an
        OutboundHardSettlement.
    """
    instructions = [
        PostingInstruction(
            instruction=OutboundHardSettlement(
                target_account_id=target_account_id,
                internal_account_id=internal_account_id,
                amount=amount,
                denomination=denomination,
                advice=advice,
                target_account_address=target_account_address,
                asset=asset,
                target_sub_account_id=target_sub_account_id,
            ),
            client_transaction_id=client_transaction_id,
            instruction_details=instruction_details,
            override=override,
            value_timestamp=value_timestamp,
            booking_timestamp=booking_timestamp,
        )
    ]
    return create_pib_event_from_posting_instructions(
        instructions=instructions,
        event_datetime=event_datetime,
        client_id=client_id,
        client_batch_id=client_batch_id,
        batch_details=batch_details,
    )


def create_release_pi_event(
    event_datetime: datetime,
    client_transaction_id: str,
    require_pre_posting_hook_execution: bool = False,
    instruction_details: dict[str, str] | None = None,
    override: bool = False,
    value_timestamp: datetime | None = None,
    booking_timestamp: datetime | None = None,
    client_id: str = "",
    client_batch_id: str = "",
    batch_details: dict[str, str] | None = None,
) -> SimulationEvent:
    """
    Creates a SimulationEvent for a Posting Instruction Batch with a Release
    where Posting Instruction level fields can be explicitly defined.

    :param event_datetime: the datetime at which the event will be applied in the simulation.
    :param client_transaction_id: the ID of the client transaction this posting
        instruction is creating or mutating.
    :param require_pre_posting_hook_execution: If true, this ensures the pre-posting hook
        is executed when the settlement is processed. Defaults to false.
    :param instruction_details: An optional mapping containing instruction level metadata.
    :param override: If true, allows to override certain checks for this Posting Instruction.
        Defaults to false.
    :param value_timestamp: Optional timestamp at which the Posting Instruction.
        will be applied in the simulation. Defaults to the generated insertion_timestamp.
    :param booking_timestamp: Optional timestamp at which all committed postings within the Posting
        Instruction are considered to be booked. Defaults to the generated insertion_timestamp.
    :param client_id: An id to uniquely identify a client entity across the platform.
    :param client_batch_id: An id which allows related Posting Instructions
        to be associated with each other.
    :param batch_details: A dictionary containing batch level metadata.
    :return: SimulationEvent containing a Posting Instruction Batch instructing a Release.
    """
    instructions = [
        PostingInstruction(
            instruction=Release(require_pre_posting_hook_execution),
            client_transaction_id=client_transaction_id,
            instruction_details=instruction_details,
            override=override,
            value_timestamp=value_timestamp,
            booking_timestamp=booking_timestamp,
        )
    ]
    return create_pib_event_from_posting_instructions(
        instructions=instructions,
        event_datetime=event_datetime,
        client_id=client_id,
        client_batch_id=client_batch_id,
        batch_details=batch_details,
    )


def create_settlement_pi_event(
    event_datetime: datetime,
    client_transaction_id: str,
    amount: str,
    final: bool = False,
    require_pre_posting_hook_execution: bool = False,
    instruction_details: dict[str, str] | None = None,
    override: bool = False,
    value_timestamp: datetime | None = None,
    booking_timestamp: datetime | None = None,
    client_id: str = "",
    client_batch_id: str = "",
    batch_details: dict[str, str] | None = None,
) -> SimulationEvent:
    """
    Creates a SimulationEvent for a Posting Instruction Batch with a Settlement
    where Posting Instruction level fields can be explicitly defined.

    :param event_datetime: the datetime at which the event will be applied in the simulation.
    :param client_transaction_id: the ID of the client transaction this posting
        instruction is creating or mutating.
    :param amount: string representation of the amount to be sent.
    :param final: If true, any remaining amount authorised for the client_transaction_id will
        be released. Defaults to false.
    :param require_pre_posting_hook_execution: If true, this ensures the pre-posting hook
        is executed when the settlement is processed. Defaults to false.
    :param instruction_details: An optional mapping containing instruction level metadata.
    :param override: If true, allows to override certain checks for this Posting Instruction.
        Defaults to false.
    :param value_timestamp: Optional timestamp at which the Posting Instruction.
        will be applied in the simulation. Defaults to the generated insertion_timestamp.
    :param booking_timestamp: Optional timestamp at which all committed postings within the Posting
        Instruction are considered to be booked. Defaults to the generated insertion_timestamp.
    :param client_id: An id to uniquely identify a client entity across the platform.
    :param client_batch_id: An id which allows related Posting Instructions
        to be associated with each other.
    :param batch_details: A dictionary containing batch level metadata.
    :return: SimulationEvent containing a Posting Instruction Batch instructing a Settlement.
    """
    instructions = [
        PostingInstruction(
            instruction=Settlement(
                amount=amount,
                final=final,
                require_pre_posting_hook_execution=require_pre_posting_hook_execution,
            ),
            client_transaction_id=client_transaction_id,
            instruction_details=instruction_details,
            override=override,
            value_timestamp=value_timestamp,
            booking_timestamp=booking_timestamp,
        )
    ]
    return create_pib_event_from_posting_instructions(
        instructions=instructions,
        event_datetime=event_datetime,
        client_id=client_id,
        client_batch_id=client_batch_id,
        batch_details=batch_details,
    )


def create_transfer_pi_event(
    event_datetime: datetime,
    amount: str,
    denomination: str,
    debtor_target_account_id: str,
    creditor_target_account_id: str,
    client_transaction_id: str = "",
    instruction_details: dict[str, str] | None = None,
    override: bool = False,
    value_timestamp: datetime | None = None,
    booking_timestamp: datetime | None = None,
    client_id: str = "",
    client_batch_id: str = "",
    batch_details: dict[str, str] | None = None,
    debtor_target_sub_account_id: str | None = None,
    creditor_target_sub_account_id: str | None = None,
    debtor_target_account_address: str | None = None,
    creditor_target_account_address: str | None = None,
) -> SimulationEvent:
    """
    Creates a SimulationEvent for a Posting Instruction Batch with a Transfer
    where Posting Instruction level fields can be explicitly defined.

    :param event_datetime: the datetime at which the event will be applied in the simulation.
    :param amount: string representation of the amount to be sent.
    :param denomination: the denomination the posting instruction will be in.
    :param debtor_target_account_id: account to debit for Transfer.
    :param creditor_target_account_id: account to credit for Transfer.
    :param client_transaction_id: the ID of the client transaction this posting
        instruction is creating or mutating.
    :param instruction_details: An optional mapping containing instruction level metadata.
    :param override: If true, allows to override certain checks for this Posting Instruction.
        Defaults to false.
    :param value_timestamp: Optional timestamp at which the Posting Instruction.
        will be applied in the simulation. Defaults to the generated insertion_timestamp.
    :param booking_timestamp: Optional timestamp at which all committed postings within the Posting
        Instruction are considered to be booked. Defaults to the generated insertion_timestamp.
    :param client_id: An id to uniquely identify a client entity across the platform.
    :param client_batch_id: An id which allows related Posting Instructions
        to be associated with each other.
    :param batch_details: A dictionary containing batch level metadata.
    :param debtor_target_sub_account_id: Optional Sub-Account ID targeting a specific
        debtor Sub-Account.
    :param creditor_target_sub_account_id: Optional Sub-Account ID targeting a specific
        creditor Sub-Account.
    :param debtor_target_account_address: Optional address targeting a specific debtor address.
    :param creditor_target_account_address: Optional address targeting a specific creditor address.
    :return: SimulationEvent containing a Posting Instruction Batch instructing a Transfer.
    """
    instructions = [
        PostingInstruction(
            instruction=Transfer(
                amount=amount,
                denomination=denomination,
                creditor_target_account_id=creditor_target_account_id,
                debtor_target_account_id=debtor_target_account_id,
                debtor_target_sub_account_id=debtor_target_sub_account_id,
                creditor_target_sub_account_id=creditor_target_sub_account_id,
                debtor_target_account_address=debtor_target_account_address,
                creditor_target_account_address=creditor_target_account_address,
            ),
            client_transaction_id=client_transaction_id,
            instruction_details=instruction_details,
            override=override,
            value_timestamp=value_timestamp,
            booking_timestamp=booking_timestamp,
        )
    ]

    return create_pib_event_from_posting_instructions(
        instructions=instructions,
        event_datetime=event_datetime,
        client_id=client_id,
        client_batch_id=client_batch_id,
        batch_details=batch_details,
    )


def create_pib_event_from_posting_instructions(
    event_datetime: datetime,
    instructions: Sequence[PostingInstruction],
    client_id: str = "",
    client_batch_id: str = "",
    batch_details: dict[str, str] | None = None,
) -> SimulationEvent:
    return SimulationEvent(
        event_datetime,
        create_pib_from_posting_instructions(
            posting_instructions=instructions,
            client_id=client_id,
            client_batch_id=client_batch_id,
            batch_details=batch_details,
        ),
    )
