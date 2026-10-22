# standard libs
from datetime import datetime
from decimal import Decimal
from unittest import TestCase
from unittest.mock import sentinel
from zoneinfo import ZoneInfo

# contracts api
from contracts_api import (
    DEFAULT_ADDRESS,
    DEFAULT_ASSET,
    Balance,
    BalanceDiscreteTimeseries,
    BalanceTimeseries,
    CalendarEvent,
    CalendarEvents,
    HookName,
    InboundAuthorisation,
    InboundHardSettlement,
    OutboundAuthorisation,
    OutboundHardSettlement,
    Phase,
    Release,
    ScheduledEventHookResult,
    Settlement,
    Transfer,
    Tside,
)

# inception sdk
from inception_sdk.test_framework.contracts.unit.common import ContractTest


class TestCreateMockBase(TestCase):
    contract_test: ContractTest

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.contract_test = ContractTest()
        cls.contract_test.tside = Tside.ASSET


class TestGetLastExecutionDatetime(TestCreateMockBase):
    def test_get_last_execution_datetime_raises(self):
        mock_vault = self.contract_test.create_mock(last_execution_datetimes={"some_event": None})
        with self.assertRaises(ValueError) as err:
            mock_vault.get_last_execution_datetime(event_type="another_event")
        self.assertEqual(
            err.exception.args[0],
            "Missing event_type in last_execution_datetimes mapping.",
        )

    def test_get_last_execution_datetime_returns_datetime(self):
        mock_vault = self.contract_test.create_mock(
            last_execution_datetimes={
                "some_event": None,
                "another_event": datetime(2023, 1, 1, 1, 1),
            }
        )
        result = mock_vault.get_last_execution_datetime(event_type="another_event")
        self.assertEqual(result, datetime(2023, 1, 1, 1, 1))

    def test_get_last_execution_datetime_returns_None(self):
        mock_vault = self.contract_test.create_mock(
            last_execution_datetimes={
                "some_event": None,
                "another_event": datetime(2023, 1, 1, 1, 1),
            }
        )
        result = mock_vault.get_last_execution_datetime(event_type="some_event")
        self.assertIsNone(result)


class TestGetLastScheduledEventDatetimesObservation(TestCreateMockBase):
    def test_mock_get_last_scheduled_event_datetimes_observation(self):
        mock_vault = self.contract_test.create_mock(
            last_scheduled_event_datetimes_observation_mapping={"fetcher_id": sentinel.observation}
        )
        self.assertEqual(
            mock_vault.get_last_scheduled_event_datetimes_observation(fetcher_id="fetcher_id"),
            sentinel.observation,
        )

    def test_mock_get_last_scheduled_event_datetimes_observation_with_undefined_fetcher_id(self):
        mock_vault = self.contract_test.create_mock(
            last_scheduled_event_datetimes_observation_mapping={"fetcher_id": sentinel.observation}
        )
        with self.assertRaises(KeyError) as err:
            mock_vault.get_last_scheduled_event_datetimes_observation(
                fetcher_id="another_fetcher_id"
            )
        self.assertEqual(
            err.exception.args[0],
            "Missing last scheduled event datetimes observation in "
            "test setup for fetcher_id='another_fetcher_id'",
        )

    def test_get_last_scheduled_event_datetimes_observation_raises_without_fetcher_id(self):
        mock_vault = self.contract_test.create_mock(
            last_scheduled_event_datetimes_observation_mapping={
                "some_fetcher_id": sentinel.observation
            },
        )
        with self.assertRaises(TypeError) as err:
            mock_vault.get_last_scheduled_event_datetimes_observation()
        self.assertIn(
            "missing 1 required positional argument: 'fetcher_id'",
            err.exception.args[0],
        )

    def test_mock_get_last_scheduled_event_datetimes_observation_raises_on_supervisee(self):
        mock_vault = self.contract_test.create_mock(
            is_supervisee_vault=True,
            last_scheduled_event_datetimes_observation_mapping={
                "some_fetcher_id": sentinel.observation
            },
        )
        with self.assertRaises(ValueError) as err:
            mock_vault.get_last_scheduled_event_datetimes_observation(fetcher_id="some_fetcher_id")
        self.assertEqual(
            err.exception.args[0],
            "get_last_scheduled_event_datetimes_observation method cannot be called on a "
            "supervisee Vault object with account_id='default_account'. If the Vault object is "
            "not a supervisee, make sure create_mock is not called with `is_supervisee=True`.",
        )


class TestGetAccountActivationDatetime(TestCreateMockBase):
    def test_get_account_activation_datetime_defaulted_datetime(self):
        mock_vault = self.contract_test.create_mock()
        result = mock_vault.get_account_activation_datetime()
        expected = datetime(2019, 1, 1, tzinfo=ZoneInfo("UTC"))
        self.assertEqual(result, expected)

    def test_get_account_activation_datetime_custom_datetime(self):
        mock_vault = self.contract_test.create_mock(
            activation_datetime=datetime(2019, 1, 2, tzinfo=ZoneInfo("UTC"))
        )
        result = mock_vault.get_account_activation_datetime()
        expected = datetime(2019, 1, 2, tzinfo=ZoneInfo("UTC"))
        self.assertEqual(result, expected)


class TestGetAccountCreationDatetime(TestCreateMockBase):
    def test_get_account_creation_datetime_defaulted_datetime(self):
        mock_vault = self.contract_test.create_mock()
        result = mock_vault.get_account_creation_datetime()
        expected = datetime(2019, 1, 1, tzinfo=ZoneInfo("UTC"))
        self.assertEqual(result, expected)

    def test_get_account_creation_datetime_custom_datetime(self):
        mock_vault = self.contract_test.create_mock(
            creation_date=datetime(2019, 1, 2, tzinfo=ZoneInfo("UTC"))
        )
        result = mock_vault.get_account_creation_datetime()
        expected = datetime(2019, 1, 2, tzinfo=ZoneInfo("UTC"))
        self.assertEqual(result, expected)


