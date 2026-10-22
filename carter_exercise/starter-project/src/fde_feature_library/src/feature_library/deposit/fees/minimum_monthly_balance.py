__smart_contract_feature__ = True

# standard libs
from datetime import datetime
from decimal import Decimal
from json import loads
from typing import Mapping, NamedTuple
from zoneinfo import ZoneInfo

from dateutil.relativedelta import relativedelta

import feature_library.common.balance_utils as balance_utils
import feature_library.common.date_and_time as date_and_time
import feature_library.common.denomination as denomination_module
import feature_library.common.fetchers as fetchers
import feature_library.common.posting_utils as posting_utils
import feature_library.common.state_utils as state_utils
import feature_library.common.utils as common_utils
import feature_library.deposit.common as common
import feature_library.deposit.fees.partial_fee as partial_fee
import feature_library.deposit.interfaces as deposit_interfaces

# contracts api
from contracts_api import (
    DEFAULT_ADDRESS,
    DEFAULT_ASSET,
    BalanceCoordinate,
    BalanceDiscreteTimeseries,
    CustomInstruction,
    DefinedDateTime,
    ExpectedParameter,
    ParametersFilter,
    ParametersObservationFetcher,
    Phase,
    ScheduledEvent,
    ScheduleExpression,
    SmartContractEventType,
)

# inception sdk
from inception_sdk.vault.contracts.extensions.contracts_api_extensions import SmartContractVault

APPLY_MINIMUM_MONTHLY_BALANCE_EVENT = "APPLY_MINIMUM_BALANCE_FEE"
UTC = ZoneInfo("UTC")

# Addresses
OUTSTANDING_MINIMUM_BALANCE_FEE_TRACKER = "outstanding_minimum_balance_fee_tracker"

# Parameters
MINIMUM_BALANCE_FEE_PARAM_ID = "&{minimum_balance_fee}"
MINIMUM_BALANCE_FEE_PARAM = ExpectedParameter(
    id=MINIMUM_BALANCE_FEE_PARAM_ID,
    triggers_pre_parameter_change_hook=False,
    triggers_post_parameter_change_hook=False,
)

MINIMUM_BALANCE_THRESHOLD_BY_TIER_PARAM_ID = "&{minimum_balance_threshold_by_tier}"
"""
The parameter value should look like this:
{
    "UPPER_TIER": "25",
    "MIDDLE_TIER": "75",
    "LOWER_TIER": "100",
}
"""
MINIMUM_BALANCE_THRESHOLD_BY_TIER_PARAM = ExpectedParameter(
    id=MINIMUM_BALANCE_THRESHOLD_BY_TIER_PARAM_ID,
    triggers_pre_parameter_change_hook=False,
    triggers_post_parameter_change_hook=False,
)

MINIMUM_BALANCE_FEE_INCOME_ACCOUNT_PARAM_ID = "&{minimum_balance_fee_income_account}"
MINIMUM_BALANCE_FEE_INCOME_ACCOUNT_PARAM = ExpectedParameter(
    id=MINIMUM_BALANCE_FEE_INCOME_ACCOUNT_PARAM_ID,
    triggers_pre_parameter_change_hook=False,
    triggers_post_parameter_change_hook=False,
)

MINIMUM_BALANCE_FEE_APPLICATION_DAY_PARAM_ID = "&{minimum_balance_fee_application_day}"
MINIMUM_BALANCE_FEE_APPLICATION_DAY_PARAM = ExpectedParameter(
    id=MINIMUM_BALANCE_FEE_APPLICATION_DAY_PARAM_ID,
    triggers_pre_parameter_change_hook=False,
    triggers_post_parameter_change_hook=False,
)

MINIMUM_BALANCE_FEE_APPLICATION_TIME_PARAM_ID = "&{minimum_balance_fee_application_time}"
MINIMUM_BALANCE_FEE_APPLICATION_TIME_PARAM = ExpectedParameter(
    id=MINIMUM_BALANCE_FEE_APPLICATION_TIME_PARAM_ID,
    triggers_pre_parameter_change_hook=False,
    triggers_post_parameter_change_hook=False,
)

