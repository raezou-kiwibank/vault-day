__smart_contract_feature__ = True

# standard libs
from datetime import datetime
from decimal import Decimal
from typing import Iterable, Mapping

# feature_library
import feature_library.common.posting_utils as posting_utils
import feature_library.common.utils as utils

# contracts api
from contracts_api import (
    DEFAULT_ADDRESS,
    DEFAULT_ASSET,
    Balance,
    BalanceCoordinate,
    BalanceDefaultDict,
    BalanceTimeseries,
    Phase,
    Rejection,
    RejectionReason,
    Tside,
)

# inception sdk
from inception_sdk.vault.contracts.extensions.contracts_api_extensions import SmartContractVault


## Balance helpers
def balance_at_coordinates(
    balances: BalanceDefaultDict,
    denomination: str,
    address: str = DEFAULT_ADDRESS,
    asset: str = DEFAULT_ASSET,
    phase: Phase = Phase.COMMITTED,
    decimal_places: int | None = None,
) -> Decimal:
    """Retrieves the balance net for the specified coordinates."""
    balance_net = balances[BalanceCoordinate(address, asset, denomination, phase)].net
    return (
        balance_net
        if decimal_places is None
        else utils.round_decimal(amount=balance_net, decimal_places=decimal_places)
    )


def get_balance_from_observation(
    vault: SmartContractVault,
    balance_coordinate: BalanceCoordinate,
    fetcher_id: str,
) -> Decimal:
    """Retrieves the balance net from a vault observation."""
    balances = vault.get_balances_observation(fetcher_id=fetcher_id).balances

    return balance_at_coordinates(
        balances=balances,
        address=balance_coordinate.account_address,
        denomination=balance_coordinate.denomination,
        asset=balance_coordinate.asset,
        phase=balance_coordinate.phase,
    )


def get_balance_from_interval(
    vault: SmartContractVault,
    balance_coordinate: BalanceCoordinate,
    fetcher_id: str,
    effective_datetime: datetime,
) -> Decimal:
    """Get the net balance at a particular effective datetime from a balance coordinate using a
    balance interval fetcher.
    """
    balances_mapping = vault.get_balances_timeseries(fetcher_id=fetcher_id)
    balances = get_balance_default_dict_from_mapping(
        mapping=balances_mapping,
        effective_datetime=effective_datetime,
    )
    return balance_at_coordinates(
        balances=balances,
        address=balance_coordinate.account_address,
        denomination=balance_coordinate.denomination,
        asset=balance_coordinate.asset,
        phase=balance_coordinate.phase,
    )


def get_balances_from_interval(
    vault: SmartContractVault,
    fetcher_id: str,
    effective_datetime: datetime,
) -> BalanceDefaultDict:
    """Get all the balances from an interval fetcher at a particular effective datetime."""
    balances_mapping = vault.get_balances_timeseries(fetcher_id=fetcher_id)
    balances = get_balance_default_dict_from_mapping(
        mapping=balances_mapping,
        effective_datetime=effective_datetime,
    )
    return balances


def get_balance_default_dict_from_mapping(
    mapping: Mapping[BalanceCoordinate, BalanceTimeseries],
    effective_datetime: datetime | None = None,
) -> BalanceDefaultDict:
    """Converts the balances mapping fetched from `vault.get_balances_timeseries()` into a
    BalanceDefaultDict, taking either the latest or at_datetime entry of the timeseries

    :param mapping: map of balance coordinates to balance timeseries
    :param effective_datetime: if provided, the timeseries value at that timestamp will be used,
    otherwise the latest value will be used
    :return: BalanceDefaultDict from the timeseries mapping
    """
    balance_mapping: dict[BalanceCoordinate, Balance] = {
        coord: (ts.at(at_datetime=effective_datetime) if effective_datetime else ts.latest())
        for coord, ts in mapping.items()
    }
    return BalanceDefaultDict(mapping=balance_mapping)


def sum_balances(
    balances: BalanceDefaultDict,
    denomination: str,
    addresses: Iterable[str] | None = None,
    asset: str = DEFAULT_ASSET,
    phases: Iterable[Phase] | None = None,
) -> Balance:
    """Aggregates balances across a specific set of coordinates.

    This function performs a cross-product summation over the provided addresses
    and phases for a single asset and denomination. If no addresses or phases
    are provided, it defaults to the standard committed address.

    Args:
        balances (BalanceDefaultDict): The balance map to query.
        denomination (str): The currency denomination (e.g., 'GBP').
        addresses (Iterable[str] | None): A set of account addresses to sum.
            Defaults to {DEFAULT_ADDRESS}.
        asset (str): The asset type. Defaults to DEFAULT_ASSET.
        phases (Iterable[Phase] | None): The transaction phases to include
            (e.g., COMMITTED, PENDING). Defaults to {Phase.COMMITTED}.

    Returns:
        Balance: A single Balance object representing the sum of all
            matched coordinates.
    """
    addresses_set = set(addresses) if addresses else {DEFAULT_ADDRESS}
    phases_set = set(phases) if phases else {Phase.COMMITTED}
    return sum(
        [
            balances[BalanceCoordinate(a, asset, denomination, p)]
            for a in addresses_set
            for p in phases_set
        ],
        Balance(),
    )


def net_debit(bal: Balance) -> Decimal:
    """Calculates the net debit value of a Balance object.

    The result is positive if debits exceed credits, representing the
    net amount owed or withdrawn.

    Args:
        bal (Balance): The balance object containing debit and credit totals.

    Returns:
        Decimal: The difference of (debit - credit).
    """
    return bal.debit - bal.credit


