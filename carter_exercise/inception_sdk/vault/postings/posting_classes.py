# Copyright @ 2020 - 2024 Thought Machine Group Limited. All rights reserved.

# standard libs
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any, Sequence

# inception sdk
from inception_sdk.test_framework.common.date_helper import isoformat

DEFAULT_INTERNAL_ACCOUNT = "1"
DEFAULT_TARGET_ACCOUNT = "Main account"
DEFAULT_CLIENT_ID = "InceptionSDKE2EPostingsAPIClient"
DEFAULT_CLIENT_BATCH_ID = str(uuid.uuid4())
DEFAULT_CLIENT_TRANSACTION_ID = str(uuid.uuid4())
DEFAULT_DENOMINATION = "GBP"
DEFAULT_ADVICE = False
DEFAULT_FINAL = False
DEFAULT_ASSET = "COMMERCIAL_BANK_MONEY"
DEFAULT_OVERRIDE_ALL = False
DEFAULT_REQUIRE_PRE_POSTING_HOOK_EXECUTION = False
DEFAULT_ADDRESS = "DEFAULT"


class Override:
    """
    This class provides the ability to instruct posting batches
    to ignore any or all restrictions on an account.
    Please note that `.to_dict()` must be called when the object is passed into vault_caller.
    """

    def __init__(self, override_all=DEFAULT_OVERRIDE_ALL, restriction_ids=None):
        self.override_all = override_all
        self.restriction_ids = restriction_ids or []

    def to_dict(self):
        return self.__dict__ if self.override_all or self.restriction_ids else {}


class Instruction(ABC):
    def __init__(
        self,
        type: str,  # noqa: A002 - aligned this to Core API
        instruction_details: dict[str, str] | None = None,
    ):
        self.type = type
        self.instruction_details = instruction_details

    @abstractmethod
    def to_dict(self) -> dict[str, Any]:
        raise NotImplementedError("Implemented in subclasses.")


class OutboundAuthorisation(Instruction):
    """
    This class represents an Outbound Authorisation Posting Instruction type

    Args:
        param amount: string representation of the amount to be sent
        param target_account_id: account from which the money should be authorised
        param denomination: denomination in which the money should be sent
        param internal_account_id: account to which the money should be sent
        param advice: if true, the amount will be authorised regardless of balance checks
        param payment_device_token: payment_device_token to which the money should be sent
        param instruction_details: dict of free form information about the posting instruction
        param target_account_address: address to which the money should be sent
        param asset: asset type of the financial movement
        param target_sub_account_id: the sub-account from which the money should be authorised
    """

    def __init__(
        self,
        amount: Decimal | str,
        target_account_id: str | None = None,
        denomination: str | None = None,
        internal_account_id: str | None = None,
        advice: bool | None = None,
        payment_device_token: str | None = None,
        instruction_details: dict[str, str] | None = None,
        target_account_address: str | None = None,
        asset: str | None = None,
        target_sub_account_id: str | None = None,
    ):
        denomination = denomination or DEFAULT_DENOMINATION
        super().__init__("outbound_authorisation", instruction_details)
        self.payment_device_token = payment_device_token
        self.target_account_id = target_account_id or DEFAULT_TARGET_ACCOUNT
        self.internal_account_id = internal_account_id or DEFAULT_INTERNAL_ACCOUNT
        self.advice = advice or DEFAULT_ADVICE
        self.target_account_address = target_account_address
        self.asset = asset
        self.amount = amount
        self.denomination = denomination
        if payment_device_token:
            self.target_account = {"payment_device_token": self.payment_device_token}
        else:
            self.target_account = {"account_id": self.target_account_id}
        self.target_sub_account_id = target_sub_account_id

    def to_dict(self):
        d = {
            self.type: {
                "amount": str(self.amount),
                "denomination": self.denomination,
                "target_account": self.target_account,
                "internal_account_id": self.internal_account_id,
                "advice": self.advice,
                "instruction_details": self.instruction_details,
            }
        }

        if self.asset is not None:
            d[self.type]["asset"] = self.asset

        if self.target_account_address is not None:
            d[self.type]["target_account_address"] = self.target_account_address

        if self.target_sub_account_id is not None:
            d[self.type]["target_sub_account_id"] = self.target_sub_account_id

        return d


