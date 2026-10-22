# Copyright @ 2026 Thought Machine Group Limited. All rights reserved.
__smart_contract_feature__ = True

# standard libs
from datetime import datetime
from decimal import Decimal
from typing import NamedTuple

# feature library
import feature_library.common.balance_utils as balance_utils
import feature_library.common.denomination as denomination
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

# Parameters
MINIMUM_LOAN_PRINCIPAL_PARAM_ID = "&{minimum_loan_principal}"
MINIMUM_LOAN_PRINCIPAL_PARAM = ExpectedParameter(
    id=MINIMUM_LOAN_PRINCIPAL_PARAM_ID,
    optional=True,
    triggers_pre_parameter_change_hook=False,
    triggers_post_parameter_change_hook=False,
)

expected_parameters = [
    MINIMUM_LOAN_PRINCIPAL_PARAM,
    denomination.DENOMINATION_PARAM,
]

# Fetchers
MINIMUM_LOAN_PRINCIPAL_ET_POF_ID = "minimum_loan_principal_et_pof"
MINIMUM_LOAN_PRINCIPAL_ET_POF = ParametersObservationFetcher(
    fetcher_id=MINIMUM_LOAN_PRINCIPAL_ET_POF_ID,
    at=DefinedDateTime.EFFECTIVE_DATETIME,
    filter=ParametersFilter(parameter_ids=[p.id for p in expected_parameters]),
)

data_fetchers = [
    MINIMUM_LOAN_PRINCIPAL_ET_POF,
]

MinimumLoanPrincipalFetchersConfig = NamedTuple(
    "MinimumLoanPrincipalFetchersConfig",
    [
        ("param_fetcher_id", str),
        ("minimum_loan_principal_param_id", str),
        ("denomination_param_id", str),
    ],
)

DEFAULT_MINIMUM_LOAN_PRINCIPAL_FETCHERS_CONFIG = MinimumLoanPrincipalFetchersConfig(
    param_fetcher_id=MINIMUM_LOAN_PRINCIPAL_ET_POF_ID,
    minimum_loan_principal_param_id=MINIMUM_LOAN_PRINCIPAL_PARAM_ID,
    denomination_param_id=denomination.DENOMINATION_PARAM_ID,
)


def get_parameters(
    vault: SmartContractVault, param_fetcher_id: str = MINIMUM_LOAN_PRINCIPAL_ET_POF_ID
) -> dict[str, datetime | Decimal | str | None]:
    """Retrieves configuration parameters for the minimum loan principal feature.

    Args:
        vault: The SmartContractVault instance to query.
        param_fetcher_id: The unique identifier for the parameter fetcher.
            Defaults to `MINIMUM_LOAN_PRINCIPAL_ET_POF_ID`.

    Returns:
        Parameters for the minimum loan principal feature.
    """
    return vault.get_parameters_observation(fetcher_id=param_fetcher_id).parameters


def _append_to_state(
    state: state_utils.SmartContractState,
    fetchers_config: MinimumLoanPrincipalFetchersConfig = (
        DEFAULT_MINIMUM_LOAN_PRINCIPAL_FETCHERS_CONFIG
    ),
) -> state_utils.SmartContractState:
    """Appends feature-specific parameters to the state.

    Args:
        state: The current state of the smart contract.
        fetchers_config: Configuration for the fetchers.

    Returns:
        The updated state object.
    """
    parameters = get_parameters(state.vault, fetchers_config.param_fetcher_id)

    return state_utils.append_to_state(
        state=state,
        parameters=parameters,
    )


def validate(
    *,
    state: state_utils.SmartContractState,
    postings: posting_utils.PostingInstructionListAlias,
    fetchers_config: MinimumLoanPrincipalFetchersConfig = (
        DEFAULT_MINIMUM_LOAN_PRINCIPAL_FETCHERS_CONFIG
    ),
) -> Rejection | None:
    """Validates proposed postings against the minimum loan principal limit.

    Args:
        state: The current state of the smart contract.
        postings: A list of proposed posting instructions.
        fetchers_config: Configuration for the feature's fetchers and parameters.

    Returns:
        A rejection if the loan amount is below the limit, otherwise None.
    """
    state = _append_to_state(state, fetchers_config)

    # Ensure required denomination parameter exists in state
    rejection = state_utils.check_parameters_exist(state, {fetchers_config.denomination_param_id})
    assert rejection is None, rejection

    minimum_loan_amount: Decimal | None = state.parameters.get(
        fetchers_config.minimum_loan_principal_param_id
    )  # type: ignore

    if minimum_loan_amount is None:
        return None

    denomination: str = state.parameters[fetchers_config.denomination_param_id]  # type: ignore

    return next(
        (
            Rejection(
                message=(
                    f"Cannot create loan smaller than minimum loan amount limit of: "
                    f"{minimum_loan_amount}."
                ),
                reason_code=RejectionReason.AGAINST_TNC,
            )
            for posting in postings
            if 0
            < balance_utils.net_debit(
                bal=balance_utils.get_available_balance(
                    balances=posting.balances(), denomination=denomination
                )
            )
            < minimum_loan_amount
        ),
        None,
    )
