# Copyright @ 2024 Thought Machine Group Limited. All rights reserved.
# standard libs
from datetime import datetime, timezone
from unittest import TestCase
from unittest.mock import Mock, sentinel

# third party
from semantic_version import Version

# inception sdk
import inception_sdk.test_framework.contracts.simulation.errors as sim_errors
from inception_sdk.test_framework.contracts.simulation.data_objects.data_objects import (
    ExpectedAccountViolation,
    ExpectedContractError,
    ExpectedContractViolation,
    ExpectedPostingViolation,
    ExpectedRejection,
    ExpectedSchedule,
)
from inception_sdk.test_framework.contracts.simulation.utils import (
    SimulationTestCase,
    SimulationTestScenario,
    SubTest,
    compile_chrono_events,
    get_calendar_created,
    get_calendar_event_created,
)
from inception_sdk.test_framework.contracts.simulation.vault_caller import VaultException


class TestVaultVersionAttribute(TestCase):
    def test_vault_version_attribute(self):
        test_case = SimulationTestCase()
        SimulationTestCase.client = Mock(
            get_vault_version=Mock(
                return_value=[
                    {
                        "version": {
                            "major": 1,
                            "minor": 2,
                            "patch": 3,
                        },
                    }
                ]
            )
        )

        # run function
        test_case.load_vault_version()
        self.assertEqual(test_case.vault_version, Version("1.2.3"))


