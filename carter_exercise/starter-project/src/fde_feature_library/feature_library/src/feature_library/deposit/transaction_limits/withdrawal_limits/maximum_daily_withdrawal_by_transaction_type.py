# Copyright @ 2026 Thought Machine Group Limited. All rights reserved.
"""Maximum Daily Withdrawal By Transaction Type limit feature."""

__smart_contract_feature__ = True

# standard libs
from datetime import datetime
from decimal import Decimal
from json import loads
from typing import NamedTuple
from zoneinfo import ZoneInfo

# feature library
import feature_library.common.client_transaction_utils as client_transaction_utils
import feature_library.common.denomination as denomination_module
import feature_library.common.fetchers as fetchers
import feature_library.common.state_utils as state_utils
import feature_library.deposit.common as common

# contracts api
from contracts_api import (
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
DAILY_WITHDRAWAL_LIMIT_BY_TRANSACTION_TYPE_PARAM_ID = (
    "&{daily_withdrawal_limit_by_transaction_type}"
)
DAILY_WITHDRAWAL_LIMIT_BY_TRANSACTION_TYPE_PARAM = ExpectedParameter(
    id=DAILY_WITHDRAWAL_LIMIT_BY_TRANSACTION_TYPE_PARAM_ID,
    optional=True,
    triggers_pre_parameter_change_hook=False,
    triggers_post_parameter_change_hook=False,
)
"""
The maximum amount that can be withdrawn from an account over the current day by transaction
type. Expected to be a stringified JSON object mapping transaction types to amounts (e.g.,
'{"ATM": "1000"}').
"""
TIERED_DAILY_WITHDRAWAL_LIMIT_PARAM_ID = "&{tiered_daily_withdrawal_limits}"
TIERED_DAILY_WITHDRAWAL_LIMIT_PARAM = ExpectedParameter(
    id=TIERED_DAILY_WITHDRAWAL_LIMIT_PARAM_ID,
    optional=True,
    triggers_pre_parameter_change_hook=False,
    triggers_post_parameter_change_hook=False,
)
"""
The daily withdrawal limits based on account tier. It defines the upper withdrawal limit that
cannot be exceeded by Maximum Daily Withdrawal Amount. If above it, the contract will consider
the tiered limit as valid. Expected to be a stringified JSON object mapping tiers to limits by
transaction type (e.g., '{"UPPER_TIER": {"ATM": "5000"}, "MIDDLE_TIER": {"ATM": "2000"},
"LOWER_TIER": {"ATM": "1500"}}').
"""
expected_parameters = [
    DAILY_WITHDRAWAL_LIMIT_BY_TRANSACTION_TYPE_PARAM,
    TIERED_DAILY_WITHDRAWAL_LIMIT_PARAM,
    common.ACCOUNT_TIER_PARAM,
    denomination_module.DENOMINATION_PARAM,
]

MAX_DAILY_WITHDRAWAL_BY_TRANSACTION_TYPE_POF_ID = "maximum_daily_withdrawal_by_transaction_type_pof"
MAX_DAILY_WITHDRAWAL_BY_TRANSACTION_TYPE_POF = ParametersObservationFetcher(
    fetcher_id=MAX_DAILY_WITHDRAWAL_BY_TRANSACTION_TYPE_POF_ID,
    at=DefinedDateTime.EFFECTIVE_DATETIME,
    filter=ParametersFilter(parameter_ids=[p.id for p in expected_parameters]),
)

data_fetchers = [MAX_DAILY_WITHDRAWAL_BY_TRANSACTION_TYPE_POF]

UTC = ZoneInfo("UTC")

MaximumDailyWithdrawalByTransactionTypeFetchersConfig = NamedTuple(
    "MaximumDailyWithdrawalByTransactionTypeFetchersConfig",
    [
        ("param_fetcher_id", str),
        ("client_transactions_fetcher_id", str),
        ("denomination_param_id", str),
        ("account_tier_param_id", str),
        ("daily_withdrawal_limit_by_transaction_type_param_id", str),
        ("tiered_daily_withdrawal_limits_param_id", str),
    ],
)
DEFAULT_MAX_DAILY_WITHDRAWAL_BY_TRANSACTION_TYPE_FETCHERS_CONFIG = MaximumDailyWithdrawalByTransactionTypeFetchersConfig(  # noqa: E501
    param_fetcher_id=MAX_DAILY_WITHDRAWAL_BY_TRANSACTION_TYPE_POF.fetcher_id,
    client_transactions_fetcher_id=fetchers.EFFECTIVE_DATE_POSTIF.fetcher_id,
    denomination_param_id=denomination_module.DENOMINATION_PARAM.id,
    account_tier_param_id=common.ACCOUNT_TIER_PARAM_ID,
    daily_withdrawal_limit_by_transaction_type_param_id=DAILY_WITHDRAWAL_LIMIT_BY_TRANSACTION_TYPE_PARAM.id,
    tiered_daily_withdrawal_limits_param_id=TIERED_DAILY_WITHDRAWAL_LIMIT_PARAM.id,
)

INSTRUCTION_DETAILS_KEY = "TRANSACTION_TYPE"


def get_parameters(
    vault: SmartContractVault,
    param_fetcher_id: str = MAX_DAILY_WITHDRAWAL_BY_TRANSACTION_TYPE_POF_ID,
) -> dict[str, datetime | Decimal | str | None]:
    """Retrieves config parameters for the maximum daily withdrawal by transaction type limit.

    Args:
        vault: The SmartContractVault instance to query.
        param_fetcher_id: The unique identifier for the parameter fetcher.
            Defaults to `MAX_DAILY_WITHDRAWAL_BY_TRANSACTION_TYPE_POF_ID`.

    Returns:
        Parameters for the maximum daily withdrawal by transaction type limit feature.
    """
    return vault.get_parameters_observation(fetcher_id=param_fetcher_id).parameters


def _append_to_state(
    state: state_utils.SmartContractState,
    param_fetcher_id: str = MAX_DAILY_WITHDRAWAL_BY_TRANSACTION_TYPE_POF_ID,
) -> state_utils.SmartContractState:
    """Updates the contract state with specific parameter observations.

    Args:
        state: The current state of the smart contract, containing the vault object.
        param_fetcher_id: The ID of the fetcher used to retrieve parameters.
            Defaults to `MAX_DAILY_WITHDRAWAL_BY_TRANSACTION_TYPE_POF_ID`.

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
    fetchers_config: MaximumDailyWithdrawalByTransactionTypeFetchersConfig = DEFAULT_MAX_DAILY_WITHDRAWAL_BY_TRANSACTION_TYPE_FETCHERS_CONFIG,  # noqa: E501
) -> Rejection | None:
    """Reject the client transactions if they would exceed the maximum daily withdrawal limit.

    Args:
        state: SmartContractState containing the vault object and effective datetime.
        client_transactions: dict of proposed ClientTransactions to process.
        fetchers_config: Configuration for the required fetchers and parameters.

    Returns:
        A rejection if any transaction type's daily limit is breached, otherwise None.
    """
    # 1. State Augmentation & Parameter Validation
    state = _append_to_state(state, fetchers_config.param_fetcher_id)
    if rejection := state_utils.check_parameters_exist(
        state, {fetchers_config.denomination_param_id, fetchers_config.account_tier_param_id}
    ):
        return rejection

    # 2. Extract Configuration (Data setup)
    params = state.parameters
    denomination: str = params[fetchers_config.denomination_param_id]  # type: ignore
    account_tier: str = params[fetchers_config.account_tier_param_id]  # type: ignore

    tiered_limits: dict[str, str] = loads(
        params.get(fetchers_config.tiered_daily_withdrawal_limits_param_id) or "{}"  # type: ignore
    )
    daily_limits: dict[str, str] = loads(
        params.get(fetchers_config.daily_withdrawal_limit_by_transaction_type_param_id) or "{}"  # type: ignore
    )

    # Early exit if no limits or transactions exist
    if (not tiered_limits and not daily_limits) or not client_transactions:
        return None

    limits: dict[str, Decimal] = _get_limit_per_transaction_type(
        tiered_limits.get(account_tier, {}), daily_limits
    )
    if not limits:
        return None

    historic_transactions = state.vault.get_client_transactions(
        fetcher_id=fetchers_config.client_transactions_fetcher_id
    )

    withdrawal_cutoff: datetime = (
        state.effective_datetime.astimezone(state.vault.events_timezone)
        .replace(hour=0, minute=0, second=0, microsecond=0)
        .astimezone(UTC)
    )

    # Define a helper to calculate the "total spent" for a specific type
    def _get_daily_spent(tx_type: str) -> Decimal:
        proposed_sum = client_transaction_utils.sum_client_transactions(
            cutoff_datetime=state.effective_datetime,
            client_transactions=client_transaction_utils.filter_client_transactions(
                client_transactions=client_transactions,
                denomination=denomination,
                key=INSTRUCTION_DETAILS_KEY,
                value=tx_type,
            ),
            denomination=denomination,
        ).debit

        if proposed_sum == 0:
            return Decimal(0)

        historic_sum = client_transaction_utils.sum_client_transactions(
            cutoff_datetime=withdrawal_cutoff,
            client_transactions=client_transaction_utils.filter_client_transactions(
                client_transactions=historic_transactions,
                denomination=denomination,
                key=INSTRUCTION_DETAILS_KEY,
                value=tx_type,
            ),
            denomination=denomination,
        ).debit

        return proposed_sum + historic_sum

    # Search for the first violation (Map -> Filter -> Next)
    return next(
        (
            Rejection(
                message=f"Transactions would cause the maximum daily {tx_type} "
                f"withdrawal limit of {limit} {denomination} to be exceeded.",
                reason_code=RejectionReason.AGAINST_TNC,
            )
            for tx_type, limit in limits.items()
            if _get_daily_spent(tx_type) > limit
        ),
        None,  # Default if no limit is breached
    )


def _get_limit_per_transaction_type(
    tiered_limit_dict: dict[str, str], daily_limit_dict: dict[str, str]
) -> dict[str, Decimal]:
    """Selects the more restrictive limit tiered and instance limits per transaction type.

    Args:
        tiered_limit_dict: Dict mapping transaction types to their tiered limit values.
        daily_limit_dict: Dict mapping transaction types to their daily instance limit values.

    Returns:
        Dict mapping transaction types to their most restrictive limit as a Decimal.
    """
    # Start with a fresh merge of both dictionaries with values as Decimal
    merged_limits = {k: Decimal(v) for k, v in (tiered_limit_dict | daily_limit_dict).items()}

    # Resolve overlapping keys with a set intersection
    for tx_type in tiered_limit_dict.keys() & daily_limit_dict.keys():
        merged_limits[tx_type] = min(
            Decimal(tiered_limit_dict[tx_type]), Decimal(daily_limit_dict[tx_type])
        )

    return merged_limits


def validate_parameter_change(
    state: state_utils.SmartContractState,
    proposed_parameter_value: str,
    fetchers_config: MaximumDailyWithdrawalByTransactionTypeFetchersConfig = (
        DEFAULT_MAX_DAILY_WITHDRAWAL_BY_TRANSACTION_TYPE_FETCHERS_CONFIG
    ),
) -> Rejection | None:
    """Validates a proposed change to the daily withdrawal limits parameter.

    Ensures that the proposed limit does not exceed the tiered limit for the account's active tier.

    Args:
        state: SmartContractState containing the vault object and effective datetime.
        proposed_parameter_value: The proposed value for the daily withdrawal limits.
        fetchers_config: Configuration for the required fetchers and parameters.

    Returns:
        A rejection if the proposed limit exceeds the tiered limit, otherwise None.
    """
    state = _append_to_state(state, fetchers_config.param_fetcher_id)
    if rejection := state_utils.check_parameters_exist(
        state,
        {fetchers_config.denomination_param_id, fetchers_config.account_tier_param_id},
    ):
        return rejection

    params = state.parameters
    account_tier: str = params[fetchers_config.account_tier_param_id]  # type: ignore
    denomination: str = params[fetchers_config.denomination_param_id]  # type: ignore

    tiered_limits: dict[str, dict[str, str]] = loads(
        params.get(fetchers_config.tiered_daily_withdrawal_limits_param_id) or "{}"  # type: ignore
    )

    # Get the specific limit map for the active tier
    active_tier_limits = tiered_limits.get(account_tier, {})
    if not active_tier_limits:
        return None

    proposed_limits: dict[str, str] = loads(proposed_parameter_value)

    # Find the first instance where the proposed value > tiered limit
    return next(
        (
            Rejection(
                message=(
                    f"Cannot update {tx_type} transaction type limit for Maximum "
                    f"Daily Withdrawal Amount because {Decimal(prop_val)} {denomination} "
                    f"exceeds tiered limit of {active_tier_limits[tx_type]} {denomination} "
                    f"for active {account_tier}."
                ),
                reason_code=RejectionReason.AGAINST_TNC,
            )
            for tx_type, prop_val in proposed_limits.items()
            if tx_type in active_tier_limits
            and Decimal(prop_val) > Decimal(active_tier_limits[tx_type])
        ),
        None,
    )