class TestGetBalances(TestCreateMockBase):

    # get_balances_observation

    def test_get_balances_observation(self):
        mock_vault = self.contract_test.create_mock(
            balances_observation_fetchers_mapping={"some_fetcher_id": sentinel.balances},
        )
        self.assertEqual(
            mock_vault.get_balances_observation(fetcher_id="some_fetcher_id"), sentinel.balances
        )

    def test_get_balances_observation_raises_without_fetcher_id(self):
        mock_vault = self.contract_test.create_mock(
            balances_observation_fetchers_mapping={"some_fetcher_id": sentinel.balances},
        )
        with self.assertRaises(TypeError) as err:
            mock_vault.get_balances_observation()
        self.assertIn(
            "missing 1 required positional argument: 'fetcher_id'",
            err.exception.args[0],
        )

    def test_get_balances_observation_raises_with_incorrect_fetcher_id(self):
        mock_vault = self.contract_test.create_mock(
            balances_observation_fetchers_mapping={"some_fetcher_id": sentinel.balances},
        )
        with self.assertRaises(KeyError) as err:
            mock_vault.get_balances_observation(fetcher_id="another_fetcher_id")
        self.assertEqual(
            err.exception.args[0],
            "Missing balance observation in test setup for fetcher_id='another_fetcher_id'",
        )

    # get_balances_timeseries

    def test_get_balances_timeseries(self):
        mock_vault = self.contract_test.create_mock(
            balances_interval_fetchers_mapping={"some_fetcher_id": sentinel.balances},
        )
        self.assertEqual(
            mock_vault.get_balances_timeseries(fetcher_id="some_fetcher_id"), sentinel.balances
        )

    def test_non_supervisee_mock_raises_fetched_balances_without_fetcher_id(self):
        mock_vault = self.contract_test.create_mock(
            is_supervisee_vault=False,
            postings_interval_mapping={"some_fetcher_id": sentinel.balances},
        )
        with self.assertRaises(ValueError) as err:
            mock_vault.get_balances_timeseries()
        self.assertEqual(
            err.exception.args[0],
            "You must provide a fetcher ID",
        )

    def test_non_supervisee_mock_raises_fetched_balances_with_incorrect_fetcher_id(self):
        mock_vault = self.contract_test.create_mock(
            is_supervisee_vault=False,
            postings_interval_mapping={"some_fetcher_id": sentinel.balances},
        )
        with self.assertRaises(KeyError) as err:
            mock_vault.get_balances_timeseries("another_fetcher_id")
        self.assertEqual(
            err.exception.args[0],
            "Missing balance interval in test setup for fetcher_id='another_fetcher_id'",
        )

    def test_supervisee_mock_returns_requires_fetched_balances(self):
        mock_vault = self.contract_test.create_mock(
            is_supervisee_vault=True, requires_fetched_balances=sentinel.balances
        )

        self.assertEqual(mock_vault.get_balances_timeseries(), sentinel.balances)

    def test_supervisee_mock_returns_mapped_fetched_balances(self):
        mock_vault = self.contract_test.create_mock(
            is_supervisee_vault=True,
            balances_interval_fetchers_mapping={"some_fetcher_id": sentinel.balances},
        )

        self.assertEqual(
            mock_vault.get_balances_timeseries(fetcher_id="some_fetcher_id"), sentinel.balances
        )

    # get_balances_discrete_timeseries

    def test_get_balances_discrete_timeseries(self):
        mock_vault = self.contract_test.create_mock(
            balances_discrete_interval_fetchers_mapping={"some_fetcher_id": sentinel.balances},
        )
        self.assertEqual(
            mock_vault.get_balances_discrete_timeseries(fetcher_id="some_fetcher_id"),
            sentinel.balances,
        )

    def test_get_balances_discrete_timeseries_raises_without_fetcher_id(self):
        mock_vault = self.contract_test.create_mock(
            balances_interval_fetchers_mapping={"some_fetcher_id": sentinel.balances},
        )
        with self.assertRaises(TypeError) as err:
            mock_vault.get_balances_discrete_timeseries()
        self.assertIn(
            "missing 1 required positional argument: 'fetcher_id'",
            err.exception.args[0],
        )

    def test_get_balances_discrete_timeseries_raises_with_incorrect_fetcher_id(self):
        mock_vault = self.contract_test.create_mock(
            balances_discrete_interval_fetchers_mapping={"some_fetcher_id": sentinel.balances},
        )
        with self.assertRaises(KeyError) as err:
            mock_vault.get_balances_discrete_timeseries(fetcher_id="another_fetcher_id")
        self.assertEqual(
            err.exception.args[0],
            "Missing balance discrete interval in test setup for fetcher_id='another_fetcher_id'",
        )

    def test_supervisee_mock_raises_on_get_balances_discrete_timeseries(self):
        mock_vault = self.contract_test.create_mock(
            is_supervisee_vault=True,
            balances_discrete_interval_fetchers_mapping={"some_fetcher_id": sentinel.balances},
        )
        with self.assertRaises(ValueError) as err:
            mock_vault.get_balances_discrete_timeseries(fetcher_id="some_fetcher_id")
        self.assertEqual(
            err.exception.args[0],
            "get_balances_discrete_timeseries method cannot be called on a supervisee "
            "Vault object with account_id='default_account'. If the Vault object is not a "
            "supervisee, make sure create_mock is not called with `is_supervisee=True`.",
        )


class TestGetPermittedDenominations(TestCreateMockBase):
    def test_get_permitted_denominations(self):
        mock_vault = self.contract_test.create_mock()
        result = mock_vault.get_permitted_denominations()
        self.assertEqual(result, ["GBP"])


class TestGetHookName(TestCreateMockBase):
    def test_get_hook_name(self):
        mock_vault = self.contract_test.create_mock(hook_name=HookName.PRE_POSTING_HOOK)
        self.assertEqual(mock_vault.get_hook_name(), HookName.PRE_POSTING_HOOK)

    def test_get_hook_name_raises_if_not_set(self):
        mock_vault = self.contract_test.create_mock()
        with self.assertRaises(ValueError) as err:
            mock_vault.get_hook_name()
        self.assertEqual(err.exception.args[0], "No hook name provided")


class TestGetAlias(TestCreateMockBase):
    def test_non_supervisee_mock_raises_on_get_alias(self):
        mock_vault = self.contract_test.create_mock()
        with self.assertRaises(ValueError) as err:
            mock_vault.get_alias()
        self.assertEqual(
            err.exception.args[0],
            "get_alias method cannot be called on a non-supervisee Vault object, "
            "make sure the create_mock argument is set correctly",
        )

    def test_supervisee_mock_raises_on_get_alias_if_not_set(self):
        mock_vault = self.contract_test.create_mock(is_supervisee_vault=True)
        with self.assertRaises(ValueError) as err:
            mock_vault.get_alias()
        self.assertEqual(err.exception.args[0], "No supervisee alias provided")

    def test_supervisee_mock_returns_alias(self):
        mock_vault = self.contract_test.create_mock(
            is_supervisee_vault=True, supervisee_alias="some_alias"
        )
        self.assertEqual(mock_vault.get_alias(), "some_alias")


class TestGetHookResult(TestCreateMockBase):
    def test_non_supervisee_mock_raises_on_get_hook_result(self):
        mock_vault = self.contract_test.create_mock()
        with self.assertRaises(ValueError) as err:
            mock_vault.get_hook_result()
        self.assertEqual(
            err.exception.args[0],
            "get_hook_result method cannot be called on a non-supervisee Vault object, "
            "make sure the create_mock argument is set correctly",
        )

    def test_supervisee_mock_raises_without_result_on_get_hook_result(self):
        mock_vault = self.contract_test.create_mock(is_supervisee_vault=True)
        with self.assertRaises(ValueError) as err:
            mock_vault.get_hook_result()
        self.assertEqual(
            err.exception.args[0],
            "get_hook_result must return one of PrePostingHookResult, "
            "PostPostingHookResult, ScheduledEventHookResult",
        )

    def test_supervisee_mock_returns_result_get_hook_result(self):
        mock_vault = self.contract_test.create_mock(
            is_supervisee_vault=True, supervisee_hook_result=ScheduledEventHookResult()
        )

        self.assertEqual(mock_vault.get_hook_result(), ScheduledEventHookResult())


class TestGetPostingInstructions(TestCreateMockBase):
    def test_supervisee_mock_returns_requires_fetched_postings(self):
        mock_vault = self.contract_test.create_mock(
            is_supervisee_vault=True, requires_fetched_postings=[sentinel.postings]
        )

        self.assertListEqual(mock_vault.get_posting_instructions(), [sentinel.postings])

    def test_non_supervisee_mock_raises_fetched_postings_without_fetcher_id(self):
        mock_vault = self.contract_test.create_mock(
            postings_interval_mapping={"some_fetcher_id": [sentinel.postings]},
        )
        with self.assertRaises(ValueError) as err:
            mock_vault.get_posting_instructions()
        self.assertEqual(
            err.exception.args[0],
            "You must provide a fetcher ID",
        )

    def test_non_supervisee_mock_fetched_postings_if_empty_list(self):
        mock_vault = self.contract_test.create_mock(
            postings_interval_mapping={"some_fetcher_id": []},
        )
        self.assertListEqual(mock_vault.get_posting_instructions(fetcher_id="some_fetcher_id"), [])

    def test_non_supervisee_mock_raises_fetched_postings_with_incorrect_fetcher_id(self):
        mock_vault = self.contract_test.create_mock(
            postings_interval_mapping={"some_fetcher_id": [sentinel.postings]},
        )
        with self.assertRaises(ValueError) as err:
            mock_vault.get_posting_instructions("another_fetcher_id")
        self.assertEqual(
            err.exception.args[0],
            "Missing posting interval in test setup for fetcher_id='another_fetcher_id'",
        )


