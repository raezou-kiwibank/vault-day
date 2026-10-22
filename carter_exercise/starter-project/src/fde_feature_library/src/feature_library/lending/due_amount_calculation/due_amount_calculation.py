"""Due amount calculation feature."""

__smart_contract_feature__ = True

# standard libs
from datetime import datetime
from decimal import Decimal
from typing import Callable, NamedTuple

from dateutil.relativedelta import relativedelta

# feature library
import feature_library.common.balance_utils as balance_utils
import feature_library.common.date_and_time as date_and_time
import feature_library.common.denomination as denomination_module
import feature_library.common.posting_utils as posting_utils
import feature_library.common.state_utils as state_utils
import feature_library.lending.addresses as lending_addresses
import feature_library.lending.interfaces as lending_interfaces
import feature_library.lending.repayments.overpayment as overpayment
import feature_library.lending.repayments.payments as payments

# contracts api
from contracts_api import (
    DEFAULT_ASSET,
    Balance,
    BalanceCoordinate,
    BalanceDefaultDict,
    CustomInstruction,
    DateTimeConstraint,
    DecimalConstraint,
    DefinedDateTime,
    EnumerationConstraint,
    EventTypesFilter,
    ExpectedParameter,
    LastScheduledEventDateTimesObservationFetcher,
    ParametersFilter,
    ParametersObservationFetcher,
    Phase,
    Posting,
    ScheduledEvent,
    ScheduleExpression,
    SmartContractEventType,
    UpdateAccountEventTypeDirective,
)

# inception sdk
from inception_sdk.vault.contracts.extensions.contracts_api_extensions import SmartContractVault

DUE_AMOUNT_CALCULATION_EVENT = "DUE_AMOUNT_CALCULATION"

# Parameters
BILLING_FREQUENCY_PARAM_ID = "&{billing_frequency}"
BILLING_FREQUENCY_PARAM = ExpectedParameter(
    id=BILLING_FREQUENCY_PARAM_ID,
    constraint=EnumerationConstraint(permitted_values=["monthly", "weekly", "fortnightly"]),
    triggers_pre_parameter_change_hook=False,
    triggers_post_parameter_change_hook=False,
)

DUE_AMOUNT_CALCULATION_TIME_PARAM_ID = "&{due_amount_calculation_time}"
DUE_AMOUNT_CALCULATION_TIME_PARAM = ExpectedParameter(
    id=DUE_AMOUNT_CALCULATION_TIME_PARAM_ID,
    triggers_pre_parameter_change_hook=False,
    triggers_post_parameter_change_hook=False,
)

DUE_AMOUNT_CALCULATION_DAY_PARAM_ID = "&{due_amount_calculation_day}"
DUE_AMOUNT_CALCULATION_DAY_PARAM = ExpectedParameter(
    id=DUE_AMOUNT_CALCULATION_DAY_PARAM_ID,
    constraint=DecimalConstraint(min_value=Decimal(1), max_value=Decimal(31)),
    triggers_pre_parameter_change_hook=False,
    triggers_post_parameter_change_hook=False,
)

FIRST_DUE_DATE_PARAM_ID = "&{first_due_date}"
FIRST_DUE_DATE_PARAM = ExpectedParameter(
    id=FIRST_DUE_DATE_PARAM_ID,
    constraint=DateTimeConstraint(),
    optional=True,
    triggers_pre_parameter_change_hook=False,
    triggers_post_parameter_change_hook=False,
)

expected_parameters = [
    BILLING_FREQUENCY_PARAM,
    DUE_AMOUNT_CALCULATION_TIME_PARAM,
    DUE_AMOUNT_CALCULATION_DAY_PARAM,
    FIRST_DUE_DATE_PARAM,
    denomination_module.DENOMINATION_PARAM,
]

DUE_AMOUNT_CALC_POF_ID = "due_amount_calculation_pof"
DUE_AMOUNT_CALC_POF = ParametersObservationFetcher(
    fetcher_id=DUE_AMOUNT_CALC_POF_ID,
    at=DefinedDateTime.EFFECTIVE_DATETIME,
    filter=ParametersFilter(parameter_ids=[p.id for p in expected_parameters]),
)

