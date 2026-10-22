# Copyright @ 2026 Thought Machine Group Limited. All rights reserved.
__smart_contract_feature__ = True

# standard libs
from datetime import datetime
from decimal import Decimal
from typing import Any, NamedTuple
from zoneinfo import ZoneInfo

from dateutil.relativedelta import relativedelta

# features
import feature_library.common.balance_utils as balance_utils
import feature_library.common.denomination as denomination_module
import feature_library.common.posting_utils as posting_utils
import feature_library.common.state_utils as state_utils

# contracts api
from contracts_api import (
    Attribute,
    AttributeDateTimeType,
    AttributeHookArguments,
    AttributeHookResult,
    DefinedDateTime,
    ExpectedParameter,
    ParametersFilter,
    ParametersObservationFetcher,
)

# inception sdk
from inception_sdk.vault.contracts.extensions.contracts_api_extensions import SmartContractVault

# Constants
UTC = ZoneInfo("UTC")

# Parameters
COOLING_OFF_PERIOD_PARAM_ID = "&{cooling_off_period}"
COOLING_OFF_PERIOD_PARAM = ExpectedParameter(
    id=COOLING_OFF_PERIOD_PARAM_ID,
    triggers_pre_parameter_change_hook=False,
    triggers_post_parameter_change_hook=False,
)

# Attributes
COOLING_OFF_PERIOD_END_DATE_ATTR_ID = "cooling_off_period_end_date"
COOLING_OFF_PERIOD_END_DATE_ATTRIBUTE = Attribute(
    name=COOLING_OFF_PERIOD_END_DATE_ATTR_ID,
    data_type=AttributeDateTimeType(),
)

attributes = [COOLING_OFF_PERIOD_END_DATE_ATTRIBUTE]

# Fetchers
COOLING_OFF_PERIOD_PARAMS_ET_POF_ID = "cooling_off_period_params_et_pof"

expected_parameters = [
    COOLING_OFF_PERIOD_PARAM,
    denomination_module.DENOMINATION_PARAM,
]

COOLING_OFF_PERIOD_PARAMS_ET_POF = ParametersObservationFetcher(
    fetcher_id=COOLING_OFF_PERIOD_PARAMS_ET_POF_ID,
    at=DefinedDateTime.EFFECTIVE_DATETIME,
    filter=ParametersFilter(parameter_ids=[p.id for p in expected_parameters]),
)

data_fetchers = [COOLING_OFF_PERIOD_PARAMS_ET_POF]


CoolingOffPeriodFetchersConfig = NamedTuple(
    "CoolingOffPeriodFetchersConfig",
    [
        ("param_fetcher_id", str),
        ("denomination_param_id", str),
        ("cooling_off_period_param_id", str),
    ],
)

DEFAULT_FETCHERS_CONFIG = CoolingOffPeriodFetchersConfig(
    param_fetcher_id=COOLING_OFF_PERIOD_PARAMS_ET_POF_ID,
    denomination_param_id=denomination_module.DENOMINATION_PARAM_ID,
    cooling_off_period_param_id=COOLING_OFF_PERIOD_PARAM_ID,
)


def get_parameters(
    vault: SmartContractVault, fetcher_id: str = COOLING_OFF_PERIOD_PARAMS_ET_POF_ID
) -> dict[str, Any]:
    """Retrieves feature-specific parameters from the vault.

    Args:
        vault: The vault object to query for observations.
        fetcher_id: The ID of the parameter observation fetcher.

    Returns:
        The dictionary of parameter values.
    """
    return vault.get_parameters_observation(fetcher_id=fetcher_id).parameters


def _append_to_state(
    *,
    state: state_utils.SmartContractState,
    fetchers_config: CoolingOffPeriodFetchersConfig = DEFAULT_FETCHERS_CONFIG,
) -> state_utils.SmartContractState:
    """Consolidates feature-specific parameters into the SmartContractState.

    Args:
        state: The current state of the smart contract.
        fetchers_config: Configuration for the fetchers.

    Returns:
        The updated state object.
    """
    return state_utils.append_to_state(
        state=state,
        parameters=get_parameters(state.vault, fetchers_config.param_fetcher_id),
    )


