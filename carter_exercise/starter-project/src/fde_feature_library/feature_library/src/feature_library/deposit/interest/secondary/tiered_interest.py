"""Tiered interest rate feature module for deposit accounts.

Calculates and retrieves tiered interest rates and accrual amounts based on balance thresholds.
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
from json import loads
from typing import NamedTuple

# feature library
import feature_library.common.balance_utils as balance_utils
import feature_library.common.denomination as denomination
import feature_library.common.parameter_utils as parameter_utils
import feature_library.common.state_utils as state_utils
import feature_library.common.tuples as common_tuples
import feature_library.common.utils as utils
import feature_library.deposit.addresses as deposit_addresses
import feature_library.deposit.interest.deposit_interest_accrual_utils as deposit_interest_accrual_utils  # noqa
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
TIERED_INTEREST_RATES_PARAM_ID = "&{tiered_interest_rates}"
TIERED_INTEREST_RATES_PARAM = ExpectedParameter(
    id=TIERED_INTEREST_RATES_PARAM_ID,
    triggers_pre_parameter_change_hook=False,
    triggers_post_parameter_change_hook=False,
)

# Data Fetchers
TIERED_INTEREST_RATE_ET_POF_ID = "tiered_interest_rate_et_pof"
TIERED_INTEREST_RATE_ET_POF = ParametersObservationFetcher(
    fetcher_id=TIERED_INTEREST_RATE_ET_POF_ID,
    at=DefinedDateTime.EFFECTIVE_DATETIME,
    filter=ParametersFilter(parameter_ids=[TIERED_INTEREST_RATES_PARAM_ID]),
)

expected_parameters = [
    TIERED_INTEREST_RATES_PARAM,
]

data_fetchers = [
    TIERED_INTEREST_RATE_ET_POF,
]

TieredInterestFetchersConfig = NamedTuple(
    "TieredInterestFetchersConfig",
    [
        ("param_fetcher_id", str),
        ("tiered_interest_param_id", str),
    ],
)

DEFAULT_TIERED_INTEREST_FETCHERS_CONFIG = TieredInterestFetchersConfig(
    param_fetcher_id=TIERED_INTEREST_RATE_ET_POF_ID,
    tiered_interest_param_id=TIERED_INTEREST_RATES_PARAM_ID,
)


def get_parameters(
    vault: SmartContractVault, param_fetcher_id: str = TIERED_INTEREST_RATE_ET_POF_ID
) -> dict[str, datetime | Decimal | str | None]:
    """Get required parameters for tiered interest from fetcher.

    Args:
        vault (SmartContractVault): The SmartContractVault instance to query.
        param_fetcher_id (str): The unique identifier for the parameter fetcher.
            Defaults to TIERED_INTEREST_RATE_ET_POF_ID.

    Returns:
        dict[str, datetime | Decimal | str | None]: Dictionary mapping parameter ids to values
    """

    return vault.get_parameters_observation(fetcher_id=param_fetcher_id).parameters


def convert_tiered_interest_param_to_json(param_value: str) -> dict[str, str]:
    """Converts a tiered interest parameter string into a JSON dictionary.

    Args:
        param_value (str): The tiered interest parameter value as a JSON string.

    Returns:
        dict[str, str]: The parsed tiered interest parameters.
    """

    parameter = loads(param_value)

    return parameter


def _append_to_state(
    state: state_utils.SmartContractState,
    param_fetcher_id: str = TIERED_INTEREST_RATE_ET_POF_ID,
) -> state_utils.SmartContractState:
    """Function used to add tiered interest parameters to state object.

    Args:
        state (state_utils.SmartContractState): Smart contract state
        param_fetcher_id (str, optional): The fetcher id for the required tiered interest
            parameters. Defaults to TIERED_INTEREST_RATE_ET_POF_ID.

    Returns:
        state_utils.SmartContractState: Updated Smart Contract state
    """
    return state_utils.append_to_state(
        state=state,
        parameters=get_parameters(state.vault, param_fetcher_id),
    )


def get_interest_rates(
    state: state_utils.SmartContractState,
    fetchers_config: TieredInterestFetchersConfig | None = None,
) -> common_tuples.InterestRateTuple:
    """Get interest rates from state.

    Args:
        state (state_utils.SmartContractState): Smart Contract state
        fetchers_config (TieredInterestFetchersConfig, optional): Fetchers configuration.
            Defaults to DEFAULT_TIERED_INTEREST_FETCHERS_CONFIG.

    Returns:
        common_tuples.InterestRateTuple: Interest rate tuple containing interest rate.
    """

    fetchers_config = fetchers_config or DEFAULT_TIERED_INTEREST_FETCHERS_CONFIG

    state = _append_to_state(
        state=state,
        param_fetcher_id=fetchers_config.param_fetcher_id,
    )

    rejection = state_utils.check_parameters_exist(
        state=state,
        param_ids={fetchers_config.tiered_interest_param_id},
    )
    assert rejection is None, rejection

    tiered_rates: str = state.parameters.get(fetchers_config.tiered_interest_param_id)  # type: ignore

    return common_tuples.InterestRateTuple(
        interest_rate_param_value=tiered_rates,
        interest_type=common_tuples.INTEREST_TYPE_TIERED,
    )


def get_tiered_accrual_amount(
    *,
    effective_balance: Balance,
    effective_datetime: datetime,
    interest_rates: str,
    days_in_year: str,
    precision: int = 5,
    state: state_utils.SmartContractState | None = None,
    fetchers_config: TieredInterestFetchersConfig | None = None,
) -> common_tuples.AccrualDetail:
    """Calculate tiered interest accrual.

    Function converts string param value to dict and orders tiered rates based on balance
    thresholds.  If balance is lower than lowest tier no interest is accrued.

    Args:
        effective_balance (Balance): The account balance
        effective_datetime (datetime): Effective datetime
        interest_rates (str): Tiered interest rates param value
        days_in_year (str): Days in year
        precision (int, optional): The rounding precision. Defaults to 5.
        state (state_utils.SmartContractState, optional): Smart contract state.
        fetchers_config (TieredInterestFetchersConfig, optional): Feature fetchers config.

    Returns:
        common_tuples.AccrualDetail: The calculated accrual amount and details.
    """
    effective_net_credit: Decimal = balance_utils.net_credit(effective_balance)
    # Guard against handling debit/overdraft interest here.
    if not effective_net_credit > 0:
        return common_tuples.AccrualDetail(accrual_amount=Decimal(0), description="")

    tiered_interest_rates: dict[str, str] = loads(interest_rates)

    # Transform tiered_interest_rates dict into a sorted list of numeric (threshold, rate) tuples.
    # Sorting by Decimal threshold ensures tiers are processed in correct numeric order.
    sorted_tiers = sorted(
        (Decimal(threshold), Decimal(rate)) for threshold, rate in tiered_interest_rates.items()
    )

    # Return zero if balance hasn't reached the minimum tier.
    if not sorted_tiers or effective_net_credit < sorted_tiers[0][0]:
        return common_tuples.AccrualDetail(accrual_amount=Decimal(0), description="")

    def process_tier(idx: int) -> tuple[Decimal, str]:
        """Calculate interest for portion of balance within the balance threshold."""
        low_threshold, rate = sorted_tiers[idx]
        high_threshold = sorted_tiers[idx + 1][0] if (idx + 1) < len(sorted_tiers) else None

        # Determine the portion of the balance that falls within the range
        # [low_threshold, high_threshold].
        upper_bound = (
            min(effective_net_credit, high_threshold)
            if high_threshold is not None
            else effective_net_credit
        )
        amount_in_tier = max(Decimal("0"), upper_bound - low_threshold)

        if amount_in_tier == 0:
            return Decimal("0"), ""

        daily_rate = parameter_utils.yearly_to_daily_rate(
            effective_date=effective_datetime,
            yearly_rate=rate,
            days_in_year=days_in_year,
        )

        return (
            amount_in_tier * daily_rate,
            f"Accrual on {amount_in_tier:.2f} at annual rate of {rate * 100:.2f}%.",
        )

    # Transform each tier index into an (amount, description) tuple.
    tier_results: list[tuple[Decimal, str]] = [process_tier(i) for i in range(len(sorted_tiers))]

    # Sum the amounts and join non-empty descriptions.
    total_accrual: Decimal = sum(amt for amt, _ in tier_results)  # type: ignore
    combined_details: str = " ".join(desc for _, desc in tier_results if desc)

    accrual_amount = utils.round_decimal(amount=total_accrual, decimal_places=precision)

    return common_tuples.AccrualDetail(
        accrual_amount=accrual_amount,
        description=combined_details,
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
    get_interest_rate=get_interest_rates,
    get_accrual_amount=get_tiered_accrual_amount,
    get_accrual_payable_customer_address=get_accrual_payable_customer_address,
    get_accrual_receivable_customer_address=get_accrual_receivable_customer_address,
    get_accrual_payable_internal_account=get_accrual_payable_internal_account,
    get_accrual_receivable_internal_account=get_accrual_receivable_internal_account,
)
