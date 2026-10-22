# Copyright @ 2026 Thought Machine Group Limited. All rights reserved.
__smart_contract_feature__ = True

from datetime import datetime
from decimal import Decimal
from typing import NamedTuple

import feature_library.common.addresses as common_addresses
import feature_library.common.balance_utils as balance_utils
import feature_library.common.denomination as denomination_module
import feature_library.common.state_utils as state_utils
import feature_library.lending.addresses as lending_addresses
import feature_library.lending.interfaces as lending_interfaces

from contracts_api import BalanceDefaultDict

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


HorizontalFetchersConfig = NamedTuple(
    "HorizontalFetchersConfig",
    [
        ("repayment_hierarchy", list[str]),
        ("late_repayment_addresses", list[str]),
        ("all_outstanding_addresses", list[str]),
        ("overdue_addresses", list[str]),
        ("denomination_param_id", str),
    ],
)

DEFAULT_HORIZONTAL_FETCHERS_CONFIG = HorizontalFetchersConfig(
    repayment_hierarchy=REPAYMENT_HIERARCHY,
    late_repayment_addresses=LATE_REPAYMENT_ADDRESSES,
    all_outstanding_addresses=ALL_OUTSTANDING,
    overdue_addresses=OVERDUE_ADDRESSES,
    denomination_param_id=denomination_module.DENOMINATION_PARAM_ID,
)


def get_total_outstanding_debt(
    state: state_utils.SmartContractState,
    fetchers_config: HorizontalFetchersConfig = DEFAULT_HORIZONTAL_FETCHERS_CONFIG,
) -> Decimal:
    """Returns the total outstanding debt by summing the balances of all outstanding addresses.

    As late repayment addresses are expected to have a date suffix e.g OVERDUE_PRINCIPAL_20260125
    it filters for the specific late repayment balances.

    Args:
        state: The current state of the smart contract.
        fetchers_config: Configuration for the horizontal repayment hierarchy.

    Returns:
        Decimal: The total outstanding debt amount.
    """

    rejection = state_utils.check_parameters_exist(
        state=state, param_ids={fetchers_config.denomination_param_id}
    )
    assert rejection is None, rejection

    denomination: str = state.parameters[fetchers_config.denomination_param_id]  # type: ignore

    all_outstanding_addresses: list[str] = fetchers_config.all_outstanding_addresses
    late_repayment_addresses: list[str] = fetchers_config.late_repayment_addresses

    other_addresses: list[str] = [
        addr for addr in all_outstanding_addresses if addr not in late_repayment_addresses
    ]

    late_repayment_balances: BalanceDefaultDict = get_late_repayment_balances(
        state=state,
        late_repayment_addresses=late_repayment_addresses,
    )

    combined_addresses: list[str] = [
        k.account_address for k in late_repayment_balances.keys()
    ] + other_addresses

    return balance_utils.net_debit(
        bal=balance_utils.sum_balances(
            balances=state.balances,
            denomination=denomination,
            addresses=combined_addresses,
        )
    )


def get_late_repayment_balances(
    state: state_utils.SmartContractState,
    late_repayment_addresses: list[str] = LATE_REPAYMENT_ADDRESSES,
) -> BalanceDefaultDict:
    """Filters the current balances to return only those associated with late repayments.

    Args:
        state: The current state of the smart contract.
        late_repayment_addresses: A list of address prefixes that indicate a late repayment.

    Returns:
        BalanceDefaultDict: A BalanceDefaultDict containing only the late repayment balances.
    """

    late_repayment_balances = {
        k: v
        for k, v in state.balances.items()
        if is_target_address(
            address=k.account_address, target_address_prefixes=late_repayment_addresses
        )
    }

    return BalanceDefaultDict(mapping=late_repayment_balances)


def _is_date_suffix(suffix: str) -> bool:
    """Checks if a suffix matches the YYYYMMDD format."""

    # Format Check: Must be 8 chars long
    if len(suffix) != 8:
        return False

    # Numeric Check: Ensure suffix only contains only digits
    if not suffix.isdigit():
        return False

    # Parsing: Convert strings to integers
    year = int(suffix[0:4])
    month = int(suffix[4:6])
    day = int(suffix[6:8])

    # Attempt to create datetime object
    try:
        datetime(year, month, day)
        return True
    except:  # noqa: E722
        return False


def _get_address_date_suffix(address: str, prefix: str) -> str | None:
    """Returns the date suffix for an address if it matches a prefix.
    For late repayment prefixes, matches exact prefix or prefix + date suffix.

    Args:
        address: The account address to check.
        prefix: The address prefix to match against.

    Returns:
        str | None: The date suffix if the address matches (00000000 for exact match), else None.
    """
    if address == prefix:
        return "00000000"

    if address.startswith(prefix + "_"):
        suffix = address[len(prefix) + 1 :]
        if _is_date_suffix(suffix):
            return suffix

    return None


def is_target_address(
    address: str,
    target_address_prefixes: list[str] = LATE_REPAYMENT_ADDRESSES,
) -> bool:
    """Checks if a given address corresponds to a target prefix, exactly or with a date suffix.

    Args:
        address: The account address to check.
        target_address_prefixes: A list of address prefixes that indicate a target address.

    Returns:
        bool: True if the address matches any of the prefixes (exact or with date suffix).
    """

    return any(_get_address_date_suffix(address, p) is not None for p in target_address_prefixes)


