__smart_contract_feature__ = True
from datetime import datetime
from decimal import Decimal

# features
import feature_library.common.posting_utils as posting_utils
import feature_library.common.state_utils as state_utils

# contracts api
from contracts_api import (
    DefinedDateTime,
    ExpectedParameter,
    ParametersFilter,
    ParametersObservationFetcher,
    PostingInstructionType,
    Rejection,
    RejectionReason,
)

# inception sdk
from inception_sdk.vault.contracts.extensions.contracts_api_extensions import SmartContractVault

__smart_contract_feature__ = True

DENOMINATION_PARAM_ID = "&{denomination}"
DENOMINATION_PARAM = ExpectedParameter(
    id=DENOMINATION_PARAM_ID,
    triggers_pre_parameter_change_hook=False,
    triggers_post_parameter_change_hook=False,
)

DENOMINATION_LIVE_POF_ID = "denomination_live_fetcher"
DENOMINATION_LIVE_POF = ParametersObservationFetcher(
    fetcher_id=DENOMINATION_LIVE_POF_ID,
    at=DefinedDateTime.LIVE,
    filter=ParametersFilter(parameter_ids=[DENOMINATION_PARAM_ID]),
)

DENOMINATION_ET_POF_ID = "denomination_at_effective_datetime_fetcher"
DENOMINATION_ET_POF = ParametersObservationFetcher(
    fetcher_id=DENOMINATION_ET_POF_ID,
    at=DefinedDateTime.EFFECTIVE_DATETIME,
    filter=ParametersFilter(parameter_ids=[DENOMINATION_PARAM_ID]),
)

expected_parameters = [
    DENOMINATION_PARAM,
]

data_fetchers = [
    DENOMINATION_ET_POF,
    DENOMINATION_LIVE_POF,
]


def get_parameters(
    vault: SmartContractVault, fetcher_id: str = DENOMINATION_ET_POF_ID
) -> dict[str, str | datetime | Decimal | None]:
    """Retrieves the denomination parameters from a vault parameter observation.

    This function extracts the raw parameters dictionary from an observation
    retrieved via the specified fetcher ID.

    Args:
        vault (SmartContractVault): The vault object to query for observations.
        fetcher_id (str): The ID of the parameter observation fetcher.
            Defaults to DENOMINATION_ET_POF_ID.

    Returns:
        dict[str, str | datetime | Decimal | None]: A dictionary containing the
            observed parameter keys and values.
    """
    return vault.get_parameters_observation(fetcher_id=fetcher_id).parameters


def add_denomination_to_state(
    state: state_utils.SmartContractState,
    param_fetcher_id: str = DENOMINATION_ET_POF_ID,
) -> state_utils.SmartContractState:
    """Updates the contract state with denomination parameters fetched from the vault.

    This function acts as a wrapper that coordinates fetching parameters from
    the vault associated with the input state and appending them to a new
    state instance.

    Fetchers:
        Parameters:
            DENOMINATION_ET_POF_ID: Used to observe denomination-related values.

    Args:
        state (state_utils.SmartContractState): The current state object.
        param_fetcher_id (str): The ID of the fetcher used to retrieve parameters.
            Defaults to DENOMINATION_ET_POF_ID.

    Returns:
        state_utils.SmartContractState: A new state object containing the merged
            denomination parameters.
    """
    return state_utils.append_to_state(
        state=state,
        parameters=get_parameters(state.vault, param_fetcher_id),
    )


def validate_denomination(
    state: state_utils.SmartContractState,
    posting_instructions: posting_utils.PostingInstructionListAlias,
    denomination_param_id: str = DENOMINATION_PARAM.id,
) -> Rejection | None:
    """Validates a list of Posting Instructions for denomination.
    Handles all Posting Instruction Types.

    Fetchers:
        Parameters:
            denomination_at_effective_datetime_fetcher

    Args:
        state (SmartContractState):
        posting_instructions (PostingInstructionListAlias): List of Posting Instructions

    Returns:
        Optional[Rejection]: Returns Rejection if any Posting Instructions contain an
        denomination that does not match the denomination parameter.
    """
    if rejection := state_utils.check_parameters_exist(state, {denomination_param_id}):
        return rejection

    denomination: str = state.parameters[denomination_param_id]  # type: ignore

    custom_pi_denoms: set[str] = {
        posting.denomination
        for posting_instruction in filter(
            lambda pi: pi.type == PostingInstructionType.CUSTOM_INSTRUCTION, posting_instructions
        )
        for posting in posting_instruction.postings
    }
    non_custom_pi_denoms: set[str] = {
        posting_instruction.denomination
        for posting_instruction in filter(
            lambda pi: pi.type != PostingInstructionType.CUSTOM_INSTRUCTION, posting_instructions
        )
    }
    instruction_denoms: set[str] = custom_pi_denoms | non_custom_pi_denoms
    if invalid_denoms := instruction_denoms - {denomination}:
        offending_denomination = ",".join(sorted(invalid_denoms))
        return Rejection(
            message=(
                "Posting Instruction contains invalid denomination(s)."
                f" Valid denomination: {denomination}."
                f" Received denomination(s): {offending_denomination}."
            ),
            reason_code=RejectionReason.WRONG_DENOMINATION,
        )
    return None