class TestGetClientTransactions(TestCreateMockBase):
    def test_supervisee_mock_returns_requires_fetched_client_transactions(self):
        mock_vault = self.contract_test.create_mock(
            is_supervisee_vault=True,
            requires_fetched_client_transactions={sentinel.unique_id: sentinel.client_transaction},
        )

        self.assertDictEqual(
            mock_vault.get_client_transactions(), {sentinel.unique_id: sentinel.client_transaction}
        )

    def test_supervisee_mock_raises_if_fetcher_id_in_get_client_transactions(self):
        mock_vault = self.contract_test.create_mock(
            is_supervisee_vault=True,
        )

        with self.assertRaises(ValueError) as err:
            mock_vault.get_client_transactions(fetcher_id="some_fetcher")
        self.assertEqual(
            err.exception.args[0],
            "Supervisee vault object cannot provide fetcher_id to get_client_transactions()",
        )

    def test_supervisee_mock_raises_if_missing_requires_fetched_get_client_transactions(self):
        mock_vault = self.contract_test.create_mock(
            is_supervisee_vault=True,
        )

        with self.assertRaises(ValueError) as err:
            mock_vault.get_client_transactions()
        self.assertEqual(
            err.exception.args[0],
            "Missing requires fetched client transactions in test setup",
        )

    def test_non_supervisee_mock_raises_fetched_client_transactions_without_fetcher_id(self):
        mock_vault = self.contract_test.create_mock(
            client_transactions_mapping={
                "some_fetcher_id": {sentinel.unique_id: sentinel.client_transaction}
            },
        )
        with self.assertRaises(ValueError) as err:
            mock_vault.get_client_transactions()
        self.assertEqual(
            err.exception.args[0],
            "You must provide a fetcher ID",
        )

    def test_non_supervisee_mock_fetched_client_transactions_if_empty_dict(self):
        mock_vault = self.contract_test.create_mock(
            client_transactions_mapping={"some_fetcher_id": {}},
        )
        self.assertDictEqual(mock_vault.get_client_transactions(fetcher_id="some_fetcher_id"), {})

    def test_non_supervisee_mock_fetched_client_transactions(self):
        mock_vault = self.contract_test.create_mock(
            client_transactions_mapping={
                "some_fetcher_id": {sentinel.unique_id: sentinel.client_transaction}
            },
        )
        self.assertDictEqual(
            mock_vault.get_client_transactions(fetcher_id="some_fetcher_id"),
            {sentinel.unique_id: sentinel.client_transaction},
        )

    def test_non_supervisee_mock_raises_fetched_client_transactions_with_incorrect_fetcher_id(self):
        mock_vault = self.contract_test.create_mock(
            client_transactions_mapping={"some_fetcher_id": {}},
        )
        with self.assertRaises(ValueError) as err:
            mock_vault.get_client_transactions("another_fetcher_id")
        self.assertEqual(
            err.exception.args[0],
            "Missing client transactions in test setup for fetcher_id='another_fetcher_id'",
        )


class TestGetCalendars(TestCreateMockBase):

    # get_calendar_events

    def test_get_calendar_events_replaces_clu_dependencies(self):
        # construct mocks
        calendar_events = [
            CalendarEvent(
                id="1",
                calendar_id="&{PUBLIC_HOLIDAYS}",
                start_datetime=datetime(2023, 1, 1, tzinfo=ZoneInfo("UTC")),
                end_datetime=datetime(2023, 1, 2, tzinfo=ZoneInfo("UTC")),
            ),
            CalendarEvent(
                id="2",
                calendar_id="&{PUBLIC_HOLIDAYS}",
                start_datetime=datetime(2023, 1, 2, tzinfo=ZoneInfo("UTC")),
                end_datetime=datetime(2023, 1, 3, tzinfo=ZoneInfo("UTC")),
            ),
        ]
        mock_vault = self.contract_test.create_mock(calendar_events=calendar_events)

        # expected result
        non_clu_calendar_events = [
            CalendarEvent(
                id="1",
                calendar_id="PUBLIC_HOLIDAYS",
                start_datetime=datetime(2023, 1, 1, tzinfo=ZoneInfo("UTC")),
                end_datetime=datetime(2023, 1, 2, tzinfo=ZoneInfo("UTC")),
            ),
            CalendarEvent(
                id="2",
                calendar_id="PUBLIC_HOLIDAYS",
                start_datetime=datetime(2023, 1, 2, tzinfo=ZoneInfo("UTC")),
                end_datetime=datetime(2023, 1, 3, tzinfo=ZoneInfo("UTC")),
            ),
        ]
        calendar_events_object = CalendarEvents(calendar_events=non_clu_calendar_events)
        # run function
        self.assertListEqual(
            mock_vault.get_calendar_events(calendar_ids=["PUBLIC_HOLIDAYS"]),
            calendar_events_object,
        )

    def test_get_calendar_events_returns_events_for_specified_ids(self):
        # construct mocks
        calendar_events = [
            CalendarEvent(
                id="1",
                calendar_id="&{PUBLIC_HOLIDAYS_1}",
                start_datetime=datetime(2023, 1, 1, tzinfo=ZoneInfo("UTC")),
                end_datetime=datetime(2023, 1, 2, tzinfo=ZoneInfo("UTC")),
            ),
            CalendarEvent(
                id="2",
                calendar_id="&{PUBLIC_HOLIDAYS_2}",
                start_datetime=datetime(2023, 1, 2, tzinfo=ZoneInfo("UTC")),
                end_datetime=datetime(2023, 1, 3, tzinfo=ZoneInfo("UTC")),
            ),
        ]
        mock_vault = self.contract_test.create_mock(calendar_events=calendar_events)

        # run function
        self.assertListEqual(
            mock_vault.get_calendar_events(calendar_ids=["PUBLIC_HOLIDAYS_2"]),
            CalendarEvents(
                calendar_events=[
                    CalendarEvent(
                        id="2",
                        calendar_id="PUBLIC_HOLIDAYS_2",
                        start_datetime=datetime(2023, 1, 2, tzinfo=ZoneInfo("UTC")),
                        end_datetime=datetime(2023, 1, 3, tzinfo=ZoneInfo("UTC")),
                    ),
                ]
            ),
        )

    def test_get_calendar_events_raises_without_calendar_ids(self):
        mock_vault = self.contract_test.create_mock()
        with self.assertRaises(TypeError) as err:
            mock_vault.get_calendar_events()
        self.assertIn(
            "missing 1 required positional argument: 'calendar_ids'",
            err.exception.args[0],
        )

    # get_calendars_observation

    def test_mock_get_calendars_observation(self):
        mock_vault = self.contract_test.create_mock(
            calendars_observation_fetchers_mapping={"fetcher_id": sentinel.calendars_observation}
        )
        self.assertEqual(
            mock_vault.get_calendars_observation(fetcher_id="fetcher_id"),
            sentinel.calendars_observation,
        )

    def test_mock_get_calendars_observation_with_undefined_fetcher_id(self):
        mock_vault = self.contract_test.create_mock(
            calendars_observation_fetchers_mapping={"fetcher_id": sentinel.calendars_observation}
        )
        with self.assertRaises(KeyError) as err:
            mock_vault.get_calendars_observation(fetcher_id="another_fetcher_id")
        self.assertEqual(
            err.exception.args[0],
            "Missing calendars observation in test setup for fetcher_id='another_fetcher_id'",
        )

    def test_get_calendars_observation_raises_without_fetcher_id(self):
        mock_vault = self.contract_test.create_mock(
            calendars_observation_fetchers_mapping={"some_fetcher_id": sentinel.observation},
        )
        with self.assertRaises(TypeError) as err:
            mock_vault.get_calendars_observation()
        self.assertIn(
            "missing 1 required positional argument: 'fetcher_id'",
            err.exception.args[0],
        )

    def test_mock_get_calendars_observation_raises_on_supervisee(self):
        mock_vault = self.contract_test.create_mock(
            is_supervisee_vault=True,
            calendars_observation_fetchers_mapping={
                "some_fetcher_id": sentinel.calendars_observation
            },
        )
        with self.assertRaises(ValueError) as err:
            mock_vault.get_calendars_observation(fetcher_id="some_fetcher_id")
        self.assertEqual(
            err.exception.args[0],
            "get_calendars_observation method cannot be called on a supervisee "
            "Vault object with account_id='default_account'. If the Vault object is not a "
            "supervisee, make sure create_mock is not called with `is_supervisee=True`.",
        )

    # get_calendars_timeseries

    def test_get_calendars_timeseries(self):
        mock_vault = self.contract_test.create_mock(
            calendars_interval_fetchers_mapping={"some_fetcher_id": sentinel.calendars},
        )
        self.assertEqual(
            mock_vault.get_calendars_timeseries(fetcher_id="some_fetcher_id"),
            sentinel.calendars,
        )

    def test_get_calendars_timeseries_raises_with_incorrect_fetcher_id(self):
        mock_vault = self.contract_test.create_mock(
            calendars_interval_fetchers_mapping={"some_fetcher_id": sentinel.calendars},
        )
        with self.assertRaises(KeyError) as err:
            mock_vault.get_calendars_timeseries("another_fetcher_id")
        self.assertEqual(
            err.exception.args[0],
            "Missing calendars interval in test setup for fetcher_id='another_fetcher_id'",
        )

    def test_get_calendars_timeseries_raises_without_fetcher_id(self):
        mock_vault = self.contract_test.create_mock(
            calendars_interval_fetchers_mapping={"some_fetcher_id": sentinel.observation},
        )
        with self.assertRaises(TypeError) as err:
            mock_vault.get_calendars_timeseries()
        self.assertIn(
            "missing 1 required positional argument: 'fetcher_id'",
            err.exception.args[0],
        )

    def test_mock_get_calendars_timeseries_raises_on_supervisee(self):
        mock_vault = self.contract_test.create_mock(
            is_supervisee_vault=True,
            calendars_interval_fetchers_mapping={"some_fetcher_id": sentinel.calendars_timeseries},
        )
        with self.assertRaises(ValueError) as err:
            mock_vault.get_calendars_timeseries(fetcher_id="some_fetcher_id")
        self.assertEqual(
            err.exception.args[0],
            "get_calendars_timeseries method cannot be called on a supervisee "
            "Vault object with account_id='default_account'. If the Vault object is not a "
            "supervisee, make sure create_mock is not called with `is_supervisee=True`.",
        )


