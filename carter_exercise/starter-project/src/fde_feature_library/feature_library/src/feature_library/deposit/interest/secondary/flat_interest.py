"""Flat interest rate feature module for deposit accounts.

Calculates and retrieves flat interest rates and accrual amounts.
"""

__smart_contract_feature__ = True
# CBF: CPP-1912
# CBF: CPP-1967
# Note: The functionality to decide between capitalisation and forfeiture of the accrued interest
# described in the CBF has not been implemented yet. Currently only the forfeiture option has been
# implemented And is part of the Tiered Interest Accrual feature.


# standard libs
from datetime import datetime
from decimal import Decimal
from typing import NamedTuple

# feature library
import feature_library.common.balance_utils as balance_utils
import feature_library.common.denomination as denomination
import feature_library.common.parameter_utils as parameter_utils
import feature_library.common.state_utils as state_utils
import feature_library.common.tuples as common_tuples
import feature_library.common.utils as utils
import feature_library.deposit.addresses as deposit_addresses
import feature_library.deposit.interest.interest_accrual as interest_accrual
import feature_library.deposit.interfaces as deposit_interfaces

# contracts api
from contracts_api import (
    Balance,
    DefinedDateTime,
    ExpectedParameter,
    ParametersFilter,
    ParametersObservationFetcher,
)

# inception sdk
from inception_sdk.vault.contracts.extensions.contracts_api_extensions import SmartContractVault

# Imported param IDs
ACCRUED_INTEREST_PAYABLE_ACCOUNT_PARAM_ID = (
    interest_accrual.ACCRUED_INTEREST_PAYABLE_ACCOUNT_PARAM_ID
)
ACCRUED_INTEREST_RECEIVABLE_ACCOUNT_PARAM_ID = (
    interest_accrual.ACCRUED_INTEREST_RECEIVABLE_ACCOUNT_PARAM_ID
)
DAYS_IN_YEAR_PARAM_ID = interest_accrual.DAYS_IN_YEAR_PARAM_ID
ACCRUAL_PRECISION_PARAM_ID = interest_accrual.ACCRUAL_PRECISION_PARAM_ID
DENOMINATION_PARAM_ID = denomination.DENOMINATION_PARAM_ID

# Balance Addresses
ACCRUED_INTEREST_PAYABLE_ADDRESS = deposit_addresses.ACCRUED_INTEREST_PAYABLE
ACCRUED_INTEREST_RECEIVABLE_ADDRESS = deposit_addresses.ACCRUED_INTEREST_RECEIVABLE

# Expected Parameters
FIXED_INTEREST_RATE_PARAM_ID = "&{fixed_interest_rate}"
FIXED_INTEREST_RATE_PARAM = ExpectedParameter(
    id=FIXED_INTEREST_RATE_PARAM_ID,
    triggers_pre_parameter_change_hook=False,
    triggers_post_parameter_change_hook=False,
)

# Data Fetchers
FIXED_INTEREST_RATE_ET_POF_ID = "fixed_interest_rate_et_pof"
FIXED_INTEREST_RATE_ET_POF = ParametersObservationFetcher(
    fetcher_id=FIXED_INTEREST_RATE_ET_POF_ID,
    at=DefinedDateTime.EFFECTIVE_DATETIME,
    filter=ParametersFilter(parameter_ids=[FIXED_INTEREST_RATE_PARAM_ID]),
)

expected_parameters = [
    FIXED_INTEREST_RATE_PARAM,
]

data_fetchers = [
    FIXED_INTEREST_RATE_ET_POF,
]

FlatInterestFetchersConfig = NamedTuple(
    "FlatInterestFetchersConfig",
    [
        ("param_fetcher_id", str),
        ("fixed_interest_rate_param_id", str),
    ],
)

DEFAULT_FLAT_INTEREST_FETCHERS_CONFIG = FlatInterestFetchersConfig(
    param_fetcher_id=FIXED_INTEREST_RATE_ET_POF_ID,
    fixed_interest_rate_param_id=FIXED_INTEREST_RATE_PARAM_ID,
)


def get_parameters(
    vault: SmartContractVault, param_fetcher_id: str = FIXED_INTEREST_RATE_ET_POF_ID
) -> dict[str, datetime | Decimal | str | None]:
    """Get required parameters for fixed interest from fetcher.

    Returns:
        dict[str, datetime | Decimal | str | None]: Dictionary mapping parameter ids to values
    """

    return vault.get_parameters_observation(fetcher_id=param_fetcher_id).parameters


def _append_to_state(
    state: state_utils.SmartContractState,
    param_fetcher_id: str = FIXED_INTEREST_RATE_ET_POF_ID,
) -> state_utils.SmartContractState:
    """Function used to add flat interest parameters to state object.

    Args:
        state (state_utils.SmartContractState): Smart contract state
        param_fetcher_id (str, optional): The fetcher id for the required fixed interest
            parameters. Defaults to TIERED_INTEREST_RATE_ET_POF_ID.

    Returns:
        state_utils.SmartContractState: Updated Smart Contract state
    """
    return state_utils.append_to_state(
        state=state,
        parameters=get_parameters(state.vault, param_fetcher_id),
    )


