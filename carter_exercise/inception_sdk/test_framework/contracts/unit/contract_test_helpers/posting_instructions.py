# Copyright @ 2026 Thought Machine Group Limited. All rights reserved.
# standard libs
from datetime import datetime
from decimal import Decimal

# contracts api
from contracts_api import (
    DEFAULT_ADDRESS,
    DEFAULT_ASSET,
    AdjustmentAmount,
    AuthorisationAdjustment,
    CustomInstruction,
    InboundAuthorisation,
    InboundHardSettlement,
    OutboundAuthorisation,
    OutboundHardSettlement,
    Phase,
    Posting,
    Release,
    Settlement,
    TransactionCode,
    Transfer,
)

# inception sdk
from inception_sdk.test_framework.contracts.unit.contract_test_helpers.constants import (
    ACCOUNT_ID,
    CLIENT_TRANSACTION_ID,
    DEFAULT_DATETIME,
    DEFAULT_INTERNAL_ACCOUNT,
    DEFAULT_PHASE,
    POSTING_CLIENT_ID,
)


def inbound_auth(
    self,
    amount: Decimal,
    client_transaction_id: str = CLIENT_TRANSACTION_ID,
    denomination: str = "",
    target_account_id: str = ACCOUNT_ID,
    internal_account_id: str = DEFAULT_INTERNAL_ACCOUNT,
    advice: bool | None = False,
    instruction_details: dict[str, str] | None = None,
    transaction_code: TransactionCode | None = None,
    override_all_restrictions: bool | None = False,
    target_account_address: str = DEFAULT_ADDRESS,
    asset: str = DEFAULT_ASSET,
    target_sub_account_id: str | None = None,
    **kwargs,
) -> InboundAuthorisation:
    denomination = denomination or self.default_denomination
    instruction = InboundAuthorisation(
        client_transaction_id=client_transaction_id,
        amount=amount,
        denomination=denomination,
        target_account_id=target_account_id,
        internal_account_id=internal_account_id,
        advice=advice,
        instruction_details=instruction_details,
        transaction_code=transaction_code,
        override_all_restrictions=override_all_restrictions,
        target_account_address=target_account_address,
        asset=asset,
        target_sub_account_id=target_sub_account_id,
    )
    committed_postings = [
        # inbound auth => credit PENDING_IN
        Posting(
            credit=True,
            amount=amount,
            denomination=denomination,
            account_id=target_account_id,
            account_address=target_account_address,
            asset=asset,
            phase=Phase.PENDING_IN,
        ),
    ]
    instruction._set_output_attributes(
        insertion_datetime=kwargs.get("insertion_datetime"),
        value_datetime=kwargs.get("value_datetime", DEFAULT_DATETIME),
        client_batch_id=kwargs.get("client_batch_id"),
        batch_id=kwargs.get("batch_id"),
        committed_postings=committed_postings,
        instruction_id=kwargs.get("instruction_id"),
        unique_client_transaction_id=kwargs.get(
            "unique_client_transaction_id", f"{POSTING_CLIENT_ID}_{client_transaction_id}"
        ),
        client_transaction_id=client_transaction_id,
        own_account_id=kwargs.get("own_account_id", ACCOUNT_ID),
        tside=self.tside,
        client_id=kwargs.get("client_id"),
        booking_datetime=kwargs.get("booking_datetime"),
        enrichment_details=kwargs.get("enrichment_details"),
    )
    return instruction