class TestCheckParameterChangeRejections(TestCase):
    def test_check_parameter_change_rejections_match_pre_v5(self):
        test_case = SimulationTestCase()
        test_case.vault_version = Version("4.0.0")

        self.assertIsNone(
            test_case.check_parameter_change_rejections(
                expected_rejections=[
                    ExpectedRejection(
                        timestamp=datetime(2019, 3, 5, tzinfo=timezone.utc),
                        rejection_type="dummy_rejection_type",
                        rejection_reason="dummy_rejection_reason",
                    )
                ],
                logs_with_timestamp={
                    datetime(2019, 3, 5, tzinfo=timezone.utc): [
                        "account parameters update rejected: dummy_rejection_reason"
                    ]
                },
            )
        )

    def test_check_parameter_change_rejections_match_partially_pre_v5(self):
        test_case = SimulationTestCase()
        test_case.vault_version = Version("4.0.0")

        self.assertIsNone(
            test_case.check_parameter_change_rejections(
                expected_rejections=[
                    ExpectedRejection(
                        timestamp=datetime(2019, 3, 5, tzinfo=timezone.utc),
                        rejection_type="dummy_rejection_type",
                        rejection_reason="dummy_rejection_reason",
                    )
                ],
                logs_with_timestamp={
                    datetime(2019, 3, 5, tzinfo=timezone.utc): [
                        "account parameters update rejected: dummy_rejection_reason and more"
                    ]
                },
            )
        )

    def test_check_parameter_change_rejections_match_v5_0_0(self):
        test_case = SimulationTestCase()
        test_case.vault_version = Version("5.0.0")

        self.assertIsNone(
            test_case.check_parameter_change_rejections(
                expected_rejections=[
                    ExpectedRejection(
                        timestamp=datetime(2019, 3, 5, tzinfo=timezone.utc),
                        rejection_type="dummy_rejection_type",
                        rejection_reason="dummy_rejection_reason",
                    )
                ],
                logs_with_timestamp={
                    datetime(2019, 3, 5, tzinfo=timezone.utc): [
                        'account parameters update rejected for account "Main account": '
                        "dummy_rejection_reason"
                    ]
                },
            )
        )

    def test_check_parameter_change_rejections_match_partially_v5_0_0(self):
        test_case = SimulationTestCase()
        test_case.vault_version = Version("5.0.0")

        self.assertIsNone(
            test_case.check_parameter_change_rejections(
                expected_rejections=[
                    ExpectedRejection(
                        timestamp=datetime(2019, 3, 5, tzinfo=timezone.utc),
                        rejection_type="dummy_rejection_type",
                        rejection_reason="dummy_rejection_reason",
                    )
                ],
                logs_with_timestamp={
                    datetime(2019, 3, 5, tzinfo=timezone.utc): [
                        'account parameters update rejected for account "Main account": '
                        "dummy_rejection_reason and more"
                    ]
                },
            )
        )

    def test_check_parameter_change_rejections_match_v5_1_0(self):
        test_case = SimulationTestCase()
        test_case.vault_version = Version("5.1.0")

        self.assertIsNone(
            test_case.check_parameter_change_rejections(
                expected_rejections=[
                    ExpectedRejection(
                        timestamp=datetime(2019, 3, 5, tzinfo=timezone.utc),
                        rejection_type="dummy_rejection_type",
                        rejection_reason="dummy_rejection_reason",
                    )
                ],
                logs_with_timestamp={
                    datetime(2019, 3, 5, tzinfo=timezone.utc): [
                        'account parameters update rejected for account "Main account": rejection'
                        ' type "dummy_rejection_type" and reason "dummy_rejection_reason"'
                    ]
                },
            )
        )

    def test_check_parameter_change_rejections_match_partially_v5_1_0(self):
        test_case = SimulationTestCase()
        test_case.vault_version = Version("5.1.0")

        self.assertIsNone(
            test_case.check_parameter_change_rejections(
                expected_rejections=[
                    ExpectedRejection(
                        timestamp=datetime(2019, 3, 5, tzinfo=timezone.utc),
                        rejection_type="dummy_rejection_type",
                        rejection_reason="dummy_rejection_reason",
                    )
                ],
                logs_with_timestamp={
                    datetime(2019, 3, 5, tzinfo=timezone.utc): [
                        'account parameters update rejected for account "Main account": rejection'
                        ' type "dummy_rejection_type" and reason "dummy_rejection_reason and more"'
                    ]
                },
            )
        )

    def test_check_parameter_change_rejections_different_reason_no_match(self):
        test_case = SimulationTestCase()
        test_case.vault_version = Version("4.6.0")

        test_rejection = ExpectedRejection(
            timestamp=datetime(2019, 3, 5, tzinfo=timezone.utc),
            rejection_type="dummy_rejection_type",
            rejection_reason="dummy_rejection_reason",
        )
        with self.assertRaises(AssertionError) as ctx:
            test_case.check_parameter_change_rejections(
                expected_rejections=[test_rejection],
                logs_with_timestamp={
                    datetime(2019, 3, 5, tzinfo=timezone.utc): [
                        "account parameters update rejected: other_rejection_reason"
                    ]
                },
            )
        self.assertIn(
            f"expected values not found: {[test_rejection]}",
            str(ctx.exception),
        )

    def test_check_parameter_change_rejections_different_date_no_match(self):
        test_case = SimulationTestCase()
        test_case.vault_version = Version("4.6.0")

        test_rejection = ExpectedRejection(
            timestamp=datetime(2019, 3, 5, tzinfo=timezone.utc),
            rejection_type="dummy_rejection_type",
            rejection_reason="dummy_rejection_reason",
        )
        with self.assertRaises(AssertionError) as ctx:
            test_case.check_parameter_change_rejections(
                expected_rejections=[test_rejection],
                logs_with_timestamp={
                    datetime(2019, 3, 5, 1, tzinfo=timezone.utc): [
                        "account parameters update rejected: dummy_rejection_reason"
                    ]
                },
            )
        self.assertIn(
            f"expected values not found: {[test_rejection]}",
            str(ctx.exception),
        )


