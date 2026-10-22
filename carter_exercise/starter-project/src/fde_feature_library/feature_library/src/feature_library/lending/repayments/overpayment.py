__smart_contract_feature__ = True

from datetime import datetime
from decimal import Decimal
from typing import Callable, NamedTuple

import feature_library.common.addresses as common_addresses
import feature_library.common.balance_utils as balance_utils
import feature_library.common.denomination as denomination
import feature_library.common.fees as fee_utils
import feature_library.common.posting_utils as posting_utils
import feature_library.common.state_utils as state_utils
import feature_library.common.utils as common_utils
import feature_library.lending.addresses as lending_addresses
import feature_library.lending.interfaces as lending_interfaces

from contracts_api import (
    DEFAULT_ADDRESS,
    BalanceDefaultDict,
    CustomInstruction,
    DefinedDateTime,
    ExpectedParameter,
    ParametersFilter,
    ParametersObservationFetcher,
    Phase,
    Posting,
    Rejection,
    RejectionReason,
)

from inception_sdk.vault.contracts.extensions.contracts_api_extensions import SmartContractVault

# Overpayment tracker address for use in tracking allowance
OVERPAYMENT_ADDRESS = "OVERPAYMENT"

# Impact preference constants
REDUCE_EMI = "reduce_emi"
REDUCE_TERM = "reduce_term"


OVERPAYMENT_FEE_RATE_PARAM_ID = "&{overpayment_fee_rate}"
OVERPAYMENT_FEE_RATE_PARAM = ExpectedParameter(
    id=OVERPAYMENT_FEE_RATE_PARAM_ID,
    triggers_post_parameter_change_hook=False,
    triggers_pre_parameter_change_hook=False,
)


OVERPAYMENT_FEE_INCOME_ACCOUNT_PARAM_ID = "&{overpayment_fee_income_account}"
OVERPAYMENT_FEE_INCOME_ACCOUNT_PARAM = ExpectedParameter(
    id=OVERPAYMENT_FEE_INCOME_ACCOUNT_PARAM_ID,
    triggers_post_parameter_change_hook=False,
    triggers_pre_parameter_change_hook=False,
)

OVERPAYMENT_IMPACT_PREFERENCE_PARAM_ID = "&{overpayment_impact_preference}"
OVERPAYMENT_IMPACT_PREFERENCE_PARAM = ExpectedParameter(
    id=OVERPAYMENT_IMPACT_PREFERENCE_PARAM_ID,
    triggers_post_parameter_change_hook=False,
    triggers_pre_parameter_change_hook=False,
)

expected_parameters = [
    OVERPAYMENT_FEE_RATE_PARAM,
    OVERPAYMENT_FEE_INCOME_ACCOUNT_PARAM,
    OVERPAYMENT_IMPACT_PREFERENCE_PARAM,
    denomination.DENOMINATION_PARAM,
]

OVERPAYMENT_PARAMS_POF_ID = "overpayment_params_pof"
OVERPAYMENT_PARAMS_POF = ParametersObservationFetcher(
    fetcher_id=OVERPAYMENT_PARAMS_POF_ID,
    at=DefinedDateTime.EFFECTIVE_DATETIME,
    filter=ParametersFilter(parameter_ids=[p.id for p in expected_parameters]),
)

# Config
OverpaymentFetchersConfig = NamedTuple(
    "OverpaymentFetchersConfig",
    [
        ("param_fetcher_id", str),
        ("overpayment_fee_rate_param_id", str),
        ("overpayment_fee_account_param_id", str),
        ("overpayment_impact_pref_param_id", str),
        ("denomination_param_id", str),
    ],
)

