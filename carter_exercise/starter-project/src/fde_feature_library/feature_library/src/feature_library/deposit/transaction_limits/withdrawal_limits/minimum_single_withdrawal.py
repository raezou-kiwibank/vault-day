# Copyright @ 2026 Thought Machine Group Limited. All rights reserved.
"""Minimum Single Withdrawal limit feature."""

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

MIN_WITHDRAWAL_PARAM_ID = "&{minimum_withdrawal}"
MIN_WITHDRAWAL_PARAM = ExpectedParameter(
    id=MIN_WITHDRAWAL_PARAM_ID,
    optional=True,
    triggers_pre_parameter_change_hook=False,
    triggers_post_parameter_change_hook=False,
)

expected_parameters = [
    MIN_WITHDRAWAL_PARAM,
    denomination_module.DENOMINATION_PARAM,
]

MIN_WITHDRAWAL_POF_ID = "minimum_withdrawal_pof"
MIN_WITHDRAWAL_POF = ParametersObservationFetcher(
    fetcher_id=MIN_WITHDRAWAL_POF_ID,
    at=DefinedDateTime.EFFECTIVE_DATETIME,
    filter=ParametersFilter(parameter_ids=[p.id for p in expected_parameters]),
)

data_fetchers = [MIN_WITHDRAWAL_POF]

MinimumSingleWithdrawalFetchersConfig = NamedTuple(
    "MinimumSingleWithdrawalFetchersConfig",
    [
        ("param_fetcher_id", str),
        ("denomination_param_id", str),
        ("minimum_withdrawal_param_id", str),
    ],
)
DEFAULT_MINIMUM_SINGLE_WITHDRAWAL_FETCHERS_CONFIG = MinimumSingleWithdrawalFetchersConfig(
    param_fetcher_id=MIN_WITHDRAWAL_POF_ID,
    denomination_param_id=denomination_module.DENOMINATION_PARAM_ID,
    minimum_withdrawal_param_id=MIN_WITHDRAWAL_PARAM_ID,
)


def get_parameters(
    vault: SmartContractVault, param_fetcher_id: str = MIN_WITHDRAWAL_POF_ID
) -> dict[str, datetime | Decimal | str | None]:
    """Retrieves configuration parameters for the minimum single withdrawal limit feature.

    Args:
        vault: The SmartContractVault instance to query.
        param_fetcher_id: The unique identifier for the parameter fetcher.
            Defaults to `MIN_WITHDRAWAL_POF_ID`.

    Returns:
        Parameters for the minimum single withdrawal limit feature.
    """
    return vault.get_parameters_observation(fetcher_id=param_fetcher_id).parameters


def _append_to_state(
    state: state_utils.SmartContractState,
    param_fetcher_id: str = MIN_WITHDRAWAL_POF_ID,
) -> state_utils.SmartContractState:
    """Updates the contract state with specific parameter observations.

    Args:
        state: The current state of the smart contract, containing the vault object.
        param_fetcher_id: The ID of the fetcher used to retrieve parameters.
            Defaults to `MIN_WITHDRAWAL_POF_ID`.

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
    fetchers_config: MinimumSingleWithdrawalFetchersConfig = DEFAULT_MINIMUM_SINGLE_WITHDRAWAL_FETCHERS_CONFIG,  # noqa: E501
) -> Rejection | None:
    """Reject the proposed postings if any amount is less than the minimum allowed withdrawal limit.

    Args:
        state: SmartContractState containing the vault object and effective datetime.
        postings: List of posting instructions to process.
        fetchers_config: Configuration for the required fetchers and parameters.

    Returns:
        A rejection if any posting is below the minimum withdrawal limit, otherwise None.
    """
    state = _append_to_state(state, fetchers_config.param_fetcher_id)
    if rejection := state_utils.check_parameters_exist(
        state, {fetchers_config.denomination_param_id}
    ):
        return rejection

    denomination: str = state.parameters[fetchers_config.denomination_param_id]  # type: ignore

    minimum_withdrawal: Decimal | None = state.parameters.get(
        fetchers_config.minimum_withdrawal_param_id
    )  # type: ignore

    if minimum_withdrawal:
        for posting in postings:
            withdrawal_value: Decimal = balance_utils.net_debit(
                balance_utils.get_available_balance(
                    balances=posting.balances(), denomination=denomination
                )
            )

            if 0 < withdrawal_value < minimum_withdrawal:
                minimum_withdrawal_quantized = minimum_withdrawal.quantize(Decimal("1.e-3"))
                return Rejection(
                    message=f"Transaction amount {round(withdrawal_value, 5).normalize()} "
                    f"{denomination} is less than the minimum withdrawal amount "
                    f"{str(minimum_withdrawal_quantized).rstrip('0').rstrip('.')} {denomination}.",
                    reason_code=RejectionReason.AGAINST_TNC,
                )

    return None