def outbound_auth(
    self,
    amount: Decimal,
    client_transaction_id: str = CLIENT_TRANSACTION_ID,
    denomination: str = "",
    target_account_id: str = ACCOUNT_ID,
    internal_account_id: str = DEFAULT_INTERNAL_ACCOUNT,
    advice: bool | None = False,
    instruction_details: dict[str, str] | None = None,
    transaction_code: TransactionCode | None = None,
    override_all_restrictions: bool | None = False,
    target_account_address: str = DEFAULT_ADDRESS,
    asset: str = DEFAULT_ASSET,
    target_sub_account_id: str | None = None,
    **kwargs,
) -> OutboundAuthorisation:
    denomination = denomination or self.default_denomination
    instruction = OutboundAuthorisation(
        client_transaction_id=client_transaction_id,
        amount=amount,
        denomination=denomination,
        target_account_id=target_account_id,
        internal_account_id=internal_account_id,
        advice=advice,
        instruction_details=instruction_details,
        transaction_code=transaction_code,
        override_all_restrictions=override_all_restrictions,
        target_account_address=target_account_address,
        asset=asset,
        target_sub_account_id=target_sub_account_id,
    )
    committed_postings = [
        # outbound auth => debit PENDING_OUT
        Posting(
            credit=False,
            amount=amount,
            denomination=denomination,
            account_id=target_account_id,
            account_address=target_account_address,
            asset=asset,
            phase=Phase.PENDING_OUT,
        ),
    ]
    instruction._set_output_attributes(
        insertion_datetime=kwargs.get("insertion_datetime"),
        value_datetime=kwargs.get("value_datetime", DEFAULT_DATETIME),
        client_batch_id=kwargs.get("client_batch_id"),
        batch_id=kwargs.get("batch_id"),
        committed_postings=committed_postings,
        instruction_id=kwargs.get("instruction_id"),
        unique_client_transaction_id=kwargs.get(
            "unique_client_transaction_id", f"{POSTING_CLIENT_ID}_{client_transaction_id}"
        ),
        client_transaction_id=client_transaction_id,
        own_account_id=kwargs.get("own_account_id", ACCOUNT_ID),
        tside=self.tside,
        booking_datetime=kwargs.get("booking_datetime"),
        client_id=kwargs.get("client_id"),
        enrichment_details=kwargs.get("enrichment_details"),
    )
    return instruction


def inbound_auth_adjust(
    self,
    # Deprecated: Use adjustment_amount.
    amount: Decimal | None = None,
    client_transaction_id: str = CLIENT_TRANSACTION_ID,
    advice: bool | None = False,
    instruction_details: dict[str, str] | None = None,
    transaction_code: TransactionCode | None = None,
    override_all_restrictions: bool | None = False,
    adjustment_amount: AdjustmentAmount | None = None,
    # ----- output values
    _authorised_amount: Decimal | None = None,
    _delta_amount: Decimal | None = None,
    _denomination: str = "",
    _target_account_id: str = ACCOUNT_ID,
    _internal_account_id: str = DEFAULT_INTERNAL_ACCOUNT,
    **kwargs,
) -> AuthorisationAdjustment:
    if adjustment_amount is None:
        if amount is None:
            raise ValueError("Must provide either 'amount' or 'adjustment_amount'.")
        adjustment_amount = AdjustmentAmount(amount=amount)

    resolved_amount = adjustment_amount.amount or adjustment_amount.replacement_amount
    assert resolved_amount is not None
    resolved_amount = Decimal(resolved_amount)

    instruction = AuthorisationAdjustment(
        client_transaction_id=client_transaction_id,
        adjustment_amount=adjustment_amount,
        advice=advice,
        instruction_details=instruction_details,
        transaction_code=transaction_code,
        override_all_restrictions=override_all_restrictions,
    )
    committed_postings = [
        Posting(
            credit=resolved_amount > 0,  # credit account if amount > 0
            amount=abs(resolved_amount),
            denomination=_denomination or self.default_denomination,
            account_id=_target_account_id,
            account_address=DEFAULT_ADDRESS,
            asset=DEFAULT_ASSET,
            phase=Phase.PENDING_IN,  # inbound => PENDING_IN
        ),
    ]
    instruction._set_output_attributes(
        insertion_datetime=kwargs.get("insertion_datetime"),
        value_datetime=kwargs.get("value_datetime", DEFAULT_DATETIME),
        client_batch_id=kwargs.get("client_batch_id"),
        batch_id=kwargs.get("batch_id"),
        committed_postings=committed_postings,
        instruction_id=kwargs.get("instruction_id"),
        unique_client_transaction_id=kwargs.get(
            "unique_client_transaction_id", f"{POSTING_CLIENT_ID}_{client_transaction_id}"
        ),
        client_transaction_id=client_transaction_id,
        own_account_id=kwargs.get("own_account_id", ACCOUNT_ID),
        tside=self.tside,
        authorised_amount=kwargs.get("authorised_amount", _authorised_amount),
        delta_amount=kwargs.get("delta_amount", _delta_amount),
        denomination=kwargs.get("denomination", _denomination or self.default_denomination),
        target_account_id=kwargs.get("target_account_id", _target_account_id),
        internal_account_id=kwargs.get("internal_account_id", _internal_account_id),
        booking_datetime=kwargs.get("booking_datetime"),
        client_id=kwargs.get("client_id"),
        enrichment_details=kwargs.get("enrichment_details"),
    )
    return instruction