class InboundAuthorisation(Instruction):
    """
    This class represents an Inbound Authorisation Posting Instruction type

    Args:
        param amount: string representation of the amount to be sent
        param target_account_id: account to which the money should be sent
        param denomination: denomination in which the money should be sent
        param internal_account_id: account from which the money should be authorised
        param advice: if true, the amount will be authorised regardless of balance check
        param payment_device_token: payment_device_token to which the money should be sent
        param instruction_details: dict of free form information about the posting instruction
        param target_account_address: address to which the money should be sent
        param asset: asset type of the financial movement
        param target_sub_account_id: the sub-account to which the money should be sent
    """

    def __init__(
        self,
        amount: Decimal | str,
        target_account_id: str | None = None,
        denomination: str | None = None,
        internal_account_id: str | None = None,
        advice: bool | None = None,
        payment_device_token: str | None = None,
        instruction_details: dict[str, str] | None = None,
        target_account_address: str | None = None,
        asset: str | None = None,
        target_sub_account_id: str | None = None,
    ):
        denomination = denomination or DEFAULT_DENOMINATION
        super().__init__("inbound_authorisation", instruction_details)
        self.payment_device_token = payment_device_token
        self.target_account_id = target_account_id or DEFAULT_TARGET_ACCOUNT
        self.internal_account_id = internal_account_id or DEFAULT_INTERNAL_ACCOUNT
        self.advice = advice or DEFAULT_ADVICE
        self.target_account_address = target_account_address
        self.asset = asset
        self.amount = amount
        self.denomination = denomination
        self.target_sub_account_id = target_sub_account_id
        if payment_device_token:
            self.target_account = {"payment_device_token": self.payment_device_token}
        else:
            self.target_account = {"account_id": self.target_account_id}

    def to_dict(self):
        d = {
            self.type: {
                "amount": str(self.amount),
                "denomination": self.denomination,
                "target_account": self.target_account,
                "internal_account_id": self.internal_account_id,
                "advice": self.advice,
                "instruction_details": self.instruction_details,
            }
        }

        if self.asset is not None:
            d[self.type]["asset"] = self.asset

        if self.target_account_address is not None:
            d[self.type]["target_account_address"] = self.target_account_address

        if self.target_sub_account_id is not None:
            d[self.type]["target_sub_account_id"] = self.target_sub_account_id

        return d


class AuthorisationAdjustment(Instruction):
    """
    This class represents an Authorisation Adjustment Instruction type

    Args:
        param amount: delta amount to be sent. Cannot be used in conjunction
        with `replacement_amount`
        param advice: if true, the amount will be authorised regardless of balance check
        param instruction_details: dict of free form information about the posting instruction
        param replacement_amount: new total authorised amount. Cannot be used in conjunction
        with `amount`
    """

    def __init__(
        self,
        amount: Decimal | str | None = None,
        advice: bool | None = None,
        instruction_details: dict[str, str] | None = None,
        replacement_amount: Decimal | str | None = None,
    ):
        if (amount is None and replacement_amount is None) or (
            amount is not None and replacement_amount is not None
        ):
            raise ValueError("Exactly one of 'amount' or 'replacement_amount' must be provided.")

        super().__init__("authorisation_adjustment", instruction_details)
        self.advice = advice or DEFAULT_ADVICE
        self.amount = amount
        self.replacement_amount = replacement_amount

    def to_dict(self):
        d = {
            self.type: {
                "advice": self.advice,
                "instruction_details": self.instruction_details,
            }
        }

        if self.amount is not None:
            d[self.type]["amount"] = str(self.amount)
        elif self.replacement_amount is not None:
            d[self.type]["replacement_amount"] = str(self.replacement_amount)

        return d


class Settlement(Instruction):
    """
    This class represents a Settlement Instruction type

    Args:
        param amount: string representation of the amount to be sent
        param final: if true, the amount will be overwritten by the full
            authorisation amount
        param require_pre_posting_hook_execution: if true, the pre-posting
            hook will be triggered for this instruction
        param instruction_details: dict of free form information about the
            posting instruction
    """

    def __init__(
        self,
        amount: Decimal | str,
        final: bool = DEFAULT_FINAL,
        require_pre_posting_hook_execution: bool = False,
        instruction_details: dict[str, str] | None = None,
    ):
        super().__init__("settlement", instruction_details)
        self.final = final
        self.require_pre_posting_hook_execution = require_pre_posting_hook_execution
        self.amount = amount

    def to_dict(self):
        return {
            self.type: {
                "amount": str(self.amount),
                "final": self.final,
                "require_pre_posting_hook_execution": self.require_pre_posting_hook_execution,
                "instruction_details": self.instruction_details,
            }
        }


