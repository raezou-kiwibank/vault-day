# Copyright @ 2020 - 2024 Thought Machine Group Limited. All rights reserved.
# standard libs
import uuid
from datetime import datetime
from typing import Sequence

# inception sdk
from inception_sdk.vault.postings.posting_classes import (
    Instruction,
    PostingInstruction,
    PostingInstructionBatch,
)


def create_posting_instruction_batch(
    instructions: Sequence[Instruction],
    # Deprecated as of release 5.5, use value_timestamp at the posting instruction level.
    # Not deprecated in the Postings Migration API.
    value_datetime: datetime | str | None = None,
    # Deprecated as of release 5.5, use booking_timestamp at the posting instruction level.
    # Not deprecated in the Postings Migration API.
    booking_timestamp: datetime | str | None = None,
    client_transaction_id: str = "",
    override: bool = False,
    batch_details: dict[str, str] | None = None,
    instruction_details: dict[str, str] | None = None,
    client_batch_id: str = "",
    client_id: str = "",
) -> dict[str, dict]:
    """
    In the current implementation of Inception posting framework, there
    are three levels of objects to be instantiated which helps convert
    the data into a valid json payload for posting apis, they are:

    1. Instruction
    2. PostingInstruction
    3. PostingInstructionBatch

    this helper method takes in a list of Instruction objects, instantiates
    both PostingInstruction and PostingInstructionBatch objects accordingly,
    then returns a valid dict from the final PIB object to be used as payload.

    Certain values like client_id, client_transaction_id and client_batch_id all
    have standard default values as set in the corresponding class constructors.

    The output of this helper is valid in both e2e posting api calls as well as
    simulator events.

    As Instruction objects are mostly fungible, once instantiated, the same
    object instance can be used multiple times as input of this helper, as distinguishing
    factors like client_transaction_id and timestamps all sit outside of Instruction
    """
    client_batch_id = client_batch_id or str(uuid.uuid4())
    posting_instructions = [
        PostingInstruction(
            client_transaction_id=client_transaction_id,
            override=override,
            instruction=instruction,
            instruction_details=instruction_details,
        )
        for instruction in instructions
        if isinstance(instruction, Instruction)
    ]

    return create_pib_from_posting_instructions(
        posting_instructions=posting_instructions,
        value_datetime=value_datetime,
        booking_timestamp=booking_timestamp,
        batch_details=batch_details,
        client_batch_id=client_batch_id,
        client_id=client_id,
    )


def create_pib_from_posting_instructions(
    posting_instructions: Sequence[PostingInstruction],
    # Deprecated as of release 5.5, use value_timestamp at the posting instruction level.
    # Not deprecated in the Postings Migration API.
    value_datetime: datetime | str | None = None,
    # Deprecated as of release 5.5, use booking_timestamp at the posting instruction level.
    # Not deprecated in the Postings Migration API.
    booking_timestamp: datetime | str | None = None,
    batch_details: dict[str, str] | None = None,
    client_batch_id: str = "",
    client_id: str = "",
) -> dict[str, dict]:
    """
    Create a Posting Instruction Batch from a list of Posting Instructions
    """
    client_batch_id = client_batch_id or str(uuid.uuid4())

    if value_datetime and isinstance(value_datetime, datetime):
        value_datetime = datetime.isoformat(value_datetime)

    return {
        "posting_instruction_batch": PostingInstructionBatch(
            posting_instructions=posting_instructions,
            value_timestamp=value_datetime if value_datetime else None,
            booking_timestamp=booking_timestamp,
            client_batch_id=client_batch_id,
            batch_details=batch_details,
            client_id=client_id,
        ).to_dict()
    }
