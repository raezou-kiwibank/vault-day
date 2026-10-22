# Copyright @ 2026 Thought Machine Group Limited. All rights reserved.
"""Declining principal feature."""

__smart_contract_feature__ = True

# standard libs
import math
from decimal import ROUND_CEILING, ROUND_HALF_UP, Decimal
from typing import Callable, NamedTuple

# feature library
import feature_library.common.application_precision as application_precision
import feature_library.common.balance_utils as balance_utils
import feature_library.common.denomination as denomination_module
import feature_library.common.parameter_utils as parameter_utils
import feature_library.common.state_utils as state_utils
import feature_library.common.utils as utils
import feature_library.lending.addresses as lending_addresses
import feature_library.lending.amortisations.eia as eia_module
import feature_library.lending.interfaces as lending_interfaces
import feature_library.lending.principal.principal as lending_principal
import feature_library.lending.term.term as term_helpers
from feature_library.lending.amortisations.amortisation_methods import (
    TermDetails,
)

from contracts_api import CustomInstruction

PrincipalAndInterestRate = NamedTuple(
    "PrincipalAndInterestRate",
    [
        ("principal", Decimal),
        ("interest_rate", Decimal),
    ],
)


ACCOUNT_ACTIVATION_EVENT = "ACCOUNT_ACTIVATION"

AMORTISATION_METHOD = "DECLINING_PRINCIPAL"

TermDetailsFetchersConfig = NamedTuple(
    "TermDetailsFetchersConfig",
    [
        ("denomination_param_id", str),
        ("term_param_id", str),
        ("principal_address", str),
        ("eia_address", str),
    ],
)
DEFAULT_TERM_DETAILS_FETCHERS_CONFIG = TermDetailsFetchersConfig(
    denomination_param_id=denomination_module.DENOMINATION_PARAM_ID,
    term_param_id=term_helpers.TERM_PARAM_ID,
    principal_address=lending_addresses.PRINCIPAL,
    eia_address=lending_addresses.EIA,
)

