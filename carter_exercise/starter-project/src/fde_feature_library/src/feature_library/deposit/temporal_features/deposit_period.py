__smart_contract_feature__ = True

# standard libs
from datetime import datetime
from decimal import Decimal
from typing import NamedTuple
from zoneinfo import ZoneInfo

from dateutil.relativedelta import relativedelta

# features
import feature_library.common.balance_utils as balance_utils
import feature_library.common.denomination as denomination
import feature_library.common.posting_utils as posting_utils
import feature_library.common.schedule_utils as schedule_utils
import feature_library.common.state_utils as state_utils

# contracts api
from contracts_api import (
    AccountNotificationDirective,
    Attribute,
    AttributeDateTimeType,
    DefinedDateTime,
    ExpectedParameter,
    ParametersFilter,
    ParametersObservationFetcher,
    Rejection,
    RejectionReason,
    ScheduledEvent,
    SmartContractEventType,
)

# inception sdk
from inception_sdk.vault.contracts.extensions.contracts_api_extensions import SmartContractVault

# Number of permitted deposit enumeration constants
SINGLE = "single"
UNLIMITED = "unlimited"

# notifications
DEPOSIT_PERIOD_END_SUFFIX = "_DEPOSIT_PERIOD_END"
# Schedule event names
DEPOSIT_PERIOD_END_EVENT = "DEPOSIT_PERIOD_END"

# parameters
DEPOSIT_PERIOD_PARAM_ID = "&{deposit_period}"
DEPOSIT_PERIOD_PARAM = ExpectedParameter(
    id=DEPOSIT_PERIOD_PARAM_ID,
    triggers_pre_parameter_change_hook=False,
    triggers_post_parameter_change_hook=False,
)

NUMBER_OF_PERMITTED_DEPOSITS_PARAM_ID = "&{number_of_permitted_deposits}"
NUMBER_OF_PERMITTED_DEPOSITS_PARAM = ExpectedParameter(
    id=NUMBER_OF_PERMITTED_DEPOSITS_PARAM_ID,
    triggers_pre_parameter_change_hook=False,
    triggers_post_parameter_change_hook=False,
)

# Attributes
DEPOSIT_PERIOD_END_DATE_ATTR_ID = "deposit_period_end_date"
DEPOSIT_PERIOD_END_DATE_ATTRIBUTE = Attribute(
    name=DEPOSIT_PERIOD_END_DATE_ATTR_ID,
    data_type=AttributeDateTimeType(),
)

# Fetchers
DEPOSIT_PERIOD_PARAMS_ET_POF_ID = "deposit_period_params_et_pof"
DEPOSIT_PERIOD_PARAMS_ET_POF = ParametersObservationFetcher(
    fetcher_id=DEPOSIT_PERIOD_PARAMS_ET_POF_ID,
    at=DefinedDateTime.EFFECTIVE_DATETIME,
    filter=ParametersFilter(
        parameter_ids=[
            DEPOSIT_PERIOD_PARAM_ID,
            NUMBER_OF_PERMITTED_DEPOSITS_PARAM_ID,
        ]
    ),
)

expected_parameters = [
    DEPOSIT_PERIOD_PARAM,
    NUMBER_OF_PERMITTED_DEPOSITS_PARAM,
]

data_fetchers = [
    DEPOSIT_PERIOD_PARAMS_ET_POF,
]

# Config
DepositPeriodFetchersConfig = NamedTuple(
    "DepositPeriodFetchersConfig",
    [
        ("param_fetcher_id", str),
        ("deposit_period_param_id", str),
        ("number_of_permitted_deposits", str),
        ("denomination_param_id", str),
    ],
)

DEFAULT_FETCHERS_CONFIG = DepositPeriodFetchersConfig(
    param_fetcher_id=DEPOSIT_PERIOD_PARAMS_ET_POF_ID,
    deposit_period_param_id=DEPOSIT_PERIOD_PARAM_ID,
    number_of_permitted_deposits=NUMBER_OF_PERMITTED_DEPOSITS_PARAM_ID,
    denomination_param_id=denomination.DENOMINATION_PARAM_ID,
)

