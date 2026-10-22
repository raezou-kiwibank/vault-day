# standard libs
from collections import namedtuple
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import DefaultDict

# contracts api
from contracts_api import DEFAULT_ADDRESS, DEFAULT_ASSET

# inception sdk
from inception_sdk.test_framework.common.constants import (
    DEFAULT_DENOMINATION,
    DEFAULT_POSTING_PHASE,
)
from inception_sdk.vault.core_api import LiveBalanceV2

# This is for sim and e2e tests only
BalanceDimensions = namedtuple(
    "BalanceDimensions",
    ["address", "asset", "denomination", "phase"],
    defaults=[DEFAULT_ADDRESS, DEFAULT_ASSET, DEFAULT_DENOMINATION, DEFAULT_POSTING_PHASE],
)


class Balance(object):
    def __init__(
        self,
        # These are the 'lossless' types to use. Decimal(float) works but results in unexpected
        # rounding issues and we don't want to encourage its use
        credit: Decimal | str | int = Decimal("0"),
        debit: Decimal | str | int = Decimal("0"),
        net: Decimal | str | int = Decimal("0"),
        value_timestamp: datetime | None = None,
    ):
        self.credit = Decimal(credit)
        self.debit = Decimal(debit)
        self.net = Decimal(net)
        self.value_timestamp = value_timestamp

    def __repr__(self):
        return f"Balance(credit={self.credit}, debit={self.debit}, net={self.net})"

    def __str__(self):
        return f"Balance(credit={self.credit}, debit={self.debit}, net={self.net})"

    def __eq__(self, other):
        return (
            isinstance(other, Balance)
            and self.net == other.net
            and self.credit == other.credit
            and self.debit == other.debit
        )

    def __add__(self, other):
        if not isinstance(other, Balance):
            return NotImplemented
        return Balance(
            credit=(self.credit + other.credit),
            debit=(self.debit + other.debit),
            net=(self.net + other.net),
        )


def compare_balances(
    expected_balances: list[tuple[BalanceDimensions, str]],
    actual_balances: DefaultDict[BalanceDimensions, Balance],
) -> dict[BalanceDimensions, dict[str, Decimal]]:
    """
    Compare two sets of balances, returning a dictionary with dimensions for which the two did not
    match as keys, and a dictionary containing the expected and actual balances for those
    dimensions as the values. For example:
    {
        BalanceDimensions('DEFAULT', 'COMMERCIAL_BANK_MONEY', 'GBP', 'POSTING_PHASE_COMMITTED'):{
            'expected': Decimal('10'),
            'actual': Decimal('5')
        }
    }

    Able to compare credits and debits of a balance if compare_debits_and_credits is True
    - Note that to be able to do this the expected balances must be
    dict[BalanceDimensions, ExpectedBalanceComparison]
    """
    return {
        dimensions: {
            "expected": Decimal(net),
            "actual": actual_balances[dimensions].net,
        }
        for dimensions, net in expected_balances
        if Decimal(net) != actual_balances[dimensions].net
    }


@dataclass
class NetBalance:
    """
    NetBalance is a subset of the Core API's LiveBalanceV2 class containing just the net amount.
    That is, it does not contain the `total_credit` or `total_debit`.
    """

    amount: Decimal
    account_id: str
    account_address: str
    phase: str
    asset: str
    denomination: str
    sub_account_id: str = ""


@dataclass
class NetBalances:
    """
    NetBalances wraps lists of `NetBalance` representing value and booking balances respectively.
    Each `NetBalance` represents an Account-level or Sub-Account-level net balance.
    """

    value_net_balances: list[NetBalance]
    booking_net_balances: list[NetBalance]


def dict_to_net_balance(data: dict) -> NetBalance:
    """
    Converts dict to a NetBalance. It first converts it to a LiveBalanceV2, including the validation
    of said model, before transforming it to a NetBalance.
    """
    live_balance = LiveBalanceV2.model_validate(dict(data))
    return NetBalance(
        amount=live_balance.amount,
        account_id=live_balance.account_id,
        account_address=live_balance.account_address,
        phase=live_balance.phase,
        asset=live_balance.asset,
        denomination=live_balance.denomination,
        sub_account_id=live_balance.sub_account_id,
    )


@dataclass
class NetBalanceMismatches:
    """
    Wrapper class for holding mismatched expected value and booking balances against actual
    value and booking balances.
    """

    expected_value_balances: list[NetBalance] = field(default_factory=list)
    expected_booking_balances: list[NetBalance] = field(default_factory=list)
    actual_value_balances: list[NetBalance] = field(default_factory=list)
    actual_booking_balances: list[NetBalance] = field(default_factory=list)


def get_account_ids_from_net_balances(balances: NetBalances) -> set[str]:
    """
    Returns all the unique Account IDs present within the given NetBalances.

    :param balances: The balances to retrieve Account IDs from.
    """
    return {b.account_id for b in balances.value_net_balances + balances.booking_net_balances}


def get_net_balances_for_account(
    balances: NetBalances,
    account_id: str,
) -> NetBalances:
    """
    Filters balances by an account_id, returning only those balances which have that
    account_id.

    :param balances: The balances to be filtered.
    :param account_id: The Account ID to use as the filter.
    """
    return NetBalances(
        value_net_balances=[b for b in balances.value_net_balances if b.account_id == account_id],
        booking_net_balances=[
            b for b in balances.booking_net_balances if b.account_id == account_id
        ],
    )


def get_net_balance_mismatches(
    expected: NetBalances,
    actual: NetBalances,
) -> dict[str, NetBalanceMismatches]:
    """
    Compares two balance lists, returning a dictionary mapping
    Account IDs to net balance mismatches for balances which are in the expected list
    but not present in the actual list.

    :param expected: Expected balances to be present.
    :param actual: Actual balances to check against.
    :return: dict mapping Account ID to NetBalanceMismatches
    """
    mismatches: dict[str, NetBalanceMismatches] = {}

    account_ids = get_account_ids_from_net_balances(expected)

    for account_id in account_ids:
        expected_balances_for_account = get_net_balances_for_account(expected, account_id)
        actual_balances_for_account = get_net_balances_for_account(actual, account_id)

        has_mismatched_value_balances = any(
            b not in actual_balances_for_account.value_net_balances
            for b in expected_balances_for_account.value_net_balances
        )
        has_mismatched_booking_balances = any(
            b not in actual_balances_for_account.booking_net_balances
            for b in expected_balances_for_account.booking_net_balances
        )

        if has_mismatched_value_balances or has_mismatched_booking_balances:
            mismatch = NetBalanceMismatches()

            if has_mismatched_value_balances:
                mismatch.expected_value_balances = expected_balances_for_account.value_net_balances
                mismatch.actual_value_balances = actual_balances_for_account.value_net_balances

            if has_mismatched_booking_balances:
                mismatch.expected_booking_balances = (
                    expected_balances_for_account.booking_net_balances
                )
                mismatch.actual_booking_balances = actual_balances_for_account.booking_net_balances

            mismatches[account_id] = mismatch

    return mismatches