LAST_DUE_AMOUNT_CALCULATION_SOF_ID = "LAST_DUE_AMOUNT_CALCULATION_SOF"
LAST_DUE_AMOUNT_CALCULATION_SOF = LastScheduledEventDateTimesObservationFetcher(
    fetcher_id=LAST_DUE_AMOUNT_CALCULATION_SOF_ID,
    filter=EventTypesFilter(
        event_types=[DUE_AMOUNT_CALCULATION_EVENT],
    ),
    at=DefinedDateTime.EFFECTIVE_DATETIME,
)

data_fetchers = [
    DUE_AMOUNT_CALC_POF,
    LAST_DUE_AMOUNT_CALCULATION_SOF,
]


def get_parameters(
    vault: SmartContractVault, param_fetcher_id: str = DUE_AMOUNT_CALC_POF_ID
) -> dict[str, datetime | Decimal | str | None]:
    """Retrieves the parameters from the vault observation fetcher.

    Args:
        vault: The SmartContractVault instance.
        param_fetcher_id: The ID of the parameter observation fetcher.

    Returns:
        dict: A dictionary of parameter values.
    """
    return vault.get_parameters_observation(fetcher_id=param_fetcher_id).parameters


def _append_to_state(
    state: state_utils.SmartContractState,
    fetchers_config_pof_id: str = DUE_AMOUNT_CALC_POF_ID,
) -> state_utils.SmartContractState:
    parameters = get_parameters(state.vault, fetchers_config_pof_id)
    return state_utils.append_to_state(state=state, parameters=parameters)


def get_previous_application_datetime(
    state: state_utils.SmartContractState,
    last_sof_id: str = LAST_DUE_AMOUNT_CALCULATION_SOF_ID,
) -> datetime:
    """Retrieves the previous execution datetime for the due calculation event.

    Args:
        state: The current state of the smart contract.
        last_sof_id: The ID of the fetcher for last scheduled event datetimes.

    Returns:
        datetime: The previous application datetime, or account activation datetime if none.
    """
    last_exec = state.vault.get_last_scheduled_event_datetimes_observation(
        fetcher_id=last_sof_id
    ).last_scheduled_event_datetimes.get(DUE_AMOUNT_CALCULATION_EVENT)

    if last_exec is None:
        return state.vault.get_account_activation_datetime()

    return last_exec


def event_types(product_name: str) -> list[SmartContractEventType]:
    """Return the event types for the due amount calculation feature.

    Args:
        product_name: The product name.

    Returns:
        The smart contract event types list.
    """
    return [
        SmartContractEventType(
            name=DUE_AMOUNT_CALCULATION_EVENT,
            scheduler_tag_ids=[f"{product_name.upper()}_{DUE_AMOUNT_CALCULATION_EVENT}_AST"],
        )
    ]


DueAmountCalculationScheduleLogicResult = NamedTuple(
    "DueAmountCalculationScheduleLogicResult",
    [
        ("custom_instructions", list[CustomInstruction]),
        ("event_type_directives", list[UpdateAccountEventTypeDirective]),
    ],
)


def get_scheduled_events(
    state: state_utils.SmartContractState,
    first_due_datetime: datetime | None = None,
    skip: bool = False,
    param_fetcher_id: str = DUE_AMOUNT_CALC_POF_ID,
) -> dict[str, ScheduledEvent]:
    """Create a recurring due amount calculation schedule.

    Args:
        state: The smart contract state.
        first_due_datetime: The first due amount calculation datetime. If None,
            it will be calculated using `get_first_due_datetime`.
        skip: If True, schedule will be skipped.
        param_fetcher_id: The parameter fetcher ID.

    Returns:
        A dictionary containing the due amount calculation schedule.
    """
    state = _append_to_state(state, param_fetcher_id)

    billing_frequency = str(state.parameters[BILLING_FREQUENCY_PARAM_ID])

    if first_due_datetime is None:
        first_due_datetime = _get_first_due_datetime(state)

    time_str = str(state.parameters[DUE_AMOUNT_CALCULATION_TIME_PARAM_ID])
    parsed_time = date_and_time.parse_time_str(time_str)

    local_start = first_due_datetime.astimezone(state.vault.events_timezone).replace(
        hour=parsed_time.hour, minute=parsed_time.minute, second=parsed_time.second
    )

    if billing_frequency == "monthly":
        expression = ScheduleExpression(
            year=str(local_start.year),
            month=str(local_start.month),
            day=str(local_start.day),
            hour=str(local_start.hour),
            minute=str(local_start.minute),
            second=str(local_start.second),
        )
    else:
        expression = ScheduleExpression(
            day_of_week=str(local_start.weekday()),
            hour=str(local_start.hour),
            minute=str(local_start.minute),
            second=str(local_start.second),
        )

    return {
        DUE_AMOUNT_CALCULATION_EVENT: ScheduledEvent(
            start_datetime=local_start.replace(hour=0, minute=0, second=0),
            expression=expression,
            skip=skip,
        )
    }


