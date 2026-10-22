# Copyright @ 2026 Thought Machine Group Limited. All rights reserved.
# standard libs
from datetime import datetime
from decimal import Decimal
from typing import overload

# contracts api
from contracts_api import (
    DEFAULT_ADDRESS,
    DEFAULT_ASSET,
    Balance,
    BalanceCoordinate,
    BalanceDiscreteTimeseries,
    BalanceTimeseries,
    Phase,
    Tside,
)


@overload
def balance(self, *, net: Decimal | str): ...


@overload
def balance(self, *, debit: Decimal | str, credit: Decimal | str): ...


def balance(
    self,
    *,
    net: Decimal | str | None = None,
    debit: Decimal | str | None = None,
    credit: Decimal | str | None = None,
) -> Balance:
    """
    Given a net, or a debit/credit pair, return an equivalent Balance object
    Direction of net is derived from Tside of account (asset vs. liability).
    Only currently works for positive net values.
    :param net: If populated, debit and credit parameters are ignored. For Liability tside, the
    debit is set to 0 and credit set to net. For Asset tside, the debit it set to net and credit
    set to 0. If not populated, net is derived as debit - credit (tside Asset) or
    credit - debit (tside Liability)
    :param debit: Only considered if net is not populated. If so, must be >= 0 and credit must
    also be populated
    :param credit: Only considered if net is not populated. If so, must be >= 0 and debit must
    also be populated
    """
    if net is None:
        if credit is None or debit is None:
            raise ValueError("Cannot create balance with net `None` and credit/debit also `None`")
        credit = Decimal(credit)
        debit = Decimal(debit)
        if credit < 0 or debit < 0:
            raise ValueError(f"{credit=} and {debit=} must be zero or positive")
        net = credit - debit if self.tside == Tside.LIABILITY else debit - credit

    else:
        net = Decimal(net)
        if self.tside == Tside.LIABILITY and net > 0 or self.tside == Tside.ASSET and net < 0:
            credit = abs(net)
            debit = Decimal(0)
        else:
            credit = Decimal(0)
            debit = abs(net)
    return Balance(debit=debit, credit=credit, net=net)


def balance_coordinate(
    self,
    *,
    account_address: str = DEFAULT_ADDRESS,
    denomination: str = "",
    phase: Phase = Phase.COMMITTED,
    asset: str = DEFAULT_ASSET,
) -> BalanceCoordinate:
    denomination = denomination if denomination else self.default_denomination
    return BalanceCoordinate(
        account_address=account_address,
        asset=asset,
        denomination=denomination,
        phase=phase,
    )


@overload
def construct_balance_timeseries(
    self,
    *,
    dt: datetime,
    net: Decimal | str,
) -> BalanceTimeseries: ...


@overload
def construct_balance_timeseries(
    self,
    *,
    dt: datetime,
    debit: Decimal | str,
    credit: Decimal | str,
) -> BalanceTimeseries: ...


def construct_balance_timeseries(
    self,
    *,
    dt: datetime,
    net: Decimal | str | None = None,
    debit: Decimal | str | None = None,
    credit: Decimal | str | None = None,
) -> BalanceTimeseries:
    """
    Creates a BalanceTimeseries with a single balance, as specified by net or debit/credit,
    at dt.

    :param datetime dt: timestamps of the balances present in your desired timeseries
    :param net: If populated, debit and credit parameters are ignored.
    For Liability tside, the debit is set to 0 and credit set to net. For Asset tside, the
    debit it set to net and credit set to 0. If not populated, net is derived as
    debit - credit (tside Asset) or credit - debit (tside Liability)
    :param debit: Only considered if net is not populated. If so, must be >= 0 and credit must
    also be populated
    :param credit: Only considered if net is not populated. If so, must be >= 0 and debit must
    also be populated
    :return BalanceTimeseries: Simple BalanceTimeseries with 1 balance at 1 time point
    """
    if net is not None:
        return BalanceTimeseries([(dt, self.balance(net=net))])
    elif debit is not None and credit is not None:
        return BalanceTimeseries([(dt, self.balance(debit=debit, credit=credit))])
    else:
        raise ValueError("Specify net alone, or debit and credit")


@overload
def construct_balance_discrete_timeseries(
    self,
    *,
    dt: datetime,
    net: Decimal | str,
) -> BalanceDiscreteTimeseries: ...


@overload
def construct_balance_discrete_timeseries(
    self,
    *,
    dt: datetime,
    debit: Decimal | str,
    credit: Decimal | str,
) -> BalanceDiscreteTimeseries: ...


def construct_balance_discrete_timeseries(
    self,
    *,
    dt: datetime,
    net: Decimal | str | None = None,
    debit: Decimal | str | None = None,
    credit: Decimal | str | None = None,
) -> BalanceDiscreteTimeseries:
    """
    Creates a BalanceDiscreteTimeseries with a single balance, as specified by net
    or debit/credit, at dt.

    :param datetime dt: timestamps of the balances present in your desired timeseries
    :param net: If populated, debit and credit parameters are ignored.
    For Liability tside, the debit is set to 0 and credit set to net. For Asset tside, the
    debit it set to net and credit set to 0. If not populated, net is derived as
    debit - credit (tside Asset) or credit - debit (tside Liability)
    :param debit: Only considered if net is not populated. If so, must be >= 0 and credit must
    also be populated
    :param credit: Only considered if net is not populated. If so, must be >= 0 and debit must
    also be populated
    :return BalanceDiscreteTimeseries: Simple BalanceDiscreteTimeseries with 1 balance at
    1 time point
    """
    if net is not None:
        return BalanceDiscreteTimeseries([(dt, self.balance(net=net))])
    elif debit is not None and credit is not None:
        return BalanceDiscreteTimeseries([(dt, self.balance(debit=debit, credit=credit))])
    else:
        raise ValueError("Specify net alone, or debit and credit")
