# Copyright @ 2021-2023 Thought Machine Group Limited. All rights reserved.
# standard libs
import json
import logging
import os
import re
from collections import defaultdict
from copy import deepcopy
from datetime import datetime, timezone
from dateutil import parser
from decimal import Decimal
from pathlib import Path
from time import time
from typing import Any, Callable, ClassVar, DefaultDict, Generator, Iterator
from unittest import TestCase

# third party
from semantic_version import Version

# inception sdk
import inception_sdk.common.python.flag_utils as flag_utils
import inception_sdk.vault.core_api as core_api
import inception_sdk.vault.sim_api.contract_sim as sim
from inception_sdk.common.exceptions import TestSetupException
from inception_sdk.common.python.file_utils import load_file_contents, load_module_from_filepath
from inception_sdk.test_framework.common.balance_helpers import (
    Balance,
    BalanceDimensions,
    NetBalances,
    compare_balances,
    dict_to_net_balance,
    get_net_balance_mismatches,
)
from inception_sdk.test_framework.common.config import (
    EnvironmentPurpose,
    extract_framework_environments_from_config,
)
from inception_sdk.test_framework.common.timeseries import TimeSeries
from inception_sdk.test_framework.common.utils import extract_parameters
from inception_sdk.test_framework.contracts.simulation import vault_caller
from inception_sdk.test_framework.contracts.simulation.data_objects.data_objects import (
    AccountConfig,
    ContractConfig,
    ExpectedAccountAttributeValue,
    ExpectedAccountViolation,
    ExpectedContractError,
    ExpectedContractNotification,
    ExpectedContractViolation,
    ExpectedDerivedParameter,
    ExpectedPostingEnrichments,
    ExpectedPostingViolation,
    ExpectedRejection,
    ExpectedSchedule,
    ExpectedSubAccountEvent,
    SimulationEvent,
    SimulationTestScenario,
    SubTest,
    SuperviseeConfig,
    SupervisorConfig,
)
from inception_sdk.test_framework.contracts.simulation.data_objects.events.parameter_events import (
    CreateGlobalParameterEvent,
)
from inception_sdk.test_framework.contracts.simulation.helper import (
    get_contract_setup_events,
    get_supervisor_setup_events,
)
from inception_sdk.tools.renderer.render_utils import is_file_renderable
from inception_sdk.tools.renderer.renderer import RendererConfig, SmartContractRenderer

MAIN_ACCOUNT = "Main account"