DEFAULT_OVERPAYMENT_FETCHERS_CONFIG = OverpaymentFetchersConfig(
    param_fetcher_id=OVERPAYMENT_PARAMS_POF_ID,
    overpayment_fee_rate_param_id=OVERPAYMENT_FEE_RATE_PARAM_ID,
    overpayment_fee_account_param_id=OVERPAYMENT_FEE_INCOME_ACCOUNT_PARAM_ID,
    overpayment_impact_pref_param_id=OVERPAYMENT_IMPACT_PREFERENCE_PARAM_ID,
    denomination_param_id=denomination.DENOMINATION_PARAM_ID,
)


def get_parameters(
    vault: SmartContractVault, param_fetcher_id: str = OVERPAYMENT_PARAMS_POF_ID
) -> dict[str, str | Decimal | datetime | None]:
    """Retrieves configuration parameters for the overpayment feature from the vault.

    Args:
        vault: The vault object containing the parameter observations.
        param_fetcher_id: The ID of the fetcher used to retrieve the overpayment parameters.
            Defaults to `OVERPAYMENT_PARAMS_POF_ID`.

    Returns:
        dict[str, str | Decimal | datetime | None]: A dictionary of parameter values keyed by their
        ID.
    """
    return vault.get_parameters_observation(fetcher_id=param_fetcher_id).parameters


def _append_to_state(
    state: state_utils.SmartContractState,
    fetchers_config: OverpaymentFetchersConfig = DEFAULT_OVERPAYMENT_FETCHERS_CONFIG,
) -> state_utils.SmartContractState:
    """Appends late repayment specific parameters to the provided smart contract state.

    Args:
        state: The current state of the smart contract to be augmented.
        fetchers_config: Configuration for the late repayment fetchers, defining which
            parameter IDs to retrieve. Defaults to `DEFAULT_FETCHERS_CONFIG`.

    Returns:
        state_utils.SmartContractState: A new state object containing the original state
            plus the retrieved late repayment parameters.
    """
    return state_utils.append_to_state(
        state=state,
        parameters=get_parameters(state.vault, fetchers_config.param_fetcher_id),
    )


def get_max_overpayment_fee(
    fee_rate: Decimal,
    balances: BalanceDefaultDict,
    denomination: str,
    precision: int = 2,
    principal_address: str = lending_addresses.PRINCIPAL,
) -> Decimal:
    """The maximum overpayment fee is the maximum_overpayment_amount * overpayment_fee_rate.

    Maximum Overpayment Amount Proof:
        X = maximum_overpayment_amount
        R = overpayment_fee_rate
        P = remaining_principal
        F = overpayment_fee

        overpayment_fee = overpayment_amount * overpayment_fee_rate
        principal_repaid = overpayment_amount - overpayment_fee
        maximum_overpayment_amount is when principal_repaid == remaining_principal, therefore

        P = X - F
        but F = X*R
        => P = X - XR => X(1-R)
        and so:
        X = P / (1-R)
        and so F_max = PR / (1-R)

    Args:
        fee_rate (Decimal): overpayment fee rate
        balances (BalanceDefaultDict): account balances
        denomination (str): the account's denomination
        precision (int, optional): Rounding precision. Defaults to 2dp.
        principal_address (str, optional): The prinicpal address. Defaults to
            lending_addresses.PRINCIPAL.

    Returns:
        Decimal: Maximum overpayment fee
    """

    if fee_rate >= 1:
        return Decimal("0")

    principal = balance_utils.net_debit(
        bal=balance_utils.get_current_net_balance(
            balances=balances,
            address=principal_address,
            denomination=denomination,
            phase=Phase.COMMITTED,
        )
    )

    maximum_overpayment = common_utils.round_decimal(
        amount=(principal / (1 - fee_rate)), decimal_places=precision
    )

    overpayment_fee = get_overpayment_fee(
        principal_repaid=maximum_overpayment,
        overpayment_fee_rate=fee_rate,
        precision=precision,
    )

    return overpayment_fee


