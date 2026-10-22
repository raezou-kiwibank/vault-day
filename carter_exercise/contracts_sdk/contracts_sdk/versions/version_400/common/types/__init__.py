from typing import Any

from .....utils.feature_flags import (
    is_fflag_enabled,
    ACCOUNT_OPENING_WITH_SUB_ACCOUNTS,
    CONTRACTS_BOOKING_PERIODS,
    ACCOUNT_ATTRIBUTE_HOOK,
    ADJUSTMENTS,
    CALENDAR_FETCHERS,
    SCHEDULER_EXECUTION_TIMES,
    
    EXPECTED_PID_REJECTIONS,
    ENRICH_POSTING_INSTRUCTIONS,
    GET_HOOK_NAME,
    
    HISTORIC_CONTRACT_RESOLUTION,
    
    
    
    
)



from .balances import (  # noqa: F401
    AddressDetails,
    Balance,
    BalanceCoordinate,
    BalanceDefaultDict,
    BalancesObservation,
    SubAccountAddressDetails,
)

from .calendars import (
    CalendarEvent,
    CalendarEvents,
    CalendarsObservation,
)
from .constants import (  # noqa: F401
    defaultAsset,
    transaction_reference_field_name,
    defaultAddress,
    DEFAULT_ASSET,
    TRANSACTION_REFERENCE_FIELD_NAME,
    DEFAULT_ADDRESS,
)



from .attributes import Attribute
from .attribute_data_types import AttributeDecimalType, AttributeDateTimeType, AttributeStringType

from .enums import (  # noqa: F401
    AdjustmentStrategy,
    DateFailover,
    DateTimePrecision,
    DateTimeView,
    HookName,
    Phase,
    PostingInstructionRejectionReason,
    PostingInstructionType,
    RejectionReason,
    
    SupervisionExecutionMode,
    Timeline,
    Tside,
)



from .event_types import (  # noqa: F401
    EventTypesGroup,
    ScheduledEvent,
    ScheduleExpression,
    ScheduleSkip,
    SmartContractEventType,
    SupervisorContractEventType,
    
    LastScheduledEventDateTimesObservation,
    
)

from .expected_parameters import (  # noqa: F401
    AccountConstraint,
    DateTimeConstraint,
    DecimalConstraint,
    EnumerationConstraint,
    ExpectedParameter,
    StringConstraint,
    
)

from .fetchers import (  # noqa: F401
    BalancesIntervalFetcher,
    BalancesObservationFetcher,
    BalancesDiscreteIntervalFetcher,
    
    CalendarsIntervalFetcher,
    CalendarsObservationFetcher,
    FlagsIntervalFetcher,
    FlagsObservationFetcher,
    IntervalFetcher,
    LastScheduledEventDateTimesObservationFetcher,
    ParametersIntervalFetcher,
    ParametersObservationFetcher,
    PostingsIntervalFetcher,
)
from .decorators import (  # noqa: F401
    populate_fetch_account_data_decorator_spec,
    fetch_account_data,
    
    
    requires,
    populate_requires_decorator_spec,
)

from .flags import FlagsObservation

from .filters import (  # noqa: F401
    BalancesFilter,
    CalendarsFilter,
    FlagsFilter,
    ParametersFilter,
    
    EventTypesFilter,
)

from .hook_arguments import (  # noqa: F401
    ActivationHookArguments,
    
    AttributeHookArguments,
    ConversionAdjustmentHookArguments,
    ConversionHookArguments,
    DeactivationHookArguments,
    DerivedParameterHookArguments,
    PostParameterChangeHookArguments,
    PostPostingHookArguments,
    PreParameterChangeHookArguments,
    PrePostingHookArguments,
    PostParameterChangeAdjustmentHookArguments,
    PostPostingAdjustmentHookArguments,
    ScheduledEventAdjustmentHookArguments,
    ScheduledEventHookArguments,
    
    
    SupervisorActivationHookArguments,
    SupervisorConversionHookArguments,
    SupervisorPostPostingHookArguments,
    SupervisorPrePostingHookArguments,
    SupervisorScheduledEventHookArguments,
)
from .hook_results import (  # noqa: F401
    ActivationHookResult,
    
    AttributeHookResult,
    ConversionAdjustmentHookResult,
    ConversionHookResult,
    DeactivationHookResult,
    DerivedParameterHookResult,
    PreParameterChangeHookResult,
    PostParameterChangeHookResult,
    PostParameterChangeAdjustmentHookResult,
    PostPostingAdjustmentHookResult,
    PostPostingHookResult,
    PrePostingHookResult,
    ScheduledEventAdjustmentHookResult,
    ScheduledEventHookResult,
    SupervisorActivationHookResult,
    SupervisorConversionHookResult,
    SupervisorPostPostingHookResult,
    SupervisorPrePostingHookResult,
    SupervisorScheduledEventHookResult,
    
    
)
from .log import Logger  # noqa: F401
from .account_notification_directive import AccountNotificationDirective  # noqa: F401
from .parameters import (  # noqa: F401
    AccountIdShape,
    DateShape,
    DenominationShape,
    ParameterLevel,
    NumberShape,
    OptionalShape,
    OptionalValue,
    Parameter,
    StringShape,
    UnionItem,
    UnionItemValue,
    UnionShape,
    ParameterUpdatePermission,
)

