__smart_contract_feature__ = True

# standard libs
from decimal import Decimal
from typing import Any, Callable, NamedTuple

# feature library
# contracts api
from contracts_api import CustomInstruction, Posting

# inception sdk

Amortisation = NamedTuple(
    "Amortisation",
    [
        (
            "calculate_eia",
            Callable[
                # state: state_utils.SmartContractState,
                # use_expected_term: bool,
                # principal_amount: Decimal | None,
                # interest_calculation_feature: InterestRate | None,
                # principal_adjustments: list[PrincipalAdjustment] | None,
                ...,
                Decimal,
            ],
        ),
        (
            "term_details",
            Callable[
                # state: state_utils.SmartContractState,
                # use_expected_term: bool,
                # interest_rate: InterestRate | None,
                # principal_adjustments: list[PrincipalAdjustment] | None,
                ...,
                # elapsed term, remaining term
                tuple[int, int],
            ],
        ),
        (
            "override_final_event",
            # Override the final event where we do not want to move the remaining principal
            # to principal due. An example of this is for balloon payments where the final
            # principal application will be deferred for the balloon payment.
            bool,
        ),
    ],
)

SupervisorAmortisation = NamedTuple(
    "SupervisorAmortisation",
    [
        (
            "calculate_eia",
            Callable[
                # loan_state: state_utils.SmartContractState,
                # main_state: state_utils.SmartContractState,
                # use_expected_term: bool,
                # principal_amount: Decimal | None,
                # interest_calculation_feature: InterestRate | None,
                # principal_adjustments: list[SupervisorPrincipalAdjustment] | None,
                ...,
                Decimal,
            ],
        ),
        (
            "term_details",
            Callable[
                # loan_state: state_utils.SmartContractState,
                # main_state: state_utils.SmartContractState,
                # use_expected_term: bool,
                # interest_rate: InterestRate | None,
                # principal_adjustments: list[SupervisorPrincipalAdjustment] | None,
                ...,
                # elapsed term, remaining term
                tuple[int, int],
            ],
        ),
        (
            "override_final_event",
            # Override the final event where we do not want to move the remaining principal
            # to principal due. An example of this is for balloon payments where the final
            # principal application will be deferred for the balloon payment.
            bool,
        ),
    ],
)

ReamortisationCondition = NamedTuple(
    "ReamortisationCondition",
    [
        (
            "should_trigger_reamortisation",
            Callable[
                # state: state_utils.SmartContractState,
                # period_start_datetime: datetime,
                # period_end_datetime: datetime,
                # elapsed_term: int | None,
                ...,
                bool,
            ],
        ),
    ],
)

SupervisorReamortisationCondition = NamedTuple(
    "SupervisorReamortisationCondition",
    [
        (
            "should_trigger_reamortisation",
            Callable[
                # loan_state: state_utils.SmartContractState,
                # main_state: state_utils.SmartContractState,
                # period_start_datetime: datetime,
                # period_end_datetime: datetime,
                # elapsed_term: int | None,
                ...,
                bool,
            ],
        ),
    ],
)

InterestRate = NamedTuple(
    "InterestRate",
    [
        (
            "get_daily_interest_rate",
            Callable[
                # state: state_utils.SmartContractState,
                ...,
                Decimal,
            ],
        ),
        (
            "get_monthly_interest_rate",
            Callable[
                # state: state_utils.SmartContractState,
                ...,
                Decimal,
            ],
        ),
        (
            "get_annual_interest_rate",
            Callable[
                # state: state_utils.SmartContractState,
                ...,
                Decimal,
            ],
        ),
    ],
)

InterestRateConfig = NamedTuple(
    "InterestRateConfig",
    [
        ("interest_rate", InterestRate),
        ("fetchers_config", Any),
    ],
)

Overpayment = NamedTuple(
    "Overpayment",
    [
        (
            "handle_overpayment",
            Callable[
                # state: state_utils.SmartContractState,
                # overpayment_amount: Decimal,
                # repay_accrued_interest_callable: Callable,
                ...,
                list[Posting],
            ],
        ),
    ],
)