log = logging.getLogger(__name__)
logging.basicConfig(
    level=os.environ.get("LOGLEVEL", "INFO"),
    format="%(asctime)s.%(msecs)03d - %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


## Test Decorators


def skipForVaultVersion(
    callback: Callable[[Version], bool] | None = None,
    reason=None,
):
    """
    Skips a test method based on the Vault Version provided.

    :param callback: the function to run to determine if the test should be skipped or not. If
    omitted or None, the test will always be skipped.
    :param reason: the reason for skipping the test.
    """

    def decorator(method):
        def inner(ref: SimulationTestCase):
            version: Version = ref.vault_version
            if callback is None:
                skip_reason = reason or "This test should be skipped for all versions of Vault."
                # This raises an exception.
                ref.skipTest(skip_reason)
            is_skip = callback(version)
            if is_skip:
                skip_reason = reason or f"This test should be skipped for Vault v{str(version)}."
                # This raises an exception.
                ref.skipTest(skip_reason)
            return method(ref)

        return inner

    return decorator


def skipForVaultVersionLessThan(
    min_version: Version,
    reason: str | None = None,
):
    """
    Skips a test method if the Vault version is less than the specified version.

    :param min_version: the version to compare against.
    :param reason: the reason for skipping the test.
    """
    return skipForVaultVersion(
        callback=lambda v: v < min_version,
        reason=reason or f"Vault version {min_version} or higher is required",
    )


def skipForVaultVersionGreaterThan(
    max_version: Version,
    reason: str | None = None,
):
    """
    Skips a test method or class if the Vault version is greater than the specified version.
    :param max_version: the version to compare against.
    :param reason: the reason for skipping the test.
    """
    return skipForVaultVersion(
        callback=lambda v: v > max_version,
        reason=reason or f"Vault version {max_version} or lower is required",
    )


def skipForMissingExtension(required_extensions: list[core_api.VaultCoreExtension]):
    """
    This decorator can only be used when running against environments on Vault versions 5.8+, since
    the `extensions` information isn't available via the Core API before this.

    Skips a test method based on enabled Vault Core extensions on the environment.
    """

    def decorator(method):
        def inner(ref: SimulationTestCase):
            enabled_extensions = ref.vault_extensions
            if ref.vault_version < Version("5.8.0"):
                raise TestSetupException(
                    "`skipForMissingExtension` decorator only available for Vault versions 5.8+."
                )

            required = {e.name for e in required_extensions}
            enabled = {e.name for e in enabled_extensions}

            if not required.issubset(enabled):
                missing = sorted(list(required.difference(enabled)))
                ref.skipTest(
                    f"This test requires {sorted(list(required))} extensions to be enabled but "
                    f"the environment has {sorted(list(enabled))} extensions enabled. "
                    f"Missing required extensions: {missing}."
                )

            return method(ref)

        return inner

    return decorator


class SimulationTestCase(TestCase):
    contract_filepaths: list[str] = []
    input_data_filename: str = ""
    expected_output_filename: str = ""
    default_instance_params: dict[str, str] | None = None
    default_template_params: dict[str, str] | None = None
    internal_accounts: dict[str, str] | None = None
    # Adding a new variable for V2 Internal Account balances
    internal_accounts_mapping: dict[str, str] | None = None
    smart_contract_path_to_content: dict[str, str] = {}
    parameter_resource_dirs: list[str] = []
    parameters: list[core_api.ParameterResource] = []
    flag_definition_ids: list[str] | None = None
    calendar_ids: list[str] | None = None
    # TODO: In the future can initialise it to a dummy client that will error if you
    # call it and return a helpful message like (you need to load env config before using the
    # client), and then load config method then calls a 'setup' method on the client
    client: ClassVar[vault_caller.Client]
    vault_version: Version
    use_v1_accounts: bool = True
    # For Vault versions <5.8, this will be not be set since extensions information isn't available
    # on the Core API. For 5.8+, it will be a list of the enabled extensions on the environment,
    # which could be an empty list.
    vault_extensions: list[core_api.VaultCoreExtension]

    @classmethod
    def load_contract_from_file(cls):
        for contract in cls.contract_filepaths:
            reader = (
                SimulationTestCase.render_and_read_smart_contract
                if is_file_renderable(Path(contract))
                else SimulationTestCase.read_smart_contract
            )
            cls.smart_contract_path_to_content.update({contract: reader(contract)})

    @staticmethod
    def render_and_read_smart_contract(contract: str) -> str:
        scr_config = RendererConfig(
            autogen_warning="# Code auto-generated for simulation testing",
            apply_formatting=False,
            use_git=False,
        )
        scr = SmartContractRenderer(load_module_from_filepath(contract), scr_config)
        scr.render(write_to_file=False)
        return scr.rendered_contract

    @staticmethod
    def read_smart_contract(contract: str) -> str:
        with open(contract, encoding="utf-8") as smart_contract_file:
            return smart_contract_file.read()

    @classmethod
    def load_test_config(cls):
        # we allow unknown because there may be unittest flags in argv
        flag_utils.parse_flags(allow_unknown=True)
        environment, _ = extract_framework_environments_from_config(
            environment_purpose=EnvironmentPurpose.SIM
        )
        cls.client = vault_caller.Client(environment=environment)

    @classmethod
    def load_input_data(cls):
        if cls.input_data_filename:
            with open(cls.input_data_filename, encoding="utf-8") as input_data_file:
                cls.input_data = json.load(input_data_file)
        else:
            cls.input_data = {}

    @classmethod
    def load_output_data(cls):
        if cls.expected_output_filename:
            with open(cls.expected_output_filename, encoding="utf-8") as expected_output_file:
                cls.expected_output = json.load(expected_output_file)
        else:
            cls.expected_output = {}

    @classmethod
    def load_parameters(cls):
        if cls.parameter_resource_dirs:
            cls.parameters = extract_parameters(cls.parameter_resource_dirs)

    @classmethod
    def load_vault_version(cls) -> None:
        data: list[dict[str, Any]] = cls.client.get_vault_version()
        version: dict[str, Any] = data[0]["version"]
        # As far as we know, major, minor, and patch are always integers.
        major: int = version["major"]
        minor: int = version["minor"]
        patch: int = version["patch"]
        label: str = version.get("label", "")
        cls.vault_version = Version(f"{major}.{minor}.{patch}{label}")
        if (extensions_data := data[0].get("extensions")) is not None:
            cls.vault_extensions = [core_api.VaultCoreExtension(e) for e in extensions_data]

    @classmethod
    def setUpClass(cls):
        # This ensures we get full balance diffs when using check_balances
        cls.maxDiff = None

        cls.load_contract_from_file()
        cls.load_test_config()
        cls.load_parameters()
        cls.load_input_data()
        cls.load_output_data()
        cls.load_vault_version()

    def setUp(self):
        self._started_at = time()

    def tearDown(self):
        self._elapsed_time = time() - self._started_at
        # Uncomment this for timing info.
        # print('{} ({}s)'.format(self.id().rpartition('.')[2], round(self._elapsed_time, 2))

    def assertBalancesEqual(
        self,
        expected_balances: list[tuple[BalanceDimensions, str]],
        actual_balances: DefaultDict[BalanceDimensions, Balance],
        msg: str = "",
    ) -> None:
        """
        Fail if the balances for the given dimensions do not match expected values:
        :param expected_balances: balance dimensions and corresponding expected net values
        :param actual_balances: default dict of balance dimensions and corresponding actual
        balances
        :param msg: message to show on assertion failure. The differences between expected and
        actual balances will be appended to this
        """
        self.assertExpectations(expected_balances, actual_balances, compare_balances, msg)

    def assertExpectations(
        self,
        expected: Any,
        actual: Any,
        comparator: Callable[[Any, Any], dict | list],
        msg: str = "",
    ) -> None:
        """
        Fails if actual values do not match expected values
        :param expected: objects specifying expected values
        :param actual: objects that contains actual outcome from the simulator
        :param comparator: callable that takes in expected and actual as arguments, and returns
        a collection of expected values not found in actual
        :param msg: message to show on assertion failure. The differences between expected and
        actual will be appended to this
        """
        failed_expectations = comparator(expected, actual)
        if len(failed_expectations) > 0:
            raise AssertionError((msg or "expected values not found") + f": {failed_expectations}")

    @staticmethod
    def assertions_exist_in_subtests(subtests: list[SubTest]):
        """
        Checks if there exists any subtest assertions in a given list of subtests

        :param subtests: list of subtests, commonly defined as SimulationTestScenario.subtests
        :return: `True` if assertions exists in the Subtests, otherwise `False`
        """
        for sub_test in subtests:
            possible_expectations = [
                sub_test.expected_account_activation_rejections,
                sub_test.expected_account_conversion_rejections,
                sub_test.expected_account_deactivation_rejections,
                sub_test.expected_account_violations,
                sub_test.expected_balances_at_ts,
                sub_test.expected_net_balances,
                sub_test.expected_booking_balances_at_ts,
                sub_test.expected_contract_errors,
                sub_test.expected_contract_notifications,
                sub_test.expected_contract_violations,
                sub_test.expected_derived_parameters,
                sub_test.expected_parameter_change_rejections,
                sub_test.expected_posting_enrichments,
                sub_test.expected_posting_rejections,
                sub_test.expected_posting_violations,
                sub_test.expected_schedules,
                sub_test.expected_sub_accounts,
                sub_test.expected_value_balances_at_ts,
            ]
            if any(possible_expectations):
                return True
        return False

    def check_balances(
        self,
        expected_balances: dict[str, dict[datetime, list[tuple[BalanceDimensions, str]]]],
        actual_balances: DefaultDict[str, TimeSeries],
    ) -> None:
        """
        Simplifies balance checking inside simulation tests. Does not support backdated tests
        :param expected_balances: Expected balances structured as follows. The datetime represents
        value_timestamp
        {
            'account_id': {
                datetime(2020, 1, 1,): [
                    (BalanceDimensions(), '0'),
                    (BalanceDimensions(address='CUSTOM_ADDRESS), '10')
                ]
            }
        }
        :param actual_balances: actual balances as returned by get_balances
        """
        for account_id, account_expected_balances in expected_balances.items():
            account_balances = actual_balances[account_id]
            for value_timestamp, balance_tuples in account_expected_balances.items():
                self.assertBalancesEqual(
                    expected_balances=balance_tuples,
                    actual_balances=account_balances.at(value_timestamp),
                    msg=f"expected & actual balances differ for {account_id} at {value_timestamp}",
                )

    def check_balances_by_ts(
        self,
        expected_balances: dict[datetime, dict[str, list[tuple[BalanceDimensions, str]]]],
        actual_balances: DefaultDict[str, TimeSeries],
        description: str = "",
    ) -> None:
        """
        Similar to check_balances, except allows the expected balances to be organised by timestamp
        and then account, instead of account and then timestamp. This is helpful to improve
        legibility of tests that check multiple accounts' balances
        :param expected_balances: Expected balances structured as follows. The datetime represents
        value_timestamp
        {
            datetime(2020, 1, 1) : {
                'account_id': [
                    (BalanceDimensions(), '0'),
                    (BalanceDimensions(address='CUSTOM_ADDRESS), '10')
                ]
            }
        }
        :param actual_balances: actual balances as returned by get_balances
        :param description: msg for assertion errors
        """
        for value_timestamp, account_expected_balances in expected_balances.items():
            for account_id, balance_tuples in account_expected_balances.items():
                account_balances = actual_balances[account_id]
                self.assertBalancesEqual(
                    expected_balances=balance_tuples,
                    actual_balances=account_balances.at(value_timestamp),
                    msg=(
                        description
                        or f"expected and actual balances differ "
                        f"for {account_id} at {value_timestamp}"
                    ),
                )

    def check_live_balances_v2(
        self,
        expected_balances: dict[datetime, NetBalances],
        actual_balances: dict[datetime, NetBalances],
        description: str = "",
    ) -> None:
        """
        Validates that all the expected balances for a given timestamp exist,
        raises error if not.

        :param expected_balances: Dictionary of datetime to expected balances.
        :param actual_balances: Dictionary of datetime to actual balances.
        :param description: Optional description to be displayed if balances don't match.
        """

        def get_mismatched_balances(expected, actual):
            """
            Helper method to iterate over balance dictionaries.
            """
            mismatches: dict[datetime, Any] = {}
            for timestamp, expected_account_balances in expected.items():
                if timestamp not in actual:
                    mismatches[timestamp] = f"No balances found at expected timestamp {timestamp}"
                    continue
                actual_account_balances = actual[timestamp]
                timestamp_mismatches = get_net_balance_mismatches(
                    expected_account_balances, actual_account_balances
                )
                if timestamp_mismatches:
                    mismatches[timestamp] = timestamp_mismatches
            return mismatches

        self.assertExpectations(
            expected_balances,
            actual_balances,
            get_mismatched_balances,
            description,
        )

    def check_derived_parameters(
        self,
        expected_derived_parameters: list[ExpectedDerivedParameter],
        derived_parameters: dict[str, TimeSeries],
        description: str = "",
    ) -> None:
        def get_mismatched_derived_params(expected_derived_parameters, actual_derived_parameters):
            mismatched_derived_params = {}
            for expected_derived_param in expected_derived_parameters:
                account_id = expected_derived_param.account_id
                value_timestamp = expected_derived_param.timestamp
                parameter = expected_derived_param.name
                expected_value = expected_derived_param.value
                actual_derived_params = actual_derived_parameters[account_id].at(value_timestamp)
                if parameter not in actual_derived_params:
                    mismatched_derived_params[parameter] = (
                        "ERROR: parameter is missing from actual values"
                    )
                elif expected_value != actual_derived_params[parameter]:
                    mismatched_derived_params[
                        f'param: "{parameter}" '
                        f'account: "{account_id}" '
                        f'@: "{str(value_timestamp)}"'
                    ] = f'Expected: "{expected_value}" Got: "{actual_derived_params[parameter]}"'
            return mismatched_derived_params

        self.assertExpectations(
            expected_derived_parameters,
            derived_parameters,
            get_mismatched_derived_params,
            description,
        )

    def check_contract_errors(
        self,
        expected_contract_errors: list[ExpectedContractError],
        logs_with_timestamp: dict,
        description: str = "",
    ):
        def get_contract_error_regex(expected_contract_error: ExpectedContractError) -> str:
            return (
                f"account.id:{expected_contract_error.account_id}.*"
                f"exception_type:{expected_contract_error.exception_type}.*"
            )

        def get_missing_contract_errors(
            expected_contract_errors: list[ExpectedContractError],
            logs_with_timestamp: dict,
        ):
            return [
                expected_contract_errors
                for expected_contract_error in expected_contract_errors
                if not any(
                    re.search(get_contract_error_regex(expected_contract_error), log)
                    for log in logs_with_timestamp.get(expected_contract_error.timestamp, [])
                )
            ]

        self.assertExpectations(
            expected_contract_errors,
            logs_with_timestamp,
            get_missing_contract_errors,
            description,
        )

    def check_account_activation_rejections(
        self,
        expected_rejections: list[ExpectedRejection],
        logs_with_timestamp: dict,
        description: str = "",
    ) -> None:
        def get_rejection_message(expected_rejection: ExpectedRejection) -> str:
            return (
                f"processing create account v2 instruction: activation hook "
                f"returned a rejection: violations[{{violation_type: CHANGE_REJECTED_BY_CONTRACT, "
                f"metadata: map[rejection_message:{expected_rejection.rejection_reason} "
                f"rejection_type:{expected_rejection.rejection_type}]}}]"
            )

        def get_missing_rejections(
            expected_rejections: list[ExpectedRejection],
            logs_with_timestamp: dict,
        ):
            return [
                expected_rejection
                for expected_rejection in expected_rejections
                if not any(
                    get_rejection_message(expected_rejection) in log
                    for log in logs_with_timestamp.get(expected_rejection.timestamp, [])
                )
            ]

        self.assertExpectations(
            expected_rejections,
            logs_with_timestamp,
            get_missing_rejections,
            description,
        )

    def check_account_conversion_rejections(
        self,
        expected_rejections: list[ExpectedRejection],
        logs_with_timestamp: dict,
        description: str = "",
    ) -> None:
        def get_rejection_message(expected_rejection: ExpectedRejection) -> str:
            return (
                f"processing update account v2 instruction: conversion hook "
                f"returned a rejection: violations[{{violation_type: CHANGE_REJECTED_BY_CONTRACT, "
                f"metadata: map[rejection_message:{expected_rejection.rejection_reason} "
                f"rejection_type:{expected_rejection.rejection_type}]}}]"
            )

        def get_missing_rejections(
            expected_rejections: list[ExpectedRejection],
            logs_with_timestamp: dict,
        ):
            return [
                expected_rejection
                for expected_rejection in expected_rejections
                if not any(
                    get_rejection_message(expected_rejection) in log
                    for log in logs_with_timestamp.get(expected_rejection.timestamp, [])
                )
            ]

        self.assertExpectations(
            expected_rejections,
            logs_with_timestamp,
            get_missing_rejections,
            description,
        )

    def check_account_deactivation_rejections(
        self,
        expected_rejections: list[ExpectedRejection],
        logs_with_timestamp: dict,
        description: str = "",
    ) -> None:
        def get_rejection_message(expected_rejection: ExpectedRejection) -> str:
            return (
                f"processing update account v2 instruction: deactivation hook "
                f"returned a rejection: violations[{{violation_type: "
                f"CHANGE_REJECTED_BY_CONTRACT, metadata: map[rejection_message:"
                f"{expected_rejection.rejection_reason} "
                f"rejection_type:{expected_rejection.rejection_type}]}}]"
            )

        def get_missing_rejections(
            expected_rejections: list[ExpectedRejection],
            logs_with_timestamp: dict,
        ):
            return [
                expected_rejection
                for expected_rejection in expected_rejections
                if not any(
                    get_rejection_message(expected_rejection) in log
                    for log in logs_with_timestamp.get(expected_rejection.timestamp, [])
                )
            ]

        self.assertExpectations(
            expected_rejections,
            logs_with_timestamp,
            get_missing_rejections,
            description,
        )

    def check_posting_rejections(
        self,
        expected_rejections: list[ExpectedRejection],
        logs_with_timestamp: dict,
        description: str = "",
    ) -> None:
        def get_rejection_message(expected_rejection: ExpectedRejection) -> str:
            resource_type = "account" if expected_rejection.account_id else "plan"
            resource_id = expected_rejection.account_id or expected_rejection.plan_id
            return (
                f'{resource_type} "{resource_id}" rejected with rejection type '
                f'"{expected_rejection.rejection_type}" and reason '
                # we intentionally don't close the double quotes to allow for partial matching
                # this is arguably less correct, but is also backwards compatible
                f'"{expected_rejection.rejection_reason}'
            )

        def get_missing_rejections(
            expected_rejections: list[ExpectedRejection],
            logs_with_timestamp: dict,
        ):
            return [
                expected_rejection
                for expected_rejection in expected_rejections
                if not any(
                    get_rejection_message(expected_rejection) in log
                    for log in logs_with_timestamp.get(expected_rejection.timestamp, [])
                )
            ]

        self.assertExpectations(
            expected_rejections,
            logs_with_timestamp,
            get_missing_rejections,
            description,
        )

    def check_parameter_change_rejections(
        self,
        expected_rejections: list[ExpectedRejection],
        logs_with_timestamp: dict,
        description: str = "",
    ) -> None:
        """
        Validates that all expected parameter change rejections are present in the log of the
        response to the simulate API

        :param expected_rejections: rejections that should be generated during the simulation
        :param logs_with_timestamp: logs retrieved from the result of calling the API
        :param description: description of the subtest used to identify the subtest in case the
        assertion fails
        """

        def get_rejection_message(expected_rejection: ExpectedRejection) -> str:
            if self.vault_version >= Version("5.1.0"):
                return (
                    f"account parameters update rejected for account "
                    f'"{expected_rejection.account_id}": rejection type '
                    f'"{expected_rejection.rejection_type}" and reason '
                    # we intentionally don't close the double quotes to allow for partial matching
                    # this is arguably less correct, but is consistent with other checks
                    f'"{expected_rejection.rejection_reason}'
                )
            elif self.vault_version == Version("5.0.0"):
                return (
                    f"account parameters update rejected for account "
                    f'"{expected_rejection.account_id}": '
                    # The rejection reason is not double quoted on 5.0.0, strangely
                    f"{expected_rejection.rejection_reason}"
                )
            else:
                return f"account parameters update rejected: {expected_rejection.rejection_reason}"

        def get_missing_rejections(expected_rejections, logs_with_timestamp):
            return [
                expected_rejection
                for expected_rejection in expected_rejections
                if not any(
                    get_rejection_message(expected_rejection) in log
                    for log in logs_with_timestamp.get(expected_rejection.timestamp, [])
                )
            ]

        self.assertExpectations(
            expected_rejections,
            logs_with_timestamp,
            get_missing_rejections,
            description,
        )

    def check_simulation_error(
        self,
        expected_error: Exception | None = None,
        actual_error: Exception | None = None,
    ):
        """
        Compares an expected simulation error to an actual simulation error
        :param expected_error: the expected error from a simulation.
        :param actual_error: the actual error received from the simulation
        """

        def compare_errors(expected: Exception | None, actual: Exception | None):
            outcome: dict[str, str] = {}
            if expected == actual:
                return outcome

            outcome["expected"] = expected.__repr__() if expected else "None"
            outcome["actual"] = actual.__repr__() if actual else "None"

            return outcome

        self.assertExpectations(
            expected=expected_error,
            actual=actual_error,
            comparator=compare_errors,
        )

    def check_schedule_processed(
        self,
        expected_schedule_runs: list[ExpectedSchedule],
        res: list[dict[str, Any]],
        description: str = "",
    ) -> None:
        def get_missing_schedule_runs(expected_schedules, simulator_results):
            missing_schedule_runs = []
            for expected_schedule in expected_schedules:
                processed_schedules = get_processed_scheduled_events(
                    simulator_results,
                    expected_schedule.event_id,
                    account_id=expected_schedule.account_id,
                    plan_id=expected_schedule.plan_id,
                )
                if expected_schedule.count is not None:
                    self.assertEqual(expected_schedule.count, len(processed_schedules), description)

                missing_schedule_runs.extend(
                    (
                        expected_schedule_run
                        for expected_schedule_run in expected_schedule.run_times
                        if (
                            expected_schedule_run.strftime("%Y-%m-%dT%H:%M:%SZ")
                            not in processed_schedules
                        )
                    )
                )
            return missing_schedule_runs

        self.assertExpectations(expected_schedule_runs, res, get_missing_schedule_runs, description)

    def check_contract_notifications(
        self,
        expected_contract_notifications: list[ExpectedContractNotification],
        contract_notifications: dict[str, dict[str, list]],
        description: str = "",
    ) -> None:
        def get_mismatched_notifications(
            expected_notifications: list[ExpectedContractNotification],
            actual_notifications: dict[str, dict[str, list]],
        ):
            mismatched_notifications = []
            for expected_notification in expected_notifications:
                potential_match_notifications = actual_notifications[
                    expected_notification.resource_id
                ][expected_notification.notification_type]

                potential_match = {}
                for notification in potential_match_notifications:
                    # Comparing timestamps
                    if notification[0] == expected_notification.timestamp:
                        potential_match = notification[1]
                        # Comparing notification details
                        if (
                            potential_match["notification_details"]
                            == expected_notification.notification_details
                        ):
                            break
                        else:
                            mismatched_notifications.append(
                                f"Notification found for type and resource id but with different "
                                f"details: {potential_match.get('notification_details')}.\n"
                                f"Expected {expected_notification.notification_details}"
                            )
                # No match found for the expected_notification in actual_notifications
                if not potential_match:
                    mismatched_notifications.append(
                        f"No notification found for this type and resource id at "
                        f"{expected_notification.timestamp}"
                    )

            return mismatched_notifications

        self.assertExpectations(
            expected_contract_notifications,
            contract_notifications,
            get_mismatched_notifications,
            description,
        )

    def check_posting_enrichments(
        self,
        expected_posting_enrichments: list[ExpectedPostingEnrichments],
        posting_enrichments: dict[str, dict[str, str]],
        description: str = "",
    ) -> None:
        def get_mismatched_enrichments(
            expected_enrichments: list[ExpectedPostingEnrichments],
            actual_enrichments: dict[str, dict[str, str]],
        ):
            mismatched_enrichments = []

            for expected_enrichment in expected_enrichments:
                expected_resource_id = expected_enrichment.account_id
                expected_details = expected_enrichment.enrichment_details

                actual_details = actual_enrichments.get(expected_resource_id)

                if actual_details is None:
                    mismatched_enrichments.append(
                        f"No enrichments found for resource id '{expected_resource_id}'."
                    )
                    continue

                if actual_details != expected_details:
                    mismatched_enrichments.append(
                        f"Mismatch for resource id '{expected_resource_id}':\n"
                        f"Expected: {expected_details}\n"
                        f"Actual:   {actual_details}"
                    )

            return mismatched_enrichments

        self.assertExpectations(
            expected_posting_enrichments,
            posting_enrichments,
            get_mismatched_enrichments,
            description,
        )

    def check_account_violations(
        self,
        expected_account_violations: dict[datetime, list[ExpectedAccountViolation]],
        account_violations: dict[datetime, dict[str, list[core_api.AccountViolation]]],
        description: str = "",
    ):
        def get_mismatched_violations(
            timestamp_to_expected_violations: dict[datetime, list[ExpectedAccountViolation]],
            timestamp_to_actual_violations: dict[
                datetime, dict[str, list[core_api.AccountViolation]]
            ],
        ) -> list[str]:
            mismatched_violations: list[str] = []
            for timestamp, expected_violations in timestamp_to_expected_violations.items():
                actual_violations = timestamp_to_actual_violations.get(timestamp)
                if actual_violations is None:
                    extracted_violations = [
                        expected_violation.account_violation
                        for expected_violation in expected_violations
                    ]
                    mismatched_violations.append(
                        f"No account violations found at timestamp '{timestamp}'.\n"
                        f"Expected: {extracted_violations} Got: {actual_violations}"
                    )
                    continue
                all_actual_violations = {
                    violation
                    for violation_vals in actual_violations.values()
                    for violation in violation_vals
                }
                for expected_violation in expected_violations:
                    extracted_violation = expected_violation.account_violation
                    client_tx_id = expected_violation.client_transaction_id
                    if client_tx_id is not None:
                        violations = actual_violations.get(client_tx_id)
                        if violations is None:
                            mismatched_violations.append(
                                f"No account violations for client transaction ID {client_tx_id} "
                                f"at {timestamp}.\n"
                                f"Expected: {extracted_violation} Got: {actual_violations}"
                            )
                            continue
                        if extracted_violation not in violations:
                            mismatched_violations.append(
                                f"Expected account violation for client transaction ID "
                                f"{client_tx_id} at {timestamp} not found.\n"
                                f"Expected: {extracted_violation} "
                                f"Got: {violations}"
                            )
                            continue
                    else:
                        if extracted_violation not in all_actual_violations:
                            mismatched_violations.append(
                                f"Expected account violation not found in actual account "
                                f"violations:\n"
                                f"Expected: {extracted_violation} Got: {actual_violations}"
                            )
                            continue

            return mismatched_violations

        self.assertExpectations(
            expected_account_violations,
            account_violations,
            get_mismatched_violations,
            description,
        )

    def check_contract_violations(
        self,
        expected_contract_violations: dict[datetime, list[ExpectedContractViolation]],
        contract_violations: dict[datetime, dict[str, list[core_api.ContractViolation]]],
        description: str = "",
    ):
        def get_mismatched_violations(
            timestamp_to_expected_violations: dict[datetime, list[ExpectedContractViolation]],
            timestamp_to_actual_violations: dict[
                datetime, dict[str, list[core_api.ContractViolation]]
            ],
        ) -> list[str]:
            mismatched_violations: list[str] = []
            for timestamp, expected_violations in timestamp_to_expected_violations.items():
                actual_violations = timestamp_to_actual_violations.get(timestamp)
                if actual_violations is None:
                    extracted_violation = [
                        expected_violation.contract_violation
                        for expected_violation in expected_violations
                    ]
                    mismatched_violations.append(
                        f"No contract violations found at timestamp '{timestamp}'.\n"
                        f"Expected: {extracted_violation} Got: {actual_violations}"
                    )
                    continue
                all_actual_violations = {
                    violation
                    for violation_vals in actual_violations.values()
                    for violation in violation_vals
                }
                for expected_violation in expected_violations:
                    extracted_violations = expected_violation.contract_violation
                    client_tx_id = expected_violation.client_transaction_id
                    if client_tx_id is not None:
                        violations = actual_violations.get(client_tx_id)
                        if violations is None:
                            mismatched_violations.append(
                                f"No contract violations for client transaction ID {client_tx_id} "
                                f"at {timestamp}.\n"
                                f"Expected: {extracted_violations} Got: {actual_violations}"
                            )
                            continue
                        if extracted_violations not in violations:
                            mismatched_violations.append(
                                f"Expected contract violation for client transaction ID "
                                f"{client_tx_id} at {timestamp} not found.\n"
                                f"Expected: {extracted_violations} "
                                f"Got: {violations}"
                            )
                            continue
                    else:
                        if extracted_violations not in all_actual_violations:
                            mismatched_violations.append(
                                f"Expected contract violation not found in actual contract "
                                f"violations:\n"
                                f"Expected: {extracted_violations} "
                                f"Got: {actual_violations}"
                            )
                            continue

            return mismatched_violations

        self.assertExpectations(
            expected_contract_violations,
            contract_violations,
            get_mismatched_violations,
            description,
        )

    def check_posting_violations(
        self,
        expected_posting_violations: dict[datetime, list[ExpectedPostingViolation]],
        posting_violations: dict[datetime, dict[str, list[core_api.PostingViolation]]],
        description: str = "",
    ):
        def get_mismatched_violations(
            timestamp_to_expected_violations: dict[datetime, list[ExpectedPostingViolation]],
            timestamp_to_actual_violations: dict[
                datetime, dict[str, list[core_api.PostingViolation]]
            ],
        ) -> list[str]:
            mismatched_violations: list[str] = []
            for timestamp, expected_violations in timestamp_to_expected_violations.items():
                actual_violations = timestamp_to_actual_violations.get(timestamp)
                if actual_violations is None:
                    extracted_violation = [
                        expected_violation.posting_violation
                        for expected_violation in expected_violations
                    ]
                    mismatched_violations.append(
                        f"No posting violations found at timestamp '{timestamp}'.\n"
                        f"Expected: {extracted_violation} Got: {actual_violations}"
                    )
                    continue
                all_actual_violations = {
                    violation
                    for violation_vals in actual_violations.values()
                    for violation in violation_vals
                }
                for expected_violation in expected_violations:
                    extracted_violations = expected_violation.posting_violation
                    client_tx_id = expected_violation.client_transaction_id
                    if client_tx_id is not None:
                        violations = actual_violations.get(client_tx_id)
                        if violations is None:
                            mismatched_violations.append(
                                f"No posting violations for client transaction ID {client_tx_id} "
                                f"at {timestamp}.\n"
                                f"Expected: {extracted_violations} Got: {actual_violations}"
                            )
                            continue
                        if extracted_violations not in violations:
                            mismatched_violations.append(
                                f"Expected posting violation for client transaction ID "
                                f"{client_tx_id} at {timestamp} not found.\n"
                                f"Expected: {extracted_violations} "
                                f"Got: {violations}"
                            )
                            continue
                    else:
                        if extracted_violations not in all_actual_violations:
                            mismatched_violations.append(
                                f"Expected posting violation not found in actual posting "
                                f"violations:\n"
                                f"Expected: {extracted_violations} "
                                f"Got: {actual_violations}"
                            )
                            continue

            return mismatched_violations

        self.assertExpectations(
            expected_posting_violations,
            posting_violations,
            get_mismatched_violations,
            description,
        )

    def check_account_attribute_values(
        self,
        expected_account_attribute_values: list[ExpectedAccountAttributeValue],
        account_attribute_values_by_account: dict,
        description: str = "",
    ):
        def compare_account_attribute_value(
            expected_account_attribute_value: ExpectedAccountAttributeValue,
            account_attribute_value: core_api.AccountAttributeValue,
        ):
            return account_attribute_value == expected_account_attribute_value.to_core_api_model()

        def get_mismatched_account_attributes(
            expected_account_attributes: list[ExpectedAccountAttributeValue],
            actual_account_attribute_values_by_account: dict,
        ):
            return [
                expected_account_attribute
                for expected_account_attribute in expected_account_attributes
                if not any(
                    compare_account_attribute_value(
                        expected_account_attribute, account_attribute_value
                    )
                    for account_id, account_attribute_values in actual_account_attribute_values_by_account.items()  # noqa: E501
                    if account_id == expected_account_attribute.account_id
                    for account_attribute_value in account_attribute_values
                )
            ]

        self.assertExpectations(
            expected_account_attribute_values,
            account_attribute_values_by_account,
            get_mismatched_account_attributes,
            description,
        )

    def check_sub_account_events(
        self,
        expected_sub_accounts: list[ExpectedSubAccountEvent],
        logs_with_timestamp: dict[datetime, list[str]],
        description: str = "",
    ):
        """
        Validates that all expected Sub-Account events occurred during the simulation.

        :param expected_sub_accounts: A list of `ExpectedSubAccountEvent` objects detailing
            timestamp of the event, and the parent and Sub-Account IDs that should be verified.
        :param logs_with_timestamp: dictionary of output logs from the simulation endpoint,
            keyed by timestamp.
        :param description: An optional description to prepend to the assertion error
            message if a missing Sub-Account event causes the test to fail.
        :raises AssertionError: If any of the expected Sub-Account events cannot be found in the
            simulation logs.
        """

        def get_missing_sub_account_events(
            expected_sub_account_events: list[ExpectedSubAccountEvent],
            logs_with_timestamp: dict[datetime, list[str]],
        ):
            """
            Helper function to check logs for expected Sub-Account events.
            Returns dictionary of all missing Sub-Account events.
            """
            missing_sub_account_events = {}

            for expected_event in expected_sub_account_events:
                log = logs_with_timestamp.get(expected_event.timestamp)
                if log is None:
                    missing_sub_account_events[
                        f"{expected_event}"
                    ] = f"""
                        No simulation logs found for timestamp {expected_event.timestamp}
                    """
                else:
                    log_text = " ".join(log)

                    expected_pattern = expected_event.expected_log_pattern
                    if not expected_pattern.search(log_text):
                        missing_sub_account_events[
                            f"{expected_event}"
                        ] = f"""
                            Expected pattern '{expected_pattern.pattern}' not found in {log}
                        """

            # Add all logs to dict for easier debugging
            if missing_sub_account_events:
                missing_sub_account_events["full logs"] = str(logs_with_timestamp)

            return missing_sub_account_events

        self.assertExpectations(
            expected_sub_accounts,
            logs_with_timestamp,
            get_missing_sub_account_events,
            description,
        )

    def run_test_scenario(
        self,
        test_scenario: SimulationTestScenario,
        expected_simulation_error: vault_caller.VaultException | None = None,
        smart_contracts: list | None = None,
    ):
        """
        run_test_scenario will run the provided test case scenario.
        The platform erroneously returns an API rejection instead of a simulation result
        when Rejections are returned in hooks other than pre-posting.
        Consequently no Sub-Test expectations may be set if a simulation error is expected.

        """
        setup_events: list[SimulationEvent] = []
        smart_contracts = [] if smart_contracts is None else smart_contracts
        supervisor_contract_code = None
        supervisee_version_id_mapping = None
        supervisor_contract_version_id = None
        supervisor_contract_config = None
        self.use_v1_accounts = test_scenario.use_v1_accounts

        if test_scenario.contract_config and test_scenario.supervisor_config:
            log.warning(
                "Both supervisor and contract config detected, "
                "setup events will be based on supervisor config"
            )

        elif test_scenario.supervisor_config:
            setup_events.extend(get_supervisor_setup_events(test_scenario))
            if test_scenario.supervisor_config.supervisor_file_path:
                supervisor_contract_code = load_file_contents(
                    test_scenario.supervisor_config.supervisor_file_path
                )
            else:
                supervisor_contract_code = test_scenario.supervisor_config.supervisor_contract
            supervisor_contract_version_id = (
                test_scenario.supervisor_config.supervisor_contract_version_id
            )
            supervisee_version_id_mapping = {
                supervisee_contract.clu_resource_id: supervisee_contract.smart_contract_version_id
                for supervisee_contract in test_scenario.supervisor_config.supervisee_contracts
                if supervisee_contract.clu_resource_id
            }
            smart_contracts.extend(test_scenario.supervisor_config.supervisee_contracts)

            supervisor_contract_config = test_scenario.supervisor_config

        elif test_scenario.contract_config:
            setup_events.extend(get_contract_setup_events(test_scenario))
            smart_contracts.append(test_scenario.contract_config)

        else:
            raise ValueError("Test scenario must have supervisor or contract config!")

        if expected_simulation_error and self.assertions_exist_in_subtests(test_scenario.sub_tests):
            raise ValueError(
                "Test scenario should not contain expectations when a simulation error is expected."
            )
        internal_accounts = test_scenario.internal_accounts or self.internal_accounts
        self.internal_accounts_mapping = internal_accounts

        flag_definition_ids = test_scenario.flag_definition_ids or self.flag_definition_ids
        parameters = test_scenario.parameters or self.parameters
        calendar_ids = test_scenario.calendar_ids or self.calendar_ids
        events, derived_param_outputs = compile_chrono_events(
            test_scenario=test_scenario,
            setup_events=setup_events,
            vault_version=self.vault_version,
        )

        contract_codes = get_contract_contents(smart_contracts)

        received_error: Exception | None = None
        try:
            res = self.client.simulate_smart_contract(
                start_timestamp=test_scenario.start,
                end_timestamp=test_scenario.end,
                supervisor_contract_code=supervisor_contract_code,
                supervisor_contract_version_id=supervisor_contract_version_id,
                supervisee_version_id_mapping=supervisee_version_id_mapping,
                contract_codes=contract_codes,
                smart_contract_version_ids=[
                    contract.smart_contract_version_id for contract in smart_contracts
                ],
                templates_parameters=[contract.template_params for contract in smart_contracts],
                internal_account_ids=internal_accounts,
                contract_config=test_scenario.contract_config,
                supervisor_contract_config=supervisor_contract_config,
                events=events,
                output_account_ids=[output[0] for output in derived_param_outputs],
                output_timestamps=[output[1] for output in derived_param_outputs],
                debug=test_scenario.debug,
                flag_definition_ids=flag_definition_ids,
                calendar_ids=calendar_ids,
                parameters=parameters,
                use_v1_accounts=self.use_v1_accounts,
                globally_owned_parameter_values=test_scenario.globally_owned_parameter_values,
                default_timezone=test_scenario.default_timezone,
            )
        except Exception as e:
            received_error = e
        finally:
            self.check_simulation_error(expected_simulation_error, received_error)
            # Breakout as simulation errored as expected. Do not run further assertions
            if expected_simulation_error:
                return

        self.perform_sub_tests(res, test_scenario.sub_tests)
        return res

    def perform_sub_tests(self, res: list[dict[str, Any]], sub_tests: list[SubTest]):
        # TODO: could add a boolean here to skip processing IAs in get_balances
        actual_value_balances: defaultdict[
            str, TimeSeries[defaultdict[BalanceDimensions, Balance]]
        ] = defaultdict(lambda: TimeSeries([], return_on_empty=defaultdict(lambda: Balance())))
        actual_booking_balances: defaultdict[
            str, TimeSeries[defaultdict[BalanceDimensions, Balance]]
        ] = defaultdict(lambda: TimeSeries([], return_on_empty=defaultdict(lambda: Balance())))

        account_violations: dict[datetime, dict[str, list[core_api.AccountViolation]]] = {}
        contract_violations: dict[datetime, dict[str, list[core_api.ContractViolation]]] = {}
        posting_violations: dict[datetime, dict[str, list[core_api.PostingViolation]]] = {}

        if self.vault_version < Version("5.7.0"):
            actual_value_balances = get_balances(res)
        else:
            actual_value_balances, actual_booking_balances = get_value_and_booking_balances(res)
            account_violations, contract_violations, posting_violations = get_violations(res)
        if not self.use_v1_accounts:
            # Internal Account balances are not populated when using Accounts V2
            # so we need to manually aggregate them
            internal_account_balances = get_internal_account_balances(
                res, self.internal_accounts_mapping
            )
            # Override the empty balance entries for IAs with the derived balances.
            # We don't want to generate booking balance views for internal accounts.
            actual_value_balances.update(internal_account_balances)

        logs_with_timestamp = get_logs_with_timestamp(res)
        derived_parameters = get_derived_parameters(res)
        contract_notifications = get_contract_notifications(res)
        posting_enrichments = get_posting_enrichments(res)
        account_attribute_values = get_account_attribute_values(res)
        actual_net_balances = get_net_balances(res)

        for sub_test in sub_tests:
            if sub_test.expected_balances_at_ts and sub_test.expected_value_balances_at_ts:
                raise ValueError(
                    "cannot provide both expected_balances_at_ts and expected_value_balances_at_ts"
                )

            if sub_test.expected_net_balances and (
                sub_test.expected_balances_at_ts or sub_test.expected_value_balances_at_ts
            ):
                log.warning(
                    "expected_net_balances is the recommended way to assert all balances."
                    " It is advised to update your test to use this approach exclusively."
                )

            if sub_test.expected_net_balances:
                self.check_live_balances_v2(
                    sub_test.expected_net_balances,
                    actual_net_balances,
                    sub_test.description,
                )
            expected_value_balances_at_ts = (
                sub_test.expected_value_balances_at_ts or sub_test.expected_balances_at_ts
            )
            if expected_value_balances_at_ts:
                self.check_balances_by_ts(
                    expected_value_balances_at_ts,
                    actual_value_balances,
                    sub_test.description,
                )
            if sub_test.expected_booking_balances_at_ts:

                def check_no_internal_account_ids_provided(
                    expected_booking_balances_at_ts, internal_accounts_mapping
                ):
                    if internal_accounts_mapping is None:
                        return
                    for expected_booking_balances in expected_booking_balances_at_ts.values():
                        for account_id in expected_booking_balances.keys():
                            if account_id in internal_accounts_mapping.keys():
                                raise ValueError(
                                    "cannot assert booking balances for internal account ID"
                                )

                check_no_internal_account_ids_provided(
                    sub_test.expected_booking_balances_at_ts, self.internal_accounts_mapping
                )
                self.check_balances_by_ts(
                    sub_test.expected_booking_balances_at_ts,
                    actual_booking_balances,
                    sub_test.description,
                )
            if sub_test.expected_schedules:
                self.check_schedule_processed(
                    sub_test.expected_schedules, res, sub_test.description
                )
            if sub_test.expected_account_activation_rejections:
                self.check_account_activation_rejections(
                    sub_test.expected_account_activation_rejections,
                    logs_with_timestamp,
                    sub_test.description,
                )
            if sub_test.expected_account_conversion_rejections:
                self.check_account_conversion_rejections(
                    sub_test.expected_account_conversion_rejections,
                    logs_with_timestamp,
                    sub_test.description,
                )
            if sub_test.expected_account_deactivation_rejections:
                self.check_account_deactivation_rejections(
                    sub_test.expected_account_deactivation_rejections,
                    logs_with_timestamp,
                    sub_test.description,
                )
            if sub_test.expected_posting_rejections:
                self.check_posting_rejections(
                    sub_test.expected_posting_rejections,
                    logs_with_timestamp,
                    sub_test.description,
                )
            if sub_test.expected_parameter_change_rejections:
                self.check_parameter_change_rejections(
                    sub_test.expected_parameter_change_rejections,
                    logs_with_timestamp,
                    sub_test.description,
                )
            if sub_test.expected_derived_parameters:
                self.check_derived_parameters(
                    sub_test.expected_derived_parameters,
                    derived_parameters,
                    sub_test.description,
                )
            if sub_test.expected_contract_notifications:
                self.check_contract_notifications(
                    sub_test.expected_contract_notifications,
                    contract_notifications,
                    sub_test.description,
                )
            if sub_test.expected_contract_errors:
                self.check_contract_errors(
                    sub_test.expected_contract_errors,
                    logs_with_timestamp,
                    sub_test.description,
                )
            if sub_test.expected_posting_enrichments:
                self.check_posting_enrichments(
                    sub_test.expected_posting_enrichments,
                    posting_enrichments,
                    sub_test.description,
                )
            if sub_test.expected_account_violations:
                self.check_account_violations(
                    sub_test.expected_account_violations, account_violations, sub_test.description
                )
            if sub_test.expected_contract_violations:
                self.check_contract_violations(
                    sub_test.expected_contract_violations, contract_violations, sub_test.description
                )
            if sub_test.expected_posting_violations:
                self.check_posting_violations(
                    sub_test.expected_posting_violations, posting_violations, sub_test.description
                )
            if sub_test.expected_account_attribute_values:
                self.check_account_attribute_values(
                    sub_test.expected_account_attribute_values,
                    account_attribute_values,
                    sub_test.description,
                )
            if sub_test.expected_sub_accounts:
                self.check_sub_account_events(
                    sub_test.expected_sub_accounts,
                    logs_with_timestamp,
                    sub_test.description,
                )

    def run_simulation_test(
        self,
        request: sim.SimulateRequest,
        sub_tests: list[SubTest],
        debug: bool = False,
    ) -> list[dict[str, Any]]:
        res = self.client.simulate(request, debug=debug)
        self.perform_sub_tests(res, sub_tests)
        return res


def get_contract_contents(contract_configs: list[ContractConfig]) -> list[str]:
    return [
        (
            contract_config.contract_content
            if contract_config.contract_content
            else load_file_contents(contract_config.contract_file_path)  # type: ignore
        )
        for contract_config in contract_configs
    ]


def compile_chrono_events(
    test_scenario: SimulationTestScenario,
    setup_events: list[SimulationEvent],
    vault_version: Version,
) -> tuple[list[SimulationEvent], list[tuple[str, datetime]]]:
    """
    Combines setup events with custom events from test scenario subtests.
    Sorts events chronologically.

    :param test_scenario: SimulationTestScenario
    :param setup_events: SimulationEvents generated by helper methods, e.g.
    account/plan creations or plan association events
    :returns: list of setup events + custom scenario events, and list of require derived param
     outputs as tuple of account id and datetime
    """
    previous_subtest_last_event_ts = datetime.min.replace(tzinfo=timezone.utc)
    previous_subtest_last_assertion_ts = datetime.min.replace(tzinfo=timezone.utc)
    current_subtest_first_event_ts = datetime.max.replace(tzinfo=timezone.utc)
    current_subtest_first_assertion_ts = datetime.max.replace(tzinfo=timezone.utc)
    assertion_ts: list[datetime] = []
    events: list[SimulationEvent] = []
    derived_param_outputs: list[tuple[str, datetime]] = []

    for sub_test in test_scenario.sub_tests:
        if sub_test.events:
            current_subtest_first_event_ts = sub_test.events[0].time

            if current_subtest_first_event_ts < previous_subtest_last_event_ts:
                log.warning(
                    f'Subtest "{sub_test.description}" contains '
                    "event timestamp before the previous one."
                )

            previous_subtest_last_event_ts = sub_test.events[-1].time
            events.extend(sub_test.events)

        if sub_test.expected_balances_at_ts:
            assertion_ts.extend(sub_test.expected_balances_at_ts.keys())

        if sub_test.expected_net_balances:
            assertion_ts.extend(sub_test.expected_net_balances.keys())

        if sub_test.expected_posting_rejections:
            # Raise an error here if plan_id is set and the Vault version is less than 5.2.0.
            # Only the account_id is supported for earlier versions. The check is done here rather
            # than on the ExpectedRejection instantiation since the vault_version is needed.
            if vault_version < Version("5.2.0") and any(
                expected_rejection.plan_id
                for expected_rejection in sub_test.expected_posting_rejections
            ):
                raise ValueError(
                    "Prior to Vault 5.2.0 expected posting rejections must be made against the "
                    "account_id instead of plan_id."
                )
            assertion_ts.extend(
                expected_rejection.timestamp
                for expected_rejection in sub_test.expected_posting_rejections
            )
        if sub_test.expected_parameter_change_rejections:
            assertion_ts.extend(
                expected_rejection.timestamp
                for expected_rejection in sub_test.expected_parameter_change_rejections
            )
        if sub_test.expected_schedules:
            assertion_ts.extend(
                runtime
                for expected_schedule in sub_test.expected_schedules
                for runtime in expected_schedule.run_times
            )

        if sub_test.expected_derived_parameters:
            for expected_derived_param in sub_test.expected_derived_parameters:
                assertion_ts.append(expected_derived_param.timestamp)
                derived_param_outputs.append(
                    (
                        expected_derived_param.account_id,
                        expected_derived_param.timestamp,
                    )
                )

        if assertion_ts:
            sorted_assertion_ts = sorted(assertion_ts)
            current_subtest_first_assertion_ts = sorted_assertion_ts[0]

            if current_subtest_first_assertion_ts < previous_subtest_last_assertion_ts:
                log.warning(
                    f'Subtest "{sub_test.description}" contains '
                    "assertion timestamp before the previous one."
                )

            previous_subtest_last_assertion_ts = sorted_assertion_ts[-1]
            assertion_ts.clear()

        if vault_version < Version("5.7.0"):
            expected_violations = []

            if sub_test.expected_account_violations:
                expected_violations.append("expected_account_violations")
            if sub_test.expected_posting_violations:
                expected_violations.append("expected_posting_violations")
            if sub_test.expected_contract_violations:
                expected_violations.append("expected_contract_violations")

            if expected_violations:
                raise ValueError(
                    f"Subtest '{sub_test.description}' contains {expected_violations} which are "
                    f"unsupported prior to Vault 5.7.0."
                )

    if (
        previous_subtest_last_event_ts > test_scenario.end
        or previous_subtest_last_assertion_ts > test_scenario.end
    ):
        log.warning("last assertion or event happens outside of simulation window")

    all_events = sorted(setup_events + events, key=lambda event: event.time)

    return all_events, derived_param_outputs


def convert_sim_balance(sim_balance: dict[str, str]) -> tuple[BalanceDimensions, Balance]:
    """
    Converts a simulation balance to a BalanceDefaultDict entry.
    :param sim_balance: simulation balance to convert
    """
    return (
        BalanceDimensions(
            address=sim_balance["account_address"],
            asset=sim_balance["asset"],
            denomination=sim_balance["denomination"],
            phase=sim_balance["phase"],
        ),
        Balance(
            Decimal(sim_balance["total_credit"]),
            Decimal(sim_balance["total_debit"]),
            Decimal(sim_balance["amount"]),
        ),
    )


def get_violations(res: list[dict[str, Any]]) -> tuple[
    dict[datetime, dict[str, list[core_api.AccountViolation]]],
    dict[datetime, dict[str, list[core_api.ContractViolation]]],
    dict[datetime, dict[str, list[core_api.PostingViolation]]],
]:
    event_time_to_account_violations: defaultdict[
        datetime, defaultdict[str, list[core_api.AccountViolation]]
    ] = defaultdict(lambda: defaultdict(list))
    event_time_to_contract_violations: defaultdict[
        datetime, defaultdict[str, list[core_api.ContractViolation]]
    ] = defaultdict(lambda: defaultdict(list))
    event_time_to_posting_violations: defaultdict[
        datetime, defaultdict[str, list[core_api.PostingViolation]]
    ] = defaultdict(lambda: defaultdict(list))

    for event_timestamp, pi in _get_posting_instructions(res):
        client_tx_id = pi["client_transaction_id"]
        event_time_to_account_violations[event_timestamp][client_tx_id].extend(
            [
                core_api.AccountViolation.model_validate(account_violation)
                for account_violation in pi["account_violations"]
            ]
        )
        event_time_to_contract_violations[event_timestamp][client_tx_id].extend(
            [
                core_api.ContractViolation.model_validate(contract_violation)
                for contract_violation in pi["contract_violations"]
            ]
        )
        event_time_to_posting_violations[event_timestamp][client_tx_id].extend(
            [
                core_api.PostingViolation.model_validate(posting_violation)
                for posting_violation in pi["posting_violations"]
            ]
        )

    return (
        {k: dict(v) for k, v in event_time_to_account_violations.items()},
        {k: dict(v) for k, v in event_time_to_contract_violations.items()},
        {k: dict(v) for k, v in event_time_to_posting_violations.items()},
    )


def _get_posting_instructions(
    res: list[dict[str, Any]],
) -> Iterator[tuple[datetime, dict[str, Any]]]:
    for result in res:
        result_inner = result["result"]
        event_timestamp = parser.parse(result_inner["timestamp"])
        for pib_created_events in result_inner["posting_instruction_batch_created_events"]:
            posting_instructions = pib_created_events["posting_instruction_batch"][
                "posting_instructions"
            ]
            for posting_instruction in posting_instructions:
                yield event_timestamp, posting_instruction


def get_balances(res: list[dict[str, Any]]) -> DefaultDict[str, TimeSeries]:
    """
    Returns a Balance timeseries by value_timestamp for each account
    The timeseries entries map a given datetime to a DefaultDict of BalanceDimensions to a
    TimeSeries of Balances.

    WARNING: We do not support multiple events with same value and event_timestamp. Although the
    simulator may enable this, it is not reflective of real Vault behaviour as balance consistency
    constraints and timing would not allow identical insertion_timestamps
    :param res: output from simulation endpoint
    :return: account ids to corresponding balance timeseries
    """

    # This stores account id -> value_timestamp -> BalanceDimensions -> (event_timestamp, balance)
    account_balance_updates: defaultdict[
        str, defaultdict[datetime, defaultdict[BalanceDimensions, list[tuple[datetime, Balance]]]]
    ] = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: [])))

    # result data structure for balances is 'balances' -> account_id -> 'balances' -> list[balance]
    for result in res:
        result_inner = result["result"]
        for balances in result_inner["balances"].values():
            balances_inner = balances["balances"]
            for sim_balance in balances_inner:
                # results are ordered by event_timestamp so if there are multiple per
                #  value_timestamp we don't need to worry about ordering them
                event_timestamp = parser.parse(result_inner["timestamp"])
                value_timestamp = parser.parse(sim_balance["value_time"])
                dimensions, balance = convert_sim_balance(sim_balance)
                account_balance_updates[sim_balance["account_id"]][value_timestamp][
                    dimensions
                ].append((event_timestamp, balance))

    # This stores account id -> TimeSeries [BalanceDefaultDict]
    account_balance_timeseries: defaultdict[
        str, TimeSeries[defaultdict[BalanceDimensions, Balance]]
    ] = defaultdict(lambda: TimeSeries([], return_on_empty=defaultdict(lambda: Balance())))

    account_balance_timeseries = convert_balance_updates_to_balance_timeseries(
        account_balance_updates, account_balance_timeseries
    )

    return account_balance_timeseries