def get_overpayment_fee(
    principal_repaid: Decimal,
    overpayment_fee_rate: Decimal,
    precision: int,
) -> Decimal:
    """Determines the overpayment fee for a given amount of principal being repaid.

    Args:
        principal_repaid (Decimal): the amount of principal repaid by the repayment
        overpayment_fee_rate (Decimal): the percentage of principal to include in the fee. Must be
    < 1, or 0 is returned
        precision (int): decimal places to round the fee to

    Returns:
        Decimal: the overpayment fee
    """
    if overpayment_fee_rate >= 1:
        return Decimal("0")
    return common_utils.round_decimal(
        amount=(principal_repaid * overpayment_fee_rate), decimal_places=precision
    )


def charge_overpayment_fee_as_penalty(
    state: state_utils.SmartContractState,
    vault: SmartContractVault,
    overpayment_amount: Decimal,
    precision: int,
    fetchers_config: OverpaymentFetchersConfig = DEFAULT_OVERPAYMENT_FETCHERS_CONFIG,
) -> list[CustomInstruction]:
    """Calculates and generates instructions to charge an overpayment fee as a penalty.

    The fee is charged to the penalties address.

    Args:
        state: The current state of the smart contract.
        vault: The vault object containing the account data.
        overpayment_amount: The amount of the overpayment to calculate the fee on.
        precision: The number of decimal places to round the fee to.
        fetchers_config: The configuration of the fetchers used to get parameters.

    Returns:
        list[CustomInstruction]: The custom instruction containing the fee postings, if any.
    """

    state = _append_to_state(state=state, fetchers_config=fetchers_config)

    rejection = state_utils.check_parameters_exist(
        state=state,
        param_ids={
            fetchers_config.denomination_param_id,
            fetchers_config.overpayment_fee_rate_param_id,
            fetchers_config.overpayment_fee_account_param_id,
        },
    )
    assert rejection is None, rejection

    params = state.parameters
    denomination: str = params[fetchers_config.denomination_param_id]  # type: ignore
    overpayment_fee_rate: Decimal = params[fetchers_config.overpayment_fee_rate_param_id]  # type: ignore
    overpayment_fee_income_account: str = params[fetchers_config.overpayment_fee_account_param_id]  # type: ignore

    overpayment_fee = get_overpayment_fee(
        principal_repaid=overpayment_amount,
        overpayment_fee_rate=overpayment_fee_rate,
        precision=precision,
    )
    overpayment_fee_postings = get_overpayment_fee_postings(
        overpayment_fee=overpayment_fee,
        denomination=denomination,
        customer_account_id=vault.account_id,
        customer_account_address=lending_addresses.PENALTIES,
        internal_account=overpayment_fee_income_account,
    )

    return (
        [
            CustomInstruction(
                postings=overpayment_fee_postings,
                instruction_details=posting_utils.standard_instruction_details(
                    description=f"Charge {overpayment_fee=} on {overpayment_amount=}",
                    event_type="CHARGE_OVERPAYMENT_FEE",
                    gl_impacted=True,
                ),
                override_all_restrictions=True,
            )
        ]
        if overpayment_fee_postings
        else []
    )


def get_overpayment_fee_postings(
    overpayment_fee: Decimal,
    denomination: str,
    customer_account_id: str,
    customer_account_address: str,
    internal_account: str,
) -> list[Posting]:
    """Creates postings to charge the overpayment fee.

    Args:
        overpayment_fee: The amount of the fee to charge.
        denomination: The denomination of the fee.
        customer_account_id: The ID of the customer's account.
        customer_account_address: The address to debit the fee from.
        internal_account: The ID of the internal account to credit the fee to.

    Returns:
        list[Posting]: The postings required to charge the fee.
    """
    return fee_utils.fee_postings(
        customer_account_id=customer_account_id,
        customer_account_address=customer_account_address,
        denomination=denomination,
        amount=overpayment_fee,
        internal_account=internal_account,
    )