class TestGetParameters(TestCreateMockBase):

    # get_parameter_timeseries

    def test_mock_get_parameter_ts_with_name(self):
        mock_vault = self.contract_test.create_mock(
            parameter_ts={"param_name": sentinel.parameter_ts}
        )
        self.assertEqual(
            mock_vault.get_parameter_timeseries(name="param_name"), sentinel.parameter_ts
        )

    def test_mock_get_parameter_ts_with_undefined_parameter(self):
        mock_vault = self.contract_test.create_mock(
            parameter_ts={"param_name": sentinel.parameter_ts}
        )
        with self.assertRaises(KeyError) as err:
            mock_vault.get_parameter_timeseries(name="another_param_name")
        self.assertEqual(
            err.exception.args[0],
            "Missing parameter timeseries in test setup for parameter name='another_param_name'",
        )

    def test_mock_get_parameter_ts_with_fetcher_id(self):
        mock_vault = self.contract_test.create_mock(
            parameters_interval_fetchers_mapping={"fetcher_id": sentinel.parameter_value_ts}
        )
        self.assertEqual(
            mock_vault.get_parameter_timeseries(fetcher_id="fetcher_id"),
            sentinel.parameter_value_ts,
        )

    def test_mock_get_parameter_ts_with_undefined_fetcher_id(self):
        mock_vault = self.contract_test.create_mock(
            parameters_interval_fetchers_mapping={"fetcher_id": sentinel.parameter_value_ts}
        )
        with self.assertRaises(KeyError) as err:
            mock_vault.get_parameter_timeseries(fetcher_id="another_fetcher_id")
        self.assertEqual(
            err.exception.args[0],
            "Missing parameter interval in test setup for fetcher_id='another_fetcher_id'",
        )

    def test_mock_get_parameter_ts_with_no_name_or_fetcher_id(self):
        mock_vault = self.contract_test.create_mock(
            parameter_ts={"param_name": sentinel.parameter_ts}
        )
        with self.assertRaises(ValueError) as err:
            mock_vault.get_parameter_timeseries()
        self.assertEqual(
            err.exception.args[0],
            "get_parameter_timeseries called without `name` or `fetcher_id` kwargs",
        )

    def test_mock_get_parameters_ts_with_fetcher_id_raises_on_supervisee(self):
        mock_vault = self.contract_test.create_mock(
            is_supervisee_vault=True,
            parameters_interval_fetchers_mapping={"some_fetcher_id": sentinel.parameters},
        )
        with self.assertRaises(ValueError) as err:
            mock_vault.get_parameter_timeseries(fetcher_id="some_fetcher_id")
        self.assertEqual(
            err.exception.args[0],
            "Supervisee vault object cannot provide fetcher_id to get_parameter_timeseries().",
        )

    # get_parameters_observation

    def test_mock_get_parameters_observation(self):
        mock_vault = self.contract_test.create_mock(
            parameters_observation_fetchers_mapping={"fetcher_id": sentinel.parameters_observation}
        )
        self.assertEqual(
            mock_vault.get_parameters_observation(fetcher_id="fetcher_id"),
            sentinel.parameters_observation,
        )

    def test_mock_get_parameters_observation_with_undefined_fetcher_id(self):
        mock_vault = self.contract_test.create_mock(
            parameters_observation_fetchers_mapping={"fetcher_id": sentinel.parameters_observation}
        )
        with self.assertRaises(KeyError) as err:
            mock_vault.get_parameters_observation(fetcher_id="another_fetcher_id")
        self.assertEqual(
            err.exception.args[0],
            "Missing parameter observation in test setup for fetcher_id='another_fetcher_id'",
        )

    def test_get_parameters_observation_raises_without_fetcher_id(self):
        mock_vault = self.contract_test.create_mock(
            parameters_observation_fetchers_mapping={"some_fetcher_id": sentinel.parameters},
        )
        with self.assertRaises(TypeError) as err:
            mock_vault.get_parameters_observation()
        self.assertIn(
            "missing 1 required positional argument: 'fetcher_id'",
            err.exception.args[0],
        )

    def test_mock_get_parameters_observation_raises_on_supervisee(self):
        mock_vault = self.contract_test.create_mock(
            is_supervisee_vault=True,
            parameters_observation_fetchers_mapping={
                "some_fetcher_id": sentinel.parameters_observation
            },
        )
        with self.assertRaises(ValueError) as err:
            mock_vault.get_parameters_observation(fetcher_id="some_fetcher_id")
        self.assertEqual(
            err.exception.args[0],
            "get_parameters_observation method cannot be called on a supervisee "
            "Vault object with account_id='default_account'. If the Vault object is not a "
            "supervisee, make sure create_mock is not called with `is_supervisee=True`.",
        )