def get_value_and_booking_balances(res: list[dict[str, Any]]) -> tuple[
    DefaultDict[str, TimeSeries],
    DefaultDict[str, TimeSeries],
]:
    """
    Returns a Balance timeseries for value and booking balances by timestamp for each account.
    The timeseries entries map a given datetime to a DefaultDict of BalanceDimensions to a
    TimeSeries of Balances.

    WARNING: We only retrieve the balances targeting the Account, not any Sub-Accounts.
    Use `get_balances_v2()` for Sub-Account balance support.

    WARNING: We do not support multiple events with same value and event_timestamp. Although the
    simulator may enable this, it is not reflective of real Vault behaviour as balance consistency
    constraints and timing would not allow identical insertion_timestamps

    :param res: output from simulation endpoint
    :return: a tuple with each value being the account ids to corresponding value/booking balance
    timeseries
    """
    # This stores account id -> timestamp -> BalanceDimensions -> (event_timestamp, balance)
    account_value_balance_updates: defaultdict[
        str, defaultdict[datetime, defaultdict[BalanceDimensions, list[tuple[datetime, Balance]]]]
    ] = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: [])))
    account_booking_balance_updates: defaultdict[
        str, defaultdict[datetime, defaultdict[BalanceDimensions, list[tuple[datetime, Balance]]]]
    ] = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: [])))

    for result in res:
        result_inner = result["result"]
        event_timestamp = parser.parse(result_inner["timestamp"])
        for pib_created_event in result_inner["posting_instruction_batch_created_events"]:
            for live_balance in pib_created_event["live_balances"]:
                account_id = live_balance["account_id"]
                for balance in live_balance["value_balances"]:
                    # Balances v1 used 1970/01/01 when initialising the balances but in balances v2
                    # it is now empty. We use min time so we can create a time series of balances.
                    balance_timestamp = datetime.min.replace(tzinfo=timezone.utc)
                    if balance["timestamp"] is not None:
                        balance_timestamp = parser.parse(balance["timestamp"])
                    dimensions, balance = convert_sim_balance(balance)
                    account_value_balance_updates[account_id][balance_timestamp][dimensions].append(
                        (event_timestamp, balance)
                    )
                for balance in live_balance["booking_balances"]:
                    # Balances v1 used 1970/01/01 when initialising the balances but in balances v2
                    # it is now empty. We use min time so we can create a time series of balances.
                    balance_timestamp = datetime.min.replace(tzinfo=timezone.utc)
                    if balance["timestamp"] is not None:
                        balance_timestamp = parser.parse(balance["timestamp"])
                    dimensions, balance = convert_sim_balance(balance)
                    account_booking_balance_updates[account_id][balance_timestamp][
                        dimensions
                    ].append((event_timestamp, balance))

    # This stores account id -> TimeSeries [BalanceDefaultDict]
    account_value_balance_timeseries: defaultdict[
        str, TimeSeries[defaultdict[BalanceDimensions, Balance]]
    ] = defaultdict(lambda: TimeSeries([], return_on_empty=defaultdict(lambda: Balance())))
    account_booking_balance_timeseries: defaultdict[
        str, TimeSeries[defaultdict[BalanceDimensions, Balance]]
    ] = defaultdict(lambda: TimeSeries([], return_on_empty=defaultdict(lambda: Balance())))

    account_value_balance_timeseries = convert_balance_updates_to_balance_timeseries(
        account_value_balance_updates, account_value_balance_timeseries
    )

    account_booking_balance_timeseries = convert_balance_updates_to_balance_timeseries(
        account_booking_balance_updates, account_booking_balance_timeseries
    )

    return account_value_balance_timeseries, account_booking_balance_timeseries


