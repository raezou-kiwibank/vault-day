# Copyright @ 2026 Thought Machine Group Limited. All rights reserved.
__smart_contract_feature__ = True

# standard libs
from datetime import datetime
from decimal import Decimal
from typing import Mapping, NamedTuple
from zoneinfo import ZoneInfo

from dateutil.relativedelta import relativedelta

import feature_library.common.addresses as common_addresses

# feature library
import feature_library.common.balance_utils as balance_utils
import feature_library.common.date_and_time as date_and_time
import feature_library.common.denomination as denomination_module
import feature_library.common.fees as fees
import feature_library.common.posting_utils as posting_utils
import feature_library.common.state_utils as state_utils
import feature_library.common.utils as utils
import feature_library.lending.addresses as lending_addresses
import feature_library.lending.interfaces as lending_interfaces
import feature_library.lending.repayments.overpayment as overpayment

# contracts api
from contracts_api import (
    DEFAULT_ASSET,
    Attribute,
    AttributeDecimalType,
    BalanceCoordinate,
    BalanceDefaultDict,
    BalancesFilter,
    BalancesIntervalFetcher,
    BalancesObservationFetcher,
    BalanceTimeseries,
    CustomInstruction,
    DefinedDateTime,
    EventTypesFilter,
    ExpectedParameter,
    LastScheduledEventDateTimesObservationFetcher,
    Override,
    ParametersFilter,
    ParametersIntervalFetcher,
    ParametersObservationFetcher,
    ParameterValueTimeseries,
    Phase,
    Posting,
    Rejection,
    RejectionReason,
    RelativeDateTime,
    ScheduledEvent,
    ScheduleExpression,
    ScheduleSkip,
    Shift,
    SmartContractEventType,
)

# inception sdk
from inception_sdk.vault.contracts.extensions.contracts_api_extensions import SmartContractVault

UTC = ZoneInfo("UTC")

# feature addresses
REMAINING_OVERPAYMENT_ALLOWANCE_TRACKER = "REMAINING_OVERPAYMENT_ALLOWANCE_TRACKER"

# events
CHECK_OVERPAYMENT_ALLOWANCE_EVENT = "CHECK_OVERPAYMENT_ALLOWANCE"

# expected parameters
OVERPAYMENT_ALLOWANCE_PERCENTAGE_PARAM_ID = "&{overpayment_allowance_percentage}"
OVERPAYMENT_ALLOWANCE_PERCENTAGE_PARAM = ExpectedParameter(
    id=OVERPAYMENT_ALLOWANCE_PERCENTAGE_PARAM_ID,
    triggers_pre_parameter_change_hook=False,
    triggers_post_parameter_change_hook=False,
)

OVERPAYMENT_ALLOWANCE_FEE_PERCENTAGE_PARAM_ID = "&{overpayment_allowance_fee_percentage}"
OVERPAYMENT_ALLOWANCE_FEE_PERCENTAGE_PARAM = ExpectedParameter(
    id=OVERPAYMENT_ALLOWANCE_FEE_PERCENTAGE_PARAM_ID,
    triggers_pre_parameter_change_hook=False,
    triggers_post_parameter_change_hook=False,
)

OVERPAYMENT_ALLOWANCE_FEE_INCOME_ACCOUNT_PARAM_ID = "&{overpayment_allowance_fee_income_account}"
OVERPAYMENT_ALLOWANCE_FEE_INCOME_ACCOUNT_PARAM = ExpectedParameter(
    id=OVERPAYMENT_ALLOWANCE_FEE_INCOME_ACCOUNT_PARAM_ID,
    triggers_pre_parameter_change_hook=False,
    triggers_post_parameter_change_hook=False,
)

CHECK_OVERPAYMENT_ALLOWANCE_TIME_PARAM_ID = "&{check_overpayment_allowance_time}"
CHECK_OVERPAYMENT_ALLOWANCE_TIME_PARAM = ExpectedParameter(
    id=CHECK_OVERPAYMENT_ALLOWANCE_TIME_PARAM_ID,
    triggers_pre_parameter_change_hook=False,
    triggers_post_parameter_change_hook=False,
)

expected_parameters = [
    OVERPAYMENT_ALLOWANCE_PERCENTAGE_PARAM,
    OVERPAYMENT_ALLOWANCE_FEE_PERCENTAGE_PARAM,
    OVERPAYMENT_ALLOWANCE_FEE_INCOME_ACCOUNT_PARAM,
    CHECK_OVERPAYMENT_ALLOWANCE_TIME_PARAM,
    denomination_module.DENOMINATION_PARAM,
]

# fetchers
OVERPAYMENT_ALLOWANCE_PARAM_POF_ID = "OVERPAYMENT_ALLOWANCE_PARAM_POF"
OVERPAYMENT_ALLOWANCE_PARAM_POF = ParametersObservationFetcher(
    fetcher_id=OVERPAYMENT_ALLOWANCE_PARAM_POF_ID,
    at=DefinedDateTime.EFFECTIVE_DATETIME,
    filter=ParametersFilter(parameter_ids=[p.id for p in expected_parameters]),
)

ONE_YEAR_ALLOWANCE_PARAM_PIF_ID = "ONE_YEAR_ALLOWANCE_PIF"
ONE_YEAR_ALLOWANCE_PARAM_PIF = ParametersIntervalFetcher(
    fetcher_id=ONE_YEAR_ALLOWANCE_PARAM_PIF_ID,
    start=RelativeDateTime(
        origin=DefinedDateTime.EFFECTIVE_DATETIME,
        shift=Shift(years=-1),
    ),
    end=DefinedDateTime.EFFECTIVE_DATETIME,
    filter=ParametersFilter(
        parameter_ids=[
            OVERPAYMENT_ALLOWANCE_PERCENTAGE_PARAM_ID,
            OVERPAYMENT_ALLOWANCE_FEE_PERCENTAGE_PARAM_ID,
        ]
    ),
)

ONE_YEAR_OVERPAYMENT_ALLOWANCE_BOF_ID = "ONE_YEAR_OVERPAYMENT_ALLOWANCE_BOF"
ONE_YEAR_OVERPAYMENT_ALLOWANCE_BOF = BalancesObservationFetcher(
    fetcher_id=ONE_YEAR_OVERPAYMENT_ALLOWANCE_BOF_ID,
    at=RelativeDateTime(
        origin=DefinedDateTime.EFFECTIVE_DATETIME,
        shift=Shift(years=-1),
        find=Override(hour=0, minute=0, second=0),
    ),
    filter=BalancesFilter(addresses=[overpayment.OVERPAYMENT_ADDRESS, lending_addresses.PRINCIPAL]),
)

