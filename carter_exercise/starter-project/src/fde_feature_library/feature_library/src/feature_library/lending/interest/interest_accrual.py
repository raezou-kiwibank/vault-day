"""Interest accrual feature."""

__smart_contract_feature__ = True

# standard libs
from decimal import ROUND_HALF_UP, Decimal
from typing import Callable, NamedTuple
from zoneinfo import ZoneInfo

# features
import feature_library.common.accrual_utils as accrual_utils
import feature_library.common.balance_utils as balance_utils
import feature_library.common.date_and_time as date_and_time
import feature_library.common.denomination as denomination_module
import feature_library.common.parameter_utils as parameter_utils
import feature_library.common.posting_utils as posting_utils
import feature_library.common.state_utils as state_utils
import feature_library.common.utils as utils
import feature_library.lending.addresses as lending_addresses
import feature_library.lending.fetchers as lending_fetchers

# contracts api
from contracts_api import (
    BalanceDefaultDict,
    CustomInstruction,
    DefinedDateTime,
    ExpectedParameter,
    ParametersFilter,
    ParametersObservationFetcher,
    ScheduledEvent,
    ScheduleExpression,
    SmartContractEventType,
)

UTC = ZoneInfo("UTC")

# Events
ACCRUAL_EVENT = "ACCRUE_INTEREST"


# Parameter IDs
ACCRUED_INTEREST_RECEIVABLE_ACCOUNT_PARAM_ID = "&{accrued_interest_receivable_account}"
ACCRUED_INTEREST_RECEIVABLE_ACCOUNT_PARAM = ExpectedParameter(
    id=ACCRUED_INTEREST_RECEIVABLE_ACCOUNT_PARAM_ID,
    triggers_pre_parameter_change_hook=False,
    triggers_post_parameter_change_hook=False,
)
DAYS_IN_YEAR_PARAM_ID = "&{days_in_year}"
DAYS_IN_YEAR_PARAM = ExpectedParameter(
    id=DAYS_IN_YEAR_PARAM_ID,
    triggers_pre_parameter_change_hook=False,
    triggers_post_parameter_change_hook=False,
)
ACCRUAL_PRECISION_PARAM_ID = "&{accrual_precision}"
ACCRUAL_PRECISION_PARAM = ExpectedParameter(
    id=ACCRUAL_PRECISION_PARAM_ID,
    triggers_pre_parameter_change_hook=False,
    triggers_post_parameter_change_hook=False,
)
ACCRUAL_TIME_PARAM_ID = "&{interest_accrual_time}"
ACCRUAL_TIME_PARAM = ExpectedParameter(
    id=ACCRUAL_TIME_PARAM_ID,
    triggers_pre_parameter_change_hook=False,
    triggers_post_parameter_change_hook=False,
)

expected_parameters = [
    ACCRUED_INTEREST_RECEIVABLE_ACCOUNT_PARAM,
    DAYS_IN_YEAR_PARAM,
    ACCRUAL_PRECISION_PARAM,
    ACCRUAL_TIME_PARAM,
    denomination_module.DENOMINATION_PARAM,
]

# Fetchers
PARAM_ET_POF_ID = "interest_accrual_params_et_pof"
PARAM_ET_POF = ParametersObservationFetcher(
    fetcher_id=PARAM_ET_POF_ID,
    at=DefinedDateTime.EFFECTIVE_DATETIME,
    filter=ParametersFilter(parameter_ids=[p.id for p in expected_parameters]),
)

data_fetchers = [
    PARAM_ET_POF,
]

event_types = [
    SmartContractEventType(name=ACCRUAL_EVENT),
]

# Fetchers Config
InterestAccrualFetchersConfig = NamedTuple(
    "InterestAccrualFetchersConfig",
    [
        ("param_fetcher_id", str),
        ("balance_fetcher_id", str),
        ("denomination_param_id", str),
        ("days_in_year_param_id", str),
        ("accrual_precision_param_id", str),
        ("accrued_receivable_account_param_id", str),
        ("interest_accrual_time_param_id", str),
    ],
)

DEFAULT_FETCHERS_CONFIG = InterestAccrualFetchersConfig(
    param_fetcher_id=PARAM_ET_POF_ID,
    balance_fetcher_id=lending_fetchers.PRINCIPAL_ET_BOF_ID,
    denomination_param_id=denomination_module.DENOMINATION_PARAM_ID,
    days_in_year_param_id=DAYS_IN_YEAR_PARAM_ID,
    accrual_precision_param_id=ACCRUAL_PRECISION_PARAM_ID,
    accrued_receivable_account_param_id=ACCRUED_INTEREST_RECEIVABLE_ACCOUNT_PARAM_ID,
    interest_accrual_time_param_id=ACCRUAL_TIME_PARAM_ID,
)

GetScheduledEventsFetchersConfig = NamedTuple(
    "GetScheduledEventsFetchersConfig",
    [
        ("param_fetcher_id", str),
        ("interest_accrual_time_param_id", str),
    ],
)

DEFAULT_GET_SCHEDULED_EVENTS_FETCHERS_CONFIG = GetScheduledEventsFetchersConfig(
    param_fetcher_id=PARAM_ET_POF_ID,
    interest_accrual_time_param_id=ACCRUAL_TIME_PARAM_ID,
)


