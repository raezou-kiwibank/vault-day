# CBF: CPP-1913
from zoneinfo import ZoneInfo

__smart_contract_feature__ = True

# standard libs
from datetime import datetime
from decimal import Decimal
from typing import NamedTuple

from dateutil.relativedelta import relativedelta

# features
import feature_library.common.accrual_utils as accrual_utils
import feature_library.common.balance_utils as balance_utils
import feature_library.common.denomination as denomination_module
import feature_library.common.fetchers as fetchers
import feature_library.common.posting_utils as posting_utils
import feature_library.common.schedule_utils as schedule_utils
import feature_library.common.state_utils as state_utils
import feature_library.common.tuples as common_tuples
import feature_library.common.utils as utils
import feature_library.deposit.addresses as deposit_addresses
import feature_library.deposit.interest.interest_accrual as interest_accrual

# contracts api
from contracts_api import (
    DEFAULT_ADDRESS,
    CustomInstruction,
    DefinedDateTime,
    ExpectedParameter,
    ParametersFilter,
    ParametersObservationFetcher,
    ScheduledEvent,
    SmartContractEventType,
    UpdateAccountEventTypeDirective,
)

# inception sdk
from inception_sdk.vault.contracts.extensions.contracts_api_extensions import SmartContractVault

UTC = ZoneInfo("UTC")

# Event
APPLICATION_EVENT = "APPLY_INTEREST"

INTEREST_APPLICATION_PREFIX = "interest_application"

# Parameters
INTEREST_APPLICATION_DAY_PARAM_ID = "&{interest_application_day}"
INTEREST_APPLICATION_DAY_PARAM = ExpectedParameter(
    id=INTEREST_APPLICATION_DAY_PARAM_ID,
    triggers_pre_parameter_change_hook=False,
    triggers_post_parameter_change_hook=False,
)

INTEREST_APPLICATION_FREQUENCY_PARAM_ID = "&{interest_application_frequency}"
INTEREST_APPLICATION_FREQUENCY_PARAM = ExpectedParameter(
    id=INTEREST_APPLICATION_FREQUENCY_PARAM_ID,
    triggers_pre_parameter_change_hook=False,
    triggers_post_parameter_change_hook=False,
)

INTEREST_APPLICATION_TIME_PARAM_ID = "&{interest_application_time}"
INTEREST_APPLICATION_TIME_PARAM = ExpectedParameter(
    id=INTEREST_APPLICATION_TIME_PARAM_ID,
    triggers_pre_parameter_change_hook=False,
    triggers_post_parameter_change_hook=False,
)

APPLICATION_PRECISION_PARAM_ID = "&{application_precision}"
APPLICATION_PRECISION_PARAM = ExpectedParameter(
    id=APPLICATION_PRECISION_PARAM_ID,
    triggers_pre_parameter_change_hook=False,
    triggers_post_parameter_change_hook=False,
)

INTEREST_PAID_ACCOUNT_PARAM_ID = "&{interest_paid_account}"
INTEREST_PAID_ACCOUNT_PARAM = ExpectedParameter(
    id=INTEREST_PAID_ACCOUNT_PARAM_ID,
    triggers_pre_parameter_change_hook=False,
    triggers_post_parameter_change_hook=False,
)

INTEREST_RECEIVED_ACCOUNT_PARAM_ID = "&{interest_received_account}"
INTEREST_RECEIVED_ACCOUNT_PARAM = ExpectedParameter(
    id=INTEREST_RECEIVED_ACCOUNT_PARAM_ID,
    triggers_pre_parameter_change_hook=False,
    triggers_post_parameter_change_hook=False,
)

expected_parameters = [
    INTEREST_APPLICATION_DAY_PARAM,
    INTEREST_APPLICATION_FREQUENCY_PARAM,
    INTEREST_APPLICATION_TIME_PARAM,
    APPLICATION_PRECISION_PARAM,
    INTEREST_PAID_ACCOUNT_PARAM,
    INTEREST_RECEIVED_ACCOUNT_PARAM,
    denomination_module.DENOMINATION_PARAM,
]