# This is for use in scenarios where we don't know when the start of the
# allowance period is (e.g. account attributes) and must compute the start
# within the hook
# ONE_YEAR_OVERPAYMENT_ALLOWANCE_BDIF_ID = "ONE_YEAR_OVERPAYMENT_ALLOWANCE_BDIF"
# ONE_YEAR_OVERPAYMENT_ALLOWANCE_BDIF = BalancesDiscreteIntervalFetcher(
#     fetcher_id=ONE_YEAR_OVERPAYMENT_ALLOWANCE_BDIF_ID,
#     start=RelativeDateTime(
#         origin=DefinedDateTime.EFFECTIVE_DATETIME,
#         shift=Shift(years=-1),
#     ),
#     end=DefinedDateTime.EFFECTIVE_DATETIME,
#     sampling_period=Period(days=1),
#     filter=BalancesFilter(
#         addresses=[overpayment.OVERPAYMENT_ADDRESS, lending_addresses.PRINCIPAL]
#     ),
# )

ONE_YEAR_OVERPAYMENT_ALLOWANCE_BIF_ID = "ONE_YEAR_OVERPAYMENT_ALLOWANCE_BIF"
ONE_YEAR_OVERPAYMENT_ALLOWANCE_BIF = BalancesIntervalFetcher(
    fetcher_id=ONE_YEAR_OVERPAYMENT_ALLOWANCE_BIF_ID,
    start=RelativeDateTime(
        origin=DefinedDateTime.EFFECTIVE_DATETIME,
        shift=Shift(years=-1),
    ),
    end=DefinedDateTime.EFFECTIVE_DATETIME,
    filter=BalancesFilter(addresses=[overpayment.OVERPAYMENT_ADDRESS, lending_addresses.PRINCIPAL]),
)


EOD_OVERPAYMENT_ALLOWANCE_BOF_ID = "EFFECTIVE_OVERPAYMENT_ALLOWANCE_BOF"
EOD_OVERPAYMENT_ALLOWANCE_BOF = BalancesObservationFetcher(
    fetcher_id=EOD_OVERPAYMENT_ALLOWANCE_BOF_ID,
    at=RelativeDateTime(
        origin=DefinedDateTime.EFFECTIVE_DATETIME,
        find=Override(hour=0, minute=0, second=0),
    ),
    filter=BalancesFilter(
        addresses=[
            REMAINING_OVERPAYMENT_ALLOWANCE_TRACKER,
            lending_addresses.PRINCIPAL,
            overpayment.OVERPAYMENT_ADDRESS,
        ]
    ),
)


OVERPAYMENT_ALLOWANCE_LAST_EXECUTION_SOF_ID = "OVERPAYMENT_ALLOWANCE_LAST_EXECUTION_SOF"
OVERPAYMENT_ALLOWANCE_LAST_EXECUTION_SOF = LastScheduledEventDateTimesObservationFetcher(
    fetcher_id=OVERPAYMENT_ALLOWANCE_LAST_EXECUTION_SOF_ID,
    filter=EventTypesFilter(
        event_types=[CHECK_OVERPAYMENT_ALLOWANCE_EVENT],
    ),
    at=DefinedDateTime.EFFECTIVE_DATETIME,
)

data_fetchers = [
    OVERPAYMENT_ALLOWANCE_PARAM_POF,
    ONE_YEAR_ALLOWANCE_PARAM_PIF,
    ONE_YEAR_OVERPAYMENT_ALLOWANCE_BOF,
    ONE_YEAR_OVERPAYMENT_ALLOWANCE_BIF,
    EOD_OVERPAYMENT_ALLOWANCE_BOF,
    OVERPAYMENT_ALLOWANCE_LAST_EXECUTION_SOF,
]

# Attributes
OVERPAYMENT_ALLOWANCE_REMAINING_ATTR_ID = "overpayment_allowance_remaining"
OVERPAYMENT_ALLOWANCE_REMAINING_ATTRIBUTE = Attribute(
    name=OVERPAYMENT_ALLOWANCE_REMAINING_ATTR_ID,
    data_type=AttributeDecimalType(),
)

OVERPAYMENT_ALLOWANCE_USED_ATTR_ID = "overpayment_allowance_used"
OVERPAYMENT_ALLOWANCE_USED_ATTRIBUTE = Attribute(
    name=OVERPAYMENT_ALLOWANCE_USED_ATTR_ID,
    data_type=AttributeDecimalType(),
)

OVERPAYMENT_ALLOWANCE_FEE_ATTR_ID = "overpayment_allowance_fee"
OVERPAYMENT_ALLOWANCE_FEE_ATTRIBUTE = Attribute(
    name=OVERPAYMENT_ALLOWANCE_FEE_ATTR_ID,
    data_type=AttributeDecimalType(),
)

attributes = [
    OVERPAYMENT_ALLOWANCE_REMAINING_ATTRIBUTE,
    OVERPAYMENT_ALLOWANCE_USED_ATTRIBUTE,
    OVERPAYMENT_ALLOWANCE_FEE_ATTRIBUTE,
]

# Types
OverpaymentAllowanceStatus = NamedTuple(
    "OverpaymentAllowanceStatus",
    [
        ("overpayment_allowance", Decimal),
        ("overpayment_allowance_used", Decimal),
    ],
)

# Fetchers configs
HandleAllowanceUsageFetchersConfig = NamedTuple(
    "HandleAllowanceUsageFetchersConfig",
    [
        ("param_fetcher_id", str),
        ("denomination_param_id", str),
        ("overpayment_allowance_percentage_param_id", str),
        ("overpayment_allowance_fee_percentage_param_id", str),
        ("overpayment_allowance_fee_income_account_param_id", str),
        ("one_year_overpayment_allowance_bof_id", str),
        ("eod_overpayment_allowance_bof_id", str),
        ("remaining_overpayment_allowance_tracker_address", str),
    ],
)

DEFAULT_HANDLE_ALLOWANCE_USAGE_FETCHERS_CONFIG = HandleAllowanceUsageFetchersConfig(
    param_fetcher_id=OVERPAYMENT_ALLOWANCE_PARAM_POF_ID,
    denomination_param_id=denomination_module.DENOMINATION_PARAM_ID,
    overpayment_allowance_percentage_param_id=OVERPAYMENT_ALLOWANCE_PERCENTAGE_PARAM_ID,
    overpayment_allowance_fee_percentage_param_id=OVERPAYMENT_ALLOWANCE_FEE_PERCENTAGE_PARAM_ID,
    overpayment_allowance_fee_income_account_param_id=OVERPAYMENT_ALLOWANCE_FEE_INCOME_ACCOUNT_PARAM_ID,
    one_year_overpayment_allowance_bof_id=ONE_YEAR_OVERPAYMENT_ALLOWANCE_BOF_ID,
    eod_overpayment_allowance_bof_id=EOD_OVERPAYMENT_ALLOWANCE_BOF_ID,
    remaining_overpayment_allowance_tracker_address=REMAINING_OVERPAYMENT_ALLOWANCE_TRACKER,
)


HandleAllowanceUsageAdhocFetchersConfig = NamedTuple(
    "HandleAllowanceUsageAdhocFetchersConfig",
    [
        ("param_fetcher_id", str),
        ("denomination_param_id", str),
        ("overpayment_allowance_percentage_param_id", str),
        ("overpayment_allowance_fee_percentage_param_id", str),
        ("overpayment_allowance_fee_income_account_param_id", str),
        ("one_year_allowance_bif_id", str),
        ("overpayment_allowance_last_execution_sof_id", str),
        ("check_overpayment_allowance_event", str),
    ],
)