class TestCheckContractErrors(TestCase):
    def test_expected_contract_error(self):
        test_case = SimulationTestCase()
        test_case.vault_version = Version("5.5.0")

        account_id = sentinel.account_id
        exception_type = sentinel.exception_type

        self.assertIsNone(
            test_case.check_contract_errors(
                expected_contract_errors=[
                    ExpectedContractError(
                        timestamp=sentinel.timestamp,
                        account_id=account_id,
                        exception_type=exception_type,
                    )
                ],
                logs_with_timestamp={
                    sentinel.timestamp: [
                        "processing create account v2 instruction: activation "
                        "hook raised an exception: violations[{violation_type:"
                        "EXCEPTION_RAISED_BY_SMART_CONTRACT, metadata: "
                        f"map[account.id:{account_id}  exception_args:"
                        "[<class 'decimal.ConversionSyntax'>]"
                        f"exception_type:{exception_type} smart_contract_version.id:0"
                        "stack_trace:File contract, line 15, in activation_hook]}]"
                    ]
                },
            )
        )

    def test_unexpected_contract_error_raises_error(self):
        test_case = SimulationTestCase()
        test_case.vault_version = Version("5.5.0")

        account_id = sentinel.account_id
        exception_type = sentinel.exception_type
        unexpected_exception_type = sentinel.unexpected_exception_type
        test_contract_error = ExpectedContractError(
            timestamp=sentinel.timestamp,
            account_id=account_id,
            exception_type=exception_type,
        )
        with self.assertRaises(AssertionError) as ctx:
            test_case.check_contract_errors(
                expected_contract_errors=[test_contract_error],
                logs_with_timestamp={
                    sentinel.timestamp: [
                        "processing create account v2 instruction: activation "
                        "hook raised an exception: violations[{violation_type:"
                        "EXCEPTION_RAISED_BY_SMART_CONTRACT, metadata: "
                        f"map[account.id:{account_id}  exception_args:"
                        "[<class 'decimal.ConversionSyntax'>]"
                        f"exception_type:{unexpected_exception_type} smart_contract_version.id:0"
                        "stack_trace:File contract, line 15, in activation_hook]}]"
                    ]
                },
            )
        self.assertIn(
            f"expected values not found: {[[test_contract_error]]}",
            str(ctx.exception),
        )


class TestCheckAccountActivationRejections(TestCase):
    def test_expected_activation_rejections_found(self):
        test_case = SimulationTestCase()
        test_case.vault_version = Version("5.5.0")

        resource_id = sentinel.account_id
        rejection_type = sentinel.rejection_type
        rejection_reason = sentinel.rejection_reason

        self.assertIsNone(
            test_case.check_account_activation_rejections(
                expected_rejections=[
                    ExpectedRejection(
                        timestamp=sentinel.timestamp,
                        rejection_type=rejection_type,
                        rejection_reason=rejection_reason,
                        account_id=resource_id,
                    )
                ],
                logs_with_timestamp={
                    sentinel.timestamp: [
                        f"processing create account v2 instruction: activation hook "
                        f"returned a rejection: violations[{{violation_type: "
                        f"CHANGE_REJECTED_BY_CONTRACT, metadata: map[rejection_message:"
                        f"{rejection_reason} rejection_type:{rejection_type}]}}]"
                    ]
                },
            )
        )

    def test_expected_activation_rejections_not_found(self):
        test_case = SimulationTestCase()
        test_case.vault_version = Version("5.5.0")
        resource_id = sentinel.account_id
        rejection_type = sentinel.rejection_type
        rejection_reason = sentinel.rejection_reason

        test_rejection = ExpectedRejection(
            timestamp=sentinel.timestamp,
            rejection_type=rejection_type,
            rejection_reason=rejection_reason,
            account_id=resource_id,
        )

        with self.assertRaises(AssertionError) as ctx:
            test_case.check_account_activation_rejections(
                expected_rejections=[test_rejection],
                logs_with_timestamp={
                    sentinel.timestamp: [
                        f"processing create account v2 instruction: activation hook "
                        f"returned a rejection: violations[{{violation_type: "
                        f"CHANGE_REJECTED_BY_CONTRACT, metadata: map[rejection_message:"
                        f"{rejection_reason} rejection_type:"
                        f"{sentinel.unexpected_rejection_type}]}}]"
                    ]
                },
            )
        self.assertIn(
            f"expected values not found: {[test_rejection]}",
            str(ctx.exception),
        )


