# Copyright @ 2026 Thought Machine Group Limited. All rights reserved.
__smart_contract_feature__ = True

# standard libs
from decimal import Decimal
from typing import NamedTuple

# feature library
import feature_library.common.balance_utils as balance_utils
import feature_library.common.denomination as denomination_module
import feature_library.common.posting_utils as posting_utils
import feature_library.common.state_utils as state_utils
import feature_library.lending.interfaces as lending_interfaces
import feature_library.lending.repayments.payments as payments

# contracts api
from contracts_api import (
    DEFAULT_ASSET,
    Attribute,
    AttributeDecimalType,
    BalanceCoordinate,
    BalanceDefaultDict,
    CustomInstruction,
    Phase,
    Posting,
    Rejection,
    RejectionReason,
    Tside,
)

AVAILABLE_REDRAW_FUNDS_ATTR_ID = "available_redraw_funds"
AVAILABLE_REDRAW_FUNDS_ATTRIBUTE = Attribute(
    name=AVAILABLE_REDRAW_FUNDS_ATTR_ID,
    data_type=AttributeDecimalType(),
)
attributes = [AVAILABLE_REDRAW_FUNDS_ATTRIBUTE]


RedrawFetchersConfig = NamedTuple(
    "RedrawFetchersConfig",
    [
        ("denomination_param_id", str),
    ],
)

DEFAULT_REDRAW_FETCHERS_CONFIG = RedrawFetchersConfig(
    denomination_param_id=denomination_module.DENOMINATION_PARAM_ID,
)

REDRAW_ADDRESS = "REDRAW"


def handle_overpayment(
    state: state_utils.SmartContractState,
    overpayment_amount: Decimal,
    fetchers_config: RedrawFetchersConfig = DEFAULT_REDRAW_FETCHERS_CONFIG,
) -> list[Posting]:
    """Handle overpayments by rebalancing the amount to the REDRAW address.

    Args:
        state: The smart contract state.
        overpayment_amount: The amount being overpaid.
        fetchers_config: The fetchers configuration.

    Returns:
        Postings to handle the overpayment.
    """
    rejection = state_utils.check_parameters_exist(
        state=state,
        param_ids={
            fetchers_config.denomination_param_id,
        },
    )
    assert rejection is None, rejection

    denomination: str = state.parameters[fetchers_config.denomination_param_id]  # type: ignore
    return posting_utils.create_postings(
        debit_account=state.vault.account_id,
        denomination=denomination,
        amount=overpayment_amount,
        credit_account=state.vault.account_id,
        credit_address=REDRAW_ADDRESS,
    )


OverpaymentFeature = lending_interfaces.Overpayment(handle_overpayment=handle_overpayment)


def auto_repayment(
    state: state_utils.SmartContractState,
    due_amount_posting_instructions: list[CustomInstruction],
    repayment_hierarchy: list[str],
    redraw_address: str = REDRAW_ADDRESS,
    fetchers_config: RedrawFetchersConfig = DEFAULT_REDRAW_FETCHERS_CONFIG,
) -> list[CustomInstruction]:
    """Create posting instructions to automatically repay due balances from the redraw balance.

    Args:
        state: The smart contract state.
        due_amount_posting_instructions: The postings for any due amounts
            to be committed to the ledger.
        repayment_hierarchy: Order in which a repayment amount is to be
            distributed across due addresses.
        redraw_address: The address for redraw. Defaults to REDRAW_ADDRESS.
        fetchers_config: The fetchers configuration.

    Returns:
        The custom instructions that automatically repay any due balances.
    """
    rejection = state_utils.check_parameters_exist(
        state=state,
        param_ids={
            fetchers_config.denomination_param_id,
        },
    )
    assert rejection is None, rejection

    denomination: str = state.parameters[fetchers_config.denomination_param_id]  # type: ignore
    redraw_balance = get_available_redraw_funds(state=state, fetchers_config=fetchers_config)

    if redraw_balance >= Decimal(0) or not due_amount_posting_instructions:
        return []

    # get a map of due addresses to due amounts
    # e.g. {"PRINCIPAL_DUE": Decimal("60"), "INTEREST_DUE": Decimal("20")}
    due_amount_mapping = {}
    for due_instruction in due_amount_posting_instructions:
        balance_dict: BalanceDefaultDict = due_instruction.balances(
            account_id=state.vault.account_id, tside=Tside.ASSET
        )
        for balance in balance_dict.keys():
            if balance.account_address in repayment_hierarchy:
                due_amount_mapping.update(
                    {balance.account_address: balance_utils.net_debit(balance_dict[balance])}
                )

    auto_repayment_postings: list[Posting] = []
    remaining_redraw_balance = abs(redraw_balance)
    for address in repayment_hierarchy:
        if remaining_redraw_balance == Decimal(0):
            break

        repayment_amount = min(
            remaining_redraw_balance, due_amount_mapping.get(address, Decimal(0))
        )
        if repayment_amount > Decimal(0):
            auto_repayment_postings += payments.redistribute_postings(
                debit_account=state.vault.account_id,
                denomination=denomination,
                amount=repayment_amount,
                credit_account=state.vault.account_id,
                credit_address=address,
                debit_address=redraw_address,
            )
            remaining_redraw_balance -= repayment_amount

    if auto_repayment_postings:
        return [
            CustomInstruction(
                postings=auto_repayment_postings,
                instruction_details={
                    "description": "Auto repay due balances from the redraw balance",
                    "event": "PROCESS_AUTO_REPAYMENT_FROM_REDRAW_BALANCE",
                },
                override_all_restrictions=True,
            )
        ]
    return []