DEFAULT_HANDLE_ALLOWANCE_USAGE_ADHOC_FETCHERS_CONFIG = HandleAllowanceUsageAdhocFetchersConfig(
    param_fetcher_id=OVERPAYMENT_ALLOWANCE_PARAM_POF_ID,
    denomination_param_id=denomination_module.DENOMINATION_PARAM_ID,
    overpayment_allowance_percentage_param_id=OVERPAYMENT_ALLOWANCE_PERCENTAGE_PARAM_ID,
    overpayment_allowance_fee_percentage_param_id=OVERPAYMENT_ALLOWANCE_FEE_PERCENTAGE_PARAM_ID,
    overpayment_allowance_fee_income_account_param_id=OVERPAYMENT_ALLOWANCE_FEE_INCOME_ACCOUNT_PARAM_ID,
    one_year_allowance_bif_id=ONE_YEAR_OVERPAYMENT_ALLOWANCE_BIF_ID,
    overpayment_allowance_last_execution_sof_id=OVERPAYMENT_ALLOWANCE_LAST_EXECUTION_SOF_ID,
    check_overpayment_allowance_event=CHECK_OVERPAYMENT_ALLOWANCE_EVENT,
)


ReduceOverpaymentAllowanceFetchersConfig = NamedTuple(
    "ReduceOverpaymentAllowanceFetchersConfig",
    [
        ("param_fetcher_id", str),
        ("denomination_param_id", str),
        ("remaining_overpayment_allowance_tracker_address", str),
        ("principal_address", str),
        ("internal_contra_address", str),
    ],
)

DEFAULT_REDUCE_OVERPAYMENT_ALLOWANCE_FETCHERS_CONFIG = ReduceOverpaymentAllowanceFetchersConfig(
    param_fetcher_id=OVERPAYMENT_ALLOWANCE_PARAM_POF_ID,
    denomination_param_id=denomination_module.DENOMINATION_PARAM_ID,
    remaining_overpayment_allowance_tracker_address=REMAINING_OVERPAYMENT_ALLOWANCE_TRACKER,
    principal_address=lending_addresses.PRINCIPAL,
    internal_contra_address=common_addresses.INTERNAL_CONTRA,
)


GetOverpaymentAllowanceFeeForEarlyRepaymentFetchersConfig = NamedTuple(
    "GetOverpaymentAllowanceFeeForEarlyRepaymentFetchersConfig",
    [
        ("param_fetcher_id", str),
        ("denomination_param_id", str),
        ("overpayment_allowance_fee_percentage_param_id", str),
        ("remaining_overpayment_allowance_tracker_address", str),
        ("outstanding_addresses", list[str]),
        ("repayment_hierarchy", list[str]),
    ],
)

DEFAULT_GET_OVERPAYMENT_ALLOWANCE_FEE_FOR_EARLY_REPAYMENT_FETCHERS_CONFIG = (
    GetOverpaymentAllowanceFeeForEarlyRepaymentFetchersConfig(
        param_fetcher_id=OVERPAYMENT_ALLOWANCE_PARAM_POF_ID,
        denomination_param_id=denomination_module.DENOMINATION_PARAM_ID,
        overpayment_allowance_fee_percentage_param_id=OVERPAYMENT_ALLOWANCE_FEE_PERCENTAGE_PARAM_ID,
        remaining_overpayment_allowance_tracker_address=REMAINING_OVERPAYMENT_ALLOWANCE_TRACKER,
        outstanding_addresses=lending_addresses.ALL_OUTSTANDING,
        repayment_hierarchy=lending_addresses.REPAYMENT_HIERARCHY,
    )
)


InitialiseOverpaymentAllowanceFetchersConfig = NamedTuple(
    "InitialiseOverpaymentAllowanceFetchersConfig",
    [
        ("param_fetcher_id", str),
        ("denomination_param_id", str),
        ("overpayment_allowance_percentage_param_id", str),
    ],
)

DEFAULT_INITIALISE_OVERPAYMENT_ALLOWANCE_FETCHERS_CONFIG = (
    InitialiseOverpaymentAllowanceFetchersConfig(
        param_fetcher_id=OVERPAYMENT_ALLOWANCE_PARAM_POF_ID,
        denomination_param_id=denomination_module.DENOMINATION_PARAM_ID,
        overpayment_allowance_percentage_param_id=OVERPAYMENT_ALLOWANCE_PERCENTAGE_PARAM_ID,
    )
)

GetOverpaymentAllowanceStatusFetchersConfig = NamedTuple(
    "GetOverpaymentAllowanceStatusFetchersConfig",
    [
        ("param_fetcher_id", str),
        ("denomination_param_id", str),
        ("one_year_allowance_param_pif_id", str),
        ("one_year_allowance_bif_id", str),
        ("overpayment_allowance_last_execution_sof_id", str),
        ("overpayment_allowance_percentage_param_id", str),
    ],
)

DEFAULT_GET_OVERPAYMENT_ALLOWANCE_STATUS_FETCHERS_CONFIG = (
    GetOverpaymentAllowanceStatusFetchersConfig(  # noqa: E501
        param_fetcher_id=OVERPAYMENT_ALLOWANCE_PARAM_POF_ID,
        denomination_param_id=denomination_module.DENOMINATION_PARAM_ID,
        one_year_allowance_param_pif_id=ONE_YEAR_ALLOWANCE_PARAM_PIF_ID,
        one_year_allowance_bif_id=ONE_YEAR_OVERPAYMENT_ALLOWANCE_BIF_ID,
        overpayment_allowance_last_execution_sof_id=OVERPAYMENT_ALLOWANCE_LAST_EXECUTION_SOF_ID,
        overpayment_allowance_percentage_param_id=OVERPAYMENT_ALLOWANCE_PERCENTAGE_PARAM_ID,
    )
)

ScheduledEventsFetchersConfig = NamedTuple(
    "ScheduledEventsFetchersConfig",
    [
        ("param_fetcher_id", str),
        ("allowance_time_param_id", str),
        ("denomination_param_id", str),
        ("overpayment_allowance_percentage_param_id", str),
    ],
)

DEFAULT_SCHEDULED_EVENTS_FETCHERS_CONFIG = ScheduledEventsFetchersConfig(
    param_fetcher_id=OVERPAYMENT_ALLOWANCE_PARAM_POF_ID,
    allowance_time_param_id=CHECK_OVERPAYMENT_ALLOWANCE_TIME_PARAM_ID,
    denomination_param_id=denomination_module.DENOMINATION_PARAM_ID,
    overpayment_allowance_percentage_param_id=OVERPAYMENT_ALLOWANCE_FEE_PERCENTAGE_PARAM_ID,
)

FetcherConfigAlias = (
    HandleAllowanceUsageFetchersConfig
    | HandleAllowanceUsageAdhocFetchersConfig
    | ReduceOverpaymentAllowanceFetchersConfig
    | GetOverpaymentAllowanceFeeForEarlyRepaymentFetchersConfig
    | InitialiseOverpaymentAllowanceFetchersConfig
    | GetOverpaymentAllowanceStatusFetchersConfig
    | ScheduledEventsFetchersConfig
)


