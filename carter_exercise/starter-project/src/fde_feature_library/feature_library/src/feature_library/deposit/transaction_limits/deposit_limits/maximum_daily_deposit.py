__smart_contract_feature__ = True

# standard libs
from datetime import datetime
from decimal import Decimal
from typing import NamedTuple

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
MAXIMUM_DAILY_DEPOSIT_PARAM_ID = "&{maximum_daily_deposit}"
MAXIMUM_DAILY_DEPOSIT_PARAM = ExpectedParameter(
    id=MAXIMUM_DAILY_DEPOSIT_PARAM_ID,
    optional=True,
    triggers_pre_parameter_change_hook=False,
    triggers_post_parameter_change_hook=False,
)

expected_parameters = [
    MAXIMUM_DAILY_DEPOSIT_PARAM,
    denomination_module.DENOMINATION_PARAM,
]

# Fetchers
MAX_DAILY_DEPOSIT_POF_ID = "max_daily_deposit_pof"
MAX_DAILY_DEPOSIT_POF = ParametersObservationFetcher(
    fetcher_id=MAX_DAILY_DEPOSIT_POF_ID,
    at=DefinedDateTime.EFFECTIVE_DATETIME,
    filter=ParametersFilter(parameter_ids=[p.id for p in expected_parameters]),
)

data_fetchers = [
    fetchers.EFFECTIVE_DATE_POSTIF,
    MAX_DAILY_DEPOSIT_POF,
]

MaximumDailyDepositFetchersConfig = NamedTuple(
    "MaximumDailyDepositFetchersConfig",
    [
        ("param_fetcher_id", str),
        ("denomination_param_id", str),
        ("client_transactions_fetcher_id", str),
    ],
)

DEFAULT_MAXIMUM_DAILY_DEPOSIT_FETCHERS_CONFIG = MaximumDailyDepositFetchersConfig(
    param_fetcher_id=MAX_DAILY_DEPOSIT_POF_ID,
    denomination_param_id=denomination_module.DENOMINATION_PARAM.id,
    client_transactions_fetcher_id=fetchers.EFFECTIVE_DATE_POSTIF_ID,
)


def get_parameters(
    vault: SmartContractVault, param_fetcher_id: str = MAX_DAILY_DEPOSIT_POF_ID
) -> dict[str, datetime | Decimal | str | None]:
    """Retrieves configuration parameters for the maximum daily deposit limit feature.

    Args:
        vault: The SmartContractVault instance to query.
        param_fetcher_id: The unique identifier for the parameter fetcher.
            Defaults to `MAX_DAILY_DEPOSIT_POF_ID`.

    Returns:
        Parameters for the maximum daily deposit feature.
    """
    return vault.get_parameters_observation(fetcher_id=param_fetcher_id).parameters


def _append_to_state(
    state: state_utils.SmartContractState,
    param_fetcher_id: str = MAX_DAILY_DEPOSIT_POF_ID,
) -> state_utils.SmartContractState:
    """Updates the contract state with specific parameter observations.

    Args:
        state: The current state of the smart contract, containing the vault object.
        param_fetcher_id: The ID of the fetcher used to retrieve parameters.
            Defaults to `MAX_DAILY_DEPOSIT_POF_ID`.

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
    fetchers_config: MaximumDailyDepositFetchersConfig = (
        DEFAULT_MAXIMUM_DAILY_DEPOSIT_FETCHERS_CONFIG
    ),
) -> Rejection | None:
    """Reject the proposed client transactions if they would exceed the limit.

    Args:
        state: SmartContractState containing the vault object and effective datetime.
        client_transactions: dict of proposed ClientTransactions to process.
        fetchers_config: Configuration for the required fetchers and parameters.

    Returns:
        A rejection if the limit conditions are not met, otherwise None.
    """
    state = _append_to_state(state, fetchers_config.param_fetcher_id)
    rejection = state_utils.check_parameters_exist(state, {fetchers_config.denomination_param_id})
    if rejection is not None:
        return rejection

    max_daily_deposit: Decimal | None = state.parameters.get(MAXIMUM_DAILY_DEPOSIT_PARAM_ID)  # type: ignore
    if max_daily_deposit is None:
        return None

    denomination = str(state.parameters[fetchers_config.denomination_param_id])

    proposed_change_in_bals: Balance = client_transaction_utils.sum_client_transactions(
        cutoff_datetime=state.effective_datetime,
        client_transactions=client_transactions,
        denomination=denomination,
    )
    proposed_postings_deposited_amount: Decimal = proposed_change_in_bals.credit
    if proposed_postings_deposited_amount == 0:
        return None

    effective_date_client_transactions: dict[str, ClientTransaction] = (
        state.vault.get_client_transactions(
            fetcher_id=fetchers_config.client_transactions_fetcher_id
        )
    )

    deposit_cutoff_datetime: datetime = state.effective_datetime.astimezone(
        state.vault.events_timezone
    ).replace(hour=0, minute=0, second=0, microsecond=0)

    actual_change_in_bals: Balance = client_transaction_utils.sum_client_transactions(
        cutoff_datetime=deposit_cutoff_datetime,
        client_transactions=effective_date_client_transactions,
        denomination=denomination,
    )
    amount_deposited_actual: Decimal = actual_change_in_bals.credit
    deposit_daily_spent = proposed_postings_deposited_amount + amount_deposited_actual

    if deposit_daily_spent > max_daily_deposit:
        return Rejection(
            message=f"Transactions would cause the maximum daily deposit limit of "
            f"{max_daily_deposit} {denomination} to be exceeded.",
            reason_code=RejectionReason.AGAINST_TNC,
        )

    return None