def outbound_auth_adjust(
    self,
    # Deprecated: Use adjustment_amount.
    amount: Decimal | None = None,
    client_transaction_id: str = CLIENT_TRANSACTION_ID,
    advice: bool | None = False,
    instruction_details: dict[str, str] | None = None,
    transaction_code: TransactionCode | None = None,
    override_all_restrictions: bool | None = False,
    adjustment_amount: AdjustmentAmount | None = None,
    # ----- output values
    _authorised_amount: Decimal | None = None,
    _delta_amount: Decimal | None = None,
    _denomination: str | None = None,
    _target_account_id: str = ACCOUNT_ID,
    _internal_account_id: str = DEFAULT_INTERNAL_ACCOUNT,
    **kwargs,
) -> AuthorisationAdjustment:
    if adjustment_amount is None:
        if amount is None:
            raise ValueError("Must provide either 'amount' or 'adjustment_amount'.")
        adjustment_amount = AdjustmentAmount(amount=amount)

    resolved_amount = adjustment_amount.amount or adjustment_amount.replacement_amount
    assert resolved_amount is not None
    resolved_amount = Decimal(resolved_amount)

    instruction = AuthorisationAdjustment(
        client_transaction_id=client_transaction_id,
        adjustment_amount=adjustment_amount,
        advice=advice,
        instruction_details=instruction_details,
        transaction_code=transaction_code,
        override_all_restrictions=override_all_restrictions,
    )
    committed_postings = [
        Posting(
            credit=not (resolved_amount > 0),  # debit account if amount > 0
            amount=abs(resolved_amount),
            denomination=_denomination or self.default_denomination,
            account_id=_target_account_id,
            account_address=DEFAULT_ADDRESS,
            asset=DEFAULT_ASSET,
            phase=Phase.PENDING_OUT,  # outbound => PENDING_OUT
        )
    ]
    instruction._set_output_attributes(
        insertion_datetime=kwargs.get("insertion_datetime"),
        value_datetime=kwargs.get("value_datetime", DEFAULT_DATETIME),
        client_batch_id=kwargs.get("client_batch_id"),
        batch_id=kwargs.get("batch_id"),
        committed_postings=committed_postings,
        instruction_id=kwargs.get("instruction_id"),
        unique_client_transaction_id=kwargs.get(
            "unique_client_transaction_id", f"{POSTING_CLIENT_ID}_{client_transaction_id}"
        ),
        client_transaction_id=client_transaction_id,
        own_account_id=kwargs.get("own_account_id", ACCOUNT_ID),
        tside=self.tside,
        authorised_amount=kwargs.get("authorised_amount", _authorised_amount),
        delta_amount=kwargs.get("delta_amount", _delta_amount),
        denomination=kwargs.get("denomination", _denomination or self.default_denomination),
        target_account_id=kwargs.get("target_account_id", _target_account_id),
        internal_account_id=kwargs.get("internal_account_id", _internal_account_id),
        booking_datetime=kwargs.get("booking_datetime"),
        client_id=kwargs.get("client_id"),
        enrichment_details=kwargs.get("enrichment_details"),
    )
    return instruction