UTC = ZoneInfo("UTC")


def get_parameters(
    vault: SmartContractVault, fetcher_id: str = DEPOSIT_PERIOD_PARAMS_ET_POF_ID
) -> dict[str, str | datetime | Decimal | None]:
    """Retrieves feature-specific parameters from the vault.

    Args:
        vault: The vault object to query for observations.
        fetcher_id: The ID of the parameter observation fetcher.

    Returns:
        dict[str, str | datetime | Decimal | None]: A dictionary of parameter values.
    """
    return vault.get_parameters_observation(fetcher_id=fetcher_id).parameters


def _append_to_state(
    state: state_utils.SmartContractState,
    fetchers_config: DepositPeriodFetchersConfig = DEFAULT_FETCHERS_CONFIG,
) -> state_utils.SmartContractState:
    """Appends feature-specific parameters and balances to the state.

    Args:
        state: The current state of the smart contract.
        fetchers_config: Configuration for the fetchers.

    Returns:
        state_utils.SmartContractState: The updated state object.
    """

    return state_utils.append_to_state(
        state=state,
        parameters=get_parameters(state.vault, fetchers_config.param_fetcher_id),
    )


def notification_type(*, product_name: str) -> str:
    """Returns a notification type.

    Args:
        product_name: The product name.

    Returns:
        str: notification type.
    """
    return f"{product_name.upper()}{DEPOSIT_PERIOD_END_SUFFIX}"


def event_types(*, product_name: str) -> list[SmartContractEventType]:
    """Returns a list of event types for the feature.

    Args:
        product_name: The name of the product.

    Returns:
        list[SmartContractEventType]: A list of SmartContractEventType objects.
    """
    return [
        SmartContractEventType(
            name=DEPOSIT_PERIOD_END_EVENT,
            scheduler_tag_ids=[f"{product_name.upper()}_{DEPOSIT_PERIOD_END_EVENT}_AST"],
        )
    ]


def get_scheduled_events(
    *,
    state: state_utils.SmartContractState,
    fetchers_config: DepositPeriodFetchersConfig = DEFAULT_FETCHERS_CONFIG,
) -> dict[str, ScheduledEvent]:
    """Creates execution schedules for the deposit period end.

    Args:
        state: The current state of the smart contract.
        fetchers_config: Configuration for the fetchers.

    Returns:
        dict[str, ScheduledEvent]: A dictionary of scheduled events.
    """
    state = _append_to_state(state, fetchers_config)

    rejection = state_utils.check_parameters_exist(state, {fetchers_config.deposit_period_param_id})
    assert rejection is None, rejection

    deposit_period_end_datetime = get_deposit_period_end_datetime(state=state)
    scheduled_event = ScheduledEvent(
        start_datetime=deposit_period_end_datetime - relativedelta(seconds=1),
        expression=schedule_utils.one_off_schedule_expression(
            schedule_datetime=deposit_period_end_datetime
        ),
        end_datetime=deposit_period_end_datetime,
    )
    return {DEPOSIT_PERIOD_END_EVENT: scheduled_event}