CalculateEiaFetchersConfig = NamedTuple(
    "CalculateEiaFetchersConfig",
    [
        ("principal_param_id", str),
        ("term_param_id", str),
        ("application_precision_param_id", str),
    ],
)
DEFAULT_CALCULATE_EIA_FETCHERS_CONFIG = CalculateEiaFetchersConfig(
    principal_param_id=lending_principal.PRINCIPAL_PARAM_ID,
    term_param_id=term_helpers.TERM_PARAM_ID,
    application_precision_param_id=application_precision.APPLICATION_PRECISION_PARAM_ID,
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


def is_declining_principal_loan(amortisation_method: str) -> bool:
    """Return True if the amortisation_method is 'DECLINING_PRINCIPAL'.

    Args:
        amortisation_method: The amortisation method to check.

    Returns:
        True if the amortisation method is 'DECLINING_PRINCIPAL', False otherwise.
    """
    return amortisation_method.upper() == AMORTISATION_METHOD


def term_details(
    state: state_utils.SmartContractState,
    get_annual_interest_rate: Callable[..., Decimal],
    use_expected_term: bool = True,
    principal_adjustments: list[lending_interfaces.PrincipalAdjustment] | None = None,
    fetchers_config: TermDetailsFetchersConfig = DEFAULT_TERM_DETAILS_FETCHERS_CONFIG,
) -> TermDetails:
    """Calculate the elapsed and remaining term for a loan.

    Args:
        state: The smart contract state.
        get_annual_interest_rate: callback function to get the annual interest rate
        use_expected_term: If True, the remaining term is purely based on original and
            elapsed term, ignoring any adjustments etc. If False, it is calculated based on
            principal, interest rate and EIA.
        principal_adjustments: Features used to adjust the principal that is amortised.
            If no value provided, no adjustment is made to the principal.
        fetchers_config: The fetchers configuration for retrieving term and principal details.

    Returns:
        The elapsed and remaining term.
    """
    vault = state.vault
    effective_datetime = state.effective_datetime
    balances = state.balances
    parameters = state.parameters

    rejection = state_utils.check_parameters_exist(
        state,
        param_ids={
            fetchers_config.denomination_param_id,
        },
    )
    assert rejection is None, rejection

    original_total_term = int(parameters[fetchers_config.term_param_id])  # type: ignore

    # this allows us to avoid fetching balances in activation hook
    if effective_datetime == vault.get_account_activation_datetime():
        # in account activation, elapsed is 0 and the remaining term is the parameter value
        return TermDetails(elapsed=0, remaining=original_total_term)

    denomination: str = parameters[fetchers_config.denomination_param_id]  # type: ignore

    principal_balance = balance_utils.balance_at_coordinates(
        balances=balances,
        address=fetchers_config.principal_address,
        denomination=denomination,
    )

    elapsed = term_helpers.get_elapsed_term(balances=balances, denomination=denomination)

    # This is to handle the scenario where the loan has been fully repaid (as a result of an early
    # repayment or otherwise) but the account has been left open
    expected_remaining_term = (original_total_term - elapsed) if principal_balance > 0 else 0
    if use_expected_term:
        return TermDetails(elapsed=elapsed, remaining=expected_remaining_term)

    eia = balance_utils.balance_at_coordinates(
        balances=balances,
        address=lending_addresses.EIA,
        denomination=denomination,
    )
    # eia can be 0 outside of activation if we've had to reset it (e.g. conversion) or if the loan
    # didn't originally require amortising (e.g. interest only period)
    if eia == 0:
        return TermDetails(elapsed=elapsed, remaining=expected_remaining_term)

    monthly_interest_rate: Decimal = (
        parameter_utils.yearly_to_monthly_rate(get_annual_interest_rate(state=state))
        if get_annual_interest_rate is not None
        else Decimal(0)
    )
    adjusted_principal: Decimal = principal_balance + Decimal(
        sum(
            adjustment.calculate_principal_adjustment(state=state)
            for adjustment in principal_adjustments or []
        )
    )

    remaining: int = calculate_remaining_term(
        eia=eia,
        remaining_principal=adjusted_principal,
        monthly_interest_rate=monthly_interest_rate,
    )

    # We need to use min here because the calculated value will not handle scenarios where
    # the principal hasn't reduced but the elapsed term has increased, for example, during a
    # repayment holiday
    remaining = min(remaining, expected_remaining_term)

    return TermDetails(elapsed=elapsed, remaining=remaining)


def calculate_remaining_term(
    eia: Decimal,
    remaining_principal: Decimal,
    monthly_interest_rate: Decimal,
    decimal_places: int = 2,
    rounding: str = ROUND_HALF_UP,
) -> int:
    """Calculate the remaining term using the amortisation formula.

    Formula: math.log((EIA/(EIA - P*R)), (1+R)), where:
    EIA is the equated monthly instalment.
    P is the remaining principal.
    R is the monthly interest rate.

    Args:
        eia: The equated monthly instalment.
        remaining_principal: The remaining principal.
        monthly_interest_rate: The monthly interest rate.
        decimal_places: The number of decimal places to round to.
        rounding: The type of rounding strategy to use.

    Returns:
        The remaining term left on the loan.
    """
    if eia == Decimal(0):
        return 0

    remaining_term = (
        Decimal(
            math.log(
                (eia / (eia - (remaining_principal * monthly_interest_rate))),
                (1 + monthly_interest_rate),
            )
        )
        if monthly_interest_rate > Decimal(0)
        else remaining_principal / eia
    )

    # we use ceil to ensure that 'partial' terms, after rounding, are recognised as a full term
    return int(
        utils.round_decimal(
            amount=remaining_term, decimal_places=decimal_places, rounding=rounding
        ).to_integral_exact(rounding=ROUND_CEILING)
    )


def calculate_eia(
    state: state_utils.SmartContractState,
    get_annual_interest_rate: Callable[..., Decimal],
    use_expected_term: bool = True,
    principal_amount: Decimal | None = None,
    principal_adjustments: list[lending_interfaces.PrincipalAdjustment] | None = None,
    fetchers_config: CalculateEiaFetchersConfig = DEFAULT_CALCULATE_EIA_FETCHERS_CONFIG,
) -> Decimal:
    """Extract relevant data required and calculate declining principal EIA.

    Args:
        state: The smart contract state.
        get_annual_interest_rate: callback function to get the annual interest rate
        use_expected_term: If True, the remaining term is purely based on original and
            elapsed term, ignoring any adjustments etc. If False, it is calculated based on
            principal, interest rate and EIA.
        principal_amount: The principal amount used for amortisation.
            If no value provided, the principal set on parameter level is used.
        principal_adjustments: Features used to adjust the principal that is amortised.
            If no value provided, no adjustment is made to the principal.
        fetchers_config: The fetchers configuration for retrieving EIA details.

    Returns:
        The EIA amount.
    """
    principal, interest_rate = _get_declining_principal_formula_terms(
        state=state,
        get_annual_interest_rate=get_annual_interest_rate,
        principal_amount=principal_amount,
        fetchers_config=fetchers_config,
    )

    the_term_details: TermDetails = term_details(
        state=state,
        get_annual_interest_rate=get_annual_interest_rate,
        use_expected_term=use_expected_term,
        principal_adjustments=principal_adjustments,
    )

    if principal_adjustments:
        principal += Decimal(
            sum(
                adjustment.calculate_principal_adjustment(state=state)
                for adjustment in principal_adjustments
            )
        )
    application_precision = int(state.parameters[fetchers_config.application_precision_param_id])  # type: ignore

    return apply_declining_principal_formula(
        remaining_principal=principal,
        interest_rate=interest_rate,
        fulfillment_precision=application_precision,
        remaining_term=the_term_details.remaining,
    )


def apply_declining_principal_formula(
    remaining_principal: Decimal,
    interest_rate: Decimal,
    remaining_term: int,
    fulfillment_precision: int = 2,
    lump_sum_amount: Decimal | None = None,
) -> Decimal:
    """Calculate the EIA according to the declining principal formula.

    Formula: EIA = (P-(L/(1+R)^(N)))*R*(((1+R)^N)/((1+R)^N-1))

    Args:
        remaining_principal: The principal remaining.
        interest_rate: The interest rate appropriate for the term unit.
        remaining_term: The number of integer term units remaining.
        fulfillment_precision: The precision needed for interest fulfillment.
        lump_sum_amount: An optional one-off repayment amount.

    Returns:
        The EIA amount.
    """
    lump_sum_amount = lump_sum_amount or Decimal(0)

    # the remaining term can be <= 0 when there is no more principal to amortise, but there is
    # still some due/overdue principal that keeps the loan open
    if remaining_term <= Decimal(0):
        return remaining_principal
    # Handle division by zero error, when interest_rate is zero eg BNPL
    elif interest_rate == Decimal(0):
        return utils.round_decimal(remaining_principal / remaining_term, fulfillment_precision)
    else:
        growth_factor: Decimal = (1 + interest_rate) ** remaining_term
        # Calculate the adjusted principal after accounting for the lump sum's present value
        adjusted_principal: Decimal = remaining_principal - (lump_sum_amount / growth_factor)
        numerator: Decimal = adjusted_principal * interest_rate * growth_factor
        denominator: Decimal = growth_factor - 1
        return utils.round_decimal(numerator / denominator, fulfillment_precision)


def _get_declining_principal_formula_terms(
    state: state_utils.SmartContractState,
    get_annual_interest_rate: Callable[..., Decimal],
    principal_amount: Decimal | None = None,
    fetchers_config: CalculateEiaFetchersConfig = DEFAULT_CALCULATE_EIA_FETCHERS_CONFIG,
) -> PrincipalAndInterestRate:
    """Get the principal and interest rate terms for the declining principal formula.

    Args:
        state: The smart contract state.
        get_annual_interest_rate: callback function to get the annual interest rate
        principal_amount: The principal amount used for amortisation.
            If no value provided, the principal set on parameter level is used.
        fetchers_config: The fetchers configuration for retrieving EIA details.

    Returns:
        The principal and interest rate to use in the calculation.
    """
    rejection = state_utils.check_parameters_exist(
        state, param_ids={fetchers_config.principal_param_id}
    )
    assert rejection is None, rejection

    principal: Decimal = (  # type: ignore
        state.parameters[fetchers_config.principal_param_id]
        if principal_amount is None
        else principal_amount
    )

    interest_rate: Decimal = (
        Decimal(0)
        if not get_annual_interest_rate
        else parameter_utils.yearly_to_monthly_rate(get_annual_interest_rate(state=state))
    )

    return PrincipalAndInterestRate(principal=principal, interest_rate=interest_rate)


def amortise(
    state: state_utils.SmartContractState,
    get_annual_interest_rate: Callable[..., Decimal],
    use_expected_term: bool = True,
    principal_amount: Decimal | None = None,
    principal_adjustments: list[lending_interfaces.PrincipalAdjustment] | None = None,
    event: str = ACCOUNT_ACTIVATION_EVENT,
    eia_address: str = lending_addresses.EIA,
    fetchers_config: AmortiseFetchersConfig = DEFAULT_AMORTISE_FETCHERS_CONFIG,
) -> list[CustomInstruction]:
    """Amortise a loan by calculating EIA and creating a custom instruction.

    Args:
        state: The smart contract state.
        get_annual_interest_rate: callback function to get the annual interest rate.
        use_expected_term: Indicates whether to calculate the expected term or use the elapsed term.
        principal_amount: The principal amount used for amortisation.
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
        use_expected_term=use_expected_term,
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