def settle_inbound_auth(
    self,
    unsettled_amount: Decimal,
    amount: Decimal | None = None,  # TODO: link with client transaction
    client_transaction_id: str = CLIENT_TRANSACTION_ID,
    final: bool | None = False,
    instruction_details: dict[str, str] | None = None,
    transaction_code: TransactionCode | None = None,
    override_all_restrictions: bool | None = False,
    # ----- output values
    _denomination: str = "",
    _target_account_id: str = ACCOUNT_ID,
    _internal_account_id: str = DEFAULT_INTERNAL_ACCOUNT,
    **kwargs,
) -> Settlement:
    amount = amount or unsettled_amount
    pending_amount = unsettled_amount if final else min(amount, unsettled_amount)

    instruction = Settlement(
        client_transaction_id=client_transaction_id,
        amount=amount,
        final=final,
        instruction_details=instruction_details,
        transaction_code=transaction_code,
        override_all_restrictions=override_all_restrictions,
        _from_proto=kwargs.get("_from_proto", False),
    )
    committed_postings = [
        Posting(
            # inbound auth is crediting PENDING_IN=> settlement is debiting
            credit=False,
            amount=pending_amount,
            denomination=_denomination or self.default_denomination,
            account_id=_target_account_id,
            account_address=DEFAULT_ADDRESS,
            asset=DEFAULT_ASSET,
            phase=Phase.PENDING_IN,
            _from_proto=kwargs.get("_from_proto", False),
        ),
        Posting(
            credit=True,  # settle inbound => True
            amount=amount,
            denomination=_denomination or self.default_denomination,
            account_id=_target_account_id,
            account_address=DEFAULT_ADDRESS,
            asset=DEFAULT_ASSET,
            phase=DEFAULT_PHASE,
            _from_proto=kwargs.get("_from_proto", False),
        ),
    ]
    instruction._set_output_attributes(
        insertion_datetime=kwargs.get("insertion_datetime"),
        value_datetime=kwargs.get("value_datetime", DEFAULT_DATETIME),
        client_batch_id=kwargs.get("client_batch_id"),
        batch_id=kwargs.get("batch_id"),
        committed_postings=committed_postings,
        instruction_id=kwargs.get("instruction_id"),
        unique_client_transaction_id=kwargs.get(
            "unique_client_transaction_id", f"{POSTING_CLIENT_ID}_{client_transaction_id}"
        ),
        client_transaction_id=client_transaction_id,
        own_account_id=kwargs.get("own_account_id", ACCOUNT_ID),
        tside=self.tside,
        denomination=kwargs.get("denomination", _denomination or self.default_denomination),
        target_account_id=kwargs.get("target_account_id", _target_account_id),
        internal_account_id=kwargs.get("internal_account_id", _internal_account_id),
        booking_datetime=kwargs.get("booking_datetime"),
        client_id=kwargs.get("client_id"),
        enrichment_details=kwargs.get("enrichment_details"),
    )
    return instruction


def settle_outbound_auth(
    self,
    unsettled_amount: Decimal,
    amount: Decimal | None = None,  # TODO: link with client transaction
    client_transaction_id: str = CLIENT_TRANSACTION_ID,
    final: bool | None = False,
    instruction_details: dict[str, str] | None = None,
    transaction_code: TransactionCode | None = None,
    override_all_restrictions: bool | None = False,
    # ----- output values
    _denomination: str = "",
    _target_account_id: str = ACCOUNT_ID,
    _internal_account_id: str = DEFAULT_INTERNAL_ACCOUNT,
    **kwargs,
) -> Settlement:
    """
    - unsettled_amount: this can be used as the amount if the settlement is final
    and has no amount, or to zero out any pending_in/out phase balances if the
     settlement has an amount > ringfenced amount
    """
    amount = amount or unsettled_amount
    pending_amount = unsettled_amount if final else min(amount, unsettled_amount)

    instruction = Settlement(
        client_transaction_id=client_transaction_id,
        amount=amount,
        final=final,
        instruction_details=instruction_details,
        transaction_code=transaction_code,
        override_all_restrictions=override_all_restrictions,
        _from_proto=kwargs.get("_from_proto", False),
    )
    committed_postings = [
        Posting(
            # outbound auth is debiting PENDING_OUT => settlement is credit
            credit=True,
            amount=pending_amount,
            denomination=_denomination or self.default_denomination,
            account_id=_target_account_id,
            account_address=DEFAULT_ADDRESS,
            asset=DEFAULT_ASSET,
            phase=Phase.PENDING_OUT,
            _from_proto=kwargs.get("_from_proto", False),
        ),
        Posting(
            credit=False,  # settle outbound => False
            amount=amount,
            denomination=_denomination or self.default_denomination,
            account_id=_target_account_id,
            account_address=DEFAULT_ADDRESS,
            asset=DEFAULT_ASSET,
            phase=DEFAULT_PHASE,
            _from_proto=kwargs.get("_from_proto", False),
        ),
    ]
    instruction._set_output_attributes(
        insertion_datetime=kwargs.get("insertion_datetime"),
        value_datetime=kwargs.get("value_datetime", DEFAULT_DATETIME),
        client_batch_id=kwargs.get("client_batch_id"),
        batch_id=kwargs.get("batch_id"),
        committed_postings=committed_postings,
        instruction_id=kwargs.get("instruction_id"),
        unique_client_transaction_id=kwargs.get(
            "unique_client_transaction_id", f"{POSTING_CLIENT_ID}_{client_transaction_id}"
        ),
        client_transaction_id=client_transaction_id,
        own_account_id=kwargs.get("own_account_id", ACCOUNT_ID),
        tside=self.tside,
        denomination=kwargs.get("denomination", _denomination or self.default_denomination),
        target_account_id=kwargs.get("target_account_id", _target_account_id),
        internal_account_id=kwargs.get("internal_account_id", _internal_account_id),
        booking_datetime=kwargs.get("booking_datetime"),
        client_id=kwargs.get("client_id"),
        enrichment_details=kwargs.get("enrichment_details"),
    )
    return instruction


