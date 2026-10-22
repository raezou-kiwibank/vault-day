# Copyright @ 2022 Thought Machine Group Limited. All rights reserved.
# standard libs
import logging
import os
from collections import defaultdict
from datetime import datetime
from decimal import Decimal
from typing import overload
from unittest import TestCase
from unittest.mock import Mock
from zoneinfo import ZoneInfo

# contracts api
# It is very important to use contracts_api here and not any of the extension
# types. This is because the types here will be passed into the contract and must therefore be
# exactly as per the API (see documentation/testing/unit.md for more details). 
# Many of these imports exist for backwards compatibility. 
# Do not remove these even if they're not directly used.
from contracts_api import (  # noqa: F401
    DEFAULT_ADDRESS,
    DEFAULT_ASSET,
    AdjustmentAmount,
    AuthorisationAdjustment,
    Balance,
    BalanceCoordinate,
    BalanceDiscreteTimeseries,
    BalancesObservation,
    BalanceTimeseries,
    CalendarEvent,
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
    OptionalValue,
    OutboundAuthorisation,
    OutboundHardSettlement,
    ParametersObservation,
    ParameterTimeseries,
    ParameterValueTimeseries,
    Phase,
    Posting,
    PostPostingHookResult,
    PrePostingHookResult,
    Release,
    ScheduledEventHookResult,
    Settlement,
    TransactionCode,
    Transfer,
    Tside,
    UnionItemValue,
)

# inception sdk
from inception_sdk.test_framework.contracts.unit.contract_test_helpers import (
    balance_helpers,
    mock_vault_methods,
    posting_instructions,
    sub_account_helpers,
)
from inception_sdk.vault.contracts.extensions.contracts_api_extensions.vault_types import (
    SmartContractVault,
)

# These are imported to provide backwards compatibility to anything that imports from common. Do
# not remove these.
from inception_sdk.test_framework.contracts.unit.contract_test_helpers.constants import (  # noqa
    ACCOUNT_ID,
    CLIENT_TRANSACTION_ID,
    DEFAULT_DATETIME,
    DEFAULT_DENOMINATION,
    DEFAULT_HOOK_EXECUTION_ID,
    DEFAULT_INTERNAL_ACCOUNT,
    DEFAULT_PHASE,
    POSTING_CLIENT_ID,
    PostingInstruction,
    PostingInstructionTypeList,
)

ParameterValueType = Decimal | str | datetime | OptionalValue | UnionItemValue | int