# Fetchers
INTEREST_APPLICATION_PARAMS_ET_POF_ID = "interest_application_params_et_pof"
INTEREST_APPLICATION_PARAMS_ET_POF = ParametersObservationFetcher(
    fetcher_id=INTEREST_APPLICATION_PARAMS_ET_POF_ID,
    at=DefinedDateTime.EFFECTIVE_DATETIME,
    filter=ParametersFilter(parameter_ids=[p.id for p in expected_parameters]),
)

data_fetchers = [
    fetchers.ALL_BALANCES_ET_BOF,
    INTEREST_APPLICATION_PARAMS_ET_POF,
]

# Config
InterestApplicationFetchersConfig = NamedTuple(
    "InterestApplicationFetchersConfig",
    [
        ("balance_fetcher_id", str | None),
        ("param_fetcher_id", str),
        ("denomination_param_id", str),
    ],
)

AccrualAccountFetchersConfig = NamedTuple(
    "AccrualAccountFetchersConfig",
    [
        ("balance_fetcher_id", str | None),
        ("param_fetcher_id", str),
        ("accrued_payable_acc_param_id", str),
        ("accrued_receivable_acc_param_id", str),
    ],
)


DEFAULT_APPLICATION_FETCHERS_CONFIG = InterestApplicationFetchersConfig(
    balance_fetcher_id=fetchers.ALL_BALANCES_ET_BOF_ID,
    param_fetcher_id=INTEREST_APPLICATION_PARAMS_ET_POF_ID,
    denomination_param_id=denomination_module.DENOMINATION_PARAM_ID,
)

DEFAULT_ACCRUAL_ACC_FETCHERS_CONFIG = AccrualAccountFetchersConfig(
    balance_fetcher_id=None,
    param_fetcher_id=interest_accrual.INTEREST_ACCRUAL_PARAMS_ET_POF_ID,
    accrued_payable_acc_param_id=interest_accrual.ACCRUED_INTEREST_PAYABLE_ACCOUNT_PARAM_ID,
    accrued_receivable_acc_param_id=interest_accrual.ACCRUED_INTEREST_RECEIVABLE_ACCOUNT_PARAM_ID,
)


def event_types(product_name: str) -> list[SmartContractEventType]:
    """Returns a list of SmartContractEventTypes for the interest application feature.

    :param product_name: The name of the product, used to prefix the scheduler tag.
    :return: A list containing the SmartContractEventType for interest application.
    """
    return [
        SmartContractEventType(
            name=APPLICATION_EVENT,
            scheduler_tag_ids=[f"{product_name.upper()}_{APPLICATION_EVENT}_AST"],
        )
    ]


def get_parameters(
    vault: SmartContractVault, param_fetcher_id: str = INTEREST_APPLICATION_PARAMS_ET_POF_ID
) -> dict[str, datetime | Decimal | str | None]:
    """Retrieves parameters for the interest application feature from the vault.

    :param vault: The SmartContractVault object to fetch parameters from.
    :param param_fetcher_id: The ID of the parameter fetcher to use.
    :return: A dictionary of parameters.
    """
    return vault.get_parameters_observation(fetcher_id=param_fetcher_id).parameters


def _append_to_state(
    state: state_utils.SmartContractState,
    fetchers_config: (
        InterestApplicationFetchersConfig | AccrualAccountFetchersConfig
    ) = DEFAULT_APPLICATION_FETCHERS_CONFIG,
) -> state_utils.SmartContractState:
    """Appends balances and parameters to the SmartContractState based on the fetchers config.

    :param state: The current SmartContractState.
    :param fetchers_config: Configuration containing the fetcher IDs for balances and parameters.
    :return: The updated SmartContractState with appended balances and parameters.
    """
    balances = (
        state.vault.get_balances_observation(fetcher_id=fetchers_config.balance_fetcher_id).balances
        if fetchers_config.balance_fetcher_id
        else None
    )
    return state_utils.append_to_state(
        state=state,
        parameters=get_parameters(state.vault, fetchers_config.param_fetcher_id),
        balances=balances,
    )