def get_net_balances(res: list[dict[str, Any]]) -> dict[datetime, NetBalances]:
    """
    Extracts balances from the simulation response live_balances field
    and maps them to NetBalances value and booking balances.

    :param res: Output from simulation endpoint.
    :return: A dict mapping event timestamp (datetime) to balances.
    """
    event_timestamp_to_balances: dict[datetime, NetBalances] = {}

    for result in res:
        result_inner = result["result"]
        event_timestamp = parser.parse(result_inner["timestamp"])

        if event_timestamp not in event_timestamp_to_balances:
            event_timestamp_to_balances[event_timestamp] = NetBalances(
                value_net_balances=[],
                booking_net_balances=[],
            )

        balance_lists = event_timestamp_to_balances[event_timestamp]

        pib_created_events = result_inner.get("posting_instruction_batch_created_events") or []
        for pib_created_event in pib_created_events:
            for live_balance in pib_created_event.get("live_balances") or []:
                # live_balances is a list of live value and booking balance for all of the affected
                # customer accounts.
                # Each element contains account_id, value_balances, and booking_balances.

                account_id = live_balance["account_id"]

                for account_value_balance_raw in live_balance.get("value_balances") or []:
                    balance_dict = dict(account_value_balance_raw)
                    balance_dict["account_id"] = account_id

                    balanceV2 = dict_to_net_balance(balance_dict)
                    balance_lists.value_net_balances.append(balanceV2)

                for account_booking_balance_raw in live_balance.get("booking_balances") or []:
                    balance_dict = dict(account_booking_balance_raw)
                    balance_dict["account_id"] = account_id

                    balanceV2 = dict_to_net_balance(balance_dict)
                    balance_lists.booking_net_balances.append(balanceV2)

    return event_timestamp_to_balances