def get_next_overdue_event_directive(
    state: state_utils.SmartContractState,
    repayment_period: int,
    check_overdue_time: str,
    overdue_event_name: str = "CHECK_OVERDUE",
) -> UpdateAccountEventTypeDirective:
    """Calculates and returns an UpdateAccountEventTypeDirective for the next CHECK_OVERDUE event.

    Args:
        state: The current state of the smart contract.
        repayment_period: The repayment period in days.
        check_overdue_time: The time str for the check overdue event (e.g. "00:00:00").
        overdue_event_name: The name of the overdue event. Defaults to "CHECK_OVERDUE".

    Returns:
        UpdateAccountEventTypeDirective: The directive to update the schedule.
    """
    next_overdue_datetime = state.effective_datetime + relativedelta(days=repayment_period)
    parsed_time = date_and_time.parse_time_str(check_overdue_time)

    schedule_datetime = next_overdue_datetime.astimezone(state.vault.events_timezone).replace(
        hour=parsed_time.hour, minute=parsed_time.minute, second=parsed_time.second
    )

    return UpdateAccountEventTypeDirective(
        event_type=overdue_event_name,
        expression=ScheduleExpression(
            year=str(schedule_datetime.year),
            month=str(schedule_datetime.month),
            day=str(schedule_datetime.day),
            hour=str(schedule_datetime.hour),
            minute=str(schedule_datetime.minute),
            second=str(schedule_datetime.second),
        ),
    )