log = logging.getLogger(__name__)
logging.basicConfig(
    level=os.environ.get("LOGLEVEL", "INFO"),
    format="%(asctime)s.%(msecs)03d - %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


def construct_parameter_timeseries(
    parameter_name_to_value_map: dict[str, ParameterValueType], default_datetime: datetime
) -> dict[str, ParameterTimeseries]:
    """
    returns a dict where key is param name and value is a ParameterTimeseries object to
    be used as the parameter_ts for the mock vault object
    """
    return {
        param_name: ParameterTimeseries([(default_datetime, param_value)])
        for param_name, param_value in parameter_name_to_value_map.items()
    }


def construct_flag_timeseries(
    flag_name_to_bool_map: dict[str, bool], default_datetime: datetime
) -> dict[str, FlagTimeseries]:
    return {
        flag_name: FlagTimeseries([(default_datetime, flag_bool)])
        for flag_name, flag_bool in flag_name_to_bool_map.items()
    }


class ContractTest(TestCase):
    tside: Tside
    default_denomination: str = DEFAULT_DENOMINATION
    events_timezone: ZoneInfo = ZoneInfo("UTC")

    @classmethod
    def setUpClass(cls) -> None:
        try:
            cls.tside
        except AttributeError:
            raise AttributeError(
                "You must supply the Tside of the product at the start of the test class"
            )

    def create_mock(
        self,
        account_id: str = ACCOUNT_ID,
        activation_datetime: datetime = DEFAULT_DATETIME,
        balances_observation_fetchers_mapping: dict[str, BalancesObservation] | None = None,
        balances_interval_fetchers_mapping: (
            dict[str, defaultdict[BalanceCoordinate, BalanceTimeseries]] | None
        ) = None,
        balances_discrete_interval_fetchers_mapping: (
            dict[str, defaultdict[BalanceCoordinate, BalanceDiscreteTimeseries]] | None
        ) = None,
        calendar_events: list[CalendarEvent] | None = None,
        calendars_observation_fetchers_mapping: dict[str, CalendarsObservation] | None = None,
        calendars_interval_fetchers_mapping: dict[str, CalendarTimeseries] | None = None,
        client_transactions_mapping: dict[str, dict[str, ClientTransaction]] | None = None,
        creation_date: datetime = DEFAULT_DATETIME,
        existing_mock: Mock | None = None,
        flags_ts: dict[str, FlagTimeseries] | None = None,
        flags_observation_fetchers_mapping: dict[str, FlagsObservation] | None = None,
        flags_interval_fetchers_mapping: (
            dict[str, FlagValueTimeseries] | defaultdict[str, FlagValueTimeseries] | None
        ) = None,
        hook_name: HookName | None = None,
        last_execution_datetimes: dict[str, datetime | None] | None = None,
        last_scheduled_event_datetimes_observation_mapping: (
            dict[str, LastScheduledEventDateTimesObservation] | None
        ) = None,
        parameter_ts: dict[str, ParameterTimeseries] | None = None,
        parameters_observation_fetchers_mapping: dict[str, ParametersObservation] | None = None,
        parameters_interval_fetchers_mapping: dict[str, ParameterValueTimeseries] | None = None,
        postings_interval_mapping: dict[str, PostingInstructionTypeList] | None = None,
        requires_fetched_balances: defaultdict[BalanceCoordinate, BalanceTimeseries] | None = None,
        requires_fetched_client_transactions: dict[str, ClientTransaction] | None = None,
        requires_fetched_postings: PostingInstructionTypeList | None = None,
        supervisee_alias: str | None = None,
        supervisee_hook_result: (
            PostPostingHookResult | PrePostingHookResult | ScheduledEventHookResult | None
        ) = None,
        is_supervisee_vault: bool = False,
    ) -> Mock | SmartContractVault:
        """
        Create mock Vault object for the test

        account_id, activation_datetime, and creation_date will be given default values if
        not provided. All other arguments are optional

        :param account_id: Account ID
        :param activation_datetime: Account activation datetime. Used to mock
        `vault.get_account_activation_datetime()`
        :param balances_observation_fetchers_mapping: mapping of fetcher_id to balance observation.
        Used to mock `vault.get_balances_observation()`
        :param balances_interval_fetchers_mapping: mapping of fetcher_id to balance timeseries.
        Used to mock `vault.get_balances_timeseries()`
        :param balances_discrete_interval_fetchers_mapping: mapping of fetcher_id to balance
        discrete timeseries. Used to mock `vault.get_balances_discrete_timeseries()`
        :param calendar_events: list of calendar events. Used to mock `vault.get_calendar_events()`
        :param calendars_observation_fetchers_mapping: mapping of fetcher_id to
        calendars observation. Used to mock `vault.get_calendars_observation()`
        :param calendars_interval_fetchers_mapping: mapping of fetcher_id to calendars timeseries.
        Used to mock `vault.get_calendars_timeseries()`
        :param client_transactions_mapping: mapping of postings fetcher id to Client transactions
        including proposed. Used to mock `vault.get_client_transactions`.
        :param creation_date: Account creation date. Used to mock
        `vault.get_account_creation_datetime()`
        :param existing_mock: An mock object to re-use instead of creating a new mock
        :param flags_ts: dict where key is flag name and value is a FlagTimeseries object
        :param flags_observation_fetchers_mapping: mapping of fetcher_id to flags observation.
        Used to mock `vault.get_flags_observation()`
        :param flags_interval_fetchers_mapping: mapping of fetcher_id to flag value timeseries.
        The dictionary has type defaultdict if the FlagsIntervalFetcher did not specify a
        FlagsFilter. Otherwise, the dictionary has type dict. Used to mock
        `vault.get_flags_timeseries(fetcher_id=...)`
        :param hook_name: the Enum of the hook being run during this test.
        Used to mock `vault.get_hook_name()`
        :param last_execution_datetimes: dict of event_type to last execution datetime
        :param last_scheduled_event_datetimes_observation_mapping: mapping of fetcher_id to
        last scheduled event datetimes observation.
        Used to mock `vault.get_last_scheduled_event_datetimes_observation()`
        :param parameter_ts: dict where key is param name and value is a ParameterTimeseries object.
        Used to mock `vault.get_parameter_timeseries(name=...)`
        :param parameters_observation_fetchers_mapping: mapping of fetcher_id to parameters
        observation. Used to mock `vault.get_parameters_observation()`
        :param parameters_interval_fetchers_mapping: mapping of fetcher_id to parameter value
        timeseries. Used to mock `vault.get_parameter_timeseries(fetcher_id=...)`
        :param postings_interval_mapping: mapping of postings fetcher_id to posting instructions
        Used to mock `vault.get_posting_instructions()`

        # supervisee specific arguments - these following arguments should only used on supervisee
        vault objects
        :param requires_fetched_balances: balances fetched from the requires decorator, this should
        only be used in the post_posting_hook or scheduled_event_hook where optimised data fetchers
        for supervisors are not yet supported
        :param requires_fetched_client_transactions: client transactions fetched from the requires
        decorator, this should only be used in the post_posting_hook or scheduled_event_hook where
        optimised data fetchers for supervisors are not yet supported
        :param requires_fetched_postings: postings fetched from the requires decorator, this should
        only be used in the post_posting_hook or scheduled_event_hook where optimised data fetchers
        for supervisors are not yet supported
        :param supervisee_alias: alias of the supervisee vault object
        :param supervisee_hook_result: returned hook result of the supervised hook
        :param is_supervisee_vault: boolean used to determine whether this is a supervisee vault
        object or not

        :raises KeyError: when the mocked methods are used to access data for fetcher_id values
        that weren't provided on initialisation (e.g. contract is using a different fetcher_id to
        the provided mappings).
        :raises ValueError: when illegal/missing values are passed in to the mocked methods (e.g.
        calling get_parameter_timeseries() without a named argument)

        :return: a mock vault object
        """
        parameter_ts = parameter_ts or {}
        flags_ts = flags_ts or {}
        calendar_events = calendar_events or []
        # replace CLU dependency syntax from flag definitions. This allows for consistency between
        # the contract and the tests since unit tests run the contract directly as a python module,
        # these aren't removed in any class setup or rendering
        flags_ts = {
            flag.replace("&{", "").replace("}", ""): datetime_bool
            for flag, datetime_bool in flags_ts.items()
        }

        calendar_events = [
            CalendarEvent(
                id=calendar_event.id,
                calendar_id=calendar_event.calendar_id.replace("&{", "").replace("}", ""),
                start_datetime=calendar_event.start_datetime,
                end_datetime=calendar_event.end_datetime,
            )
            for calendar_event in calendar_events
        ]

        last_execution_datetimes = last_execution_datetimes or {}
        calendars_observation_fetchers_mapping = calendars_observation_fetchers_mapping or {}
        calendars_interval_fetchers_mapping = calendars_interval_fetchers_mapping or {}
        flags_observation_fetchers_mapping = flags_observation_fetchers_mapping or {}
        flags_interval_fetchers_mapping = flags_interval_fetchers_mapping or {}
        last_scheduled_event_datetimes_observation_mapping = (
            last_scheduled_event_datetimes_observation_mapping or {}
        )
        parameters_observation_fetchers_mapping = parameters_observation_fetchers_mapping or {}
        parameters_interval_fetchers_mapping = parameters_interval_fetchers_mapping or {}

        def raise_if_called_from_supervisee_vault(method_name: str) -> ValueError | None:
            if is_supervisee_vault:
                raise ValueError(
                    f"{method_name} method cannot be called on a supervisee Vault "
                    f"object with {account_id=}. If the Vault object is not a supervisee, "
                    "make sure create_mock is not called with `is_supervisee=True`."
                )
            return None

        def mock_get_calendar_events(calendar_ids: list[str]) -> CalendarEvents:
            # replace CLU dependency syntax from flag definitions. This allows for consistency
            # between the contract and the tests since unit tests run the contract directly as
            # a python module, these aren't removed in any class setup or rendering
            calendar_ids = [
                calendar_id.replace("&{", "").replace("}", "") for calendar_id in calendar_ids
            ]
            events = [event for event in calendar_events if event.calendar_id in calendar_ids]
            return CalendarEvents(calendar_events=events)

        def mock_get_calendars_observation(fetcher_id: str) -> CalendarsObservation:
            raise_if_called_from_supervisee_vault("get_calendars_observation")

            if fetcher_id in calendars_observation_fetchers_mapping:
                return calendars_observation_fetchers_mapping[fetcher_id]
            raise KeyError(f"Missing calendars observation in test setup for {fetcher_id=}")

        def mock_get_calendars_timeseries(fetcher_id: str) -> CalendarTimeseries:
            raise_if_called_from_supervisee_vault("get_calendars_timeseries")

            if fetcher_id in calendars_interval_fetchers_mapping:
                return calendars_interval_fetchers_mapping[fetcher_id]
            raise KeyError(f"Missing calendars interval in test setup for {fetcher_id=}")

        def mock_get_flag_timeseries(flag: str) -> FlagTimeseries:
            # replace CLU dependency syntax from flag definitions. This allows for consistency
            # between the contract and the tests since unit tests run the contract directly as
            # a python module, these aren't removed in any class setup or rendering
            flag = flag.replace("&{", "").replace("}", "")

            if flag in flags_ts:
                # flag settings have been supplied as a timeseries
                flag_timeseries = flags_ts[flag]
            else:
                # No setting supplied for flag, so it is False as per Vault behaviour
                flag_timeseries = FlagTimeseries([(creation_date, False)])
            return flag_timeseries

        def mock_get_flags_observation(fetcher_id: str) -> FlagsObservation:
            raise_if_called_from_supervisee_vault("get_flags_observation")

            if fetcher_id in flags_observation_fetchers_mapping:
                return flags_observation_fetchers_mapping[fetcher_id]
            raise KeyError(f"Missing Flag observation in test setup for {fetcher_id=}")

        def mock_get_flags_timeseries(fetcher_id: str) -> FlagValueTimeseries:
            raise_if_called_from_supervisee_vault("get_flags_timeseries")

            if fetcher_id in flags_interval_fetchers_mapping:
                return flags_interval_fetchers_mapping[fetcher_id]
            raise KeyError(f"Missing Flag interval in test setup for {fetcher_id=}")

        def mock_get_hook_name():
            if hook_name:
                return hook_name
            raise ValueError("No hook name provided")

        def mock_get_last_execution_datetime(event_type: str) -> datetime | None:
            if event_type in last_execution_datetimes:
                return last_execution_datetimes[event_type]
            raise ValueError("Missing event_type in last_execution_datetimes mapping.")

        def mock_get_last_scheduled_event_datetimes_observation(
            fetcher_id: str,
        ) -> LastScheduledEventDateTimesObservation:
            raise_if_called_from_supervisee_vault("get_last_scheduled_event_datetimes_observation")

            if fetcher_id in last_scheduled_event_datetimes_observation_mapping:
                return last_scheduled_event_datetimes_observation_mapping[fetcher_id]
            raise KeyError(
                "Missing last scheduled event datetimes observation"
                f" in test setup for {fetcher_id=}"
            )

        @overload
        def mock_get_parameter_timeseries(*, name: str) -> ParameterTimeseries: ...

        @overload
        def mock_get_parameter_timeseries(*, fetcher_id: str) -> ParameterValueTimeseries: ...

        def mock_get_parameter_timeseries(
            *, name: str | None = None, fetcher_id: str | None = None
        ) -> ParameterTimeseries | ParameterValueTimeseries:
            if is_supervisee_vault:
                if fetcher_id is not None:
                    raise ValueError(
                        "Supervisee vault object cannot provide fetcher_id to "
                        "get_parameter_timeseries()."
                    )

            if name and fetcher_id:
                raise ValueError(
                    "get_parameter_timeseries cannot be called "
                    "with both `name` or `fetcher_id` kwargs."
                )

            if name:
                if name in parameter_ts:
                    return parameter_ts[name]
                raise KeyError(f"Missing parameter timeseries in test setup for parameter {name=}")
            elif fetcher_id:
                if fetcher_id in parameters_interval_fetchers_mapping:
                    return parameters_interval_fetchers_mapping[fetcher_id]
                raise KeyError(f"Missing parameter interval in test setup for {fetcher_id=}")
            else:
                raise ValueError(
                    "get_parameter_timeseries called without `name` or `fetcher_id` kwargs"
                )

        def mock_get_parameters_observation(fetcher_id: str) -> ParametersObservation:
            raise_if_called_from_supervisee_vault("get_parameters_observation")

            if fetcher_id in parameters_observation_fetchers_mapping:
                return parameters_observation_fetchers_mapping[fetcher_id]
            raise KeyError(f"Missing parameter observation in test setup for {fetcher_id=}")

        # supervisee specific methods

        def raise_if_unsupported_non_supervisee_method(method_name: str) -> ValueError | None:
            if not is_supervisee_vault:
                raise ValueError(
                    f"{method_name} method cannot be called on a non-supervisee Vault object, "
                    "make sure the create_mock argument is set correctly"
                )
            return None

        def mock_get_alias() -> str:
            raise_if_unsupported_non_supervisee_method("get_alias")
            if supervisee_alias is not None:
                return supervisee_alias
            else:
                raise ValueError("No supervisee alias provided")

        def mock_get_hook_result() -> (
            PrePostingHookResult | PostPostingHookResult | ScheduledEventHookResult
        ):
            raise_if_unsupported_non_supervisee_method("get_hook_result")
            if supervisee_hook_result:
                return supervisee_hook_result
            else:
                raise ValueError(
                    "get_hook_result must return one of PrePostingHookResult, "
                    "PostPostingHookResult, ScheduledEventHookResult"
                )

        # Identify mocks more easily, especially in supervisor scenarios
        mock_vault = existing_mock or Mock(name=account_id)

        # attributes
        mock_vault.account_id = account_id
        mock_vault.tside = self.tside
        mock_vault.events_timezone = self.events_timezone
        mock_vault.sub_accounts = sub_account_helpers.SubAccountsDict()

        # methods
        mock_vault.get_account_activation_datetime.return_value = activation_datetime
        mock_vault.get_account_creation_datetime.return_value = creation_date
        mock_vault.get_calendar_events.side_effect = mock_get_calendar_events
        mock_vault.get_calendars_observation.side_effect = mock_get_calendars_observation
        mock_vault.get_calendars_timeseries.side_effect = mock_get_calendars_timeseries
        mock_vault.get_flag_timeseries.side_effect = mock_get_flag_timeseries
        mock_vault.get_flags_observation.side_effect = mock_get_flags_observation
        mock_vault.get_flags_timeseries.side_effect = mock_get_flags_timeseries
        mock_vault.get_hook_execution_id.return_value = DEFAULT_HOOK_EXECUTION_ID
        mock_vault.get_hook_name.side_effect = mock_get_hook_name
        mock_vault.get_last_execution_datetime.side_effect = mock_get_last_execution_datetime
        mock_vault.get_last_scheduled_event_datetimes_observation.side_effect = (
            mock_get_last_scheduled_event_datetimes_observation
        )
        mock_vault.get_parameter_timeseries.side_effect = mock_get_parameter_timeseries
        mock_vault.get_parameters_observation.side_effect = mock_get_parameters_observation
        mock_vault.get_permitted_denominations.return_value = [self.default_denomination]

        sub_account_helpers.apply_get_sub_accounts(mock_parent_account=mock_vault)

        # methods common to Account and Sub-Account Vault objects
        mock_vault_methods.apply_mock_methods(
            mock_vault=mock_vault,
            balances_observation_fetchers_mapping=balances_observation_fetchers_mapping,
            balances_interval_fetchers_mapping=balances_interval_fetchers_mapping,
            balances_discrete_interval_fetchers_mapping=balances_discrete_interval_fetchers_mapping,
            client_transactions_mapping=client_transactions_mapping,
            postings_interval_mapping=postings_interval_mapping,
        )

        if is_supervisee_vault:

            def mock_get_balances_discrete_timeseries_supervisee(fetcher_id: str):
                raise ValueError(
                    f"get_balances_discrete_timeseries method cannot be called on a supervisee "
                    f"Vault object with {account_id=}. If the Vault object is not a supervisee, "
                    "make sure create_mock is not called with `is_supervisee=True`."
                )

            mock_vault.get_balances_discrete_timeseries.side_effect = (
                mock_get_balances_discrete_timeseries_supervisee
            )

            if requires_fetched_balances is not None:
                mock_vault.get_balances_timeseries.side_effect = None
                mock_vault.get_balances_timeseries.return_value = requires_fetched_balances

            def mock_get_client_transaction_supervisee(fetcher_id: str | None = None):
                if fetcher_id:
                    raise ValueError(
                        "Supervisee vault object cannot provide fetcher_id to "
                        "get_client_transactions()"
                    )
                if requires_fetched_client_transactions is None:
                    raise ValueError("Missing requires fetched client transactions in test setup")
                return requires_fetched_client_transactions

            mock_vault.get_client_transactions.side_effect = mock_get_client_transaction_supervisee

            if requires_fetched_postings is not None:
                mock_vault.get_posting_instructions.side_effect = None
                mock_vault.get_posting_instructions.return_value = requires_fetched_postings

        # supervisee specific methods
        mock_vault.get_alias.side_effect = mock_get_alias
        mock_vault.get_hook_result.side_effect = mock_get_hook_result

        return mock_vault

    # Posting Instruction types
    inbound_auth = posting_instructions.inbound_auth
    outbound_auth = posting_instructions.outbound_auth
    inbound_auth_adjust = posting_instructions.inbound_auth_adjust
    outbound_auth_adjust = posting_instructions.outbound_auth_adjust
    settle_inbound_auth = posting_instructions.settle_inbound_auth
    settle_outbound_auth = posting_instructions.settle_outbound_auth
    release_inbound_auth = posting_instructions.release_inbound_auth
    release_outbound_auth = posting_instructions.release_outbound_auth
    inbound_hard_settlement = posting_instructions.inbound_hard_settlement
    outbound_hard_settlement = posting_instructions.outbound_hard_settlement
    inbound_transfer = posting_instructions.inbound_transfer
    outbound_transfer = posting_instructions.outbound_transfer
    custom_instruction = posting_instructions.custom_instruction

    # Balance helpers
    balance = balance_helpers.balance
    balance_coordinate = balance_helpers.balance_coordinate
    construct_balance_timeseries = balance_helpers.construct_balance_timeseries
    construct_balance_discrete_timeseries = balance_helpers.construct_balance_discrete_timeseries

    # Sub-Accounts helpers
    create_sub_account_mock = sub_account_helpers.create_sub_account_mock


class FeatureTest(ContractTest):
    # Override tside since features should not need them, but if a specific test needs tside
    # then this can be set at the class level
    tside = None  # type: ignore
