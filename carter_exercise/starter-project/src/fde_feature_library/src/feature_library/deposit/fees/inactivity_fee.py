__smart_contract_feature__ = True

# standard libs
from datetime import datetime
from decimal import Decimal
from json import loads
from typing import NamedTuple

# feature library
import feature_library.common.date_and_time as date_and_time
import feature_library.common.denomination as denomination_module
import feature_library.common.fetchers as fetchers
import feature_library.common.posting_utils as posting_utils
import feature_library.common.schedule_utils as schedule_utils
import feature_library.common.state_utils as state_utils
import feature_library.common.tuples as common_tuples
import feature_library.common.utils as common_utils
import feature_library.deposit.fees.partial_fee as partial_fee
import feature_library.deposit.interfaces as deposit_interfaces

# contracts api
from contracts_api import (
    CustomInstruction,
    DefinedDateTime,
    ExpectedParameter,
    FlagsObservationFetcher,
    ParametersFilter,
    ParametersObservationFetcher,
    ScheduledEvent,
    ScheduleExpression,
    SmartContractEventType,
    UpdateAccountEventTypeDirective,
)

# inception sdk
from inception_sdk.vault.contracts.extensions.contracts_api_extensions import SmartContractVault

APPLICATION_EVENT = "APPLY_INACTIVITY_FEE"

# Addresses
OUTSTANDING_INACTIVITY_FEE_TRACKER = "outstanding_inactivity_fee_tracker"

# Parameters
INACTIVITY_FLAGS_PARAM_ID = "&{inactivity_flags}"
INACTIVITY_FLAGS_PARAM = ExpectedParameter(
    id=INACTIVITY_FLAGS_PARAM_ID,
    triggers_pre_parameter_change_hook=False,
    triggers_post_parameter_change_hook=False,
)

INACTIVITY_FEE_PARAM_ID = "&{inactivity_fee}"
INACTIVITY_FEE_PARAM = ExpectedParameter(
    id=INACTIVITY_FEE_PARAM_ID,
    triggers_pre_parameter_change_hook=False,
    triggers_post_parameter_change_hook=False,
)

INACTIVITY_FEE_INCOME_ACCOUNT_PARAM_ID = "&{inactivity_fee_income_account}"
INACTIVITY_FEE_INCOME_ACCOUNT_PARAM = ExpectedParameter(
    id=INACTIVITY_FEE_INCOME_ACCOUNT_PARAM_ID,
    triggers_pre_parameter_change_hook=False,
    triggers_post_parameter_change_hook=False,
)

INACTIVITY_FEE_PARTIAL_FEE_ENABLED_PARAM_ID = "&{partial_inactivity_fee_enabled}"
INACTIVITY_FEE_PARTIAL_FEE_ENABLED_PARAM = ExpectedParameter(
    id=INACTIVITY_FEE_PARTIAL_FEE_ENABLED_PARAM_ID,
    triggers_pre_parameter_change_hook=False,
    triggers_post_parameter_change_hook=False,
)

INACTIVITY_FEE_APPLICATION_DAY_PARAM_ID = "&{inactivity_fee_application_day}"
INACTIVITY_FEE_APPLICATION_DAY_PARAM = ExpectedParameter(
    id=INACTIVITY_FEE_APPLICATION_DAY_PARAM_ID,
    triggers_pre_parameter_change_hook=False,
    triggers_post_parameter_change_hook=False,
)

INACTIVITY_FEE_APPLICATION_TIME_PARAM_ID = "&{inactivity_fee_application_time}"
INACTIVITY_FEE_APPLICATION_TIME_PARAM = ExpectedParameter(
    id=INACTIVITY_FEE_APPLICATION_TIME_PARAM_ID,
    triggers_pre_parameter_change_hook=False,
    triggers_post_parameter_change_hook=False,
)

