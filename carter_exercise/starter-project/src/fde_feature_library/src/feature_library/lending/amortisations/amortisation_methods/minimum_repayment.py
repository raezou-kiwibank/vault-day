# Copyright @ 2026 Thought Machine Group Limited. All rights reserved.
"""Minimum repayment feature."""

__smart_contract_feature__ = True

# standard libs
from decimal import Decimal
from typing import Callable, NamedTuple

# feature library
import feature_library.common.application_precision as application_precision
import feature_library.common.balance_utils as balance_utils
import feature_library.common.denomination as denomination
import feature_library.common.state_utils as state_utils
import feature_library.lending.addresses as lending_addresses
import feature_library.lending.amortisations.amortisation_methods.declining_principal as declining_principal  # noqa: E501
import feature_library.lending.amortisations.eia as eia_module
import feature_library.lending.interfaces as lending_interfaces
import feature_library.lending.principal.principal as lending_principal
import feature_library.lending.term.term as term_helpers
from feature_library.lending.amortisations.amortisation_methods import (
    TermDetails,
)

from contracts_api import (
    CustomInstruction,
    DefinedDateTime,
    ExpectedParameter,
    ParametersFilter,
    ParametersObservationFetcher,
)

AMORTISATION_METHOD = "MINIMUM_REPAYMENT_WITH_BALLOON_PAYMENT"


ACCOUNT_ACTIVATION_EVENT = "ACCOUNT_ACTIVATION"

# Parameters
BALLOON_EMI_AMOUNT_PARAM_ID = "&{balloon_emi_amount}"
BALLOON_EMI_AMOUNT_PARAM = ExpectedParameter(
    id=BALLOON_EMI_AMOUNT_PARAM_ID,
    triggers_pre_parameter_change_hook=False,
    triggers_post_parameter_change_hook=False,
)

BALLOON_PAYMENT_AMOUNT_PARAM_ID = "&{balloon_payment_amount}"
BALLOON_PAYMENT_AMOUNT_PARAM = ExpectedParameter(
    id=BALLOON_PAYMENT_AMOUNT_PARAM_ID,
    triggers_pre_parameter_change_hook=False,
    triggers_post_parameter_change_hook=False,
)

expected_parameters = [
    BALLOON_EMI_AMOUNT_PARAM,
    BALLOON_PAYMENT_AMOUNT_PARAM,
    lending_principal.PRINCIPAL_PARAM,
    term_helpers.TERM_PARAM,
    application_precision.APPLICATION_PRECISION_PARAM,
]

# Fetchers
MINIMUM_REPAYMENT_POF_ID = "minimum_repayment_pof"
MINIMUM_REPAYMENT_POF = ParametersObservationFetcher(
    fetcher_id=MINIMUM_REPAYMENT_POF_ID,
    at=DefinedDateTime.EFFECTIVE_DATETIME,
    filter=ParametersFilter(parameter_ids=[p.id for p in expected_parameters]),
)

data_fetchers = [
    MINIMUM_REPAYMENT_POF,
]

# Fetchers Config
CalculateEiaFetchersConfig = NamedTuple(
    "CalculateEiaFetchersConfig",
    [
        ("principal_param_id", str),
        ("term_param_id", str),
        ("application_precision_param_id", str),
        ("param_observation_fetcher_id", str),
    ],
)
DEFAULT_CALCULATE_EIA_FETCHERS_CONFIG = CalculateEiaFetchersConfig(
    principal_param_id=lending_principal.PRINCIPAL_PARAM_ID,
    term_param_id=term_helpers.TERM_PARAM_ID,
    application_precision_param_id=application_precision.APPLICATION_PRECISION_PARAM_ID,
    param_observation_fetcher_id=MINIMUM_REPAYMENT_POF_ID,
)

TermDetailsFetchersConfig = NamedTuple(
    "TermDetailsFetchersConfig",
    [
        ("denomination_param_id", str),
        ("term_param_id", str),
    ],
)
DEFAULT_TERM_DETAILS_FETCHERS_CONFIG = TermDetailsFetchersConfig(
    denomination_param_id=denomination.DENOMINATION_PARAM_ID,
    term_param_id=term_helpers.TERM_PARAM_ID,
)


def is_minimum_repayment_loan(amortisation_method: str) -> bool:
    """Returns True if the amortisation_method is 'MINIMUM_REPAYMENT_WITH_BALLOON_PAYMENT'."""
    return amortisation_method.upper() == AMORTISATION_METHOD