def release_inbound_auth(
    self,
    unsettled_amount: Decimal,
    client_transaction_id: str = CLIENT_TRANSACTION_ID,
    denomination: str = "",
    target_account_id: str = ACCOUNT_ID,
    instruction_details: dict[str, str] | None = None,
    transaction_code: TransactionCode | None = None,
    override_all_restrictions: bool | None = False,
    **kwargs,
) -> Release:
    denomination = denomination or self.default_denomination
    instruction = Release(
        client_transaction_id=client_transaction_id,
        instruction_details=instruction_details,
        transaction_code=transaction_code,
        override_all_restrictions=override_all_restrictions,
        _from_proto=kwargs.get("_from_proto", False),
    )
    committed_postings = [
        Posting(
            credit=False,  # release inbound => False
            amount=unsettled_amount,
            denomination=denomination,
            account_id=target_account_id,
            account_address=DEFAULT_ADDRESS,
            asset=DEFAULT_ASSET,
            phase=Phase.PENDING_IN,  # inbound => PENDING_IN
            _from_proto=kwargs.get("_from_proto", False),
        ),
    ]
    instruction._set_output_attributes(
        insertion_datetime=kwargs.get("insertion_datetime"),
        value_datetime=kwargs.get("value_datetime", DEFAULT_DATETIME),
        client_batch_id=kwargs.get("client_batch_id"),
        batch_id=kwargs.get("batch_id"),
        committed_postings=committed_postings,
        instruction_id=kwargs.get("instruction_id"),
        unique_client_transaction_id=kwargs.get(
            "unique_client_transaction_id", f"{POSTING_CLIENT_ID}_{client_transaction_id}"
        ),
        client_transaction_id=client_transaction_id,
        own_account_id=kwargs.get("own_account_id", ACCOUNT_ID),
        tside=self.tside,
        amount=unsettled_amount,
        denomination=denomination,
        target_account_id=target_account_id,
        internal_account_id=kwargs.get("internal_account_id", DEFAULT_INTERNAL_ACCOUNT),
        booking_datetime=kwargs.get("booking_datetime"),
        client_id=kwargs.get("client_id"),
        enrichment_details=kwargs.get("enrichment_details"),
    )
    return instruction


