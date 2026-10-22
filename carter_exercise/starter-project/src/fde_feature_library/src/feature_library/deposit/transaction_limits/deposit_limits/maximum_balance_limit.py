# CBF: CPP-1986
__smart_contract_feature__ = True

# standard libs
from datetime import datetime
from decimal import Decimal
from typing import NamedTuple

# features
import feature_library.common.balance_utils as balance_utils
import feature_library.common.denomination as denomination_module
import feature_library.common.fetchers as fetchers
import feature_library.common.posting_utils as posting_utils
import feature_library.common.state_utils as state_utils

# contracts api
from contracts_api import (
    Balance,
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
MAXIMUM_BALANCE_PARAM_ID = "&{maximum_balance}"
MAXIMUM_BALANCE_PARAM = ExpectedParameter(
    id=MAXIMUM_BALANCE_PARAM_ID,
    optional=True,
    triggers_pre_parameter_change_hook=False,
    triggers_post_parameter_change_hook=False,
)

# Fetchers
MAX_BAL_LIMIT_POF_ID = "max_bal_limit_pof"
MAX_BAL_LIMIT_POF = ParametersObservationFetcher(
    fetcher_id=MAX_BAL_LIMIT_POF_ID,
    at=DefinedDateTime.EFFECTIVE_DATETIME,
    filter=ParametersFilter(parameter_ids=[MAXIMUM_BALANCE_PARAM_ID]),
)

data_fetchers = [fetchers.ALL_BALANCES_LIVE_BOF, MAX_BAL_LIMIT_POF]

expected_parameters = [
    MAXIMUM_BALANCE_PARAM,
    denomination_module.DENOMINATION_PARAM,
]

MaximumBalanceLimitFetchersConfig = NamedTuple(
    "MaximumBalanceLimitFetchersConfig",
    [
        ("balance_fetcher_id", str),
        ("param_fetcher_id", str),
        ("denomination_param_id", str),
        ("maximum_balance_param_id", str),
    ],
)

DEFAULT_MAXIMUM_BALANCE_LIMIT_FETCHERS_CONFIG = MaximumBalanceLimitFetchersConfig(
    balance_fetcher_id=fetchers.ALL_BALANCES_LIVE_BOF_ID,
    param_fetcher_id=MAX_BAL_LIMIT_POF_ID,
    denomination_param_id=denomination_module.DENOMINATION_PARAM_ID,
    maximum_balance_param_id=MAXIMUM_BALANCE_PARAM_ID,
)


def get_parameters(
    vault: SmartContractVault, param_fetcher_id: str = MAX_BAL_LIMIT_POF_ID
) -> dict[str, datetime | Decimal | str | None]:
    """Retrieves configuration parameters from a for the maximum balance limit feature.

    Args:
        vault: The SmartContractVault instance to query.
        param_fetcher_id: The unique identifier for the parameter fetcher.
            Defaults to `MAX_BAL_LIMIT_POF_ID`.

    Returns:
        Parameters for the maximum balance limit feature.
        (datetime, Decimal, string, or None).
    """
    return vault.get_parameters_observation(fetcher_id=param_fetcher_id).parameters


def _append_to_state(
    state: state_utils.SmartContractState,
    fetchers_config: MaximumBalanceLimitFetchersConfig = (
        DEFAULT_MAXIMUM_BALANCE_LIMIT_FETCHERS_CONFIG
    ),
) -> state_utils.SmartContractState:
    """Updates the contract state with live balances and specific parameter observations.

    Args:
        state: The current state of the smart contract, containing the vault object.
        fetchers_config: Configuration for the fetchers used.

    Returns:
        A new state object containing the appended balances and parameters.
    """
    return state_utils.append_to_state(
        state=state,
        parameters=get_parameters(state.vault, fetchers_config.param_fetcher_id),
        balances=state.vault.get_balances_observation(
            fetcher_id=fetchers_config.balance_fetcher_id
        ).balances,
    )


def validate(
    *,
    state: state_utils.SmartContractState,
    postings: posting_utils.PostingInstructionListAlias,
    fetchers_config: MaximumBalanceLimitFetchersConfig = (
        DEFAULT_MAXIMUM_BALANCE_LIMIT_FETCHERS_CONFIG
    ),
) -> Rejection | None:
    """Reject the posting if the deposit will cause the balance to exceed the maximum.

    Args:
        state: SmartContractState containing the vault object and effective datetime.
        postings: list of postings instructions that are being processed.
        fetchers_config: Configuration for the fetchers and parameters used.

    Returns:
        rejection if the limit conditions are not met, otherwise None.
    """
    state = _append_to_state(state, fetchers_config)
    if rejection := state_utils.check_parameters_exist(
        state, {fetchers_config.denomination_param_id}
    ):
        return rejection

    denomination: str = state.parameters[fetchers_config.denomination_param_id]  # type: ignore
    maximum_balance: Decimal | None = state.parameters[fetchers_config.maximum_balance_param_id]  # type: ignore

    if maximum_balance is None or denomination is None:
        return None

    current_balance: Balance = balance_utils.get_current_net_balance(
        balances=state.balances, denomination=denomination
    )
    deposit_proposed_amount: Balance = sum(
        (
            balance_utils.get_current_net_balance(balances=p.balances(), denomination=denomination)
            for p in postings
        ),
        Balance(),
    )
    proposed_balance = current_balance + deposit_proposed_amount

    if balance_utils.net_credit(proposed_balance) > maximum_balance:
        return Rejection(
            message=f"Posting would exceed maximum permitted balance {maximum_balance} "
            f"{denomination}.",
            reason_code=RejectionReason.AGAINST_TNC,
        )

    return None
