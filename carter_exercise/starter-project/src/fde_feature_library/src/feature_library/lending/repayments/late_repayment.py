# Copyright @ 2026 Thought Machine Group Limited. All rights reserved.
__smart_contract_feature__ = True

# standard libs
from datetime import datetime
from decimal import Decimal
from typing import NamedTuple
from zoneinfo import ZoneInfo

# features
import feature_library.common.denomination as denomination
import feature_library.common.posting_utils as posting_utils
import feature_library.common.schedule_utils as schedule_utils
import feature_library.common.state_utils as state_utils
import feature_library.lending.addresses as lending_addresses
import feature_library.lending.interfaces as lending_interfaces

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
)

# inception sdk
from inception_sdk.vault.contracts.extensions.contracts_api_extensions import SmartContractVault

UTC = ZoneInfo("UTC")

# Events
CHECK_LATE_REPAYMENT_EVENT = "CHECK_LATE_REPAYMENT"

# Parameters
LATE_REPAYMENT_FEE_PARAM_ID = "&{late_repayment_fee}"
LATE_REPAYMENT_FEE_PARAM = ExpectedParameter(
    id=LATE_REPAYMENT_FEE_PARAM_ID,
    triggers_pre_parameter_change_hook=False,
    triggers_post_parameter_change_hook=False,
)

LATE_REPAYMENT_FEE_INCOME_ACCOUNT_PARAM_ID = "&{late_repayment_fee_income_account}"
LATE_REPAYMENT_FEE_INCOME_ACCOUNT_PARAM = ExpectedParameter(
    id=LATE_REPAYMENT_FEE_INCOME_ACCOUNT_PARAM_ID,
    triggers_pre_parameter_change_hook=False,
    triggers_post_parameter_change_hook=False,
)

CHECK_LATE_REPAYMENT_TIME_PARAM_ID = "&{check_late_repayment_time}"
CHECK_LATE_REPAYMENT_TIME_PARAM = ExpectedParameter(
    id=CHECK_LATE_REPAYMENT_TIME_PARAM_ID,
    triggers_pre_parameter_change_hook=False,
    triggers_post_parameter_change_hook=False,
)

expected_parameters = [
    LATE_REPAYMENT_FEE_PARAM,
    LATE_REPAYMENT_FEE_INCOME_ACCOUNT_PARAM,
    CHECK_LATE_REPAYMENT_TIME_PARAM,
    denomination.DENOMINATION_PARAM,
]

# Fetchers
LATE_REPAYMENT_POF_ID = "late_repayment_pof"
LATE_REPAYMENT_POF = ParametersObservationFetcher(
    fetcher_id=LATE_REPAYMENT_POF_ID,
    at=DefinedDateTime.EFFECTIVE_DATETIME,
    filter=ParametersFilter(
        parameter_ids=[
            LATE_REPAYMENT_FEE_PARAM_ID,
            LATE_REPAYMENT_FEE_INCOME_ACCOUNT_PARAM_ID,
            CHECK_LATE_REPAYMENT_TIME_PARAM_ID,
        ]
    ),
)

data_fetchers = [LATE_REPAYMENT_POF]

# Config
LateRepaymentFetchersConfig = NamedTuple(
    "LateRepaymentFetchersConfig",
    [
        ("param_fetcher_id", str),
        ("late_repayment_fee_param_id", str),
        ("late_repayment_fee_income_account_param_id", str),
        ("check_late_repayment_time_param_id", str),
        ("denomination_param_id", str),
    ],
)

DEFAULT_FETCHERS_CONFIG = LateRepaymentFetchersConfig(
    param_fetcher_id=LATE_REPAYMENT_POF_ID,
    late_repayment_fee_param_id=LATE_REPAYMENT_FEE_PARAM_ID,
    late_repayment_fee_income_account_param_id=LATE_REPAYMENT_FEE_INCOME_ACCOUNT_PARAM_ID,
    check_late_repayment_time_param_id=CHECK_LATE_REPAYMENT_TIME_PARAM_ID,
    denomination_param_id=denomination.DENOMINATION_PARAM_ID,
)


def get_parameters(
    vault: SmartContractVault, param_fetcher_id: str = LATE_REPAYMENT_POF_ID
) -> dict[str, str | Decimal | datetime | None]:
    """Retrieves configuration parameters for the late repayment feature from the vault.

    Args:
        vault: The vault object containing the parameter observations.
        param_fetcher_id: The ID of the fetcher used to retrieve the late repayment parameters.
            Defaults to `LATE_REPAYMENT_POF_ID`.

    Returns:
        dict[str, str | Decimal | datetime | None]: A dictionary of parameter values keyed by their
        ID.
    """
    return vault.get_parameters_observation(fetcher_id=param_fetcher_id).parameters


def _append_to_state(
    state: state_utils.SmartContractState,
    fetchers_config: LateRepaymentFetchersConfig = DEFAULT_FETCHERS_CONFIG,
) -> state_utils.SmartContractState:
    """Appends late repayment specific parameters to the provided smart contract state.

    Args:
        state: The current state of the smart contract to be augmented.
        fetchers_config: Configuration for the late repayment fetchers, defining which
            parameter IDs to retrieve. Defaults to `DEFAULT_FETCHERS_CONFIG`.

    Returns:
        state_utils.SmartContractState: A new state object containing the original state
            plus the retrieved late repayment parameters.
    """
    return state_utils.append_to_state(
        state=state,
        parameters=get_parameters(state.vault, fetchers_config.param_fetcher_id),
    )