class Release(Instruction):
    """
    This class represents a Release Instruction type
    Args:
        param require_pre_posting_hook_execution: if true, the pre-posting
            hook will be triggered for this instruction
        param instruction_details: dict of free form information about the
            posting instruction
    """

    def __init__(
        self,
        require_pre_posting_hook_execution: bool = False,
        instruction_details: dict[str, str] | None = None,
    ):
        super().__init__("release", instruction_details)
        self.require_pre_posting_hook_execution = require_pre_posting_hook_execution

    def to_dict(self):
        return {
            self.type: {
                "require_pre_posting_hook_execution": self.require_pre_posting_hook_execution,
                "instruction_details": self.instruction_details,
            }
        }


class InboundHardSettlement(Instruction):
    """
    This class represents an Inbound Hard Settlement Posting Instruction type

    Args:
        param amount: string representation of the amount to be sent
        param target_account_id: account to which the money should be sent
        param denomination: denomination in which the money should be sent
        param internal_account_id: account from which the money should be authorised
        param advice: if true, the amount will be authorised regardless of balance check
        param payment_device_token: payment_device_token to which the money should be sent
        param instruction_details: dict of free form information about the posting instruction
        param target_account_address: address to which the money should be sent
        param asset: asset type of the financial movement
        param target_sub_account_id: sub-account to which the money should be sent
    """

    def __init__(
        self,
        amount: Decimal | str,
        target_account_id: str | None = None,
        denomination: str | None = None,
        internal_account_id: str | None = None,
        advice: bool | None = None,
        payment_device_token: str | None = None,
        instruction_details: dict[str, str] | None = None,
        target_account_address: str | None = None,
        asset: str | None = None,
        target_sub_account_id: str | None = None,
    ):
        denomination = denomination or DEFAULT_DENOMINATION
        super().__init__("inbound_hard_settlement", instruction_details)
        self.payment_device_token = payment_device_token
        self.target_account_id = target_account_id or DEFAULT_TARGET_ACCOUNT
        self.internal_account_id = internal_account_id or DEFAULT_INTERNAL_ACCOUNT
        self.advice = advice or DEFAULT_ADVICE
        self.target_account_address = target_account_address
        self.asset = asset
        self.amount = amount
        self.denomination = denomination
        self.target_sub_account_id = target_sub_account_id
        if payment_device_token:
            self.target_account = {"payment_device_token": self.payment_device_token}
        else:
            self.target_account = {"account_id": self.target_account_id}

    def to_dict(self):
        d = {
            self.type: {
                "amount": str(self.amount),
                "denomination": self.denomination,
                "target_account": self.target_account,
                "internal_account_id": self.internal_account_id,
                "advice": self.advice,
                "instruction_details": self.instruction_details,
            }
        }

        if self.asset is not None:
            d[self.type]["asset"] = self.asset

        if self.target_account_address is not None:
            d[self.type]["target_account_address"] = self.target_account_address

        if self.target_sub_account_id is not None:
            d[self.type]["target_sub_account_id"] = self.target_sub_account_id

        return d


class OutboundHardSettlement(Instruction):
    """
    This class represents an Outbound Hard Settlement Posting Instruction type

    Args:
        param amount: string representation of the amount to be sent
        param target_account_id: account to which the money should be sent
        param denomination: denomination in which the money should be sent
        param internal_account_id: account from which the money should be authorised
        param advice: if true, the amount will be authorised regardless of balance check
        param payment_device_token: payment_device_token to which the money should be sent
        param instruction_details: dict of free form information about the posting instruction
        param target_account_address: address to which the money should be sent
        param asset: asset type of the financial movement
        param target_sub_account_id: sub-account to which the money should be sent
    """

    def __init__(
        self,
        amount: Decimal | str,
        target_account_id: str | None = None,
        denomination: str | None = None,
        internal_account_id: str | None = None,
        advice: bool | None = None,
        payment_device_token: str | None = None,
        instruction_details: dict[str, str] | None = None,
        target_account_address: str | None = None,
        asset: str | None = None,
        target_sub_account_id: str | None = None,
    ):
        denomination = denomination or DEFAULT_DENOMINATION
        super().__init__("outbound_hard_settlement", instruction_details)
        self.payment_device_token = payment_device_token
        self.target_account_id = target_account_id or DEFAULT_TARGET_ACCOUNT
        self.internal_account_id = internal_account_id or DEFAULT_INTERNAL_ACCOUNT
        self.advice = advice or DEFAULT_ADVICE
        self.target_account_address = target_account_address
        self.asset = asset
        self.amount = amount
        self.denomination = denomination
        self.target_sub_account_id = target_sub_account_id
        if payment_device_token:
            self.target_account = {"payment_device_token": self.payment_device_token}
        else:
            self.target_account = {"account_id": self.target_account_id}

    def to_dict(self):
        d = {
            self.type: {
                "amount": str(self.amount),
                "denomination": self.denomination,
                "target_account": self.target_account,
                "internal_account_id": self.internal_account_id,
                "advice": self.advice,
                "instruction_details": self.instruction_details,
            }
        }

        if self.asset is not None:
            d[self.type]["asset"] = self.asset

        if self.target_account_address is not None:
            d[self.type]["target_account_address"] = self.target_account_address

        if self.target_sub_account_id is not None:
            d[self.type]["target_sub_account_id"] = self.target_sub_account_id

        return d