MultiTargetOverpayment = NamedTuple(
    "MultiTargetOverpayment",
    [
        (
            "handle_overpayment",
            Callable[
                # main_state: state_utils.SmartContractState,
                # overpayment_amount: Decimal,
                # balances_per_target_vault: dict[SuperviseeContractVault, BalanceDefaultDict],
                ...,
                dict[str, list[Posting]],
            ],
        )
    ],
)

PrincipalAdjustment = NamedTuple(
    "PrincipalAdjustment",
    [
        (
            "calculate_principal_adjustment",
            Callable[
                # state: state_utils.SmartContractState,
                ...,
                Decimal,
            ],
        ),
    ],
)
SupervisorPrincipalAdjustment = NamedTuple(
    "SupervisorPrincipalAdjustment",
    [
        (
            "calculate_principal_adjustment",
            Callable[
                # loan_state: state_utils.SmartContractState,
                # main_state: state_utils.SmartContractState,
                ...,
                Decimal,
            ],
        ),
    ],
)

ResidualCleanup = NamedTuple(
    "ResidualCleanup",
    [
        (
            "get_residual_cleanup_postings",
            Callable[
                # state: state_utils.SmartContractState,
                # account_id:str
                ...,
                list[Posting],
            ],
        ),
    ],
)

# Non-EIA interest for a given due amount calculation is the interest accrued outside of the
# due amount calculation period (e.g. more than a month from the due amount calculation day,
# assuming a monthly repayment frequency).
# While the sum of EIA and non-EIA interest represent the due interest for that period, only the
# EIA interest typically contributes to the due principal calculation. This ensures that the
# principal paid by the customer in their first repayment, or after a due amount calculation day
# change, is not affected by the additional number of days in the period.
InterestAmounts = NamedTuple(
    "InterestAmounts",
    [
        ("eia_rounded_accrued", Decimal),
        ("eia_accrued", Decimal),
        ("non_eia_rounded_accrued", Decimal),
        ("non_eia_accrued", Decimal),
        ("total_rounded", Decimal),
    ],
)

InterestApplication = NamedTuple(
    "InterestApplication",
    [
        (
            "apply_interest",
            Callable[..., list[Posting]],
        ),
        (
            "get_interest_to_apply",
            Callable[..., InterestAmounts],
        ),
    ],
)

EarlyRepaymentFee = NamedTuple(
    "EarlyRepaymentFee",
    [
        ("get_early_repayment_fee_amount", Callable[..., Decimal]),
        ("charge_early_repayment_fee", Callable[..., list[CustomInstruction]]),
        ("fee_name", str),
    ],
)

RepaymentHierarchy = NamedTuple(
    "RepaymentHierarchy",
    [
        ("get_total_outstanding_debt", Callable[..., Decimal]),
        ("get_total_overdue_amount", Callable[..., Decimal]),
        ("get_total_due_amount", Callable[..., Decimal]),
        ("get_repayment_hierarchy_order", Callable[..., list[str]]),
    ],
)

RepaymentHierarchyConfig = NamedTuple(
    "RepaymentHierarchyConfig",
    [
        ("repayment_hierarchy", RepaymentHierarchy),
        ("fetchers_config", Any),
    ],
)

CreditLimitCheck = NamedTuple(
    "CreditLimitCheck",
    [
        (
            "get_available_credit",
            Callable[
                ...,
                Decimal,
            ],
        ),
    ],
)

PaymentAllocation = NamedTuple(
    "PaymentAllocation",
    [
        (
            "allocate_payment",
            Callable[
                ...,
                list,
            ],
        ),
    ],
)

TransactionFee = NamedTuple(
    "TransactionFee",
    [
        (
            "calculate_fee",
            Callable[
                ...,
                Decimal,
            ],
        ),
        ("fee_type", str),
    ],
)

MinimumPaymentCalculation = NamedTuple(
    "MinimumPaymentCalculation",
    [
        (
            "calculate_minimum_payment",
            Callable[
                ...,
                Decimal,
            ],
        ),
    ],
)
