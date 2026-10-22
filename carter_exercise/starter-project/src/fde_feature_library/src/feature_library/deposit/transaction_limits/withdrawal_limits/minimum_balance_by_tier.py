# Copyright @ 2026 Thought Machine Group Limited. All rights reserved.
"""Minimum Balance By Tier limit feature."""

__smart_contract_feature__ = True

# standard libs
from datetime import datetime
from decimal import Decimal
from json import loads
from typing import NamedTuple

# feature library
import feature_library.common.balance_utils as balance_utils
import feature_library.common.denomination as denomination_module
import feature_library.common.fetchers as fetchers
import feature_library.common.posting_utils as posting_utils
import feature_library.common.state_utils as state_utils
import feature_library.deposit.common as common

# contracts api
from contracts_api import (
    DefinedDateTime,
    ExpectedParameter,
    ParametersFilter,
    ParametersObservationFetcher,
    Rejection,
    RejectionReason,
)

# inception sdk
from inception_sdk.vault.contracts.extensions.contracts_api_extensions import SmartContractVault

TIERED_MIN_BALANCE_THRESHOLD_PARAM_ID = "&{tiered_minimum_balance_threshold}"
TIERED_MIN_BALANCE_THRESHOLD_PARAM = ExpectedParameter(
    id=TIERED_MIN_BALANCE_THRESHOLD_PARAM_ID,
    optional=True,
    triggers_pre_parameter_change_hook=False,
    triggers_post_parameter_change_hook=False,
)

expected_parameters = [
    TIERED_MIN_BALANCE_THRESHOLD_PARAM,
    common.ACCOUNT_TIER_PARAM,
    denomination_module.DENOMINATION_PARAM,
]

MIN_BALANCE_BY_TIER_POF_ID = "minimum_balance_by_tier_pof"
MIN_BALANCE_BY_TIER_POF = ParametersObservationFetcher(
    fetcher_id=MIN_BALANCE_BY_TIER_POF_ID,
    at=DefinedDateTime.EFFECTIVE_DATETIME,
    filter=ParametersFilter(parameter_ids=[p.id for p in expected_parameters]),
)

data_fetchers = [
    MIN_BALANCE_BY_TIER_POF,
    fetchers.ALL_BALANCES_LIVE_BOF,
]

MinimumBalanceByTierFetchersConfig = NamedTuple(
    "MinimumBalanceByTierFetchersConfig",
    [
        ("param_fetcher_id", str),
        ("balances_fetcher_id", str),
        ("denomination_param_id", str),
        ("account_tier_param_id", str),
        ("tiered_minimum_balance_threshold_param_id", str),
    ],
)
DEFAULT_MINIMUM_BALANCE_BY_TIER_FETCHERS_CONFIG = MinimumBalanceByTierFetchersConfig(
    param_fetcher_id=MIN_BALANCE_BY_TIER_POF_ID,
    balances_fetcher_id=fetchers.ALL_BALANCES_LIVE_BOF_ID,
    denomination_param_id=denomination_module.DENOMINATION_PARAM.id,
    account_tier_param_id=common.ACCOUNT_TIER_PARAM_ID,
    tiered_minimum_balance_threshold_param_id=TIERED_MIN_BALANCE_THRESHOLD_PARAM.id,
)


def get_parameters(
    vault: SmartContractVault, param_fetcher_id: str = MIN_BALANCE_BY_TIER_POF_ID
) -> dict[str, datetime | Decimal | str | None]:
    """Retrieves configuration parameters for the minimum balance by tier limit feature.

    Args:
        vault: The SmartContractVault instance to query.
        param_fetcher_id: The unique identifier for the parameter fetcher.
            Defaults to `MIN_BALANCE_BY_TIER_POF_ID`.

    Returns:
        Parameters for the minimum balance by tier limit feature.
    """
    return vault.get_parameters_observation(fetcher_id=param_fetcher_id).parameters


def _append_to_state(
    state: state_utils.SmartContractState,
    param_fetcher_id: str = MIN_BALANCE_BY_TIER_POF_ID,
    balances_fetcher_id: str = fetchers.ALL_BALANCES_LIVE_BOF_ID,
) -> state_utils.SmartContractState:
    """Updates the contract state with specific parameter and balance observations.

    Args:
        state: The current state of the smart contract, containing the vault object.
        param_fetcher_id: The ID of the fetcher used to retrieve parameters.
            Defaults to `MIN_BALANCE_BY_TIER_POF_ID`.
        balances_fetcher_id: The ID of the fetcher used to retrieve balances.
            Defaults to `fetchers.ALL_BALANCES_LIVE_BOF_ID`.

    Returns:
        A new state object containing the appended parameters and balances.
    """
    return state_utils.append_to_state(
        state=state,
        parameters=get_parameters(state.vault, param_fetcher_id),
        balances=state.vault.get_balances_observation(fetcher_id=balances_fetcher_id).balances,
    )


def validate(
    state: state_utils.SmartContractState,
    postings: posting_utils.PostingInstructionListAlias,
    fetchers_config: MinimumBalanceByTierFetchersConfig = DEFAULT_MINIMUM_BALANCE_BY_TIER_FETCHERS_CONFIG,  # noqa: E501
) -> Rejection | None:
    """Reject if the PIB takes the account below the minimum threshold for the account tier.

    Args:
        state: SmartContractState containing the vault object and effective datetime.
        postings: List of posting instructions to process.
        fetchers_config: Configuration for the required fetchers and parameters.

    Returns:
        A rejection if the minimum balance limit conditions are not met, otherwise None.
    """
    state = _append_to_state(
        state, fetchers_config.param_fetcher_id, fetchers_config.balances_fetcher_id
    )
    if rejection := state_utils.check_parameters_exist(
        state,
        {
            fetchers_config.denomination_param_id,
            fetchers_config.account_tier_param_id,
        },
    ):
        return rejection

    denomination: str = state.parameters[fetchers_config.denomination_param_id]  # type: ignore
    account_tier: str = state.parameters[fetchers_config.account_tier_param_id]  # type: ignore

    min_balance_threshold_by_tier_str: str | None = state.parameters.get(
        fetchers_config.tiered_minimum_balance_threshold_param_id
    )  # type: ignore

    if not min_balance_threshold_by_tier_str:
        return None

    min_balance_threshold_by_tier: dict[str, str] = loads(min_balance_threshold_by_tier_str)

    min_balance = Decimal(min_balance_threshold_by_tier.get(account_tier, "0"))

    available_balance: Decimal = balance_utils.net_credit(
        balance_utils.get_available_balance(balances=state.balances, denomination=denomination)
    )

    proposed_amount: Decimal = sum(
        (
            balance_utils.net_credit(
                balance_utils.get_available_balance(
                    balances=posting.balances(), denomination=denomination
                )
            )
            for posting in postings
        ),
        Decimal(0),
    )

    if available_balance + proposed_amount < min_balance:
        return Rejection(
            message=f"Transaction amount {proposed_amount} {denomination} will result in the "
            f"account balance falling below the minimum permitted "
            f"of {min_balance} {denomination}.",
            reason_code=RejectionReason.AGAINST_TNC,
        )

    return None