def cooling_off_period_end_date_attribute_handler(
    vault: SmartContractVault,
    hook_arguments: AttributeHookArguments,
    fetchers_config: CoolingOffPeriodFetchersConfig = DEFAULT_FETCHERS_CONFIG,
) -> AttributeHookResult:
    """Gets the cooling-off period end date for the attribute hook.

    Args:
        vault: The vault object for the account.
        hook_arguments: The attribute hook arguments.
        fetchers_config: Configuration for the fetchers.

    Returns:
        The attribute hook result containing the cooling-off period end date.
    """
    state = state_utils.initialise_state(
        vault=vault,
        effective_datetime=hook_arguments.effective_datetime,
    )

    return AttributeHookResult(
        attribute_value=get_cooling_off_period_end_datetime(
            state=state, fetchers_config=fetchers_config
        )
    )


def get_cooling_off_period_end_datetime(
    *,
    state: state_utils.SmartContractState,
    fetchers_config: CoolingOffPeriodFetchersConfig = DEFAULT_FETCHERS_CONFIG,
) -> datetime:
    """Calculates and returns the cooling-off period end datetime.

    This date will represent the midnight (00:00:00) of the account activation datetime
    plus the number of days in the cooling-off period.

    Args:
        state: The current state of the smart contract.
        fetchers_config: Configuration for the fetchers.

    Returns:
        The datetime when the cooling-off period ends.
    """
    state = _append_to_state(state=state, fetchers_config=fetchers_config)

    rejection = state_utils.check_parameters_exist(
        state=state, param_ids={fetchers_config.cooling_off_period_param_id}
    )
    assert rejection is None, rejection

    cooling_off_period = int(state.parameters[fetchers_config.cooling_off_period_param_id])  # type: ignore

    account_activation_datetime = state.vault.get_account_activation_datetime()

    cooling_off_period_end = account_activation_datetime.astimezone(
        state.vault.events_timezone
    ) + relativedelta(days=cooling_off_period, hour=0, minute=0, second=0, microsecond=0)

    return cooling_off_period_end


def is_within_cooling_off_period(
    *,
    state: state_utils.SmartContractState,
    fetchers_config: CoolingOffPeriodFetchersConfig = DEFAULT_FETCHERS_CONFIG,
) -> bool:
    """Determines whether the effective datetime is within the cooling-off period of an account.

    Args:
        state: The current state of the smart contract.
        fetchers_config: Configuration for the fetchers.

    Returns:
        True if the effective datetime is less than or equal to the cooling-off period end datetime.
    """
    return state.effective_datetime <= get_cooling_off_period_end_datetime(
        state=state, fetchers_config=fetchers_config
    )


def is_withdrawal_subject_to_fees(
    *,
    state: state_utils.SmartContractState,
    posting_instructions: posting_utils.PostingInstructionListAlias,
    fetchers_config: CoolingOffPeriodFetchersConfig = DEFAULT_FETCHERS_CONFIG,
) -> bool:
    """Determine if a withdrawal is subject to fees.

    For use in the post_posting_hook.

    If a full withdrawal is made during the cooling-off period, then no fees will be charged,
    otherwise the withdrawal is subject to fees. Deposits are not subject to fees.

    Args:
        state: The current state of the smart contract.
        posting_instructions: The list of posting instructions.
        fetchers_config: Configuration for the fetchers.

    Returns:
        True if the withdrawal is subject to fees, False otherwise.
    """
    state = _append_to_state(state=state, fetchers_config=fetchers_config)

    rejection = state_utils.check_parameters_exist(
        state=state, param_ids={fetchers_config.denomination_param_id}
    )
    assert rejection is None, rejection

    denomination: str = state.parameters[fetchers_config.denomination_param_id]  # type: ignore

    withdrawal_amount = balance_utils.net_debit(
        bal=balance_utils.sum_balances(
            balances=posting_utils.get_posting_instructions_balances(
                posting_instructions=posting_instructions
            ),
            denomination=denomination,
        )
    )

    is_withdrawal = withdrawal_amount > Decimal("0")

    # Deposits are not subject to fees.
    if not is_withdrawal:
        return False

    current_balance = balance_utils.net_credit(
        bal=balance_utils.get_available_balance(balances=state.balances, denomination=denomination)
    )

    is_full_withdrawal = is_withdrawal and current_balance == Decimal("0")

    return not (
        is_full_withdrawal
        and is_within_cooling_off_period(state=state, fetchers_config=fetchers_config)
    )
