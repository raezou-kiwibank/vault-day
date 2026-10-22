# standard libs
from datetime import datetime
from unittest import TestCase
from unittest.mock import MagicMock, patch, sentinel
from zoneinfo import ZoneInfo

# contracts api
from contracts_api import CalendarEvent, Tside,CalendarEvents

# inception sdk
from inception_sdk.test_framework.contracts.unit.common import ContractTest
from inception_sdk.test_framework.contracts.unit.supervisor.common import SupervisorContractTest


@patch.object(ContractTest, "create_mock")
class TestCreateSuperviseeMock(TestCase):
    def test_create_supervisee_mock_inserts_arg_if_missing(
        self, mocked_super_create_mock: MagicMock
    ):
        test_case = SupervisorContractTest()
        test_case.tside = Tside.ASSET

        test_case.create_supervisee_mock()
        mocked_super_create_mock.assert_called_once_with(
            supervisee_alias=None, supervisee_hook_result=None, is_supervisee_vault=True
        )

    def test_create_supervisee_mock_does_not_override_arg_if_present(
        self, mocked_super_create_mock: MagicMock
    ):
        test_case = SupervisorContractTest()
        test_case.tside = Tside.ASSET

        test_case.create_supervisee_mock(is_supervisee_vault=False)
        mocked_super_create_mock.assert_called_once_with(
            supervisee_alias=None, supervisee_hook_result=None, is_supervisee_vault=False
        )


class TestCreateSupervisorMock(TestCase):
    def test_create_supervisor_mock_defaults_plan_id_if_not_set(self):
        test_case = SupervisorContractTest()
        test_case.tside = Tside.ASSET

        supervisor_mock = test_case.create_supervisor_mock()
        self.assertEqual(supervisor_mock.plan_id, "MOCK_PLAN")

    def test_create_supervisor_mock_returns_plan_id_if_set(self):
        test_case = SupervisorContractTest()
        test_case.tside = Tside.ASSET

        supervisor_mock = test_case.create_supervisor_mock(plan_id="SOME_PLAN_ID")
        self.assertEqual(supervisor_mock.plan_id, "SOME_PLAN_ID")

    def test_create_supervisor_mock_returns_supervisees_if_set(self):
        test_case = SupervisorContractTest()
        test_case.tside = Tside.ASSET
        supervisees = {"alias_1": sentinel.vault_1, "alias_2": sentinel.vault_2}
        supervisor_mock = test_case.create_supervisor_mock(supervisees=supervisees)
        self.assertEqual(supervisor_mock.supervisees, supervisees)

    def test_create_supervisor_mock_returns_empty_supervisees_if_not_set(self):
        test_case = SupervisorContractTest()
        test_case.tside = Tside.ASSET

        supervisor_mock = test_case.create_supervisor_mock()
        self.assertDictEqual(supervisor_mock.supervisees, {})

    def test_create_supervisor_mock_get_plan_opening_datetime(self):
        test_case = SupervisorContractTest()
        test_case.tside = Tside.ASSET

        supervisor_mock = test_case.create_supervisor_mock(creation_date=sentinel.datetime)
        self.assertEqual(supervisor_mock.get_plan_opening_datetime(), sentinel.datetime)

    def test_create_supervisor_mock_get_plan_opening_datetime_default(self):
        test_case = SupervisorContractTest()
        test_case.tside = Tside.ASSET

        supervisor_mock = test_case.create_supervisor_mock()
        self.assertEqual(
            supervisor_mock.get_plan_opening_datetime(),
            datetime(2019, 1, 1, tzinfo=ZoneInfo("UTC")),
        )

    def test_create_supervisor_get_hook_execution_id(self):
        test_case = SupervisorContractTest()
        test_case.tside = Tside.ASSET

        supervisor_mock = test_case.create_supervisor_mock()
        self.assertEqual(supervisor_mock.get_hook_execution_id(), "MOCK_HOOK")

    def test_create_supervisor_get_calendar_events_returns_none(self):
        test_case = SupervisorContractTest()
        test_case.tside = Tside.ASSET

        supervisor_mock = test_case.create_supervisor_mock()
        self.assertIsNone(supervisor_mock.get_calendar_events(calendar_ids=["some_calendar"]))

    def test_create_supervisor_get_calendar_events_returns_calendar_events(self):
        test_case = SupervisorContractTest()
        test_case.tside = Tside.ASSET
        start_datetime = datetime(2019, 1, 1, tzinfo=ZoneInfo("UTC"))
        end_datetime = datetime(2019, 1, 2, tzinfo=ZoneInfo("UTC"))

        supervisor_mock = test_case.create_supervisor_mock(
            calendar_events=[
                CalendarEvent(
                    id="1",
                    calendar_id="some_calendar",
                    start_datetime=start_datetime,
                    end_datetime=end_datetime,
                ),
                CalendarEvent(
                    id="2",
                    calendar_id="another_calendar",
                    start_datetime=start_datetime,
                    end_datetime=end_datetime,
                ),
                CalendarEvent(
                    id="3",
                    calendar_id="another_calendar?!",
                    start_datetime=start_datetime,
                    end_datetime=end_datetime,
                ),
            ]
        )
        expected = CalendarEvents(
            calendar_events=[
                CalendarEvent(
                    id="1",
                    calendar_id="some_calendar",
                    start_datetime=start_datetime,
                    end_datetime=end_datetime,
                ),
                CalendarEvent(
                    id="2",
                    calendar_id="another_calendar",
                    start_datetime=start_datetime,
                    end_datetime=end_datetime,
                ),
            ]
        )
        result = supervisor_mock.get_calendar_events(
            calendar_ids=["some_calendar", "another_calendar"]
        )
        self.assertEqual(len(result), len(expected))
        for index, event in enumerate(result):
            self.assertEqual(event, expected[index])
