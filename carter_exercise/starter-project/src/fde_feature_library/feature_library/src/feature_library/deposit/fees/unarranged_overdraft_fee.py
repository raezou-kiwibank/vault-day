# Copyright @ 2026 Thought Machine Group Limited. All rights reserved.
__smart_contract_feature__ = True

# standard libs
from datetime import datetime
from decimal import Decimal
from typing import NamedTuple

from dateutil.relativedelta import relativedelta

# feature library
import feature_library.common.accrual_utils as accrual_utils
import feature_library.common.balance_utils as balance_utils
import feature_library.common.date_and_time as date_and_time
import feature_library.common.denomination as denomination_module
import feature_library.common.fetchers as fetchers
import feature_library.common.posting_utils as posting_utils
import feature_library.common.state_utils as state_utils
import feature_library.deposit.fees.overdraft_limit as overdraft_limit

# contracts api
from contracts_api import (
    DEFAULT_ADDRESS,
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

# inception sdk
from inception_sdk.vault.contracts.extensions.contracts_api_extensions import SmartContractVault

ACCRUAL_EVENT = "ACCRUE_UNARRANGED_OVERDRAFT_FEE"
APPLICATION_EVENT = "APPLY_UNARRANGED_OVERDRAFT_FEE"

# Addresses
OVERDRAFT_FEE_ADDRESS = "UNARRANGED_OVERDRAFT_FEE"

# Parameters
UNARRANGED_OVERDRAFT_FEE_PARAM_ID = "&{unarranged_overdraft_fee}"
UNARRANGED_OVERDRAFT_FEE_PARAM = ExpectedParameter(
    id=UNARRANGED_OVERDRAFT_FEE_PARAM_ID,
    optional=True,
    triggers_pre_parameter_change_hook=False,
    triggers_post_parameter_change_hook=False,
)

UNARRANGED_OVERDRAFT_FEE_CAP_PARAM_ID = "&{unarranged_overdraft_fee_cap}"
UNARRANGED_OVERDRAFT_FEE_CAP_PARAM = ExpectedParameter(
    id=UNARRANGED_OVERDRAFT_FEE_CAP_PARAM_ID,
    optional=True,
    triggers_pre_parameter_change_hook=False,
    triggers_post_parameter_change_hook=False,
)

UNARRANGED_OVERDRAFT_FEE_INCOME_ACCOUNT_PARAM_ID = "&{unarranged_overdraft_fee_income_account}"
UNARRANGED_OVERDRAFT_FEE_INCOME_ACCOUNT_PARAM = ExpectedParameter(
    id=UNARRANGED_OVERDRAFT_FEE_INCOME_ACCOUNT_PARAM_ID,
    optional=True,
    triggers_pre_parameter_change_hook=False,
    triggers_post_parameter_change_hook=False,
)

UNARRANGED_OVERDRAFT_FEE_RECEIVABLE_ACCOUNT_PARAM_ID = (
    "&{unarranged_overdraft_fee_receivable_account}"
)
UNARRANGED_OVERDRAFT_FEE_RECEIVABLE_ACCOUNT_PARAM = ExpectedParameter(
    id=UNARRANGED_OVERDRAFT_FEE_RECEIVABLE_ACCOUNT_PARAM_ID,
    optional=True,
    triggers_pre_parameter_change_hook=False,
    triggers_post_parameter_change_hook=False,
)

UNARRANGED_OVERDRAFT_FEE_ACCRUAL_TIME_PARAM_ID = "&{unarranged_overdraft_fee_accrual_time}"
UNARRANGED_OVERDRAFT_FEE_ACCRUAL_TIME_PARAM = ExpectedParameter(
    id=UNARRANGED_OVERDRAFT_FEE_ACCRUAL_TIME_PARAM_ID,
    triggers_pre_parameter_change_hook=False,
    triggers_post_parameter_change_hook=False,
)

UNARRANGED_OVERDRAFT_FEE_APPLICATION_DAY_PARAM_ID = "&{unarranged_overdraft_fee_application_day}"
UNARRANGED_OVERDRAFT_FEE_APPLICATION_DAY_PARAM = ExpectedParameter(
    id=UNARRANGED_OVERDRAFT_FEE_APPLICATION_DAY_PARAM_ID,
    triggers_pre_parameter_change_hook=False,
    triggers_post_parameter_change_hook=False,
)

UNARRANGED_OVERDRAFT_FEE_APPLICATION_TIME_PARAM_ID = "&{unarranged_overdraft_fee_application_time}"
UNARRANGED_OVERDRAFT_FEE_APPLICATION_TIME_PARAM = ExpectedParameter(
    id=UNARRANGED_OVERDRAFT_FEE_APPLICATION_TIME_PARAM_ID,
    triggers_pre_parameter_change_hook=False,
    triggers_post_parameter_change_hook=False,
)

expected_parameters = [
    UNARRANGED_OVERDRAFT_FEE_PARAM,
    UNARRANGED_OVERDRAFT_FEE_CAP_PARAM,
    UNARRANGED_OVERDRAFT_FEE_INCOME_ACCOUNT_PARAM,
    UNARRANGED_OVERDRAFT_FEE_RECEIVABLE_ACCOUNT_PARAM,
    overdraft_limit.ARRANGED_OVERDRAFT_AMOUNT_PARAM,
    overdraft_limit.UNARRANGED_OVERDRAFT_AMOUNT_PARAM,
    UNARRANGED_OVERDRAFT_FEE_ACCRUAL_TIME_PARAM,
    UNARRANGED_OVERDRAFT_FEE_APPLICATION_DAY_PARAM,
    UNARRANGED_OVERDRAFT_FEE_APPLICATION_TIME_PARAM,
    denomination_module.DENOMINATION_PARAM,
]

UNARRANGED_OVERDRAFT_FEE_POF_ID = "unarranged_overdraft_fee_pof"
UNARRANGED_OVERDRAFT_FEE_POF = ParametersObservationFetcher(
    fetcher_id=UNARRANGED_OVERDRAFT_FEE_POF_ID,
    at=DefinedDateTime.EFFECTIVE_DATETIME,
    filter=ParametersFilter(parameter_ids=[p.id for p in expected_parameters]),
)

data_fetchers = [
    fetchers.ALL_BALANCES_ET_BOF,
    UNARRANGED_OVERDRAFT_FEE_POF,
]

event_types = [
    SmartContractEventType(name=ACCRUAL_EVENT),
    SmartContractEventType(name=APPLICATION_EVENT),
]

UnarrangedOverdraftFeeFetchersConfig = NamedTuple(
    "UnarrangedOverdraftFeeFetchersConfig",
    [
        ("param_fetcher_id", str),
        ("denomination_param_id", str),
        ("eod_balance_fetcher_id", str),
    ],
)
DEFAULT_UNARRANGED_OVERDRAFT_FEE_FETCHERS_CONFIG = UnarrangedOverdraftFeeFetchersConfig(
    param_fetcher_id=UNARRANGED_OVERDRAFT_FEE_POF_ID,
    denomination_param_id=denomination_module.DENOMINATION_PARAM.id,
    eod_balance_fetcher_id=fetchers.ALL_BALANCES_ET_BOF.fetcher_id,
)


def get_parameters(
    vault: SmartContractVault, param_fetcher_id: str = UNARRANGED_OVERDRAFT_FEE_POF_ID
) -> dict[str, datetime | Decimal | str | None]:
    """Retrieves configuration parameters for the unarranged overdraft fee feature.

    Args:
        vault: The SmartContractVault instance to query.
        param_fetcher_id: The unique identifier for the parameter fetcher.
            Defaults to `UNARRANGED_OVERDRAFT_FEE_POF_ID`.

    Returns:
        Parameters for the unarranged overdraft fee feature.
    """
    return vault.get_parameters_observation(fetcher_id=param_fetcher_id).parameters


def _append_to_state(
    state: state_utils.SmartContractState,
    fetchers_config: UnarrangedOverdraftFeeFetchersConfig = (
        DEFAULT_UNARRANGED_OVERDRAFT_FEE_FETCHERS_CONFIG
    ),
    balance_fetcher_id: str = fetchers.ALL_BALANCES_ET_BOF_ID,
) -> state_utils.SmartContractState:
    """Updates the contract state with live balances and specific parameter observations.

    Args:
        state: The current state of the smart contract, containing the vault object.
        fetchers_config: Configuration for the fetchers used to retrieve parameters.
        balance_fetcher_id: The ID of the fetcher used to retrieve balances.
            Defaults to `common_fetchers.ALL_BALANCES_ET_BOF_ID`.

    Returns:
        A new state object containing the appended balances and parameters.
    """
    return state_utils.append_to_state(
        state=state,
        parameters=get_parameters(state.vault, fetchers_config.param_fetcher_id),
        balances=state.vault.get_balances_observation(fetcher_id=balance_fetcher_id).balances,
    )


def get_scheduled_events(
    state: state_utils.SmartContractState,
    fetchers_config: UnarrangedOverdraftFeeFetchersConfig = (
        DEFAULT_UNARRANGED_OVERDRAFT_FEE_FETCHERS_CONFIG
    ),
) -> dict[str, ScheduledEvent]:
    """Returns the scheduled events for accruing and applying unarranged overdraft fees.

    Args:
        state: The current state of the smart contract.
        fetchers_config: Configuration for the fetchers used to retrieve parameters.

    Returns:
        A dictionary mapping event names to scheduled events.
    """
    state = state_utils.append_to_state(
        state=state,
        parameters=get_parameters(state.vault, fetchers_config.param_fetcher_id),
    )

    schedule_param_ids = {
        UNARRANGED_OVERDRAFT_FEE_ACCRUAL_TIME_PARAM.id,
        UNARRANGED_OVERDRAFT_FEE_APPLICATION_DAY_PARAM.id,
        UNARRANGED_OVERDRAFT_FEE_APPLICATION_TIME_PARAM.id,
    }

    rejection = state_utils.check_parameters_exist(state=state, param_ids=schedule_param_ids)
    assert rejection is None, rejection

    accrual_time_str = str(state.parameters[UNARRANGED_OVERDRAFT_FEE_ACCRUAL_TIME_PARAM.id])
    accrual_time: date_and_time.Time = date_and_time.parse_time_str(accrual_time_str)

    application_time_str = str(state.parameters[UNARRANGED_OVERDRAFT_FEE_APPLICATION_TIME_PARAM.id])
    application_time: date_and_time.Time = date_and_time.parse_time_str(application_time_str)

    application_day = int(str(state.parameters[UNARRANGED_OVERDRAFT_FEE_APPLICATION_DAY_PARAM.id]))

    start_datetime = (
        state.effective_datetime.astimezone(state.vault.events_timezone) + relativedelta(days=1)
    ).replace(hour=0, minute=0, second=0, microsecond=0)

    return {
        ACCRUAL_EVENT: ScheduledEvent(
            start_datetime=start_datetime,
            expression=ScheduleExpression(
                hour=accrual_time.hour,
                minute=accrual_time.minute,
                second=accrual_time.second,
            ),
        ),
        APPLICATION_EVENT: ScheduledEvent(
            start_datetime=start_datetime,
            expression=ScheduleExpression(
                day=application_day,
                hour=application_time.hour,
                minute=application_time.minute,
                second=application_time.second,
            ),
        ),
    }


def accrue_fees(
    state: state_utils.SmartContractState,
    account_type: str = "",
    fetchers_config: UnarrangedOverdraftFeeFetchersConfig = (
        DEFAULT_UNARRANGED_OVERDRAFT_FEE_FETCHERS_CONFIG
    ),
) -> list[CustomInstruction]:
    """Accrues the daily unarranged overdraft fee based on the previous day's end-of-day balance.

    The fee is accrued if the account is in an unarranged overdraft (i.e., its balance is
    greater net debit than the arranged overdraft limit).

    Args:
        state: The current state of the smart contract.
        account_type: The account type for GL purposes.
        fetchers_config: Configuration for the fetchers used to retrieve parameters.

    Returns:
        A list of CustomInstructions for accruing the unarranged overdraft fee.
    """
    state = state_utils.append_to_state(
        state=state,
        parameters=get_parameters(state.vault, fetchers_config.param_fetcher_id),
        balances=state.vault.get_balances_observation(
            fetcher_id=fetchers_config.eod_balance_fetcher_id
        ).balances,
    )

    rejection = state_utils.check_parameters_exist(
        state,
        {
            fetchers_config.denomination_param_id,
            UNARRANGED_OVERDRAFT_FEE_PARAM.id,
            UNARRANGED_OVERDRAFT_FEE_INCOME_ACCOUNT_PARAM.id,
            UNARRANGED_OVERDRAFT_FEE_RECEIVABLE_ACCOUNT_PARAM.id,
            overdraft_limit.ARRANGED_OVERDRAFT_AMOUNT_PARAM.id,
            overdraft_limit.UNARRANGED_OVERDRAFT_AMOUNT_PARAM.id,
        },
    )
    assert rejection is None, rejection

    denomination: str = str(state.parameters[fetchers_config.denomination_param_id])

    overdrawn_amount: Decimal = balance_utils.net_debit(
        balance_utils.sum_balances(balances=state.balances, denomination=denomination)
    )

    if overdrawn_amount <= 0:
        return []

    arranged_overdraft_amount: Decimal = state.parameters.get(
        overdraft_limit.ARRANGED_OVERDRAFT_AMOUNT_PARAM.id, 0
    )  # type: ignore

    if overdrawn_amount <= arranged_overdraft_amount:
        return []

    overdraft_fee: Decimal = state.parameters.get(UNARRANGED_OVERDRAFT_FEE_PARAM.id, 0)  # type: ignore
    if overdraft_fee <= 0:
        return []

    overdraft_fee_cap: Decimal | None = state.parameters.get(UNARRANGED_OVERDRAFT_FEE_CAP_PARAM.id)  # type: ignore

    overdraft_fee_receivable_account: str = str(
        state.parameters.get(UNARRANGED_OVERDRAFT_FEE_RECEIVABLE_ACCOUNT_PARAM.id)
    )

    current_balances: BalanceDefaultDict = state.vault.get_balances_observation(
        fetcher_id=fetchers.ALL_BALANCES_ET_BOF_ID
    ).balances

    unarranged_overdraft_fee_balance = balance_utils.net_debit(
        balance_utils.sum_balances(
            balances=current_balances,
            addresses={OVERDRAFT_FEE_ADDRESS},
            denomination=denomination,
        )
    )

    if overdraft_fee_cap is not None:
        if unarranged_overdraft_fee_balance >= overdraft_fee_cap:
            return []

        if unarranged_overdraft_fee_balance + overdraft_fee > overdraft_fee_cap:
            overdraft_fee = overdraft_fee_cap - unarranged_overdraft_fee_balance

    return accrual_utils.create_receivable_accrual_custom_instruction(
        customer_account=state.vault.account_id,
        customer_address=OVERDRAFT_FEE_ADDRESS,
        denomination=denomination,
        amount=overdraft_fee,
        internal_account=overdraft_fee_receivable_account,
        instruction_details={
            "description": f"Daily unarranged overdraft fee of {overdraft_fee} {denomination}",
            "event": ACCRUAL_EVENT,
        },
    )


def apply_fees(
    state: state_utils.SmartContractState,
    account_type: str = "",
    fetchers_config: UnarrangedOverdraftFeeFetchersConfig = (
        DEFAULT_UNARRANGED_OVERDRAFT_FEE_FETCHERS_CONFIG
    ),
) -> list[CustomInstruction]:
    """Applies the total accrued unarranged overdraft fee to the account.

    The application moves the accrued amount from the internal receivable account to the
    customer's account balance and also records the revenue in the internal income account.

    Args:
        state: The current state of the smart contract.
        account_type: The type of the account (for GL impact details).
        fetchers_config: Configuration for the fetchers used to retrieve parameters.

    Returns:
        A list of CustomInstructions for applying the accrued fees.
    """
    state = _append_to_state(state=state, fetchers_config=fetchers_config)

    rejection = state_utils.check_parameters_exist(
        state,
        {
            fetchers_config.denomination_param_id,
            UNARRANGED_OVERDRAFT_FEE_PARAM.id,
            UNARRANGED_OVERDRAFT_FEE_INCOME_ACCOUNT_PARAM.id,
            UNARRANGED_OVERDRAFT_FEE_RECEIVABLE_ACCOUNT_PARAM.id,
            overdraft_limit.ARRANGED_OVERDRAFT_AMOUNT_PARAM.id,
            overdraft_limit.UNARRANGED_OVERDRAFT_AMOUNT_PARAM.id,
        },
    )
    assert rejection is None, rejection

    denomination: str = str(state.parameters[fetchers_config.denomination_param_id])

    unarranged_overdraft_fee_balance = balance_utils.net_debit(
        balance_utils.sum_balances(
            balances=state.balances,
            addresses=[OVERDRAFT_FEE_ADDRESS],
            denomination=denomination,
        )
    )

    if unarranged_overdraft_fee_balance == 0:
        return []

    overdraft_fee_receivable_account = str(
        state.parameters[UNARRANGED_OVERDRAFT_FEE_RECEIVABLE_ACCOUNT_PARAM.id]
    )
    overdraft_fee_income_account = str(
        state.parameters[UNARRANGED_OVERDRAFT_FEE_INCOME_ACCOUNT_PARAM.id]
    )
    return accrual_utils.create_receivable_accrual_application_custom_instruction(
        customer_account=state.vault.account_id,
        denomination=denomination,
        application_amount=unarranged_overdraft_fee_balance,
        accrual_amount=unarranged_overdraft_fee_balance,
        accrual_customer_address=OVERDRAFT_FEE_ADDRESS,
        accrual_internal_account=overdraft_fee_receivable_account,
        application_customer_address=DEFAULT_ADDRESS,
        application_internal_account=overdraft_fee_income_account,
        instruction_details=posting_utils.standard_instruction_details(
            description=(
                f"Unarranged overdraft fee of {unarranged_overdraft_fee_balance} "
                f"{denomination} applied."
            ),
            event_type=APPLICATION_EVENT,
            gl_impacted=True,
            account_type=account_type,
        ),
    )
