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
import feature_library.lending.addresses as lending_addresses
import feature_library.lending.interfaces as lending_interfaces

# contracts api
from contracts_api import (
    BalanceDefaultDict,
    CustomInstruction,
    DefinedDateTime,
    ExpectedParameter,
    ParametersFilter,
    ParametersObservationFetcher,
)

from inception_sdk.vault.contracts.extensions.contracts_api_extensions import SmartContractVault

# Parameters
EARLY_REPAYMENT_FEE_INCOME_ACCOUNT_PARAM_ID = "&{early_repayment_fee_income_account}"
EARLY_REPAYMENT_FEE_INCOME_ACCOUNT_PARAM = ExpectedParameter(
    id=EARLY_REPAYMENT_FEE_INCOME_ACCOUNT_PARAM_ID,
    triggers_pre_parameter_change_hook=False,
    triggers_post_parameter_change_hook=False,
)

EARLY_REPAYMENT_FLAT_FEE_PARAM_ID = "&{early_repayment_flat_fee}"
EARLY_REPAYMENT_FLAT_FEE_PARAM = ExpectedParameter(
    id=EARLY_REPAYMENT_FLAT_FEE_PARAM_ID,
    triggers_pre_parameter_change_hook=False,
    triggers_post_parameter_change_hook=False,
)

EARLY_REPAYMENT_FEE_RATE_PARAM_ID = "&{early_repayment_fee_rate}"
EARLY_REPAYMENT_FEE_RATE_PARAM = ExpectedParameter(
    id=EARLY_REPAYMENT_FEE_RATE_PARAM_ID,
    triggers_pre_parameter_change_hook=False,
    triggers_post_parameter_change_hook=False,
)

expected_parameters = [
    EARLY_REPAYMENT_FEE_INCOME_ACCOUNT_PARAM,
    EARLY_REPAYMENT_FLAT_FEE_PARAM,
    EARLY_REPAYMENT_FEE_RATE_PARAM,
    denomination.DENOMINATION_PARAM,
]

# Fetchers
EARLY_REPAYMENT_ET_POF_ID = "early_repayment_et_pof"
EARLY_REPAYMENT_ET_POF = ParametersObservationFetcher(
    fetcher_id=EARLY_REPAYMENT_ET_POF_ID,
    at=DefinedDateTime.EFFECTIVE_DATETIME,
    filter=ParametersFilter(parameter_ids=[p.id for p in expected_parameters]),
)

data_fetchers = [
    EARLY_REPAYMENT_ET_POF,
]

EarlyRepaymentFetchersConfig = NamedTuple(
    "EarlyRepaymentFetchersConfig",
    [
        ("param_fetcher_id", str),
        ("early_repayment_fee_income_account_param_id", str),
        ("early_repayment_flat_fee_param_id", str),
        ("early_repayment_fee_rate_param_id", str),
        ("denomination_param_id", str),
        ("principal_addresses", set[str]),
    ],
)

DEFAULT_EARLY_REPAYMENT_FETCHERS_CONFIG = EarlyRepaymentFetchersConfig(
    param_fetcher_id=EARLY_REPAYMENT_ET_POF_ID,
    early_repayment_fee_income_account_param_id=EARLY_REPAYMENT_FEE_INCOME_ACCOUNT_PARAM_ID,
    early_repayment_flat_fee_param_id=EARLY_REPAYMENT_FLAT_FEE_PARAM_ID,
    early_repayment_fee_rate_param_id=EARLY_REPAYMENT_FEE_RATE_PARAM_ID,
    denomination_param_id=denomination.DENOMINATION_PARAM_ID,
    principal_addresses={lending_addresses.PRINCIPAL},
)


def get_parameters(
    vault: SmartContractVault, param_fetcher_id: str = EARLY_REPAYMENT_ET_POF_ID
) -> dict[str, datetime | Decimal | str | None]:
    """Retrieves configuration parameters for the early repayment feature.

    Args:
        vault: The SmartContractVault instance to query.
        param_fetcher_id: The unique identifier for the parameter fetcher.
            Defaults to `EARLY_REPAYMENT_ET_POF_ID`.

    Returns:
        Parameters for the early repayment feature.
    """
    return vault.get_parameters_observation(fetcher_id=param_fetcher_id).parameters