class Transfer(Instruction):
    """
    This class represents a Transfer Posting Instruction type

    Args:
        param amount: string representation of the amount to be sent
        param debtor_target_account: account from which the money should be sent
        param creditor_target_account: account to which the money should be sent
        param denomination: denomination in which the money should be sent
        param instruction_details: dict of free form information about the posting instruction.
        param debtor_target_sub_account_id: sub-account from which the money should be sent
        param creditor_target_sub_account_id: sub-account to which the money should be sent
    """

    def __init__(
        self,
        amount: Decimal | str,
        debtor_target_account_id: str,
        creditor_target_account_id: str,
        denomination: str | None = None,
        debtor_target_sub_account_id: str | None = None,
        creditor_target_sub_account_id: str | None = None,
        instruction_details: dict[str, str] | None = None,
        creditor_target_account_address: str | None = None,
        debtor_target_account_address: str | None = None,
    ):
        denomination = denomination or DEFAULT_DENOMINATION
        super().__init__("transfer", instruction_details)
        self.debtor_target_account_id = debtor_target_account_id
        self.creditor_target_account_id = creditor_target_account_id
        self.amount = amount
        self.debtor_target_sub_account_id = debtor_target_sub_account_id
        self.creditor_target_sub_account_id = creditor_target_sub_account_id
        self.denomination = denomination
        self.creditor_target_account_address = creditor_target_account_address
        self.debtor_target_account_address = debtor_target_account_address

    def to_dict(self):
        transfer_dict = {
            self.type: {
                "amount": str(self.amount),
                "denomination": self.denomination,
                "debtor_target_account": {
                    "account_id": self.debtor_target_account_id,
                },
                "creditor_target_account": {
                    "account_id": self.creditor_target_account_id,
                },
                "instruction_details": self.instruction_details,
            }
        }

        # Debtor and creditor target accounts addresses are only supported when posting
        # to a sub-account:
        if self.debtor_target_sub_account_id is not None:
            transfer_dict[self.type][
                "debtor_target_sub_account_id"
            ] = self.debtor_target_sub_account_id
            transfer_dict[self.type][
                "debtor_target_account_address"
            ] = self.debtor_target_account_address

        if self.creditor_target_sub_account_id is not None:
            transfer_dict[self.type][
                "creditor_target_sub_account_id"
            ] = self.creditor_target_sub_account_id
            transfer_dict[self.type][
                "creditor_target_account_address"
            ] = self.creditor_target_account_address

        return transfer_dict


class Posting:
    def __init__(
        self,
        account_id: str,
        amount,
        credit,
        denomination: str | None = None,
        asset: str | None = None,
        account_address: str | None = None,
        phase: str | None = None,
        sub_account_id: str | None = None,
    ):
        self.account_id = account_id
        self.amount = amount
        self.denomination = denomination or DEFAULT_DENOMINATION
        self.asset = asset or DEFAULT_ASSET
        self.account_address = account_address or "DEFAULT"
        self.phase = phase or "POSTING_PHASE_COMMITTED"
        self.credit = credit
        self.sub_account_id = sub_account_id

    def to_dict(self):
        posting_dict = {
            "account_id": self.account_id,
            "amount": str(self.amount),
            "denomination": self.denomination,
            "asset": self.asset,
            "account_address": self.account_address,
            "phase": self.phase,
            "credit": self.credit,
        }

        if self.sub_account_id is not None:
            posting_dict["sub_account_id"] = self.sub_account_id

        return posting_dict


class CustomInstruction(Instruction):
    """
    This class represents a Custom Posting Instruction type

    Args:
        param postings: Posting instruction batch
        param instruction_details: dict of free form information about the posting instruction
    """

    def __init__(
        self,
        postings: Sequence[Posting],
        instruction_details: dict[str, str] | None = None,
    ):
        super().__init__("custom_instruction", instruction_details)
        self.postings = postings

    def to_dict(self):
        return {
            self.type: {
                "postings": [post.to_dict() for post in self.postings],
                "instruction_details": self.instruction_details,
            }
        }


