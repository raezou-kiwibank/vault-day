# Copyright @ 2026 Thought Machine Group Limited. All rights reserved.
__smart_contract_feature__ = True

from decimal import Decimal
from typing import NamedTuple

import feature_library.common.addresses as common_addresses
import feature_library.common.balance_utils as balance_utils
import feature_library.common.denomination as denomination_module
import feature_library.common.state_utils as state_utils
import feature_library.lending.addresses as lending_addresses
import feature_library.lending.interfaces as lending_interfaces

DUE_ADDRESSES = [lending_addresses.PRINCIPAL_DUE, lending_addresses.INTEREST_DUE]
OVERDUE_ADDRESSES = [lending_addresses.PRINCIPAL_OVERDUE, lending_addresses.INTEREST_OVERDUE]
LATE_REPAYMENT_ADDRESSES = OVERDUE_ADDRESSES + [common_addresses.PENALTIES]
REPAYMENT_HIERARCHY = LATE_REPAYMENT_ADDRESSES + DUE_ADDRESSES

DEBT_ADDRESSES = REPAYMENT_HIERARCHY + [lending_addresses.PRINCIPAL]

ALL_OUTSTANDING = [
    *DEBT_ADDRESSES,
    lending_addresses.ACCRUED_INTEREST_RECEIVABLE,
    lending_addresses.ACCRUED_OVERDUE_INTEREST_PENDING_CAPITALISATION,
]


VerticalFetchersConfig = NamedTuple(
    "VerticalFetchersConfig",
    [
        # list of balances for dues, overdues and penalties in repayment hierarchy order
        ("repayment_hierarchy", list[str]),
        # list of all balances that include outstanding amounts:
        # repayment_hierarchy + principal & accrued interest addresses
        ("all_outstanding_addresses", list[str]),
        # list of adresses for overdue amounts
        ("overdue_addresses", list[str]),
        ("denomination_param_id", str),
    ],
)

DEFAULT_VERTICAL_FETCHERS_CONFIG = VerticalFetchersConfig(
    repayment_hierarchy=REPAYMENT_HIERARCHY,
    all_outstanding_addresses=ALL_OUTSTANDING,
    overdue_addresses=OVERDUE_ADDRESSES,
    denomination_param_id=denomination_module.DENOMINATION_PARAM_ID,
)


def get_total_outstanding_debt(
    state: state_utils.SmartContractState,
    fetchers_config: VerticalFetchersConfig = DEFAULT_VERTICAL_FETCHERS_CONFIG,
) -> Decimal:
    """Returns the total outstanding debt by summing the balances of all outstanding addresses.

    Args:
        state: The current state of the smart contract.
        fetchers_config: Configuration for the vertical repayment hierarchy.

    Returns:
        Decimal: The total outstanding debt amount.
    """

    rejection = state_utils.check_parameters_exist(
        state=state, param_ids={fetchers_config.denomination_param_id}
    )
    assert rejection is None, rejection

    denomination: str = state.parameters[fetchers_config.denomination_param_id]  # type: ignore

    return balance_utils.net_debit(
        bal=balance_utils.sum_balances(
            balances=state.balances,
            denomination=denomination,
            addresses=fetchers_config.all_outstanding_addresses,
        )
    )


def get_total_overdue_amount(
    state: state_utils.SmartContractState,
    fetchers_config: VerticalFetchersConfig = DEFAULT_VERTICAL_FETCHERS_CONFIG,
) -> Decimal:
    """Returns the total overdue amount by summing the balances of all overdue addresses.

    Args:
        state: The current state of the smart contract.
        fetchers_config: Configuration for the vertical repayment hierarchy.

    Returns:
        Decimal: The total overdue amount.
    """

    rejection = state_utils.check_parameters_exist(
        state=state, param_ids={fetchers_config.denomination_param_id}
    )

    assert rejection is None, rejection

    denomination: str = state.parameters[fetchers_config.denomination_param_id]  # type: ignore

    total_overdue = balance_utils.net_debit(
        bal=balance_utils.sum_balances(
            balances=state.balances,
            denomination=denomination,
            addresses=fetchers_config.overdue_addresses,
        )
    )

    return total_overdue


def get_total_due_amount(
    state: state_utils.SmartContractState,
    fetchers_config: VerticalFetchersConfig = DEFAULT_VERTICAL_FETCHERS_CONFIG,
) -> Decimal:
    """Get the total due amount by summing the balances of all due and overdue addresses.

    Args:
        state (state_utils.SmartContractState): The current state of the smart contract.
        fetchers_config (VerticalFetchersConfig, optional): Configuration for the vertical
            repayment hierarchy. Defaults to DEFAULT_VERTICAL_FETCHERS_CONFIG.

    Returns:
        Decimal: _description_
    """

    rejection = state_utils.check_parameters_exist(
        state=state, param_ids={fetchers_config.denomination_param_id}
    )

    assert rejection is None, rejection

    denomination: str = state.parameters[fetchers_config.denomination_param_id]  # type: ignore

    total_due = balance_utils.net_debit(
        bal=balance_utils.sum_balances(
            balances=state.balances,
            denomination=denomination,
            addresses=fetchers_config.repayment_hierarchy,
        )
    )

    return total_due


def get_repayment_hierarchy_order(
    state: state_utils.SmartContractState,
    fetchers_config: VerticalFetchersConfig = DEFAULT_VERTICAL_FETCHERS_CONFIG,
) -> list[str]:
    """Returns the repayment hierarchy order.

    Args:
        state: The current state of the smart contract.
        fetchers_config: Configuration for the vertical repayment hierarchy.

    Returns:
        list[str]: The repayment hierarchy order.
    """

    return fetchers_config.repayment_hierarchy


VerticalRepaymentHierarchy = lending_interfaces.RepaymentHierarchy(
    get_total_outstanding_debt=get_total_outstanding_debt,
    get_total_overdue_amount=get_total_overdue_amount,
    get_total_due_amount=get_total_due_amount,
    get_repayment_hierarchy_order=get_repayment_hierarchy_order,
)