class TestCheckAccountConversionRejections(TestCase):
    def test_expected_conversion_rejections_found(self):
        test_case = SimulationTestCase()
        test_case.vault_version = Version("5.5.0")

        resource_id = sentinel.account_id
        rejection_type = sentinel.rejection_type
        rejection_reason = sentinel.rejection_reason

        self.assertIsNone(
            test_case.check_account_conversion_rejections(
                expected_rejections=[
                    ExpectedRejection(
                        timestamp=sentinel.timestamp,
                        rejection_type=rejection_type,
                        rejection_reason=rejection_reason,
                        account_id=resource_id,
                    )
                ],
                logs_with_timestamp={
                    sentinel.timestamp: [
                        f"processing update account v2 instruction: conversion hook "
                        f"returned a rejection: violations[{{violation_type: "
                        f"CHANGE_REJECTED_BY_CONTRACT, metadata: map[rejection_message:"
                        f"{rejection_reason} rejection_type:{rejection_type}]}}]"
                    ]
                },
            )
        )

    def test_expected_conversion_rejections_not_found(self):
        test_case = SimulationTestCase()
        test_case.vault_version = Version("5.5.0")

        resource_id = sentinel.account_id
        rejection_type = sentinel.rejection_type
        rejection_reason = sentinel.rejection_reason

        expected_rejection = ExpectedRejection(
            timestamp=sentinel.timestamp,
            rejection_type=rejection_type,
            rejection_reason=rejection_reason,
            account_id=resource_id,
        )
        with self.assertRaises(AssertionError) as ctx:
            test_case.check_account_conversion_rejections(
                expected_rejections=[expected_rejection],
                logs_with_timestamp={
                    sentinel.timestamp: [
                        f"processing update account v2 instruction: conversion hook "
                        f"returned a rejection: violations[{{violation_type: "
                        f"CHANGE_REJECTED_BY_CONTRACT, metadata: map[rejection_message:"
                        f"{rejection_reason} rejection_type:"
                        f"{sentinel.unexpected_rejection_type}]}}]"
                    ]
                },
            )
        self.assertIn(f"expected values not found: {[expected_rejection]}", str(ctx.exception))


class TestCheckAccountDeactivationRejections(TestCase):
    def test_expected_deactivation_rejections_found(self):
        test_case = SimulationTestCase()
        test_case.vault_version = Version("5.5.0")

        resource_id = sentinel.account_id
        rejection_type = sentinel.rejection_type
        rejection_reason = sentinel.rejection_reason

        self.assertIsNone(
            test_case.check_account_deactivation_rejections(
                expected_rejections=[
                    ExpectedRejection(
                        timestamp=sentinel.timestamp,
                        rejection_type=rejection_type,
                        rejection_reason=rejection_reason,
                        account_id=resource_id,
                    )
                ],
                logs_with_timestamp={
                    sentinel.timestamp: [
                        f"processing update account v2 instruction: deactivation hook "
                        f"returned a rejection: violations[{{violation_type: "
                        f"CHANGE_REJECTED_BY_CONTRACT, metadata: map[rejection_message:"
                        f"{rejection_reason} rejection_type:{rejection_type}]}}]"
                    ]
                },
            )
        )

    def test_expected_deactivation_rejections_not_found(self):
        test_case = SimulationTestCase()
        test_case.vault_version = Version("5.5.0")

        resource_id = sentinel.account_id
        rejection_type = sentinel.rejection_type
        rejection_reason = sentinel.rejection_reason

        expected_rejection = ExpectedRejection(
            timestamp=sentinel.timestamp,
            rejection_type=rejection_type,
            rejection_reason=rejection_reason,
            account_id=resource_id,
        )
        with self.assertRaises(AssertionError) as ctx:
            test_case.check_account_conversion_rejections(
                expected_rejections=[expected_rejection],
                logs_with_timestamp={
                    sentinel.timestamp: [
                        f"processing update account v2 instruction: deactivation hook "
                        f"returned a rejection: violations[{{violation_type: "
                        f"CHANGE_REJECTED_BY_CONTRACT, metadata: map[rejection_message:"
                        f"{rejection_reason} rejection_type:"
                        f"{sentinel.unexpected_rejection_type}]}}]"
                    ]
                },
            )
        self.assertIn(f"expected values not found: {[expected_rejection]}", str(ctx.exception))


