__smart_contract_feature__ = True
# standard libs
from datetime import datetime
from decimal import Decimal
from typing import NamedTuple

import feature_library.common.accrual_utils as accrual_utils
import feature_library.common.balance_utils as balance_utils
import feature_library.common.date_and_time as date_and_time
import feature_library.common.denomination as denomination_module
import feature_library.common.posting_utils as posting_utils
import feature_library.common.state_utils as state_utils
import feature_library.common.tuples as common_tuples
import feature_library.common.tuples as tuples
import feature_library.deposit.interest.deposit_interest_accrual_utils as deposit_interest_accrual_utils  # noqa

# feature library
import feature_library.deposit.interfaces as deposit_interfaces

# contracts api
from contracts_api import (
    Balance,
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

INTEREST_ACCRUAL_EVENT_TYPE = "INTEREST_ACCRUAL"

# Expected Parameters
ACCRUAL_PRECISION_PARAM_ID = "&{accrual_precision}"
ACCRUAL_PRECISION_PARAM = ExpectedParameter(
    id=ACCRUAL_PRECISION_PARAM_ID,
    triggers_pre_parameter_change_hook=False,
    triggers_post_parameter_change_hook=False,
)

INTEREST_ACCRUAL_TIME_PARAM_ID = "&{interest_accrual_time}"
INTEREST_ACCRUAL_TIME_PARAM = ExpectedParameter(
    id=INTEREST_ACCRUAL_TIME_PARAM_ID,
    triggers_pre_parameter_change_hook=False,
    triggers_post_parameter_change_hook=False,
)

DAYS_IN_YEAR_PARAM_ID = "&{days_in_year_option}"
DAYS_IN_YEAR_PARAM = ExpectedParameter(
    id=DAYS_IN_YEAR_PARAM_ID,
    triggers_pre_parameter_change_hook=False,
    triggers_post_parameter_change_hook=False,
)


ACCRUED_INTEREST_PAYABLE_ACCOUNT_PARAM_ID = "&{accrued_interest_payable_account}"
ACCRUED_INTEREST_PAYABLE_ACCOUNT_PARAM = ExpectedParameter(
    id=ACCRUED_INTEREST_PAYABLE_ACCOUNT_PARAM_ID,
    triggers_pre_parameter_change_hook=False,
    triggers_post_parameter_change_hook=False,
)

ACCRUED_INTEREST_RECEIVABLE_ACCOUNT_PARAM_ID = "&{accrued_interest_receivable_account}"
ACCRUED_INTEREST_RECEIVABLE_ACCOUNT_PARAM = ExpectedParameter(
    id=ACCRUED_INTEREST_RECEIVABLE_ACCOUNT_PARAM_ID,
    triggers_pre_parameter_change_hook=False,
    triggers_post_parameter_change_hook=False,
)


event_types = [
    SmartContractEventType(name=INTEREST_ACCRUAL_EVENT_TYPE),
]

expected_parameters = [
    INTEREST_ACCRUAL_TIME_PARAM,
    ACCRUAL_PRECISION_PARAM,
    DAYS_IN_YEAR_PARAM,
    ACCRUED_INTEREST_PAYABLE_ACCOUNT_PARAM,
    ACCRUED_INTEREST_RECEIVABLE_ACCOUNT_PARAM,
    denomination_module.DENOMINATION_PARAM,
]

# data fetchers
INTEREST_ACCRUAL_PARAMS_ET_POF_ID = "INTEREST_ACCRUAL_PARAMS_ET_POF"
INTEREST_ACCRUAL_PARAMS_ET_POF = ParametersObservationFetcher(
    fetcher_id=INTEREST_ACCRUAL_PARAMS_ET_POF_ID,
    at=DefinedDateTime.EFFECTIVE_DATETIME,
    filter=ParametersFilter(parameter_ids=[p.id for p in expected_parameters]),
)

data_fetchers = [
    INTEREST_ACCRUAL_PARAMS_ET_POF,
]

AccrualParams = NamedTuple(
    "AccrualParams",
    [
        ("denomination", str),
        ("days_in_year", str),
        ("rounding_precision", int),
        ("accrued_payable_account", str),
        ("accrued_receivable_account", str),
    ],
)

InterestAccrualFetchersConfig = NamedTuple(
    "InterestAccrualFetchersConfig",
    [
        ("param_fetcher_id", str),
        ("denomination_param_id", str),
        ("days_in_year_param_id", str),
        ("rounding_precision_param_id", str),
        ("accrued_payable_account_param_id", str),
        ("accrued_receivable_account_param_id", str),
        ("interest_accrual_time_param_id", str),
    ],
)

DEFAULT_INTEREST_ACCRUAL_FETCHERS_CONFIG = InterestAccrualFetchersConfig(
    param_fetcher_id=INTEREST_ACCRUAL_PARAMS_ET_POF_ID,
    denomination_param_id=denomination_module.DENOMINATION_PARAM_ID,
    days_in_year_param_id=DAYS_IN_YEAR_PARAM_ID,
    rounding_precision_param_id=ACCRUAL_PRECISION_PARAM_ID,
    accrued_payable_account_param_id=ACCRUED_INTEREST_PAYABLE_ACCOUNT_PARAM_ID,
    accrued_receivable_account_param_id=ACCRUED_INTEREST_RECEIVABLE_ACCOUNT_PARAM_ID,
    interest_accrual_time_param_id=INTEREST_ACCRUAL_TIME_PARAM_ID,
)

InterestTypeConfig = deposit_interfaces.InterestTypeConfig


def get_parameters(
    vault: SmartContractVault, param_fetcher_id: str = INTEREST_ACCRUAL_PARAMS_ET_POF_ID
) -> dict[str, datetime | Decimal | str | None]:
    """Retrieves configuration parameters for the interest accrual feature.

    Args:
        vault (SmartContractVault): The SmartContractVault instance to query.
        param_fetcher_id (str): The unique identifier for the parameter fetcher.
            Defaults to INTEREST_ACCRUAL_PARAMS_ET_POF_ID.

    Returns:
        dict[str, datetime | Decimal | str | None]: Parameters for the interest accrual feature.
    """

    return vault.get_parameters_observation(fetcher_id=param_fetcher_id).parameters


def _append_to_state(
    state: state_utils.SmartContractState,
    param_fetcher_id: str = INTEREST_ACCRUAL_PARAMS_ET_POF_ID,
) -> state_utils.SmartContractState:
    """Append interest accrual parameters to state.

    Args:
        state (state_utils.SmartContractState): Smart Contract State
        param_fetcher_id (str, optional): Fetcher id for required parameters. Defaults to
            INTEREST_ACCRUAL_PARAMS_ET_POF_ID.

    Returns:
        state_utils.SmartContractState: The updated state object.
    """
    return state_utils.append_to_state(
        state=state,
        parameters=get_parameters(state.vault, param_fetcher_id),
    )


def get_scheduled_events(
    state: state_utils.SmartContractState,
    fetchers_config: InterestAccrualFetchersConfig = DEFAULT_INTEREST_ACCRUAL_FETCHERS_CONFIG,
) -> dict[str, ScheduledEvent]:
    """Get scheduled event for interest accrual. Uses interest accrual time parameter.

    Args:
        state (state_utils.SmartContractState): Smart Contract state
        fetchers_config (InterestAccrualFetchersConfig, optional): Fetchers configuration.
            Defaults to DEFAULT_INTEREST_ACCRUAL_FETCHERS_CONFIG.

    Returns:
        dict[str, ScheduledEvent]: Interest accrual scheduled event.
    """

    state = _append_to_state(state=state, param_fetcher_id=fetchers_config.param_fetcher_id)

    rejection = state_utils.check_parameters_exist(
        state=state, param_ids={fetchers_config.interest_accrual_time_param_id}
    )
    assert rejection is None, rejection
    accrual_time_str: str = state.parameters.get(fetchers_config.interest_accrual_time_param_id)  # type: ignore
    accrual_time: date_and_time.Time = date_and_time.parse_time_str(accrual_time_str)

    return {
        INTEREST_ACCRUAL_EVENT_TYPE: ScheduledEvent(
            start_datetime=state.effective_datetime,
            expression=ScheduleExpression(
                hour=accrual_time.hour,
                minute=accrual_time.minute,
                second=accrual_time.second,
            ),
        )
    }


def _get_accrual_parameters(
    state: state_utils.SmartContractState,
    denomination_param_id: str,
    days_in_year_param_id: str,
    rounding_precision_param_id: str,
    accrued_payable_account_param_id: str,
    accrued_receivable_account_param_id: str,
) -> AccrualParams:
    """Helper to extract parameters from state after validation."""
    return AccrualParams(
        denomination=state.parameters.get(denomination_param_id),  # type: ignore
        days_in_year=state.parameters.get(days_in_year_param_id),  # type: ignore
        rounding_precision=int(state.parameters.get(rounding_precision_param_id)),  # type: ignore
        accrued_payable_account=state.parameters.get(accrued_payable_account_param_id),  # type: ignore
        accrued_receivable_account=state.parameters.get(accrued_receivable_account_param_id),  # type: ignore
    )


def schedule_logic(
    state: state_utils.SmartContractState,
    interest_types: list[InterestTypeConfig],
    fetchers_config: InterestAccrualFetchersConfig = DEFAULT_INTEREST_ACCRUAL_FETCHERS_CONFIG,
    event: str = INTEREST_ACCRUAL_EVENT_TYPE,
) -> list[CustomInstruction]:
    """Schedule logic for handling interest accrual.

    Retrieve required parameters, calculate accrued
    interest for provided interest features and create custom instructions.

    Args:
        state (state_utils.SmartContractState): Smart Contract State
        interest_types (list[InterestTypeConfig]): List of interest feature configurations.
        balances (BalanceDefaultDict | None, optional): Balances required for interest calculations.
            Defaults to None.
        fetchers_config (InterestAccrualFetchersConfig, optional): Fetchers configuration.
            Defaults to DEFAULT_INTEREST_ACCRUAL_FETCHERS_CONFIG.
        event (str, optional): The event name to be used in instruction details. Defaults to
            INTEREST_ACCRUAL_EVENT_TYPE.

    Returns:
        list[CustomInstruction]: Accrual custom instructions
    """

    state = _append_to_state(state=state, param_fetcher_id=fetchers_config.param_fetcher_id)

    rejection = state_utils.check_parameters_exist(
        state=state,
        param_ids={
            fetchers_config.denomination_param_id,
            fetchers_config.days_in_year_param_id,
            fetchers_config.rounding_precision_param_id,
            fetchers_config.accrued_payable_account_param_id,
            fetchers_config.accrued_receivable_account_param_id,
        },
    )
    assert rejection is None, rejection

    accrual_params: AccrualParams = _get_accrual_parameters(
        state,
        fetchers_config.denomination_param_id,
        fetchers_config.days_in_year_param_id,
        fetchers_config.rounding_precision_param_id,
        fetchers_config.accrued_payable_account_param_id,
        fetchers_config.accrued_receivable_account_param_id,
    )
    balances = state.balances

    effective_balance: Balance = deposit_interest_accrual_utils.get_accrual_capital(
        state=state,
        balances=balances,
    )
    if effective_balance.net == 0:
        return []

    def process_interest_type(
        interest_config: InterestTypeConfig,
    ) -> list[CustomInstruction]:
        """Gets interest rate/rates from interest type feature and calculates accrued interest.

        Args:
            interest_config (InterestTypeConfig): The interest feature's configuration.

        Returns:
            list[CustomInstruction]: Accrual custom instructions
        """
        interest_type: deposit_interfaces.InterestType = interest_config.interest_type
        rate_tuple: tuples.InterestRateTuple = interest_type.get_interest_rate(
            state=state, fetchers_config=interest_config.fetchers_config
        )

        # Skip if no interest rate or balance direction doesn't match feature type
        if rate_tuple.interest_rate_param_value is None:
            return []

        accrual_detail: common_tuples.AccrualDetail = interest_type.get_accrual_amount(
            effective_balance=effective_balance,
            effective_datetime=state.effective_datetime,
            interest_rates=rate_tuple.interest_rate_param_value,
            days_in_year=accrual_params.days_in_year,
            precision=accrual_params.rounding_precision,
            state=state,
            fetchers_config=interest_config.fetchers_config,
        )

        if accrual_detail.accrual_amount == 0:
            return []

        instruction_details = posting_utils.standard_instruction_details(
            description=accrual_detail.description,
            event_type=event,
            gl_impacted=True,
        )

        # True for a positive accrual amount for credit interest, or for a negative accrual
        # amount for debit interest.
        is_payable_accrual: bool = (balance_utils.net_credit(effective_balance) > 0) == (
            accrual_detail.accrual_amount > 0
        )

        return (
            accrual_utils.create_payable_accrual_custom_instruction(
                customer_account=state.vault.account_id,
                customer_address=interest_type.get_accrual_payable_customer_address(),
                denomination=accrual_params.denomination,
                amount=abs(accrual_detail.accrual_amount),
                internal_account=interest_type.get_accrual_payable_internal_account(state=state),
                instruction_details=instruction_details,
            )
            if is_payable_accrual
            else accrual_utils.create_receivable_accrual_custom_instruction(
                customer_account=state.vault.account_id,
                customer_address=interest_type.get_accrual_receivable_customer_address(),
                denomination=accrual_params.denomination,
                amount=abs(accrual_detail.accrual_amount),
                internal_account=interest_type.get_accrual_receivable_internal_account(state=state),
                instruction_details=instruction_details,
            )
        )

    return [
        instruction
        for interest_config in interest_types
        for instruction in process_interest_type(interest_config)
    ]