def net_credit(bal: Balance) -> Decimal:
    """Calculates the net credit value of a Balance object.

    The result is positive if credits exceed debits, representing the
    net amount held or deposited.

    Args:
        bal (Balance): The balance object containing debit and credit totals.

    Returns:
        Decimal: The difference of (credit - debit).
    """
    return bal.credit - bal.debit


def get_available_balance(
    balances: BalanceDefaultDict,
    denomination: str,
    address: str = DEFAULT_ADDRESS,
    asset: str = DEFAULT_ASSET,
    phase: Phase | None = None,
) -> Balance:
    """Returns the sum of net balances including COMMITTED and PENDING_OUT only.

    The function serves two different purposes, depending on the type of balances provided:
    1. When account balances (absolute balances) are used, it returns the available balance
    of the account
    2. When posting balances (relative balances) are used, it calculates the impact of the
    posting on the available balance of the account, providing insights into how the posting
    will affect the account balance

    :param balances: BalanceDefaultDict, account balances or posting balances
    :param denomination: balance denomination
    :param address: balance address
    :param asset: balance asset
    :param phase: posting phase.  Defaults to {Phase.COMMITTED, Phase.PENDING_OUT} if not specified.
    :return: sum of committed and pending out balance coordinates
    """
    phases = {phase} if phase else {Phase.COMMITTED, Phase.PENDING_OUT}
    return sum_balances(
        balances=balances,
        denomination=denomination,
        addresses={address},
        asset=asset,
        phases=phases,
    )


def get_current_net_balance(
    balances: BalanceDefaultDict,
    denomination: str,
    address: str = DEFAULT_ADDRESS,
    asset: str = DEFAULT_ASSET,
    phase: Phase | None = None,
) -> Balance:
    """Returns the sum of net balances for COMMITTED and PENDING_IN only.
    Used for depositing scenarios.

    :param balances: BalanceDefaultDict for an account
    :param denomination: balance denomination
    :param address: balance address
    :param asset: balance asset
    :param phase: posting phase.  Defaults to {Phase.COMMITTED, Phase.PENDING_IN} if not specified.
    :return: sum of net attribute of committed and pending_in balance coordinates
    """
    phases = {phase} if phase else {Phase.COMMITTED, Phase.PENDING_IN}
    return sum_balances(
        balances=balances,
        denomination=denomination,
        addresses={address},
        asset=asset,
        phases=phases,
    )


def get_current_balance_coordinates(
    *,
    denomination: str,
    address: str,
    asset: str,
) -> tuple[BalanceCoordinate, BalanceCoordinate]:
    """Returns the COMMITTED and PENDING_IN balance coordinates.

    :param denomination: balance denomination
    :param address: balance address
    :param asset: balance asset
    :return: the committed and pending balance coordinates
    """
    committed_coordinate = BalanceCoordinate(
        account_address=address, asset=asset, denomination=denomination, phase=Phase.COMMITTED
    )
    pending_in_coordinate = BalanceCoordinate(
        account_address=address, asset=asset, denomination=denomination, phase=Phase.PENDING_IN
    )
    return committed_coordinate, pending_in_coordinate


def get_coordinates(
    addresses: Iterable[str],
    denomination: str,
    asset: str = DEFAULT_ASSET,
    phases: Iterable[Phase] | None = None,
) -> set[BalanceCoordinate]:
    """Returns a list of Balance coordinates based on provided address names, denomination, asset and
    phases

    Args:
        addresses (Iterable[str]): The address names
        denomination (str): The denomination
        asset (str, optional): The asset type. Defaults to DEFAULT_ASSET.
        phases (Iterable[Phase] | None, optional): The required balance phases. Defaults to None.

    Returns:
        set[BalanceCoordinate]: Set of balance coordinates
    """

    addresses_set = set(addresses)
    phases_set = set(phases) if phases else {Phase.COMMITTED}

    return {BalanceCoordinate(a, asset, denomination, p) for a in addresses_set for p in phases_set}


def validate_ready_for_closure(balances: BalanceDefaultDict) -> Rejection | None:
    """Validates if an account is ready for closure by checking if all balances are zero.

    Args:
        balances (BalanceDefaultDict): The balances to check.

    Returns:
        Rejection | None: A rejection if any balance is non-zero, otherwise None.
    """
    has_non_zero_bals = any(balances[bal_coord].net for bal_coord in balances.keys())
    if has_non_zero_bals:
        return Rejection(
            message="There are non-zero balances.", reason_code=RejectionReason.AGAINST_TNC
        )

    return None


def update_inflight_balances(
    account_id: str,
    tside: Tside,
    current_balances: BalanceDefaultDict,
    posting_instructions: posting_utils.PostingInstructionListAlias,
) -> BalanceDefaultDict:
    """Returns a new BalanceDefaultDict, merging the current balances with the posting balances

    :param account_id: id of the vault account, required for the .balances() method
    :param tside: tside of the account, required for the .balances() method
    :param current_balances: the current balances to be merged with the posting balances
    :param posting_instructions: list of posting instruction objects to get the balances of to
    merge with the current balances
    :return: A new BalanceDefaultDict with the merged balances
    """
    # A new BalanceDefaultDict object is created to avoid mutating the current balances
    inflight_balances = BalanceDefaultDict(mapping=current_balances)
    for posting_instruction in posting_instructions:
        inflight_balances += posting_instruction.balances(account_id=account_id, tside=tside)

    return inflight_balances