class TestCheckPostingRejections(TestCase):
    def test_expected_posting_rejections_with_account_id(self):
        test_case = SimulationTestCase()
        test_case.vault_version = Version("5.2.0")

        resource_type = "account"
        resource_id = sentinel.account_id
        rejection_type = sentinel.rejection_type
        rejection_reason = sentinel.rejection_reason

        self.assertIsNone(
            test_case.check_posting_rejections(
                expected_rejections=[
                    ExpectedRejection(
                        timestamp=sentinel.timestamp,
                        rejection_type=rejection_type,
                        rejection_reason=rejection_reason,
                        account_id=resource_id,
                    )
                ],
                logs_with_timestamp={
                    sentinel.timestamp: [
                        f'{resource_type} "{resource_id}" rejected with rejection type '
                        f'"{rejection_type}" and reason "{rejection_reason}"'
                    ]
                },
            )
        )

    def test_expected_posting_rejections_with_plan_id(self):
        test_case = SimulationTestCase()
        test_case.vault_version = Version("5.2.0")

        resource_type = "plan"
        resource_id = sentinel.plan_id
        rejection_type = sentinel.rejection_type
        rejection_reason = sentinel.rejection_reason

        self.assertIsNone(
            test_case.check_posting_rejections(
                expected_rejections=[
                    ExpectedRejection(
                        timestamp=sentinel.timestamp,
                        rejection_type=rejection_type,
                        rejection_reason=rejection_reason,
                        plan_id=resource_id,
                    )
                ],
                logs_with_timestamp={
                    sentinel.timestamp: [
                        f'{resource_type} "{resource_id}" rejected with rejection type '
                        f'"{rejection_type}" and reason "{rejection_reason}"'
                    ]
                },
            )
        )

    def test_expected_posting_rejections_with_neither_account_or_plan_id(self):
        test_case = SimulationTestCase()
        test_case.vault_version = Version("5.2.0")

        resource_type = "account"
        # Defaults to Main account
        resource_id = "Main account"
        rejection_type = sentinel.rejection_type
        rejection_reason = sentinel.rejection_reason

        self.assertIsNone(
            test_case.check_posting_rejections(
                expected_rejections=[
                    ExpectedRejection(
                        timestamp=sentinel.timestamp,
                        rejection_type=rejection_type,
                        rejection_reason=rejection_reason,
                    )
                ],
                logs_with_timestamp={
                    sentinel.timestamp: [
                        f'{resource_type} "{resource_id}" rejected with rejection type '
                        f'"{rejection_type}" and reason "{rejection_reason}"'
                    ]
                },
            )
        )

    def test_expected_posting_rejections_not_found(self):
        test_case = SimulationTestCase()
        test_case.vault_version = Version("5.2.0")

        resource_id = sentinel.account_id
        rejection_type = sentinel.rejection_type
        rejection_reason = sentinel.rejection_reason

        test_rejection = ExpectedRejection(
            timestamp=sentinel.timestamp,
            rejection_type=rejection_type,
            rejection_reason=rejection_reason,
            account_id=resource_id,
        )
        with self.assertRaises(AssertionError) as ctx:
            test_case.check_posting_rejections(
                expected_rejections=[test_rejection],
                # plan id returned in 5.2.0 in some instances
                # so expected rejection with account here is not found
                logs_with_timestamp={
                    sentinel.timestamp: [
                        f'plan "{sentinel.plan_id}" rejected with rejection type '
                        f'"{rejection_type}" and reason "{rejection_reason}"'
                    ]
                },
            )
        self.assertIn(
            f"expected values not found: {[test_rejection]}",
            str(ctx.exception),
        )

    def test_expected_posting_rejections_with_plan_id_raises_error_pre_v5_2_0(self):
        test_scenario = SimulationTestScenario(
            start=sentinel.start,
            end=sentinel.end,
            sub_tests=[
                SubTest(
                    description=sentinel.description,
                    expected_posting_rejections=[
                        ExpectedRejection(
                            timestamp=sentinel.timestamp,
                            rejection_type=sentinel.rejection_type,
                            rejection_reason=sentinel.rejection_reason,
                            plan_id=sentinel.resource_id,
                        )
                    ],
                ),
            ],
        )

        with self.assertRaises(ValueError) as value_error:
            compile_chrono_events(
                test_scenario=test_scenario, setup_events=[], vault_version=Version("4.6.10")
            )

        self.assertEqual(
            value_error.exception.args[0],
            "Prior to Vault 5.2.0 expected posting rejections must be made against the "
            "account_id instead of plan_id.",
        )

    def test_expected_posting_rejections_with_partial_rejection_reason_match(self):
        test_case = SimulationTestCase()
        test_case.vault_version = Version("5.2.0")

        resource_type = "account"
        resource_id = sentinel.account_id
        rejection_type = sentinel.rejection_type
        rejection_reason = sentinel.rejection_reason

        self.assertIsNone(
            test_case.check_posting_rejections(
                expected_rejections=[
                    ExpectedRejection(
                        timestamp=sentinel.timestamp,
                        rejection_type=rejection_type,
                        rejection_reason=rejection_reason,
                        account_id=resource_id,
                    )
                ],
                logs_with_timestamp={
                    sentinel.timestamp: [
                        f'{resource_type} "{resource_id}" rejected with rejection type '
                        f'"{rejection_type}" and reason "{rejection_reason} and some extra text"'
                    ]
                },
            )
        )


