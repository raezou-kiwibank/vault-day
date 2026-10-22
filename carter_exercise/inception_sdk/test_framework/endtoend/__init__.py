# Copyright @ 2020 Thought Machine Group Limited. All rights reserved.
# flake8: noqa
# standard libs
import functools
import inspect
import logging
import os
import signal
import sys
import unittest
from typing import Callable

# third party
from semantic_version import Version

# inception sdk
import inception_sdk.common.python.flag_utils as flag_utils
import inception_sdk.test_framework.endtoend as endtoend
import inception_sdk.test_framework.endtoend.accounts_helper as accounts_helper
import inception_sdk.test_framework.endtoend.adjustments_helper as adjustments_helper
import inception_sdk.test_framework.endtoend.balances as balances_helper
import inception_sdk.test_framework.endtoend.contract_modules_helper as contract_modules_helper
import inception_sdk.test_framework.endtoend.contracts_helper as contracts_helper
import inception_sdk.test_framework.endtoend.core_api_helper as core_api_helper
import inception_sdk.test_framework.endtoend.data_loader_helper as data_loader_helper
import inception_sdk.test_framework.endtoend.helper as helper
import inception_sdk.test_framework.endtoend.kafka_helper as kafka_helper
import inception_sdk.test_framework.endtoend.posting_instructions_helper as posting_instructions_helper
import inception_sdk.test_framework.endtoend.postings as postings_helper
import inception_sdk.test_framework.endtoend.schedule_helper as schedule_helper
import inception_sdk.test_framework.endtoend.sub_accounts_helper as sub_accounts_helper
import inception_sdk.test_framework.endtoend.supervisors_helper as supervisors_helper
import inception_sdk.test_framework.endtoend.workflows_api_helper as workflows_api_helper
import inception_sdk.test_framework.endtoend.workflows_helper as workflows_helper
from inception_sdk.common.exceptions import TestSetupException
from inception_sdk.test_framework.common.config import FLAGS, EnvironmentPurpose, flags
from inception_sdk.test_framework.common.utils import (
    extract_parameters,
    safe_merge_dicts,
    set_e2e_ids,
)
from inception_sdk.vault.core_api import VaultCoreExtension

# SemVers with prerelease have the format 0.0.0-<prerelease>.
_DEFAULT_PRERELEASES_TO_EXCLUDE_FROM_SKIP_TEST = frozenset({"master", "test"})