def is_posting_an_overpayment(
    state: state_utils.SmartContractState,
    repayment_hierarchy_config: lending_interfaces.RepaymentHierarchyConfig,
    repayment_amount: Decimal,
    fetchers_config: OverpaymentFetchersConfig = DEFAULT_OVERPAYMENT_FETCHERS_CONFIG,
) -> bool:
    """Checks whether the given posting involves an overpayment amount.

    An overpayment is defined as any repayment that exceeds the current total amount due
    (including any past due arrears and current due cycle).

    Args:
        state: The current state of the smart contract.
        repayment_hierarchy_config: Configuration defining the repayment hierarchy and its fetchers.
        repayment_amount: The amount of the repayment being made.
        fetchers_config: Configuration of the fetchers used for overpayment.

    Returns:
        bool: True if the repayment amount is greater than the total due amount, False otherwise.
    """

    state = _append_to_state(state=state, fetchers_config=fetchers_config)

    if repayment_amount <= 0:
        return False

    total_due_amount: Decimal = repayment_hierarchy_config.repayment_hierarchy.get_total_due_amount(
        state=state,
        fetchers_config=repayment_hierarchy_config.fetchers_config,
    )
    return repayment_amount > total_due_amount


# all criteria for an overpayment (checks if posting is > total debt)
def validate_if_overpayment_is_greater_than_max(
    state: state_utils.SmartContractState,
    repayment_amount: Decimal,
    repayment_hierarchy_config: lending_interfaces.RepaymentHierarchyConfig,
    fetchers_config: OverpaymentFetchersConfig = DEFAULT_OVERPAYMENT_FETCHERS_CONFIG,
) -> Rejection | None:
    """Rejects repayments if the amount exceeds total owed, including Principal, + overpayment fee.

    For use in the pre-posting hook.

    Args:
        state (state_utils.SmartContractState): The smart contract state
        repayment_amount (Decimal): the repayment amount. Expected to be positive.
        repayment_hierarchy_config (lending_interfaces.RepaymentHierarchyConfig): the repayment
            hierarchy configuration
        fetchers_config (OverpaymentFetchersConfig, optional): the overpayment fetchers config.
            Defaults to DEFAULT_OVERPAYMENT_FETCHERS_CONFIG.

    Returns:
        Rejection | None: Rejection if amount exceeds total owned.
    """

    if repayment_amount <= 0:
        return None

    max_overpayment_amount = get_max_overpayment_amount(
        state=state,
        repayment_hierarchy_config=repayment_hierarchy_config,
        fetchers_config=fetchers_config,
    )

    if repayment_amount > max_overpayment_amount:
        return Rejection(
            message="Cannot pay more than is owed.",
            reason_code=RejectionReason.AGAINST_TNC,
        )
    return None


def get_max_overpayment_amount(
    state: state_utils.SmartContractState,
    repayment_hierarchy_config: lending_interfaces.RepaymentHierarchyConfig,
    fetchers_config: OverpaymentFetchersConfig = DEFAULT_OVERPAYMENT_FETCHERS_CONFIG,
) -> Decimal:
    """Calculates the maximum allowed overpayment amount.

    This considers the total outstanding debt and any potential maximum overpayment fee
    that may be charged.

    Args:
        state: The current state of the smart contract.
        repayment_hierarchy_config: Configuration defining the repayment hierarchy.
        fetchers_config: Configuration of the fetchers used for overpayment.

    Returns:
        Decimal: The maximum amount that can be overpaid.
    """

    state = _append_to_state(state=state, fetchers_config=fetchers_config)

    rejection = state_utils.check_parameters_exist(
        state=state,
        param_ids={
            fetchers_config.overpayment_fee_rate_param_id,
            fetchers_config.denomination_param_id,
        },
    )
    assert rejection is None, rejection

    params = state.parameters
    overpayment_fee_rate: Decimal = params[fetchers_config.overpayment_fee_rate_param_id]  # type: ignore
    denomination: str = params[fetchers_config.denomination_param_id]  # type: ignore

    total_outstanding_debt: Decimal = (
        repayment_hierarchy_config.repayment_hierarchy.get_total_outstanding_debt(
            state=state,
            fetchers_config=repayment_hierarchy_config.fetchers_config,
        )
    )

    max_overpayment_fee = get_max_overpayment_fee(
        fee_rate=overpayment_fee_rate,
        balances=state.balances,
        denomination=denomination,
    )
    return total_outstanding_debt + max_overpayment_fee


