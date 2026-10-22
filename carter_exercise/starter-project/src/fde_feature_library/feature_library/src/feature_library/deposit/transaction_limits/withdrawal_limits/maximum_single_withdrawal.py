# Copyright @ 2026 Thought Machine Group Limited. All rights reserved.
"""Maximum Single Withdrawal limit feature."""

__smart_contract_feature__ = True

# standard libs
from datetime import datetime
from decimal import Decimal
from typing import NamedTuple

# feature library
import feature_library.common.balance_utils as balance_utils
import feature_library.common.denomination as denomination_module
import feature_library.common.posting_utils as posting_utils
import feature_library.common.state_utils as state_utils

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

MAX_WITHDRAWAL_PARAM_ID = "&{maximum_withdrawal}"
MAX_WITHDRAWAL_PARAM = ExpectedParameter(
    id=MAX_WITHDRAWAL_PARAM_ID,
    optional=True,
    triggers_pre_parameter_change_hook=False,
    triggers_post_parameter_change_hook=False,
)

expected_parameters = [
    MAX_WITHDRAWAL_PARAM,
    denomination_module.DENOMINATION_PARAM,
]

MAX_WITHDRAWAL_POF_ID = "maximum_withdrawal_pof"
MAX_WITHDRAWAL_POF = ParametersObservationFetcher(
    fetcher_id=MAX_WITHDRAWAL_POF_ID,
    at=DefinedDateTime.EFFECTIVE_DATETIME,
    filter=ParametersFilter(parameter_ids=[p.id for p in expected_parameters]),
)

data_fetchers = [MAX_WITHDRAWAL_POF]

MaximumSingleWithdrawalFetchersConfig = NamedTuple(
    "MaximumSingleWithdrawalFetchersConfig",
    [
        ("param_fetcher_id", str),
        ("denomination_param_id", str),
        ("maximum_withdrawal_param_id", str),
    ],
)
DEFAULT_MAXIMUM_SINGLE_WITHDRAWAL_FETCHERS_CONFIG = MaximumSingleWithdrawalFetchersConfig(
    param_fetcher_id=MAX_WITHDRAWAL_POF_ID,
    denomination_param_id=denomination_module.DENOMINATION_PARAM_ID,
    maximum_withdrawal_param_id=MAX_WITHDRAWAL_PARAM_ID,
)


def get_parameters(
    vault: SmartContractVault, param_fetcher_id: str = MAX_WITHDRAWAL_POF_ID
) -> dict[str, datetime | Decimal | str | None]:
    """Retrieve configuration parameters for the maximum single withdrawal limit feature.

    Args:
        vault: The SmartContractVault instance to query.
        param_fetcher_id: The unique identifier for the parameter fetcher.
            Defaults to `MAX_WITHDRAWAL_POF_ID`.

    Returns:
        Parameters for the maximum single withdrawal limit feature.

    """
    return vault.get_parameters_observation(fetcher_id=param_fetcher_id).parameters


def _append_to_state(
    state: state_utils.SmartContractState,
    param_fetcher_id: str = MAX_WITHDRAWAL_POF_ID,
) -> state_utils.SmartContractState:
    """Update the contract state with specific parameter observations.

    Args:
        state: The current state of the smart contract, containing the vault object.
        param_fetcher_id: The ID of the fetcher used to retrieve parameters.
            Defaults to `MAX_WITHDRAWAL_POF_ID`.

    Returns:
        A new state object containing the appended parameters.

    """
    return state_utils.append_to_state(
        state=state,
        parameters=get_parameters(state.vault, param_fetcher_id),
    )


def validate(
    state: state_utils.SmartContractState,
    postings: posting_utils.PostingInstructionListAlias,
    fetchers_config: MaximumSingleWithdrawalFetchersConfig = DEFAULT_MAXIMUM_SINGLE_WITHDRAWAL_FETCHERS_CONFIG,  # noqa: E501
) -> Rejection | None:
    """Reject the proposed postings if any amount is greater than the maximum withdrawal limit.

    Args:
        state: SmartContractState containing the vault object and effective datetime.
        postings: List of posting instructions to process.
        fetchers_config: Configuration for the required fetchers and parameters.

    Returns:
        A rejection if any posting exceeds the maximum withdrawal limit, otherwise None.

    """
    state = _append_to_state(state, fetchers_config.param_fetcher_id)
    if rejection := state_utils.check_parameters_exist(
        state, {fetchers_config.denomination_param_id}
    ):
        return rejection

    denomination: str = state.parameters[fetchers_config.denomination_param_id]  # type: ignore

    max_withdrawal: Decimal | None = state.parameters.get(
        fetchers_config.maximum_withdrawal_param_id
    )  # type: ignore

    if max_withdrawal is None:
        return None

    return next(
        (
            rejection
            for p in postings
            if (
                rejection := _validate_posting_against_max_withdrawal(
                    p, denomination, max_withdrawal
                )
            )
        ),
        None,
    )


def _validate_posting_against_max_withdrawal(
    posting: posting_utils.PostingInstructionTypeAlias, denomination: str, max_withdrawal: Decimal
) -> Rejection | None:
    """Check if the proposed posting exceeds the maximum withdrawal limit.

    Args:
        posting: The posting instruction to validate.
        denomination: The denomination to check the limit in.
        max_withdrawal: The maximum allowed withdrawal amount.

    Returns:
        A rejection if the limit is exceeded, otherwise None.

    """
    posting_value: Decimal = balance_utils.net_debit(
        balance_utils.get_available_balance(balances=posting.balances(), denomination=denomination)
    )
    if posting_value <= 0:
        return None
    elif posting_value > max_withdrawal:
        return Rejection(
            message=f"Transaction amount {abs(posting_value)} {denomination} is greater than "
            f"the maximum withdrawal amount {max_withdrawal} {denomination}.",
            reason_code=RejectionReason.AGAINST_TNC,
        )

    return None
