__smart_contract_feature__ = True

# standard-library
from datetime import datetime
from decimal import Decimal

# feature-library
import feature_library.common.state_utils as state_utils

# contracts-api
from contracts_api import (
    DefinedDateTime,
    ExpectedParameter,
    ParametersFilter,
    ParametersObservationFetcher,
)

# inception sdk
from inception_sdk.vault.contracts.extensions.contracts_api_extensions import SmartContractVault

APPLICATION_PRECISION_PARAM_ID = "&{application_precision}"
APPLICATION_PRECISION_PARAM = ExpectedParameter(
    id=APPLICATION_PRECISION_PARAM_ID,
    triggers_pre_parameter_change_hook=False,
    triggers_post_parameter_change_hook=False,
)

APPLICATION_PRECISION_LIVE_POF_ID = "application_precision_live_fetcher"
APPLICATION_PRECISION_LIVE_POF = ParametersObservationFetcher(
    fetcher_id=APPLICATION_PRECISION_LIVE_POF_ID,
    at=DefinedDateTime.LIVE,
    filter=ParametersFilter(parameter_ids=[APPLICATION_PRECISION_PARAM_ID]),
)

APPLICATION_PRECISION_ET_POF_ID = "application_precision_at_effective_datetime_fetcher"
APPLICATION_PRECISION_ET_POF = ParametersObservationFetcher(
    fetcher_id=APPLICATION_PRECISION_ET_POF_ID,
    at=DefinedDateTime.EFFECTIVE_DATETIME,
    filter=ParametersFilter(parameter_ids=[APPLICATION_PRECISION_PARAM_ID]),
)

expected_parameters = [
    APPLICATION_PRECISION_PARAM,
]

data_fetchers = [
    APPLICATION_PRECISION_ET_POF,
    APPLICATION_PRECISION_LIVE_POF,
]


def get_parameters(
    vault: SmartContractVault, fetcher_id: str = APPLICATION_PRECISION_ET_POF_ID
) -> dict[str, str | datetime | Decimal | None]:
    """Retrieves the application precision parameters from a vault parameter observation.

    Args:
        vault (SmartContractVault): The vault object to query for observations.
        fetcher_id (str): The ID of the parameter observation fetcher.
            Defaults to APPLICATION_PRECISION_ET_POF_ID.

    Returns:
        dict[str, str | datetime | Decimal | None]: A dictionary containing the
            observed parameter keys and values.
    """
    return vault.get_parameters_observation(fetcher_id=fetcher_id).parameters


def add_application_precision_to_state(
    state: state_utils.SmartContractState,
    param_fetcher_id: str = APPLICATION_PRECISION_ET_POF_ID,
) -> state_utils.SmartContractState:
    """Updates the contract state with application precision parameters fetched from the vault.

    Args:
        state (state_utils.SmartContractState): The current state object.
        param_fetcher_id (str): The ID of the fetcher used to retrieve parameters.
            Defaults to APPLICATION_PRECISION_ET_POF_ID.

    Returns:
        state_utils.SmartContractState: A new state object containing the merged
            application precision parameters.
    """
    return state_utils.append_to_state(
        state=state,
        parameters=get_parameters(state.vault, param_fetcher_id),
    )


def get_application_precision(
    state: state_utils.SmartContractState,
    application_precision_param_id: str = APPLICATION_PRECISION_PARAM_ID,
) -> int:
    """Retrieves the application precision from the state.

    Args:
        state (state_utils.SmartContractState): The current state object.
        application_precision_param_id (str): The ID of the application precision parameter.
            Defaults to APPLICATION_PRECISION_PARAM_ID.

    Returns:
        int: The application precision value.
    """
    rejection = state_utils.check_parameters_exist(state, {application_precision_param_id})
    assert rejection is None, rejection

    return int(state.parameters[application_precision_param_id])  # type: ignore
