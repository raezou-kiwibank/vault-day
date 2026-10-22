__smart_contract_feature__ = True
# standard libs
from datetime import datetime
from decimal import Decimal
from typing import NamedTuple

import feature_library.common.balance_utils as balance_utils

# contracts api
from contracts_api import (
    DEFAULT_ASSET,
    Balance,
    BalanceCoordinate,
    BalanceDefaultDict,
    CustomInstruction,
    Phase,
    Rejection,
    RejectionReason,
)

# inception sdk
from inception_sdk.vault.contracts.extensions.contracts_api_extensions import (
    SmartContractVault,
)

# features

SmartContractState = NamedTuple(
    "SmartContractState",
    [
        ("vault", "SmartContractVault"),
        ("effective_datetime", datetime),
        ("parameters", dict[str, datetime | Decimal | str | None]),
        ("balances", BalanceDefaultDict),
        ("inflight_postings", list[CustomInstruction]),
    ],
)


def initialise_state(
    vault: SmartContractVault,
    effective_datetime: datetime,
    parameters: dict[str, datetime | Decimal | str | None] | None = None,
    balances: BalanceDefaultDict | None = None,
    inflight_postings: list[CustomInstruction] = None,
) -> SmartContractState:
    """Initialises a SmartContractState object with the provided vault and values.

    This constructor-wrapper ensures that all optional state components are properly
    instantiated, preventing attribute errors by defaulting None values to
    empty collections.

    Args:
        vault (SmartContractVault): The vault object associated with the contract state.
        effective_datetime (datetime): The point in time at which this state is valid.
        parameters (dict[str, datetime | Decimal | str | None] | None): A dictionary
            of parameter values. Defaults to an empty dict.
        balances (BalanceDefaultDict | None): A dictionary-like object representing
            account balances. Defaults to an empty BalanceDefaultDict.
        inflight_postings (list[CustomInstruction] | None): Postings that will be returned
          by the hook.

    Returns:
        SmartContractState: A fully initialised state object ready for use in
            contract logic.
    """
    return SmartContractState(
        vault=vault,
        effective_datetime=effective_datetime,
        parameters=parameters or {},
        balances=balances or BalanceDefaultDict(lambda: Balance(), {}),
        inflight_postings=inflight_postings or [],
    )


def append_to_state(
    state: SmartContractState,
    vault: SmartContractVault | None = None,
    effective_datetime: datetime | None = None,
    parameters: dict[str, datetime | Decimal | str | None] | None = None,
    balances: BalanceDefaultDict | None = None,
    inflight_postings: list[CustomInstruction] | None = None,
) -> SmartContractState:
    """Creates a new SmartContractState by merging provided values with an existing state.

    This function follows a "copy-on-write" pattern, performing a shallow merge of
    dictionaries and collections. New values provided in the arguments will
    overwrite existing keys in the current state.

    Args:
        state (SmartContractState): The original state to build upon.
        vault (SmartContractVault | None): An optional replacement vault.
            Defaults to state.vault.
        effective_datetime (datetime | None): An optional replacement timestamp.
            Defaults to state.effective_datetime.
        parameters (dict | None): New parameters to merge into the existing set.
            Defaults to an empty dict.
        balances (BalanceDefaultDict | None): New balances to merge into the
            existing set. Defaults to an empty BalanceDefaultDict.
        inflight_postings (list[CustomInstruction] | None): Postings that will be returned
          by the hook.

    Returns:
        SmartContractState: A new state instance containing the merged data.
    """
    return SmartContractState(
        vault=vault or state.vault,
        effective_datetime=effective_datetime or state.effective_datetime,
        parameters=state.parameters | (parameters or {}),
        balances=state.balances | (balances or BalanceDefaultDict(lambda: Balance(), {})),
        inflight_postings=(state.inflight_postings or []) + (inflight_postings or []),
    )


def check_parameters_exist(state: SmartContractState, param_ids: set[str]) -> Rejection | None:
    """Validates that the required parameter IDs are present in the SmartContractState.

    This function performs a two-stage check:
    1. Ensures the state's parameters dictionary is initialized.
    2. Identifies any requested IDs that are missing from the current state.

    Args:
        state (SmartContractState): The contract state to be validated.
        param_ids (set[str]): A set of parameter IDs that must exist in the state.

    Returns:
        Rejection | None: Returns a Rejection object if the parameters are undefined
            or if specific keys are missing. Returns None if all parameters are
            successfully found.

    Rejection Scenarios:
        - RejectionReason.AGAINST_TNC: Raised if state.parameters is None.
        - RejectionReason.AGAINST_TNC: Raised if any ID in param_ids is not found,
          listing all missing IDs in alphabetical order within the message.
    """
    if state.parameters is None:
        return Rejection(
            message="State parameters are not defined.", reason_code=RejectionReason.AGAINST_TNC
        )

    if missing_param_ids := sorted(param_ids - state.parameters.keys()):
        return Rejection(
            message=f"The following parameters are missing: {', '.join(missing_param_ids)}",
            reason_code=RejectionReason.AGAINST_TNC,
        )

    return None


def is_coordinates_in_state(state: SmartContractState, coordinates: set[BalanceCoordinate]) -> bool:
    """Checks if all specified balance coordinates are present in the state's balances.

    Args:
        state (SmartContractState): The contract state to check.
        coordinates (set[BalanceCoordinate]): A set of coordinates to verify.

    Returns:
        bool: True if all coordinates exist in state.balances, False otherwise.
    """

    if not all(coord in state.balances for coord in coordinates):
        return False

    return True


def get_balance_from_state(
    state: SmartContractState,
    fetcher_id: str,
    account_address: str,
    denomination: str,
    asset: str = DEFAULT_ASSET,
    phase: Phase = Phase.COMMITTED,
) -> Decimal:
    """Attempts to get Balance Observation Value from State object.

    If a value has not been stored for the given fetcher_id and balance coordinate,
    get the value from vault object instead.

    Args:
        state (SmartContractState): The current contract state.
        fetcher_id (str): The ID of the fetcher used to observe the balance.
        account_address (str): The account address (e.g., DEFAULT_ADDRESS).
        denomination (str): The currency denomination.
        asset (str): The asset type. Defaults to DEFAULT_ASSET.
        phase (Phase): The transaction phase. Defaults to Phase.COMMITTED.

    Returns:
        Decimal: Net balance
    """
    balance_coordinate = BalanceCoordinate(
        account_address=account_address,
        asset=asset,
        denomination=denomination,
        phase=phase,
    )
    if balance_coordinate in state.balances and fetcher_id in state.balances[balance_coordinate]:
        return state.balances[balance_coordinate][fetcher_id]
    else:
        balance = balance_utils.get_balance_from_observation(
            state.vault, balance_coordinate, fetcher_id=fetcher_id
        )
        if balance_coordinate not in state.balances:
            state.balances[balance_coordinate] = {}
        state.balances[balance_coordinate][fetcher_id] = balance

        return balance
