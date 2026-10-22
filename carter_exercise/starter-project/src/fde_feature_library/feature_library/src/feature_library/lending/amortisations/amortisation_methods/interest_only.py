# Copyright @ 2026 Thought Machine Group Limited. All rights reserved.
"""Interest only feature."""

__smart_contract_feature__ = True

# standard libs
from decimal import Decimal
from typing import NamedTuple

import feature_library.common.balance_utils as balance_utils
import feature_library.common.denomination as denomination_module

# feature library
import feature_library.common.state_utils as state_utils
import feature_library.lending.addresses as lending_addresses
import feature_library.lending.amortisations.eia as eia_module
import feature_library.lending.term.term as term_helpers
from feature_library.lending.amortisations.amortisation_methods import (
    DEFAULT_TERM_DETAILS_FETCHERS_CONFIG,
    TermDetails,
    TermDetailsFetchersConfig,
)

from contracts_api import CustomInstruction

# contracts api

# inception sdk

AMORTISATION_METHOD = "INTEREST_ONLY"


ACCOUNT_ACTIVATION_EVENT = "ACCOUNT_ACTIVATION"

AmortiseFetchersConfig = NamedTuple(
    "AmortiseFetchersConfig",
    [
        ("denomination_param_id", str),
    ],
)
DEFAULT_AMORTISE_FETCHERS_CONFIG = AmortiseFetchersConfig(
    denomination_param_id=denomination_module.DENOMINATION_PARAM_ID,
)


def is_interest_only_loan(amortisation_method: str) -> bool:
    """Returns True if the amortisation_method is 'INTEREST_ONLY'."""
    return amortisation_method.upper() == AMORTISATION_METHOD


def term_details(
    state: state_utils.SmartContractState,
    fetchers_config: TermDetailsFetchersConfig = DEFAULT_TERM_DETAILS_FETCHERS_CONFIG,
) -> TermDetails:
    """Calculate the elapsed and remaining term for a loan using a counter-based approach.

    Args:
        state: The smart contract state.
        get_annual_interest_rate: callback function to get the annual interest rate.
            Not used but required for the interface.
        use_expected_term: Not used but required for the interface.
        principal_adjustments: Not used but required for the interface.
        fetchers_config: The fetchers configuration for retrieving term details.

    Returns:
        The elapsed and remaining term.
    """
    rejection = state_utils.check_parameters_exist(
        state=state,
        param_ids={
            fetchers_config.term_param_id,
            fetchers_config.denomination_param_id,
        },
    )
    assert rejection is None, rejection

    parameters = state.parameters
    balances = state.balances

    original_total_term = int(parameters[fetchers_config.term_param_id])  # type: ignore

    if state.effective_datetime == state.vault.get_account_activation_datetime():
        return TermDetails(elapsed=0, remaining=original_total_term)

    denomination: str = parameters[fetchers_config.denomination_param_id]  # type: ignore
    elapsed = term_helpers.get_elapsed_term(balances=balances, denomination=denomination)
    remaining = max(0, original_total_term - elapsed)

    return TermDetails(elapsed=elapsed, remaining=remaining)


def calculate_eia() -> Decimal:
    """Return 0 EIA for interest-only amortisation.

    Args:
        state: The smart contract state.
        get_annual_interest_rate: callback function to get the annual interest rate.
            Not used but required for the interface.
        use_expected_term: Not used but required for the interface.
        principal_amount: Not used but required for the interface.
        principal_adjustments: Not used but required for the interface.
        fetchers_config: The fetchers configuration for retrieving details.

    Returns:
        0 EIA.
    """
    return Decimal(0)


def amortise(
    state: state_utils.SmartContractState,
    event: str = ACCOUNT_ACTIVATION_EVENT,
    eia_address: str = lending_addresses.EIA,
    fetchers_config: AmortiseFetchersConfig = DEFAULT_AMORTISE_FETCHERS_CONFIG,
) -> list[CustomInstruction]:
    """Amortise a loan by calculating EIA and creating a custom instruction.

    Args:
        state: The smart contract state.
        event: Event string to be included in the CustomInstruction instruction_details.
        eia_address: The address to post the EIA to.
        fetchers_config: The fetchers configuration for retrieving EIA details.

    Returns:
        A list of custom instructions, empty if no changes to the EIA.
    """
    rejection = state_utils.check_parameters_exist(
        state=state,
        param_ids={
            fetchers_config.denomination_param_id,
        },
    )
    assert rejection is None, rejection

    updated_eia = calculate_eia()

    denomination: str = state.parameters[fetchers_config.denomination_param_id]  # type: ignore

    current_eia = balance_utils.balance_at_coordinates(
        balances=state.balances, address=eia_address, denomination=denomination
    )

    update_eia_postings = eia_module.update_eia(
        account_id=state.vault.account_id,
        denomination=denomination,
        current_eia=current_eia,
        updated_eia=updated_eia,
    )
    if not update_eia_postings:
        return []

    return [
        CustomInstruction(
            postings=update_eia_postings,
            instruction_details={
                "description": f"Updating EIA to {updated_eia}",
                "event": event,
            },
        )
    ]
