from collections import defaultdict
from copy import deepcopy
from functools import lru_cache
from decimal import Decimal
from typing import Dict, NamedTuple, Optional, List, Callable
from datetime import datetime

from .enums import (
    Phase,
    Tside,
    DateTimeView,
)

from ...common.docs import _common_docs_path
from .....utils import symbols, types_utils
from .....utils.exceptions import InvalidSmartContractError
from .....utils.timezone_utils import validate_timezone_is_utc


class AddressDetails(types_utils.ContractsLanguageDunderMixin):
    def __init__(
        self, *, account_address: str, description: str, tags: List[str], _from_proto: bool = False
    ):
        self.account_address = account_address
        self.description = description
        self.tags = tags
        if not _from_proto:
            self._validate_attributes()

    def _validate_attributes(self):
        if self.account_address is None or self.account_address == "":
            raise InvalidSmartContractError("AddressDetails 'account_address' must be populated")
        if self.description is None:
            raise InvalidSmartContractError("AddressDetails 'description' must be populated")
        if self.tags is None:
            raise InvalidSmartContractError("AddressDetails 'tags' must be populated")
        types_utils.validate_type(self.tags, list, prefix="tags")

    @classmethod
    @lru_cache()
    def _spec(cls, language_code=symbols.Languages.ENGLISH):
        if language_code != symbols.Languages.ENGLISH:
            raise ValueError("Language not supported")

        return types_utils.ClassSpec(
            name="AddressDetails",
            docstring="""
                Address details gives a rich description of an address.
                The tags can be shared between addresses and even different accounts.
            """,
            public_attributes=[
                types_utils.ValueSpec(
                    name="account_address",
                    type="str",
                    docstring="""
                        The account address the details describe.
                    """,
                ),
                types_utils.ValueSpec(
                    name="description",
                    type="str",
                    docstring="""
                        The human-readable description of the address.
                    """,
                ),
                types_utils.ValueSpec(
                    name="tags",
                    type="List[str]",
                    docstring="""
                        The list of string tags related to the described address.
                    """,
                ),
            ],
            constructor=types_utils.ConstructorSpec(
                docstring="Constructs a new AddressDetails object.",
                args=[
                    types_utils.ValueSpec(
                        name="account_address",
                        type="str",
                        docstring="""
                        The account address the details describe.
                    """,
                    ),
                    types_utils.ValueSpec(
                        name="description",
                        type="str",
                        docstring="""
                        The human-readable description of the address.
                    """,
                    ),
                    types_utils.ValueSpec(
                        name="tags",
                        type="List[str]",
                        docstring="""
                        The list of string tags related to the described address.
                    """,
                    ),
                ],
            ),
        )


class SubAccountAddressDetails(types_utils.ContractsLanguageDunderMixin):
    def __init__(self, *, address: str, description: Optional[str] = None):
        self.address = address
        self.description = description
        self._validate_attributes()

    def _validate_attributes(self):
        types_utils.validate_type(
            self.address,
            str,
            check_empty=True,
            hint="str",
            prefix=f"{self.__class__.__name__}.address",
        )
        types_utils.validate_type(
            self.description,
            str,
            check_empty=False,
            is_optional=True,
            hint="str",
            prefix=f"{self.__class__.__name__}.description",
        )

    @classmethod
    @lru_cache()
    def _spec(cls, language_code=symbols.Languages.ENGLISH):
        if language_code != symbols.Languages.ENGLISH:
            raise ValueError("Language not supported")

        return types_utils.ClassSpec(
            name=cls.__name__,
            docstring="SubAccountAddressDetails describes an address for a Sub-Account.",
            public_attributes=cls._public_attributes(language_code),
            constructor=types_utils.ConstructorSpec(
                docstring=f"Constructs a new {cls.__name__} object.",
                args=cls._public_attributes(language_code),
            ),
        )

    @classmethod
    @lru_cache()
    def _public_attributes(cls, language_code=symbols.Languages.ENGLISH):
        if language_code != symbols.Languages.ENGLISH:
            raise ValueError("Language not supported")

        return [
            types_utils.ValueSpec(
                name="address",
                type="str",
                docstring="The address that belongs to a Sub-Account.",
            ),
            types_utils.ValueSpec(
                name="description",
                type="Optional[str]",
                docstring="The description of the address that belongs to a Sub-Account.",
            ),
        ]