def _append_to_state(
    state: state_utils.SmartContractState,
    fetchers_config: InterestAccrualFetchersConfig = DEFAULT_FETCHERS_CONFIG,
) -> state_utils.SmartContractState:
    """Append interest accrual parameters to state.

    Args:
        state (state_utils.SmartContractState): Smart Contract State
        fetchers_config (InterestAccrualFetchersConfig, optional): Fetchers configuration.
            Defaults to DEFAULT_FETCHERS_CONFIG.

    Returns:
        state_utils.SmartContractState: The updated state object.
    """
    parameters = state.vault.get_parameters_observation(
        fetcher_id=fetchers_config.param_fetcher_id
    ).parameters

    balances = (
        state.vault.get_balances_observation(fetcher_id=fetchers_config.balance_fetcher_id).balances
        if fetchers_config.balance_fetcher_id
        else None
    )

    return state_utils.append_to_state(
        state=state,
        parameters=parameters,
        balances=balances,
    )


def get_scheduled_events(
    state: state_utils.SmartContractState,
    fetchers_config: GetScheduledEventsFetchersConfig = DEFAULT_GET_SCHEDULED_EVENTS_FETCHERS_CONFIG,
) -> dict[str, ScheduledEvent]:
    """Get scheduled event for interest accrual.

    Uses interest accrual time parameter.
        state (state_utils.SmartContractState): Smart Contract state
        fetchers_config (GetScheduledEventsFetchersConfig, optional): Fetchers configuration.
            Defaults to DEFAULT_GET_SCHEDULED_EVENTS_FETCHERS_CONFIG.

    Returns:
        dict[str, ScheduledEvent]: Interest accrual scheduled event.
    """
    parameters = state.vault.get_parameters_observation(
        fetcher_id=fetchers_config.param_fetcher_id
    ).parameters

    state = state_utils.append_to_state(
        state=state,
        parameters=parameters,
    )

    rejection = state_utils.check_parameters_exist(
        state=state, param_ids={fetchers_config.interest_accrual_time_param_id}
    )
    assert rejection is None, rejection

    accrual_time_str: str = state.parameters.get(fetchers_config.interest_accrual_time_param_id)  # type: ignore
    accrual_time: date_and_time.Time = date_and_time.parse_time_str(accrual_time_str)

    return {
        ACCRUAL_EVENT: ScheduledEvent(
            start_datetime=state.effective_datetime.astimezone(state.vault.events_timezone),
            expression=ScheduleExpression(
                hour=accrual_time.hour,
                minute=accrual_time.minute,
                second=accrual_time.second,
            ),
        )
    }


def schedule_logic(
    state: state_utils.SmartContractState,
    get_annual_interest_rate: Callable[..., Decimal],
    account_type: str,
    principal_addresses: list[str] | None = None,
    customer_accrual_address: str | None = None,
    fetchers_config: InterestAccrualFetchersConfig = DEFAULT_FETCHERS_CONFIG,
    event: str = ACCRUAL_EVENT,
) -> list[CustomInstruction]:
    """Schedule logic for handling interest accrual.

    Retrieve required parameters, calculate accrued interest for provided interest
    features and create custom instructions.

    Args:
        state (state_utils.SmartContractState): Smart Contract State
        get_annual_interest_rate (Callable): Callback to get the annual interest rate.
        account_type (str): the account type for GL purposes
        principal_addresses (list[str] | None, optional): Addresses to accrue on. Defaults to None.
        customer_accrual_address (str | None, optional): Accrual address. Defaults to None.
        fetchers_config (InterestAccrualFetchersConfig, optional): Fetchers configuration.
            Defaults to DEFAULT_FETCHERS_CONFIG.
        event (str, optional): The name of the event. Defaults to ACCRUAL_EVENT.
    """
    state = _append_to_state(state=state, fetchers_config=fetchers_config)

    rejection = state_utils.check_parameters_exist(
        state=state,
        param_ids={
            fetchers_config.denomination_param_id,
            fetchers_config.days_in_year_param_id,
            fetchers_config.accrual_precision_param_id,
            fetchers_config.accrued_receivable_account_param_id,
        },
    )
    assert rejection is None, rejection

    params = state.parameters

    denomination: str = params.get(fetchers_config.denomination_param_id)  # type: ignore
    days_in_year: str = params.get(fetchers_config.days_in_year_param_id)  # type: ignore
    precision: int = int(params.get(fetchers_config.accrual_precision_param_id))  # type: ignore
    receivable_account: str = params.get(fetchers_config.accrued_receivable_account_param_id)  # type: ignore
    balances: BalanceDefaultDict = state.vault.get_balances_observation(
        fetcher_id=fetchers_config.balance_fetcher_id
    ).balances

    principal_addresses = principal_addresses or [lending_addresses.PRINCIPAL]

    effective_balance: Decimal = balance_utils.net_debit(
        balance_utils.sum_balances(
            balances=balances,
            denomination=denomination,
            addresses=principal_addresses,
        )
    )

    annual_rate: Decimal = get_annual_interest_rate(state=state)
    daily_rate: Decimal = parameter_utils.yearly_to_daily_rate(
        effective_date=state.effective_datetime,
        yearly_rate=annual_rate,
        days_in_year=days_in_year,
    )

    accrual_amount: Decimal = utils.round_decimal(
        amount=effective_balance * daily_rate,
        decimal_places=precision,
        rounding=ROUND_HALF_UP,
    )

    return accrual_utils.create_receivable_accrual_custom_instruction(
        customer_account=state.vault.account_id,
        customer_address=customer_accrual_address or lending_addresses.ACCRUED_INTEREST_RECEIVABLE,
        denomination=denomination,
        amount=accrual_amount,
        internal_account=receivable_account,
        instruction_details=posting_utils.standard_instruction_details(
            description=f"Daily interest accrued at {(daily_rate * 100):0.5f}%"
            f" on balance of {effective_balance:0.2f}",
            event_type=event,
            gl_impacted=True,
            account_type=account_type,
        ),
    )