MINIMUM_BALANCE_PARTIAL_FEE_ENABLED_PARAM_ID = "&{partial_minimum_balance_fee_application_enabled}"
MINIMUM_BALANCE_PARTIAL_FEE_ENABLED_PARAM = ExpectedParameter(
    id=MINIMUM_BALANCE_PARTIAL_FEE_ENABLED_PARAM_ID,
    triggers_pre_parameter_change_hook=False,
    triggers_post_parameter_change_hook=False,
    optional=True,
)

expected_parameters = [
    MINIMUM_BALANCE_FEE_PARAM,
    MINIMUM_BALANCE_THRESHOLD_BY_TIER_PARAM,
    MINIMUM_BALANCE_FEE_INCOME_ACCOUNT_PARAM,
    MINIMUM_BALANCE_FEE_APPLICATION_DAY_PARAM,
    MINIMUM_BALANCE_FEE_APPLICATION_TIME_PARAM,
    MINIMUM_BALANCE_PARTIAL_FEE_ENABLED_PARAM,
    common.ACCOUNT_TIER_PARAM,
    denomination_module.DENOMINATION_PARAM,
]

MINIMUM_BALANCE_FEE_POF_ID = "minimum_balance_fee_pof"
MINIMUM_BALANCE_FEE_POF = ParametersObservationFetcher(
    fetcher_id=MINIMUM_BALANCE_FEE_POF_ID,
    at=DefinedDateTime.EFFECTIVE_DATETIME,
    filter=ParametersFilter(parameter_ids=[p.id for p in expected_parameters]),
)

data_fetchers = [
    fetchers.ALL_BALANCES_ET_BOF,
    MINIMUM_BALANCE_FEE_POF,
    fetchers.ONE_MONTH_EFFECTIVE_DATE_BDIF,
]

event_types = [
    SmartContractEventType(name=APPLY_MINIMUM_MONTHLY_BALANCE_EVENT),
]

MinimumBalanceFetchersConfig = NamedTuple(
    "MinimumBalanceFetchersConfig",
    [
        ("param_fetcher_id", str),
        ("denomination_param_id", str),
        ("month_balances_fetcher_id", str),
    ],
)
DEFAULT_MINIMUM_BALANCE_FETCHERS_CONFIG = MinimumBalanceFetchersConfig(
    param_fetcher_id=MINIMUM_BALANCE_FEE_POF_ID,
    denomination_param_id=denomination_module.DENOMINATION_PARAM_ID,
    month_balances_fetcher_id=fetchers.ONE_MONTH_EFFECTIVE_DATE_BDIF.fetcher_id,
)


def get_parameters(
    vault: SmartContractVault, param_fetcher_id: str = MINIMUM_BALANCE_FEE_POF_ID
) -> dict[str, datetime | Decimal | str | None]:
    """Retrieves configuration parameters for the minimum monthly balance fee feature.

    Args:
        vault: The vault object to retrieve parameters from.
        param_fetcher_id: The ID of the fetcher used to retrieve parameters.

    Returns:
        A dictionary mapping parameter IDs to their values.
    """
    return vault.get_parameters_observation(fetcher_id=param_fetcher_id).parameters


def _append_to_state(
    state: state_utils.SmartContractState,
    fetchers_config: MinimumBalanceFetchersConfig = DEFAULT_MINIMUM_BALANCE_FETCHERS_CONFIG,
    balance_fetcher_id: str = fetchers.ALL_BALANCES_ET_BOF_ID,
) -> state_utils.SmartContractState:
    """Updates the contract state with the minimum monthly balance fee parameters and balances.

    Args:
        state: The current state of the smart contract.
        fetchers_config: Configuration for the fetchers used.
        balance_fetcher_id: The ID of the fetcher used to retrieve balances.

    Returns:
        The updated state object.
    """
    return state_utils.append_to_state(
        state=state,
        parameters=get_parameters(state.vault, fetchers_config.param_fetcher_id),
        balances=state.vault.get_balances_observation(fetcher_id=balance_fetcher_id).balances,
    )