def convert_balance_updates_to_balance_timeseries(
    balance_updates: defaultdict[
        str, defaultdict[datetime, defaultdict[BalanceDimensions, list[tuple[datetime, Balance]]]]
    ],
    balance_timeseries: defaultdict[str, TimeSeries[defaultdict[BalanceDimensions, Balance]]],
) -> defaultdict[str, TimeSeries[defaultdict[BalanceDimensions, Balance]]]:
    for account_id, balance_map in balance_updates.items():
        # By not resetting the entries for each value_timestamp, we ensure we get the most recent
        # non-default value for given dimensions
        value_timestamp_entries: list[tuple[datetime, defaultdict[BalanceDimensions, Balance]]] = []
        dimension_entries: defaultdict[BalanceDimensions, Balance] = defaultdict(lambda: Balance())

        for value_timestamp, balance_dict in balance_map.items():
            for dimensions, event_ts_balance_list in balance_dict.items():
                dimension_entries[dimensions] = event_ts_balance_list[-1][1]

            value_timestamp_entries.append((value_timestamp, deepcopy(dimension_entries)))

        balance_timeseries[account_id] = TimeSeries(
            value_timestamp_entries, return_on_empty=defaultdict(lambda: Balance())
        )
    return balance_timeseries


def get_internal_account_balances(
    res: list[dict[str, Any]], internal_accounts: dict[str, str] | None
) -> defaultdict[str, TimeSeries[defaultdict[BalanceDimensions, Balance]]]:
    # This stores account id -> TimeSeries [BalanceDefaultDict]
    internal_account_balance_timeseries: defaultdict[
        str, TimeSeries[defaultdict[BalanceDimensions, Balance]]
    ] = defaultdict(lambda: TimeSeries([], return_on_empty=defaultdict(lambda: Balance())))

    # return an empty balance timeseries if there are no internal accounts to consider
    if not internal_accounts:
        return internal_account_balance_timeseries

    # This stores (account id, BalanceDimensions) -> balance
    running_balances: defaultdict[tuple[str, BalanceDimensions], Balance] = defaultdict(
        lambda: Balance()
    )

    # This stores account id -> value_timestamp -> BalanceDimensions -> (event_timestamp, balance)
    account_balance_updates: defaultdict[
        str, defaultdict[datetime, defaultdict[BalanceDimensions, list[tuple[datetime, Balance]]]]
    ] = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: [])))

    for result in res:
        result_inner = result["result"]
        posting_instruction_batches = result_inner["posting_instruction_batches"]
        if not posting_instruction_batches:
            continue

        event_timestamp = parser.parse(result_inner["timestamp"])
        inflight_balances = get_inflight_balances(posting_instruction_batches, internal_accounts)
        for account_id, inflight_balance in inflight_balances.items():
            for value_ts, (dimension, balance) in inflight_balance.items():
                # update the running balances with the inflight balance for the given account_id
                running_balances[(account_id, dimension)] += balance
                account_balance_updates[account_id][value_ts][dimension].append(
                    (event_timestamp, running_balances[(account_id, dimension)])
                )

    internal_account_balance_timeseries = convert_balance_updates_to_balance_timeseries(
        account_balance_updates, internal_account_balance_timeseries
    )
    return internal_account_balance_timeseries