def get_parameters(
    vault: SmartContractVault, param_fetcher_id: str = OVERPAYMENT_ALLOWANCE_PARAM_POF_ID
) -> dict[str, str | Decimal | datetime | None]:
    """Retrieves configuration parameters for the overpayment feature from the vault.

    Args:
        vault: The vault object containing the parameter observations.
        param_fetcher_id: The ID of the fetcher used to retrieve the overpayment parameters.
            Defaults to `OVERPAYMENT_PARAMS_POF_ID`.

    Returns:
        dict[str, str | Decimal | datetime | None]: A dictionary of parameter values keyed by their
        ID.
    """
    return vault.get_parameters_observation(fetcher_id=param_fetcher_id).parameters


def _append_to_state(
    state: state_utils.SmartContractState,
    fetchers_config: FetcherConfigAlias,
) -> state_utils.SmartContractState:
    """Appends late repayment specific parameters to the provided smart contract state.

    Args:
        state: The current state of the smart contract to be augmented.
        fetchers_config: Configuration for the late repayment fetchers, defining which
            parameter IDs to retrieve.

    Returns:
        state_utils.SmartContractState: A new state object containing the original state
            plus the retrieved late repayment parameters.
    """
    return state_utils.append_to_state(
        state=state,
        parameters=get_parameters(state.vault, fetchers_config.param_fetcher_id),
    )


def event_types(account_type: str) -> list[SmartContractEventType]:
    """Return the event types for the overpayment allowance schedule.

    Args:
        account_type: The account type prefix.

    Returns:
        List of SmartContractEventTypes.
    """
    return [
        SmartContractEventType(
            name=CHECK_OVERPAYMENT_ALLOWANCE_EVENT,
            scheduler_tag_ids=[f"{account_type.upper()}_{CHECK_OVERPAYMENT_ALLOWANCE_EVENT}_AST"],
        )
    ]


def scheduled_events(
    state: state_utils.SmartContractState,
    allowance_period_start_datetime: datetime,
    fetchers_config: ScheduledEventsFetchersConfig = DEFAULT_SCHEDULED_EVENTS_FETCHERS_CONFIG,
) -> dict[str, ScheduledEvent]:
    """Create scheduled event to check the overpayment allowance on account opening anniversary.

    Args:
        state: The smart contract state.
        allowance_period_start_datetime: The datetime on which the yearly allowance starts.
            The time components are ignored. The schedule will run one year from this.
        fetchers_config: Configuration for the fetchers.

    Returns:
        Schedule events for the yearly overpayment allowance check.
    """
    state = _append_to_state(state=state, fetchers_config=fetchers_config)
    rejection = state_utils.check_parameters_exist(
        state=state,
        param_ids={
            fetchers_config.allowance_time_param_id,
        },
    )
    assert rejection is None, rejection

    time_param: str = state.parameters[fetchers_config.allowance_time_param_id]  # type: ignore
    schedule_time: date_and_time.Time = date_and_time.parse_time_str(time_str=time_param)

    one_year_from_period_start = allowance_period_start_datetime.replace(
        hour=0, minute=0, second=0, microsecond=0
    ) + relativedelta(years=1)

    hour: int = schedule_time.hour
    minute: int = schedule_time.minute
    second: int = schedule_time.second

    schedule_datetime = one_year_from_period_start.replace(hour=hour, minute=minute, second=second)

    return {
        CHECK_OVERPAYMENT_ALLOWANCE_EVENT: ScheduledEvent(
            # start_datetime is exclusive, so offset by 1s to support running at midnight exactly
            start_datetime=one_year_from_period_start - relativedelta(seconds=1),
            expression=ScheduleExpression(
                year=None,
                month=str(schedule_datetime.month),
                day=str(schedule_datetime.day),
                hour=str(schedule_datetime.hour),
                minute=str(schedule_datetime.minute),
                second=str(schedule_datetime.second),
            ),
        )
    }


def update_scheduled_event(
    state: state_utils.SmartContractState,
    effective_datetime: datetime,
    fetchers_config: ScheduledEventsFetchersConfig = DEFAULT_SCHEDULED_EVENTS_FETCHERS_CONFIG,
) -> dict[str, ScheduledEvent]:
    """Re-anchor the schedule event to check the overpayment allowance.

     This happens on the anniversary of the effective datetime.  It must only be used in the
     conversion hook as start_datetime is omitted.

    Args:
        state: The smart contract state.
        effective_datetime: The datetime on which the yearly allowance is anchored on.
            The time components are ignored. The schedule will run one year from this.
        fetchers_config: Configuration for the fetchers.

    Returns:
        Schedule events for the yearly overpayment allowance check.
    """

    state = _append_to_state(state=state, fetchers_config=fetchers_config)
    rejection = state_utils.check_parameters_exist(
        state=state,
        param_ids={
            fetchers_config.allowance_time_param_id,
        },
    )
    assert rejection is None, rejection

    time_param: str = state.parameters[fetchers_config.allowance_time_param_id]  # type: ignore
    schedule_time: date_and_time.Time = date_and_time.parse_time_str(time_str=time_param)

    one_year_from_effective_datetime = effective_datetime.astimezone(
        state.vault.events_timezone
    ) + relativedelta(years=1, hour=0, minute=0, second=0, microsecond=0)

    hour: int = schedule_time.hour
    minute: int = schedule_time.minute
    second: int = schedule_time.second

    schedule_datetime = one_year_from_effective_datetime.replace(
        hour=hour, minute=minute, second=second
    )

    return {
        CHECK_OVERPAYMENT_ALLOWANCE_EVENT: ScheduledEvent(
            expression=ScheduleExpression(
                year=None,
                month=str(schedule_datetime.month),
                day=str(schedule_datetime.day),
                hour=str(schedule_datetime.hour),
                minute=str(schedule_datetime.minute),
                second=str(schedule_datetime.second),
            ),
            # as we can't update the start datetime of the event we must skip until just before we
            # expect it to run again
            skip=ScheduleSkip(end=one_year_from_effective_datetime + relativedelta(seconds=-1)),
        )
    }


def get_allowance_for_period(
    start_of_period_balances: BalanceDefaultDict,
    allowance_percentage: Decimal,
    denomination: str,
    principal_address: str = lending_addresses.PRINCIPAL,
) -> Decimal:
    """Determine the allowance for the period.

    Args:
        start_of_period_balances: Balances at start of the allowance period.
        allowance_percentage: Percentage of principal at start of allowance period that can be
            overpaid.
        denomination: Denomination of the account.
        principal_address: Address to use for the principal. Defaults to lending_addresses.PRINCIPAL

    Returns:
        The allowance for the period.
    """
    return get_allowance(
        principal=balance_utils.balance_at_coordinates(
            balances=start_of_period_balances,
            address=principal_address,
            denomination=denomination,
        ),
        allowance_percentage=allowance_percentage,
    )


