__smart_contract_feature__ = True

# standard libs
from datetime import datetime
from decimal import Decimal
from typing import NamedTuple

# feature library
import feature_library.common.balance_utils as balance_utils
import feature_library.common.denomination as denomination_module
import feature_library.common.posting_utils as posting_utils
import feature_library.common.state_utils as state_utils
import feature_library.common.utils as common_utils

# contracts api
from contracts_api import (
    DefinedDateTime,
    ExpectedParameter,
    ParametersFilter,
    ParametersObservationFetcher,
    Rejection,
    RejectionReason,
)

# inception sdk
from inception_sdk.vault.contracts.extensions.contracts_api_extensions import SmartContractVault

# Parameters
MINIMUM_SINGLE_DEPOSIT_PARAM_ID = "&{minimum_deposit}"
MINIMUM_SINGLE_DEPOSIT_PARAM = ExpectedParameter(
    id=MINIMUM_SINGLE_DEPOSIT_PARAM_ID,
    optional=True,
    triggers_pre_parameter_change_hook=False,
    triggers_post_parameter_change_hook=False,
)

expected_parameters = [
    MINIMUM_SINGLE_DEPOSIT_PARAM,
    denomination_module.DENOMINATION_PARAM,
]

# Fetchers
MIN_SINGLE_DEPOSIT_POF_ID = "min_single_deposit_pof"
MIN_SINGLE_DEPOSIT_POF = ParametersObservationFetcher(
    fetcher_id=MIN_SINGLE_DEPOSIT_POF_ID,
    at=DefinedDateTime.EFFECTIVE_DATETIME,
    filter=ParametersFilter(parameter_ids=[p.id for p in expected_parameters]),
)

data_fetchers = [
    MIN_SINGLE_DEPOSIT_POF,
]

MinimumSingleDepositFetchersConfig = NamedTuple(
    "MinimumSingleDepositFetchersConfig",
    [
        ("param_fetcher_id", str),
        ("denomination_param_id", str),
    ],
)

DEFAULT_MINIMUM_SINGLE_DEPOSIT_FETCHERS_CONFIG = MinimumSingleDepositFetchersConfig(
    param_fetcher_id=MIN_SINGLE_DEPOSIT_POF_ID,
    denomination_param_id=denomination_module.DENOMINATION_PARAM.id,
)


def get_parameters(
    vault: SmartContractVault, param_fetcher_id: str = MIN_SINGLE_DEPOSIT_POF_ID
) -> dict[str, datetime | Decimal | str | None]:
    """Retrieves configuration parameters for the minimum single deposit limit feature.

    Args:
        vault: The SmartContractVault instance to query.
        param_fetcher_id: The unique identifier for the parameter fetcher.
            Defaults to `MIN_SINGLE_DEPOSIT_POF_ID`.

    Returns:
        Parameters for the minimum single deposit limit feature.
    """
    return vault.get_parameters_observation(fetcher_id=param_fetcher_id).parameters


def append_to_state(
    state: state_utils.SmartContractState,
    param_fetcher_id: str = MIN_SINGLE_DEPOSIT_POF_ID,
) -> state_utils.SmartContractState:
    """Updates the contract state with specific parameter observations.

    Args:
        state: The current state of the smart contract, containing the vault object.
        param_fetcher_id: The ID of the fetcher used to retrieve parameters.
            Defaults to `MIN_SINGLE_DEPOSIT_POF_ID`.

    Returns:
        A new state object containing the appended parameters.
    """
    return state_utils.append_to_state(
        state=state,
        parameters=get_parameters(state.vault, param_fetcher_id),
    )


def validate(
    state: state_utils.SmartContractState,
    postings: posting_utils.PostingInstructionListAlias,
    fetchers_config: MinimumSingleDepositFetchersConfig = (
        DEFAULT_MINIMUM_SINGLE_DEPOSIT_FETCHERS_CONFIG
    ),
) -> Rejection | None:
    """Reject if the deposit amount does not meet the minimum deposit limit.

    Args:
        state: SmartContractState containing the vault object and effective datetime.
        postings: List of posting instructions to process.
        fetchers_config: Configuration for the required fetchers and parameters.

    Returns:
        A rejection if the limit conditions are not met, otherwise None.
    """
    state = append_to_state(state, fetchers_config.param_fetcher_id)
    rejection = state_utils.check_parameters_exist(state, {fetchers_config.denomination_param_id})
    if rejection is not None:
        return rejection

    minimum_deposit: Decimal | None = state.parameters.get(MINIMUM_SINGLE_DEPOSIT_PARAM_ID)  # type: ignore
    if minimum_deposit is None:
        return None

    denomination = str(state.parameters[fetchers_config.denomination_param_id])

    for posting in postings:
        posting_balances = posting.balances()
        deposit_value = balance_utils.net_credit(
            balance_utils.get_current_net_balance(
                balances=posting_balances, denomination=denomination
            )
        )
        if 0 < deposit_value < minimum_deposit:
            deposit_value_rounded = common_utils.round_decimal(deposit_value, 5)
            minimum_deposit_rounded = common_utils.round_decimal(minimum_deposit, 5)
            return Rejection(
                message=f"Transaction amount {common_utils.remove_exponent(deposit_value_rounded)} "
                f"{denomination} is less than the minimum deposit amount "
                f"{common_utils.remove_exponent(minimum_deposit_rounded)} {denomination}.",
                reason_code=RejectionReason.AGAINST_TNC,
            )

    return None