class PostingInstruction:
    """
    This class represents an individual posting instruction object.

    Args:
        param instruction: the instruction object, must be a supported posting instruction type.
        param client_transaction_id: id to identify and correlate this posting instruction.
        param instruction_details: dict of free form information about the posting instruction.
        param override: object that defines which restrictions should be overwritten if any.
        param value_timestamp: optional time at which all committed postings of this posting
            instruction will affect balances.
        param booking_timestamp: optional time at which all committed postings of this posting
            instruction will be booked.
    """

    def __init__(
        self,
        instruction: Instruction,
        client_transaction_id=None,
        instruction_details: dict[str, str] | None = None,
        override: bool = False,
        value_timestamp: datetime | str | None = None,
        booking_timestamp: datetime | str | None = None,
    ):
        if override:
            override_obj = Override(override_all=True)
        else:
            override_obj = Override()
        self.client_transaction_id = client_transaction_id or str(uuid.uuid4())
        self.instruction_details = instruction_details or {}
        self.override = override_obj
        self.instruction = instruction
        self.value_timestamp = value_timestamp
        self.booking_timestamp = booking_timestamp

    def to_dict(self):
        return {
            "client_transaction_id": self.client_transaction_id,
            "instruction_details": (
                self.instruction.instruction_details
                if hasattr(self.instruction, "instruction_details")
                and self.instruction.instruction_details
                else self.instruction_details
            ),
            "override": self.override.to_dict(),
            "value_timestamp": isoformat(self.value_timestamp),
            "booking_timestamp": isoformat(self.booking_timestamp),
            **self.instruction.to_dict(),
        }


class PostingInstructionBatch:
    """
    This class represents a Posting Instruction Batch event that can be consumed
    by the Simulation endpoint and the Postings API to instruct the movement of money.
    Please note that `.to_dict()` must be called when the object is passed into vault_caller.

    Args:
        param posting_instructions: a list of PostingInstruction objects.
        param value_timestamp: a datetime, or isoformat string of a datetime, of the
            effective_datetime of the posting instruction batch. Deprecated as of
            release 5.5, use value_timestamp at the posting instruction level.
            Not deprecated in the Postings Migration API.
        param booking_timestamp: the accounting datetime. Deprecated as of
            release 5.5, use booking_timestamp at the posting instruction level.
            Not deprecated in the Postings Migration API.
        param client_batch_id: an id that allows to correlate multiple
            Posting Instruction Batches together.
        param client_id: id of the client Vault should use to fulfil the postings.
        param batch_details: free from dict containing extra information about the PIB.
    """

    def __init__(
        self,
        posting_instructions: Sequence[PostingInstruction],
        value_timestamp: datetime | str | None = None,
        booking_timestamp: datetime | str | None = None,
        client_batch_id: str | None = None,
        client_id: str | None = None,
        batch_details: dict[str, str] | None = None,
    ):
        # TODO(INC-10286): move our custom defaulting out of the base classes and into helpers
        self.batch_details = batch_details or {}
        self.client_id = client_id or DEFAULT_CLIENT_ID
        self.client_batch_id = client_batch_id or DEFAULT_CLIENT_BATCH_ID
        self.value_timestamp = value_timestamp
        self.booking_timestamp = booking_timestamp
        self.posting_instructions = posting_instructions

    def to_dict(self):
        d = dict(
            client_id=self.client_id,
            client_batch_id=self.client_batch_id,
            posting_instructions=[post.to_dict() for post in self.posting_instructions],
            batch_details=self.batch_details,
        )

        if self.value_timestamp:
            d.update(value_timestamp=isoformat(self.value_timestamp))

        if self.booking_timestamp:
            d.update(booking_timestamp=isoformat(self.booking_timestamp))

        return d


@dataclass
class PostingInstructionBatchRequest:
    """
    This class is for loading postings onto the Postings API.
    """

    request_id: str
    posting_instruction_batch: PostingInstructionBatch

    def to_dict(self):
        return dict(
            request_id=self.request_id,
            posting_instruction_batch=self.posting_instruction_batch.to_dict(),
        )


@dataclass
class MigrationPostingInstructionBatchRequest(PostingInstructionBatchRequest):
    """
    This class is for loading postings onto the Postings Migration API.
    """

    source_insert_timestamp: datetime
    account_sequence_number: int
    target_account_id: str

    def to_dict(self):
        base_d = PostingInstructionBatchRequest.to_dict(self)
        this_d = dict(
            source_insert_timestamp=self.source_insert_timestamp.isoformat(),
            account_sequence_number=str(self.account_sequence_number),
            target_account_id=self.target_account_id,
        )

        return base_d | this_d