def get_scheduled_events(
    state: state_utils.SmartContractState,
    fetchers_config: MinimumBalanceFetchersConfig = DEFAULT_MINIMUM_BALANCE_FETCHERS_CONFIG,
) -> dict[str, ScheduledEvent]:
    """Returns the scheduled events for applying the minimum monthly balance fee.

    Args:
        state: The current state of the smart contract.
        fetchers_config: Configuration for the fetchers used.

    Returns:
        A dictionary mapping event names to scheduled events.
    """
    state = state_utils.append_to_state(
        state=state,
        parameters=get_parameters(state.vault, fetchers_config.param_fetcher_id),
    )

    schedule_param_ids = {
        MINIMUM_BALANCE_FEE_APPLICATION_DAY_PARAM.id,
        MINIMUM_BALANCE_FEE_APPLICATION_TIME_PARAM.id,
    }

    rejection = state_utils.check_parameters_exist(state=state, param_ids=schedule_param_ids)
    assert rejection is None, rejection

    application_time_str = str(state.parameters[MINIMUM_BALANCE_FEE_APPLICATION_TIME_PARAM.id])
    application_time: date_and_time.Time = date_and_time.parse_time_str(application_time_str)

    day = int(str(state.parameters[MINIMUM_BALANCE_FEE_APPLICATION_DAY_PARAM.id]))

    start_datetime = state.effective_datetime.astimezone(
        state.vault.events_timezone
    ) + relativedelta(months=1, hour=0, minute=0, second=0, microsecond=0)

    return {
        APPLY_MINIMUM_MONTHLY_BALANCE_EVENT: ScheduledEvent(
            start_datetime=start_datetime,
            expression=ScheduleExpression(
                day=day,
                hour=application_time.hour,
                minute=application_time.minute,
                second=application_time.second,
            ),
        )
    }


def _average_balance(balances: list[Decimal]) -> Decimal:
    """Calculates the average of a list of balances.

    Args:
        balances: A list of Decimal balance values.

    Returns:
        The average balance as a Decimal.
    """
    if not balances:
        return Decimal(0)
    return sum(balances) / Decimal(len(balances))


def _is_monthly_mean_balance_above_threshold(
    state: state_utils.SmartContractState,
    fetchers_config: MinimumBalanceFetchersConfig,
) -> bool:
    """Checks if the monthly mean balance is above the configured threshold for the account's tier.

    Args:
        state: The current state of the smart contract.
        fetchers_config: Configuration for the fetchers used.

    Returns:
        True if the monthly mean balance is above the threshold, False otherwise.
    """
    thresholds_by_tier_str = str(state.parameters[MINIMUM_BALANCE_THRESHOLD_BY_TIER_PARAM.id])
    minimum_balance_threshold_tiers = loads(thresholds_by_tier_str)

    tier = str(state.parameters[common.ACCOUNT_TIER_PARAM.id])

    minimum_balance_threshold = Decimal(minimum_balance_threshold_tiers.get(tier, "0"))

    if minimum_balance_threshold <= Decimal(0):
        return True

    creation_date = state.vault.get_account_activation_datetime().date()
    period_start = (state.effective_datetime - relativedelta(months=1)).date()

    if period_start <= creation_date:
        period_start = creation_date + relativedelta(days=1)

    num_days = (state.effective_datetime.date() - period_start).days

    if num_days <= 0:
        return True

    num_days = min(num_days, 31)
    denomination: str = state.parameters[fetchers_config.denomination_param_id]  # type: ignore

    one_month_bals_ts_map: Mapping[BalanceCoordinate, BalanceDiscreteTimeseries] = (
        state.vault.get_balances_discrete_timeseries(
            fetcher_id=fetchers_config.month_balances_fetcher_id,
        )
    )
    coord = BalanceCoordinate(
        account_address=DEFAULT_ADDRESS,
        asset=DEFAULT_ASSET,
        denomination=denomination,
        phase=Phase.COMMITTED,
    )
    if coord not in one_month_bals_ts_map:
        return False

    one_month_bals_ts: BalanceDiscreteTimeseries = one_month_bals_ts_map[coord]

    balances_to_average: list[Decimal] = [
        balance_utils.net_credit(ts_item.value)
        for i in range(num_days)
        if (
            ts_item := one_month_bals_ts.get(
                at_datetime=state.effective_datetime - relativedelta(days=i)
            )
        )
        is not None
    ]
    monthly_mean_balance = _average_balance(balances_to_average)

    return monthly_mean_balance >= minimum_balance_threshold