def get_inflight_balances(
    posting_instruction_batches: list[dict[str, Any]],
    internal_accounts: dict[str, str],
) -> dict[str, dict[datetime, tuple[BalanceDimensions, Balance]]]:
    # This stores account id -> value_timestamp -> BalanceDimensions -> balance.
    # The nested defaultdict[BalanceDimensions, Balance] is to make it easy to
    # sum the balances per dimension
    committed_postings_per_ia: defaultdict[
        str, defaultdict[datetime, defaultdict[BalanceDimensions, Balance]]
    ] = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: Balance())))
    internal_account_ids = set(internal_accounts.keys())

    for pib in posting_instruction_batches:
        pib_value_timestamp_str = pib.get("value_timestamp")

        for pi in pib["posting_instructions"]:
            pi_value_timestamp_str = pib_value_timestamp_str or pi.get("value_timestamp")
            if not pi_value_timestamp_str:
                raise ValueError(
                    "Simulation response is malformed: `value_timestamp` is not set on either PI "
                    "or PIB level."
                )
            pi_value_timestamp = parser.parse(pi_value_timestamp_str)

            for posting in pi["committed_postings"]:
                account_id = posting["account_id"]
                # do not consider non-internal accounts
                if account_id not in internal_account_ids:
                    continue

                liability = True if internal_accounts[account_id] == "LIABILITY" else False
                balance_dimension, balance = convert_committed_posting(posting, liability)
                committed_postings_per_ia[account_id][pi_value_timestamp][
                    balance_dimension
                ] += balance

    # This stores account id -> value_timestamp -> (BalanceDimensions, balance)
    balance_updates_by_ts: dict[str, dict[datetime, tuple[BalanceDimensions, Balance]]] = {
        account_id: {
            value_ts: (balance_dim, balance)
            for value_ts, balance_dict in inflight_balance.items()
            for balance_dim, balance in balance_dict.items()
        }
        for account_id, inflight_balance in committed_postings_per_ia.items()
    }

    return balance_updates_by_ts


