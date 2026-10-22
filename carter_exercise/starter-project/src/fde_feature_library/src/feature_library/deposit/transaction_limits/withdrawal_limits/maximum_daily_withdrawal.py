# Copyright @ 2026 Thought Machine Group Limited. All rights reserved.
__smart_contract_feature__ = True

# standard libs
from datetime import datetime
from decimal import Decimal
from typing import NamedTuple
from zoneinfo import ZoneInfo

# feature library
import feature_library.common.client_transaction_utils as client_transaction_utils
import feature_library.common.denomination as denomination_module
import feature_library.common.fetchers as fetchers
import feature_library.common.state_utils as state_utils

# contracts api
from contracts_api import (
    Balance,
    ClientTransaction,
    DefinedDateTime,
    ExpectedParameter,
    ParametersFilter,
    ParametersObservationFetcher,
    Rejection,
    RejectionReason,
)

# inception sdk
from inception_sdk.vault.contracts.extensions.contracts_api_extensions import SmartContractVault

# Parameters
MAX_DAILY_WITHDRAWAL_PARAM_ID = "&{maximum_daily_withdrawal}"
MAX_DAILY_WITHDRAWAL_PARAM = ExpectedParameter(
    id=MAX_DAILY_WITHDRAWAL_PARAM_ID,
    optional=True,
    triggers_pre_parameter_change_hook=False,
    triggers_post_parameter_change_hook=False,
)

expected_parameters = [
    MAX_DAILY_WITHDRAWAL_PARAM,
    denomination_module.DENOMINATION_PARAM,
]

# Fetchers
MAX_DAILY_WITHDRAWAL_POF_ID = "maximum_daily_withdrawal_pof"
MAX_DAILY_WITHDRAWAL_POF = ParametersObservationFetcher(
    fetcher_id=MAX_DAILY_WITHDRAWAL_POF_ID,
    at=DefinedDateTime.EFFECTIVE_DATETIME,
    filter=ParametersFilter(parameter_ids=[p.id for p in expected_parameters]),
)

data_fetchers = [MAX_DAILY_WITHDRAWAL_POF]

UTC = ZoneInfo("UTC")

MaximumDailyWithdrawalFetchersConfig = NamedTuple(
    "MaximumDailyWithdrawalFetchersConfig",
    [
        ("param_fetcher_id", str),
        ("client_transactions_fetcher_id", str),
        ("denomination_param_id", str),
        ("maximum_daily_withdrawal_param_id", str),
    ],
)
DEFAULT_MAXIMUM_DAILY_WITHDRAWAL_FETCHERS_CONFIG = MaximumDailyWithdrawalFetchersConfig(
    param_fetcher_id=MAX_DAILY_WITHDRAWAL_POF_ID,
    client_transactions_fetcher_id=fetchers.EFFECTIVE_DATE_POSTIF_ID,
    denomination_param_id=denomination_module.DENOMINATION_PARAM_ID,
    maximum_daily_withdrawal_param_id=MAX_DAILY_WITHDRAWAL_PARAM_ID,
)


def get_parameters(
    vault: SmartContractVault, param_fetcher_id: str = MAX_DAILY_WITHDRAWAL_POF_ID
) -> dict[str, datetime | Decimal | str | None]:
    """Retrieves configuration parameters for the maximum daily withdrawal limit feature.

    Args:
        vault: The SmartContractVault instance to query.
        param_fetcher_id: The unique identifier for the parameter fetcher.
            Defaults to `MAX_DAILY_WITHDRAWAL_POF_ID`.

    Returns:
        Parameters for the maximum daily withdrawal limit feature.
    """
    return vault.get_parameters_observation(fetcher_id=param_fetcher_id).parameters


def append_to_state(
    state: state_utils.SmartContractState,
    param_fetcher_id: str = MAX_DAILY_WITHDRAWAL_POF_ID,
) -> state_utils.SmartContractState:
    """Updates the contract state with specific parameter observations.

    Args:
        state: The current state of the smart contract, containing the vault object.
        param_fetcher_id: The ID of the fetcher used to retrieve parameters.
            Defaults to `MAX_DAILY_WITHDRAWAL_POF_ID`.

    Returns:
        A new state object containing the appended parameters.
    """
    return state_utils.append_to_state(
        state=state,
        parameters=get_parameters(state.vault, param_fetcher_id),
    )


def validate(
    state: state_utils.SmartContractState,
    client_transactions: dict[str, ClientTransaction],
    fetchers_config: MaximumDailyWithdrawalFetchersConfig = DEFAULT_MAXIMUM_DAILY_WITHDRAWAL_FETCHERS_CONFIG,  # noqa: E501
) -> Rejection | None:
    """Reject the client transactions if they would exceed the maximum daily withdrawal limit.

    Args:
        state: SmartContractState containing the vault object and effective datetime.
        client_transactions: dict of proposed ClientTransactions to process.
        fetchers_config: Configuration for the required fetchers and parameters.

    Returns:
        A rejection if the limit conditions are not met, otherwise None.
    """
    state = append_to_state(state, fetchers_config.param_fetcher_id)
    if rejection := state_utils.check_parameters_exist(
        state, {fetchers_config.denomination_param_id}
    ):
        return rejection

    denomination: str = state.parameters[fetchers_config.denomination_param_id]  # type: ignore

    max_daily_withdrawal: Decimal | None = state.parameters[
        fetchers_config.maximum_daily_withdrawal_param_id
    ]  # type: ignore
    if max_daily_withdrawal is None:
        return None

    # Obtain the impact of the proposed client transactions
    proposed_change_in_bals: Balance = client_transaction_utils.sum_client_transactions(
        cutoff_datetime=state.effective_datetime,
        client_transactions=client_transactions,
        denomination=denomination,
    )

    if proposed_change_in_bals.debit == 0:
        return None

    effective_date_client_transactions: dict[str, ClientTransaction] = (
        state.vault.get_client_transactions(
            fetcher_id=fetchers_config.client_transactions_fetcher_id
        )
    )

    withdrawal_cutoff_datetime: datetime = (
        state.effective_datetime.astimezone(state.vault.events_timezone)
        .replace(hour=0, minute=0, second=0, microsecond=0)
        .astimezone(UTC)
    )

    actual_change_in_bals: Balance = client_transaction_utils.sum_client_transactions(
        cutoff_datetime=withdrawal_cutoff_datetime,
        client_transactions=effective_date_client_transactions,
        denomination=denomination,
    )

    withdrawal_daily_spent: Decimal = proposed_change_in_bals.debit + actual_change_in_bals.debit

    if withdrawal_daily_spent > max_daily_withdrawal:
        return Rejection(
            message=f"Transactions with a total of {withdrawal_daily_spent} {denomination} would "
            f"cause the maximum daily withdrawal limit of {max_daily_withdrawal} {denomination} "
            "to be exceeded.",
            reason_code=RejectionReason.AGAINST_TNC,
        )

    return None