class TestDataObjects(TestCase):
    def test_expected_rejection_with_account_and_plan_id_raises_error(self):
        with self.assertRaises(ValueError) as value_error:
            ExpectedRejection(
                timestamp=sentinel.timestamp,
                rejection_type=sentinel.rejection_type,
                rejection_reason=sentinel.rejection_reason,
                account_id=sentinel.account_id,
                plan_id=sentinel.resource_id,
            )

        self.assertEqual(
            value_error.exception.args[0],
            "The account_id and plan_id cannot both be set on ExpectedRejection("
            "timestamp=sentinel.timestamp, rejection_type=sentinel.rejection_type, "
            "rejection_reason=sentinel.rejection_reason, account_id=sentinel.account_id, "
            "plan_id=sentinel.resource_id). See ExpectedRejection docstring for more details.",
        )


class TestSimulationErrorHandling(TestCase):
    def test_no_error(self):
        sim_test_case = SimulationTestCase()
        sim_test_case.vault_version = Version("1.0.0")

        self.assertIsNone(
            sim_test_case.check_simulation_error(
                actual_error=None,
                expected_error=None,
            )
        )

    def test_unexpected_error(self):
        sim_test_case = SimulationTestCase()

        with self.assertRaisesRegex(
            AssertionError, r"^expected values not found: {'expected': 'None', 'actual': "
        ):
            sim_test_case.check_simulation_error(
                actual_error=sim_errors.DeactivationFailure(
                    account_id=sentinel.account_id,
                    reason_suffix=sentinel.suffix,
                ),
                expected_error=None,
            )

    def test_unexpected_error_types(self):
        sim_test_case = SimulationTestCase()

        with self.assertRaises(
            AssertionError,
        ) as ctx:
            sim_test_case.check_simulation_error(
                actual_error=ValueError("actual"),
                expected_error=KeyError("expected"),
            )
        self.assertEqual(
            ctx.exception.args[0],
            "expected values not found: {'expected': \"KeyError('expected')\", "
            "'actual': \"ValueError('actual')\"}",
        )

    def test_expected_error_not_raised(self):
        sim_test_case = SimulationTestCase()

        with self.assertRaises(
            AssertionError,
        ) as ctx:
            sim_test_case.check_simulation_error(
                actual_error=None,
                expected_error=sim_errors.DeactivationFailure(
                    account_id=sentinel.account_id,
                    reason_suffix=sentinel.suffix,
                ),
            )
        self.assertEqual(
            ctx.exception.args[0],
            "expected values not found: {'expected': 'VaultException(vault_error_code=014.005.000, "
            "message=failed to run deactivation hook for account "
            "\"sentinel.account_id\": sentinel.suffix, details=[])', 'actual': 'None'}",
        )

    def test_deactivation_error(self):
        sim_test_case = SimulationTestCase()

        actual_error = VaultException(
            vault_error_code="014.005.000",
            message=(
                'failed to run deactivation hook for account "sentinel.account_id": sentinel.suffix'
            ),
        )

        expected_error = sim_errors.DeactivationFailure(
            account_id=sentinel.account_id,
            reason_suffix=sentinel.suffix,
        )

        self.assertIsNone(
            sim_test_case.check_simulation_error(
                actual_error=actual_error,
                expected_error=expected_error,
            )
        )

    def test_missing_param_value(self):
        sim_test_case = SimulationTestCase()

        actual_error = VaultException(
            vault_error_code="014.005.000",
            message=(
                "value was not provided for non-derived, non-optional instance parameter with name "
                '"sentinel.param_name"'
            ),
        )
        expected_error = sim_errors.MissingInstanceParameterValue(param=sentinel.param_name)

        self.assertIsNone(
            sim_test_case.check_simulation_error(
                actual_error=actual_error, expected_error=expected_error
            )
        )

    def test_non_existent_param(self):
        sim_test_case = SimulationTestCase()

        actual_error = VaultException(
            vault_error_code="014.005.000",
            message=(
                'non-derived instance parameter with name "sentinel.param_name" does not exist '
                "- cannot set value"
            ),
        )
        expected_error = sim_errors.AccountCreatedWithNonExistentInstanceParameter(
            param=sentinel.param_name
        )

        self.assertIsNone(
            sim_test_case.check_simulation_error(
                actual_error=actual_error, expected_error=expected_error
            )
        )