def get_scheduled_events(
    state: state_utils.SmartContractState,
    reference_datetime: datetime | None = None,
    fetchers_config: InterestApplicationFetchersConfig = DEFAULT_APPLICATION_FETCHERS_CONFIG,
) -> dict[str, ScheduledEvent]:
    """Creates execution schedules for interest application.

    :param state: SmartContractState to retrieve application frequency and schedule params
    :param fetchers_config: Config for fetcher IDs
    :return: ScheduledEventsResult containing interest application scheduled events
    """
    reference_datetime = reference_datetime if reference_datetime else state.effective_datetime

    # Can't fetch balances in activation hook so use fetchers config without balances
    fetchers_config_no_balances = InterestApplicationFetchersConfig(
        balance_fetcher_id=None,
        param_fetcher_id=fetchers_config.param_fetcher_id,
        denomination_param_id=fetchers_config.denomination_param_id,
    )
    state = _append_to_state(state=state, fetchers_config=fetchers_config_no_balances)

    param_ids = {
        INTEREST_APPLICATION_FREQUENCY_PARAM_ID,
        INTEREST_APPLICATION_DAY_PARAM_ID,
        INTEREST_APPLICATION_TIME_PARAM_ID,
    }

    rejection = state_utils.check_parameters_exist(state=state, param_ids=param_ids)
    assert rejection is None, rejection

    application_frequency: str = state.parameters[INTEREST_APPLICATION_FREQUENCY_PARAM_ID]  # type: ignore
    application_day = int(state.parameters[INTEREST_APPLICATION_DAY_PARAM_ID])  # type: ignore
    application_time: str = state.parameters[INTEREST_APPLICATION_TIME_PARAM_ID]  # type: ignore

    start_datetime = start_datetime = reference_datetime.astimezone(
        state.vault.events_timezone
    ).replace(hour=0, minute=0, second=0, microsecond=0)

    next_datetime = schedule_utils.get_next_schedule_date(
        start_date=start_datetime,
        schedule_frequency=application_frequency,
        intended_day=application_day,
    )

    # TODO: opened INC-8478 to investigate the issue with year=None
    schedule_expression = schedule_utils.get_schedule_expression_from_parameters(
        time=application_time,
        day=next_datetime.day,
        month=next_datetime.month,
        year=(
            None
            if (
                application_frequency == schedule_utils.ANNUALLY
                and (
                    int(next_datetime.month) != 2
                    or (int(next_datetime.month) == 2 and application_day < 29)
                )
            )
            else next_datetime.year
        ),
    )

    # adding a month to start_datetime param to apply interest for the first time
    # on the following year and not on the current one
    # the schedule frequency is quarterly or annually and thus we need to ensure
    # the start datetime is not in the past
    start_delta = (
        relativedelta(months=1)
        if application_frequency == schedule_utils.ANNUALLY
        else relativedelta(days=1)
    )
    scheduled_event = ScheduledEvent(
        start_datetime=start_datetime + start_delta, expression=schedule_expression
    )

    return {APPLICATION_EVENT: scheduled_event}