def convert_committed_posting(
    committed_posting: dict[str, Any], liability: bool
) -> tuple[BalanceDimensions, Balance]:
    """
    Convert a committed posting object from the simulation response to the
    respective (BalanceDimension, Balance) tuple, using the Tside of the account
    to calculate net amount.

    :param committed_posting: committing posting dict from sim response.
    :param liability: True if the account's Tside is liability, False for asset.
    :return: tuple of BalanceDimension and Balance
    """
    posting_amount = Decimal(committed_posting["amount"])
    credit = posting_amount if committed_posting["credit"] else Decimal(0)
    debit = Decimal(0) if committed_posting["credit"] else posting_amount
    amount = (credit - debit) if liability else (debit - credit)

    return (
        BalanceDimensions(
            address=committed_posting["account_address"],
            asset=committed_posting["asset"],
            denomination=committed_posting["denomination"],
            phase=committed_posting["phase"],
        ),
        Balance(
            credit=credit,
            debit=debit,
            net=amount,
        ),
    )


def get_derived_parameters(res: list[dict[str, Any]]) -> dict[str, TimeSeries]:
    """
    Returns a dictionary of derived parameters timeseries, using the account id as a key
    :param res: The response from simulation endpoint
    """

    outputs = defaultdict(lambda: [])

    for result in res:
        derived_params = result["result"]["derived_params"]
        if derived_params:
            timestamp = parser.parse(result["result"]["timestamp"])
            for account_id in derived_params:
                outputs[account_id].append((timestamp, derived_params[account_id]["values"]))

    return {k: TimeSeries(outputs[k]) for k in outputs}


def get_contract_notifications(
    res: list[dict[str, Any]],
) -> dict[str, dict[str, list[tuple[datetime, dict[str, str]]]]]:
    """
    Extract notifications from simulation response
    :param res: output from simulation endpoint
    :return: dict of resource id to notification type to list of notifications
    """

    # resource id -> notification type -> [(datetime, notification contents)]
    outputs: dict[str, dict[str, list[tuple[datetime, dict[str, str]]]]] = defaultdict(
        lambda: defaultdict(lambda: ([]))
    )

    for result in res:
        if "contract_notification_events" in result["result"]:
            timestamp = parser.parse(result["result"]["timestamp"])
            for resource_id, notifications in result["result"][
                "contract_notification_events"
            ].items():
                for notification in notifications["contract_notification_events"]:
                    outputs[resource_id][notification["notification_type"]].append(
                        (timestamp, notification)
                    )
    return outputs


def get_account_attribute_values(
    res: list[dict[str, Any]],
) -> dict[str, list[core_api.AccountAttributeValue]]:
    """
    Extract account attribute value from simulation response
    :param res: output from simulation endpoint
    :return: dict of resource id to account attribute values
    """

    # resource id -> list of account attribute values
    resource_id_to_account_attribute_values_list: dict[str, list] = defaultdict(lambda: ([]))

    for result in res:
        if "account_attribute_values" in result["result"]:
            for resource_id, account_attribute_values in result["result"][
                "account_attribute_values"
            ].items():
                for account_attribute_value in account_attribute_values["account_attribute_values"]:
                    resource_id_to_account_attribute_values_list[resource_id].append(
                        core_api.AccountAttributeValue(**account_attribute_value)
                    )

    return resource_id_to_account_attribute_values_list


def get_calendar_created(res: list[dict[str, Any]], calendar_id: str) -> bool:
    """
    Returns True if log found for create_calendar
    :param res: output from simulation endpoint
    :param calendar_id: calendar id
    :return: true if event found in logs
    """

    calendar_id_created_substr = f'created calendar with id "{calendar_id}"'

    return any(_get_logs_with_substring(res, calendar_id_created_substr))


def get_calendar_event_created(res: list[dict[str, Any]], calendar_id: str) -> bool:
    """
    Returns True if log found for create_calendar_event
    :param res: output from simulation endpoint
    :param calendar_id: calendar id
    :return: true if event found in logs
    """

    calendar_created_substr = f'created calendar event for calendar "{calendar_id}"'

    return any(_get_logs_with_substring(res, calendar_created_substr))


def get_flag_definition_created(res: list[dict[str, Any]], flag_definition_id: str) -> bool:
    """
    Returns True if log found for create_flag_definition_event
    :param res: output from simulation endpoint
    :return: true if event found in logs
    """

    flag_definition_created_substr = f'created flag definition "{flag_definition_id}"'

    return any(_get_logs_with_substring(res, flag_definition_created_substr))


def get_flag_created(
    res: list[dict[str, Any]], flag_definition_id: str, account_id: str = MAIN_ACCOUNT
) -> bool:
    """
    Returns True if log found for create_flag_event
    :param res: output from simulation endpoint
    :param flag_definition_id: flag definition id
    :param account_id: internal or customer account id
    :return: true if event found in logs
    """

    flag_created_substr = f'"{flag_definition_id}" for account "{account_id}"'

    return any(_get_logs_with_substring(res, flag_created_substr))