def get_allowance(principal: Decimal, allowance_percentage: Decimal) -> Decimal:
    """Determine the allowance for a given principal.

    Args:
        principal: The principal to use in the allowance calculation.
        allowance_percentage: The percentage of principal included in the allowance.

    Returns:
        The allowance for the period.
    """
    return utils.round_decimal(
        amount=allowance_percentage * principal,
        decimal_places=2,
    )


def get_allowance_usage(
    start_of_period_balances: BalanceDefaultDict,
    end_of_period_balances: BalanceDefaultDict,
    denomination: str,
    overpayment_address: str = overpayment.OVERPAYMENT_ADDRESS,
) -> Decimal:
    """Determine the allowance usage over the allowance period.

    Args:
        start_of_period_balances: Balances at start of the allowance period.
        end_of_period_balances: Balances at end of the allowance period.
        denomination: Denomination of the account.
        overpayment_address: Address to use for the overpayment. Defaults to
            overpayment.OVERPAYMENT_ADDRESS.

    Returns:
        The allowance usage over the allowance period.
    """
    end_of_period_overpayment_bal: Decimal = balance_utils.net_debit(
        bal=balance_utils.get_current_net_balance(
            balances=end_of_period_balances,
            denomination=denomination,
            address=overpayment_address,
            phase=Phase.COMMITTED,
        )
    )

    start_of_period_overpayment_bal: Decimal = balance_utils.net_debit(
        bal=balance_utils.get_current_net_balance(
            balances=start_of_period_balances,
            denomination=denomination,
            address=overpayment_address,
            phase=Phase.COMMITTED,
        )
    )

    used_allowance = end_of_period_overpayment_bal - start_of_period_overpayment_bal

    # it's theoretically possible for the net OVERPAYMENT balance to have decreased
    used_allowance = max(used_allowance, Decimal(0))

    return used_allowance


def get_allowance_usage_fee(
    allowance: Decimal, used_allowance: Decimal, overpayment_allowance_fee_percentage: Decimal
) -> Decimal:
    """Determine the fee amount to charge.

    Args:
        allowance: The allowance for the period.
        used_allowance: The used allowance for the period.
        overpayment_allowance_fee_percentage: The percentage of excess used allowance to charge.

    Returns:
        The fee amount, which can be 0.
    """
    if used_allowance <= allowance:
        return Decimal(0)

    return utils.round_decimal(
        overpayment_allowance_fee_percentage * (used_allowance - allowance), decimal_places=2
    )


def handle_allowance_usage(
    state: state_utils.SmartContractState,
    account_type: str,
    fetchers_config: HandleAllowanceUsageFetchersConfig = (
        DEFAULT_HANDLE_ALLOWANCE_USAGE_FETCHERS_CONFIG
    ),
) -> list[CustomInstruction]:
    """Check the overpayments in the past year and charges a fee if the total exceeds the allowance.

    For use inside the annual schedule when the start of allowance is at
    a fixed delta from the effective date.

    Args:
        state: The smart contract state.
        account_type: The account's type, used for posting metadata purposes.
        fetchers_config: The fetchers configuration.

    Returns:
        CustomInstructions for any required fees.
    """

    state = _append_to_state(state=state, fetchers_config=fetchers_config)

    rejection = state_utils.check_parameters_exist(
        state=state,
        param_ids={
            fetchers_config.denomination_param_id,
            fetchers_config.overpayment_allowance_percentage_param_id,
            fetchers_config.overpayment_allowance_fee_percentage_param_id,
            fetchers_config.overpayment_allowance_fee_income_account_param_id,
        },
    )
    assert rejection is None, rejection

    custom_instructions: list[CustomInstruction] = []
    denomination: str = state.parameters[fetchers_config.denomination_param_id]  # type: ignore
    overpayment_percentage: Decimal = state.parameters[
        fetchers_config.overpayment_allowance_percentage_param_id
    ]  # type: ignore
    overpayment_allowance_fee_percentage: Decimal = state.parameters[
        fetchers_config.overpayment_allowance_fee_percentage_param_id
    ]  # type: ignore
    overpayment_allowance_fee_income_account: str = state.parameters[
        fetchers_config.overpayment_allowance_fee_income_account_param_id
    ]  # type: ignore

    start_of_period_balances = state.vault.get_balances_observation(
        fetcher_id=fetchers_config.one_year_overpayment_allowance_bof_id
    ).balances

    end_of_period_balances = state.vault.get_balances_observation(
        fetcher_id=fetchers_config.eod_overpayment_allowance_bof_id
    ).balances

    # the overpayment allowance tracker balance needs to be
    # updated with the new overpayment allowance amount every
    # time the overpayment allowance check schedule runs
    # since the tracker is tracking the allowance of the period that is
    # about to start, get_allowance_for_period needs the balances for the
    # upcoming period, i.e. the end_of_period_balances
    current_overpayment_allowance = balance_utils.balance_at_coordinates(
        balances=end_of_period_balances,
        address=fetchers_config.remaining_overpayment_allowance_tracker_address,
        denomination=denomination,
    )

    updated_overpayment_allowance = get_allowance_for_period(
        start_of_period_balances=end_of_period_balances,
        allowance_percentage=overpayment_percentage,
        denomination=denomination,
    )

    custom_instructions += set_overpayment_allowance_for_period(
        current_overpayment_allowance=current_overpayment_allowance,
        updated_overpayment_allowance=updated_overpayment_allowance,
        denomination=denomination,
        account_id=state.vault.account_id,
    )

    custom_instructions += _handle_allowance_usage_inner(
        account_id=state.vault.account_id,
        account_type=account_type,
        start_of_period_balances=start_of_period_balances,
        end_of_period_balances=end_of_period_balances,
        denomination=denomination,
        overpayment_percentage=overpayment_percentage,
        overpayment_allowance_fee_percentage=overpayment_allowance_fee_percentage,
        overpayment_allowance_fee_income_account=overpayment_allowance_fee_income_account,
    )

    return custom_instructions