def schedule_logic(
    state: state_utils.SmartContractState,
    account_type: str = "",
    application_fetchers_config: InterestApplicationFetchersConfig = DEFAULT_APPLICATION_FETCHERS_CONFIG,  # noqa
    accrual_fetchers_config: AccrualAccountFetchersConfig = DEFAULT_ACCRUAL_ACC_FETCHERS_CONFIG,
    interest_types: list[interest_accrual.InterestTypeConfig] | None = None,
) -> common_tuples.ScheduleLogicResult:  # list[CustomInstruction]:
    """Creates the posting instructions to consolidate accrued interest.

    Debit the rounded amount from the customer accrued address and credit the internal account
    Debit the rounded amount from the internal account to the customer applied address

    :param state: the SmartContractState containing the vault and balances
    :param account_type: the account type used to apply interest
    :param fetchers_config: Config for fetcher IDs

    :return: the accrual application posting instructions
    """
    custom_instructions: list[CustomInstruction] = []
    event_type_directives: list[UpdateAccountEventTypeDirective] = []

    state = _append_to_state(state, application_fetchers_config)
    state = _append_to_state(state, accrual_fetchers_config)

    param_ids = {
        APPLICATION_PRECISION_PARAM_ID,
        INTEREST_PAID_ACCOUNT_PARAM_ID,
        INTEREST_RECEIVED_ACCOUNT_PARAM_ID,
        application_fetchers_config.denomination_param_id,
        accrual_fetchers_config.accrued_payable_acc_param_id,
        accrual_fetchers_config.accrued_receivable_acc_param_id,
    }

    rejection = state_utils.check_parameters_exist(state=state, param_ids=param_ids)
    assert rejection is None, rejection

    denomination: str = state.parameters[application_fetchers_config.denomination_param_id]  # type: ignore
    precision: int = int(state.parameters[APPLICATION_PRECISION_PARAM_ID])  # type: ignore
    interest_paid_account: str = state.parameters[INTEREST_PAID_ACCOUNT_PARAM_ID]  # type: ignore
    interest_received_account: str = state.parameters[INTEREST_RECEIVED_ACCOUNT_PARAM_ID]  # type: ignore
    accrued_interest_payable_account: str = state.parameters[
        accrual_fetchers_config.accrued_payable_acc_param_id
    ]  # type: ignore
    accrued_interest_receivable_account: str = state.parameters[
        accrual_fetchers_config.accrued_receivable_acc_param_id
    ]  # type: ignore

    # Map addresses to internal accounts and types
    accrual_configs = [
        # address, accrual internal account, application internal account, is payable
        (
            deposit_addresses.ACCRUED_INTEREST_RECEIVABLE,
            accrued_interest_receivable_account,
            interest_received_account,
            False,
        ),
        (
            deposit_addresses.ACCRUED_INTEREST_PAYABLE,
            accrued_interest_payable_account,
            interest_paid_account,
            True,
        ),
    ]

    # Dynamically discover custom addresses from any provided interest types
    known_addresses = {config[0] for config in accrual_configs}

    for interest_config in interest_types or []:
        interest_type = interest_config.interest_type
        # To discover all possible accrual addresses a feature might use, we probe the
        # interface with dummy accrual amounts representing both directions of money flow.
        receivable_addr = interest_type.get_accrual_receivable_customer_address()
        if receivable_addr not in known_addresses:
            known_addresses.add(receivable_addr)
            accrual_configs.append(
                (
                    receivable_addr,
                    interest_type.get_accrual_payable_internal_account(
                        state=state,
                    ),
                    interest_received_account,
                    False,
                )
            )

        payable_addr = interest_type.get_accrual_payable_customer_address()
        if payable_addr not in known_addresses:
            known_addresses.add(payable_addr)
            accrual_configs.append(
                (
                    payable_addr,
                    interest_type.get_accrual_payable_internal_account(
                        state=state,
                    ),
                    interest_paid_account,
                    True,
                )
            )

    custom_instructions: list[CustomInstruction] = []
    for address, accrual_internal, application_internal, is_payable in accrual_configs:
        custom_instructions.extend(
            _get_application_instructions(
                state=state,
                address=address,
                accrual_internal=accrual_internal,
                application_internal=application_internal,
                denomination=denomination,
                precision=precision,
                account_type=account_type,
                is_payable=is_payable,
            )
        )

    if event_directive := update_next_schedule_execution(state=state):
        event_type_directives.append(event_directive)

    return common_tuples.ScheduleLogicResult(
        custom_instructions=custom_instructions,
        event_type_directives=event_type_directives,
        notification_directives=[],
    )