def get_postings(
    res: list[dict[str, Any]],
    account_id: str = MAIN_ACCOUNT,
    balance_dimensions: BalanceDimensions | None = None,
) -> list[dict[str, Any]]:
    """
    Returns committed postings for specified account_id and balance address
    :param res: output from simulation endpoint
    :param account_id: internal or customer account id
    :param balance_dimensions: balance dimensions
    :return: committed postings
    """
    balance_dimensions = balance_dimensions or BalanceDimensions()
    pibs = (
        pibs
        for response in res
        for pibs in response["result"]["posting_instruction_batches"]
        if response["result"]["posting_instruction_batches"]
    )

    posting_instructions = (pi for pib in pibs for pi in pib["posting_instructions"])

    return [
        committed_posting
        for pi in posting_instructions
        for committed_posting in pi["committed_postings"]
        if committed_posting["account_address"] == balance_dimensions.address
        and committed_posting["account_id"] == account_id
    ]


def get_posting_instruction_batch(
    res: list[dict[str, Any]], event_type: str
) -> dict[str, TimeSeries]:
    """
    Returns a posting instruction timeseries by timestamp for each target_account_id.
    :param res: output from simulation endpoint
    :param event_type: event type
    :return: list of posting instruction events
    """
    # this stores target_account_id -> timestamp -> posting instruction records
    posting_instructions: defaultdict[str, defaultdict[datetime, list[dict]]] = defaultdict(
        lambda: defaultdict(lambda: [])
    )
    for result in res:
        result_data = result["result"]
        event_timestamp = parser.parse(result_data["timestamp"])

        for pibs in result_data["posting_instruction_batches"]:
            for pis in pibs["posting_instructions"]:
                if event_type not in pis:
                    continue

                posting_instructions[pis[event_type]["target_account_id"]][event_timestamp].append(
                    pis[event_type]
                )

    # this stores target_account_id -> (timestamp, posting instruction records)
    posting_instructions_timeseries: defaultdict[str, TimeSeries[list[dict]]] = defaultdict(
        lambda: TimeSeries([])
    )
    for account, timeseries in posting_instructions.items():
        posting_instructions_timeseries[account] = TimeSeries(
            [(timestamp, pi) for timestamp, pi in timeseries.items()], return_on_empty=[]
        )

    return posting_instructions_timeseries


def get_num_postings(
    res: list[dict[str, Any]],
    account_id: str = MAIN_ACCOUNT,
    balance_dimensions: BalanceDimensions | None = None,
) -> int:
    """
    Returns number of committed postings for specified account_id and balance address
    :param res: output from simulation endpoint
    :param account_id: internal or customer account id
    :param balance_dimensions: balance dimensions
    :return: number of comitted postings
    """
    balance_dimensions = balance_dimensions or BalanceDimensions()
    return len(get_postings(res, account_id, balance_dimensions))


def get_logs(res: list[dict[str, Any]]) -> str:
    """
    Returns all logs from simulation result
    :param res: output from simulation endpoint
    :return: logs from simulation endpoint
    """

    return "; ".join(
        (log for list_of_log_lists in res for log in list_of_log_lists["result"]["logs"])
    )


def get_account_logs(res: list[dict[str, Any]], account_id: str = MAIN_ACCOUNT) -> str:
    """
    Returns logs from simulation result for a specific account_id
    :param res: output from simulation endpoint
    :param account_id: internal or customer account id
    :return: logs from simulation endpoint for specific account ID
    """
    account_substr = f'account "{account_id}"'
    return "; ".join(_get_logs_with_substring(res, account_substr))


def create_supervisor_config(
    supervisor_contract: str,
    supervisor_contract_version_id: str,
    supervisees: list[SuperviseeConfig],
    global_params: list[CreateGlobalParameterEvent] | None = None,
) -> SupervisorConfig:
    """
    Creates a SupervisorConfig object based on the parameters supplied.
    :param supervisor_contract: supervisor contract file
    :param supervisor_contract_version_id: supervisor contract version ID
    :param supervisees: list of SuperviseeConfig objects
    """
    supervisee_contracts = []
    for supervisee in supervisees:
        account_config = [
            AccountConfig(
                account_id_base=f"{supervisee.account_name} ",
                instance_params=supervisee.instance_parameters,
                number_of_accounts=supervisee.instances,
            )
        ]

        contract_config = ContractConfig(
            clu_resource_id=supervisee.contract_id,
            contract_file_path=supervisee.contract_file,
            template_params=supervisee.template_parameters,
            smart_contract_version_id=supervisee.version,
            account_configs=account_config,
            linked_contract_modules=supervisee.linked_contract_modules,
        )

        supervisee_contracts.append(contract_config)

    return SupervisorConfig(
        supervisor_file_path=supervisor_contract,
        supervisee_contracts=supervisee_contracts,
        supervisor_contract_version_id=supervisor_contract_version_id,
        global_params=global_params,
    )


def get_plan_logs(res: list[dict[str, Any]], plan_id: str) -> str:
    """
    Returns plan logs from simulation result for a specific plan id
    :param res: output from simulation endpoint
    :param plan_id: plan instruction id
    :return: plan logs
    """
    plan_substr = f'plan "{plan_id}"'
    return "; ".join(_get_logs_with_substring(res, plan_substr))


def get_plan_created(
    res: list[dict[str, Any]], plan_id: str, supervisor_version_id: str = ""
) -> bool:
    """
    Returns True if plan has been created and False if plan creation information cannot be found
    in logs
    :param res: output from simulation endpoint
    :param plan_id: plan instruction id
    :param supervisor_version_id: supervisor contract version id
    :return: True if plan creation log exists in response
    """
    plan_created = f'created plan "{plan_id}"'
    if supervisor_version_id:
        plan_created += f' for supervisor contract version "{supervisor_version_id}"'

    return any(_get_logs_with_substring(res, plan_created))


def get_plan_assoc_created(res: list[dict[str, Any]], plan_id: str, account_id: str) -> bool:
    """
    Returns True if plan association has been created and False if plan association
    information cannot be found in logs
    :param res: output from simulation endpoint
    :param plan_id: plan instruction id
    :param account_id: customer account id
    :return: True if plan association creation log exists in response
    """
    plan_assoc_created = f'created account plan association for account "{account_id}"'
    plan_assoc_created += f' and plan "{plan_id}"'

    return any(_get_logs_with_substring(res, plan_assoc_created))


def get_module_link_created(
    res: list[dict[str, Any]], aliases: list[str], smart_contract_version_id: str
) -> bool:
    """
    Returns True if contract module links have been created and False if contract module links
    information cannot be found in logs
    :param res: output from simulation endpoint
    :param module_alias: alias of the contract module
    :param account_id: customer account id
    :return: True if contract module link log exists in response
    """
    contract_module_link_created = "created smart contract module versions link with id "
    aliases_as_str = "_".join(aliases)
    contract_module_link_created += (
        f'"sim_link_modules_{aliases_as_str}_with_contract_{smart_contract_version_id}"'
    )
    return any(_get_logs_with_substring(res, contract_module_link_created))


def get_logs_with_timestamp(res: list[dict[str, Any]]) -> defaultdict[datetime, list[str]]:
    """
    Returns all logs from simulation result with logs grouped by timestamp
    :param res: output from simulation endpoint
    :return: logs grouped by timestamp
    """

    list_of_logs = (
        {log["result"]["timestamp"]: log["result"]["logs"]} for log in res if log["result"]["logs"]
    )

    logs_with_timestamp: defaultdict[datetime, list[str]] = defaultdict(list)

    for result in list_of_logs:
        k, v = list(result.items())[0]
        logs_with_timestamp[parser.parse(k)] += v

    return logs_with_timestamp


def has_matching_processed_scheduled_event(
    logs: list[str], event_id: str, account_id: str = "", plan_id: str = ""
) -> bool:
    for_str = ""
    if account_id:
        for_str = f'for account "{account_id}"'
    elif plan_id:
        for_str = f'for plan "{plan_id}"'
    else:
        # This is prevented on the ExpectedSchedule already, but we raise just in case to avoid
        # accidentally matching to both accounts and plans given the partial matching approach
        raise ValueError("account_id or plan_id must be provided")

    # We allow for partial string matching to handle plan schedules that override account
    # schedules as this results in additional log information, but isn't useful from a test
    # assertion perspective
    return any(f'processed scheduled event "{event_id}" {for_str}' in log for log in logs)


def get_processed_scheduled_events(
    res: list[dict[str, Any]],
    event_id: str,
    account_id: str = "",
    plan_id: str = "",
) -> list[str]:
    """
    Returns a list of timestamps for processed scheduled events found for specific
    account id or plan id
    :param res: output from simulation endpoint
    :param event_id: id of the event
    :param account_id: internal or customer account id
    :param plan_id: account plan association id
    :return: list of timestamps
    """
    return [
        result["result"]["timestamp"]
        for result in res
        if has_matching_processed_scheduled_event(
            result["result"]["logs"], event_id, account_id, plan_id
        )
    ]


def print_json(print_identifier: str, json_obj: Any) -> None:
    print(
        f"{print_identifier}: "
        f"{json.dumps(json_obj, indent=4, sort_keys=True, cls=DecimalEncoder)}"
    )


def print_postings(
    res: list[dict[str, Any]],
    account_id: str = MAIN_ACCOUNT,
    balance_dimensions: BalanceDimensions | None = None,
) -> None:
    balance_dimensions = balance_dimensions or BalanceDimensions()
    postings = get_postings(res, account_id, balance_dimensions)
    print_json("Postings", postings)


def print_log(res: list[dict[str, Any]]) -> None:
    print_json("Event log", get_logs(res))


def _get_logs_with_substring(res: list[dict[str, Any]], substring: str) -> Generator:
    return (
        log
        for list_of_log_lists in res
        for log in list_of_log_lists["result"]["logs"]
        if substring in "".join(list_of_log_lists["result"]["logs"])
    )


def get_posting_enrichments(
    res: list[dict[str, Any]],
) -> dict[str, dict[str, str]]:
    """
    Extract posting enrichments from simulation response
    :param res: output from simulation endpoint
    :return: dict of account id to enrichment details
    """

    outputs: dict[str, dict[str, str]] = {}

    for result in res:
        result_data = result.get("result", {})

        for pib in result_data.get("posting_instruction_batches", []):
            for pi in pib.get("posting_instructions", []):
                enrichments = pi.get("enrichments", {})
                for account_id, enrichment in enrichments.items():
                    outputs[account_id] = enrichment.get("details", {})

    return outputs


class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, Decimal):
            return float(o)
        return super(DecimalEncoder, self).default(o)