class TestExpectedSchedules(TestCase):
    def test_plan_schedules(self):
        test_case = SimulationTestCase()

        self.assertIsNone(
            test_case.check_schedule_processed(
                expected_schedule_runs=[
                    ExpectedSchedule(
                        run_times=[datetime(2019, 3, 5, 1, 2, 3, tzinfo=timezone.utc)],
                        plan_id="my_plan",
                        event_id="my_event",
                    )
                ],
                res=[
                    {
                        "result": {
                            "timestamp": "2019-03-05T01:02:03Z",
                            "logs": ['processed scheduled event "my_event" for plan "my_plan"'],
                            "posting_instruction_batches": [],
                            "balances": {},
                            "account_notes": {},
                            "instantiate_workflow_requests": {},
                            "derived_params": {},
                        }
                    }
                ],
            )
        )

    def test_plan_schedules_with_overrides(self):
        test_case = SimulationTestCase()

        self.assertIsNone(
            test_case.check_schedule_processed(
                expected_schedule_runs=[
                    ExpectedSchedule(
                        run_times=[datetime(2019, 3, 5, 1, 2, 3, tzinfo=timezone.utc)],
                        plan_id="my_plan",
                        event_id="my_event",
                    )
                ],
                res=[
                    {
                        "result": {
                            "timestamp": "2019-03-05T01:02:03Z",
                            "logs": [
                                'processed scheduled event "my_event" for plan "my_plan" which '
                                "overrides events for accounts [account_1, account_2]"
                            ],
                            "posting_instruction_batches": [],
                            "balances": {},
                            "account_notes": {},
                            "instantiate_workflow_requests": {},
                            "derived_params": {},
                        }
                    }
                ],
            )
        )

    def test_account_schedules(self):
        test_case = SimulationTestCase()

        self.assertIsNone(
            test_case.check_schedule_processed(
                expected_schedule_runs=[
                    ExpectedSchedule(
                        run_times=[datetime(2019, 3, 5, 1, 2, 3, tzinfo=timezone.utc)],
                        account_id="my_account",
                        event_id="my_event",
                    )
                ],
                res=[
                    {
                        "result": {
                            "timestamp": "2019-03-05T01:02:03Z",
                            "logs": [
                                'processed scheduled event "my_event" for account "my_account"'
                            ],
                            "posting_instruction_batches": [],
                            "balances": {},
                            "account_notes": {},
                            "instantiate_workflow_requests": {},
                            "derived_params": {},
                        }
                    }
                ],
            )
        )

    def test_account_schedules_with_count(self):
        test_case = SimulationTestCase()

        self.assertIsNone(
            test_case.check_schedule_processed(
                expected_schedule_runs=[
                    ExpectedSchedule(
                        run_times=[], account_id="my_account", event_id="my_event", count=1
                    )
                ],
                res=[
                    {
                        "result": {
                            "timestamp": "2019-03-05T01:02:03Z",
                            "logs": [
                                'processed scheduled event "my_event" for account "my_account"'
                            ],
                            "posting_instruction_batches": [],
                            "balances": {},
                            "account_notes": {},
                            "instantiate_workflow_requests": {},
                            "derived_params": {},
                        }
                    }
                ],
            )
        )

    def test_multiple_schedules(self):
        test_case = SimulationTestCase()

        self.assertIsNone(
            test_case.check_schedule_processed(
                expected_schedule_runs=[
                    ExpectedSchedule(
                        run_times=[
                            datetime(2019, 3, 5, 1, 2, 3, tzinfo=timezone.utc),
                            datetime(2019, 3, 6, 1, 2, 3, tzinfo=timezone.utc),
                        ],
                        account_id="my_account",
                        event_id="my_event",
                    ),
                    ExpectedSchedule(
                        run_times=[datetime(2019, 3, 7, 1, 2, 3, tzinfo=timezone.utc)],
                        plan_id="my_plan",
                        event_id="my_event",
                    ),
                ],
                res=[
                    {
                        "result": {
                            "timestamp": "2019-03-05T01:02:03Z",
                            "logs": [
                                'processed scheduled event "my_event" for account "my_account"'
                            ],
                        },
                    },
                    {
                        "result": {
                            "timestamp": "2019-03-06T01:02:03Z",
                            "logs": [
                                'processed scheduled event "my_event" for account "my_account"'
                            ],
                        },
                    },
                    {
                        "result": {
                            "timestamp": "2019-03-07T01:02:03Z",
                            "logs": ['processed scheduled event "my_event" for plan "my_plan"'],
                        },
                    },
                ],
            )
        )


