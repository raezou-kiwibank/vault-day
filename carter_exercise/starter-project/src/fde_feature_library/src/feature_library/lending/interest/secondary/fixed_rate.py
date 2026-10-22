"""Fixed rate feature."""

__smart_contract_feature__ = True

# standard libs
from datetime import datetime
from decimal import Decimal
from typing import NamedTuple

# features
import feature_library.common.state_utils as state_utils

# contracts api
from contracts_api import (
    DefinedDateTime,
    ExpectedParameter,
    ParametersFilter,
    ParametersObservationFetcher,
)

# inception sdk
from inception_sdk.vault.contracts.extensions.contracts_api_extensions import SmartContractVault

FIXED_INTEREST_RATE_PARAM_ID = "&{fixed_interest_rate}"
FIXED_INTEREST_RATE_PARAM = ExpectedParameter(
    id=FIXED_INTEREST_RATE_PARAM_ID,
    triggers_pre_parameter_change_hook=False,
    triggers_post_parameter_change_hook=False,
)


expected_parameters = [FIXED_INTEREST_RATE_PARAM]


# Fetchers
FIXED_INTEREST_RATE_ET_POF_ID = "fixed_interest_rate_et_pof"
FIXED_INTEREST_RATE_ET_POF = ParametersObservationFetcher(
    fetcher_id=FIXED_INTEREST_RATE_ET_POF_ID,
    at=DefinedDateTime.EFFECTIVE_DATETIME,
    filter=ParametersFilter(parameter_ids=[p.id for p in expected_parameters]),
)

data_fetchers = [
    FIXED_INTEREST_RATE_ET_POF,
]

FixedInterestFetchersConfig = NamedTuple(
    "FixedInterestFetchersConfig",
    [
        ("param_fetcher_id", str),
        ("fixed_interest_rate_param_id", str),
    ],
)

DEFAULT_FIXED_INTEREST_FETCHERS_CONFIG = FixedInterestFetchersConfig(
    param_fetcher_id=FIXED_INTEREST_RATE_ET_POF.fetcher_id,
    fixed_interest_rate_param_id=FIXED_INTEREST_RATE_PARAM.id,
)


def get_parameters(
    vault: SmartContractVault, param_fetcher_id: str = FIXED_INTEREST_RATE_ET_POF_ID
) -> dict[str, datetime | Decimal | str | None]:
    """Get the fixed interest parameters from the specified fetcher.

    Args:
        vault (SmartContractVault): Vault object to retrieve the parameters from
        param_fetcher_id (str, optional): The ID of the parameter fetcher to use.
            Defaults to FIXED_INTEREST_RATE_ET_POF_ID.

    Returns:
        dict[str, datetime | Decimal | str | None]: A dictionary mapping parameter IDs to values
    """
    return vault.get_parameters_observation(fetcher_id=param_fetcher_id).parameters


def _append_to_state(
    state: state_utils.SmartContractState,
    param_fetcher_id: str = FIXED_INTEREST_RATE_ET_POF_ID,
) -> state_utils.SmartContractState:
    """Append fixed interest parameters to the smart contract state.

    Args:
        state (SmartContractState): The current smart contract state
        param_fetcher_id (str, optional): The ID of the parameter fetcher to use.
            Defaults to FIXED_INTEREST_RATE_ET_POF_ID.

    Returns:
        SmartContractState: The updated smart contract state
    """
    return state_utils.append_to_state(
        state=state,
        parameters=get_parameters(state.vault, param_fetcher_id),
    )


def get_annual_interest_rate(
    state: state_utils.SmartContractState,
    fetchers_config: FixedInterestFetchersConfig = DEFAULT_FIXED_INTEREST_FETCHERS_CONFIG,
) -> Decimal:
    """Get the annual fixed interest rate from the smart contract state.

    Args:
        state (SmartContractState): The current smart contract state
        fetchers_config (FixedInterestFetchersConfig, optional): Configuration for the parameter
            fetchers. Defaults to DEFAULT_FIXED_INTEREST_FETCHERS_CONFIG.

    Returns:
        Decimal: The annual fixed interest rate
    """
    state = _append_to_state(state=state, param_fetcher_id=fetchers_config.param_fetcher_id)

    rejection = state_utils.check_parameters_exist(
        state=state,
        param_ids={
            fetchers_config.fixed_interest_rate_param_id,
        },
    )

    assert rejection is None, rejection

    return state.parameters[fetchers_config.fixed_interest_rate_param_id]  # type: ignore
