# Copyright @ 2026 Thought Machine Group Limited. All rights reserved.
"""Rule of 78 feature."""

__smart_contract_feature__ = True

# standard libs
from decimal import Decimal
from typing import Callable, NamedTuple

# feature library
import feature_library.common.application_precision as application_precision
import feature_library.common.balance_utils as balance_utils
import feature_library.common.denomination as denomination_module
import feature_library.common.fees as fees
import feature_library.common.parameter_utils as parameter_utils
import feature_library.common.state_utils as state_utils
import feature_library.common.utils as utils
import feature_library.lending.addresses as lending_addresses
import feature_library.lending.amortisations.eia as eia_module
import feature_library.lending.interest.interest_application as interest_application
import feature_library.lending.interest.secondary.fixed_rate as fixed_rate
import feature_library.lending.interfaces as lending_interfaces
import feature_library.lending.principal.principal as lending_principal
import feature_library.lending.term.term as term_helpers
from feature_library.lending.amortisations.amortisation_methods import (
    TermDetails,
)

# contracts api
from contracts_api import CustomInstruction, Posting

ACCOUNT_ACTIVATION_EVENT = "ACCOUNT_ACTIVATION"

AMORTISATION_METHOD = "RULE_OF_78"

TermDetailsFetchersConfig = NamedTuple(
    "TermDetailsFetchersConfig",
    [
        ("denomination_param_id", str),
        ("term_param_id", str),
        ("principal_address", str),
    ],
)
DEFAULT_TERM_DETAILS_FETCHERS_CONFIG = TermDetailsFetchersConfig(
    denomination_param_id=denomination_module.DENOMINATION_PARAM_ID,
    term_param_id=term_helpers.TERM_PARAM_ID,
    principal_address=lending_addresses.PRINCIPAL,
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

GetInterestFetchersConfig = NamedTuple(
    "GetInterestFetchersConfig",
    [
        ("denomination_param_id", str),
        ("principal_param_id", str),
        ("term_param_id", str),
        ("fixed_interest_rate_param_id", str),
        ("application_precision_param_id", str),
    ],
)
DEFAULT_GET_INTEREST_FETCHERS_CONFIG = GetInterestFetchersConfig(
    denomination_param_id=denomination_module.DENOMINATION_PARAM_ID,
    principal_param_id=lending_principal.PRINCIPAL_PARAM_ID,
    term_param_id=term_helpers.TERM_PARAM_ID,
    fixed_interest_rate_param_id=fixed_rate.FIXED_INTEREST_RATE_PARAM_ID,
    application_precision_param_id=application_precision.APPLICATION_PRECISION_PARAM_ID,
)

ApplyInterestFetchersConfig = NamedTuple(
    "ApplyInterestFetchersConfig",
    [
        ("denomination_param_id", str),
        ("interest_received_account_param_id", str),
        ("interest_due_address", str),
    ],
)
DEFAULT_APPLY_INTEREST_FETCHERS_CONFIG = ApplyInterestFetchersConfig(
    denomination_param_id=denomination_module.DENOMINATION_PARAM_ID,
    interest_received_account_param_id=interest_application.INTEREST_RECEIVED_ACCOUNT_PARAM_ID,
    interest_due_address=lending_addresses.INTEREST_DUE,
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


def is_rule_of_78_loan(amortisation_method: str) -> bool:
    """Return True if the amortisation_method is 'RULE_OF_78'.

    Args:
        amortisation_method: The amortisation method to check.

    Returns:
        True if the amortisation method is 'RULE_OF_78', False otherwise.
    """
    return amortisation_method.upper() == AMORTISATION_METHOD


def term_details(
    state: state_utils.SmartContractState,
    fetchers_config: TermDetailsFetchersConfig = DEFAULT_TERM_DETAILS_FETCHERS_CONFIG,
) -> TermDetails:
    """Calculate the elapsed and remaining term for a loan.

    Args:
        state: The smart contract state.
        use_expected_term: Not used but required for the interface.
        interest_rate: Not used but required for the interface.
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

    principal_balance = balance_utils.balance_at_coordinates(
        balances=balances,
        address=fetchers_config.principal_address,
        denomination=denomination,
    )

    elapsed = term_helpers.get_elapsed_term(balances=balances, denomination=denomination)

    # This is to handle the scenario where the loan has been fully repaid (as a result of an early
    # repayment or otherwise) but the account has been left open
    expected_remaining_term = (original_total_term - elapsed) if principal_balance > 0 else 0

    return TermDetails(elapsed=elapsed, remaining=expected_remaining_term)


def calculate_eia(
    state: state_utils.SmartContractState,
    get_annual_interest_rate: Callable[..., Decimal],
    principal_amount: Decimal | None = None,
    principal_adjustments: list[lending_interfaces.PrincipalAdjustment] | None = None,
    fetchers_config: CalculateEiaFetchersConfig = DEFAULT_CALCULATE_EIA_FETCHERS_CONFIG,
) -> Decimal:
    """Calculate the EIA for a Rule of 78 loan.

    Args:
        state: The smart contract state.
        use_expected_term: Not used but required for the interface.
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
            fetchers_config.term_param_id,
            fetchers_config.principal_param_id,
            fetchers_config.application_precision_param_id,
        },
    )
    assert rejection is None, rejection

    fixed_interest_rate = (
        Decimal(0) if not get_annual_interest_rate else get_annual_interest_rate(state=state)
    )

    total_term: int = int(state.parameters[fetchers_config.term_param_id])  # type: ignore

    principal: Decimal = (  # type: ignore
        state.parameters[fetchers_config.principal_param_id]
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

    precision = int(state.parameters[fetchers_config.application_precision_param_id])  # type: ignore

    total_loan_interest = calculate_non_accruing_loan_total_interest(
        original_principal=principal,
        annual_interest_rate=fixed_interest_rate,
        total_term=total_term,
        precision=precision,
    )

    return utils.round_decimal((principal + total_loan_interest) / total_term, precision)


def apply_interest(
    *,
    state: state_utils.SmartContractState,
    fetchers_config: ApplyInterestFetchersConfig = DEFAULT_APPLY_INTEREST_FETCHERS_CONFIG,
) -> list[Posting]:
    """Create the postings needed to apply interest for a loan using rule of 78 loan amortisation.

    Args:
        state: The smart contract state.
        fetchers_config: The fetchers configuration for retrieving application details.

    Returns:
        A list of postings.
    """
    rejection = state_utils.check_parameters_exist(
        state=state,
        param_ids={
            fetchers_config.interest_received_account_param_id,
            fetchers_config.denomination_param_id,
        },
    )
    assert rejection is None, rejection

    application_internal_account: str = state.parameters[
        fetchers_config.interest_received_account_param_id
    ]  # type: ignore
    application_interest_address: str = fetchers_config.interest_due_address
    denomination: str = state.parameters[fetchers_config.denomination_param_id]  # type: ignore

    interest_application_amounts = get_interest_to_apply(
        state=state,
    )

    return fees.fee_postings(
        customer_account_id=state.vault.account_id,
        customer_account_address=application_interest_address,
        denomination=denomination,
        amount=interest_application_amounts.eia_rounded_accrued,
        internal_account=application_internal_account,
    )


def get_interest_to_apply(
    *,
    state: state_utils.SmartContractState,
    fetchers_config: GetInterestFetchersConfig = DEFAULT_GET_INTEREST_FETCHERS_CONFIG,
) -> lending_interfaces.InterestAmounts:
    """Determines the interest amount for application using rule of 78 amortisation.

    Args:
        state: Smart contract state.
        effective_datetime: current effective datetime.
        previous_application_datetime: previous application datetime.
        application_precision: number of places that interest is rounded to during application.
        fetchers_config: The fetchers configuration for retrieving application details.

    Returns:
        lending_interfaces.InterestAmounts: the interest amounts
    """
    rejection = state_utils.check_parameters_exist(
        state=state,
        param_ids={
            fetchers_config.denomination_param_id,
            fetchers_config.principal_param_id,
            fetchers_config.term_param_id,
            fetchers_config.fixed_interest_rate_param_id,
            fetchers_config.application_precision_param_id,
        },
    )
    assert rejection is None, rejection

    application_precision = int(state.parameters[fetchers_config.application_precision_param_id])  # type: ignore
    denomination: str = state.parameters[fetchers_config.denomination_param_id]  # type: ignore
    principal: Decimal = state.parameters[fetchers_config.principal_param_id]  # type: ignore
    total_term = int(state.parameters[fetchers_config.term_param_id])  # type: ignore

    # Calculating the remaining term again here instead of passing it from the due amount
    # calculation feature as only rule of 78 amortisation method would require remaining term
    elapsed = term_helpers.get_elapsed_term(balances=state.balances, denomination=denomination)
    term_remaining = total_term - elapsed

    # Rule of 78 only supports fixed_interest loans, therefore we always use the
    # fixed_interest_rate
    fixed_interest_rate: Decimal = state.parameters[fetchers_config.fixed_interest_rate_param_id]  # type: ignore

    total_interest = calculate_non_accruing_loan_total_interest(
        original_principal=principal,
        annual_interest_rate=fixed_interest_rate,
        total_term=total_term,
        precision=application_precision,
    )

    rule_of_78_denominator = _get_sum_1_to_n(total_term)

    interest_due = _calculate_interest_due(
        total_interest=total_interest,
        total_term=total_term,
        term_remaining=term_remaining,
        denominator=rule_of_78_denominator,
        application_precision=application_precision,
    )

    return lending_interfaces.InterestAmounts(
        eia_accrued=Decimal(0),
        eia_rounded_accrued=interest_due,
        non_eia_accrued=Decimal(0),
        non_eia_rounded_accrued=Decimal(0),
        total_rounded=interest_due,
    )


def _calculate_interest_due(
    total_interest: Decimal,
    total_term: int,
    term_remaining: int,
    denominator: int,
    application_precision: int,
) -> Decimal:
    """Returns the amount of interest due for a rule of 78 loan accounting for final event.

    Args:
        total_interest: total interest to be paid during the loan's tenure
        total_term: total term of the loan
        term_remaining: number of repayments remaining on the loan
        denominator: rule of 78 denominator
        application_precision: number of places that interest is rounded to during application.

    Returns:
        Decimal: Interest due.
    """
    if term_remaining == 1:
        return _calculate_final_month_interest(
            total_interest=total_interest,
            total_term=total_term,
            rule_of_78_denominator=denominator,
            application_precision=application_precision,
        )

    return utils.round_decimal(
        total_interest * term_remaining / denominator,
        application_precision,
    )


def _calculate_final_month_interest(
    total_interest: Decimal,
    total_term: int,
    rule_of_78_denominator: int,
    application_precision: int,
) -> Decimal:
    """Calculates the final month interest.

    Args:
        total_interest: total interest to be paid.
        total_term: total term of the loan.
        rule_of_78_denominator: rule of 78 denominator.
        application_precision: precision for interest calculation.

    Returns:
        Decimal: Final month interest.
    """
    return total_interest - Decimal(
        sum(
            utils.round_decimal(
                amount=(total_interest * (total_term - n) / rule_of_78_denominator),
                decimal_places=application_precision,
            )
            for n in range(0, total_term - 1)
        )
    )


def _get_sum_1_to_n(N: int) -> int:  # noqa: N803
    """Returns the sum of integers from 1 to N.

    Args:
        N: The integer to sum to.

    Returns:
        int: The sum.
    """
    return int(N * (N + 1) / 2)


def calculate_non_accruing_loan_total_interest(
    original_principal: Decimal,
    annual_interest_rate: Decimal,
    total_term: int,
    precision: int,
) -> Decimal:
    """Returns the total loan interest for a flat interest or rule of 78 amortised loan.

    Args:
        original_principal: principal of the loan at loan start
        annual_interest_rate: yearly interest rate of the loan
        total_term: total term of the loan
        precision: number of places that interest is rounded to before application.

    Returns:
        Decimal: Total interest.
    """
    return utils.round_decimal(
        original_principal
        * parameter_utils.yearly_to_monthly_rate(yearly_rate=annual_interest_rate)
        * Decimal(total_term),
        precision,
    )


def amortise(
    state: state_utils.SmartContractState,
    get_annual_interest_rate: Callable[..., Decimal],
    principal_amount: Decimal | None = None,
    principal_adjustments: list[lending_interfaces.PrincipalAdjustment] | None = None,
    event: str = ACCOUNT_ACTIVATION_EVENT,
    eia_address: str = lending_addresses.EIA,
    fetchers_config: AmortiseFetchersConfig = DEFAULT_AMORTISE_FETCHERS_CONFIG,
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