expected_parameters = [
    INACTIVITY_FLAGS_PARAM,
    INACTIVITY_FEE_PARAM,
    INACTIVITY_FEE_INCOME_ACCOUNT_PARAM,
    INACTIVITY_FEE_PARTIAL_FEE_ENABLED_PARAM,
    INACTIVITY_FEE_APPLICATION_DAY_PARAM,
    INACTIVITY_FEE_APPLICATION_TIME_PARAM,
    denomination_module.DENOMINATION_PARAM,
]


INACTIVITY_FEE_POF_ID = "inactivity_fee_pof"
INACTIVITY_FEE_POF = ParametersObservationFetcher(
    fetcher_id=INACTIVITY_FEE_POF_ID,
    at=DefinedDateTime.EFFECTIVE_DATETIME,
    filter=ParametersFilter(parameter_ids=[p.id for p in expected_parameters]),
)

INACTIVITY_FOF_ID = "inactivity_flags_fetcher"
INACTIVITY_FOF = FlagsObservationFetcher(
    fetcher_id=INACTIVITY_FOF_ID,
    at=DefinedDateTime.EFFECTIVE_DATETIME,
)

data_fetchers = [
    fetchers.ALL_BALANCES_ET_BOF,
    INACTIVITY_FEE_POF,
    INACTIVITY_FOF,
]

event_types = [
    SmartContractEventType(name=APPLICATION_EVENT),
]

InactivityFeeFetchersConfig = NamedTuple(
    "InactivityFeeFetchersConfig",
    [
        ("param_fetcher_id", str),
        ("flags_fetcher_id", str),
        ("denomination_param_id", str),
    ],
)
DEFAULT_INACTIVITY_FEE_FETCHERS_CONFIG = InactivityFeeFetchersConfig(
    param_fetcher_id=INACTIVITY_FEE_POF_ID,
    flags_fetcher_id=INACTIVITY_FOF_ID,
    denomination_param_id=denomination_module.DENOMINATION_PARAM.id,
)


def get_parameters(
    vault: SmartContractVault, param_fetcher_id: str = INACTIVITY_FEE_POF_ID
) -> dict[str, datetime | Decimal | str | None]:
    """Retrieves configuration parameters for the inactivity fee feature.

    Args:
        vault: The SmartContractVault instance to query.
        param_fetcher_id: The unique identifier for the parameter fetcher.
            Defaults to `INACTIVITY_FEE_POF_ID`.

    Returns:
        Parameters for the inactivity fee feature.
    """
    return vault.get_parameters_observation(fetcher_id=param_fetcher_id).parameters


def _append_to_state(
    state: state_utils.SmartContractState,
    balance_fetcher_id: str = fetchers.ALL_BALANCES_ET_BOF_ID,
    param_fetcher_id: str = INACTIVITY_FEE_POF_ID,
) -> state_utils.SmartContractState:
    """Updates the contract state with live balances and specific parameter observations.

    Args:
        state: The current state of the smart contract, containing the vault object.
        balance_fetcher_id: The ID of the fetcher used to retrieve balances.
            Defaults to `common_fetchers.ALL_BALANCES_ET_BOF_ID`.
        param_fetcher_id: The ID of the fetcher used to retrieve parameters.
            Defaults to `INACTIVITY_FEE_POF_ID`.

    Returns:
        A new state object containing the appended balances and parameters.
    """
    return state_utils.append_to_state(
        state=state,
        parameters=get_parameters(state.vault, param_fetcher_id),
        balances=state.vault.get_balances_observation(fetcher_id=balance_fetcher_id).balances,
    )