def get_total_overdue_amount(
    state: state_utils.SmartContractState,
    fetchers_config: HorizontalFetchersConfig = DEFAULT_HORIZONTAL_FETCHERS_CONFIG,
) -> Decimal:
    """Returns the total overdue amount by summing the balances of all overdue addresses.

    Args:
        state: The current state of the smart contract.
        fetchers_config: Configuration for the horizontal repayment hierarchy.

    Returns:
        Decimal: The total overdue amount.
    """

    rejection = state_utils.check_parameters_exist(
        state=state, param_ids={fetchers_config.denomination_param_id}
    )
    assert rejection is None, rejection

    denomination: str = state.parameters[fetchers_config.denomination_param_id]  # type: ignore

    overdue_balances: BalanceDefaultDict = get_overdue_balances(
        state=state,
        overdue_addresses=fetchers_config.overdue_addresses,
    )

    actual_overdue_addresses: list[str] = [k.account_address for k in overdue_balances.keys()]

    return balance_utils.net_debit(
        bal=balance_utils.sum_balances(
            balances=state.balances,
            denomination=denomination,
            addresses=actual_overdue_addresses,
        )
    )


def get_overdue_balances(
    state: state_utils.SmartContractState,
    overdue_addresses: list[str] = OVERDUE_ADDRESSES,
) -> BalanceDefaultDict:
    """Filters the current balances to return only those associated with late repayments.

    Args:
        state: The current state of the smart contract.
        overdue_addresses: A list of address prefixes that indicate an overdue address.

    Returns:
        BalanceDefaultDict: A BalanceDefaultDict containing only the overdue balances.
    """

    overdue_balances = {
        k: v
        for k, v in state.balances.items()
        if is_target_address(address=k.account_address, target_address_prefixes=overdue_addresses)
    }

    return BalanceDefaultDict(mapping=overdue_balances)


def get_total_due_amount(
    state: state_utils.SmartContractState,
    fetchers_config: HorizontalFetchersConfig = DEFAULT_HORIZONTAL_FETCHERS_CONFIG,
) -> Decimal:
    """Returns the total due amount by summing the balances of all due and overdue addresses.

    Args:
        state: The current state of the smart contract.
        fetchers_config: Configuration for the horizontal repayment hierarchy.

    Returns:
        Decimal: The total due amount.
    """

    rejection = state_utils.check_parameters_exist(
        state=state, param_ids={fetchers_config.denomination_param_id}
    )
    assert rejection is None, rejection

    denomination: str = state.parameters[fetchers_config.denomination_param_id]  # type: ignore

    late_repayment_balances: BalanceDefaultDict = get_late_repayment_balances(
        state=state,
        late_repayment_addresses=fetchers_config.late_repayment_addresses,
    )

    combined_addresses: list[str] = [
        k.account_address for k in late_repayment_balances.keys()
    ] + DUE_ADDRESSES

    return balance_utils.net_debit(
        bal=balance_utils.sum_balances(
            balances=state.balances,
            denomination=denomination,
            addresses=combined_addresses,
        )
    )


def _get_address_repayment_metadata(
    address: str,
    repayment_hierarchy: list[str],
    late_prefixes: set[str],
) -> tuple[int, str, int] | None:
    """Finds the first matching prefix in the hierarchy and returns sorting metadata.

    Args:
        address: The account address to check.
        repayment_hierarchy: The ordered list of address prefixes to match against.
        late_prefixes: The set of prefixes considered as late repayments.

    Returns:
        tuple[int, str, int] | None: (priority, suffix, index) if matched, else None.
        Priority 0 for late repayments, 1 for others.
    """
    for index, prefix in enumerate(repayment_hierarchy):
        if prefix in late_prefixes:
            if (suffix := _get_address_date_suffix(address, prefix)) is not None:
                return (0, suffix, index)
        elif address == prefix:
            return (1, "00000000", index)

    return None


def get_repayment_hierarchy_order(
    state: state_utils.SmartContractState,
    fetchers_config: HorizontalFetchersConfig = DEFAULT_HORIZONTAL_FETCHERS_CONFIG,
) -> list[str]:
    """Returns the repayment hierarchy order.

    As late repayment addresses are expected to have a date suffix e.g OVERDUE_PRINCIPAL_20260125
    it dynamically builds the hierarchy based on the current balances. It prioritizes the
    date suffix (oldest first) across all late repayment addresses before following the
    type hierarchy.

    Args:
        state: The current state of the smart contract.
        fetchers_config: Configuration for the horizontal repayment hierarchy.

    Returns:
        list[str]: The repayment hierarchy order.
    """

    account_addresses = sorted({k.account_address for k in state.balances.keys()})
    late_prefixes = set(fetchers_config.late_repayment_addresses)

    # Identify all matches and their sorting metadata
    matches = [
        (addr, metadata)
        for addr in account_addresses
        if (
            metadata := _get_address_repayment_metadata(
                addr, fetchers_config.repayment_hierarchy, late_prefixes
            )
        )
    ]

    # Sort: late repayments first (by date then hierarchy index), then other repayments (by index)
    matches.sort(key=lambda x: x[1])

    repayment_hierarchy_order = [m[0] for m in matches]

    # Default back to the configured hierarchy if no addresses were found in balances
    return repayment_hierarchy_order or fetchers_config.repayment_hierarchy


HorizontalRepaymentHierarchy = lending_interfaces.RepaymentHierarchy(
    get_total_outstanding_debt=get_total_outstanding_debt,
    get_total_overdue_amount=get_total_overdue_amount,
    get_total_due_amount=get_total_due_amount,
    get_repayment_hierarchy_order=get_repayment_hierarchy_order,
)