PARTIAL_FEE_DETAILS = deposit_interfaces.PartialFeeCollection(
    outstanding_fee_address=OUTSTANDING_MINIMUM_BALANCE_FEE_TRACKER,
    fee_type="Partial Minimum Balance Fee",
    internal_account_parameter_id=MINIMUM_BALANCE_FEE_INCOME_ACCOUNT_PARAM.id,
)


def _are_partial_payments_enabled(
    state: state_utils.SmartContractState,
) -> bool:
    """Checks if partial minimum balance fee application is enabled.

    Args:
        state: The current state of the smart contract.

    Returns:
        True if partial payments are enabled, False otherwise.
    """
    return common_utils.str_to_bool(
        str(state.parameters.get(MINIMUM_BALANCE_PARTIAL_FEE_ENABLED_PARAM.id, "False"))
    )


def apply_fees(
    state: state_utils.SmartContractState,
    account_type: str,
    fetchers_config: MinimumBalanceFetchersConfig = DEFAULT_MINIMUM_BALANCE_FETCHERS_CONFIG,
    available_balance_feature: deposit_interfaces.AvailableBalance | None = None,
) -> list[CustomInstruction]:
    """Calculates and applies minimum monthly balance fees if mean balance is below threshold.

    Args:
        state: The current state of the smart contract.
        account_type: The account type to be noted in the custom instruction details.
        fetchers_config: Configuration for the fetchers used.
        available_balance_feature: The feature used to determine the available balance
            for partial fee charging.

    Returns:
        A list of CustomInstructions for charging the minimum balance fee.
    """
    state = _append_to_state(state=state, fetchers_config=fetchers_config)

    rejection = state_utils.check_parameters_exist(
        state,
        {
            fetchers_config.denomination_param_id,
            common.ACCOUNT_TIER_PARAM.id,
            MINIMUM_BALANCE_FEE_PARAM.id,
            MINIMUM_BALANCE_FEE_INCOME_ACCOUNT_PARAM.id,
            MINIMUM_BALANCE_THRESHOLD_BY_TIER_PARAM.id,
        },
    )
    assert rejection is None, rejection

    minimum_balance_fee = Decimal(str(state.parameters[MINIMUM_BALANCE_FEE_PARAM.id]))

    if minimum_balance_fee <= 0:
        return []

    if _is_monthly_mean_balance_above_threshold(
        state=state,
        fetchers_config=fetchers_config,
    ):
        return []

    income_account = str(state.parameters[MINIMUM_BALANCE_FEE_INCOME_ACCOUNT_PARAM.id])
    denomination = str(state.parameters[fetchers_config.denomination_param_id])

    fee_instructions = [
        CustomInstruction(
            postings=posting_utils.create_postings(
                amount=minimum_balance_fee,
                debit_account=state.vault.account_id,
                credit_account=income_account,
                denomination=denomination,
            ),
            value_datetime=state.effective_datetime,
            instruction_details=posting_utils.standard_instruction_details(
                description="Minimum balance fee",
                event_type=APPLY_MINIMUM_MONTHLY_BALANCE_EVENT,
                gl_impacted=True,
                account_type=account_type,
            ),
            override_all_restrictions=True,
        )
    ]

    if _are_partial_payments_enabled(state):
        return partial_fee.charge_partial_fee(
            state=state,
            fee_custom_instruction=fee_instructions[0],
            fee_details=PARTIAL_FEE_DETAILS,
            available_balance_feature=available_balance_feature,
        )

    return fee_instructions