def calculate_eia(
    state: state_utils.SmartContractState,
    get_annual_interest_rate: Callable[..., Decimal],
    principal_amount: Decimal | None = None,
    principal_adjustments: list[lending_interfaces.PrincipalAdjustment] | None = None,
    fetchers_config: CalculateEiaFetchersConfig = DEFAULT_CALCULATE_EIA_FETCHERS_CONFIG,
) -> Decimal:
    """Extract relevant data required and calculate minimum repayment EIA.

    Args:
        state: The smart contract state.
        use_expected_term: If True, the remaining term is purely based on original and
            elapsed term, ignoring any adjustments etc. If False, it is calculated based on
            principal, interest rate and EIA.
        principal_amount: The principal amount used for amortisation.
            If no value provided, the principal set on parameter level is used.
        get_annual_interest_rate: callback function to get the annual interest rate
        principal_adjustments: Features used to adjust the principal that is amortised.
            If no value provided, no adjustment is made to the principal.
        fetchers_config: The fetchers configuration for retrieving EIA details.

    Returns:
        The EIA amount.
    """
    rejection = state_utils.check_parameters_exist(
        state=state,
        param_ids={
            fetchers_config.principal_param_id,
            fetchers_config.term_param_id,
            fetchers_config.application_precision_param_id,
        },
    )
    assert rejection is None, rejection

    parameters = state.parameters
    # Check if this is a balloon payment loan with a fixed EIA or a fixed Balloon payment.
    static_emi: Decimal = parameters[BALLOON_EMI_AMOUNT_PARAM_ID]  # type: ignore

    # A fixed EIA that is defined at activation.
    # If there exists a predefined static EIA, then skip the needed calculations.
    # If the value is unset then assume that the EIA is not static
    if static_emi:
        return static_emi

    # Set assume that there is no balloon payment if the value is unset.
    balloon_payment_amount: Decimal = parameters.get(BALLOON_PAYMENT_AMOUNT_PARAM_ID, Decimal(0))  # type: ignore

    interest_rate: Decimal = (
        Decimal(0)
        if not get_annual_interest_rate
        else declining_principal.parameter_utils.yearly_to_monthly_rate(
            get_annual_interest_rate(state=state)
        )
    )
    principal: Decimal = (  # type: ignore
        parameters[fetchers_config.principal_param_id]
        if principal_amount is None
        else principal_amount
    )

    if principal_adjustments:
        principal += Decimal(
            sum(
                adjustment.calculate_principal_adjustment(state=state)
                for adjustment in principal_adjustments
            )
        )

    the_term_details: TermDetails = term_details(
        state=state,
    )
    application_precision = int(state.parameters[fetchers_config.application_precision_param_id])  # type: ignore

    return declining_principal.apply_declining_principal_formula(
        remaining_principal=principal,
        interest_rate=interest_rate,
        remaining_term=the_term_details.remaining,
        fulfillment_precision=application_precision,
        lump_sum_amount=balloon_payment_amount,
    )


def term_details(
    state: state_utils.SmartContractState,
    fetchers_config: TermDetailsFetchersConfig = DEFAULT_TERM_DETAILS_FETCHERS_CONFIG,
) -> TermDetails:
    """Calculate the elapsed and remaining term for a loan using a counter-based approach.

    Args:
        state: The smart contract state.
        use_expected_term: Not used but required for the interface.
        interest_rate: Not used but required for the interface.
        principal_adjustments: Not used but required for the interface.
        fetchers_config: The fetchers configuration for retrieving term details.

    Returns:
        The elapsed and remaining term.
    """
    vault = state.vault
    effective_datetime = state.effective_datetime
    balances = state.balances
    parameters = state.parameters

    original_total_term = int(parameters[fetchers_config.term_param_id])  # type: ignore

    # this allows us to avoid fetching balances in activation hook
    if effective_datetime == vault.get_account_activation_datetime():
        # in account activation, elapsed is 0 and the remaining term is the parameter value
        return TermDetails(elapsed=0, remaining=original_total_term)

    denomination: str = parameters[fetchers_config.denomination_param_id]  # type: ignore

    elapsed = term_helpers.get_elapsed_term(balances=balances, denomination=denomination)
    expected_remaining_term = original_total_term - elapsed

    return TermDetails(elapsed=elapsed, remaining=expected_remaining_term)


def amortise(
    state: state_utils.SmartContractState,
    get_annual_interest_rate: Callable[..., Decimal],
    principal_amount: Decimal | None = None,
    principal_adjustments: list[lending_interfaces.PrincipalAdjustment] | None = None,
    event: str = ACCOUNT_ACTIVATION_EVENT,
    eia_address: str = lending_addresses.EIA,
    fetchers_config: eia_module.AmortiseFetchersConfig = (
        eia_module.DEFAULT_AMORTISE_FETCHERS_CONFIG
    ),
) -> list[CustomInstruction]:
    """Amortise a loan by calculating EIA and creating a custom instruction.

    Args:
        state: The smart contract state.
        principal_amount: The principal amount used for amortisation.
        get_annual_interest_rate: callback function to get the annual interest rate
        principal_adjustments: Features used to adjust the principal that is amortised.
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

    updated_eia = calculate_eia(
        state=state,
        get_annual_interest_rate=get_annual_interest_rate,
        principal_amount=principal_amount,
        principal_adjustments=principal_adjustments,
    )

    denomination: str = state.parameters[fetchers_config.denomination_param_id]  # type: ignore

    current_eia = balance_utils.balance_at_coordinates(
        balances=state.balances, address=eia_address, denomination=denomination
    )

    update_eia_postings = eia_module.update_eia(
        account_id=state.vault.account_id,
        denomination=denomination,
        current_eia=current_eia,
        updated_eia=updated_eia,
        eia_address=eia_address,
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