def validate(
    *,
    state: state_utils.SmartContractState,
    posting_instructions: posting_utils.PostingInstructionListAlias,
    fetchers_config: DepositPeriodFetchersConfig = DEFAULT_FETCHERS_CONFIG,
) -> Rejection | None:
    """Validates proposed postings against the deposit period.

    Args:
        state: The current state of the smart contract.
        posting_instructions: A list of proposed posting instructions.
        fetchers_config: Configuration for the fetchers.

    Returns:
        Rejection | None: A rejection if validation fails, otherwise None.
    """
    state = _append_to_state(state, fetchers_config)

    param_ids = {
        fetchers_config.deposit_period_param_id,
        fetchers_config.number_of_permitted_deposits,
        fetchers_config.denomination_param_id,
    }
    rejection = state_utils.check_parameters_exist(state, param_ids)
    assert rejection is None, rejection

    denomination: str = state.parameters[fetchers_config.denomination_param_id]  # type: ignore
    deposit_proposed_amount: Decimal = balance_utils.get_current_net_balance(
        balances=posting_utils.get_posting_instructions_balances(
            posting_instructions=posting_instructions
        ),
        denomination=denomination,
    ).credit

    if deposit_proposed_amount > Decimal("0"):
        # reject deposits after deposit period
        if not is_within_deposit_period(state=state):
            return Rejection(
                message="No deposits are allowed after the deposit period end datetime.",
                reason_code=RejectionReason.AGAINST_TNC,
            )

        # reject multiple deposits when only single is allowed
        number_of_permitted_deposits: str = state.parameters[NUMBER_OF_PERMITTED_DEPOSITS_PARAM_ID]  # type: ignore

        if number_of_permitted_deposits == SINGLE:
            credit_default_balance: Decimal = balance_utils.get_current_net_balance(
                balances=state.balances, denomination=denomination
            ).credit

            if credit_default_balance > Decimal(0):
                return Rejection(
                    message="Only a single deposit is allowed.",
                    reason_code=RejectionReason.AGAINST_TNC,
                )

    return None


def schedule_logic(
    *,
    state: state_utils.SmartContractState,
    product_name: str,
    fetchers_config: DepositPeriodFetchersConfig = DEFAULT_FETCHERS_CONFIG,
) -> list[AccountNotificationDirective]:
    """Executes logic for the deposit period end schedule.

    Args:
        state: The current state of the smart contract.
        product_name: The product name for notification types.
        fetchers_config: Configuration for the fetchers.

    Returns:
        list[AccountNotificationDirective]: A list of account notification directives.
    """
    state = _append_to_state(state, fetchers_config)

    rejection = state_utils.check_parameters_exist(state, {fetchers_config.denomination_param_id})
    assert rejection is None, rejection

    denomination: str = state.parameters[fetchers_config.denomination_param_id]  # type: ignore

    net_balance: Decimal = balance_utils.net_credit(
        bal=balance_utils.get_current_net_balance(
            balances=state.balances, denomination=denomination
        )
    )

    if net_balance == Decimal(0):
        return [
            AccountNotificationDirective(
                notification_type=notification_type(product_name=product_name),
                notification_details={
                    "account_id": state.vault.account_id,
                    "deposit_balance": str(net_balance),
                    "deposit_period_end_datetime": str(state.effective_datetime),
                    "reason": "Close account due to lack of deposits at the end of deposit period",
                },
            )
        ]

    return []


def get_deposit_period_end_datetime(*, state: state_utils.SmartContractState) -> datetime:
    """Calculates and returns the deposit period end datetime.

    The end datetime is the start of the day (00:00:00) after the deposit period ends,
    calculated from the activation date.

    Args:
        state: The current state of the smart contract.

    Returns:
        datetime: The datetime when the deposit period ends.
    """
    rejection = state_utils.check_parameters_exist(state, {DEPOSIT_PERIOD_PARAM_ID})
    assert rejection is None, rejection

    account_activation_datetime: datetime = state.vault.get_account_activation_datetime()
    deposit_period: int = int(state.parameters[DEPOSIT_PERIOD_PARAM_ID])  # type: ignore

    # Returns the start of the day (00:00:00) after the deposit period has elapsed
    return account_activation_datetime.astimezone(state.vault.events_timezone).replace(
        hour=0, minute=0, second=0, microsecond=0
    ) + relativedelta(days=deposit_period)


def is_within_deposit_period(*, state: state_utils.SmartContractState) -> bool:
    """Determines whether the effective datetime is within the deposit period.

    Args:
        state: The current state of the smart contract.

    Returns:
        bool: True if within the deposit period, otherwise False.
    """
    return state.effective_datetime <= get_deposit_period_end_datetime(state=state)
