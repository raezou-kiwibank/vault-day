__smart_contract_feature__ = True

# standard libs
from datetime import datetime
from decimal import Decimal
from json import loads
from typing import NamedTuple

# features
import feature_library.common.state_utils as state_utils

# contracts api
from contracts_api import (
    DefinedDateTime,
    ExpectedParameter,
    FlagsObservationFetcher,
    ParametersFilter,
    ParametersObservationFetcher,
    Rejection,
    RejectionReason,
)

# inception sdk
from inception_sdk.vault.contracts.extensions.contracts_api_extensions import SmartContractVault

# Parameters
DORMANCY_FLAGS_PARAM_ID = "&{dormancy_flags}"
DORMANCY_FLAGS_PARAM = ExpectedParameter(
    id=DORMANCY_FLAGS_PARAM_ID,
    triggers_pre_parameter_change_hook=False,
    triggers_post_parameter_change_hook=False,
)

expected_parameters = [DORMANCY_FLAGS_PARAM]

# Fetchers
DORMANCY_PARAMS_ET_POF_ID = "dormancy_params_et_pof"
DORMANCY_PARAMS_ET_POF = ParametersObservationFetcher(
    fetcher_id=DORMANCY_PARAMS_ET_POF_ID,
    at=DefinedDateTime.EFFECTIVE_DATETIME,
    filter=ParametersFilter(parameter_ids=[p.id for p in expected_parameters]),
)

DORMANCY_FOF_ID = "dormancy_flags_fetcher"
DORMANCY_FOF = FlagsObservationFetcher(
    fetcher_id=DORMANCY_FOF_ID,
    at=DefinedDateTime.EFFECTIVE_DATETIME,
)

data_fetchers = [
    DORMANCY_PARAMS_ET_POF,
    DORMANCY_FOF,
]

DormancyFetchersConfig = NamedTuple(
    "DormancyFetchersConfig",
    [
        ("param_fetcher_id", str),
        ("flags_fetcher_id", str),
    ],
)
DEFAULT_DORMANCY_FETCHERS_CONFIG = DormancyFetchersConfig(
    param_fetcher_id=DORMANCY_PARAMS_ET_POF_ID,
    flags_fetcher_id=DORMANCY_FOF_ID,
)


def get_parameters(
    vault: SmartContractVault, param_fetcher_id: str = DORMANCY_PARAMS_ET_POF_ID
) -> dict[str, datetime | Decimal | str | None]:
    """Retrieves configuration parameters for the dormancy feature.

    Args:
        vault: The SmartContractVault instance to query.
        param_fetcher_id: The unique identifier for the parameter fetcher.
            Defaults to `DORMANCY_PARAMS_ET_POF_ID`.

    Returns:
        dict[str, datetime | Decimal | str | None]: Parameters for the dormancy feature.
    """
    return vault.get_parameters_observation(fetcher_id=param_fetcher_id).parameters  # type: ignore


def _append_to_state(
    state: state_utils.SmartContractState,
    fetchers_config: DormancyFetchersConfig = DEFAULT_DORMANCY_FETCHERS_CONFIG,
) -> state_utils.SmartContractState:
    """Updates the contract state with specific parameter observations.

    Args:
        state: The current state of the smart contract, containing the vault object.
        fetchers_config: Configuration for the fetchers used to retrieve parameters.
            Defaults to `DEFAULT_DORMANCY_FETCHERS_CONFIG`.

    Returns:
        state_utils.SmartContractState: A new state object containing the appended parameters.
    """
    return state_utils.append_to_state(
        state=state,
        parameters=get_parameters(state.vault, fetchers_config.param_fetcher_id),
    )


def is_account_dormant(
    state: state_utils.SmartContractState,
    fetchers_config: DormancyFetchersConfig = DEFAULT_DORMANCY_FETCHERS_CONFIG,
) -> bool:
    """Checks if the account has any of the specified dormancy flags applied.

    Args:
        state: The current state of the smart contract.
        fetchers_config: Configuration for the fetchers used to retrieve parameters and flags.
            Defaults to `DEFAULT_DORMANCY_FETCHERS_CONFIG`.

    Returns:
        bool: True if the account is dormant, False otherwise.
    """
    rejection = state_utils.check_parameters_exist(state=state, param_ids={DORMANCY_FLAGS_PARAM_ID})
    assert rejection is None, rejection

    dormancy_flags: list[str] = loads(state.parameters[DORMANCY_FLAGS_PARAM_ID])  # type: ignore

    flags_observation = state.vault.get_flags_observation(
        fetcher_id=fetchers_config.flags_fetcher_id
    )
    if not flags_observation:
        return False

    return any(flags_observation.flags.get(flag_id) for flag_id in dormancy_flags)


def validate_account_transaction(
    state: state_utils.SmartContractState,
    fetchers_config: DormancyFetchersConfig = DEFAULT_DORMANCY_FETCHERS_CONFIG,
) -> Rejection | None:
    """Validates proposed postings against dormancy rules.

    Args:
        state: The current state of the smart contract.
        fetchers_config: Configuration for the fetchers used to retrieve parameters and flags.
            Defaults to `DEFAULT_DORMANCY_FETCHERS_CONFIG`.

    Returns:
        Rejection | None: A rejection if validation fails, otherwise None.
    """
    state = _append_to_state(state=state, fetchers_config=fetchers_config)

    if is_account_dormant(state=state, fetchers_config=fetchers_config):
        return Rejection(
            message="Account flagged 'Dormant' does not accept external transactions.",
            reason_code=RejectionReason.AGAINST_TNC,
        )
    return None