class Balance(types_utils.ContractsLanguageDunderMixin):
    def __init__(
        self,
        credit: Decimal = Decimal(0),
        debit: Decimal = Decimal(0),
        net: Decimal = Decimal(0),
    ):
        self.credit = credit
        self.debit = debit
        self.net = net

    def _adjust(
        self,
        tside: Tside,
        credit: Optional[Decimal] = None,
        debit: Optional[Decimal] = None,
    ):
        if credit:
            self.credit += credit
        if debit:
            self.debit += debit
        self.net = (self.credit - self.debit) * symbols.TSIDE_NET_BALANCE_MAP[tside.value]

    def __str__(self):
        return "Balance(credit=%s, debit=%s, net=%s)" % (self.credit, self.debit, self.net)

    @classmethod
    @lru_cache()
    def _spec(cls, language_code=symbols.Languages.ENGLISH):
        if language_code != symbols.Languages.ENGLISH:
            raise ValueError("Language not supported")

        return types_utils.ClassSpec(
            name="Balance",
            docstring=(
                "The credit, debit, and net balances (credit - debit) for a given balance phase."
            ),
            public_attributes=cls._public_attributes(language_code),  # noqa: SLF001
            constructor=types_utils.ConstructorSpec(
                docstring="Constructs a new Balance object.",
                args=cls._public_attributes(language_code),  # noqa: SLF001
            ),
            public_methods=[
                types_utils.MethodSpec(
                    name="__str__",
                    docstring="Python dunder method. Returns a string representation of the class name and its attributes.",
                    args=[],
                    return_value=types_utils.ValueSpec(
                        name=None,
                        type="str",
                        docstring="A string representation. Example: `Balance(credit=20, debit=16, net=4)`",
                    ),
                ),
            ],
        )

    @classmethod
    @lru_cache()
    def _public_attributes(cls, language_code=symbols.Languages.ENGLISH):
        if language_code != symbols.Languages.ENGLISH:
            raise ValueError("Language not supported")

        return [
            types_utils.ValueSpec(
                name="credit", type="Decimal", docstring="The total credit balance"
            ),
            types_utils.ValueSpec(
                name="debit", type="Decimal", docstring="The total debit balance"
            ),
            types_utils.ValueSpec(
                name="net",
                type="Decimal",
                docstring="""
                    The total net balance.
                    If the contract specifies Tside.LIABILITY, this will equal (credit - debit).
                    If the contract specifies Tside.ASSET, this will equal (debit - credit).
                """,
            ),
        ]

    def __add__(self, other):
        return self.__class__(
            credit=self.credit + other.credit,
            debit=self.debit + other.debit,
            net=self.net + other.net,
        )

    def __radd__(self, other):
        return self.__add__(other)

    def __iadd__(self, other):
        self.credit += other.credit
        self.debit += other.debit
        self.net += other.net
        return self


class BalanceCoordinate(NamedTuple):
    account_address: str
    asset: str
    denomination: str
    phase: Phase

    def __str__(self):
        return (
            f"BalanceCoordinate(account_address={self.account_address}, asset={self.asset}, "
            f"denomination={self.denomination}, phase={self.phase})"
        )

    @classmethod
    @lru_cache()
    def _spec(cls, language_code=symbols.Languages.ENGLISH):
        if language_code != symbols.Languages.ENGLISH:
            raise ValueError("Language not supported")

        return types_utils.ClassSpec(
            name="BalanceCoordinate",
            docstring=f"""
                Unique key for
                [BalanceDefaultDict]({_common_docs_path}classes/#BalanceDefaultDict)
                made up of attributes identifying a particular Balance.
            """,
            public_attributes=cls._public_attributes(language_code),
            constructor=types_utils.ConstructorSpec(
                docstring="Constructs a new BalanceCoordinate object.",
                args=cls._public_attributes(language_code),
            ),
            public_methods=[
                types_utils.MethodSpec(
                    name="__str__",
                    docstring="Python dunder method. Returns a string representation of the class name and its attributes.",
                    args=[],
                    return_value=types_utils.ValueSpec(
                        name=None,
                        type="str",
                        docstring="A string representation. Example: `BalanceCoordinate(account_address=DEFAULT, asset=COMMERCIAL_BANK_MONEY, denomination=GBP, phase=Phase.COMMITTED)`",
                    ),
                ),
            ],
        )

    @classmethod
    @lru_cache()
    def _public_attributes(cls, language_code=symbols.Languages.ENGLISH):
        if language_code != symbols.Languages.ENGLISH:
            raise ValueError("Language not supported")
        return [
            types_utils.ValueSpec(
                name="account_address",
                type="str",
                docstring="The account address associated with the Balance.",
            ),
            types_utils.ValueSpec(
                name="asset",
                type="str",
                docstring="The underlying asset of the Balance.",
            ),
            types_utils.ValueSpec(
                name="denomination",
                type="str",
                docstring="The underlying denomination of the Balance.",
            ),
            types_utils.ValueSpec(
                name="phase",
                type="Phase",
                docstring="The current phase of the Balance.",
            ),
        ]