def _get_application_instructions(
    state: state_utils.SmartContractState,
    address: str,
    accrual_internal: str,
    application_internal: str,
    denomination: str,
    precision: int,
    account_type: str,
    is_payable: bool,
) -> list[CustomInstruction]:
    """Generates the custom posting instructions to apply accrued interest.

    :param state: The SmartContractState containing balances and vault information.
    :param address: The customer account address where interest is accrued.
    :param accrual_internal: The internal account where accrued interest is tracked.
    :param application_internal: The internal account where applied interest is tracked.
    :param denomination: The denomination of the interest being applied.
    :param precision: The number of decimal places to round the applied interest to.
    :param account_type: The account type used in the instruction details.
    :param is_payable: set to True if applying a payable charge, or False for a receivable charge.
    :return: A list of CustomInstructions to apply the interest.
    """
    balance = balance_utils.balance_at_coordinates(state.balances, denomination, address=address)

    if balance == 0:
        return []

    rounded_amount = utils.round_decimal(balance, precision)
    if is_payable:
        return accrual_utils.create_payable_accrual_application_custom_instruction(
            customer_account=state.vault.account_id,
            denomination=denomination,
            application_amount=abs(rounded_amount),
            accrual_amount=abs(balance),
            instruction_details=posting_utils.standard_instruction_details(
                description=f"Apply {rounded_amount} {denomination} interest of "
                f"{balance} rounded to {precision} and "
                f"consolidate {balance} {denomination} to {state.vault.account_id}",
                event_type=APPLICATION_EVENT,
                gl_impacted=True,
                account_type=account_type,
            ),
            accrual_customer_address=address,
            accrual_internal_account=accrual_internal,
            application_customer_address=DEFAULT_ADDRESS,
            application_internal_account=application_internal,
        )
    else:
        return accrual_utils.create_receivable_accrual_application_custom_instruction(
            customer_account=state.vault.account_id,
            denomination=denomination,
            application_amount=abs(rounded_amount),
            accrual_amount=abs(balance),
            instruction_details=posting_utils.standard_instruction_details(
                description=f"Apply {rounded_amount} {denomination} interest of "
                f"{balance} rounded to {precision} and "
                f"consolidate {balance} {denomination} to {state.vault.account_id}",
                event_type=APPLICATION_EVENT,
                gl_impacted=True,
                account_type=account_type,
            ),
            accrual_customer_address=address,
            accrual_internal_account=accrual_internal,
            application_customer_address=DEFAULT_ADDRESS,
            application_internal_account=application_internal,
        )


def update_next_schedule_execution(
    state: state_utils.SmartContractState,
) -> UpdateAccountEventTypeDirective | None:
    """Update next scheduled execution.

    Will update if frequency not monthly or annually with
    intended month not february

    :param state: SmartContractState to retrieve interest application params
    :return: optional update event directive
    """

    rejection = state_utils.check_parameters_exist(
        state=state,
        param_ids={
            INTEREST_APPLICATION_FREQUENCY_PARAM_ID,
            INTEREST_APPLICATION_DAY_PARAM_ID,
        },
    )
    assert rejection is None, rejection

    application_frequency: str = state.parameters.get(INTEREST_APPLICATION_FREQUENCY_PARAM_ID)  # type: ignore

    day = int(state.parameters.get(INTEREST_APPLICATION_DAY_PARAM_ID))  # type: ignore

    # no need to reschedule if annual frequency and application month not february or
    # schedule day < 29 since there's no leap year logic to adapt
    if application_frequency == schedule_utils.ANNUALLY and (
        int(state.effective_datetime.month) != 2
        or (int(state.effective_datetime.month) == 2 and day < 29)
    ):
        return None

    new_schedule = get_scheduled_events(
        state=state,
        reference_datetime=state.effective_datetime,
    )

    return UpdateAccountEventTypeDirective(
        event_type=APPLICATION_EVENT,
        expression=new_schedule[APPLICATION_EVENT].expression,
    )