def schedule_logic(
    state: state_utils.SmartContractState,
    get_expected_eia_callable: Callable[[state_utils.SmartContractState], Decimal],
    interest_application_feature: lending_interfaces.InterestApplication,
    repayment_hierarchy_config: lending_interfaces.RepaymentHierarchyConfig,
    is_repayment_holiday_active_callable: Callable[[state_utils.SmartContractState], bool]
    | None = None,  # noqa: E501
    get_due_principal_callable: Callable[
        [state_utils.SmartContractState, Decimal, Decimal], Decimal
    ]
    | None = None,
    param_fetcher_id: str = DUE_AMOUNT_CALC_POF_ID,
    denomination_param_id: str = denomination_module.DENOMINATION_PARAM_ID,
) -> DueAmountCalculationScheduleLogicResult:
    """Calculates dues for both Interest and Principal, applying Excess balance if available.

    Args:
        state: The current smart contract state.
        get_expected_eia_callable: Callable to get the expected EIA amount.
        interest_application_feature: InterestApplication interface containing application methods.
        repayment_hierarchy_config: Configuration defining the repayment hierarchy and its fetchers.
        is_repayment_holiday_active_callable: Callable to check if repayment holiday is active.
        get_due_principal_callable: Callable to calculate due principal based on expected EIA and
            EIA rounded accrued interest. Defaults to standard declining principal formula if None.
        param_fetcher_id: The parameter fetcher ID.
        denomination_param_id: Denomination parameter ID.

    Returns:
        DueAmountCalculationScheduleLogicResult: The logic execution results.
    """
    state = _append_to_state(state, param_fetcher_id)

    # Check for active Repayment Holiday
    if is_repayment_holiday_active_callable is not None and is_repayment_holiday_active_callable(
        state
    ):
        return DueAmountCalculationScheduleLogicResult(
            custom_instructions=[], event_type_directives=[]
        )

    # Check for Fortnightly odd-week skip
    billing_frequency = str(state.parameters[BILLING_FREQUENCY_PARAM_ID])
    if billing_frequency == "fortnightly":
        account_activation_datetime = state.vault.get_account_activation_datetime()
        local_tz = state.vault.events_timezone
        activation_date = account_activation_datetime.astimezone(local_tz).date()
        effective_date = state.effective_datetime.astimezone(local_tz).date()
        elapsed_days = (effective_date - activation_date).days
        elapsed_weeks = elapsed_days // 7
        if elapsed_weeks % 2 != 0:
            return DueAmountCalculationScheduleLogicResult(
                custom_instructions=[], event_type_directives=[]
            )

    rejection = state_utils.check_parameters_exist(state, {denomination_param_id})
    assert rejection is None, rejection

    denomination = str(state.parameters[denomination_param_id])

    previous_application_datetime = get_previous_application_datetime(state)

    # 1. Interest Application Postings and Amount
    interest_postings = interest_application_feature.apply_interest(
        state=state,
        previous_application_datetime=previous_application_datetime,
    )
    interest_amounts = interest_application_feature.get_interest_to_apply(
        state=state,
        previous_application_datetime=previous_application_datetime,
    )
    due_interest = interest_amounts.total_rounded

    # 2. Principal Due Postings and Amount
    expected_eia = get_expected_eia_callable(state)
    if get_due_principal_callable is not None:
        due_principal = get_due_principal_callable(
            state, expected_eia, interest_amounts.eia_rounded_accrued
        )
    else:
        due_principal = max(Decimal("0"), expected_eia - interest_amounts.eia_rounded_accrued)

    principal_postings: list[Posting] = []
    if due_principal > 0:
        principal_postings = posting_utils.create_postings(
            amount=due_principal,
            denomination=denomination,
            debit_account=state.vault.account_id,
            debit_address=lending_addresses.PRINCIPAL_DUE,
            credit_account=state.vault.account_id,
            credit_address=lending_addresses.PRINCIPAL,
        )

    # Combined due creation postings
    combined_postings = interest_postings + principal_postings

    # Calculate event_type_directives
    event_type_directives: list[UpdateAccountEventTypeDirective] = []
    if billing_frequency == "monthly":
        first_due_date_param = state.parameters.get(FIRST_DUE_DATE_PARAM_ID)
        if first_due_date_param is not None:
            calc_day = first_due_date_param.day  # type: ignore
        else:
            calc_day = int(state.parameters[DUE_AMOUNT_CALCULATION_DAY_PARAM_ID])  # type: ignore

        time_str = str(state.parameters[DUE_AMOUNT_CALCULATION_TIME_PARAM_ID])
        parsed_time = date_and_time.parse_time_str(time_str)
        local_tz = state.vault.events_timezone

        # Calculate next execution datetime
        next_due = state.effective_datetime.astimezone(local_tz).replace(
            hour=parsed_time.hour,
            minute=parsed_time.minute,
            second=parsed_time.second,
            microsecond=0,
        ) + relativedelta(months=1, day=calc_day)

        event_type_directives.append(
            UpdateAccountEventTypeDirective(
                event_type=DUE_AMOUNT_CALCULATION_EVENT,
                expression=ScheduleExpression(
                    year=str(next_due.year),
                    month=str(next_due.month),
                    day=str(next_due.day),
                    hour=str(next_due.hour),
                    minute=str(next_due.minute),
                    second=str(next_due.second),
                ),
            )
        )

    if not combined_postings:
        return DueAmountCalculationScheduleLogicResult(
            custom_instructions=[],
            event_type_directives=event_type_directives,
        )

    # 3. Inline Excess/Overpayment Knock-off
    excess_bal_coord = BalanceCoordinate(
        account_address=overpayment.OVERPAYMENT_ADDRESS,
        asset=DEFAULT_ASSET,
        denomination=denomination,
        phase=Phase.COMMITTED,
    )
    excess_amount = balance_utils.net_credit(state.balances[excess_bal_coord])

    excess_postings: list[Posting] = []
    if excess_amount > 0:
        # Create a simulated BalanceDefaultDict representing state balances plus the new dues
        simulated_balances = BalanceDefaultDict(lambda: Balance(), state.balances)

        coord_interest_due = BalanceCoordinate(
            account_address=lending_addresses.INTEREST_DUE,
            asset=DEFAULT_ASSET,
            denomination=denomination,
            phase=Phase.COMMITTED,
        )
        coord_principal_due = BalanceCoordinate(
            account_address=lending_addresses.PRINCIPAL_DUE,
            asset=DEFAULT_ASSET,
            denomination=denomination,
            phase=Phase.COMMITTED,
        )

        existing_interest_due = simulated_balances[coord_interest_due].net
        existing_principal_due = simulated_balances[coord_principal_due].net

        simulated_balances[coord_interest_due] = Balance(
            net=existing_interest_due + due_interest,
            credit=Decimal("0"),
            debit=existing_interest_due + due_interest,
        )
        simulated_balances[coord_principal_due] = Balance(
            net=existing_principal_due + due_principal,
            credit=Decimal("0"),
            debit=existing_principal_due + due_principal,
        )

        # Distribute the excess across the repayment hierarchy
        repayment_hierarchy = (
            repayment_hierarchy_config.repayment_hierarchy.get_repayment_hierarchy_order(
                state=state,
                fetchers_config=repayment_hierarchy_config.fetchers_config,
            )
        )

        distribution = payments.distribute_repayment_for_single_target(
            balances=simulated_balances,
            repayment_amount=excess_amount,
            denomination=denomination,
            repayment_hierarchy=repayment_hierarchy,
        )

        for addr, rep_amounts in distribution.repayment_per_address.items():
            if rep_amounts.rounded_amount > 0:
                excess_postings += payments.redistribute_postings(
                    debit_account=state.vault.account_id,
                    denomination=denomination,
                    amount=rep_amounts.rounded_amount,
                    credit_account=state.vault.account_id,
                    credit_address=addr,
                    debit_address=overpayment.OVERPAYMENT_ADDRESS,
                )

    total_postings = combined_postings + excess_postings

    custom_instructions = [
        CustomInstruction(
            postings=total_postings,
            instruction_details={
                "description": "Due amount calculation and excess balance knock-off",
                "event": DUE_AMOUNT_CALCULATION_EVENT,
            },
        )
    ]

    return DueAmountCalculationScheduleLogicResult(
        custom_instructions=custom_instructions,
        event_type_directives=event_type_directives,
    )


