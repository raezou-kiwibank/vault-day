__smart_contract_feature__ = True

# standard libs
from datetime import datetime
from decimal import Decimal

import feature_library.common.balance_utils as balance_utils

# features
import feature_library.common.denomination as denomination_module
import feature_library.common.fetchers as fetchers
import feature_library.common.posting_utils as posting_utils
import feature_library.common.state_utils as state_utils

# contracts api
from contracts_api import (
    BalanceDefaultDict,
    DefinedDateTime,
    ExpectedParameter,
    ParametersFilter,
    ParametersObservationFetcher,
    Phase,
    Rejection,
    RejectionReason,
)

# inception sdk
from inception_sdk.vault.contracts.extensions.contracts_api_extensions import SmartContractVault

# Parameters
MIN_INITIAL_DEPOSIT_PARAM_ID = "&{minimum_initial_deposit}"
MIN_INITIAL_DEPOSIT_PARAM = ExpectedParameter(
    id=MIN_INITIAL_DEPOSIT_PARAM_ID,
    triggers_pre_parameter_change_hook=False,
    triggers_post_parameter_change_hook=False,
)

expected_parameters = [
    MIN_INITIAL_DEPOSIT_PARAM,
    denomination_module.DENOMINATION_PARAM,
]

# Fetchers
MIN_INITIAL_DEPOSIT_POF_ID = "minimum_initial_deposit_pof"
MIN_INITIAL_DEPOSIT_POF = ParametersObservationFetcher(
    fetcher_id=MIN_INITIAL_DEPOSIT_POF_ID,
    at=DefinedDateTime.EFFECTIVE_DATETIME,
    filter=ParametersFilter(parameter_ids=[MIN_INITIAL_DEPOSIT_PARAM.id]),
)
data_fetchers = [fetchers.ALL_BALANCES_LIVE_BOF, MIN_INITIAL_DEPOSIT_POF]


def get_parameters(
    vault: SmartContractVault, param_fetcher_id: str = MIN_INITIAL_DEPOSIT_POF_ID
) -> dict[str, datetime | Decimal | str | None]:
    """Retrieves configuration parameters from a for the maximum balance limit feature.

    Args:
        vault: The SmartContractVault instance to query.
        param_fetcher_id: The unique identifier for the parameter fetcher.
            Defaults to `MIN_INITIAL_DEPOSIT_POF_ID`.

    Returns:
        Parameters for the maximum balance limit feature.
        (datetime, Decimal, string, or None).
    """
    return vault.get_parameters_observation(fetcher_id=param_fetcher_id).parameters


def _append_to_state(
    state: state_utils.SmartContractState,
    balance_fetcher_id: str = fetchers.ALL_BALANCES_LIVE_BOF_ID,
    param_fetcher_id: str = MIN_INITIAL_DEPOSIT_POF_ID,
) -> state_utils.SmartContractState:
    """Extends the Smart Contract state with vault parameters and balance observations.

    This helper function fetches parameter data and live balances from the vault
    associated with the current state and merges them into a new state object.

    Fetchers:
        Balances:
            LIVE_BALANCES_BOF_ID: Used to retrieve current vault balances.
        Parameters:
            MIN_INITIAL_DEPOSIT_POF_ID: Used to retrieve vault parameter observations.

    Args:
        state (SmartContractState): The current state object containing the vault reference.
        balance_fetcher_id (str): The ID of the fetcher used to observe balances.
            Defaults to LIVE_BALANCES_BOF_ID.
        param_fetcher_id (str): The ID of the fetcher used to observe parameters.
            Defaults to MIN_INITIAL_DEPOSIT_POF_ID.

    Returns:
        SmartContractState: A new state object updated with the fetched parameters
            and balances.
    """
    return state_utils.append_to_state(
        state=state,
        parameters=get_parameters(state.vault, param_fetcher_id),
        balances=state.vault.get_balances_observation(fetcher_id=balance_fetcher_id).balances,
    )


def validate(
    *,
    state: state_utils.SmartContractState,
    postings: posting_utils.PostingInstructionListAlias,
    balance_fetcher_id: str = fetchers.ALL_BALANCES_LIVE_BOF_ID,
    param_fetcher_id: str = MIN_INITIAL_DEPOSIT_POF_ID,
    denomination_param_id: str = denomination_module.DENOMINATION_PARAM_ID,
    minimum_initial_deposit_param_id: str = MIN_INITIAL_DEPOSIT_PARAM_ID,
) -> Rejection | None:
    """Reject the list of postings if their net affect does not meet the minimum initial deposit limit
    :param vault: Vault object for the account whose limits are being validated
    :param postings: list of postings instructions being checked to ensure they meet the initial
    deposit limit
    :param denomination: the denomination of the account
    :param balances: latest account balances available, if not provided will retrieve the latest
    balances
    :return: rejection if the limit conditions are not met
    """
    state = _append_to_state(state, balance_fetcher_id, param_fetcher_id)
    if rejection := state_utils.check_parameters_exist(state, {denomination_param_id}):
        return rejection

    denomination: str = state.parameters[denomination_param_id]  # type: ignore

    min_initial_deposit: Decimal | None = state.parameters[minimum_initial_deposit_param_id]  # type: ignore
    if min_initial_deposit is None:
        return None

    available_credit_balance: Decimal = balance_utils.net_credit(
        balance_utils.sum_balances(
            balances=state.balances,
            denomination=denomination,
            phases={Phase.COMMITTED, Phase.PENDING_IN},
        )
    )

    # THe current posting is not the initial posting due to existing credit, so don't validate it.
    if available_credit_balance > Decimal(0):
        return None

    # Calculate the net affect of postings
    posting_balances: BalanceDefaultDict = posting_utils.get_posting_instructions_balances(postings)
    deposit_value: Decimal = balance_utils.net_credit(
        balance_utils.sum_balances(balances=posting_balances, denomination=denomination)
    )

    # Reject if the net effect is below the min threhsold, but ignore debits.
    if Decimal(0) < deposit_value < min_initial_deposit:
        return Rejection(
            message=f"Transaction amount {deposit_value:0.2f} {denomination} is less than the "
            f"minimum initial deposit amount {min_initial_deposit:0.2f} {denomination}.",
            reason_code=RejectionReason.AGAINST_TNC,
        )

    return None