def _append_to_state(
    state: state_utils.SmartContractState,
    fetchers_config: EarlyRepaymentFetchersConfig = DEFAULT_EARLY_REPAYMENT_FETCHERS_CONFIG,
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


def is_posting_an_early_repayment(
    state: state_utils.SmartContractState,
    repayment_amount: Decimal,
    repayment_hierarchy_config: lending_interfaces.RepaymentHierarchyConfig,
    early_repayment_fees: list[lending_interfaces.EarlyRepaymentFee] | None,
    precision: int = 2,
    fetchers_config: EarlyRepaymentFetchersConfig = DEFAULT_EARLY_REPAYMENT_FETCHERS_CONFIG,
) -> bool:
    """Determines if the repayment amount is for a full early repayment.

    The repayment amount is compared to the total amount required to fully
    pay off and close the account. A repayment posting amount will be less
    than 0 since this is for asset/lending products.

    Args:
        state: The current state of the smart contract.
        repayment_amount: The amount being repaid.
        repayment_hierarchy_config: Configuration for the repayment hierarchy.
        early_repayment_fees: Early repayment fee features.
        precision: The number of decimal places to round to.
        fetchers_config: Configuration for the fetchers.

    Returns:
        True if the repayment amount matches the required amount to do a full early repayment.
    """
    if repayment_amount <= Decimal("0"):
        return False

    rejection = state_utils.check_parameters_exist(state, {fetchers_config.denomination_param_id})
    assert rejection is None, rejection

    denomination: str = state.parameters[fetchers_config.denomination_param_id]  # type: ignore

    # If this is called after the final due calculation event, principal will be zero
    # and therefore any repayment posting would not be for an early repayment.
    if _is_zero_principal(
        balances=state.balances,
        denomination=denomination,
        principal_addresses=fetchers_config.principal_addresses,
    ):
        return False

    return repayment_amount == get_total_early_repayment_amount(
        state=state,
        repayment_hierarchy_config=repayment_hierarchy_config,
        early_repayment_fees=early_repayment_fees,
        precision=precision,
        fetchers_config=fetchers_config,
    )


def get_total_early_repayment_amount(
    *,
    state: state_utils.SmartContractState,
    repayment_hierarchy_config: lending_interfaces.RepaymentHierarchyConfig,
    early_repayment_fees: list[lending_interfaces.EarlyRepaymentFee] | None,
    precision: int = 2,
    check_for_outstanding_accrued_interest_on_zero_principal: bool = False,
    fetchers_config: EarlyRepaymentFetchersConfig = DEFAULT_EARLY_REPAYMENT_FETCHERS_CONFIG,
) -> Decimal:
    """Get the exact repayment amount required for a full early repayment.

    Args:
        state: The current state of the smart contract.
        repayment_hierarchy_config: Configuration for the repayment hierarchy.
        early_repayment_fees: Early repayment fee features.
        precision: The number of decimal places to round to.
        check_for_outstanding_accrued_interest_on_zero_principal: Whether outstanding balances on
            loans that have zero principal should count as early repayment.
        fetchers_config: Configuration for the fetchers.

    Returns:
        The exact repayment amount required for a full early repayment.
    """

    rejection = state_utils.check_parameters_exist(state, {fetchers_config.denomination_param_id})
    assert rejection is None, rejection

    denomination: str = state.parameters[fetchers_config.denomination_param_id]  # type: ignore

    # If this is called after the final due calculation event, principal will be zero
    # and therefore any repayment posting would not be for an early repayment.
    # However, if an overpayment has resulted in zero principal, there may still be accrued interest
    # that has not yet been applied
    if not check_for_outstanding_accrued_interest_on_zero_principal and _is_zero_principal(
        balances=state.balances,
        denomination=denomination,
        principal_addresses=fetchers_config.principal_addresses,
    ):
        return Decimal("0")

    total_outstanding_debt: Decimal = (
        repayment_hierarchy_config.repayment_hierarchy.get_total_outstanding_debt(
            state=state,
            fetchers_config=repayment_hierarchy_config.fetchers_config,
        )
    )

    early_repayment_fees = early_repayment_fees or []

    early_repayment_fees_sum: Decimal = sum(
        (
            fee.get_early_repayment_fee_amount(state=state, precision=precision)
            for fee in early_repayment_fees
        ),
        Decimal(0),
    )

    return total_outstanding_debt + early_repayment_fees_sum


def get_early_repayment_flat_fee(
    *,
    state: state_utils.SmartContractState,
    precision: int = 2,
    fetchers_config: EarlyRepaymentFetchersConfig = DEFAULT_EARLY_REPAYMENT_FETCHERS_CONFIG,
) -> Decimal:
    """Get the early repayment flat fee amount from the parameter value.

    Args:
        state: The current state of the smart contract.
        precision: The number of decimal places to round to.
        fetchers_config: Configuration for the fetchers.

    Returns:
        The flat fee amount.
    """
    state = _append_to_state(state, fetchers_config)
    rejection = state_utils.check_parameters_exist(
        state, {fetchers_config.early_repayment_flat_fee_param_id}
    )
    assert rejection is None, rejection

    early_repayment_flat_fee: Decimal = state.parameters[
        fetchers_config.early_repayment_flat_fee_param_id
    ]  # type: ignore

    return round(early_repayment_flat_fee, precision)


def calculate_early_repayment_percentage_fee(
    *,
    state: state_utils.SmartContractState,
    precision: int = 2,
    fetchers_config: EarlyRepaymentFetchersConfig = DEFAULT_EARLY_REPAYMENT_FETCHERS_CONFIG,
) -> Decimal:
    """Calculates the early repayment fee using the rate from the parameter.

    The fee is calculated as a percentage of the total remaining principal.

    Args:
        state: The current state of the smart contract.
        precision: The number of decimal places to round to.
        fetchers_config: Configuration for the fetchers.

    Returns:
        The percentage fee amount.
    """
    state = _append_to_state(state, fetchers_config)
    rejection = state_utils.check_parameters_exist(
        state,
        {
            fetchers_config.denomination_param_id,
            fetchers_config.early_repayment_fee_rate_param_id,
        },
    )
    assert rejection is None, rejection

    denomination: str = state.parameters[fetchers_config.denomination_param_id]  # type: ignore
    early_repayment_fee_rate: Decimal = state.parameters[
        fetchers_config.early_repayment_fee_rate_param_id
    ]  # type: ignore

    total_remaining_principal = balance_utils.net_debit(
        balance_utils.sum_balances(
            balances=state.balances,
            denomination=denomination,
            addresses=fetchers_config.principal_addresses,
        )
    )

    return round(total_remaining_principal * early_repayment_fee_rate, precision)


def charge_early_repayment_fee(
    *,
    state: state_utils.SmartContractState,
    amount_to_charge: Decimal,
    fee_name: str,
    fetchers_config: EarlyRepaymentFetchersConfig = DEFAULT_EARLY_REPAYMENT_FETCHERS_CONFIG,
) -> list[CustomInstruction]:
    """Handles the early repayment fee within post-posting.

    Returns the associated posting instructions for the fee.

    Args:
        state: The current state of the smart contract.
        amount_to_charge: The amount to charge for the fee.
        fee_name: The name of the early repayment fee type.
        fetchers_config: Configuration for the fetchers.

    Returns:
        Custom instruction to handle the charge of the fee.
    """
    if amount_to_charge <= Decimal("0"):
        return []

    state = _append_to_state(state, fetchers_config)
    rejection = state_utils.check_parameters_exist(
        state,
        {
            fetchers_config.denomination_param_id,
            fetchers_config.early_repayment_fee_income_account_param_id,
        },
    )
    assert rejection is None, rejection

    denomination: str = state.parameters[fetchers_config.denomination_param_id]  # type: ignore
    early_repayment_fee_income_account: str = state.parameters[
        fetchers_config.early_repayment_fee_income_account_param_id
    ]  # type: ignore

    postings = posting_utils.create_postings(
        amount=amount_to_charge,
        debit_account=state.vault.account_id,
        credit_account=early_repayment_fee_income_account,
        denomination=denomination,
    )
    if postings:
        return [
            CustomInstruction(
                postings=postings,
                instruction_details={
                    "description": f"Early Repayment Fee: {fee_name}",
                    "event": "EARLY_REPAYMENT",
                },
            )
        ]
    return []


def _is_zero_principal(
    balances: BalanceDefaultDict,
    denomination: str,
    principal_addresses: set[str] | None = None,
) -> bool:
    """Return true if there is a zero or negative principal balance.

    Args:
        balances: Balances of the account.
        denomination: Denomination of the relevant loan.
        principal_addresses: Principal balance addresses.

    Returns:
        True if there is a zero or negative principal balance.
    """

    principal_addresses = principal_addresses or {lending_addresses.PRINCIPAL}

    total_principal_balance = balance_utils.sum_balances(
        balances=balances,
        denomination=denomination,
        addresses=principal_addresses,
    )

    return balance_utils.net_debit(total_principal_balance) <= Decimal("0")


EarlyRepaymentFlatFee = lending_interfaces.EarlyRepaymentFee(
    get_early_repayment_fee_amount=get_early_repayment_flat_fee,
    charge_early_repayment_fee=charge_early_repayment_fee,
    fee_name="Flat Fee",
)

EarlyRepaymentPercentageFee = lending_interfaces.EarlyRepaymentFee(
    get_early_repayment_fee_amount=calculate_early_repayment_percentage_fee,
    charge_early_repayment_fee=charge_early_repayment_fee,
    fee_name="Percentage Fee",
)
