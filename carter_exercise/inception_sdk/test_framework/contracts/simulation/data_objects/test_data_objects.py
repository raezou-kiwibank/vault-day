# standard libs
from datetime import datetime, timezone
from unittest import TestCase
from unittest.mock import sentinel

# inception sdk
import inception_sdk.test_framework.contracts.simulation.data_objects.data_objects as data_objects


class TestExpectedSchedules(TestCase):
    def test_expected_schedule_with_account_id_and_plan_id_raises(self):
        with self.assertRaises(ValueError):
            data_objects.ExpectedSchedule(
                run_times=[datetime(2020, 1, 2)],
                event_id="my_event",
                account_id="my_account",
                plan_id="my_plan",
            )

    def test_expected_schedule_with_no_resource_ids_raises(self):
        with self.assertRaises(ValueError):
            data_objects.ExpectedSchedule(
                run_times=[datetime(2020, 1, 2)],
                event_id="my_event",
            )

    def test_expected_schedule_with_one_id_ok(self):
        data_objects.ExpectedSchedule(
            run_times=[datetime(2020, 1, 2)], event_id="my_event", account_id="my_account"
        )


class TestSimulationTestScenario(TestCase):
    def test_contract_errors_with_v1_accounts(self):
        with self.assertRaises(ValueError) as ctx:
            start = sentinel.start
            end = sentinel.end
            use_v1_accounts = True
            sub_tests = [
                data_objects.SubTest(
                    description=sentinel.description,
                    expected_contract_errors=[sentinel.contract_error],
                )
            ]
            data_objects.SimulationTestScenario(
                sub_tests=sub_tests, start=start, end=end, use_v1_accounts=use_v1_accounts
            )
        self.assertIn("Contract Errors are not supported for v1 Accounts.", str(ctx.exception))

    def test_v1_accounts_with_expected_activation_rejections(self):
        with self.assertRaises(ValueError) as ctx:
            start = sentinel.start
            end = sentinel.end
            use_v1_accounts = True
            sub_tests = [
                data_objects.SubTest(
                    description=sentinel.description,
                    expected_account_activation_rejections=[sentinel.activation_rejection],
                )
            ]
            data_objects.SimulationTestScenario(
                sub_tests=sub_tests, start=start, end=end, use_v1_accounts=use_v1_accounts
            )
        self.assertIn(
            "The following features are not supported for v1 Accounts: "
            "Account Activation Rejections, "
            "Account Conversion Rejections, "
            "Account Deactivation Rejections.",
            str(ctx.exception),
        )

    def test_v1_accounts_with_expected_conversion_rejections(self):
        with self.assertRaises(ValueError) as ctx:
            start = sentinel.start
            end = sentinel.end
            use_v1_accounts = True
            sub_tests = [
                data_objects.SubTest(
                    description=sentinel.description,
                    expected_account_conversion_rejections=[sentinel.conversion_rejection],
                )
            ]
            data_objects.SimulationTestScenario(
                sub_tests=sub_tests, start=start, end=end, use_v1_accounts=use_v1_accounts
            )
        self.assertIn(
            "The following features are not supported for v1 Accounts: "
            "Account Activation Rejections, "
            "Account Conversion Rejections, "
            "Account Deactivation Rejections.",
            str(ctx.exception),
        )

    def test_v1_accounts_with_expected_deactivation_rejections(self):
        with self.assertRaises(ValueError) as ctx:
            start = sentinel.start
            end = sentinel.end
            use_v1_accounts = True
            sub_tests = [
                data_objects.SubTest(
                    description=sentinel.description,
                    expected_account_deactivation_rejections=[sentinel.deactivation_rejection],
                )
            ]
            data_objects.SimulationTestScenario(
                sub_tests=sub_tests, start=start, end=end, use_v1_accounts=use_v1_accounts
            )
        self.assertIn(
            "The following features are not supported for v1 Accounts: "
            "Account Activation Rejections, "
            "Account Conversion Rejections, "
            "Account Deactivation Rejections.",
            str(ctx.exception),
        )


class TestExpectedSubAccountEvents(TestCase):
    def test_sub_account_create_with_account_event_pattern(self):
        event = data_objects.ExpectedSubAccountCreateWithAccountEvent(
            timestamp=datetime(2019, 1, 31, tzinfo=timezone.utc),
            parent_account_id="parent_acc_1",
            sub_account_id="sub_acc_1",
        )
        pattern = event.expected_log_pattern

        self.assertTrue(
            pattern.search('created account "parent_acc_1" created sub-accounts ["sub_acc_1"]')
        )
        self.assertTrue(
            pattern.search(
                'created account "parent_acc_1" created sub-accounts ["sub_acc_1", "sub_acc_2"]'
            )
        )
        self.assertTrue(
            pattern.search(
                'created account "parent_acc_1" created sub-accounts '
                '["sub_acc_0", "sub_acc_1", "sub_acc_2"]'
            )
        )

        self.assertFalse(
            pattern.search('created account "wrong_parent" created sub-accounts ["sub_acc_1"]')
        )
        self.assertFalse(
            pattern.search('created account "parent_acc_1" created sub-accounts ["wrong_sub"]')
        )

    def test_sub_account_create_after_account_event_pattern(self):
        event = data_objects.ExpectedSubAccountCreateAfterAccountEvent(
            timestamp=datetime(2019, 1, 31, tzinfo=timezone.utc),
            parent_account_id="parent_acc_1",
            sub_account_id="sub_acc_1",
        )
        pattern = event.expected_log_pattern

        self.assertTrue(pattern.search("created sub-account sub_acc_1 for account parent_acc_1"))

        self.assertFalse(pattern.search("created sub-account wrong_sub for account parent_acc_1"))
        self.assertFalse(pattern.search("created sub-account sub_acc_1 for account wrong_parent"))