class TestGetFlags(TestCreateMockBase):

    # get_flags_timeseries

    def test_mock_get_flags_ts_with_fetcher_id(self):
        mock_vault = self.contract_test.create_mock(
            flags_interval_fetchers_mapping={"fetcher_id": sentinel.flags_timeseries}
        )
        self.assertEqual(
            mock_vault.get_flags_timeseries(fetcher_id="fetcher_id"),
            sentinel.flags_timeseries,
        )

    def test_mock_get_flags_ts_with_undefined_fetcher_id(self):
        mock_vault = self.contract_test.create_mock(
            flags_interval_fetchers_mapping={"fetcher_id": sentinel.flags_timeseries}
        )
        with self.assertRaises(KeyError):
            mock_vault.get_flags_timeseries(fetcher_id="another_fetcher_id")

    def test_get_flags_timeseries_raises_without_fetcher_id(self):
        mock_vault = self.contract_test.create_mock(
            flags_interval_fetchers_mapping={"some_fetcher_id": sentinel.flags_timeseries},
        )
        with self.assertRaises(TypeError) as err:
            mock_vault.get_flags_timeseries()
        self.assertIn(
            "missing 1 required positional argument: 'fetcher_id'",
            err.exception.args[0],
        )

    def test_mock_get_flags_timeseries_raises_on_supervisee(self):
        mock_vault = self.contract_test.create_mock(
            is_supervisee_vault=True,
            flags_interval_fetchers_mapping={"some_fetcher_id": sentinel.flags_timeseries},
        )
        with self.assertRaises(ValueError) as err:
            mock_vault.get_flags_timeseries(fetcher_id="some_fetcher_id")
        self.assertEqual(
            err.exception.args[0],
            "get_flags_timeseries method cannot be called on a supervisee "
            "Vault object with account_id='default_account'. If the Vault object is not a "
            "supervisee, make sure create_mock is not called with `is_supervisee=True`.",
        )

    # get_flags_observation

    def test_mock_get_flags_observation(self):
        mock_vault = self.contract_test.create_mock(
            flags_observation_fetchers_mapping={"fetcher_id": sentinel.flags_observation}
        )
        self.assertEqual(
            mock_vault.get_flags_observation(fetcher_id="fetcher_id"),
            sentinel.flags_observation,
        )

    def test_mock_get_flags_observation_with_undefined_fetcher_id(self):
        mock_vault = self.contract_test.create_mock(
            flags_observation_fetchers_mapping={"fetcher_id": sentinel.flags_observation}
        )
        with self.assertRaises(KeyError):
            mock_vault.get_flags_observation(fetcher_id="another_fetcher_id")

    def test_get_flags_observation_raises_without_fetcher_id(self):
        mock_vault = self.contract_test.create_mock(
            flags_observation_fetchers_mapping={"some_fetcher_id": sentinel.flags_observation},
        )
        with self.assertRaises(TypeError) as err:
            mock_vault.get_flags_observation()
        self.assertIn(
            "missing 1 required positional argument: 'fetcher_id'",
            err.exception.args[0],
        )

    def test_mock_get_flags_observation_raises_on_supervisee(self):
        mock_vault = self.contract_test.create_mock(
            is_supervisee_vault=True,
            flags_observation_fetchers_mapping={"some_fetcher_id": sentinel.flags_observation},
        )
        with self.assertRaises(ValueError) as err:
            mock_vault.get_flags_observation(fetcher_id="some_fetcher_id")
        self.assertEqual(
            err.exception.args[0],
            "get_flags_observation method cannot be called on a supervisee "
            "Vault object with account_id='default_account'. If the Vault object is not a "
            "supervisee, make sure create_mock is not called with `is_supervisee=True`.",
        )


class TestPostingHelpers(TestCreateMockBase):
    def test_can_create_zero_amount_outbound_settlement_with_from_proto(self):
        self.assertIsInstance(
            self.contract_test.settle_outbound_auth(
                unsettled_amount=Decimal("0"), amount=Decimal("0"), _from_proto=True
            ),
            Settlement,
        )

    def test_cant_create_zero_amount_outbound_settlement_without_from_proto(self):
        # Can't access the InvalidSmartContractError from the contracts_api
        with self.assertRaisesRegex(Exception, r"Amount must be greater than 0"):
            self.contract_test.settle_outbound_auth(
                unsettled_amount=Decimal("0"),
                amount=Decimal("0"),
            )

    def test_can_create_zero_amount_inbound_settlement_with_from_proto(self):
        self.assertIsInstance(
            self.contract_test.settle_inbound_auth(
                unsettled_amount=Decimal("0"), amount=Decimal("0"), _from_proto=True
            ),
            Settlement,
        )

    def test_cant_create_zero_amount_inbound_settlement_without_from_proto(self):
        # Can't access the InvalidSmartContractError from the contracts_api
        with self.assertRaisesRegex(Exception, r"Amount must be greater than 0"):
            self.contract_test.settle_inbound_auth(
                unsettled_amount=Decimal("0"),
                amount=Decimal("0"),
            )

    def test_can_create_zero_amount_outbound_release_with_from_proto(self):
        self.assertIsInstance(
            self.contract_test.release_outbound_auth(
                unsettled_amount=Decimal("0"), amount=Decimal("0"), _from_proto=True
            ),
            Release,
        )

    def test_cant_create_zero_amount_outbound_release_without_from_proto(self):
        # Can't access the InvalidSmartContractError from the contracts_api
        with self.assertRaisesRegex(Exception, r"Amount must be greater than 0"):
            self.contract_test.release_outbound_auth(
                unsettled_amount=Decimal("0"),
                amount=Decimal("0"),
            )

    def test_can_create_zero_amount_inbound_release_with_from_proto(self):
        self.assertIsInstance(
            self.contract_test.release_inbound_auth(
                unsettled_amount=Decimal("0"), amount=Decimal("0"), _from_proto=True
            ),
            Release,
        )

    def test_cant_create_zero_amount_inbound_release_without_from_proto(self):
        # Can't access the InvalidSmartContractError from the contracts_api
        with self.assertRaisesRegex(Exception, r"Amount must be greater than 0"):
            self.contract_test.release_inbound_auth(
                unsettled_amount=Decimal("0"),
                amount=Decimal("0"),
            )

    def test_inbound_auth_explicit_parameter_defaults(self):
        result_default = self.contract_test.inbound_auth(amount=Decimal(100))
        self.assertEqual(result_default.client_transaction_id, "MOCK_POSTING")

    def test_inbound_auth_explicit_parameter_provided(self):
        custom_client_transaction_id = "explicit-custom-id"
        result_provided = self.contract_test.inbound_auth(
            amount=Decimal(100), client_transaction_id=custom_client_transaction_id
        )
        self.assertEqual(result_provided.client_transaction_id, custom_client_transaction_id)

    def test_outbound_hard_settlement_kwargs_parameter_defaults(self):
        result_default = self.contract_test.outbound_hard_settlement(amount=Decimal(200))
        actual_id = getattr(result_default, "_client_transaction_id", "")
        self.assertEqual(actual_id, "MOCK_POSTING")

    def test_outbound_hard_settlement_kwargs_parameter_provided(self):
        custom_client_transaction_id = "kwargs-custom-id"
        result_provided = self.contract_test.outbound_hard_settlement(
            amount=Decimal(200), client_transaction_id=custom_client_transaction_id
        )
        actual_id = getattr(result_provided, "_client_transaction_id", "")
        self.assertEqual(actual_id, custom_client_transaction_id)

    def test_inbound_auth_with_target_sub_account_id(self):
        result = self.contract_test.inbound_auth(
            amount=Decimal(100), target_sub_account_id="sub-acc-1"
        )
        self.assertIsInstance(result, InboundAuthorisation)
        self.assertEqual(result.target_sub_account_id, "sub-acc-1")

    def test_outbound_auth_with_target_sub_account_id(self):
        result = self.contract_test.outbound_auth(
            amount=Decimal(100), target_sub_account_id="sub-acc-1"
        )
        self.assertIsInstance(result, OutboundAuthorisation)
        self.assertEqual(result.target_sub_account_id, "sub-acc-1")

    def test_inbound_hard_settlement_with_target_sub_account_id(self):
        result = self.contract_test.inbound_hard_settlement(
            amount=Decimal(100), target_sub_account_id="sub-acc-1"
        )
        self.assertIsInstance(result, InboundHardSettlement)
        self.assertEqual(result.target_sub_account_id, "sub-acc-1")

    def test_outbound_hard_settlement_with_target_sub_account_id(self):
        result = self.contract_test.outbound_hard_settlement(
            amount=Decimal(100), target_sub_account_id="sub-acc-1"
        )
        self.assertIsInstance(result, OutboundHardSettlement)
        self.assertEqual(result.target_sub_account_id, "sub-acc-1")

    def test_inbound_transfer_with_target_sub_account_ids(self):
        result = self.contract_test.inbound_transfer(
            amount=Decimal(100),
            debtor_target_sub_account_id="sub-acc-1",
            creditor_target_sub_account_id="sub-acc-2",
        )
        self.assertIsInstance(result, Transfer)
        self.assertEqual(result.debtor_target_sub_account_id, "sub-acc-1")
        self.assertEqual(result.creditor_target_sub_account_id, "sub-acc-2")

    def test_outbound_transfer_with_target_sub_account_ids(self):
        result = self.contract_test.outbound_transfer(
            amount=Decimal(100),
            debtor_target_sub_account_id="sub-acc-1",
            creditor_target_sub_account_id="sub-acc-2",
        )
        self.assertIsInstance(result, Transfer)
        self.assertEqual(result.debtor_target_sub_account_id, "sub-acc-1")
        self.assertEqual(result.creditor_target_sub_account_id, "sub-acc-2")