class TestCalendar(TestCase):
    def test_get_calendar_created(self):
        is_calendar_id_created = get_calendar_created(
            res=[
                {
                    "result": {
                        "timestamp": "2019-01-01T00:00:00Z",
                        "logs": ['created calendar with id "debug_calendar"'],
                        "posting_instruction_batches": [],
                        "balances": {},
                        "account_notes": {},
                        "instantiate_workflow_requests": {},
                        "derived_params": {},
                        "contract_notification_events": {},
                        "hook_execution_logs": [],
                    }
                }
            ],
            calendar_id="debug_calendar",
        )

        self.assertTrue(is_calendar_id_created)

    def test_get_calendar_event_created(self):
        is_calendar_created = get_calendar_event_created(
            res=[
                {
                    "result": {
                        "timestamp": "2019-01-01T00:00:00Z",
                        "logs": ['created calendar event for calendar "debug_calendar"'],
                        "posting_instruction_batches": [],
                        "balances": {},
                        "account_notes": {},
                        "instantiate_workflow_requests": {},
                        "derived_params": {},
                        "contract_notification_events": {},
                        "hook_execution_logs": [],
                    }
                }
            ],
            calendar_id="debug_calendar",
        )

        self.assertTrue(is_calendar_created)


class TestExpectedViolations(TestCase):
    def test_expected_violations_raises_error_pre_v5_7_0(self):
        test_scenario = SimulationTestScenario(
            start=sentinel.start,
            end=sentinel.end,
            sub_tests=[
                SubTest(
                    description=sentinel.description,
                    expected_account_violations={
                        datetime(2019, 3, 5, tzinfo=timezone.utc): [
                            ExpectedAccountViolation(
                                account_violation=sentinel.account_violation,
                            )
                        ]
                    },
                    expected_contract_violations={
                        datetime(2019, 3, 5, tzinfo=timezone.utc): [
                            ExpectedContractViolation(
                                contract_violation=sentinel.contract_violation,
                            )
                        ],
                    },
                    expected_posting_violations={
                        datetime(2019, 3, 5, tzinfo=timezone.utc): [
                            ExpectedPostingViolation(
                                posting_violation=sentinel.posting_violation,
                            )
                        ],
                    },
                ),
            ],
        )

        with self.assertRaises(ValueError) as value_error:
            compile_chrono_events(
                test_scenario=test_scenario, setup_events=[], vault_version=Version("5.6.5")
            )

        self.assertEqual(
            value_error.exception.args[0],
            (
                "Subtest 'sentinel.description' contains ['expected_account_violations', "
                "'expected_posting_violations', 'expected_contract_violations'] which are "
                "unsupported prior to Vault 5.7.0."
            ),
        )