def _get_first_due_datetime(
    state: state_utils.SmartContractState,
) -> datetime:
    """Calculates the first due amount calculation datetime.

    If `FIRST_DUE_DATE_PARAM` is populated, returns that value.
    Otherwise, calculates it based on the billing frequency and day parameters,
    relative to the account activation datetime.

    Args:
        state: The smart contract state.
        param_fetcher_id: The parameter fetcher ID.

    Returns:
        The calculated first due amount calculation datetime.
    """
    # 1. Check override parameter first
    first_due_date_param = state.parameters.get(FIRST_DUE_DATE_PARAM_ID)
    if first_due_date_param is not None:
        return first_due_date_param  # type: ignore

    # 2. Otherwise calculate based on activation date and parameters
    account_activation_datetime = state.vault.get_account_activation_datetime()
    local_tz = state.vault.events_timezone
    activation_local = account_activation_datetime.astimezone(local_tz)

    billing_frequency = str(state.parameters[BILLING_FREQUENCY_PARAM_ID])
    time_str = str(state.parameters[DUE_AMOUNT_CALCULATION_TIME_PARAM_ID])
    parsed_time = date_and_time.parse_time_str(time_str)

    # Get the target day/day of week parameter
    calc_day_param = state.parameters.get(DUE_AMOUNT_CALCULATION_DAY_PARAM_ID)
    calc_day = int(calc_day_param)  # type: ignore

    if billing_frequency == "monthly":
        first_due = activation_local.replace(
            hour=parsed_time.hour,
            minute=parsed_time.minute,
            second=parsed_time.second,
            microsecond=0,
        ) + relativedelta(months=1, day=calc_day)

        if calc_day < activation_local.day:
            first_due += relativedelta(months=1)

    elif billing_frequency == "weekly":
        target_weekday = (calc_day - 1) % 7
        first_due = activation_local.replace(
            hour=parsed_time.hour,
            minute=parsed_time.minute,
            second=parsed_time.second,
            microsecond=0,
        ) + relativedelta(weeks=1)
        days_to_add = (target_weekday - first_due.weekday()) % 7
        first_due += relativedelta(days=days_to_add)

    elif billing_frequency == "fortnightly":
        target_weekday = (calc_day - 1) % 7
        first_due = activation_local.replace(
            hour=parsed_time.hour,
            minute=parsed_time.minute,
            second=parsed_time.second,
            microsecond=0,
        ) + relativedelta(weeks=2)
        days_to_add = (target_weekday - first_due.weekday()) % 7
        first_due += relativedelta(days=days_to_add)

    return first_due  # type: ignore