class TestBalanceHelpers(TestCreateMockBase):
    def test_balance_positive_net_liability(self):
        self.contract_test.tside = Tside.LIABILITY
        self.assertEqual(
            self.contract_test.balance(net="10"),
            Balance(credit=Decimal("10"), debit=Decimal("0"), net=Decimal("10")),
        )

    def test_balance_positive_net_asset(self):
        self.contract_test.tside = Tside.ASSET
        self.assertEqual(
            self.contract_test.balance(net="10"),
            Balance(credit=Decimal("0"), debit=Decimal("10"), net=Decimal("10")),
        )

    def test_balance_negative_net_liability(self):
        self.contract_test.tside = Tside.LIABILITY
        self.assertEqual(
            self.contract_test.balance(net="-10"),
            Balance(credit=Decimal("0"), debit=Decimal("10"), net=Decimal("-10")),
        )

    def test_balance_negative_net_asset(self):
        self.contract_test.tside = Tside.ASSET
        self.assertEqual(
            self.contract_test.balance(net="-10"),
            Balance(credit=Decimal("10"), debit=Decimal("0"), net=Decimal("-10")),
        )

    def test_balance_credit_gt_debit_liability(self):
        self.contract_test.tside = Tside.LIABILITY
        self.assertEqual(
            self.contract_test.balance(credit="10", debit="2"),
            Balance(credit=Decimal("10"), debit=Decimal("2"), net=Decimal("8")),
        )

    def test_balance_credit_gt_debit_asset(self):
        self.contract_test.tside = Tside.ASSET
        self.assertEqual(
            self.contract_test.balance(credit="10", debit="2"),
            Balance(credit=Decimal("10"), debit=Decimal("2"), net=Decimal("-8")),
        )

    def test_balance_credit_lt_debit_liability(self):
        self.contract_test.tside = Tside.LIABILITY
        self.assertEqual(
            self.contract_test.balance(credit="2", debit="10"),
            Balance(credit=Decimal("2"), debit=Decimal("10"), net=Decimal("-8")),
        )

    def test_balance_credit_lt_debit_asset(self):
        self.contract_test.tside = Tside.ASSET
        self.assertEqual(
            self.contract_test.balance(credit="2", debit="10"),
            Balance(credit=Decimal("2"), debit=Decimal("10"), net=Decimal("8")),
        )

    def test_balance_credit_eq_debit_liability(self):
        self.contract_test.tside = Tside.LIABILITY
        self.assertEqual(
            self.contract_test.balance(credit="2", debit="2"),
            Balance(credit=Decimal("2"), debit=Decimal("2"), net=Decimal("0")),
        )

    def test_balance_credit_eq_debit_asset(self):
        self.contract_test.tside = Tside.ASSET
        self.assertEqual(
            self.contract_test.balance(credit="2", debit="2"),
            Balance(credit=Decimal("2"), debit=Decimal("2"), net=Decimal("0")),
        )

    def test_balance_negative_debit(self):
        self.contract_test.tside = Tside.ASSET
        with self.assertRaises(ValueError) as ctx:
            self.contract_test.balance(debit="-2", credit="2")
        self.assertEqual(
            ctx.exception.args[0],
            "credit=Decimal('2') and debit=Decimal('-2') must be zero or positive",
        )

    def test_balance_missing_args(self):
        self.contract_test.tside = Tside.ASSET
        with self.assertRaises(ValueError) as ctx:
            # testing error handling that should be avoided by overloads
            self.contract_test.balance(credit="2")
        self.assertEqual(
            ctx.exception.args[0],
            "Cannot create balance with net `None` and credit/debit also `None`",
        )

    def test_balance_timeseries_net_balance(self):
        self.contract_test.tside = Tside.LIABILITY
        dt = datetime(2020, 1, 1, tzinfo=ZoneInfo("UTC"))
        self.assertEqual(
            self.contract_test.construct_balance_timeseries(dt=dt, net="3"),
            BalanceTimeseries(
                [(dt, Balance(credit=Decimal("3"), debit=Decimal("0"), net=Decimal("3")))]
            ),
        )

    def test_balance_timeseries_net_zero_balance(self):
        self.contract_test.tside = Tside.LIABILITY
        dt = datetime(2020, 1, 1, tzinfo=ZoneInfo("UTC"))
        self.assertEqual(
            self.contract_test.construct_balance_timeseries(dt=dt, net="0"),
            BalanceTimeseries(
                [(dt, Balance(credit=Decimal("0"), debit=Decimal("0"), net=Decimal("0")))]
            ),
        )

    def test_balance_timeseries_credit_debit_balance(self):
        self.contract_test.tside = Tside.LIABILITY
        dt = datetime(2020, 1, 1, tzinfo=ZoneInfo("UTC"))
        self.assertEqual(
            self.contract_test.construct_balance_timeseries(dt=dt, credit="3", debit="1"),
            BalanceTimeseries(
                [(dt, Balance(credit=Decimal("3"), debit=Decimal("1"), net=Decimal("2")))]
            ),
        )

    def test_balance_timeseries_credit_debit_zero_balance(self):
        self.contract_test.tside = Tside.LIABILITY
        dt = datetime(2020, 1, 1, tzinfo=ZoneInfo("UTC"))
        self.assertEqual(
            self.contract_test.construct_balance_timeseries(dt=dt, credit="0", debit="0"),
            BalanceTimeseries(
                [(dt, Balance(credit=Decimal("0"), debit=Decimal("0"), net=Decimal("0")))]
            ),
        )

    def test_balance_timeseries_missing_args(self):
        self.contract_test.tside = Tside.ASSET
        with self.assertRaises(ValueError) as ctx:
            # testing error handling that should be avoided by overloads
            self.contract_test.construct_balance_timeseries(
                dt=datetime(2020, 1, 1),
                credit="2",
            )
        self.assertEqual(
            ctx.exception.args[0],
            "Specify net alone, or debit and credit",
        )

    def test_balance_discrete_timeseries_net_balance(self):
        self.contract_test.tside = Tside.LIABILITY
        dt = datetime(2020, 1, 1, tzinfo=ZoneInfo("UTC"))
        self.assertEqual(
            self.contract_test.construct_balance_discrete_timeseries(dt=dt, net="3"),
            BalanceDiscreteTimeseries(
                [(dt, Balance(credit=Decimal("3"), debit=Decimal("0"), net=Decimal("3")))]
            ),
        )

    def test_balance_discrete_timeseries_net_zero_balance(self):
        self.contract_test.tside = Tside.LIABILITY
        dt = datetime(2020, 1, 1, tzinfo=ZoneInfo("UTC"))
        self.assertEqual(
            self.contract_test.construct_balance_discrete_timeseries(dt=dt, net="0"),
            BalanceDiscreteTimeseries(
                [(dt, Balance(credit=Decimal("0"), debit=Decimal("0"), net=Decimal("0")))]
            ),
        )

    def test_balance_discrete_timeseries_credit_debit_balance(self):
        self.contract_test.tside = Tside.LIABILITY
        dt = datetime(2020, 1, 1, tzinfo=ZoneInfo("UTC"))
        self.assertEqual(
            self.contract_test.construct_balance_discrete_timeseries(dt=dt, credit="3", debit="1"),
            BalanceDiscreteTimeseries(
                [(dt, Balance(credit=Decimal("3"), debit=Decimal("1"), net=Decimal("2")))]
            ),
        )

    def test_balance_discrete_timeseries_credit_debit_zero_balance(self):
        self.contract_test.tside = Tside.LIABILITY
        dt = datetime(2020, 1, 1, tzinfo=ZoneInfo("UTC"))
        self.assertEqual(
            self.contract_test.construct_balance_discrete_timeseries(dt=dt, credit="0", debit="0"),
            BalanceDiscreteTimeseries(
                [(dt, Balance(credit=Decimal("0"), debit=Decimal("0"), net=Decimal("0")))]
            ),
        )

    def test_balance_discrete_timeseries_missing_args(self):
        self.contract_test.tside = Tside.ASSET
        with self.assertRaises(ValueError) as ctx:
            # testing error handling that should be avoided by overloads
            self.contract_test.construct_balance_discrete_timeseries(
                dt=datetime(2020, 1, 1),
                credit="2",
            )
        self.assertEqual(
            ctx.exception.args[0],
            "Specify net alone, or debit and credit",
        )

    def test_balance_coordinate_default_denomination(self):
        self.contract_test.default_denomination = "GBP"
        coord = self.contract_test.balance_coordinate()
        self.assertEqual(coord.account_address, DEFAULT_ADDRESS)
        self.assertEqual(coord.denomination, "GBP")
        self.assertEqual(coord.phase, Phase.COMMITTED)
        self.assertEqual(coord.asset, DEFAULT_ASSET)

    def test_balance_coordinate_custom_denomination_and_args(self):
        coord = self.contract_test.balance_coordinate(
            account_address="custom_address",
            denomination="USD",
            phase=Phase.PENDING_OUT,
            asset="custom_asset",
        )
        self.assertEqual(coord.account_address, "custom_address")
        self.assertEqual(coord.denomination, "USD")
        self.assertEqual(coord.phase, Phase.PENDING_OUT)
        self.assertEqual(coord.asset, "custom_asset")


