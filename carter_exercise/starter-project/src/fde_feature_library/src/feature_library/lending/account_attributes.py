__smart_contract_feature__ = True

# standard libs
from decimal import Decimal
from typing import Any, Callable, NamedTuple

# features
import feature_library.common.balance_utils as balance_utils
import feature_library.common.denomination as denomination_module
import feature_library.common.state_utils as state_utils
import feature_library.common.utils as utils
import feature_library.lending.interfaces as lending_interfaces
from feature_library.lending.amortisations.amortisation_methods import TermDetails

# contracts api
from contracts_api import (
    Attribute,
    AttributeDecimalType,
)

TOTAL_OUTSTANDING_DEBT_ATTR_ID = "total_outstanding_debt"
TOTAL_OUTSTANDING_PAYMENTS_ATTR_ID = "total_outstanding_payments"
TOTAL_REMAINING_PRINCIPAL_ATTR_ID = "total_remaining_principal"
PRINCIPAL_PAID_TO_DATE_ATTR_ID = "principal_paid_to_date"
REMAINING_TERM_ATTR_ID = "remaining_term"

TOTAL_OUTSTANDING_DEBT_ATTRIBUTE = Attribute(
    name=TOTAL_OUTSTANDING_DEBT_ATTR_ID,
    data_type=AttributeDecimalType(),
)

TOTAL_OUTSTANDING_PAYMENTS_ATTRIBUTE = Attribute(
    name=TOTAL_OUTSTANDING_PAYMENTS_ATTR_ID,
    data_type=AttributeDecimalType(),
)

TOTAL_REMAINING_PRINCIPAL_ATTRIBUTE = Attribute(
    name=TOTAL_REMAINING_PRINCIPAL_ATTR_ID,
    data_type=AttributeDecimalType(),
)

PRINCIPAL_PAID_TO_DATE_ATTRIBUTE = Attribute(
    name=PRINCIPAL_PAID_TO_DATE_ATTR_ID,
    data_type=AttributeDecimalType(),
)

REMAINING_TERM_ATTRIBUTE = Attribute(
    name=REMAINING_TERM_ATTR_ID,
    data_type=AttributeDecimalType(),
)

attributes = [
    TOTAL_OUTSTANDING_DEBT_ATTRIBUTE,
    TOTAL_OUTSTANDING_PAYMENTS_ATTRIBUTE,
    TOTAL_REMAINING_PRINCIPAL_ATTRIBUTE,
    PRINCIPAL_PAID_TO_DATE_ATTRIBUTE,
    REMAINING_TERM_ATTRIBUTE,
]

AttributesFetchersConfig = NamedTuple(
    "AttributesFetchersConfig",
    [
        ("denomination_param_id", str),
        ("precision", int),
    ],
)

DEFAULT_FETCHERS_CONFIG = AttributesFetchersConfig(
    denomination_param_id=denomination_module.DENOMINATION_PARAM.id,
    precision=2,
)


def get_total_due_amount(
    state: state_utils.SmartContractState,
    due_addresses: list[str],
    fetchers_config: AttributesFetchersConfig = DEFAULT_FETCHERS_CONFIG,
) -> Decimal:
    """Sums the balances across all due addresses.

    Args:
        state: The current state of the smart contract.
        due_addresses: A list of due addresses.
        fetchers_config: Config for fetching parameters.

    Returns:
        Due balance in Decimal.
    """
    rejection = state_utils.check_parameters_exist(state, {fetchers_config.denomination_param_id})
    assert rejection is None, rejection
    denomination: str = state.parameters[fetchers_config.denomination_param_id]  # type: ignore
    return utils.round_decimal(
        amount=balance_utils.net_debit(
            balance_utils.sum_balances(
                balances=state.balances,
                addresses=due_addresses,
                denomination=denomination,
            )
        ),
        decimal_places=fetchers_config.precision,
    )


def get_total_outstanding_debt(
    state: state_utils.SmartContractState,
    debt_addresses: list[str],
    fetchers_config: AttributesFetchersConfig = DEFAULT_FETCHERS_CONFIG,
) -> Decimal:
    """Sums the balances across all outstanding debt addresses.

    Args:
        state: The current state of the smart contract.
        debt_addresses: Outstanding debt addresses.
        fetchers_config: Config for fetching parameters.

    Returns:
        Outstanding debt balance in Decimal.
    """
    rejection = state_utils.check_parameters_exist(state, {fetchers_config.denomination_param_id})
    assert rejection is None, rejection
    denomination: str = state.parameters[fetchers_config.denomination_param_id]  # type: ignore
    return utils.round_decimal(
        amount=balance_utils.net_debit(
            balance_utils.sum_balances(
                balances=state.balances,
                addresses=debt_addresses,
                denomination=denomination,
            )
        ),
        decimal_places=fetchers_config.precision,
    )


def get_total_remaining_principal(
    state: state_utils.SmartContractState,
    principal_addresses: list[str],
    fetchers_config: AttributesFetchersConfig = DEFAULT_FETCHERS_CONFIG,
) -> Decimal:
    """Sums the balances across all principal addresses.

    Args:
        state: The current state of the smart contract.
        principal_addresses: All principal addresses.
        fetchers_config: Config for fetching parameters.

    Returns:
        The total principal remaining on the account.
    """
    rejection = state_utils.check_parameters_exist(state, {fetchers_config.denomination_param_id})
    assert rejection is None, rejection
    denomination: str = state.parameters[fetchers_config.denomination_param_id]  # type: ignore
    return utils.round_decimal(
        amount=balance_utils.net_debit(
            balance_utils.sum_balances(
                balances=state.balances,
                addresses=principal_addresses,
                denomination=denomination,
            )
        ),
        decimal_places=fetchers_config.precision,
    )


def get_principal_paid_to_date(
    state: state_utils.SmartContractState,
    original_principal: Decimal,
    principal_addresses: list[str],
    fetchers_config: AttributesFetchersConfig = DEFAULT_FETCHERS_CONFIG,
) -> Decimal:
    """Returns the amount of the original principal paid off.

    Args:
        state: The current state of the smart contract.
        original_principal: The original principal amount.
        principal_addresses: All principal addresses.
        fetchers_config: Config for fetching parameters.

    Returns:
        The principal paid to date.
    """
    return original_principal - get_total_remaining_principal(
        state=state,
        principal_addresses=principal_addresses,
        fetchers_config=fetchers_config,
    )


def get_remaining_term(
    state: state_utils.SmartContractState,
    term_details_feature: Callable[..., TermDetails],
    get_annual_interest_rate: Callable[[state_utils.SmartContractState, Any], Decimal]
    | None = None,
    principal_adjustments: list[lending_interfaces.PrincipalAdjustment] | None = None,
    use_expected_term: bool = True,
) -> int:
    """Returns the remaining term.

    Args:
        state: The current state of the smart contract.
        term_details_feature: The term details feature.
        get_annual_interest_rate: callback function to get the annual interest rate.
        principal_adjustments: Any principal adjustments to consider.
        use_expected_term: Whether to use the expected term.

    Returns:
        The remaining term in months.
    """
    return term_details_feature(
        state=state,
        get_annual_interest_rate=get_annual_interest_rate,
        use_expected_term=use_expected_term,
        principal_adjustments=principal_adjustments,
    ).remaining