def release_outbound_auth(
    self,
    unsettled_amount: Decimal,
    client_transaction_id: str = CLIENT_TRANSACTION_ID,
    denomination: str = "",
    target_account_id: str = ACCOUNT_ID,
    instruction_details: dict[str, str] | None = None,
    transaction_code: TransactionCode | None = None,
    override_all_restrictions: bool | None = False,
    **kwargs,
) -> Release:
    denomination = denomination or self.default_denomination
    instruction = Release(
        client_transaction_id=client_transaction_id,
        instruction_details=instruction_details,
        transaction_code=transaction_code,
        override_all_restrictions=override_all_restrictions,
        _from_proto=kwargs.get("_from_proto", False),
    )
    committed_postings = [
        Posting(
            credit=True,  # release outbound => True
            amount=unsettled_amount,
            denomination=denomination,
            account_id=target_account_id,
            account_address=DEFAULT_ADDRESS,
            asset=DEFAULT_ASSET,
            phase=Phase.PENDING_OUT,  # outbound => PENDING_OUT
            _from_proto=kwargs.get("_from_proto", False),
        )
    ]
    instruction._set_output_attributes(
        insertion_datetime=kwargs.get("insertion_datetime"),
        value_datetime=kwargs.get("value_datetime", DEFAULT_DATETIME),
        client_batch_id=kwargs.get("client_batch_id"),
        batch_id=kwargs.get("batch_id"),
        committed_postings=committed_postings,
        instruction_id=kwargs.get("instruction_id"),
        unique_client_transaction_id=kwargs.get(
            "unique_client_transaction_id", f"{POSTING_CLIENT_ID}_{client_transaction_id}"
        ),
        client_transaction_id=client_transaction_id,
        own_account_id=kwargs.get("own_account_id", ACCOUNT_ID),
        tside=self.tside,
        amount=unsettled_amount,
        denomination=denomination,
        target_account_id=target_account_id,
        internal_account_id=kwargs.get("internal_account_id", DEFAULT_INTERNAL_ACCOUNT),
        booking_datetime=kwargs.get("booking_datetime"),
        client_id=kwargs.get("client_id"),
        enrichment_details=kwargs.get("enrichment_details"),
    )
    return instruction


def inbound_hard_settlement(
    self,
    amount: Decimal,
    denomination: str = "",
    target_account_id: str = ACCOUNT_ID,
    internal_account_id: str = DEFAULT_INTERNAL_ACCOUNT,
    advice: bool | None = False,
    instruction_details: dict[str, str] | None = None,
    transaction_code: TransactionCode | None = None,
    override_all_restrictions: bool | None = False,
    target_account_address: str = DEFAULT_ADDRESS,
    asset: str = DEFAULT_ASSET,
    target_sub_account_id: str | None = None,
    **kwargs,
) -> InboundHardSettlement:
    denomination = denomination or self.default_denomination
    instruction = InboundHardSettlement(
        amount=amount,
        denomination=denomination,
        target_account_id=target_account_id,
        internal_account_id=internal_account_id,
        advice=advice,
        instruction_details=instruction_details,
        transaction_code=transaction_code,
        override_all_restrictions=override_all_restrictions,
        target_account_address=target_account_address,
        asset=asset,
        target_sub_account_id=target_sub_account_id,
    )
    committed_postings = [
        Posting(
            credit=True,  # inbound => True
            amount=amount,
            denomination=denomination,
            account_id=target_account_id,
            account_address=target_account_address,
            asset=asset,
            phase=DEFAULT_PHASE,  # hard settlement => COMMITTED
        ),
    ]
    client_transaction_id = kwargs.get("client_transaction_id", CLIENT_TRANSACTION_ID)
    instruction._set_output_attributes(
        insertion_datetime=kwargs.get("insertion_datetime"),
        value_datetime=kwargs.get("value_datetime", DEFAULT_DATETIME),
        client_batch_id=kwargs.get("client_batch_id"),
        batch_id=kwargs.get("batch_id"),
        committed_postings=committed_postings,
        instruction_id=kwargs.get("instruction_id"),
        unique_client_transaction_id=kwargs.get(
            "unique_client_transaction_id", f"{POSTING_CLIENT_ID}_{client_transaction_id}"
        ),
        client_transaction_id=client_transaction_id,
        own_account_id=kwargs.get("own_account_id", ACCOUNT_ID),
        tside=self.tside,
        booking_datetime=kwargs.get("booking_datetime"),
        client_id=kwargs.get("client_id"),
        enrichment_details=kwargs.get("enrichment_details"),
    )
    return instruction