class TestCreateSubAccountMock(TestCreateMockBase):
    def test_create_sub_account_mock_defaults(self):
        mock_account = self.contract_test.create_mock()
        mock_savo = self.contract_test.create_sub_account_mock(
            mock_parent_account=mock_account,
            sub_account_id="sub_acc_id",
            sub_account_type="sub_acc_type",
        )
        self.assertEqual(mock_savo.sub_account_id, "sub_acc_id")
        self.assertEqual(mock_savo.sub_account_type, "sub_acc_type")
        self.assertEqual(
            mock_savo.get_sub_account_activation_datetime(),
            datetime(2019, 1, 1, tzinfo=ZoneInfo("UTC")),
        )

    def test_create_sub_account_mock_custom_values(self):
        mock_account = self.contract_test.create_mock()
        custom_id = "custom_id"
        custom_type = "custom_type"
        custom_dt = datetime(2026, 1, 1, tzinfo=ZoneInfo("UTC"))
        mock_savo = self.contract_test.create_sub_account_mock(
            mock_parent_account=mock_account,
            sub_account_id=custom_id,
            sub_account_type=custom_type,
            activation_datetime=custom_dt,
        )
        self.assertEqual(mock_savo.sub_account_id, custom_id)
        self.assertEqual(mock_savo.sub_account_type, custom_type)
        self.assertEqual(mock_savo.get_sub_account_activation_datetime(), custom_dt)

    def test_create_sub_account_mock_populates_sub_accounts_dictionary(self):
        mock_account = self.contract_test.create_mock()
        created_sub_account = self.contract_test.create_sub_account_mock(
            mock_parent_account=mock_account,
            sub_account_id="sub_account_id",
            sub_account_type="sub_account_type",
        )
        self.assertIsInstance(mock_account.sub_accounts, dict)

        self.assertIs(mock_account.sub_accounts["sub_account_id"], created_sub_account)

    def test_sub_accounts_dictionary_cannot_be_directly_edited(self):
        mock_account = self.contract_test.create_mock()

        with self.assertRaises(TypeError):
            mock_account.sub_accounts["sub_account_id"] = "invalid Sub-Account"


class TestSubAccountBalanceHelpers(TestCreateMockBase):
    def test_mock_get_balances_observation(self):
        mock_account = self.contract_test.create_mock()
        fetcher_id = "bof_id"
        mock_savo = self.contract_test.create_sub_account_mock(
            mock_parent_account=mock_account,
            sub_account_id="sub_acc_id",
            sub_account_type="sub_acc_type",
            balances_observation_fetchers_mapping={fetcher_id: sentinel.balances_observation},
        )
        self.assertEqual(
            mock_savo.get_balances_observation(fetcher_id=fetcher_id),
            sentinel.balances_observation,
        )

        with self.assertRaises(KeyError):
            mock_savo.get_balances_observation(fetcher_id="missing_fetcher")

    def test_mock_get_balances_discrete_timeseries(self):
        mock_account = self.contract_test.create_mock()
        fetcher_id = "bdif_id"
        mock_savo = self.contract_test.create_sub_account_mock(
            mock_parent_account=mock_account,
            sub_account_id="sub_acc_id",
            sub_account_type="sub_acc_type",
            balances_discrete_interval_fetchers_mapping={fetcher_id: sentinel.discrete_timeseries},
        )
        self.assertEqual(
            mock_savo.get_balances_discrete_timeseries(fetcher_id=fetcher_id),
            sentinel.discrete_timeseries,
        )

        with self.assertRaises(KeyError):
            mock_savo.get_balances_discrete_timeseries(fetcher_id="missing_fetcher")

    def test_mock_get_balances_timeseries(self):
        mock_account = self.contract_test.create_mock()
        fetcher_id = "bif_id"
        mock_savo = self.contract_test.create_sub_account_mock(
            mock_parent_account=mock_account,
            sub_account_id="sub_acc_id",
            sub_account_type="sub_acc_type",
            balances_interval_fetchers_mapping={fetcher_id: sentinel.balances_timeseries},
        )
        self.assertEqual(
            mock_savo.get_balances_timeseries(fetcher_id=fetcher_id),
            sentinel.balances_timeseries,
        )

        with self.assertRaises(KeyError):
            mock_savo.get_balances_timeseries(fetcher_id="missing_fetcher")

    def test_mock_get_client_transactions(self):
        mock_account = self.contract_test.create_mock()
        fetcher_id = "pif"
        mock_savo = self.contract_test.create_sub_account_mock(
            mock_parent_account=mock_account,
            sub_account_id="sub_acc_id",
            sub_account_type="sub_acc_type",
            client_transactions_mapping={fetcher_id: sentinel.client_transactions},
        )
        self.assertEqual(
            mock_savo.get_client_transactions(fetcher_id=fetcher_id),
            sentinel.client_transactions,
        )

        with self.assertRaises(ValueError):
            mock_savo.get_client_transactions(fetcher_id="missing_fetcher")

    def test_mock_get_posting_instructions(self):
        mock_account = self.contract_test.create_mock()
        fetcher_id = "pif"
        mock_savo = self.contract_test.create_sub_account_mock(
            mock_parent_account=mock_account,
            sub_account_id="sub_acc_id",
            sub_account_type="sub_acc_type",
            postings_interval_mapping={fetcher_id: sentinel.posting_instructions},
        )
        self.assertEqual(
            mock_savo.get_posting_instructions(fetcher_id=fetcher_id),
            sentinel.posting_instructions,
        )

        with self.assertRaises(ValueError):
            mock_savo.get_posting_instructions(fetcher_id="missing_fetcher")