def get_scheduled_events(
    state: state_utils.SmartContractState,
    reference_datetime: datetime | None = None,
    fetchers_config: InactivityFeeFetchersConfig = DEFAULT_INACTIVITY_FEE_FETCHERS_CONFIG,
) -> dict[str, ScheduledEvent]:
    """Get scheduled event for inactivity fee application. Uses application schedule parameters.

    Args:
        state: The current state of the smart contract.
        reference_datetime: The reference datetime from which the next scheduled event is calculated.
        fetchers_config: Configuration for the fetchers used to retrieve parameters.

    Returns:
        The scheduled events for the inactivity fee.
    """
    # Don't use _append_to_state here because it attempts to fetch balances, which is forbidden
    # in the activation hook, which is where this function gets called.
    state = state_utils.append_to_state(
        state=state,
        parameters=get_parameters(state.vault, fetchers_config.param_fetcher_id),
    )

    schedule_param_ids = {
        INACTIVITY_FEE_APPLICATION_DAY_PARAM.id,
        INACTIVITY_FEE_APPLICATION_TIME_PARAM.id,
    }

    rejection = state_utils.check_parameters_exist(state=state, param_ids=schedule_param_ids)
    assert rejection is None, rejection

    inactivity_fee_application_time_str: str = state.parameters[  # type: ignore
        INACTIVITY_FEE_APPLICATION_TIME_PARAM.id
    ]
    inactivity_fee_application_time: date_and_time.Time = date_and_time.parse_time_str(
        inactivity_fee_application_time_str
    )

    day = int(state.parameters[INACTIVITY_FEE_APPLICATION_DAY_PARAM.id])  # type: ignore

    if reference_datetime is None:
        return {
            APPLICATION_EVENT: ScheduledEvent(
                start_datetime=state.effective_datetime,
                expression=ScheduleExpression(
                    day=day,
                    hour=inactivity_fee_application_time.hour,
                    minute=inactivity_fee_application_time.minute,
                    second=inactivity_fee_application_time.second,
                ),
            )
        }

    next_datetime = schedule_utils.get_next_schedule_date(
        start_date=reference_datetime,
        schedule_frequency=schedule_utils.MONTHLY,
        intended_day=day,
    )

    return {
        APPLICATION_EVENT: ScheduledEvent(
            start_datetime=reference_datetime,
            expression=ScheduleExpression(
                day=next_datetime.day,
                month=next_datetime.month,
                hour=inactivity_fee_application_time.hour,
                minute=inactivity_fee_application_time.minute,
                second=inactivity_fee_application_time.second,
            ),
        )
    }


def is_account_inactive(
    vault: SmartContractVault,
    inactivity_flags: list[str],
    flags_fetcher_id: str = INACTIVITY_FOF_ID,
) -> bool:
    """Checks if the account has any of the specified inactivity flags applied.

    Args:
        vault: The SmartContractVault instance to query.
        inactivity_flags: List of flag IDs that indicate inactivity.
        flags_fetcher_id: The ID of the fetcher used to retrieve flags.

    Returns:
        True if any of the specified flags are active on the account, False otherwise.
    """
    flags_observation = vault.get_flags_observation(fetcher_id=flags_fetcher_id)
    if not flags_observation:
        return False

    return any(flags_observation.flags.get(flag_id) for flag_id in inactivity_flags)


def _are_inactivity_partial_payments_enabled(
    state: state_utils.SmartContractState,
) -> bool:
    """Checks if partial inactivity fee collection is enabled.

    Args:
        state: The current state of the smart contract.

    Returns:
        True if partial fee collection is enabled, False otherwise.
    """
    return common_utils.str_to_bool(
        str(state.parameters.get(INACTIVITY_FEE_PARTIAL_FEE_ENABLED_PARAM.id, "False"))
    )


PARTIAL_FEE_DETAILS = deposit_interfaces.PartialFeeCollection(
    outstanding_fee_address=OUTSTANDING_INACTIVITY_FEE_TRACKER,
    fee_type="Partial Inactivity Fee",
    internal_account_parameter_id=INACTIVITY_FEE_INCOME_ACCOUNT_PARAM.id,
)