def event_types(product_name: str) -> list[SmartContractEventType]:
    """Returns the list of event types required by the late repayment feature.

    Args:
        product_name: The name of the product using this feature, used to generate
            unique scheduler tag IDs.

    Returns:
        list[SmartContractEventType]: A list containing the `CHECK_LATE_REPAYMENT` event type.
    """
    return [
        SmartContractEventType(
            name=CHECK_LATE_REPAYMENT_EVENT,
            scheduler_tag_ids=[f"{product_name.upper()}_{CHECK_LATE_REPAYMENT_EVENT}_AST"],
        )
    ]


def get_scheduled_events(
    *,
    state: state_utils.SmartContractState,
    start_datetime: datetime,
    skip: bool = False,
    fetchers_config: LateRepaymentFetchersConfig = DEFAULT_FETCHERS_CONFIG,
) -> dict[str, ScheduledEvent]:
    """Generates the schedule for late repayment checks.

    The schedule is initialized to run at the time specified by the
    `check_late_repayment_time` parameter, starting from the day of `start_datetime`.
    The day of the month is determined based on the vault's local timezone.

    Args:
        state: The current state of the smart contract.
        start_datetime: The reference date/time for initializing the schedule.
        skip: If True, the schedule will be created in a skipped state. Defaults to False.
        fetchers_config: Configuration for the late repayment fetchers.
            Defaults to `DEFAULT_FETCHERS_CONFIG`.

    Returns:
        dict[str, ScheduledEvent]: A dictionary containing the `CHECK_LATE_REPAYMENT`
            scheduled event.
    """
    state = _append_to_state(state, fetchers_config)
    rejection = state_utils.check_parameters_exist(
        state, {fetchers_config.check_late_repayment_time_param_id}
    )
    assert rejection is None, rejection

    time_str: str = state.parameters[fetchers_config.check_late_repayment_time_param_id]  # type: ignore

    local_start = start_datetime.astimezone(state.vault.events_timezone)

    return {
        CHECK_LATE_REPAYMENT_EVENT: ScheduledEvent(
            start_datetime=local_start.replace(hour=0, minute=0, second=0),
            expression=schedule_utils.get_schedule_expression_from_parameters(
                time=time_str,
                day=local_start.day,
            ),
            skip=skip,
        )
    }


def schedule_logic(
    *,
    state: state_utils.SmartContractState,
    account_type: str = "",
    check_total_overdue_amount: bool = True,
    repayment_hierarchy_config: lending_interfaces.RepaymentHierarchyConfig,
    fetchers_config: LateRepaymentFetchersConfig = DEFAULT_FETCHERS_CONFIG,
) -> list[CustomInstruction]:
    """Calculates and returns postings to charge a late repayment fee if applicable.

    The fee is charged if:
    1. A positive fee amount is configured in parameters.
    2. There is an outstanding overdue balance (unless `check_total_overdue_amount` is False).

    Args:
        state: The current state of the smart contract, including parameters and balances.
        account_type: An optional account type string for GL accounting purposes.
        check_total_overdue_amount: If True, the fee is only charged if the overdue balance
            is greater than zero. If False, the fee is charged regardless of the overdue
            balance. Defaults to True.
        repayment_hierarchy_config: Configuration defining how to calculate overdue balances.
        fetchers_config: Configuration for the late repayment fetchers.
            Defaults to `DEFAULT_FETCHERS_CONFIG`.

    Returns:
        list[CustomInstruction]: A list containing a single `CustomInstruction` to charge
            the fee if applicable, otherwise an empty list.
    """
    state = _append_to_state(state, fetchers_config)
    param_ids = {
        fetchers_config.late_repayment_fee_param_id,
        fetchers_config.late_repayment_fee_income_account_param_id,
        fetchers_config.denomination_param_id,
    }
    rejection = state_utils.check_parameters_exist(state, param_ids)
    assert rejection is None, rejection

    fee_amount: Decimal = Decimal(state.parameters[fetchers_config.late_repayment_fee_param_id])  # type: ignore

    if fee_amount <= Decimal(0):
        return []

    denomination_value: str = state.parameters[fetchers_config.denomination_param_id]  # type: ignore

    total_overdue_amount = repayment_hierarchy_config.repayment_hierarchy.get_total_overdue_amount(
        state=state, fetchers_config=repayment_hierarchy_config.fetchers_config
    )

    if check_total_overdue_amount and total_overdue_amount <= Decimal(0):
        return []

    late_repayment_fee_income_account: str = state.parameters[
        fetchers_config.late_repayment_fee_income_account_param_id
    ]  # type: ignore

    postings = posting_utils.create_postings(
        amount=fee_amount,
        denomination=denomination_value,
        debit_account=state.vault.account_id,
        debit_address=lending_addresses.PENALTIES,
        credit_account=late_repayment_fee_income_account,
        credit_address=DEFAULT_ADDRESS,
    )

    return [
        CustomInstruction(
            postings=postings,
            instruction_details=posting_utils.standard_instruction_details(
                description="Charge late repayment fee",
                event_type=CHECK_LATE_REPAYMENT_EVENT,
                account_type=account_type,
            ),
        )
    ]