def handle_allowance_usage_adhoc(
    state: state_utils.SmartContractState,
    account_type: str,
    effective_datetime: datetime,
    fetchers_config: HandleAllowanceUsageAdhocFetchersConfig = (
        DEFAULT_HANDLE_ALLOWANCE_USAGE_ADHOC_FETCHERS_CONFIG
    ),
) -> list[CustomInstruction]:
    """Check the overpayments in the past year and charges a fee if the total exceeds the allowance.

    For use inside ad-hoc hook executions, such as conversion or deactivation,
    where the start_of_period is not at a fixed delta from the effective date.

    Args:
        state: The smart contract state.
        account_type: The account's type, used for posting metadata purposes.
        effective_datetime: When the request to handle the usage is made.
        fetchers_config: The fetchers configuration.

    Returns:
        List of custom instructions for the overpayment fee.
    """

    state = _append_to_state(state=state, fetchers_config=fetchers_config)

    rejection = state_utils.check_parameters_exist(
        state=state,
        param_ids={
            fetchers_config.denomination_param_id,
            fetchers_config.overpayment_allowance_percentage_param_id,
            fetchers_config.overpayment_allowance_fee_percentage_param_id,
            fetchers_config.overpayment_allowance_fee_income_account_param_id,
        },
    )
    assert rejection is None, rejection

    # data extraction
    denomination: str = state.parameters[fetchers_config.denomination_param_id]  # type: ignore
    overpayment_percentage: Decimal = state.parameters[
        fetchers_config.overpayment_allowance_percentage_param_id
    ]  # type: ignore
    overpayment_allowance_fee_percentage: Decimal = state.parameters[
        fetchers_config.overpayment_allowance_fee_percentage_param_id
    ]  # type: ignore
    overpayment_allowance_fee_income_account: str = state.parameters[
        fetchers_config.overpayment_allowance_fee_income_account_param_id
    ]  # type: ignore

    one_year_balances: Mapping[BalanceCoordinate, BalanceTimeseries] = (
        state.vault.get_balances_timeseries(
            fetcher_id=fetchers_config.one_year_allowance_bif_id,
        )
    )

    last_allowance_schedule_datetime: datetime | None = (
        state.vault.get_last_scheduled_event_datetimes_observation(
            fetcher_id=fetchers_config.overpayment_allowance_last_execution_sof_id
        ).last_scheduled_event_datetimes[CHECK_OVERPAYMENT_ALLOWANCE_EVENT]
    )

    start_of_period_datetime = get_start_of_current_allowance_period(
        state=state,
        check_overpayment_allowance_last_execution_datetime=last_allowance_schedule_datetime,
    )

    start_of_period_balances = _extract_balance_default_dict_from_interval(
        denomination=denomination,
        balance_interval=one_year_balances,
        effective_datetime=start_of_period_datetime,
    )
    end_of_period_balances = _extract_balance_default_dict_from_interval(
        denomination=denomination,
        balance_interval=one_year_balances,
        effective_datetime=effective_datetime,
    )

    # core logic + transformation
    return _handle_allowance_usage_inner(
        account_id=state.vault.account_id,
        account_type=account_type,
        start_of_period_balances=start_of_period_balances,
        end_of_period_balances=end_of_period_balances,
        denomination=denomination,
        overpayment_percentage=overpayment_percentage,
        overpayment_allowance_fee_percentage=overpayment_allowance_fee_percentage,
        overpayment_allowance_fee_income_account=overpayment_allowance_fee_income_account,
    )


def _handle_allowance_usage_inner(
    account_id: str,
    account_type: str,
    start_of_period_balances: BalanceDefaultDict,
    end_of_period_balances: BalanceDefaultDict,
    denomination: str,
    overpayment_percentage: Decimal,
    overpayment_allowance_fee_percentage: Decimal,
    overpayment_allowance_fee_income_account: str,
) -> list[CustomInstruction]:
    """Execute inner allowance usage logic."""
    # core logic
    used_allowance = get_allowance_usage(
        start_of_period_balances=start_of_period_balances,
        end_of_period_balances=end_of_period_balances,
        denomination=denomination,
    )

    allowance = get_allowance_for_period(
        start_of_period_balances=start_of_period_balances,
        allowance_percentage=overpayment_percentage,
        denomination=denomination,
    )

    fee_amount = get_allowance_usage_fee(
        used_allowance=used_allowance,
        allowance=allowance,
        overpayment_allowance_fee_percentage=overpayment_allowance_fee_percentage,
    )

    # transformation
    if fee_amount <= Decimal(0):
        return []

    return fees.fee_custom_instruction(
        customer_account_id=account_id,
        denomination=denomination,
        amount=fee_amount,
        internal_account=overpayment_allowance_fee_income_account,
        customer_account_address=common_addresses.PENALTIES,
        instruction_details=posting_utils.standard_instruction_details(
            description=f"Overpayment fee charged due to used allowance {used_allowance} "
            f"{denomination} exceeding allowance {allowance} {denomination}",
            event_type="CHARGE_OVERPAYMENT_FEE",
            gl_impacted=True,
            account_type=account_type,
        ),
    )


def _extract_balance_default_dict_from_interval(
    denomination: str,
    balance_interval: Mapping[BalanceCoordinate, BalanceTimeseries],
    effective_datetime: datetime,
) -> BalanceDefaultDict:
    """Extracts a default dictionary of balances at a specific datetime from a balance interval.

    Args:
        denomination: The denomination of the balances.
        balance_interval: A mapping of balance coordinates to their timeseries.
        effective_datetime: The datetime at which to extract the balances.

    Returns:
        BalanceDefaultDict: A dictionary containing the overpayment and principal balances at
        the given datetime.
    """
    overpayment_coordinate = BalanceCoordinate(
        account_address=overpayment.OVERPAYMENT_ADDRESS,
        asset=DEFAULT_ASSET,
        denomination=denomination,
        phase=Phase.COMMITTED,
    )
    principal_coordinate = BalanceCoordinate(
        account_address=lending_addresses.PRINCIPAL,
        asset=DEFAULT_ASSET,
        denomination=denomination,
        phase=Phase.COMMITTED,
    )
    overpayment_at_effective_datetime = balance_interval[overpayment_coordinate].at(
        at_datetime=effective_datetime
    )
    principal_at_effective_datetime = balance_interval[principal_coordinate].at(
        at_datetime=effective_datetime
    )

    return BalanceDefaultDict(
        mapping={
            overpayment_coordinate: overpayment_at_effective_datetime,
            principal_coordinate: principal_at_effective_datetime,
        }
    )


