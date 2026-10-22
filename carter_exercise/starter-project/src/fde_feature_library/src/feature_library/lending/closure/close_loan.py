# Copyright @ 2026 Thought Machine Group Limited. All rights reserved.
__smart_contract_feature__ = True

# standard libs
from decimal import Decimal
from typing import NamedTuple

# features
import feature_library.common.addresses as common_addresses
import feature_library.common.balance_utils as balance_utils
import feature_library.common.denomination as denomination_module
import feature_library.common.posting_utils as posting_utils
import feature_library.common.state_utils as state_utils
import feature_library.lending.addresses as lending_addresses
import feature_library.lending.interfaces as lending_interfaces

# contracts api
from contracts_api import (
    AccountNotificationDirective,
    CustomInstruction,
    Posting,
    Rejection,
    RejectionReason,
    Tside,
)

# Notifications
LOAN_PAID_OFF_NOTIFICATION_SUFFIX = "_LOAN_PAID_OFF"

# address groups
DUE_ADDRESSES = [lending_addresses.PRINCIPAL_DUE, lending_addresses.INTEREST_DUE]
OVERDUE_ADDRESSES = [lending_addresses.PRINCIPAL_OVERDUE, lending_addresses.INTEREST_OVERDUE]
PENALTIES_ADDRESSES = [lending_addresses.PENALTIES]
PRINCIPAL_ADDRESSES = [lending_addresses.PRINCIPAL]

PAYMENT_ADDRESSES = OVERDUE_ADDRESSES + PENALTIES_ADDRESSES + DUE_ADDRESSES
DEBT_ADDRESSES = PAYMENT_ADDRESSES + PRINCIPAL_ADDRESSES

CloseLoanFetchersConfig = NamedTuple(
    "CloseLoanFetchersConfig",
    [
        ("denomination_param_id", str),
    ],
)

DEFAULT_FETCHER_CONFIG = CloseLoanFetchersConfig(
    denomination_param_id=denomination_module.DENOMINATION_PARAM_ID,
)


def notification_type(*, product_name: str) -> str:
    """Creates the notification type for a paid off loan.

    Args:
        product_name: The product name.

    Returns:
        The notification type string.
    """
    return f"{product_name.upper()}{LOAN_PAID_OFF_NOTIFICATION_SUFFIX}"


def does_repayment_fully_repay_loan(
    *,
    state: state_utils.SmartContractState,
    repayment_posting_instructions: list[CustomInstruction],
    repayment_hierarchy_config: lending_interfaces.RepaymentHierarchyConfig,
    fetchers_config: CloseLoanFetchersConfig = DEFAULT_FETCHER_CONFIG,
) -> bool:
    """Determines whether the repayment posting instructions fully repay the outstanding debt.

    Args:
        state: The current state of the smart contract.
        repayment_posting_instructions: The repayment posting instructions.
        repayment_hierarchy_config: Configuration for the repayment hierarchy.
        fetchers_config: Configuration for the fetchers.

    Returns:
        A boolean that indicates whether the repayment has paid off the loan.
    """
    rejection = state_utils.check_parameters_exist(
        state=state, param_ids={fetchers_config.denomination_param_id}
    )
    assert rejection is None, rejection

    denomination: str = state.parameters[fetchers_config.denomination_param_id]  # type: ignore

    repayment_amount: Decimal = balance_utils.net_credit(
        bal=balance_utils.sum_balances(
            balances=posting_utils.get_posting_instructions_balances(
                posting_instructions=repayment_posting_instructions,  # type: ignore
                account_id=state.vault.account_id,
                tside=Tside.ASSET,
            ),
            denomination=denomination,
        )
    )

    outstanding_debt = repayment_hierarchy_config.repayment_hierarchy.get_total_outstanding_debt(
        state=state,
        fetchers_config=repayment_hierarchy_config.fetchers_config,
    )

    return repayment_amount >= outstanding_debt


def send_loan_paid_off_notification(
    *,
    state: state_utils.SmartContractState,
    product_name: str,
) -> AccountNotificationDirective:
    """Instruct a loan paid off notification.

    Args:
        state: The current state of the smart contract.
        product_name: The name of the product for the notification prefix.

    Returns:
        An account notification directive indicating the loan is paid off.
    """
    return AccountNotificationDirective(
        notification_type=notification_type(product_name=product_name),
        notification_details={
            "account_id": state.vault.account_id,
        },
    )


def set_balances_to_zero(
    *,
    state: state_utils.SmartContractState,
    residual_cleanup_features: list[lending_interfaces.ResidualCleanup] | None = None,
    eia_address: str = lending_addresses.EIA,
    internal_contra_address: str = common_addresses.INTERNAL_CONTRA,
    fetchers_config: CloseLoanFetchersConfig = DEFAULT_FETCHER_CONFIG,
) -> list[CustomInstruction]:
    """Sets residual balances to zero by netting off the EIA and other accounting addresses.

    Args:
        state: The current state of the smart contract.
        residual_cleanup_features: A list of features to get residual cleanup postings.
        fetchers_config: Configuration for the fetchers.

    Returns:
        A list of custom instructions used to net all remaining balances.
    """

    rejection = state_utils.check_parameters_exist(
        state=state, param_ids={fetchers_config.denomination_param_id}
    )
    assert rejection is None, rejection

    net_postings: list[Posting] = []

    denomination: str = state.parameters[fetchers_config.denomination_param_id]  # type: ignore

    eia_amount = balance_utils.balance_at_coordinates(
        balances=state.balances, address=eia_address, denomination=denomination
    )

    net_postings.extend(
        posting_utils.create_postings(
            amount=eia_amount,
            debit_account=state.vault.account_id,
            credit_account=state.vault.account_id,
            debit_address=internal_contra_address,
            credit_address=eia_address,
            denomination=denomination,
        )
    )

    net_postings.extend(
        posting
        for feature in (residual_cleanup_features or [])
        for posting in feature.get_residual_cleanup_postings(
            balances=state.balances,
            account_id=state.vault.account_id,
            denomination=denomination,
        )
    )

    return (
        [
            CustomInstruction(
                postings=net_postings,
                instruction_details={
                    "description": "Clearing all residual balances",
                    "event": "END_OF_LOAN",
                },
            )
        ]
        if net_postings
        else []
    )


def reject_closure_when_outstanding_debt(
    *,
    state: state_utils.SmartContractState,
    repayment_hierarchy_config: lending_interfaces.RepaymentHierarchyConfig,
) -> Rejection | None:
    """Returns a rejection if the debt addresses sum to a non-zero amount.

    Args:
        state: The current state of the smart contract.
        repayment_hierarchy_config: Configuration for the repayment hierarchy.

    Returns:
        A rejection if the debt addresses sum to a non-zero value.
    """

    total_outstanding_debt = (
        repayment_hierarchy_config.repayment_hierarchy.get_total_outstanding_debt(
            state=state,
            fetchers_config=repayment_hierarchy_config.fetchers_config,
        )
    )

    if total_outstanding_debt != Decimal("0"):
        return Rejection(
            message="The loan cannot be closed until all outstanding debt is repaid",
            reason_code=RejectionReason.AGAINST_TNC,
        )
    return None