log = logging.getLogger(__name__)
logging.basicConfig(
    level=os.environ.get("LOGLEVEL", "INFO"),
    format="%(asctime)s.%(msecs)03d - %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

FLAG_PREFIX = "INC_"

# e2e-specific flags
flags.DEFINE_boolean(
    name="use_kafka",
    default=os.getenv(FLAG_PREFIX + "USE_KAFKA", "True").lower() == "true",
    help="Indicates whether the framework will attempt to use kafka helpers, where available."
    f" This may be forced to true for certain test types. Can also be set via env variable"
    f" {FLAG_PREFIX + 'USE_KAFKA'}.",
)

flags.DEFINE_boolean(
    name="use_sync_postings",
    default=os.getenv(FLAG_PREFIX + "USE_SYNC_POSTINGS", "False").lower() == "true",
    help="Configures the framework to use the synchronous postings API. Can also be set"
    f" via env variable {FLAG_PREFIX + 'USE_SYNC_POSTINGS'}.",
)

testhandle = endtoend.helper.TestInstance()
testhandle.post_init()


def sig_handler(sig, frame):
    endtoend.helper.teardown_test_resources()
    endtoend.helper.teardown_shared_resources()
    raise KeyboardInterrupt


signal.signal(signal.SIGINT, sig_handler)
signal.signal(signal.SIGTERM, sig_handler)


KAFKA_TOPICS = [
    postings_helper.POSTINGS_API_RESPONSE_TOPIC,
    accounts_helper.ACCOUNT_UPDATE_EVENTS_TOPIC,
    supervisors_helper.PLAN_UPDATE_EVENTS_TOPIC,
    balances_helper.ACCOUNT_BALANCE_EVENTS_TOPIC,
    contracts_helper.CONTRACT_NOTIFICATIONS_TOPIC,
    data_loader_helper.DATA_LOADER_EVENTS_TOPIC,
    schedule_helper.SCHEDULER_OPERATION_EVENTS_TOPIC,
]


def kafka_setup(
    topics: list[str],
    consumer_config: dict[str, str | bool | int] | None = None,
    producer_config: dict[str, str | bool | int] | None = None,
) -> None:
    try:
        if endtoend.testhandle.use_kafka != True:
            raise Exception(
                "To enable Kafka, please set the TestInstance.use_kafka flag to"
                "True. This can be done by passing the command line argument "
                "'--use_kafka'."
            )

        kafka_config = endtoend.testhandle.environment.kafka_config

        # Initialise consumers
        kafka_consumer_config = kafka_config.copy()
        kafka_consumer_config.update(consumer_config or {})
        kafka_helper.initialise_all_consumers(topics, kafka_consumer_config)

        # Initialise producer
        kafka_producer_config = kafka_config.copy()
        kafka_producer_config.update(producer_config or {})
        endtoend.testhandle.kafka_producer = endtoend.kafka_helper.initialise_producer(
            kafka_producer_config
        )

    except:
        # tearDown/tearDownClass isn't called if setUp/setUpClass fails, respectively
        endtoend.helper.teardown_shared_resources()
        raise


## Test Decorators


def skipForVaultVersion(
    callback: Callable[[Version], bool] | None = None,
    reason: str | None = None,
    prereleases_to_exclude: frozenset[str] = _DEFAULT_PRERELEASES_TO_EXCLUDE_FROM_SKIP_TEST,
    truncate_level: str = "build",
):
    """
    Skips a test method or class based on the Vault Version provided.
    The decorator can be set on the class or test level.

    If the whole test class will be skipped, it is preferential to define the decorator at the
    class level to prevent unnecessarily subscribing to Kafka for skipped tests.

    :param callback: the function to run to determine if the test should be skipped or not. If
    omitted or None, the test will always be skipped.
    :param reason: the reason for skipping the test.
    :param prereleases_to_exclude: any prereleases which, if present, will be excluded from the
    check. For example, if 'abc' is in the prereleases_to_exclude, any version with the 'abc'
    prerelease, such as "1.2.3-abc", "5.0.0-abc" or "0.0.0-abc", will bypass the check and never
    skip.
    :param truncate_level: the SemVer level at which the environment's Vault Version will be
    truncated, prior to being passed to the callback. For example, setting to 'patch' means
    anything after patch will be truncated, so 5.9.0-prerelease1-build1 would be treated as 5.9.0.
    The default 'build' value means nothing is truncated.
    """

    def decorator(target):
        def get_skip_reason(reason: str | None) -> str:
            skip_reason = ""
            version: Version = endtoend.testhandle.vault_version
            reason_str = f"{reason.strip().rstrip('.')}. " if reason else ""
            if not should_exclude_version_from_skip(version, prereleases_to_exclude):
                # By default this won't truncate anything as `build` is the lowest level
                truncated_version = version.truncate(level=truncate_level)
                if callback is None:
                    skip_reason = f"{reason_str}This test is skipped for all versions of Vault."

                elif callback(truncated_version):
                    skip_reason = f"{reason_str}This test is skipped for Vault {str(version)}."
            return skip_reason

        if inspect.isclass(target):
            if skip_reason := get_skip_reason(reason):
                return unittest.skip(skip_reason)(target)

            return target

        @functools.wraps(target)
        def wrapper(*args, **kwargs):
            if skip_reason := get_skip_reason(reason):
                raise unittest.SkipTest(skip_reason)
            return target(*args, **kwargs)

        return wrapper

    return decorator


def skipForVaultVersionLessThan(
    min_version: Version,
    reason: str | None = None,
    truncate_level: str = "build",
):
    """
    Skips a test method or class if the Vault version is less than the specified version.
    :param min_version: the version to compare against.
    :param reason: the reason for skipping the test.
    :param truncate_level: the SemVer level at which the environment's Vault Version will be
    truncated, prior to being passed to the callback. For example, setting to 'patch' means
    anything after patch will be truncated, so 5.9.0-prerelease1-build1 would be treated as 5.9.0.
    The default 'build' value means nothing is truncated.
    """
    return skipForVaultVersion(
        callback=lambda v: v < min_version,
        reason=reason or f"Vault version {min_version} or higher is required",
        truncate_level=truncate_level,
    )


def skipForVaultVersionGreaterThan(
    max_version: Version,
    reason: str | None = None,
    truncate_level: str = "build",
):
    """
    Skips a test method or class if the Vault version is greater than the specified version.
    :param max_version: the version to compare against.
    :param reason: the reason for skipping the test.
    :param truncate_level: the SemVer level at which the environment's Vault Version will be
    truncated, prior to being passed to the callback. For example, setting to 'patch' means
    anything after patch will be truncated, so 5.9.0-prerelease1-build1 would be treated as 5.9.0.
    The default 'build' value means nothing is truncated.
    """
    return skipForVaultVersion(
        callback=lambda v: v > max_version,
        reason=reason or f"Vault version {max_version} or lower is required",
        truncate_level=truncate_level,
    )


def should_exclude_version_from_skip(
    version: Version,
    to_exclude: frozenset[str] | set[str] = _DEFAULT_PRERELEASES_TO_EXCLUDE_FROM_SKIP_TEST,
) -> bool:
    for prerelease in version.prerelease or {}:
        if prerelease in to_exclude:
            return True
    return False


def skipForMissingExtension(required_extensions: list[VaultCoreExtension]):
    """
    This decorator can only be used when running against environments on Vault versions 5.8+, since
    the `extensions` information isn't available via the Core API before this.

    Skips a test method or class based on enabled Vault Core extensions on the environment.
    The decorator can be set on the class or test level.

    If the whole test class will be skipped, it is preferential to define the decorator at the
    class level to prevent unnecessarily subscribing to Kafka for skipped tests.

    """

    def decorator(target):
        def check_vault_version() -> None:
            # Truncating at patch level ensures 5.8.0 betas can use the decorator
            if endtoend.testhandle.vault_version.truncate(level="patch") < Version("5.8.0"):
                raise TestSetupException(
                    "`skipForMissingExtension` decorator only available for Vault versions 5.8+."
                )

        def get_skip_reason() -> str | None:
            """
            Returns the skip reason string if any required extensions are missing.
            """
            required = {e.name for e in required_extensions}
            enabled = {e.name for e in endtoend.testhandle.enabled_extensions}

            if not required.issubset(enabled):
                missing = sorted(list(required.difference(enabled)))
                return (
                    f"This test requires {sorted(list(required))} extensions to be enabled but "
                    f"the environment has {sorted(list(enabled))} extensions enabled. "
                    f"Missing required extensions: {missing}."
                )
            return None

        if inspect.isclass(target):
            check_vault_version()
            if skip_reason := get_skip_reason():
                return unittest.skip(skip_reason)(target)
            return target

        @functools.wraps(target)
        def wrapper(*args, **kwargs):
            check_vault_version()
            if skip_reason := get_skip_reason():
                raise unittest.SkipTest(skip_reason)
            return target(*args, **kwargs)

        return wrapper

    return decorator


def standard_setup():
    try:
        endtoend.contracts_helper.create_account_schedule_tags(
            endtoend.testhandle.CONTROLLED_SCHEDULES
        )
        endtoend.contracts_helper.create_flag_definitions(testhandle.FLAG_DEFINITIONS)
        endtoend.contracts_helper.create_calendars(testhandle.CALENDARS)
        # There is a circular dependency between workflows and contracts/supervisors due to our
        # e2e id replacement approach, but we can generate the workflow definition ids before
        # uploading them
        endtoend.workflows_helper.create_workflow_definition_id_mapping()
        endtoend.contracts_helper.create_required_internal_accounts(
            testhandle.TSIDE_TO_INTERNAL_ACCOUNT_ID
        )
        # Read parameter resources.
        test_case_parameter_resources = extract_parameters(testhandle.PARAMETER_RESOURCE_DIRS)
        e2e_test_case_parameter_resources = set_e2e_ids(test_case_parameter_resources)
        endtoend.testhandle.parameter_resource_id_to_uploaded_id |= {
            p.id: e2e_p.id
            for p, e2e_p in zip(test_case_parameter_resources, e2e_test_case_parameter_resources)
        }

        # At this point we know the resource ids used in CLU references for contracts, so
        # we create a merged dictionary for CLU replacement later on. This excludes supervisors
        endtoend.testhandle.clu_reference_mappings = safe_merge_dicts(
            (
                testhandle.calendar_ids_to_e2e_ids,
                testhandle.flag_definition_id_mapping,
                testhandle.workflow_definition_id_mapping,
                testhandle.parameter_resource_id_to_uploaded_id,
            )
        )
        endtoend.contracts_helper.upload_contracts(
            testhandle.CONTRACTS, e2e_test_case_parameter_resources
        )

        # This cannot be merged with the similar step above as Core API doesn't let us provide
        # product version ids
        endtoend.testhandle.clu_reference_mappings = safe_merge_dicts(
            (
                testhandle.clu_reference_mappings,
                testhandle.contract_pid_to_uploaded_product_version_id,
            )
        )
        endtoend.supervisors_helper.upload_supervisor_contracts(
            supervisor_contracts=testhandle.SUPERVISORCONTRACTS
        )
        endtoend.contract_modules_helper.upload_contract_modules(testhandle.CONTRACT_MODULES)

        # Our CLU ids are like `offset_mortgage_supervisor_contract_version` but within our tests
        # it is much nicer to use `offset_mortgage` as the supervisor contract's id. This interim
        # step gives us implicit support for the former and the latter
        supervisor_contract_version_id_mapping = {
            supervisor_contract_name
            + "_supervisor_contract_version": supervisor_contract_version_id
            for (
                supervisor_contract_name,
                supervisor_contract_version_id,
            ) in endtoend.testhandle.supervisorcontract_name_to_id.items()
        }

        # We can now add the remaining resource ids (e.g. supervisors) for use in workflows.
        # This could be merged with the similar step above as Core API lets us provide supervisor
        # contract version ids
        endtoend.testhandle.clu_reference_mappings = safe_merge_dicts(
            (
                testhandle.clu_reference_mappings,
                supervisor_contract_version_id_mapping,
            )
        )

        endtoend.workflows_helper.update_and_upload_workflows()
        endtoend.core_api_helper.init_postings_api_client(
            client_id=postings_helper.POSTINGS_API_CLIENT_ID,
            response_topic=postings_helper.POSTINGS_API_RESPONSE_TOPIC,
        )
    except:
        # tearDown/tearDownClass isn't called if setUp/setUpClass fails, respectively
        endtoend.helper.teardown_shared_resources()
        raise


def standard_setup_with_multiple_product_versions():
    """
    This helper defines the minimum setup to enable E2Es using multiple product versions.
    """
    try:
        endtoend.contracts_helper.create_account_schedule_tags(
            endtoend.testhandle.CONTROLLED_SCHEDULES
        )
        endtoend.contracts_helper.create_flag_definitions(testhandle.FLAG_DEFINITIONS)
        endtoend.contracts_helper.create_calendars(testhandle.CALENDARS)
        endtoend.contracts_helper.create_required_internal_accounts(
            testhandle.TSIDE_TO_INTERNAL_ACCOUNT_ID
        )
        test_case_parameter_resources = extract_parameters(testhandle.PARAMETER_RESOURCE_DIRS)
        e2e_test_case_parameter_resources = set_e2e_ids(test_case_parameter_resources)
        endtoend.testhandle.parameter_resource_id_to_uploaded_id |= {
            p.id: e2e_p.id
            for p, e2e_p in zip(test_case_parameter_resources, e2e_test_case_parameter_resources)
        }
        # At this point we know the resource ids used in CLU references for contracts, so
        # we create a merged dictionary for CLU replacement later on. This excludes supervisors.
        endtoend.testhandle.clu_reference_mappings = safe_merge_dicts(
            (
                testhandle.calendar_ids_to_e2e_ids,
                testhandle.flag_definition_id_mapping,
                testhandle.parameter_resource_id_to_uploaded_id,
                testhandle.internal_account_id_to_uploaded_id,
            )
        )
        endtoend.contracts_helper.upload_contracts_from_products(
            testhandle.PRODUCTS,
            e2e_test_case_parameter_resources,
        )
        # This cannot be merged with the similar step above as Core API doesn't let us provide
        # product version ids
        endtoend.testhandle.clu_reference_mappings = safe_merge_dicts(
            (
                testhandle.clu_reference_mappings,
                testhandle.product_version_id_to_uploaded_product_version_id,
            )
        )
        endtoend.core_api_helper.init_postings_api_client(
            client_id=postings_helper.POSTINGS_API_CLIENT_ID,
            response_topic=postings_helper.POSTINGS_API_RESPONSE_TOPIC,
        )
    except:
        endtoend.helper.teardown_shared_resources()
        raise


class End2Endtest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Ensure we can see full details of assertion failures
        cls.maxDiff = None

        if len(endtoend.testhandle.PRODUCTS) > 0:
            # guarding against both types of configurations being defined
            if len(endtoend.testhandle.CONTRACTS) > 0:
                log.error(
                    f"User defined both {endtoend.testhandle.PRODUCTS=} and "
                    f"{endtoend.testhandle.CONTRACTS=} in test setup"
                )
                raise TestSetupException(
                    "Only one of testhandle.PRODUCTS and testhandle.CONTRACTS can be defined"
                )
            standard_setup_with_multiple_product_versions()
        else:
            log.info(f"Running contracts setup: found {endtoend.testhandle.CONTRACTS}")
            standard_setup()

        # These statements cannot be merged as use_kafka may have been
        # initialised elsewhere
        if endtoend.testhandle.use_kafka:
            version: Version = endtoend.testhandle.vault_version
            extensions: list[VaultCoreExtension] = endtoend.testhandle.enabled_extensions
            # We need to use copy here so we don't modify the original list. Otherwise we will keep
            # adding this topic every time an e2e class is created and it will fail to connect to
            # Kafka because we will try to use the same consumer group.
            all_kafka_topics = KAFKA_TOPICS.copy()
            if version >= Version("5.7.0"):
                # Balances v2 were added in 5.7 so we only want to create a consumer if the
                # environment is 5.7+
                all_kafka_topics += [balances_helper.ACCOUNT_BALANCE_V2_EVENTS_TOPIC]
            if VaultCoreExtension.SUB_ACCOUNTS in extensions:
                # Sub-Accounts require the extension to be enabled so we only want to
                # create a consumer if it is enabled
                all_kafka_topics += [
                    sub_accounts_helper.SUB_ACCOUNTS_EVENT_TOPIC,
                ]
            kafka_setup(all_kafka_topics)

    @classmethod
    def tearDownClass(cls):
        endtoend.helper.teardown_shared_resources()

    def setUp(self):
        log.info(f"Running test: {self._testMethodName}")

    def tearDown(self):
        endtoend.helper.teardown_test_resources()


class AcceleratedEnd2EndTest(unittest.TestCase):
    default_tags: dict[str, str]
    paused_tags: dict[str, dict[str, str]]

    def __init__(self, methodName: str = "runTest") -> None:
        super().__init__(methodName=methodName)

    class Decorators(object):
        @classmethod
        def control_schedules(cls, schedules: dict[str, list[str]]):
            """
            Decorator that allows each test to easily define which schedules will be controlled.
            A dedicated tag will be created for each schedule, allowing them to be manipulated via
            the framework (e.g. trigger_next_schedule_job_and_wait)
            :param schedules: product name to EventType names for the schedules to control
            """

            def test_decorator(function):
                @functools.wraps(function)
                def wrapper(test, *args, **kwargs):
                    endtoend.testhandle.CONTROLLED_SCHEDULES.update(schedules)
                    function(test, *args, **kwargs)

                return wrapper

            return test_decorator

    @classmethod
    def setUpClass(cls) -> None:
        # Ensure we can see full details of assertion failures
        cls.maxDiff = None
        # accelerated e2e's use schedule changes, so having access to the kafka topic helps track
        # when scheduling events have completed
        if endtoend.testhandle.use_kafka:
            all_kafka_topics = KAFKA_TOPICS + [
                postings_helper.MIGRATIONS_POSTINGS_REQUESTS_TOPIC,
                postings_helper.MIGRATIONS_POSTINGS_RESPONSES_TOPIC,
            ]
            version: Version = endtoend.testhandle.vault_version
            extensions: list[VaultCoreExtension] = endtoend.testhandle.enabled_extensions
            if version >= Version("5.7.0"):
                # Balances v2 and Adjustments were added in 5.7 so we only want to
                # create a consumer if the environment is 5.7+
                all_kafka_topics += [
                    balances_helper.ACCOUNT_BALANCE_V2_EVENTS_TOPIC,
                    adjustments_helper.ADJUSTMENTS_EVENT_TOPIC,
                ]
            if VaultCoreExtension.SUB_ACCOUNTS in extensions:
                # Sub-Accounts require the extension to be enabled so we only want to
                # create a consumer if it is enabled
                all_kafka_topics += [
                    sub_accounts_helper.SUB_ACCOUNTS_EVENT_TOPIC,
                ]

            kafka_setup(all_kafka_topics)

    @classmethod
    def tearDownClass(cls):
        endtoend.helper.teardown_shared_resources()

    def setUp(self):
        log.info(f"Running test: {self._testMethodName}")

    def tearDown(self) -> None:
        endtoend.helper.teardown_test_resources()


def runtests() -> None:
    # This method provides support for running e2e tests from the command line as follows
    # `python3 library/common/tests/e2e/test_adjustment_creation/test_adjustment_creation.py`
    # unknown_args will not contain any e2e framework args that could trip up unittest
    # we manually re-add the binary as unittest expects this
    unknown_args = [sys.argv[0]] + flag_utils.parse_flags()
    tests = [a for a in unknown_args[1:] if a.startswith("test")]
    if len(tests) > 0:
        for test in tests:
            # this code handles cases where we have multiple TestCase classes within a module
            for i in range(len(End2Endtest.__subclasses__())):
                module = End2Endtest.__subclasses__()[i]
                if test in dir(module):
                    unittest.main(
                        # the unit test module doesn't seem to be typed correctly
                        module=module,  # type: ignore [arg-type]
                        defaultTest=test,
                        argv=unknown_args,
                    )
    else:
        unittest.main(argv=unknown_args)