def handle_overpayment(
    state: state_utils.SmartContractState,
    overpayment_amount: Decimal,
    repay_accrued_interest_callable: (
        Callable[[state_utils.SmartContractState, Decimal], list[Posting]] | None
    ) = None,
    principal_address: str = lending_addresses.PRINCIPAL,
    overpayment_address: str = OVERPAYMENT_ADDRESS,
    fetchers_config: OverpaymentFetchersConfig = DEFAULT_OVERPAYMENT_FETCHERS_CONFIG,
) -> list[Posting]:
    """Creates postings to handle standard overpayments to principal and accrued interest.

    Args:
        state (state_utils.SmartContractState): the smart contract state
        overpayment_amount (Decimal): the amount to go towards principal and accrued interest
        repay_accrued_interest_callable: optional callable to repay accrued interest if applicable.
        principal_address (str, optional): the Principal balance address. Defaults to
            lending_addresses.PRINCIPAL.
        overpayment_address (str, optional): the Overpayment balance address. Defaults to
            OVERPAYMENT_ADDRESS.
        fetchers_config (OverpaymentFetchersConfig, optional): overpayment fetchers config. Defaults
            to DEFAULT_OVERPAYMENT_FETCHERS_CONFIG.

    Returns:
        list[Posting]: the corresponding postings. Empty list if the overpayment amount
            isn't greater than 0, or if there is nothing to overpay
    """

    if overpayment_amount <= 0:
        return []

    state = _append_to_state(state=state, fetchers_config=fetchers_config)

    rejection = state_utils.check_parameters_exist(
        state=state,
        param_ids={fetchers_config.denomination_param_id},
    )
    assert rejection is None, rejection

    denomination: str = state.parameters[fetchers_config.denomination_param_id]  # type: ignore

    postings: list[Posting] = []
    repayment_amount_remaining = overpayment_amount

    actual_outstanding_principal = balance_utils.net_debit(
        bal=balance_utils.get_current_net_balance(
            balances=state.balances,
            denomination=denomination,
            address=principal_address,
            phase=Phase.COMMITTED,
        )
    )

    # the principal and interest features could be decoupled via an interface in the future
    if (overpayment_posting_amount := min(overpayment_amount, actual_outstanding_principal)) > 0:
        # The overpayment that has hit DEFAULT must be rebalanced to PRINCIPAL to reflect what
        # has been repaid, and OVERPAYMENT is used as a tracker

        postings += posting_utils.create_postings(
            amount=overpayment_posting_amount,
            debit_account=state.vault.account_id,
            debit_address=DEFAULT_ADDRESS,
            credit_account=state.vault.account_id,
            credit_address=lending_addresses.PRINCIPAL,
            denomination=denomination,
        )

        postings += posting_utils.create_postings(
            amount=overpayment_posting_amount,
            debit_account=state.vault.account_id,
            debit_address=overpayment_address,
            credit_account=state.vault.account_id,
            credit_address=common_addresses.INTERNAL_CONTRA,
            denomination=denomination,
        )

        repayment_amount_remaining -= overpayment_posting_amount

    if repay_accrued_interest_callable:
        postings += repay_accrued_interest_callable(
            state,
            repayment_amount_remaining,
        )

    return postings