def get_overpayment_allowance_status(
    state: state_utils.SmartContractState,
    effective_datetime: datetime,
    fetchers_config: GetOverpaymentAllowanceStatusFetchersConfig = DEFAULT_GET_OVERPAYMENT_ALLOWANCE_STATUS_FETCHERS_CONFIG,  # noqa: E501
) -> OverpaymentAllowanceStatus:
    """Determine the original and used overpayment allowance for the current allowance period.

    For use in adhoc situations (e.g. account attributes).
    Both numbers should be >= 0, but there is no strict relationship between the two (i.e.
    used allowance can be >,=, < original allowance).

    Args:
        state: The smart contract state.
        effective_datetime: Datetime for which the overpayment status is calculated.
        fetchers_config: Fetcher configuration for fetching state parameters.

    Returns:
        The original and used overpayment allowance.
    """

    state = _append_to_state(state=state, fetchers_config=fetchers_config)

    rejection = state_utils.check_parameters_exist(
        state=state,
        param_ids={
            fetchers_config.denomination_param_id,
            fetchers_config.overpayment_allowance_percentage_param_id,
        },
    )
    assert rejection is None, rejection

    denomination: str = state.parameters[fetchers_config.denomination_param_id]  # type: ignore

    one_year_balances = state.vault.get_balances_timeseries(
        fetcher_id=fetchers_config.one_year_allowance_bif_id,
    )

    last_allowance_schedule_datetime: datetime | None = (
        state.vault.get_last_scheduled_event_datetimes_observation(
            fetcher_id=fetchers_config.overpayment_allowance_last_execution_sof_id
        ).last_scheduled_event_datetimes[CHECK_OVERPAYMENT_ALLOWANCE_EVENT]
    )

    start_of_period_datetime = get_start_of_current_allowance_period(
        state=state,
        check_overpayment_allowance_last_execution_datetime=last_allowance_schedule_datetime,
    )

    allowance_param_timeseries: ParameterValueTimeseries | None = (
        state.vault.get_parameter_timeseries(
            fetcher_id=fetchers_config.one_year_allowance_param_pif_id,
        ).get(fetchers_config.overpayment_allowance_percentage_param_id)
    )

    assert allowance_param_timeseries is not None, Rejection(
        message=(
            f"Parameter {fetchers_config.one_year_allowance_param_pif_id} "
            "is missing from the timeseries"
        ),
        reason_code=RejectionReason.AGAINST_TNC,
    )

    allowance_percentage: Decimal = allowance_param_timeseries.at(
        at_datetime=start_of_period_datetime
    )  # type: ignore

    start_of_period_balances = _extract_balance_default_dict_from_interval(
        denomination=denomination,
        balance_interval=one_year_balances,
        effective_datetime=start_of_period_datetime,
    )
    end_of_period_balances = _extract_balance_default_dict_from_interval(
        denomination=denomination,
        balance_interval=one_year_balances,
        effective_datetime=effective_datetime,
    )

    overpayment_allowance_used = get_allowance_usage(
        start_of_period_balances=start_of_period_balances,
        end_of_period_balances=end_of_period_balances,
        denomination=denomination,
    )

    overpayment_allowance = get_allowance_for_period(
        start_of_period_balances=start_of_period_balances,
        allowance_percentage=allowance_percentage,
        denomination=denomination,
    )

    return OverpaymentAllowanceStatus(
        overpayment_allowance=overpayment_allowance,
        overpayment_allowance_used=overpayment_allowance_used,
    )


def get_start_of_current_allowance_period(
    state: state_utils.SmartContractState,
    check_overpayment_allowance_last_execution_datetime: datetime | None = None,
) -> datetime:
    """Determine the start of the allowance period in progress.

    The initial allowance period starts on account creation date and then restarts at midnight
    on the account creation anniversary.

    Args:
        state: The smart contract state.
        check_overpayment_allowance_last_execution_datetime: When the handle allowance usage
            schedule last ran, if ever.

    Returns:
        The start of the allowance period.
    """
    if check_overpayment_allowance_last_execution_datetime is not None:
        return check_overpayment_allowance_last_execution_datetime.astimezone(
            state.vault.events_timezone
        ).replace(hour=0, minute=0, second=0, microsecond=0)

    one_year_ago = state.effective_datetime.astimezone(state.vault.events_timezone).replace(
        hour=0, minute=0, second=0, microsecond=0
    ) - relativedelta(years=1)

    # we must leave time components on account creation as the period cannot start before the
    # account was actually created
    return max(state.vault.get_account_activation_datetime(), one_year_ago)


def set_overpayment_allowance_for_period(
    current_overpayment_allowance: Decimal,
    updated_overpayment_allowance: Decimal,
    denomination: str,
    account_id: str,
    remaining_overpayment_allowance_tracker_address: str = REMAINING_OVERPAYMENT_ALLOWANCE_TRACKER,
    internal_contra_address: str = common_addresses.INTERNAL_CONTRA,
) -> list[CustomInstruction]:
    """Set the overpayment allowance amount for the current period.

    Initialises the overpayment allowance tracker balance with this amount.

    NOTE: This function uses the overpayment allowance tracker balance to track the overpayment
    allowance, and so it likely duplicates work that exists in other functions in this feature.
    This feature should be refactored to remove this duplication by relying only on the
    overpayment allowance tracker balance.
    See https://pennyworth.atlassian.net/browse/INC-8754

    Args:
        current_overpayment_allowance: The overpayment allowance amount currently in the
            overpayment allowance tracker balance.
        updated_overpayment_allowance: The overpayment allowance amount for the next period.
        denomination: The denomination of the loan being repaid.
        account_id: The id of the loan account.
        remaining_overpayment_allowance_tracker_address: Address to use for the tracker balance.
        internal_contra_address: Address to use for internal contra entries.

    Returns:
        The list of postings to set the overpayment allowance tracker balance to the overpayment
            allowance amount.
    """
    postings: list[Posting] = []

    overpayment_allowance_delta = current_overpayment_allowance - updated_overpayment_allowance

    if overpayment_allowance_delta == Decimal(0):
        return []

    if overpayment_allowance_delta < Decimal(0):
        credit_address = internal_contra_address
        debit_address = remaining_overpayment_allowance_tracker_address
        overpayment_allowance_delta = abs(overpayment_allowance_delta)
    else:
        credit_address = remaining_overpayment_allowance_tracker_address
        debit_address = internal_contra_address

    postings = posting_utils.create_postings(
        amount=overpayment_allowance_delta,
        debit_account=account_id,
        debit_address=debit_address,
        credit_account=account_id,
        credit_address=credit_address,
        denomination=denomination,
    )

    return [
        CustomInstruction(
            postings=postings,
            instruction_details={
                "description": "Resetting the overpayment allowance tracker balance",
                "event": "RESET_REMAINING_OVERPAYMENT_ALLOWANCE_TRACKER",
            },
        )
    ]


def reduce_overpayment_allowance(
    state: state_utils.SmartContractState,
    overpayment_amount: Decimal,
    balances: BalanceDefaultDict | None = None,
    fetchers_config: ReduceOverpaymentAllowanceFetchersConfig = (
        DEFAULT_REDUCE_OVERPAYMENT_ALLOWANCE_FETCHERS_CONFIG
    ),
) -> list[Posting]:
    """Create postings to update the overpayment allowance tracker.

    Removes the overpayment amount from the overpayment allowance for the current allowance period.

    NOTE: This function uses the overpayment allowance tracker balance to track the overpayment
    allowance, and so it likely duplicates work that exists in other functions in this feature.
    This feature should be refactored to remove this duplication by relying only on the
    overpayment allowance tracker balance.
    See https://pennyworth.atlassian.net/browse/INC-8754

    Args:
        state: The smart contract state.
        overpayment_amount: The amount overpaid.
        balances: Balances to use. If not supplied, state.balances is used.
        fetchers_config: The fetchers configuration.

    Returns:
        The corresponding postings to update the overpayment allowance tracker balance.
    """

    state = _append_to_state(state=state, fetchers_config=fetchers_config)
    rejection = state_utils.check_parameters_exist(
        state=state,
        param_ids={
            fetchers_config.denomination_param_id,
        },
    )
    assert rejection is None, rejection

    if balances is None:
        balances = state.balances
    postings: list[Posting] = []
    denomination: str = state.parameters[fetchers_config.denomination_param_id]  # type: ignore

    outstanding_principal = balance_utils.balance_at_coordinates(
        balances=balances,
        address=fetchers_config.principal_address,
        denomination=denomination,
    )

    # since an overpayment can also pay off accrued interest, it is technically
    # possible for an overpayment to be greater than the outstanding principal on the
    # loan, which is why the check below is needed
    if (overpayment_posting_amount := min(overpayment_amount, outstanding_principal)) > Decimal(0):
        postings += posting_utils.create_postings(
            amount=overpayment_posting_amount,
            debit_account=state.vault.account_id,
            debit_address=fetchers_config.internal_contra_address,
            credit_account=state.vault.account_id,
            credit_address=fetchers_config.remaining_overpayment_allowance_tracker_address,
            denomination=denomination,
        )

    return postings


