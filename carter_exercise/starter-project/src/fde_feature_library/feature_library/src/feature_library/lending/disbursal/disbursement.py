__smart_contract_feature__ = True

from datetime import datetime

# standard libs
from decimal import Decimal
from typing import NamedTuple

import feature_library.common.denomination as denomination

# feature library
import feature_library.common.posting_utils as posting_utils
import feature_library.common.state_utils as state_utils
import feature_library.lending.addresses as lending_addresses
import feature_library.lending.principal.principal as principal

# contracts api
from contracts_api import (
    DEFAULT_ADDRESS,
    CustomInstruction,
    DefinedDateTime,
    ExpectedParameter,
    ParametersFilter,
    ParametersObservationFetcher,
)

# inception sdk
from inception_sdk.vault.contracts.extensions.contracts_api_extensions import SmartContractVault

DISBURSEMENT_EVENT = "PRINCIPAL_DISBURSEMENT"

# Expected Parameters
DEPOSIT_ACCOUNT_PARAM_ID = "&{deposit_account}"
DEPOSIT_ACCOUNT_PARAM = ExpectedParameter(
    id=DEPOSIT_ACCOUNT_PARAM_ID,
    triggers_pre_parameter_change_hook=False,
    triggers_post_parameter_change_hook=False,
)

expected_parameters = [
    principal.PRINCIPAL_PARAM,
    DEPOSIT_ACCOUNT_PARAM,
    denomination.DENOMINATION_PARAM,
]


# data fetchers
DISBURSEMENT_PARAMS_ET_POF_ID = "DISBURSEMENT_PARAMS_ET_POF"
DISBURSEMENT_PARAMS_ET_POF = ParametersObservationFetcher(
    fetcher_id=DISBURSEMENT_PARAMS_ET_POF_ID,
    at=DefinedDateTime.EFFECTIVE_DATETIME,
    filter=ParametersFilter(parameter_ids=[p.id for p in expected_parameters]),
)


data_fetchers = [
    DISBURSEMENT_PARAMS_ET_POF,
]

DisbursementFetchersConfig = NamedTuple(
    "DisbursementFetchersConfig",
    [
        ("param_fetcher_id", str),
        ("principal_param_id", str),
        ("deposit_account_param_id", str),
        ("denomination_param_id", str),
    ],
)

DEFAULT_DISBURSEMENT_FETCHERS_CONFIG = DisbursementFetchersConfig(
    param_fetcher_id=DISBURSEMENT_PARAMS_ET_POF_ID,
    principal_param_id=principal.PRINCIPAL_PARAM_ID,
    deposit_account_param_id=DEPOSIT_ACCOUNT_PARAM_ID,
    denomination_param_id=denomination.DENOMINATION_PARAM_ID,
)


def get_parameters(
    vault: SmartContractVault, param_fetcher_id: str = DISBURSEMENT_PARAMS_ET_POF_ID
) -> dict[str, str | datetime | Decimal | None]:
    """Retrieves configuration parameters for the disbursement feature.

    Args:
        vault (SmartContractVault): The SmartContractVault instance to query.
        param_fetcher_id (str): The unique identifier for the parameter fetcher.
            Defaults to DISBURSEMENT_PARAMS_ET_POF_ID.

    Returns:
        dict[str, Decimal | str | None]: Parameters for the disbursement feature.
    """

    return vault.get_parameters_observation(fetcher_id=param_fetcher_id).parameters


def _append_to_state(
    state: state_utils.SmartContractState,
    param_fetcher_id: str = DISBURSEMENT_PARAMS_ET_POF_ID,
) -> state_utils.SmartContractState:
    """Append disbursement parameters to state.

    Args:
        state (state_utils.SmartContractState): Smart Contract State
        param_fetcher_id (str, optional): Fetcher id for required parameters. Defaults to
            DISBURSEMENT_PARAMS_ET_POF_ID.

    Returns:
        state_utils.SmartContractState: The updated state object.
    """
    return state_utils.append_to_state(
        state=state,
        parameters=get_parameters(state.vault, param_fetcher_id),
    )


def get_disbursement_custom_instruction(
    *,
    state: state_utils.SmartContractState,
    fetchers_config: DisbursementFetchersConfig = DEFAULT_DISBURSEMENT_FETCHERS_CONFIG,
    principal_address: str = lending_addresses.PRINCIPAL,
) -> list[CustomInstruction]:
    """Create disbursement custom instruction.

    Args:
        state (state_utils.SmartContractState): Smart Contract State
        denomination (str): The currency denomination.
        fetchers_config (DisbursementFetchersConfig, optional): Fetchers configuration.
            Defaults to DEFAULT_DISBURSEMENT_FETCHERS_CONFIG.
        principal_address (str, optional): The address to debit the principal from.
            Defaults to lending_addresses.PRINCIPAL.

    Returns:
        list[CustomInstruction]: Disbursement custom instructions
    """

    state = _append_to_state(state=state, param_fetcher_id=fetchers_config.param_fetcher_id)

    rejection = state_utils.check_parameters_exist(
        state=state,
        param_ids={
            fetchers_config.principal_param_id,
            fetchers_config.deposit_account_param_id,
            fetchers_config.denomination_param_id,
        },
    )
    assert rejection is None, rejection

    principal: Decimal = state.parameters.get(fetchers_config.principal_param_id)  # type: ignore
    deposit_account_id: str = state.parameters.get(fetchers_config.deposit_account_param_id)  # type: ignore
    denomination: str = state.parameters.get(fetchers_config.denomination_param_id)  # type: ignore

    postings = posting_utils.create_postings(
        amount=principal,
        debit_account=state.vault.account_id,
        credit_account=deposit_account_id,
        denomination=denomination,
        debit_address=principal_address,
        credit_address=DEFAULT_ADDRESS,
    )

    if postings:
        return [
            CustomInstruction(
                postings=postings,
                override_all_restrictions=True,
                instruction_details={
                    "description": f"Principal disbursement of {principal}",
                    "event": DISBURSEMENT_EVENT,
                },
            )
        ]

    return []