def get_available_redraw_funds(
    state: state_utils.SmartContractState,
    fetchers_config: RedrawFetchersConfig = DEFAULT_REDRAW_FETCHERS_CONFIG,
) -> Decimal:
    """Return the available redraw amount.

    Args:
        state: The smart contract state.
        fetchers_config: The fetchers configuration.

    Returns:
        The remaining amount in the redraw balance.
    """
    rejection = state_utils.check_parameters_exist(
        state=state,
        param_ids={
            fetchers_config.denomination_param_id,
        },
    )
    assert rejection is None, rejection

    denomination: str = state.parameters[fetchers_config.denomination_param_id]  # type: ignore
    return balance_utils.net_credit(
        state.balances[
            BalanceCoordinate(
                account_address=REDRAW_ADDRESS,
                asset=DEFAULT_ASSET,
                denomination=denomination,
                phase=Phase.COMMITTED,
            )
        ]
    )


def reject_closure_when_outstanding_redraw_funds(
    state: state_utils.SmartContractState,
) -> Rejection | None:
    """Return a rejection if the redraw balance still contains funds.

    Args:
        state: The smart contract state.

    Returns:
        A rejection if the redraw balance contains a non-zero amount.
    """
    if get_available_redraw_funds(state) != Decimal(0):
        return Rejection(
            message="The loan cannot be closed until all remaining redraw funds are cleared.",
            reason_code=RejectionReason.AGAINST_TNC,
        )
    return None


def validate_redraw_funds(
    state: state_utils.SmartContractState,
    posting_amount: Decimal,
    fetchers_config: RedrawFetchersConfig = DEFAULT_REDRAW_FETCHERS_CONFIG,
) -> Rejection | None:
    """Reject a posting if the withdrawal amount is greater than the current redraw balance.

    Args:
        state: The smart contract state.
        posting_amount: The amount to validate against the current redraw amount.
        fetchers_config: The fetchers configuration.

    Returns:
        A rejection if the redraw amount exceeds the current redraw balance.
    """
    rejection = state_utils.check_parameters_exist(
        state=state,
        param_ids={
            fetchers_config.denomination_param_id,
        },
    )
    if rejection is not None:
        return rejection

    denomination: str = state.parameters[fetchers_config.denomination_param_id]  # type: ignore
    redraw_balance = get_available_redraw_funds(state=state, fetchers_config=fetchers_config)

    if posting_amount > 0 and posting_amount > redraw_balance:
        return Rejection(
            message=f"Transaction amount {posting_amount} {denomination} is greater than "
            f"the available redraw funds of {abs(redraw_balance)} {denomination}.",
            reason_code=RejectionReason.INSUFFICIENT_FUNDS,
        )

    return None