from .parameter_values import (  # noqa: F401
    ParametersObservation,
)

from .plan_notification_directive import PlanNotificationDirective  # noqa: F401
from .posting_instructions_directive import PostingInstructionsDirective  # noqa: F401
from .postings import (  # noqa: F401
    AdjustmentAmount,
    AuthorisationAdjustment,
    
    ClientTransaction,
    ClientTransactionEffects,
    CustomInstruction,
    PostingInstructionEnrichment,
    InboundAuthorisation,
    InboundHardSettlement,
    OutboundAuthorisation,
    OutboundHardSettlement,
    Posting,
    Release,
    Settlement,
    TransactionCode,
    Transfer,
)
from .rejection import Rejection  # noqa: F401
from .schedules import EndOfMonthSchedule, ScheduleFailover  # noqa: F401



from .periods import Period

from .supervision import SmartContractDescriptor, SupervisedHooks  # noqa: F401
from .time_operations import (  # noqa: F401
    DefinedDateTime,
    Next,
    Override,
    Previous,
    RelativeDateTime,
    Shift,
)
from .timeseries import (  # noqa: F401
    
    BalanceDiscreteTimeseries,
    CalendarTimeseries,
    TimeseriesItem,
    BalanceTimeseries,
    FlagTimeseries,
    FlagValueTimeseries,
    ParameterTimeseries,
    ParameterValueTimeseries,
    
)

from .sub_accounts import (
    
    SubAccountType,
)

from .update_account_event_type_directive import UpdateAccountEventTypeDirective  # noqa: F401
from .update_plan_event_type_directive import UpdatePlanEventTypeDirective  # noqa: F401