class BalanceDefaultDict(defaultdict):
    _balance = Balance

    def __init__(
        self,
        default_factory: Optional[Callable[..., Balance]] = None,
        mapping: Optional[Dict[BalanceCoordinate, Balance]] = None,
        **_,
    ):
        super().__init__(
            default_factory if default_factory else lambda *_: self._balance(),
            mapping if mapping else {},
        )

    def __add__(self, other):
        aggregated_balance_dict = deepcopy(self)
        for balance_key, balance in other.items():
            if balance_key in aggregated_balance_dict:
                aggregated_balance_dict[balance_key] = (
                    aggregated_balance_dict[balance_key] + balance
                )
            else:
                aggregated_balance_dict[balance_key] = balance

        return aggregated_balance_dict

    def __radd__(self, other):
        return self.__add__(other)

    def __iadd__(self, other):
        for balance_key, balance in other.items():
            self[balance_key] = self.get(balance_key, self._balance()) + balance
        return self

    def __repr__(self):
        balance_dict_str = {}
        for balance_key, balance in self.items():
            balance_dict_str[str(balance_key)] = str(balance)
        return str(balance_dict_str)

    @classmethod
    @lru_cache()
    def _spec(cls, language_code=symbols.Languages.ENGLISH):
        if language_code != symbols.Languages.ENGLISH:
            raise ValueError("Language not supported")
        return types_utils.ClassSpec(
            name="BalanceDefaultDict",
            docstring="""
                The key is a BalanceCoordinate object which contains the account_address, asset,
                denomination and phase. The value is a Balance object which contains the debit,
                credit and net balance changes. Returns defaultdict object, type -
                `Dict[BalanceCoordinate, Balance]`. If non-existing key is accessed, value with
                zero debit, credit and net balance changes returned. BalanceDefaultDict objects
                support addition operations from 3.6+.
            """,
        )


class BalancesObservation(types_utils.ContractsLanguageDunderMixin):
    def __init__(
        self,
        *,
        balances: BalanceDefaultDict,
        value_datetime: Optional[datetime] = None,
        at_datetime: Optional[datetime] = None,
        datetime_view: DateTimeView = DateTimeView.VALUE_DATETIME,
        _from_proto: bool = False,
    ):
        self.value_datetime = value_datetime
        self.balances = balances
        self.at_datetime = at_datetime
        self.datetime_view = datetime_view
        if not _from_proto:
            self._validate_attributes()

    def _validate_attributes(self):
        if self.value_datetime:
            validate_timezone_is_utc(
                self.value_datetime,
                "value_datetime",
                "BalancesObservation",
            )
        types_utils.validate_type(
            self.balances, BalanceDefaultDict, prefix="BalancesObservation.balances"
        )

    @classmethod
    @lru_cache()
    def _spec(cls, language_code=symbols.Languages.ENGLISH):
        if language_code != symbols.Languages.ENGLISH:
            raise ValueError("Language not supported")

        return types_utils.ClassSpec(
            name="BalancesObservation",
            docstring="""
                A `BalanceDefaultDict` containing an Account's balances observed at a fixed point in time.
            """,
            public_attributes=cls._public_attributes(language_code),
            constructor=types_utils.ConstructorSpec(
                docstring="Constructs a new BalancesObservation object.",
                args=cls._public_attributes(language_code),
            ),
        )

    @classmethod
    @lru_cache()
    def _public_attributes(cls, language_code=symbols.Languages.ENGLISH):
        if language_code != symbols.Languages.ENGLISH:
            raise ValueError("Language not supported")

        value_datetime_docstring = """
                    The time at which the balances are observed. This attribute will be None for
                    a live balances observation. Must be a timezone-aware UTC datetime using
                    the ZoneInfo class.
                """
        value_datetime_docstring = """
                    The time at which the balances are observed for `DateTimeView.VALUE_DATETIME`. This attribute will
                    be None for a live balances observation, or a balances observation on `DateTimeView.BOOKING_DATETIME`.
                    Note that `value_datetime` is not compatible with `DateTimeView.BOOKING_DATETIME` and `at_datetime`
                    should be used for observations on both `DateTimeView.BOOKING_DATETIME` and `DateTimeView.VALUE_DATETIME`.
                """
        public_attributes = [
            types_utils.ValueSpec(
                name="balances",
                type="BalanceDefaultDict",
                docstring="The balances at the given datetime.",
            ),
            types_utils.ValueSpec(
                name="value_datetime",
                type="Optional[datetime]",
                docstring=value_datetime_docstring,
            ),
            types_utils.ValueSpec(
                name="at_datetime",
                type="Optional[datetime]",
                docstring="""
                    The time at which the balances are observed with respect to the given `DateTimeView`. This
                    attribute will be None for a live balances observation. Must be a timezone-aware UTC datetime
                    using the ZoneInfo class.
                """,
            ),
            types_utils.ValueSpec(
                name="datetime_view",
                type="Optional[DateTimeView]",
                docstring="""
                    The datetime view on which the balances are observed. This attribute will be
                    `DateTimeview.VALUE_DATETIME` by default, if datetime_view is not specified on the fetcher.
                """,
            ),
        ]

        return public_attributes