def get_interest_rate(
    state: state_utils.SmartContractState,
    fetchers_config: FlatInterestFetchersConfig | None = None,
) -> common_tuples.InterestRateTuple:
    """Get interest rate from state.

    Args:
        state (state_utils.SmartContractState): Smart Contract state
        fetchers_config (FlatInterestFetchersConfig, optional): Fetchers configuration.
            Defaults to DEFAULT_FLAT_INTEREST_FETCHERS_CONFIG.

    Returns:
        common_tuples.InterestRateTuple: Interest rate tuple containing interest rate.
    """

    fetchers_config = fetchers_config or DEFAULT_FLAT_INTEREST_FETCHERS_CONFIG

    state = _append_to_state(
        state=state,
        param_fetcher_id=fetchers_config.param_fetcher_id,
    )

    rejection = state_utils.check_parameters_exist(
        state=state,
        param_ids={fetchers_config.fixed_interest_rate_param_id},
    )
    assert rejection is None, rejection

    fixed_interest_rate: Decimal = state.parameters.get(
        fetchers_config.fixed_interest_rate_param_id
    )  # type: ignore

    return common_tuples.InterestRateTuple(
        interest_rate_param_value=fixed_interest_rate,
        interest_type=common_tuples.INTEREST_TYPE_FLAT,
    )


def get_fixed_interest_accrual_amount(
    *,
    effective_balance: Balance,
    effective_datetime: datetime,
    interest_rates: Decimal,
    days_in_year: str,
    precision: int = 5,
    state: state_utils.SmartContractState | None = None,
    fetchers_config: FlatInterestFetchersConfig | None = None,
) -> common_tuples.AccrualDetail:
    """Calculates fixed interest accrual amount.

    Args:
        effective_balance (Balance): The account balance
        effective_datetime (datetime): Effective datetime
        interest_rates (Decimal): The interest rate
        days_in_year (str): Days in year
        precision (int, optional): The rounding precision. Defaults to 5.
        state (state_utils.SmartContractState, optional): Smart contract state.
        fetchers_config (FlatInterestFetchersConfig, optional): Feature fetchers config.

    Returns:
        common_tuples.AccrualDetail: Accrual detail tuple containing accrual amount, and description
    """
    effective_net_credit: Decimal = balance_utils.net_credit(effective_balance)

    if effective_net_credit == Decimal("0"):
        return common_tuples.AccrualDetail(
            accrual_amount=Decimal("0"),
            description="",
        )

    daily_rate = parameter_utils.yearly_to_daily_rate(
        effective_date=effective_datetime,
        yearly_rate=interest_rates,
        days_in_year=days_in_year,
    )

    accrual_amount = utils.round_decimal(
        amount=effective_net_credit * daily_rate,
        decimal_places=int(precision),
    )

    return common_tuples.AccrualDetail(
        accrual_amount=accrual_amount,
        description=f"Daily interest accrued at {(daily_rate * 100):0.5f}%"
        f" on balance of {effective_net_credit:0.2f}",
    )


def get_accrual_payable_customer_address() -> str:
    """Returns the customer account address where payable interest is accrued.

    Returns:
        str: The customer balance address for accrued payable interest.
    """
    return deposit_addresses.ACCRUED_INTEREST_PAYABLE


def get_accrual_receivable_customer_address() -> str:
    """Returns the customer account address where receivable interest is accrued.

    Returns:
        str: The customer balance address for accrued receivable interest.
    """
    return deposit_addresses.ACCRUED_INTEREST_RECEIVABLE


def get_accrual_payable_internal_account(
    state: state_utils.SmartContractState,
) -> str:
    """Returns the internal account where payable interest is accrued.

    Args:
        state: Smart contract state.

    Returns:
        The internal account ID.
    """
    state = _append_to_state(state=state)
    return state.parameters.get(interest_accrual.ACCRUED_INTEREST_PAYABLE_ACCOUNT_PARAM_ID, "")  # type: ignore


def get_accrual_receivable_internal_account(
    state: state_utils.SmartContractState,
) -> str:
    """Returns the internal account where receivable interest is accrued.

    Args:
        state: Smart contract state.

    Returns:
        The internal account ID.
    """
    state = _append_to_state(state=state)
    return state.parameters.get(interest_accrual.ACCRUED_INTEREST_RECEIVABLE_ACCOUNT_PARAM_ID, "")  # type: ignore


InterestType = deposit_interfaces.InterestType(
    get_interest_rate=get_interest_rate,
    get_accrual_amount=get_fixed_interest_accrual_amount,
    get_accrual_payable_customer_address=get_accrual_payable_customer_address,
    get_accrual_receivable_customer_address=get_accrual_receivable_customer_address,
    get_accrual_payable_internal_account=get_accrual_payable_internal_account,
    get_accrual_receivable_internal_account=get_accrual_receivable_internal_account,
)
