# standard libs
from abc import ABC, abstractmethod
from collections import defaultdict
from datetime import datetime
from typing import Mapping, overload
from zoneinfo import ZoneInfo

# contracts api
from contracts_api import (
    AuthorisationAdjustment,
    BalanceCoordinate,
    BalanceDiscreteTimeseries,
    BalancesObservation,
    BalanceTimeseries,
    CalendarEvents,
    CalendarsObservation,
    CalendarTimeseries,
    ClientTransaction,
    CustomInstruction,
    FlagsObservation,
    FlagTimeseries,
    FlagValueTimeseries,
    HookName,
    InboundAuthorisation,
    InboundHardSettlement,
    LastScheduledEventDateTimesObservation,
    OutboundAuthorisation,
    OutboundHardSettlement,
    ParametersObservation,
    ParameterTimeseries,
    ParameterValueTimeseries,
    PostPostingHookResult,
    PrePostingHookResult,
    Release,
    ScheduledEventHookResult,
    Settlement,
    Transfer,
    Tside,
)


class SubAccountVault(ABC):
    _sub_account_id: str
    _sub_account_type: str

    @property
    def sub_account_id(self) -> str:
        return self._sub_account_id

    @property
    def sub_account_type(self) -> str:
        return self._sub_account_type

    @abstractmethod
    def get_balances_discrete_timeseries(
        self, *, fetcher_id: str
    ) -> Mapping[BalanceCoordinate, BalanceDiscreteTimeseries]: ...

    @abstractmethod
    def get_balances_observation(self, *, fetcher_id: str) -> BalancesObservation: ...

    @abstractmethod
    def get_balances_timeseries(
        self, *, fetcher_id: str
    ) -> Mapping[BalanceCoordinate, BalanceTimeseries]: ...

    @abstractmethod
    def get_client_transactions(self, *, fetcher_id: str) -> dict[str, ClientTransaction]: ...

    @abstractmethod
    def get_posting_instructions(
        self, *, fetcher_id: str
    ) -> list[
        AuthorisationAdjustment
        | CustomInstruction
        | InboundAuthorisation
        | InboundHardSettlement
        | OutboundAuthorisation
        | OutboundHardSettlement
        | Release
        | Settlement
        | Transfer
    ]: ...

    @abstractmethod
    def get_sub_account_activation_datetime(self) -> datetime: ...


class SmartContractVault(ABC):
    _account_id: str
    _tside: Tside
    _events_timezone: ZoneInfo
    _sub_accounts: defaultdict[str, SubAccountVault]

    @property
    def account_id(self) -> str:
        return self._account_id

    @property
    def tside(self) -> Tside:
        return self._tside

    @property
    def events_timezone(self) -> ZoneInfo:
        return self._events_timezone

    @property
    def sub_accounts(self) -> defaultdict[str, SubAccountVault]:
        return self._sub_accounts

    @abstractmethod
    def get_account_activation_datetime(self) -> datetime: ...

    @abstractmethod
    def get_account_creation_datetime(self) -> datetime | None: ...

    @abstractmethod
    def get_balances_discrete_timeseries(
        self, *, fetcher_id: str
    ) -> Mapping[BalanceCoordinate, BalanceDiscreteTimeseries]: ...

    @abstractmethod
    def get_balances_observation(self, *, fetcher_id: str) -> BalancesObservation: ...

    @abstractmethod
    def get_balances_timeseries(
        self, *, fetcher_id: str
    ) -> Mapping[BalanceCoordinate, BalanceTimeseries]: ...

    @abstractmethod
    def get_calendar_events(self, *, calendar_ids: list[str]) -> CalendarEvents: ...

    @abstractmethod
    def get_calendars_observation(self, *, fetcher_id: str) -> CalendarsObservation: ...

    @abstractmethod
    def get_calendars_timeseries(self, *, fetcher_id: str) -> dict[str, CalendarTimeseries]: ...

    @abstractmethod
    def get_client_transactions(self, *, fetcher_id: str) -> dict[str, ClientTransaction]: ...

    @abstractmethod
    def get_flag_timeseries(self, *, flag: str) -> FlagTimeseries: ...

    @abstractmethod
    def get_flags_observation(self, *, fetcher_id: str) -> FlagsObservation: ...

    @abstractmethod
    def get_flags_timeseries(self, *, fetcher_id: str) -> dict[str, FlagValueTimeseries]: ...

    @abstractmethod
    def get_hook_execution_id(self) -> str: ...

    @abstractmethod
    def get_hook_name(self) -> HookName: ...

    @abstractmethod
    def get_last_execution_datetime(self, *, event_type: str) -> datetime | None: ...

    @abstractmethod
    def get_last_scheduled_event_datetimes_observation(
        self, *, fetcher_id: str
    ) -> LastScheduledEventDateTimesObservation: ...

    @overload
    def get_parameter_timeseries(self, *, name: str) -> ParameterTimeseries: ...

    @overload
    def get_parameter_timeseries(
        self, *, fetcher_id: str
    ) -> dict[str, ParameterValueTimeseries]: ...

    @abstractmethod
    def get_parameter_timeseries(
        self, *, name: str | None = None, fetcher_id: str | None = None
    ) -> ParameterTimeseries | dict[str, ParameterValueTimeseries]: ...

    @abstractmethod
    def get_parameters_observation(self, *, fetcher_id: str) -> ParametersObservation: ...

    @abstractmethod
    def get_permitted_denominations(self) -> list[str]: ...

    @abstractmethod
    def get_posting_instructions(
        self, *, fetcher_id: str
    ) -> list[
        AuthorisationAdjustment
        | CustomInstruction
        | InboundAuthorisation
        | InboundHardSettlement
        | OutboundAuthorisation
        | OutboundHardSettlement
        | Release
        | Settlement
        | Transfer
    ]: ...

    @abstractmethod
    def get_sub_accounts(
        self,
        *,
        sub_account_types: list[str] | None = None,
        fetcher_ids: list[str] | None = None,
        invoked: bool | None = None,
    ) -> list[SubAccountVault]: ...