# TODO: Update to get precision from param instead. A few features will also need to be updated.
def get_early_repayment_overpayment_fee(
    state: state_utils.SmartContractState,
    precision: int = 2,
    fetchers_config: OverpaymentFetchersConfig = DEFAULT_OVERPAYMENT_FETCHERS_CONFIG,
) -> Decimal:
    """Get the early repayment overpayment fee amount.

    This is always the maximum overpayment fee.
    To be used as a get_early_repayment_fee_amount callable for an EarlyRepaymentFee interface.

    Args:
        state (state_utils.SmartContractState): the smart contract state
        precision (int, optional): the number of decimal places to round to. Defaults to 2.
        fetchers_config (OverpaymentFetchersConfig, optional): _description_. Defaults to
            DEFAULT_OVERPAYMENT_FETCHERS_CONFIG.

    Returns:
        Decimal: the flat fee amount
    """

    state = _append_to_state(state=state, fetchers_config=fetchers_config)

    rejection = state_utils.check_parameters_exist(
        state=state,
        param_ids={
            fetchers_config.denomination_param_id,
            fetchers_config.overpayment_fee_rate_param_id,
        },
    )

    assert rejection is None, rejection

    balances = state.balances
    denomination: str = state.parameters[fetchers_config.denomination_param_id]  # type: ignore
    overpayment_fee_rate: Decimal = state.parameters[fetchers_config.overpayment_fee_rate_param_id]  # type: ignore

    max_overpayment_fee = get_max_overpayment_fee(
        fee_rate=overpayment_fee_rate,
        balances=balances,
        denomination=denomination,
        precision=precision,
    )
    return max_overpayment_fee


def skip_charge_early_repayment_fee_for_overpayment(
    state: state_utils.SmartContractState,
    amount_to_charge: Decimal,
    fee_name: str,
    fetchers_config: OverpaymentFetchersConfig = DEFAULT_OVERPAYMENT_FETCHERS_CONFIG,
) -> list[CustomInstruction]:
    """Skip the charge for the overpayment fee within an early repayment.

    Since this fee posting is already handled by the overpayment logic within post posting.
    To be used as a charge_early_repayment_fee callable for an EarlyRepaymentFee interface.

    Args:
        state (state_utils.SmartContractState): The smart contract state
        amount_to_charge (Decimal): only needed to satisfy the interface signature
        fee_name (str): only needed to satisfy the interface signature
        fetchers_config (OverpaymentFetchersConfig, optional): overpayment fetchers config. Defaults
            to DEFAULT_OVERPAYMENT_FETCHERS_CONFIG.

    Returns:
        list[CustomInstruction]: An empty list
    """
    return []


def get_residual_cleanup_postings(
    balances: BalanceDefaultDict, account_id: str, denomination: str
) -> list[Posting]:
    """Generates postings to net out the overpayment tracker balance.

    This is typically used during account closure or deactivation to ensure
    all tracker balances are zeroed out before the account can be closed.

    Args:
        balances: The balances of the account.
        account_id: The ID of the account.
        denomination: The denomination of the overpayment balance.

    Returns:
        list[Posting]: The postings to clear the overpayment tracker balance.
    """

    overpayment_amount: Decimal = balance_utils.net_debit(
        bal=balance_utils.get_current_net_balance(
            balances=balances,
            address=OVERPAYMENT_ADDRESS,
            denomination=denomination,
        )
    )

    return posting_utils.create_postings(
        amount=overpayment_amount,
        debit_account=account_id,
        credit_account=account_id,
        debit_address=common_addresses.INTERNAL_CONTRA,
        credit_address=OVERPAYMENT_ADDRESS,
        denomination=denomination,
    )


OverpaymentFeature = lending_interfaces.Overpayment(
    handle_overpayment=handle_overpayment,
)

EarlyRepaymentOverpaymentFee = lending_interfaces.EarlyRepaymentFee(
    get_early_repayment_fee_amount=get_early_repayment_overpayment_fee,
    charge_early_repayment_fee=skip_charge_early_repayment_fee_for_overpayment,
    fee_name="Overpayment Fee",
)

OverpaymentResidualCleanupFeature = lending_interfaces.ResidualCleanup(
    get_residual_cleanup_postings=get_residual_cleanup_postings,
)

# TODO: Overpayment impact preference recalculations - Assume this can be done during post posting