def outbound_hard_settlement(
    self,
    amount: Decimal,
    denomination: str = "",
    target_account_id: str = ACCOUNT_ID,
    internal_account_id: str = DEFAULT_INTERNAL_ACCOUNT,
    advice: bool | None = False,
    instruction_details: dict[str, str] | None = None,
    transaction_code: TransactionCode | None = None,
    override_all_restrictions: bool | None = False,
    target_account_address: str = DEFAULT_ADDRESS,
    asset: str = DEFAULT_ASSET,
    target_sub_account_id: str | None = None,
    **kwargs,
) -> OutboundHardSettlement:
    denomination = denomination or self.default_denomination
    instruction = OutboundHardSettlement(
        amount=amount,
        denomination=denomination,
        target_account_id=target_account_id,
        internal_account_id=internal_account_id,
        advice=advice,
        instruction_details=instruction_details,
        transaction_code=transaction_code,
        override_all_restrictions=override_all_restrictions,
        target_account_address=target_account_address,
        asset=asset,
        target_sub_account_id=target_sub_account_id,
    )
    committed_postings = [
        Posting(
            credit=False,  # outbound => False
            amount=amount,
            denomination=denomination,
            account_id=target_account_id,
            account_address=target_account_address,
            asset=asset,
            phase=DEFAULT_PHASE,  # hard settlement => COMMITTED
        ),
    ]
    client_transaction_id = kwargs.get("client_transaction_id", CLIENT_TRANSACTION_ID)
    instruction._set_output_attributes(
        insertion_datetime=kwargs.get("insertion_datetime"),
        value_datetime=kwargs.get("value_datetime", DEFAULT_DATETIME),
        client_batch_id=kwargs.get("client_batch_id"),
        batch_id=kwargs.get("batch_id"),
        committed_postings=committed_postings,
        instruction_id=kwargs.get("instruction_id"),
        unique_client_transaction_id=kwargs.get(
            "unique_client_transaction_id", f"{POSTING_CLIENT_ID}_{client_transaction_id}"
        ),
        client_transaction_id=client_transaction_id,
        own_account_id=kwargs.get("own_account_id", ACCOUNT_ID),
        tside=self.tside,
        booking_datetime=kwargs.get("booking_datetime"),
        client_id=kwargs.get("client_id"),
        enrichment_details=kwargs.get("enrichment_details"),
    )
    return instruction


def inbound_transfer(
    self,
    amount: Decimal,
    denomination: str = "",
    debtor_target_account_id: str = DEFAULT_INTERNAL_ACCOUNT,
    creditor_target_account_id: str = ACCOUNT_ID,
    instruction_details: dict[str, str] | None = None,
    transaction_code: TransactionCode | None = None,
    override_all_restrictions: bool | None = False,
    debtor_target_sub_account_id: str | None = None,
    creditor_target_sub_account_id: str | None = None,
    **kwargs,
) -> Transfer:
    denomination = denomination or self.default_denomination
    instruction = Transfer(
        amount=amount,
        denomination=denomination,
        debtor_target_account_id=debtor_target_account_id,
        creditor_target_account_id=creditor_target_account_id,
        instruction_details=instruction_details,
        transaction_code=transaction_code,
        override_all_restrictions=override_all_restrictions,
        debtor_target_sub_account_id=debtor_target_sub_account_id,
        creditor_target_sub_account_id=creditor_target_sub_account_id,
    )
    committed_postings = [
        Posting(
            credit=True,  # inbound => True
            amount=amount,
            denomination=denomination,
            account_id=creditor_target_account_id,
            account_address=DEFAULT_ADDRESS,
            asset=DEFAULT_ASSET,
            phase=DEFAULT_PHASE,  # transfer => COMMITTED
        ),
    ]
    client_transaction_id = kwargs.get("client_transaction_id", CLIENT_TRANSACTION_ID)
    instruction._set_output_attributes(
        insertion_datetime=kwargs.get("insertion_datetime"),
        value_datetime=kwargs.get("value_datetime", DEFAULT_DATETIME),
        client_batch_id=kwargs.get("client_batch_id"),
        batch_id=kwargs.get("batch_id"),
        committed_postings=committed_postings,
        instruction_id=kwargs.get("instruction_id"),
        unique_client_transaction_id=kwargs.get(
            "unique_client_transaction_id", f"{POSTING_CLIENT_ID}_{client_transaction_id}"
        ),
        client_transaction_id=client_transaction_id,
        own_account_id=kwargs.get("own_account_id", ACCOUNT_ID),
        tside=self.tside,
        booking_datetime=kwargs.get("booking_datetime"),
        client_id=kwargs.get("client_id"),
        enrichment_details=kwargs.get("enrichment_details"),
    )
    return instruction


