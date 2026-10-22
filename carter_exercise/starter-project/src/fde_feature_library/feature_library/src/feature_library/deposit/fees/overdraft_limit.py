# CBF: CPP-1974
# CBF: CPP-1916
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
import feature_library.deposit.interfaces as deposit_interfaces

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

# Parameters
ARRANGED_OVERDRAFT_AMOUNT_PARAM_ID = "&{arranged_overdraft_amount}"
ARRANGED_OVERDRAFT_AMOUNT_PARAM = ExpectedParameter(
    id=ARRANGED_OVERDRAFT_AMOUNT_PARAM_ID,
    optional=True,
    triggers_pre_parameter_change_hook=False,
    triggers_post_parameter_change_hook=False,
)

UNARRANGED_OVERDRAFT_AMOUNT_PARAM_ID = "&{unarranged_overdraft_amount}"
UNARRANGED_OVERDRAFT_AMOUNT_PARAM = ExpectedParameter(
    id=UNARRANGED_OVERDRAFT_AMOUNT_PARAM_ID,
    optional=True,
    triggers_pre_parameter_change_hook=False,
    triggers_post_parameter_change_hook=False,
)

expected_parameters = [
    ARRANGED_OVERDRAFT_AMOUNT_PARAM,
    UNARRANGED_OVERDRAFT_AMOUNT_PARAM,
    denomination_module.DENOMINATION_PARAM,
]

OVERDRAFT_LIMIT_POF_ID = "overdraft_limit_pof"
OVERDRAFT_LIMIT_POF = ParametersObservationFetcher(
    fetcher_id=OVERDRAFT_LIMIT_POF_ID,
    at=DefinedDateTime.EFFECTIVE_DATETIME,
    filter=ParametersFilter(parameter_ids=[p.id for p in expected_parameters]),
)

data_fetchers = [
    fetchers.ALL_BALANCES_LIVE_BOF,
    OVERDRAFT_LIMIT_POF,
]

OverdraftLimitFetchersConfig = NamedTuple(
    "OverdraftLimitFetchersConfig",
    [
        ("param_fetcher_id", str),
        ("denomination_param_id", str),
        ("balance_fetcher_id", str),
    ],
)

DEFAULT_OVERDRAFT_LIMIT_FETCHERS_CONFIG = OverdraftLimitFetchersConfig(
    param_fetcher_id=OVERDRAFT_LIMIT_POF_ID,
    denomination_param_id=denomination_module.DENOMINATION_PARAM.id,
    balance_fetcher_id=fetchers.ALL_BALANCES_LIVE_BOF_ID,
)


def get_parameters(
    vault: SmartContractVault, param_fetcher_id: str = OVERDRAFT_LIMIT_POF_ID
) -> dict[str, datetime | Decimal | str | None]:
    """Retrieves configuration parameters for the overdraft limit feature.

    Args:
        vault: The SmartContractVault instance to query.
        param_fetcher_id: The unique identifier for the parameter fetcher.
            Defaults to `OVERDRAFT_LIMIT_POF_ID`.

    Returns:
        A dictionary containing the retrieved parameters.
    """
    return vault.get_parameters_observation(fetcher_id=param_fetcher_id).parameters


def _append_to_state(
    state: state_utils.SmartContractState,
    fetchers_config: OverdraftLimitFetchersConfig = DEFAULT_OVERDRAFT_LIMIT_FETCHERS_CONFIG,
) -> state_utils.SmartContractState:
    """Updates the contract state with balances and specific parameter observations.

    Args:
        state: The current state of the smart contract, containing the vault object.
        fetchers_config: Configuration for the fetchers used to retrieve parameters and balances.

    Returns:
        A new state object containing the appended balances and parameters.
    """
    balances = state.balances
    if not balances:
        balances = state.vault.get_balances_observation(
            fetcher_id=fetchers_config.balance_fetcher_id
        ).balances

    return state_utils.append_to_state(
        state=state,
        parameters=get_parameters(state.vault, fetchers_config.param_fetcher_id),
        balances=balances,
    )


def validate(
    *,
    state: state_utils.SmartContractState,
    postings: posting_utils.PostingInstructionListAlias,
    fetchers_config: OverdraftLimitFetchersConfig = DEFAULT_OVERDRAFT_LIMIT_FETCHERS_CONFIG,
) -> Rejection | None:
    """Returns a Rejection if the postings will cause the balance to exceed the total overdraft limit.

    The total overdraft limit is the sum of the arranged and unarranged overdraft amounts.

    Args:
        state: The current state of the smart contract.
        postings: The list of posting instructions to validate.
        fetchers_config: Configuration for the fetchers used to retrieve parameters and balances.

    Returns:
        A Rejection if the limit is exceeded, otherwise None.
    """
    state = _append_to_state(state=state, fetchers_config=fetchers_config)

    rejection = state_utils.check_parameters_exist(state, {fetchers_config.denomination_param_id})
    if rejection:
        return rejection

    denomination: str = str(state.parameters[fetchers_config.denomination_param_id])

    posting_amount: Decimal = Decimal(
        sum(
            balance_utils.get_available_balance(
                balances=posting.balances(), denomination=denomination
            ).net
            for posting in postings
        )
    )

    total_available_balance = get_overdraft_available_balance(state=state)

    if posting_amount < 0 and abs(posting_amount) > total_available_balance:
        return Rejection(
            message=(
                f"Postings total {denomination} {posting_amount}, which exceeds the "
                f"available balance of {denomination} {total_available_balance}."
            ),
            reason_code=RejectionReason.INSUFFICIENT_FUNDS,
        )

    return None


def get_overdraft_available_balance(
    *,
    state: state_utils.SmartContractState,
    fetchers_config: OverdraftLimitFetchersConfig = DEFAULT_OVERDRAFT_LIMIT_FETCHERS_CONFIG,
) -> Decimal:
    """Calculates the available balance including arranged and unarranged overdraft limits.

    Args:
        state: The current state of the smart contract.
        fetchers_config: Configuration for the fetchers used to retrieve parameters and balances.

    Returns:
        The total available balance including overdraft limits.
    """
    state = _append_to_state(state=state, fetchers_config=fetchers_config)

    rejection = state_utils.check_parameters_exist(state, {fetchers_config.denomination_param_id})
    assert rejection is None, rejection
    denomination = str(state.parameters[fetchers_config.denomination_param_id])

    available_balance = balance_utils.net_credit(
        balance_utils.get_available_balance(balances=state.balances, denomination=denomination)
    )

    arranged_overdraft_amount: Decimal = state.parameters.get(
        ARRANGED_OVERDRAFT_AMOUNT_PARAM_ID, Decimal(0)
    )  # type: ignore
    unarranged_overdraft_amount: Decimal = state.parameters.get(  # type: ignore
        UNARRANGED_OVERDRAFT_AMOUNT_PARAM_ID, Decimal(0)
    )

    return available_balance + arranged_overdraft_amount + unarranged_overdraft_amount


OverdraftLimitAvailableBalance = deposit_interfaces.AvailableBalance(
    calculate=get_overdraft_available_balance
)
