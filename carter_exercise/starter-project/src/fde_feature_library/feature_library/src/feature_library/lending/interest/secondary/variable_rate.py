"""Variable rate feature."""

__smart_contract_feature__ = True

# standard libs
from datetime import datetime
from decimal import Decimal
from typing import NamedTuple

# features
import feature_library.common.state_utils as state_utils
import feature_library.lending.interest.interest_accrual as interest_accrual

# contracts api
from contracts_api import (
    DefinedDateTime,
    ExpectedParameter,
    ParametersFilter,
    ParametersObservationFetcher,
)

# inception sdk
from inception_sdk.vault.contracts.extensions.contracts_api_extensions import SmartContractVault

# Expected Parameters
ANNUAL_INTEREST_RATE_CAP_PARAM_ID = "&{annual_interest_rate_cap}"
ANNUAL_INTEREST_RATE_CAP_PARAM = ExpectedParameter(
    id=ANNUAL_INTEREST_RATE_CAP_PARAM_ID,
    optional=True,
    triggers_pre_parameter_change_hook=False,
    triggers_post_parameter_change_hook=False,
)


ANNUAL_INTEREST_RATE_FLOOR_PARAM_ID = "&{annual_interest_rate_floor}"
ANNUAL_INTEREST_RATE_FLOOR_PARAM = ExpectedParameter(
    id=ANNUAL_INTEREST_RATE_FLOOR_PARAM_ID,
    optional=True,
    triggers_pre_parameter_change_hook=False,
    triggers_post_parameter_change_hook=False,
)

VARIABLE_INTEREST_RATE_PARAM_ID = "&{variable_interest_rate}"
VARIABLE_INTEREST_RATE_PARAM = ExpectedParameter(
    id=VARIABLE_INTEREST_RATE_PARAM_ID,
    triggers_pre_parameter_change_hook=True,
    triggers_post_parameter_change_hook=True,
)

VARIABLE_RATE_ADJUSTMENT_PARAM_ID = "&{variable_rate_adjustment}"
VARIABLE_RATE_ADJUSTMENT_PARAM = ExpectedParameter(
    id=VARIABLE_RATE_ADJUSTMENT_PARAM_ID,
    triggers_pre_parameter_change_hook=True,
    triggers_post_parameter_change_hook=True,
)

BASE_RATE_PARAM_ID = "&{base_interest_rate}"
BASE_RATE_PARAM = ExpectedParameter(
    id=BASE_RATE_PARAM_ID,
    triggers_pre_parameter_change_hook=True,
    triggers_post_parameter_change_hook=True,
)


expected_parameters = [
    ANNUAL_INTEREST_RATE_CAP_PARAM,
    ANNUAL_INTEREST_RATE_FLOOR_PARAM,
    VARIABLE_INTEREST_RATE_PARAM,
    VARIABLE_RATE_ADJUSTMENT_PARAM,
    BASE_RATE_PARAM,
]

# Fetchers
VARIABLE_RATE_ET_POF_ID = "variable_rate_et_pof"
VARIABLE_RATE_ET_POF = ParametersObservationFetcher(
    fetcher_id=VARIABLE_RATE_ET_POF_ID,
    at=DefinedDateTime.EFFECTIVE_DATETIME,
    filter=ParametersFilter(parameter_ids=[p.id for p in expected_parameters]),
)

data_fetchers = [
    VARIABLE_RATE_ET_POF,
]

VariableRateFetchersConfig = NamedTuple(
    "VariableRateFetchersConfig",
    [
        ("param_fetcher_id", str),
        ("variable_rate_param_ids", set[str]),
        ("annual_rate_cap_param_id", str),
        ("annual_rate_floor_param_id", str),
        ("days_in_year_param_id", str),
    ],
)

DEFAULT_VARIABLE_RATE_FETCHERS_CONFIG = VariableRateFetchersConfig(
    param_fetcher_id=VARIABLE_RATE_ET_POF_ID,
    variable_rate_param_ids={
        VARIABLE_INTEREST_RATE_PARAM_ID,
        VARIABLE_RATE_ADJUSTMENT_PARAM_ID,
        BASE_RATE_PARAM_ID,
    },
    annual_rate_cap_param_id=ANNUAL_INTEREST_RATE_CAP_PARAM_ID,
    annual_rate_floor_param_id=ANNUAL_INTEREST_RATE_FLOOR_PARAM_ID,
    days_in_year_param_id=interest_accrual.DAYS_IN_YEAR_PARAM.id,
)


def get_parameters(
    vault: SmartContractVault, param_fetcher_id: str = VARIABLE_RATE_ET_POF_ID
) -> dict[str, datetime | Decimal | str | None]:
    """Get the variable interest parameters from the specified fetcher.

    Args:
        vault (SmartContractVault): Vault object to retrieve the parameters from
        param_fetcher_id (str, optional): The ID of the parameter fetcher to use.
            Defaults to VARIABLE_RATE_ET_POF_ID.

    Returns:
        dict[str, datetime | Decimal | str | None]: A dictionary mapping parameter IDs to values
    """
    return vault.get_parameters_observation(fetcher_id=param_fetcher_id).parameters


def _append_to_state(
    state: state_utils.SmartContractState,
    param_fetcher_id: str = VARIABLE_RATE_ET_POF_ID,
) -> state_utils.SmartContractState:
    """Append variable interest parameters to the smart contract state.

    Args:
        state (SmartContractState): The current smart contract state
        param_fetcher_id (str, optional): The ID of the parameter fetcher to use.
            Defaults to VARIABLE_RATE_ET_POF_ID.

    Returns:
        SmartContractState: The updated smart contract state
    """
    return state_utils.append_to_state(
        state=state,
        parameters=get_parameters(state.vault, param_fetcher_id),
    )


def get_annual_interest_rate(
    state: state_utils.SmartContractState,
    fetchers_config: VariableRateFetchersConfig = DEFAULT_VARIABLE_RATE_FETCHERS_CONFIG,
) -> Decimal:
    """Determines the annual variable interest rate.

    Includes any variable rate adjustment and accounts for any maximum or minimum
    interest rate limits that may be set.


    Args:
        state (SmartContractState): The current smart contract state
        fetchers_config (VariableRateFetchersConfig, optional): Configuration for the parameter
            fetchers. Defaults to None.

    Returns:
        Decimal: The annual variable interest rate
    """
    rate_param_ids = fetchers_config.variable_rate_param_ids
    annual_rate_cap_param_id = fetchers_config.annual_rate_cap_param_id
    annual_rate_floor_param_id = fetchers_config.annual_rate_floor_param_id

    state = _append_to_state(state=state, param_fetcher_id=fetchers_config.param_fetcher_id)

    rejection = state_utils.check_parameters_exist(
        state=state,
        param_ids=rate_param_ids,
    )

    assert rejection is None, rejection

    rates: list[Decimal] = [state.parameters.get(r, Decimal(0)) for r in rate_param_ids]  # type: ignore

    annual_rate = sum(rates, Decimal(0))

    interest_rate_cap: Decimal = state.parameters.get(annual_rate_cap_param_id, Decimal("inf"))  # type: ignore
    interest_rate_floor: Decimal = state.parameters.get(annual_rate_floor_param_id, Decimal("-inf"))  # type: ignore

    return max(
        min(
            annual_rate,
            interest_rate_cap,
        ),
        interest_rate_floor,
    )