def outbound_transfer(
    self,
    amount: Decimal,
    denomination: str = "",
    debtor_target_account_id: str = ACCOUNT_ID,
    creditor_target_account_id: str = DEFAULT_INTERNAL_ACCOUNT,
    instruction_details: dict[str, str] | None = None,
    transaction_code: TransactionCode | None = None,
    override_all_restrictions: bool | None = False,
    debtor_target_sub_account_id: str | None = None,
    creditor_target_sub_account_id: str | None = None,
    **kwargs,
) -> Transfer:
    denomination = denomination or self.default_denomination
    instruction = Transfer(
        amount=amount,
        denomination=denomination,
        debtor_target_account_id=debtor_target_account_id,
        creditor_target_account_id=creditor_target_account_id,
        instruction_details=instruction_details,
        transaction_code=transaction_code,
        override_all_restrictions=override_all_restrictions,
        debtor_target_sub_account_id=debtor_target_sub_account_id,
        creditor_target_sub_account_id=creditor_target_sub_account_id,
    )
    committed_postings = [
        Posting(
            credit=False,  # outbound => False
            amount=amount,
            denomination=denomination,
            account_id=debtor_target_account_id,
            account_address=DEFAULT_ADDRESS,
            asset=DEFAULT_ASSET,
            phase=DEFAULT_PHASE,  # transfer => COMMITTED
        )
    ]
    client_transaction_id = kwargs.get("client_transaction_id", CLIENT_TRANSACTION_ID)
    instruction._set_output_attributes(
        insertion_datetime=kwargs.get("insertion_datetime"),
        value_datetime=kwargs.get("value_datetime", DEFAULT_DATETIME),
        client_batch_id=kwargs.get("client_batch_id"),
        batch_id=kwargs.get("batch_id"),
        committed_postings=committed_postings,
        instruction_id=kwargs.get("instruction_id"),
        unique_client_transaction_id=kwargs.get(
            "unique_client_transaction_id", f"{POSTING_CLIENT_ID}_{client_transaction_id}"
        ),
        client_transaction_id=client_transaction_id,
        own_account_id=kwargs.get("own_account_id", ACCOUNT_ID),
        tside=self.tside,
        booking_datetime=kwargs.get("booking_datetime"),
        client_id=kwargs.get("client_id"),
        enrichment_details=kwargs.get("enrichment_details"),
    )
    return instruction


def custom_instruction(
    self,
    postings: list[Posting],
    instruction_details: dict[str, str] | None = None,
    transaction_code: TransactionCode | None = None,
    override_all_restrictions: bool | None = False,
    value_datetime: datetime | None = None,
    booking_datetime: datetime | None = None,
    **kwargs,
) -> CustomInstruction:
    instruction = CustomInstruction(
        postings=postings,
        value_datetime=value_datetime,
        booking_datetime=booking_datetime,
        instruction_details=instruction_details,
        transaction_code=transaction_code,
        override_all_restrictions=override_all_restrictions,
    )
    client_transaction_id = kwargs.get("client_transaction_id", CLIENT_TRANSACTION_ID)
    instruction._set_output_attributes(
        insertion_datetime=kwargs.get("insertion_datetime"),
        value_datetime=kwargs.get("value_datetime", DEFAULT_DATETIME),
        client_batch_id=kwargs.get("client_batch_id"),
        batch_id=kwargs.get("batch_id"),
        committed_postings=postings,
        instruction_id=kwargs.get("instruction_id"),
        unique_client_transaction_id=kwargs.get(
            "unique_client_transaction_id", f"{POSTING_CLIENT_ID}_{client_transaction_id}"
        ),
        client_transaction_id=client_transaction_id,
        own_account_id=kwargs.get("own_account_id", ACCOUNT_ID),
        tside=self.tside,
        booking_datetime=kwargs.get("booking_datetime"),
        client_id=kwargs.get("client_id"),
        enrichment_details=kwargs.get("enrichment_details"),
    )
    return instruction
