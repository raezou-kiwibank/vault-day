# standard libs
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

class SubAccountVault:
    sub_account_id: str
    sub_account_type: str

    def get_balances_discrete_timeseries(
        self, *, fetcher_id: str
    ) -> Mapping[BalanceCoordinate, BalanceDiscreteTimeseries]: ...

    def get_balances_observation(self, *, fetcher_id: str) -> BalancesObservation: ...

    def get_balances_timeseries(
        self, *, fetcher_id: str
    ) -> Mapping[BalanceCoordinate, BalanceTimeseries]: ...

    def get_client_transactions(self, *, fetcher_id: str) -> dict[str, ClientTransaction]: ...

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

    def get_sub_account_activation_datetime(self) -> datetime: ...


class SmartContractVault:
    account_id: str
    tside: Tside
    events_timezone: ZoneInfo
    sub_accounts: defaultdict[str, SubAccountVault]

    def get_account_activation_datetime(self) -> datetime: ...
    def get_account_creation_datetime(self) -> datetime: ...
    def get_balances_discrete_timeseries(
        self, *, fetcher_id: str
    ) -> Mapping[BalanceCoordinate, BalanceDiscreteTimeseries]: ...
    def get_balances_observation(self, *, fetcher_id: str) -> BalancesObservation: ...
    def get_balances_timeseries(
        self, *, fetcher_id: str
    ) -> Mapping[BalanceCoordinate, BalanceTimeseries]: ...
    def get_calendar_events(self, *, calendar_ids: list[str]) -> CalendarEvents: ...
    def get_calendars_observation(self, *, fetcher_id: str) -> CalendarsObservation: ...
    def get_calendars_timeseries(self, *, fetcher_id: str) -> dict[str, CalendarTimeseries]: ...
    def get_client_transactions(self, *, fetcher_id: str) -> dict[str, ClientTransaction]: ...
    def get_flag_timeseries(self, *, flag: str) -> FlagTimeseries: ...
    def get_flags_observation(self, *, fetcher_id: str) -> FlagsObservation: ...
    def get_flags_timeseries(self, *, fetcher_id: str) -> dict[str, FlagValueTimeseries]: ...
    def get_hook_execution_id(self) -> str: ...
    def get_hook_name(self) -> HookName: ...
    def get_last_execution_datetime(self, *, event_type: str) -> datetime | None: ...
    def get_last_scheduled_event_datetimes_observation(
        self, *, fetcher_id: str
    ) -> LastScheduledEventDateTimesObservation: ...
    @overload
    def get_parameter_timeseries(self, *, name: str) -> ParameterTimeseries: ...
    @overload
    def get_parameter_timeseries(
        self, *, fetcher_id: str
    ) -> dict[str, ParameterValueTimeseries]: ...
    def get_parameters_observation(self, *, fetcher_id: str) -> ParametersObservation: ...
    def get_permitted_denominations(self) -> list[str]: ...
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
    def get_sub_accounts(
        self,
        *,
        sub_account_types: list[str] | None = None,
        fetcher_ids: list[str] | None = None,
        invoked: bool | None = None,
    ) -> list[SubAccountVault]: ...

class SuperviseeContractVault:
    account_id: str
    tside: Tside
    events_timezone: ZoneInfo

    # SuperviseeContractVault only
    def get_alias(self) -> str: ...
    def get_hook_result(
        self,
    ) -> PostPostingHookResult | PrePostingHookResult | ScheduledEventHookResult: ...

    # Override standard vault methods due to ODF restrictions in supervisors
    def get_balances_timeseries(
        self, *, fetcher_id: str | None = None
    ) -> Mapping[BalanceCoordinate, BalanceTimeseries]: ...
    def get_client_transactions(
        self,
    ) -> dict[str, ClientTransaction]: ...
    def get_parameter_timeseries(self, *, name: str) -> ParameterTimeseries: ...
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
    def get_account_activation_datetime(self) -> datetime: ...
    def get_account_creation_datetime(self) -> datetime: ...
    def get_balances_observation(self, *, fetcher_id: str) -> BalancesObservation: ...
    def get_calendar_events(self, *, calendar_ids: list[str]) -> CalendarEvents: ...
    def get_flag_timeseries(self, *, flag: str) -> FlagTimeseries: ...
    def get_hook_execution_id(self) -> str: ...
    def get_hook_name(self) -> HookName: ...
    def get_last_execution_datetime(self, *, event_type: str) -> datetime | None: ...
    def get_permitted_denominations(self) -> list[str]: ...

class SupervisorContractVault:
    plan_id: str
    supervisees: dict[str, SuperviseeContractVault]

    def get_calendar_events(self, *, calendar_ids: list[str]) -> CalendarEvents: ...
    def get_hook_execution_id(self) -> str: ...
    def get_hook_name(self) -> HookName: ...
    def get_plan_opening_datetime(self) -> datetime: ...

# flake8: noqa
