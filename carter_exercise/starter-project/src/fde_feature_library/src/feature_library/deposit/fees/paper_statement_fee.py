# Copyright @ 2023 - 2026 Thought Machine Group Limited. All rights reserved.
__smart_contract_feature__ = True

# standard libs
from datetime import datetime
from decimal import Decimal
from typing import NamedTuple

# feature library
import feature_library.common.date_and_time as date_and_time
import feature_library.common.denomination as denomination_module
import feature_library.common.fetchers as fetchers
import feature_library.common.posting_utils as posting_utils
import feature_library.common.state_utils as state_utils
import feature_library.common.utils as common_utils
import feature_library.deposit.fees.partial_fee as partial_fee
import feature_library.deposit.interfaces as deposit_interfaces

# contracts api
from contracts_api import (
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

APPLICATION_EVENT = "APPLY_PAPER_STATEMENT_FEE"

# Addresses
OUTSTANDING_PAPER_STATEMENT_FEE_TRACKER = "OUTSTANDING_PAPER_STATEMENT_FEE_TRACKER"

# Parameters
PAPER_STATEMENT_FEE_RATE_PARAM_ID = "&{paper_statement_fee_rate}"
PAPER_STATEMENT_FEE_RATE_PARAM = ExpectedParameter(
    id=PAPER_STATEMENT_FEE_RATE_PARAM_ID,
    triggers_pre_parameter_change_hook=False,
    triggers_post_parameter_change_hook=False,
)

PAPER_STATEMENT_FEE_DAY_PARAM_ID = "&{paper_statement_fee_day}"
PAPER_STATEMENT_FEE_DAY_PARAM = ExpectedParameter(
    id=PAPER_STATEMENT_FEE_DAY_PARAM_ID,
    triggers_pre_parameter_change_hook=False,
    triggers_post_parameter_change_hook=False,
)

PAPER_STATEMENT_FEE_TIME_PARAM_ID = "&{paper_statement_fee_application_time}"
PAPER_STATEMENT_FEE_TIME_PARAM = ExpectedParameter(
    id=PAPER_STATEMENT_FEE_TIME_PARAM_ID,
    triggers_pre_parameter_change_hook=False,
    triggers_post_parameter_change_hook=False,
)

PAPER_STATEMENT_FEE_INCOME_ACCOUNT_PARAM_ID = "&{paper_statement_fee_income_account}"
PAPER_STATEMENT_FEE_INCOME_ACCOUNT_PARAM = ExpectedParameter(
    id=PAPER_STATEMENT_FEE_INCOME_ACCOUNT_PARAM_ID,
    triggers_pre_parameter_change_hook=False,
    triggers_post_parameter_change_hook=False,
)

PAPER_STATEMENT_FEE_ENABLED_PARAM_ID = "&{paper_statement_fee_enabled}"
PAPER_STATEMENT_FEE_ENABLED_PARAM = ExpectedParameter(
    id=PAPER_STATEMENT_FEE_ENABLED_PARAM_ID,
    triggers_pre_parameter_change_hook=False,
    triggers_post_parameter_change_hook=False,
)

PAPER_STATEMENT_FEE_PARTIAL_FEE_ENABLED_PARAM_ID = "&{partial_paper_statement_fee_enabled}"
PAPER_STATEMENT_FEE_PARTIAL_FEE_ENABLED_PARAM = ExpectedParameter(
    id=PAPER_STATEMENT_FEE_PARTIAL_FEE_ENABLED_PARAM_ID,
    triggers_pre_parameter_change_hook=False,
    triggers_post_parameter_change_hook=False,
)

expected_parameters = [
    PAPER_STATEMENT_FEE_RATE_PARAM,
    PAPER_STATEMENT_FEE_DAY_PARAM,
    PAPER_STATEMENT_FEE_TIME_PARAM,
    PAPER_STATEMENT_FEE_INCOME_ACCOUNT_PARAM,
    PAPER_STATEMENT_FEE_ENABLED_PARAM,
    PAPER_STATEMENT_FEE_PARTIAL_FEE_ENABLED_PARAM,
    denomination_module.DENOMINATION_PARAM,
]

PAPER_STATEMENT_FEE_POF_ID = "paper_statement_fee_pof"
PAPER_STATEMENT_FEE_POF = ParametersObservationFetcher(
    fetcher_id=PAPER_STATEMENT_FEE_POF_ID,
    at=DefinedDateTime.EFFECTIVE_DATETIME,
    filter=ParametersFilter(parameter_ids=[p.id for p in expected_parameters]),
)

data_fetchers = [
    fetchers.ALL_BALANCES_ET_BOF,
    PAPER_STATEMENT_FEE_POF,
]

event_types = [
    SmartContractEventType(name=APPLICATION_EVENT),
]

PaperStatementFeeFetchersConfig = NamedTuple(
    "PaperStatementFeeFetchersConfig",
    [
        ("param_fetcher_id", str),
        ("denomination_param_id", str),
    ],
)
DEFAULT_PAPER_STATEMENT_FEE_FETCHERS_CONFIG = PaperStatementFeeFetchersConfig(
    param_fetcher_id=PAPER_STATEMENT_FEE_POF_ID,
    denomination_param_id=denomination_module.DENOMINATION_PARAM.id,
)


def get_parameters(
    vault: SmartContractVault, param_fetcher_id: str = PAPER_STATEMENT_FEE_POF_ID
) -> dict[str, datetime | Decimal | str | None]:
    """Retrieves configuration parameters for the paper statement fee feature.

    Args:
        vault: The SmartContractVault instance to query.
        param_fetcher_id: The unique identifier for the parameter fetcher.
            Defaults to `PAPER_STATEMENT_FEE_POF_ID`.

    Returns:
        Parameters for the paper statement fee feature.
    """
    return vault.get_parameters_observation(fetcher_id=param_fetcher_id).parameters


def _append_to_state(
    state: state_utils.SmartContractState,
    balance_fetcher_id: str = fetchers.ALL_BALANCES_ET_BOF_ID,
    param_fetcher_id: str = PAPER_STATEMENT_FEE_POF_ID,
) -> state_utils.SmartContractState:
    """Updates the contract state with live balances and specific parameter observations.

    Args:
        state: The current state of the smart contract, containing the vault object.
        balance_fetcher_id: The ID of the fetcher used to retrieve balances.
            Defaults to `common_fetchers.ALL_BALANCES_ET_BOF_ID`.
        param_fetcher_id: The ID of the fetcher used to retrieve parameters.
            Defaults to `PAPER_STATEMENT_FEE_POF_ID`.

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
    fetchers_config: PaperStatementFeeFetchersConfig = DEFAULT_PAPER_STATEMENT_FEE_FETCHERS_CONFIG,
) -> dict[str, ScheduledEvent]:
    """Get scheduled event for paper statement fee application.

    Uses application schedule parameters.

    Args:
        state: The current state of the smart contract.
        fetchers_config: Configuration for the fetchers used to retrieve parameters.

    Returns:
        The scheduled events for the paper statement fee.
    """
    state = state_utils.append_to_state(
        state=state,
        parameters=get_parameters(state.vault, fetchers_config.param_fetcher_id),
    )

    schedule_param_ids = {
        PAPER_STATEMENT_FEE_DAY_PARAM.id,
        PAPER_STATEMENT_FEE_TIME_PARAM.id,
    }

    rejection = state_utils.check_parameters_exist(state=state, param_ids=schedule_param_ids)
    assert rejection is None, rejection

    paper_statement_fee_application_time_str: str = state.parameters[  # type: ignore
        PAPER_STATEMENT_FEE_TIME_PARAM.id
    ]
    paper_statement_fee_application_time: date_and_time.Time = date_and_time.parse_time_str(
        paper_statement_fee_application_time_str
    )

    day = int(state.parameters[PAPER_STATEMENT_FEE_DAY_PARAM.id])  # type: ignore

    return {
        APPLICATION_EVENT: ScheduledEvent(
            start_datetime=state.effective_datetime,
            expression=ScheduleExpression(
                day=day,
                hour=paper_statement_fee_application_time.hour,
                minute=paper_statement_fee_application_time.minute,
                second=paper_statement_fee_application_time.second,
            ),
        )
    }


def _are_partial_payments_enabled(
    state: state_utils.SmartContractState,
) -> bool:
    """Checks if partial paper statement fee collection is enabled.

    Args:
        state: The current state of the smart contract.

    Returns:
        True if partial fee collection is enabled, False otherwise.
    """
    return common_utils.str_to_bool(
        str(state.parameters.get(PAPER_STATEMENT_FEE_PARTIAL_FEE_ENABLED_PARAM.id, "False"))
    )


PARTIAL_FEE_DETAILS = deposit_interfaces.PartialFeeCollection(
    outstanding_fee_address=OUTSTANDING_PAPER_STATEMENT_FEE_TRACKER,
    fee_type="Partial Paper Statement Fee",
    internal_account_parameter_id=PAPER_STATEMENT_FEE_INCOME_ACCOUNT_PARAM.id,
)


def apply_fees(
    state: state_utils.SmartContractState,
    account_type: str,
    available_balance_feature: deposit_interfaces.AvailableBalance | None = None,
    fetchers_config: PaperStatementFeeFetchersConfig = DEFAULT_PAPER_STATEMENT_FEE_FETCHERS_CONFIG,
) -> list[CustomInstruction]:
    """Applies the paper statement fee if enabled.

    Args:
        state: The current state of the smart contract.
        account_type: The type of the account (for GL impact details).
        fetchers_config: Configuration for the fetchers used to retrieve parameters.
        available_balance_feature: Interface to calculate the available balance for partial fees.

    Returns:
        The result of the fee application, including instructions and any rejections.
    """
    state = _append_to_state(state=state, param_fetcher_id=fetchers_config.param_fetcher_id)

    rejection = state_utils.check_parameters_exist(
        state,
        {
            fetchers_config.denomination_param_id,
            PAPER_STATEMENT_FEE_RATE_PARAM.id,
            PAPER_STATEMENT_FEE_INCOME_ACCOUNT_PARAM.id,
            PAPER_STATEMENT_FEE_ENABLED_PARAM.id,
        },
    )
    assert rejection is None, rejection

    if not common_utils.str_to_bool(str(state.parameters[PAPER_STATEMENT_FEE_ENABLED_PARAM.id])):
        return []

    paper_statement_fee_amount: Decimal = state.parameters[PAPER_STATEMENT_FEE_RATE_PARAM.id]  # type: ignore

    if paper_statement_fee_amount <= 0:
        return []

    denomination: str = str(state.parameters[fetchers_config.denomination_param_id])
    paper_statement_fee_income_account: str = state.parameters[
        PAPER_STATEMENT_FEE_INCOME_ACCOUNT_PARAM.id
    ]  # type: ignore

    fee_instructions = [
        CustomInstruction(
            postings=posting_utils.create_postings(
                amount=paper_statement_fee_amount,
                debit_account=state.vault.account_id,
                credit_account=paper_statement_fee_income_account,
                denomination=denomination,
            ),
            value_datetime=state.effective_datetime,
            instruction_details=posting_utils.standard_instruction_details(
                description="Monthly Paper Statement Fee Application",
                event_type=APPLICATION_EVENT,
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
    else:
        return fee_instructions