def get_overpayment_allowance_fee_for_early_repayment(
    state: state_utils.SmartContractState,
    fetchers_config: GetOverpaymentAllowanceFeeForEarlyRepaymentFetchersConfig = (
        DEFAULT_GET_OVERPAYMENT_ALLOWANCE_FEE_FOR_EARLY_REPAYMENT_FETCHERS_CONFIG
    ),
) -> Decimal:
    """Calculate the overpayment allowance fee if the total amount on the loan were to be repaid.

    NOTE: This function uses the overpayment allowance tracker balance to calculate the
    overpayment allowance fee, and so it likely duplicates work that exists in other
    functions in this feature. This feature should be refactored to remove this duplication
    by relying only on the overpayment allowance tracker balance.
    See https://pennyworth.atlassian.net/browse/INC-8754

    Args:
        state: The smart contract state.
        fetchers_config: The fetchers configuration.

    Returns:
        The overpayment allowance fee.
    """
    state = _append_to_state(state=state, fetchers_config=fetchers_config)
    rejection = state_utils.check_parameters_exist(
        state=state,
        param_ids={
            fetchers_config.denomination_param_id,
            fetchers_config.overpayment_allowance_fee_percentage_param_id,
        },
    )
    assert rejection is None, rejection

    denomination: str = state.parameters[fetchers_config.denomination_param_id]  # type: ignore
    balances = state.balances

    overpayment_allowance_fee_percentage: Decimal = state.parameters[
        fetchers_config.overpayment_allowance_fee_percentage_param_id
    ]  # type: ignore

    total_outstanding_debt = balance_utils.net_debit(
        balance_utils.sum_balances(
            balances=balances,
            addresses=fetchers_config.outstanding_addresses,
            denomination=denomination,
        )
    )

    due_amount = balance_utils.net_debit(
        balance_utils.sum_balances(
            balances=balances,
            addresses=fetchers_config.repayment_hierarchy,
            denomination=denomination,
        )
    )

    # any amount paid towards a due balance does not count as an overpayment amount
    overpayment_needed_to_completely_repay_loan = total_outstanding_debt - due_amount

    # The overpayment allowance tracker balance is initialized with the total amount
    # that is allowed to be overpaid before a fee is charged. Every time an overpayment
    # occurs, the overpayment amount is subtracted from the overpayment allowance tracker
    # balance. This means that we need to subtract the theoretical overpayment amount
    # that is needed to completely repay the loan from the tracker balance
    # in order to properly calculate the current overpayment allowance used.
    inflight_overpayment_allowance_amount = (
        balance_utils.balance_at_coordinates(
            balances=balances,
            address=fetchers_config.remaining_overpayment_allowance_tracker_address,
            denomination=denomination,
        )
        - overpayment_needed_to_completely_repay_loan
    )

    # If the overpayment allowance tracker balance is non-negative, it means
    # the customer has not yet exceeded the overpayment allowance amount.
    # If the tracker balance is negative, the customer has exceeded the overpayment
    # allowance amount by the tracker balance amount.
    overpayment_allowance_exceeded_amount = (
        abs(inflight_overpayment_allowance_amount)
        if inflight_overpayment_allowance_amount < Decimal(0)
        else Decimal(0)
    )

    return utils.round_decimal(
        amount=overpayment_allowance_fee_percentage * overpayment_allowance_exceeded_amount,
        decimal_places=2,
    )


def initialise_overpayment_allowance_from_principal_amount(
    state: state_utils.SmartContractState,
    principal: Decimal,
    fetchers_config: InitialiseOverpaymentAllowanceFetchersConfig = (
        DEFAULT_INITIALISE_OVERPAYMENT_ALLOWANCE_FETCHERS_CONFIG
    ),
) -> list[CustomInstruction]:
    """Return postings to set the overpayment allowance amount.

    Assumes no previous overpayment allowance tracker balance exists. In other words, this function
    is intended to be used in the activation hook.

    NOTE: This function uses the overpayment allowance tracker balance to calculate the
    overpayment allowance fee, and so it likely duplicates work that exists in other
    functions in this feature. This feature should be refactored to remove this duplication
    by relying only on the overpayment allowance tracker balance.
    See https://pennyworth.atlassian.net/browse/INC-8754

    Args:
        state: The smart contract state.
        principal: The principal from which to calculate the overpayment allowance.
        fetchers_config: The fetchers configuration.

    Returns:
        The postings to set the overpayment allowance as a percent of the principal.
    """

    state = _append_to_state(state=state, fetchers_config=fetchers_config)
    rejection = state_utils.check_parameters_exist(
        state=state,
        param_ids={
            fetchers_config.denomination_param_id,
            fetchers_config.overpayment_allowance_percentage_param_id,
        },
    )
    assert rejection is None, rejection

    denomination: str = state.parameters[fetchers_config.denomination_param_id]  # type: ignore

    overpayment_allowance_percentage: Decimal = state.parameters[
        fetchers_config.overpayment_allowance_percentage_param_id
    ]  # type: ignore

    return set_overpayment_allowance_for_period(
        current_overpayment_allowance=Decimal(0),
        updated_overpayment_allowance=principal * overpayment_allowance_percentage,
        denomination=denomination,
        account_id=state.vault.account_id,
    )


def get_residual_cleanup_postings(
    balances: BalanceDefaultDict, account_id: str, denomination: str
) -> list[Posting]:
    """Return the postings needed to cleanup the overpayment allowance tracker balance.

    Args:
        balances: The balances, including the overpayment allowance tracker balance,
            that need to be cleared.
        account_id: The id of the loan account.
        denomination: The denomination of the loan being repaid.

    Returns:
        A list of postings to net out the overpayment allowance tracker balance.
    """
    overpayment_allowance_amount: Decimal = balance_utils.net_debit(
        bal=balance_utils.get_current_net_balance(
            balances=balances,
            address=REMAINING_OVERPAYMENT_ALLOWANCE_TRACKER,
            denomination=denomination,
        )
    )

    return posting_utils.create_postings(
        amount=overpayment_allowance_amount,
        debit_account=account_id,
        credit_account=account_id,
        debit_address=common_addresses.INTERNAL_CONTRA,
        credit_address=REMAINING_OVERPAYMENT_ALLOWANCE_TRACKER,
        denomination=denomination,
    )


OverpaymentAllowanceFeature = lending_interfaces.Overpayment(
    handle_overpayment=reduce_overpayment_allowance,
)

OverpaymentAllowanceResidualCleanupFeature = lending_interfaces.ResidualCleanup(
    get_residual_cleanup_postings=get_residual_cleanup_postings
)
