# Copyright @ 2026 Thought Machine Group Limited. All rights reserved.
"""Maximum Withdrawal By Payment Type limit feature."""

__smart_contract_feature__ = True

# standard libs
from datetime import datetime
from decimal import Decimal
from json import loads
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
    Posting,
    Rejection,
    RejectionReason,
)

# inception sdk
from inception_sdk.vault.contracts.extensions.contracts_api_extensions import SmartContractVault

MAX_WITHDRAWAL_BY_PAYMENT_TYPE_PARAM_ID = "&{maximum_payment_type_withdrawal}"
MAX_WITHDRAWAL_BY_PAYMENT_TYPE_PARAM = ExpectedParameter(
    id=MAX_WITHDRAWAL_BY_PAYMENT_TYPE_PARAM_ID,
    optional=True,
    triggers_pre_parameter_change_hook=False,
    triggers_post_parameter_change_hook=False,
)

expected_parameters = [
    MAX_WITHDRAWAL_BY_PAYMENT_TYPE_PARAM,
    denomination_module.DENOMINATION_PARAM,
]

MAX_WITHDRAWAL_BY_PAYMENT_TYPE_POF_ID = "maximum_withdrawal_by_payment_type_pof"
MAX_WITHDRAWAL_BY_PAYMENT_TYPE_POF = ParametersObservationFetcher(
    fetcher_id=MAX_WITHDRAWAL_BY_PAYMENT_TYPE_POF_ID,
    at=DefinedDateTime.EFFECTIVE_DATETIME,
    filter=ParametersFilter(parameter_ids=[p.id for p in expected_parameters]),
)

data_fetchers = [MAX_WITHDRAWAL_BY_PAYMENT_TYPE_POF]

PAYMENT_TYPE = "PAYMENT_TYPE"

MaximumWithdrawalByPaymentTypeFetchersConfig = NamedTuple(
    "MaximumWithdrawalByPaymentTypeFetchersConfig",
    [
        ("param_fetcher_id", str),
        ("denomination_param_id", str),
        ("maximum_payment_type_withdrawal_param_id", str),
    ],
)
DEFAULT_MAXIMUM_WITHDRAWAL_BY_PAYMENT_TYPE_FETCHERS_CONFIG = (
    MaximumWithdrawalByPaymentTypeFetchersConfig(  # noqa: E501
        param_fetcher_id=MAX_WITHDRAWAL_BY_PAYMENT_TYPE_POF_ID,
        denomination_param_id=denomination_module.DENOMINATION_PARAM_ID,
        maximum_payment_type_withdrawal_param_id=MAX_WITHDRAWAL_BY_PAYMENT_TYPE_PARAM_ID,
    )
)


def get_parameters(
    vault: SmartContractVault,
    param_fetcher_id: str = MAX_WITHDRAWAL_BY_PAYMENT_TYPE_POF_ID,
) -> dict[str, datetime | Decimal | str | None]:
    """Retrieves configuration parameters for the maximum withdrawal by payment type limit feature.

    Args:
        vault: The SmartContractVault instance to query.
        param_fetcher_id: The unique identifier for the parameter fetcher.
            Defaults to `MAX_WITHDRAWAL_BY_PAYMENT_TYPE_POF_ID`.

    Returns:
        Parameters for the maximum withdrawal by payment type limit feature.
    """
    return vault.get_parameters_observation(fetcher_id=param_fetcher_id).parameters


def _append_to_state(
    state: state_utils.SmartContractState,
    param_fetcher_id: str = MAX_WITHDRAWAL_BY_PAYMENT_TYPE_POF_ID,
) -> state_utils.SmartContractState:
    """Updates the contract state with specific parameter observations.

    Args:
        state: The current state of the smart contract, containing the vault object.
        param_fetcher_id: The ID of the fetcher used to retrieve parameters.
            Defaults to `MAX_WITHDRAWAL_BY_PAYMENT_TYPE_POF_ID`.

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
    fetchers_config: MaximumWithdrawalByPaymentTypeFetchersConfig = DEFAULT_MAXIMUM_WITHDRAWAL_BY_PAYMENT_TYPE_FETCHERS_CONFIG,  # noqa: E501
) -> Rejection | None:
    """Reject the proposed postings if the withdrawal value exceeds the PAYMENT_TYPE limit.

    Args:
        state: SmartContractState containing the vault object and effective datetime.
        postings: List of posting instructions to process.
        fetchers_config: Configuration for the required fetchers and parameters.

    Returns:
        A rejection if any posting exceeds the payment type limit, otherwise None.
    """
    state = _append_to_state(state, fetchers_config.param_fetcher_id)
    if rejection := state_utils.check_parameters_exist(
        state, {fetchers_config.denomination_param_id}
    ):
        return rejection

    denomination: str = state.parameters[fetchers_config.denomination_param_id]  # type: ignore

    max_withdrawal_by_payment_type_str: str | None = state.parameters.get(
        fetchers_config.maximum_payment_type_withdrawal_param_id
    )  # type: ignore

    if not max_withdrawal_by_payment_type_str:
        return None

    max_withdrawal_by_payment_type: dict[str, Decimal] = {
        k: Decimal(v) for k, v in loads(max_withdrawal_by_payment_type_str).items()
    }

    return next(
        (
            rejection
            for p in postings
            if (
                rejection := _validate_posting_against_withdrawal_limits(
                    p, denomination, max_withdrawal_by_payment_type
                )
            )
        ),
        None,
    )


def _validate_posting_against_withdrawal_limits(
    posting: Posting, denomination: str, max_withdrawal_by_payment_type: dict[str, Decimal]
) -> Rejection | None:
    payment_type = posting.instruction_details.get(PAYMENT_TYPE)

    if not (payment_type and payment_type in max_withdrawal_by_payment_type):
        return None

    withdrawal_limit: Decimal = max_withdrawal_by_payment_type[payment_type]
    posting_value = balance_utils.net_debit(
        balance_utils.get_available_balance(balances=posting.balances(), denomination=denomination)
    )
    if posting_value <= 0:
        return None
    elif withdrawal_limit < posting_value:
        return Rejection(
            message=f"Transaction amount {posting_value:0.2f} {denomination} is "
            f"more than the maximum withdrawal amount {withdrawal_limit} "
            f"{denomination} allowed for the the payment type {payment_type}.",
            reason_code=RejectionReason.AGAINST_TNC,
        )
    return None