class TestGetSubAccounts(TestCreateMockBase):
    def test_sub_accounts_dictionary_does_not_populate_on_missing_key_lookup(self):
        mock_account = self.contract_test.create_mock()
        self.assertIsInstance(mock_account.sub_accounts, dict)

        sub_account_mock = mock_account.sub_accounts["sub-acc-123"]
        self.assertIsNone(sub_account_mock)
        self.assertNotIn("sub-acc-123", mock_account.sub_accounts)

    def test_get_sub_accounts_no_filters_returns_all_sorted_by_id(self):
        mock_account = self.contract_test.create_mock()
        sa2 = self.contract_test.create_sub_account_mock(
            mock_parent_account=mock_account,
            sub_account_id="sub_account_2",
            sub_account_type="sub_account_type",
        )
        sa1 = self.contract_test.create_sub_account_mock(
            mock_parent_account=mock_account,
            sub_account_id="sub_account_1",
            sub_account_type="sub_account_type",
        )

        results = mock_account.get_sub_accounts()
        self.assertEqual(results, [sa1, sa2])

    def test_get_sub_accounts_filter_by_sub_account_types_union(self):
        mock_account = self.contract_test.create_mock()
        sa1 = self.contract_test.create_sub_account_mock(
            mock_parent_account=mock_account,
            sub_account_id="sub_account_1",
            sub_account_type="SAVE",
        )
        sa2 = self.contract_test.create_sub_account_mock(
            mock_parent_account=mock_account,
            sub_account_id="sub_account_2",
            sub_account_type="SPEND",
        )

        # Single type matches
        self.assertEqual(mock_account.get_sub_accounts(sub_account_types=["SAVE"]), [sa1])

        # Multiple types matches (union / OR within this list argument)
        self.assertEqual(
            mock_account.get_sub_accounts(sub_account_types=["SAVE", "SPEND"]), [sa1, sa2]
        )

        # Unmatched type raises KeyError
        with self.assertRaises(KeyError) as e:
            mock_account.get_sub_accounts(sub_account_types=["UNKNOWN"])
        self.assertIn(
            "sub_account_type 'UNKNOWN' is not present on any mock Sub-Account", str(e.exception)
        )

    def test_get_sub_accounts_filter_by_fetcher_ids_intersection(self):
        mock_account = self.contract_test.create_mock()
        sa1 = self.contract_test.create_sub_account_mock(
            mock_parent_account=mock_account,
            sub_account_id="sub_account_1",
            sub_account_type="SAVE",
            balances_observation_fetchers_mapping={"fetcher_a": sentinel.obs},
            client_transactions_mapping={"fetcher_b": sentinel.ctx},
        )

        sa2 = self.contract_test.create_sub_account_mock(
            mock_parent_account=mock_account,
            sub_account_id="sub_account_2",
            sub_account_type="SAVE",
            balances_observation_fetchers_mapping={"fetcher_a": sentinel.obs},
        )

        # Single fetcher ID matches
        self.assertEqual(mock_account.get_sub_accounts(fetcher_ids=["fetcher_a"]), [sa1, sa2])

        # Multiple fetcher IDs matches (intersection / AND within this list argument)
        self.assertEqual(
            mock_account.get_sub_accounts(fetcher_ids=["fetcher_a", "fetcher_b"]), [sa1]
        )

        # Unmatched fetcher ID raises KeyError
        with self.assertRaises(KeyError) as e:
            mock_account.get_sub_accounts(fetcher_ids=["fetcher_c"])
        self.assertIn(
            "fetcher_id 'fetcher_c' is not present on any mock Sub-Account", str(e.exception)
        )

    def test_get_sub_accounts_filter_by_invoked(self):
        mock_account = self.contract_test.create_mock()
        sa1 = self.contract_test.create_sub_account_mock(
            mock_parent_account=mock_account,
            sub_account_id="sub_account_1",
            sub_account_type="SAVE",
            invoked=True,
        )

        sa2 = self.contract_test.create_sub_account_mock(
            mock_parent_account=mock_account,
            sub_account_id="sub_account_2",
            sub_account_type="SAVE",
            invoked=False,
        )

        self.contract_test.create_sub_account_mock(
            mock_parent_account=mock_account,
            sub_account_id="sub_account_3",
            sub_account_type="SAVE",
            # Not setting invoked, should default to None
        )

        # Invoked matches
        self.assertEqual(mock_account.get_sub_accounts(invoked=True), [sa1])

        # Non-invoked matches
        self.assertEqual(mock_account.get_sub_accounts(invoked=False), [sa2])

    def test_get_sub_accounts_filter_combined_intersection(self):
        mock_account = self.contract_test.create_mock()
        sa1 = self.contract_test.create_sub_account_mock(
            mock_parent_account=mock_account,
            sub_account_id="sub_account_1",
            sub_account_type="SAVE",
            balances_observation_fetchers_mapping={"fetcher_a": sentinel.obs},
        )

        sa2 = self.contract_test.create_sub_account_mock(
            mock_parent_account=mock_account,
            sub_account_id="sub_account_2",
            sub_account_type="SAVE",
            balances_observation_fetchers_mapping={"fetcher_b": sentinel.obs},
            invoked=False,
        )

        sa3 = self.contract_test.create_sub_account_mock(
            mock_parent_account=mock_account,
            sub_account_id="sub_account_3",
            sub_account_type="SPEND",
            balances_observation_fetchers_mapping={"fetcher_b": sentinel.obs},
            invoked=True,
        )

        # SAVE & fetcher_a = sa1
        self.assertEqual(
            mock_account.get_sub_accounts(sub_account_types=["SAVE"], fetcher_ids=["fetcher_a"]),
            [sa1],
        )

        # SAVE & fetcher_b = sa2
        self.assertEqual(
            mock_account.get_sub_accounts(sub_account_types=["SAVE"], fetcher_ids=["fetcher_b"]),
            [sa2],
        )

        # SPEND & fetcher_a = empty list (intersection is empty)
        self.assertEqual(
            mock_account.get_sub_accounts(sub_account_types=["SPEND"], fetcher_ids=["fetcher_a"]),
            [],
        )

        # fetcher_b & invoked=True = sa3
        self.assertEqual(
            mock_account.get_sub_accounts(fetcher_ids=["fetcher_b"], invoked=True), [sa3]
        )

    def test_get_sub_accounts_dynamic_runtime_mutations(self):
        mock_account = self.contract_test.create_mock()
        sa1 = self.contract_test.create_sub_account_mock(
            mock_parent_account=mock_account,
            sub_account_id="sub_account_1",
            sub_account_type="SAVE",
            invoked=False,
        )

        self.assertEqual(mock_account.get_sub_accounts(invoked=False), [sa1])

        # Mutate at runtime
        sa1.invoked = True

        self.assertEqual(mock_account.get_sub_accounts(invoked=False), [])
        self.assertEqual(mock_account.get_sub_accounts(invoked=True), [sa1])
