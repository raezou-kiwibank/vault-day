__smart_contract_feature__ = True

# standard libs
from decimal import Decimal
from typing import Any, Callable, NamedTuple

import feature_library.common.tuples as common_tuples

InterestType = NamedTuple(
    "InterestType",
    [
        (
            "get_interest_rate",
            Callable[..., common_tuples.InterestRateTuple],
        ),
        (
            "get_accrual_amount",
            Callable[..., common_tuples.AccrualDetail],
        ),
        (
            "get_accrual_payable_customer_address",
            Callable[..., str],
        ),
        (
            "get_accrual_receivable_customer_address",
            Callable[..., str],
        ),
        (
            "get_accrual_payable_internal_account",
            Callable[..., str],
        ),
        (
            "get_accrual_receivable_internal_account",
            Callable[..., str],
        ),
    ],
)


InterestTypeConfig = NamedTuple(
    "InterestTypeConfig",
    [
        ("interest_type", InterestType),
        ("fetchers_config", Any),
    ],
)


PartialFeeCollection = NamedTuple(
    "PartialFeeCollection",
    [
        ("outstanding_fee_address", str),
        ("fee_type", str),
        ("internal_account_parameter_id", str),
    ],
)

AvailableBalance = NamedTuple(
    "AvailableBalance",
    [
        (
            "calculate",
            Callable[
                # state: SmartContractState,
                ...,
                Decimal,
            ],
        ),
    ],
)

DefaultBalanceAdjustment = NamedTuple(
    "DefaultBalanceAdjustment",
    [
        (
            "calculate_balance_adjustment",
            Callable[
                # vault: SmartContractVault,
                # balances: BalanceDefaultDict | None,
                # denomination: str | None
                ...,
                Decimal,
            ],
        ),
    ],
)

WaiveFeeCondition = NamedTuple(
    "WaiveFeeCondition",
    [
        (
            "waive_fees",
            Callable[
                # vault: SmartContractVault,
                # effective_datetime: datetime,
                # denomination: str | None = None,
                ...,
                bool,
            ],
        ),
    ],
)