def schedule_logic(
    state: state_utils.SmartContractState,
    account_type: str,
    fetchers_config: InactivityFeeFetchersConfig = DEFAULT_INACTIVITY_FEE_FETCHERS_CONFIG,
    available_balance_feature: deposit_interfaces.AvailableBalance | None = None,
) -> common_tuples.ScheduleLogicResult:
    """Consolidates inactivity fees and updates the schedule.

    :param state: the SmartContractState containing the vault and balances
    :param account_type: the account type used to apply inactivity fee
    :param fetchers_config: Config for fetcher IDs
    :param available_balance_feature: Interface to calculate the available balance for partial fees.
    :return: the inactivity fee custom instructions and any update event directive
    """
    state = _append_to_state(state=state, param_fetcher_id=fetchers_config.param_fetcher_id)

    custom_instructions = apply_fees(
        state=state,
        account_type=account_type,
        fetchers_config=fetchers_config,
        available_balance_feature=available_balance_feature,
    )

    event_type_directives: list[UpdateAccountEventTypeDirective] = []
    if event_directive := update_next_schedule_execution(state=state):
        event_type_directives.append(event_directive)

    return common_tuples.ScheduleLogicResult(
        custom_instructions=custom_instructions,
        event_type_directives=event_type_directives,
        notification_directives=[],
    )


def apply_fees(
    state: state_utils.SmartContractState,
    account_type: str,
    fetchers_config: InactivityFeeFetchersConfig = DEFAULT_INACTIVITY_FEE_FETCHERS_CONFIG,
    available_balance_feature: deposit_interfaces.AvailableBalance | None = None,
) -> list[CustomInstruction]:
    """Applies the inactivity fee if the account has an inactivity flag.

    Args:
        state: The current state of the smart contract.
        account_type: The type of the account (for GL impact details).
        fetchers_config: Configuration for the fetchers used to retrieve parameters and flags.
        available_balance_feature: Interface to calculate the available balance for partial fees.

    Returns:
        The result of the fee application, including instructions and any rejections.
    """
    state = _append_to_state(state=state, param_fetcher_id=fetchers_config.param_fetcher_id)

    rejection = state_utils.check_parameters_exist(
        state,
        {
            fetchers_config.denomination_param_id,
            INACTIVITY_FEE_PARAM.id,
            INACTIVITY_FEE_INCOME_ACCOUNT_PARAM.id,
            INACTIVITY_FLAGS_PARAM.id,
        },
    )
    assert rejection is None, rejection

    inactivity_fee_amount = Decimal(state.parameters[INACTIVITY_FEE_PARAM.id])  # type: ignore

    if inactivity_fee_amount <= 0:
        return []

    inactivity_flags_param = str(state.parameters[INACTIVITY_FLAGS_PARAM.id])
    inactivity_flags = loads(inactivity_flags_param)

    if not is_account_inactive(state.vault, inactivity_flags, fetchers_config.flags_fetcher_id):
        return []

    denomination: str = str(state.parameters[fetchers_config.denomination_param_id])
    inactivity_fee_income_account: str = str(
        state.parameters[INACTIVITY_FEE_INCOME_ACCOUNT_PARAM.id]
    )

    fee_instructions = [
        CustomInstruction(
            postings=posting_utils.create_postings(
                amount=inactivity_fee_amount,
                debit_account=state.vault.account_id,
                credit_account=inactivity_fee_income_account,
                denomination=denomination,
            ),
            value_datetime=state.effective_datetime,
            instruction_details=posting_utils.standard_instruction_details(
                description="Monthly Inactivity Fee Application",
                event_type=APPLICATION_EVENT,
                gl_impacted=True,
                account_type=account_type,
            ),
            override_all_restrictions=True,
        )
    ]

    if _are_inactivity_partial_payments_enabled(state):
        return partial_fee.charge_partial_fee(
            state=state,
            fee_custom_instruction=fee_instructions[0],
            fee_details=PARTIAL_FEE_DETAILS,
            available_balance_feature=available_balance_feature,
        )
    else:
        return fee_instructions


def update_next_schedule_execution(
    state: state_utils.SmartContractState,
) -> UpdateAccountEventTypeDirective | None:
    """Update next scheduled execution.

    :param state: SmartContractState to retrieve inactivity fee application params
    :return: optional update event directive
    """

    new_schedule = get_scheduled_events(
        state=state,
        reference_datetime=state.effective_datetime,
    )

    return UpdateAccountEventTypeDirective(
        event_type=APPLICATION_EVENT,
        expression=new_schedule[APPLICATION_EVENT].expression,
    )