class SuperviseeContractVault(ABC):
    _account_id: str
    _tside: Tside
    _events_timezone: ZoneInfo

    @property
    def tside(self) -> Tside:
        return self._tside

    @property
    def account_id(self) -> str:
        return self._account_id

    @property
    def events_timezone(self) -> ZoneInfo:
        return self._events_timezone

    # SuperviseeContractVault only
    @abstractmethod
    def get_alias(self) -> str: ...

    @abstractmethod
    def get_hook_result(
        self,
    ) -> PostPostingHookResult | PrePostingHookResult | ScheduledEventHookResult: ...

    # Override standard vault methods due to ODF restrictions in supervisors
    @abstractmethod
    def get_balances_timeseries(
        self, *, fetcher_id: str | None = None
    ) -> Mapping[BalanceCoordinate, BalanceTimeseries]: ...

    @abstractmethod
    def get_client_transactions(
        self,
    ) -> dict[str, ClientTransaction]: ...

    @abstractmethod
    def get_parameter_timeseries(self, *, name: str) -> ParameterTimeseries: ...

    @abstractmethod
    def get_posting_instructions(
        self,
    ) -> list[
        AuthorisationAdjustment
        | CustomInstruction
        | InboundAuthorisation
        | InboundHardSettlement
        | OutboundAuthorisation
        | OutboundHardSettlement
        | Release
        | Settlement
        | Transfer
    ]: ...

    # Inherited from SmartContractVault
    @abstractmethod
    def get_account_activation_datetime(self) -> datetime: ...

    @abstractmethod
    def get_account_creation_datetime(self) -> datetime | None: ...

    @abstractmethod
    def get_balances_observation(self, *, fetcher_id: str) -> BalancesObservation: ...

    @abstractmethod
    def get_calendar_events(self, *, calendar_ids: list[str]) -> CalendarEvents: ...

    @abstractmethod
    def get_flag_timeseries(self, *, flag: str) -> FlagTimeseries: ...

    @abstractmethod
    def get_hook_execution_id(self) -> str: ...

    @abstractmethod
    def get_hook_name(self) -> HookName: ...

    @abstractmethod
    def get_last_execution_datetime(self, *, event_type: str) -> datetime | None: ...

    @abstractmethod
    def get_permitted_denominations(self) -> list[str]: ...


class SupervisorContractVault(ABC):
    plan_id: str
    supervisees: dict[str, SuperviseeContractVault]

    @abstractmethod
    def get_calendar_events(self, *, calendar_ids: list[str]) -> CalendarEvents: ...

    @abstractmethod
    def get_hook_execution_id(self) -> str: ...

    @abstractmethod
    def get_hook_name(self) -> HookName: ...

    @abstractmethod
    def get_plan_opening_datetime(self) -> datetime: ...


# flake8: noqa
