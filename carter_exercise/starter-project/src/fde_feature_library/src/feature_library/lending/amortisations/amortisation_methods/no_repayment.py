# Copyright @ 2026 Thought Machine Group Limited. All rights reserved.
"""No repayment feature."""

__smart_contract_feature__ = True

# standard libs
from datetime import datetime
from decimal import Decimal
from typing import NamedTuple

from dateutil.relativedelta import relativedelta

import feature_library.common.balance_utils as balance_utils
import feature_library.common.denomination as denomination_module

# feature library
import feature_library.common.state_utils as state_utils
import feature_library.lending.addresses as lending_addresses
import feature_library.lending.amortisations.eia as eia_module
import feature_library.lending.term.term as term_helpers
from feature_library.lending.amortisations.amortisation_methods import (
    TermDetails,
)

from contracts_api import CustomInstruction

AMORTISATION_METHOD = "NO_REPAYMENT"


ACCOUNT_ACTIVATION_EVENT = "ACCOUNT_ACTIVATION"

TermDetailsFetchersConfig = NamedTuple(
    "TermDetailsFetchersConfig",
    [
        ("term_param_id", str),
    ],
)
DEFAULT_TERM_DETAILS_FETCHERS_CONFIG = TermDetailsFetchersConfig(
    term_param_id=term_helpers.TERM_PARAM_ID,
)

AmortiseFetchersConfig = NamedTuple(
    "AmortiseFetchersConfig",
    [
        ("denomination_param_id", str),
    ],
)
DEFAULT_AMORTISE_FETCHERS_CONFIG = AmortiseFetchersConfig(
    denomination_param_id=denomination_module.DENOMINATION_PARAM_ID,
)


def is_no_repayment_loan(amortisation_method: str) -> bool:
    """Returns True if the amortisation_method is 'NO_REPAYMENT'."""
    return amortisation_method.upper() == AMORTISATION_METHOD


def calculate_eia() -> Decimal:
    """Return 0 EIA for no repayment amortisation.

    Args:
        state: The smart contract state.
        get_annual_interest_rate: callback function to get the annual interest rate.
            Not used but required for the interface.
        use_expected_term: Not used but required for the interface.
        principal_amount: Not used but required for the interface.
        principal_adjustments: Not used but required for the interface.
        fetchers_config: The fetchers configuration for retrieving EIA details.

    Returns:
        0 EIA.
    """
    return Decimal(0)


def term_details(
    state: state_utils.SmartContractState,
    fetchers_config: TermDetailsFetchersConfig = DEFAULT_TERM_DETAILS_FETCHERS_CONFIG,
) -> TermDetails:
    """Calculate the elapsed and remaining term for a loan based on execution time.

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
        },
    )
    assert rejection is None, rejection

    vault = state.vault
    effective_datetime = state.effective_datetime
    parameters = state.parameters

    # Given that a monthly due amount calculation will not be run, and no term counter populated.
    # we will fallback to a term calculation based on the execution time relative
    # to the loan start time.
    original_total_term = int(parameters[fetchers_config.term_param_id])  # type: ignore
    loan_start_date = vault.get_account_activation_datetime()

    # in the event the loan has not started, do not use negative values
    effective_datetime = max(loan_start_date, effective_datetime)

    delta = relativedelta(effective_datetime, loan_start_date)
    delta_months = delta.years * 12 + delta.months
    remaining_months = original_total_term - delta_months

    # in the event for some reason the time is past the original term time,
    # cap this value at the original term
    if remaining_months < 0:
        return TermDetails(elapsed=original_total_term, remaining=0)

    return TermDetails(elapsed=delta_months, remaining=remaining_months)


def get_balloon_payment_datetime(state: state_utils.SmartContractState) -> datetime:
    """Calculates the balloon payment datetime.

    Args:
        state: The smart contract state.

    Returns:
        datetime: The balloon payment datetime.
    """
    vault = state.vault
    parameters = state.parameters

    balloon_payment_start_date = vault.get_account_activation_datetime()
    original_total_term = int(parameters[term_helpers.TERM_PARAM_ID])  # type: ignore
    balloon_payment_delta_days = int(
        parameters.get("balloon_payment_days_delta", 0)  # type: ignore
    )
    return balloon_payment_start_date + relativedelta(
        days=balloon_payment_delta_days, months=original_total_term
    )


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