def common_types_registry() -> dict[str, Any]:
    registry = {
        "AccountConstraint": AccountConstraint,
        "AccountIdShape": AccountIdShape,  # noqa: F405
        "AccountNotificationDirective": AccountNotificationDirective,  # noqa: F405
        "ActivationHookArguments": ActivationHookArguments,
        "ActivationHookResult": ActivationHookResult,
        "AddressDetails": AddressDetails,  # noqa: F405
        "AdjustmentAmount": AdjustmentAmount,
        "AuthorisationAdjustment": AuthorisationAdjustment,
        "Balance": Balance,  # noqa: F405
        "BalanceCoordinate": BalanceCoordinate,  # noqa: F405
        "BalanceDefaultDict": BalanceDefaultDict,  # noqa: F405
        "BalancesDiscreteIntervalFetcher": BalancesDiscreteIntervalFetcher,
        "BalanceDiscreteTimeseries": BalanceDiscreteTimeseries,
        "BalancesFilter": BalancesFilter,  # noqa: F405
        "BalancesIntervalFetcher": BalancesIntervalFetcher,  # noqa: F405
        "BalancesObservation": BalancesObservation,  # noqa: F405
        "BalancesObservationFetcher": BalancesObservationFetcher,  # noqa: F405
        "BalanceTimeseries": BalanceTimeseries,  # noqa: F405
        "CalendarEvent": CalendarEvent,  # noqa: F405
        "CalendarEvents": CalendarEvents,  # noqa: F405
        "ClientTransaction": ClientTransaction,  # noqa: F405
        "ClientTransactionEffects": ClientTransactionEffects,  # noqa: F405
        "ConversionHookArguments": ConversionHookArguments,
        "ConversionHookResult": ConversionHookResult,
        "DateFailover": DateFailover,
        "DateTimeConstraint": DateTimeConstraint,
        "DateTimePrecision": DateTimePrecision,
        "DateTimeView": DateTimeView,
        "DeactivationHookArguments": DeactivationHookArguments,
        "DeactivationHookResult": DeactivationHookResult,
        "CustomInstruction": CustomInstruction,
        "DateShape": DateShape,  # noqa: F405
        "DecimalConstraint": DecimalConstraint,
        "DEFAULT_ADDRESS": defaultAddress,  # noqa: F405
        "DEFAULT_ASSET": defaultAsset,  # noqa: F405
        "DefinedDateTime": DefinedDateTime,
        "DenominationShape": DenominationShape,  # noqa: F405
        "DerivedParameterHookArguments": DerivedParameterHookArguments,
        "DerivedParameterHookResult": DerivedParameterHookResult,
        "EndOfMonthSchedule": EndOfMonthSchedule,  # noqa: F405
        "EnumerationConstraint": EnumerationConstraint,
        "EventTypesGroup": EventTypesGroup,
        "ExpectedParameter": ExpectedParameter,
        "fetch_account_data": populate_fetch_account_data_decorator_spec(),
        "FlagsFilter": FlagsFilter,
        "FlagsIntervalFetcher": FlagsIntervalFetcher,
        "FlagsObservation": FlagsObservation,
        "FlagsObservationFetcher": FlagsObservationFetcher,
        "FlagTimeseries": FlagTimeseries,  # noqa: F405
        "FlagValueTimeseries": FlagValueTimeseries,
        "InboundAuthorisation": InboundAuthorisation,
        "InboundHardSettlement": InboundHardSettlement,
        "Logger": Logger,  # noqa: F405
        "Next": Next,  # noqa: F405
        "NumberShape": NumberShape,  # noqa: F405
        "OptionalShape": OptionalShape,  # noqa: F405
        "OptionalValue": OptionalValue,  # noqa: F405
        "OutboundAuthorisation": OutboundAuthorisation,
        "OutboundHardSettlement": OutboundHardSettlement,
        "Override": Override,  # noqa: F405
        "Parameter": Parameter,  # noqa: F405
        "ParameterLevel": ParameterLevel,
        "ParametersFilter": ParametersFilter,  # noqa: F405
        "ParametersIntervalFetcher": ParametersIntervalFetcher,  # noqa: F405
        "ParametersObservationFetcher": ParametersObservationFetcher,  # noqa: F405
        "ParametersObservation": ParametersObservation,
        "ParameterTimeseries": ParameterTimeseries,  # noqa: F405
        "ParameterValueTimeseries": ParameterValueTimeseries,
        "Phase": Phase,
        "PlanNotificationDirective": PlanNotificationDirective,
        "ParameterUpdatePermission": ParameterUpdatePermission,
        "Period": Period,
        "Posting": Posting,  # noqa: F405
        "PostingInstructionsDirective": PostingInstructionsDirective,  # noqa: F405
        "PostingInstructionType": PostingInstructionType,  # noqa: F405
        "PostingsIntervalFetcher": PostingsIntervalFetcher,  # noqa: F405
        "PostParameterChangeHookArguments": PostParameterChangeHookArguments,
        "PostParameterChangeHookResult": PostParameterChangeHookResult,
        "PostPostingHookArguments": PostPostingHookArguments,
        "PostPostingHookResult": PostPostingHookResult,
        "PrePostingHookResult": PrePostingHookResult,
        "PreParameterChangeHookArguments": PreParameterChangeHookArguments,
        "PreParameterChangeHookResult": PreParameterChangeHookResult,
        "PrePostingHookArguments": PrePostingHookArguments,
        "Previous": Previous,  # noqa: F405
        "Rejection": Rejection,
        "RejectionReason": RejectionReason,
        "RelativeDateTime": RelativeDateTime,  # noqa: F405
        "Release": Release,
        "requires": populate_requires_decorator_spec(),
        "ScheduleExpression": ScheduleExpression,
        "ScheduledEventHookArguments": ScheduledEventHookArguments,
        "ScheduledEventHookResult": ScheduledEventHookResult,
        "ScheduledEvent": ScheduledEvent,
        "ScheduleFailover": ScheduleFailover,
        "ScheduleSkip": ScheduleSkip,
        "Settlement": Settlement,
        "Shift": Shift,  # noqa: F405
        "SmartContractDescriptor": SmartContractDescriptor,  # noqa: F405
        "SmartContractEventType": SmartContractEventType,
        "StringConstraint": StringConstraint,
        "StringShape": StringShape,  # noqa: F405
        "SupervisedHooks": SupervisedHooks,
        "SupervisionExecutionMode": SupervisionExecutionMode,
        "SupervisorActivationHookArguments": SupervisorActivationHookArguments,
        "SupervisorActivationHookResult": SupervisorActivationHookResult,
        "SupervisorContractEventType": SupervisorContractEventType,
        "SupervisorConversionHookArguments": SupervisorConversionHookArguments,
        "SupervisorConversionHookResult": SupervisorConversionHookResult,
        "SupervisorPostPostingHookArguments": SupervisorPostPostingHookArguments,
        "SupervisorPostPostingHookResult": SupervisorPostPostingHookResult,
        "SupervisorPrePostingHookArguments": SupervisorPrePostingHookArguments,
        "SupervisorPrePostingHookResult": SupervisorPrePostingHookResult,
        "SupervisorScheduledEventHookArguments": SupervisorScheduledEventHookArguments,
        "SupervisorScheduledEventHookResult": SupervisorScheduledEventHookResult,
        "Timeline": Timeline,
        "TimeseriesItem": TimeseriesItem,  # noqa: F405
        "TransactionCode": TransactionCode,  # noqa: F405
        "TRANSACTION_REFERENCE_FIELD_NAME": transaction_reference_field_name,  # noqa: F405
        "Transfer": Transfer,
        "Tside": Tside,
        "UnionItem": UnionItem,  # noqa: F405
        "UnionItemValue": UnionItemValue,  # noqa: F405
        "UnionShape": UnionShape,  # noqa: F405
        "UpdateAccountEventTypeDirective": UpdateAccountEventTypeDirective,
        "UpdatePlanEventTypeDirective": UpdatePlanEventTypeDirective,
    }
    if is_fflag_enabled(CONTRACTS_BOOKING_PERIODS):
        registry["BookingPeriod"] = BookingPeriod
    if is_fflag_enabled(ACCOUNT_ATTRIBUTE_HOOK):
        registry["Attribute"] = Attribute
        registry["AttributeHookArguments"] = AttributeHookArguments
        registry["AttributeHookResult"] = AttributeHookResult
        registry["AttributeDecimalType"] = AttributeDecimalType
        registry["AttributeDateTimeType"] = AttributeDateTimeType
        registry["AttributeStringType"] = AttributeStringType

    

    if is_fflag_enabled(ADJUSTMENTS):
        registry["AdjustmentStrategy"] = AdjustmentStrategy
        registry[
            "PostParameterChangeAdjustmentHookArguments"
        ] = PostParameterChangeAdjustmentHookArguments
        registry[
            "PostParameterChangeAdjustmentHookResult"
        ] = PostParameterChangeAdjustmentHookResult
        registry["PostPostingAdjustmentHookArguments"] = PostPostingAdjustmentHookArguments
        registry["PostPostingAdjustmentHookResult"] = PostPostingAdjustmentHookResult
        registry["ScheduledEventAdjustmentHookArguments"] = ScheduledEventAdjustmentHookArguments
        registry["ScheduledEventAdjustmentHookResult"] = ScheduledEventAdjustmentHookResult

    

    if is_fflag_enabled(CALENDAR_FETCHERS):
        registry["CalendarsFilter"] = CalendarsFilter
        registry["CalendarsObservation"] = CalendarsObservation
        registry["CalendarsIntervalFetcher"] = CalendarsIntervalFetcher
        registry["CalendarsObservationFetcher"] = CalendarsObservationFetcher
        registry["CalendarTimeseries"] = CalendarTimeseries

    if is_fflag_enabled(SCHEDULER_EXECUTION_TIMES):
        registry["EventTypesFilter"] = EventTypesFilter
        registry["LastScheduledEventDateTimesObservation"] = LastScheduledEventDateTimesObservation
        registry[
            "LastScheduledEventDateTimesObservationFetcher"
        ] = LastScheduledEventDateTimesObservationFetcher

    if is_fflag_enabled(EXPECTED_PID_REJECTIONS):
        registry["PostingInstructionRejectionReason"] = PostingInstructionRejectionReason

    if is_fflag_enabled(ENRICH_POSTING_INSTRUCTIONS):
        registry["PostingInstructionEnrichment"] = PostingInstructionEnrichment

    if is_fflag_enabled(GET_HOOK_NAME):
        registry["HookName"] = HookName

    

    if is_fflag_enabled(ACCOUNT_OPENING_WITH_SUB_ACCOUNTS):
        registry["SubAccountAddressDetails"] = SubAccountAddressDetails
        registry["SubAccountType"] = SubAccountType

    if is_fflag_enabled(HISTORIC_CONTRACT_RESOLUTION):
        registry["ConversionAdjustmentHookArguments"] = ConversionAdjustmentHookArguments
        registry["ConversionAdjustmentHookResult"] = ConversionAdjustmentHookResult

    

    

    

    

    return registry
