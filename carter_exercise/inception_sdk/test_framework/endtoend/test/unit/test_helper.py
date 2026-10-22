# standard libs
import unittest
from typing import Callable
from unittest.case import SkipTest, TestCase
from unittest.mock import MagicMock, PropertyMock, call, patch, sentinel
from zoneinfo import ZoneInfo

# third party
from requests import Response
from requests.exceptions import HTTPError
from semantic_version import Version

# inception sdk
import inception_sdk.test_framework.endtoend as endtoend
import inception_sdk.vault.core_api as core_api
from inception_sdk.common.exceptions import TestSetupException
from inception_sdk.test_framework.endtoend import helper, should_exclude_version_from_skip
from inception_sdk.vault.core_api import VaultCoreExtension
from inception_sdk.vault.environment import Auth, Environment, JWTAuth, ServiceAccount

UTC = ZoneInfo("UTC")

MOCK_200_RESPONSE = MagicMock(
    name="mock_200_response",
    spec=Response,
    status_code=200,
    ok=True,
    raise_for_status=MagicMock(),
    json=MagicMock(return_value={"test": "response"}),
)

MOCK_401_RESPONSE = MagicMock(
    name="mock_401_response",
    spec=Response,
    status_code=401,
    ok=False,
    # technically this HTTPError should contain the response itself
    raise_for_status=MagicMock(side_effect=HTTPError),
)

MOCK_403_RESPONSE = MagicMock(
    name="mock_403_response",
    spec=Response,
    status_code=403,
    ok=False,
    # technically this HTTPError should contain the response itself
    raise_for_status=MagicMock(side_effect=HTTPError),
)


@patch.object(endtoend.testhandle, "session")
class SendRequestTest(TestCase):

    def tearDown(self):
        if hasattr(endtoend.testhandle, "environment"):
            del endtoend.testhandle.environment

    def test_send_request_happy_path(self, mock_session: MagicMock):
        endtoend.testhandle.environment = Environment(
            name="test_env", core_api_url="core_api_url", auth=Auth(jwt=MagicMock(spec=JWTAuth))
        )
        mock_session.request = MagicMock(return_value=MOCK_200_RESPONSE)

        response = helper.send_request(
            method="get", path="/v2/accounts", data=sentinel.data, params=sentinel.params
        )
        self.assertEqual(response, {"test": "response"})

    @patch.object(endtoend.testhandle, "workflows_session")
    def test_send_request_workflows(
        self, mock_workflows_session: MagicMock, mock_session: MagicMock
    ):
        endtoend.testhandle.environment = Environment(
            name="test_env",
            core_api_url="core_api_url",
            workflow_api_url="workflows_api_url",
            auth=Auth(service_account=MagicMock(spec=ServiceAccount)),
        )
        mock_workflows_session.request = MagicMock(return_value=MOCK_200_RESPONSE)

        response = helper.send_request(
            method="get", path="/v1/workflow", data=sentinel.data, params=sentinel.params
        )
        self.assertEqual(response, {"test": "response"})
        mock_session.request.assert_not_called()

    def test_send_request_workflows_no_url(self, mock_session: MagicMock):
        endtoend.testhandle.environment = Environment(
            name="test_env",
            core_api_url="core_api_url",
            auth=Auth(jwt=MagicMock(spec=JWTAuth)),
        )
        with self.assertRaises(helper.ConfigurationException):
            helper.send_request(
                method="get", path="/v1/workflow", data=sentinel.data, params=sentinel.params
            )

    def test_send_request_data_loader(self, mock_session: MagicMock):
        endtoend.testhandle.environment = Environment(
            name="test_env",
            core_api_url="core_api_url",
            data_loader_api_url="data_loader_api_url",
            auth=Auth(jwt=MagicMock(spec=JWTAuth)),
        )
        mock_session.request = MagicMock(return_value=MOCK_200_RESPONSE)

        response = helper.send_request(
            method="get", path="/v1/dependency-groups", data=sentinel.data, params=sentinel.params
        )
        self.assertEqual(response, {"test": "response"})

    def test_send_request_data_loader_no_url(self, mock_session: MagicMock):
        endtoend.testhandle.environment = Environment(
            name="test_env",
            core_api_url="core_api_url",
            auth=Auth(jwt=MagicMock(spec=JWTAuth)),
        )
        with self.assertRaises(helper.ConfigurationException):
            helper.send_request(
                method="get",
                path="/v1/dependency-groups",
                data=sentinel.data,
                params=sentinel.params,
            )

    def test_send_request_reraises_error(self, mock_session: MagicMock):
        endtoend.testhandle.environment = Environment(
            name="test_env", core_api_url="core_api_url", auth=Auth(jwt=MagicMock(spec=JWTAuth))
        )
        mock_session.request = MagicMock(return_value=MOCK_403_RESPONSE)

        with self.assertRaises(HTTPError):
            helper.send_request(
                method="get", path="/v2/accounts", data=sentinel.data, params=sentinel.params
            )
        # make sure we don't accidentally trigger the retry path
        mock_session.request.assert_called_once()

    def test_send_request_with_jwt_auth_retries_on_401(self, mock_session: MagicMock):
        endtoend.testhandle.environment = Environment(
            name="test_env", core_api_url="core_api_url", auth=Auth(jwt=MagicMock(spec=JWTAuth))
        )
        mock_session.request = MagicMock(side_effect=[MOCK_401_RESPONSE, MOCK_200_RESPONSE])

        response = helper.send_request(
            method="get", path="/v2/accounts", data=sentinel.data, params=sentinel.params
        )
        self.assertEqual(response, {"test": "response"})
        self.assertListEqual(
            mock_session.request.call_args_list,
            [
                call("get", "core_api_url/v2/accounts", data=sentinel.data, params=sentinel.params),
                call("get", "core_api_url/v2/accounts", data=sentinel.data, params=sentinel.params),
            ],
        )

    def test_send_request_with_jwt_auth_avoids_retry_loop_on_401(self, mock_session: MagicMock):
        endtoend.testhandle.environment = Environment(
            name="test_env", core_api_url="core_api_url", auth=Auth(jwt=MagicMock(spec=JWTAuth))
        )
        mock_session.request = MagicMock(side_effect=[MOCK_401_RESPONSE, MOCK_401_RESPONSE])

        with self.assertRaises(HTTPError):
            helper.send_request(
                method="get", path="/v2/accounts", data=sentinel.data, params=sentinel.params
            )
        self.assertListEqual(
            mock_session.request.call_args_list,
            [
                call("get", "core_api_url/v2/accounts", data=sentinel.data, params=sentinel.params),
                call("get", "core_api_url/v2/accounts", data=sentinel.data, params=sentinel.params),
            ],
        )

    def test_send_request_with_service_account_doesnt_retry_on_401(self, mock_session: MagicMock):
        endtoend.testhandle.environment = Environment(
            name="test_env",
            core_api_url="core_api_url",
            auth=Auth(service_account=MagicMock(spec=ServiceAccount)),
        )
        mock_session.request = MagicMock(side_effect=[MOCK_401_RESPONSE, MOCK_200_RESPONSE])

        with self.assertRaises(HTTPError):
            helper.send_request(
                method="get", path="/v2/accounts", data=sentinel.data, params=sentinel.params
            )
        mock_session.request.assert_called_once()

    @patch.object(endtoend.testhandle, "workflows_session")
    def test_send_request_with_workflow_url_doesnt_retry_on_401(
        self, mock_workflows_session: MagicMock, mock_session: MagicMock
    ):
        endtoend.testhandle.environment = Environment(
            name="test_env",
            core_api_url="core_api_url",
            workflow_api_url="workflow_api_url",
            auth=Auth(service_account=MagicMock(spec=ServiceAccount), jwt=MagicMock(spec=JWTAuth)),
        )
        mock_workflows_session.request = MagicMock(
            side_effect=[MOCK_401_RESPONSE, MOCK_200_RESPONSE]
        )

        with self.assertRaises(HTTPError):
            helper.send_request(
                method="get", path="/v1/workflows", data=sentinel.data, params=sentinel.params
            )
        mock_workflows_session.request.assert_called_once()


@patch.object(helper.time, "sleep", MagicMock())
class RetryHelperTest(TestCase):

    def test_unexpected_error_not_retried_and_raises(self):
        retried_function = MagicMock(side_effect=HTTPError())
        with self.assertRaises(HTTPError):
            helper.retry_call(
                func=retried_function,
                exceptions=KeyError,
            )
        retried_function.assert_called_once()

    def test_repeated_expected_error_retried_specified_times_and_raises(self):
        retried_function = MagicMock(side_effect=HTTPError())
        with self.assertRaises(HTTPError):
            helper.retry_call(func=retried_function, exceptions=HTTPError, max_retries=3)
        self.assertEqual(
            retried_function.call_count,
            # initial call + the 3 retries
            4,
        )

    def test_temporary_expected_error_retried_and_returns_after_success(self):
        retried_function = MagicMock(side_effect=[HTTPError(), sentinel.success])
        result = helper.retry_call(func=retried_function, exceptions=HTTPError, max_retries=3)
        self.assertEqual(result, sentinel.success)
        self.assertEqual(
            retried_function.call_count,
            # initial call + 1 retry
            2,
        )

    @patch.object(helper.time, "time")
    def test_raise_when_timeout_is_exceeded(self, mock_time: MagicMock):
        retried_function = MagicMock(side_effect=HTTPError())
        timeout = 2

        def dynamic_time():
            # Maps: retried_function.call_count -> simulated current time
            timeline = {0: 0, 1: 1, 2: timeout + 1}
            count = retried_function.call_count

            if count not in timeline:
                raise AssertionError(
                    f"time.time() called unexpectedly. " f"retried_function.call_count: {count}"
                )
            return timeline[count]

        mock_time.side_effect = dynamic_time

        with self.assertRaises(HTTPError):
            helper.retry_call(
                func=retried_function, exceptions=HTTPError, max_retries=3, timeout=timeout
            )
        self.assertEqual(
            retried_function.call_count,
            # initial call + 1 retry
            2,
        )

    def test_result_compared_to_expected_without_wrapper(self):
        retried_function = MagicMock(side_effect=[0, 1])
        result = helper.retry_call(
            func=retried_function,
            expected_result=1,
        )
        self.assertEqual(result, 1)
        self.assertEqual(
            retried_function.call_count,
            # initial call + 1 retry
            2,
        )

    def test_result_compared_to_expected_with_wrapper(self):
        retried_function = MagicMock(side_effect=[0, 1, 2])
        result = helper.retry_call(
            func=retried_function,
            result_wrapper=lambda x: x / 2,
            expected_result=1,
        )
        self.assertEqual(result, 2)
        self.assertEqual(
            retried_function.call_count,
            # initial call + 2 retries
            3,
        )

    def test_wrapped_result_returned_when_specified(self):
        retried_function = MagicMock(side_effect=[0, 1, 2])
        result = helper.retry_call(
            func=retried_function,
            result_wrapper=lambda x: x / 2,
            expected_result=1,
            return_wrapped_result=True,
        )
        self.assertEqual(result, 1)
        self.assertEqual(
            retried_function.call_count,
            # initial call + 2 retries
            3,
        )

    @patch.object(helper.random, "uniform")
    def test_base_sleep_decreases_if_back_off_less_than_one(self, mock_random_uniform: MagicMock):
        retried_function = MagicMock(side_effect=HTTPError())
        with self.assertRaises(HTTPError):
            helper.retry_call(
                func=retried_function,
                exceptions=HTTPError,
                max_retries=3,
                back_off=0.1,
            )
        self.assertEqual(mock_random_uniform.call_count, 3)
        mock_random_uniform.assert_has_calls(
            calls=[
                call(0, 1),
                call(0, 0.1),
                call(0, 0.1**2),
            ]
        )

    @patch.object(helper.random, "uniform")
    def test_base_sleep_increases_if_back_off_over_one(self, mock_random_uniform: MagicMock):
        retried_function = MagicMock(side_effect=HTTPError())
        with self.assertRaises(HTTPError):
            helper.retry_call(
                func=retried_function,
                exceptions=HTTPError,
                max_retries=3,
                back_off=2,
            )
        self.assertEqual(mock_random_uniform.call_count, 3)
        mock_random_uniform.assert_has_calls(
            calls=[
                call(0, 1),
                call(0, 2),
                call(0, 4),
            ]
        )

    @patch.object(helper.random, "uniform")
    def test_base_sleep_constant_if_back_off_equal_one(self, mock_random_uniform: MagicMock):
        retried_function = MagicMock(side_effect=HTTPError())
        with self.assertRaises(HTTPError):
            helper.retry_call(
                func=retried_function,
                exceptions=HTTPError,
                max_retries=3,
                back_off=1,
            )

        self.assertEqual(mock_random_uniform.call_count, 3)
        mock_random_uniform.assert_has_calls(
            calls=[
                call(0, 1),
                call(0, 1),
                call(0, 1),
            ]
        )


class SkipDecoratorTestCase(TestCase):

    def assertSkips(self, test_method: Callable, skip_message: str | None = None):
        with self.assertRaises(SkipTest) as cm:
            test_method(self)
        if skip_message is not None:
            self.assertEqual(str(cm.exception), skip_message)

    def assertDoesntSkip(self, test_method):
        try:
            test_method(self)
        except SkipTest:
            self.fail("SkipTest exception raised, but this test should not skip")


@patch.object(endtoend, "testhandle")
class TestSkipForVaultVersion(SkipDecoratorTestCase):

    def test_skip_for_vault_version_less_than_skips_when_less(self, mock_testhandle: MagicMock):
        type(mock_testhandle).vault_version = PropertyMock(return_value=Version("5.6.0"))

        @endtoend.skipForVaultVersionLessThan(Version("5.7.0"))
        def test_method(self):
            return True

        self.assertSkips(
            test_method,
            "Vault version 5.7.0 or higher is required. This test is skipped for Vault 5.6.0.",
        )

    def test_skip_for_vault_version_less_than_does_not_skip_when_equal_or_greater(
        self, mock_testhandle: MagicMock
    ):
        type(mock_testhandle).vault_version = PropertyMock(return_value=Version("5.7.0"))

        @endtoend.skipForVaultVersionLessThan(Version("5.7.0"))
        def test_method(self):
            return True

        self.assertDoesntSkip(test_method)

        type(mock_testhandle).vault_version = PropertyMock(return_value=Version("5.8.0"))
        self.assertDoesntSkip(test_method)

    def test_skip_for_vault_version_greater_than_skips_when_greater(
        self, mock_testhandle: MagicMock
    ):
        type(mock_testhandle).vault_version = PropertyMock(return_value=Version("5.8.0"))

        @endtoend.skipForVaultVersionGreaterThan(Version("5.7.0"))
        def test_method(self):
            return True

        self.assertSkips(
            test_method,
            "Vault version 5.7.0 or lower is required. This test is skipped for Vault 5.8.0.",
        )

    def test_skip_for_vault_version_greater_than_does_not_skip_when_equal_or_lower(
        self, mock_testhandle: MagicMock
    ):
        type(mock_testhandle).vault_version = PropertyMock(return_value=Version("5.7.0"))

        @endtoend.skipForVaultVersionGreaterThan(Version("5.7.0"))
        def test_method(self):
            return True

        self.assertDoesntSkip(test_method)

        type(mock_testhandle).vault_version = PropertyMock(return_value=Version("5.6.0"))
        self.assertDoesntSkip(test_method)

    def test_skip_for_vault_version_truncates_nothing_by_default(self, mock_testhandle: MagicMock):
        # this should skip as 5.7.0-beta1 is considered as a pre-release and therefore < 5.7.0
        type(mock_testhandle).vault_version = PropertyMock(return_value=Version("5.7.0-beta"))

        @endtoend.skipForVaultVersionLessThan(Version("5.7.0"))
        def test_method(self):
            return True

        self.assertSkips(test_method)

    def test_skip_for_vault_version_with_custom_truncate_level(self, mock_testhandle: MagicMock):
        # this should not skip as the prerelease will be truncated and therefore 5.7.0 == 5.7.0
        type(mock_testhandle).vault_version = PropertyMock(return_value=Version("5.7.0-beta"))

        @endtoend.skipForVaultVersionLessThan(Version("5.7.0"), truncate_level="patch")
        def test_method(self):
            return True

        self.assertDoesntSkip(test_method)

    def test_skip_for_vault_version_skips_with_callback_when_matching_condition(
        self, mock_testhandle: MagicMock
    ):
        type(mock_testhandle).vault_version = PropertyMock(return_value=Version("5.7.0"))

        @endtoend.skipForVaultVersion(
            lambda v: v == Version("5.7.0"), reason="Exact version match."
        )
        def test_method(self):
            return True

        self.assertSkips(test_method, "Exact version match. This test is skipped for Vault 5.7.0.")

    def test_skip_for_vault_version_does_not_skip_with_callback_when_not_matching_condition(
        self, mock_testhandle: MagicMock
    ):
        type(mock_testhandle).vault_version = PropertyMock(return_value=Version("5.8.0"))

        @endtoend.skipForVaultVersion(lambda v: v == Version("5.7.0"))
        def test_method(self):
            return True

        self.assertDoesntSkip(test_method)

    def test_skip_for_vault_version_skips_without_callback(self, mock_testhandle: MagicMock):
        type(mock_testhandle).vault_version = PropertyMock(return_value=Version("5.7.0"))

        @endtoend.skipForVaultVersion(reason="Always skip.")
        def test_method(self):
            return True

        self.assertSkips(
            test_method, "Always skip. This test is skipped for all versions of Vault."
        )

    def test_skip_for_vault_version_does_not_skip_on_excluded_preleases(
        self, mock_testhandle: MagicMock
    ):
        type(mock_testhandle).vault_version = PropertyMock(return_value=Version("5.6.0-master"))

        @endtoend.skipForVaultVersionLessThan(Version("5.7.0"))
        def test_method(self):
            return True

        self.assertDoesntSkip(test_method)

    def test_does_not_skip_for_vault_version_below(self, mock_testhandle: MagicMock):
        type(mock_testhandle).vault_version = PropertyMock(return_value=Version("6.3.1-rc3"))

        @endtoend.skipForVaultVersion(lambda v: v < Version("4.0.0"))
        def test_method(self):
            return True

        self.assertDoesntSkip(test_method)

    def test_does_not_skip_for_vault_version_above(self, mock_testhandle: MagicMock):
        type(mock_testhandle).vault_version = PropertyMock(return_value=Version("6.3.1-rc3"))

        @endtoend.skipForVaultVersion(lambda v: v > Version("9.0.0"))
        def test_method(self):
            return True

        self.assertDoesntSkip(test_method)

    def test_skip_for_vault_version_below(self, mock_testhandle: MagicMock):
        type(mock_testhandle).vault_version = PropertyMock(return_value=Version("6.3.1-rc3"))

        @endtoend.skipForVaultVersion(lambda v: v < Version("9.0.0"))
        def test_method(self):
            return True

        self.assertSkips(test_method, "This test is skipped for Vault 6.3.1-rc3.")

    def test_skip_for_vault_version_above(self, mock_testhandle: MagicMock):
        type(mock_testhandle).vault_version = PropertyMock(return_value=Version("6.3.1-rc3"))

        @endtoend.skipForVaultVersion(lambda v: v > Version("4.0.0"))
        def test_method(self):
            return True

        self.assertSkips(test_method, "This test is skipped for Vault 6.3.1-rc3.")

    def test_skip_for_all_vault_versions(self, mock_testhandle: MagicMock):
        type(mock_testhandle).vault_version = PropertyMock(return_value=Version("6.3.1-rc3"))

        @endtoend.skipForVaultVersion()
        def test_method(self):
            return True

        self.assertSkips(test_method, "This test is skipped for all versions of Vault.")

    def test_class_level_does_not_skip_by_vault_version(self, mock_testhandle: MagicMock):
        type(mock_testhandle).vault_version = PropertyMock(return_value=Version("6.3.1-rc3"))

        @endtoend.skipForVaultVersion(lambda v: v < Version("0.0.0"), reason="Never skip")
        class TestClassLevelDecorator(TestCase):
            def test_method(self):
                # assertions won't be directly raised as we're going through a separate runner
                raise AssertionError("This class should not be skipped.")

        suite = unittest.defaultTestLoader.loadTestsFromTestCase(TestClassLevelDecorator)
        result = unittest.TextTestRunner().run(suite)
        self.assertListEqual(result.skipped, [])

    def test_class_level_skip_by_vault_version(self, mock_testhandle: MagicMock):
        type(mock_testhandle).vault_version = PropertyMock(return_value=Version("6.3.1-rc3"))

        @endtoend.skipForVaultVersion(lambda v: v > Version("0.0.0"), reason="Skip all versions")
        class TestClassLevelDecorator(TestCase):
            def test_method(self):
                # assertions won't be directly raised as we're going through a separate runner
                raise AssertionError("This class should be skipped.")

        suite = unittest.defaultTestLoader.loadTestsFromTestCase(TestClassLevelDecorator)
        result = unittest.TextTestRunner().run(suite)
        self.assertListEqual(
            result.skipped,
            [
                (
                    TestClassLevelDecorator(methodName="test_method"),
                    "Skip all versions. This test is skipped for Vault 6.3.1-rc3.",
                )
            ],
        )


@patch.object(endtoend, "testhandle")
class TestSkipForMissingExtension(SkipDecoratorTestCase):
    def test_raises_error_if_vault_version_below_5_8(self, mock_testhandle: MagicMock):
        type(mock_testhandle).vault_version = PropertyMock(return_value=Version("4.3.1-rc3"))
        type(mock_testhandle).enabled_extensions = PropertyMock(
            return_value=[
                VaultCoreExtension.SUB_ACCOUNTS,
                VaultCoreExtension.SCHEDULED_ADJUSTMENTS,
            ]
        )

        @endtoend.skipForMissingExtension(
            [
                VaultCoreExtension.MULTIPLE_PROCESSING_GROUPS,
                VaultCoreExtension.HIGH_VOLUME_ACCOUNTS,
                VaultCoreExtension.SUB_ACCOUNTS,
                VaultCoreExtension.ATTRIBUTE_BASED_ACCESS_CONTROL,
                VaultCoreExtension.SCHEDULED_ADJUSTMENTS,
            ]
        )
        def test_func(ref):
            return None

        with self.assertRaises(TestSetupException) as ctx:
            test_func(self)
        self.assertEqual(
            str(ctx.exception),
            "`skipForMissingExtension` decorator only available for Vault versions 5.8+.",
        )

    def test_does_not_error_for_vault_version_5_8_prerelease(self, mock_testhandle: MagicMock):
        type(mock_testhandle).vault_version = PropertyMock(return_value=Version("5.8.0-prerelease"))
        type(mock_testhandle).enabled_extensions = PropertyMock(
            return_value=[
                VaultCoreExtension.SUB_ACCOUNTS,
            ]
        )

        @endtoend.skipForMissingExtension(
            [
                VaultCoreExtension.MULTIPLE_PROCESSING_GROUPS,
            ]
        )
        def test_func(ref):
            return None

        self.assertSkips(
            test_func,
            "This test requires ['MULTIPLE_PROCESSING_GROUPS'] extensions to be enabled but the "
            "environment has ['SUB_ACCOUNTS'] extensions enabled. Missing required extensions: "
            "['MULTIPLE_PROCESSING_GROUPS'].",
        )

    def test_class_level_raises_error_if_vault_version_below_5_8(self, mock_testhandle: MagicMock):
        type(mock_testhandle).vault_version = PropertyMock(return_value=Version("4.3.1-rc3"))
        type(mock_testhandle).enabled_extensions = PropertyMock(
            return_value=[
                VaultCoreExtension.SUB_ACCOUNTS,
                VaultCoreExtension.SCHEDULED_ADJUSTMENTS,
            ]
        )

        with self.assertRaises(TestSetupException) as ctx:

            @endtoend.skipForMissingExtension(
                [
                    VaultCoreExtension.MULTIPLE_PROCESSING_GROUPS,
                    VaultCoreExtension.HIGH_VOLUME_ACCOUNTS,
                    VaultCoreExtension.SUB_ACCOUNTS,
                    VaultCoreExtension.ATTRIBUTE_BASED_ACCESS_CONTROL,
                    VaultCoreExtension.SCHEDULED_ADJUSTMENTS,
                ]
            )
            class TestClassLevelDecorator:
                """
                This test class should be skipped with the decorator defined.
                """

                def test_dummy(self):
                    raise AssertionError("This class should be skipped.")

        self.assertEqual(
            str(ctx.exception),
            "`skipForMissingExtension` decorator only available for Vault versions 5.8+.",
        )

    def test_does_not_skip_if_required_extensions_enabled(self, mock_testhandle: MagicMock):
        type(mock_testhandle).vault_version = PropertyMock(return_value=Version("6.3.1-rc3"))
        type(mock_testhandle).enabled_extensions = PropertyMock(
            return_value=[
                VaultCoreExtension.MULTIPLE_PROCESSING_GROUPS,
                VaultCoreExtension.HIGH_VOLUME_ACCOUNTS,
                VaultCoreExtension.SUB_ACCOUNTS,
                VaultCoreExtension.ATTRIBUTE_BASED_ACCESS_CONTROL,
                VaultCoreExtension.SCHEDULED_ADJUSTMENTS,
            ]
        )

        @endtoend.skipForMissingExtension(
            [
                VaultCoreExtension.MULTIPLE_PROCESSING_GROUPS,
                VaultCoreExtension.HIGH_VOLUME_ACCOUNTS,
                VaultCoreExtension.SUB_ACCOUNTS,
                VaultCoreExtension.ATTRIBUTE_BASED_ACCESS_CONTROL,
                VaultCoreExtension.SCHEDULED_ADJUSTMENTS,
            ]
        )
        def test_func(ref):
            return True

        self.assertDoesntSkip(test_func)

    def test_does_skip_if_all_required_extensions_not_enabled(self, mock_testhandle: MagicMock):
        type(mock_testhandle).vault_version = PropertyMock(return_value=Version("6.3.1-rc3"))
        type(mock_testhandle).enabled_extensions = PropertyMock(return_value=[])

        @endtoend.skipForMissingExtension(
            [
                VaultCoreExtension.HIGH_VOLUME_ACCOUNTS,
                VaultCoreExtension.SCHEDULED_ADJUSTMENTS,
            ]
        )
        def test_func(ref):
            return None

        self.assertSkips(
            test_func,
            "This test requires ['HIGH_VOLUME_ACCOUNTS', "
            "'SCHEDULED_ADJUSTMENTS'] extensions to be enabled but "
            "the environment has [] extensions enabled. Missing required extensions: "
            "['HIGH_VOLUME_ACCOUNTS', 'SCHEDULED_ADJUSTMENTS'].",
        )

    def test_does_skip_if_some_required_extensions_not_enabled(self, mock_testhandle: MagicMock):
        type(mock_testhandle).vault_version = PropertyMock(return_value=Version("6.3.1-rc3"))
        type(mock_testhandle).enabled_extensions = PropertyMock(
            return_value=[
                VaultCoreExtension.HIGH_VOLUME_ACCOUNTS,
            ]
        )

        @endtoend.skipForMissingExtension(
            [
                VaultCoreExtension.HIGH_VOLUME_ACCOUNTS,
                VaultCoreExtension.SCHEDULED_ADJUSTMENTS,
            ]
        )
        def test_func(self):
            return None

        self.assertSkips(
            test_func,
            "This test requires ['HIGH_VOLUME_ACCOUNTS', "
            "'SCHEDULED_ADJUSTMENTS'] extensions to be enabled but "
            "the environment has ['HIGH_VOLUME_ACCOUNTS'] extensions enabled. "
            "Missing required extensions: ['SCHEDULED_ADJUSTMENTS'].",
        )

    def test_class_level_does_not_skip_if_required_extensions_enabled(
        self, mock_testhandle: MagicMock
    ):
        type(mock_testhandle).vault_version = PropertyMock(return_value=Version("6.3.1-rc3"))
        type(mock_testhandle).enabled_extensions = PropertyMock(
            return_value=[
                VaultCoreExtension.MULTIPLE_PROCESSING_GROUPS,
                VaultCoreExtension.HIGH_VOLUME_ACCOUNTS,
                VaultCoreExtension.SUB_ACCOUNTS,
                VaultCoreExtension.ATTRIBUTE_BASED_ACCESS_CONTROL,
                VaultCoreExtension.SCHEDULED_ADJUSTMENTS,
            ]
        )

        @endtoend.skipForMissingExtension(
            [
                VaultCoreExtension.MULTIPLE_PROCESSING_GROUPS,
                VaultCoreExtension.HIGH_VOLUME_ACCOUNTS,
                VaultCoreExtension.SUB_ACCOUNTS,
                VaultCoreExtension.ATTRIBUTE_BASED_ACCESS_CONTROL,
                VaultCoreExtension.SCHEDULED_ADJUSTMENTS,
            ]
        )
        class TestClassLevelDecorator(TestCase):
            """
            This test class should be skipped with the decorator defined.
            """

            def test_dummy(self):
                raise AssertionError("This class should be skipped.")

        suite = unittest.defaultTestLoader.loadTestsFromTestCase(TestClassLevelDecorator)
        result = unittest.TextTestRunner().run(suite)
        self.assertListEqual(result.skipped, [])

    def test_class_level_does_skip_if_all_required_extensions_not_enabled(
        self, mock_testhandle: MagicMock
    ):
        type(mock_testhandle).vault_version = PropertyMock(return_value=Version("6.3.1-rc3"))
        type(mock_testhandle).enabled_extensions = PropertyMock(return_value=[])

        @endtoend.skipForMissingExtension(
            [
                VaultCoreExtension.HIGH_VOLUME_ACCOUNTS,
                VaultCoreExtension.SCHEDULED_ADJUSTMENTS,
            ]
        )
        class TestClassLevelDecorator(TestCase):
            def test_dummy(self):
                raise AssertionError("This class should be skipped.")

        suite = unittest.defaultTestLoader.loadTestsFromTestCase(TestClassLevelDecorator)
        result = unittest.TextTestRunner().run(suite)
        self.assertListEqual(
            result.skipped,
            [
                (
                    TestClassLevelDecorator(methodName="test_dummy"),
                    "This test requires ['HIGH_VOLUME_ACCOUNTS', 'SCHEDULED_ADJUSTMENTS'] "
                    "extensions to be enabled but the environment has [] extensions enabled. "
                    "Missing required extensions: ['HIGH_VOLUME_ACCOUNTS', "
                    "'SCHEDULED_ADJUSTMENTS'].",
                )
            ],
        )

    def test_class_level_does_skip_if_some_required_extensions_not_enabled(
        self, mock_testhandle: MagicMock
    ):
        type(mock_testhandle).vault_version = PropertyMock(return_value=Version("6.3.1-rc3"))
        type(mock_testhandle).enabled_extensions = PropertyMock(
            return_value=[
                VaultCoreExtension.HIGH_VOLUME_ACCOUNTS,
            ]
        )

        @endtoend.skipForMissingExtension(
            [
                VaultCoreExtension.HIGH_VOLUME_ACCOUNTS,
                VaultCoreExtension.SCHEDULED_ADJUSTMENTS,
            ]
        )
        class TestClassLevelDecorator:
            def test_dummy(self):
                raise AssertionError("This class should be skipped.")

        is_skipped = getattr(TestClassLevelDecorator, "__unittest_skip__", None)
        self.assertTrue(is_skipped)

        skip_reason = getattr(TestClassLevelDecorator, "__unittest_skip_why__", None)
        self.assertEqual(
            skip_reason,
            "This test requires ['HIGH_VOLUME_ACCOUNTS', 'SCHEDULED_ADJUSTMENTS'] extensions to be "
            "enabled but the environment has ['HIGH_VOLUME_ACCOUNTS'] extensions enabled. "
            "Missing required extensions: ['SCHEDULED_ADJUSTMENTS'].",
        )


@patch.object(helper.time, "sleep", MagicMock())
class RetryDecoratorTest(TestCase):

    @helper.retry_decorator(on_http_error_codes=[400, 503], max_retries=3)
    def decorated_function_with_http_error_code(
        self, dummy_mock: MagicMock, error_to_raise: Exception | None
    ):
        dummy_mock()
        if error_to_raise:
            raise error_to_raise
        else:
            return None

    def test_retry_on_specified_http_error_code(self):
        mock_response = MagicMock(status_code=400)
        mock_http_error = HTTPError(response=mock_response)
        dummy_mock = MagicMock()
        with self.assertRaises(HTTPError):
            self.decorated_function_with_http_error_code(
                dummy_mock=dummy_mock, error_to_raise=mock_http_error
            )
        self.assertEqual(dummy_mock.call_count, 4)

    def test_dont_retry_on_unspecified_http_error_code(self):
        mock_response = MagicMock(status_code=404)
        mock_http_error = HTTPError(response=mock_response)
        dummy_mock = MagicMock()
        with self.assertRaises(HTTPError):
            self.decorated_function_with_http_error_code(
                dummy_mock=dummy_mock, error_to_raise=mock_http_error
            )
        self.assertEqual(dummy_mock.call_count, 1)

        return


class TestShouldExcludeVersionFromSkip(TestCase):
    def test_master_prerelease_by_default(self):
        self.assertTrue(should_exclude_version_from_skip(Version("1.2.3-master")))
        return

    def test_test_prerelease_by_default(self):
        self.assertTrue(should_exclude_version_from_skip(Version("1.2.3-test")))
        return

    def test_one_prerelease_in_custom_set(self):
        self.assertTrue(
            should_exclude_version_from_skip(Version("1.2.3-potato"), {"potato", "tomato"})
        )
        return

    def test_multiple_prereleases_match_custom_set(self):
        self.assertTrue(
            should_exclude_version_from_skip(
                Version("1.2.3-potato.tomato"),
                {"potato", "tomato", "gorilla"},
            ),
        )
        return

    def test_when_one_prerelease_matches_default(self):
        self.assertTrue(should_exclude_version_from_skip(Version("1.2.3-potato.test")))
        return

    def test_when_multiple_prereleases_match_default(self):
        self.assertTrue(should_exclude_version_from_skip(Version("1.2.3-master.test")))
        return

    def test_when_no_prerelease(self):
        self.assertFalse(should_exclude_version_from_skip(Version("1.2.3")))
        return

    def test_when_prerelease_should_not_be_skipped(self):
        self.assertFalse(should_exclude_version_from_skip(Version("1.2.3-master"), {"test"}))
        return

    def test_if_set_to_exclude_is_empty(self):
        self.assertFalse(should_exclude_version_from_skip(Version("1.2.3-master"), {}))
        return

    def test_when_custom_set_empty_and_no_prerelease(self):
        self.assertFalse(should_exclude_version_from_skip(Version("1.2.3"), {}))
        return


@patch.object(endtoend.contracts_helper, "deactivate_all_calendars")
@patch.object(endtoend.workflows_helper, "delete_all_workflows")
@patch.object(endtoend, "testhandle")
class TestTeardownSharedResources(TestCase):

    def test_teardown_tears_down_kafka_consumer_and_producer(
        self,
        mock_testhandle: MagicMock,
        delete_all_workflows: MagicMock,
        mock_deactivate_all_calendars: MagicMock,
    ):
        type(mock_testhandle).use_kafka = PropertyMock(return_value=True)
        mock_consumer = MagicMock()
        type(mock_testhandle).kafka_consumers = PropertyMock(
            return_value={"test_topic": mock_consumer}
        )
        mock_producer = MagicMock()
        type(mock_testhandle).kafka_producer = PropertyMock(return_value=mock_producer)

        helper.teardown_shared_resources()

        mock_consumer.close.assert_called_once()
        mock_producer.flush.assert_called_once()

        delete_all_workflows.assert_called_once()
        mock_deactivate_all_calendars.assert_called_once()

    def test_teardown_with_uninitialised_kafka_consumers(
        self,
        mock_testhandle: MagicMock,
        delete_all_workflows: MagicMock,
        mock_deactivate_all_calendars: MagicMock,
    ):
        type(mock_testhandle).use_kafka = PropertyMock(return_value=True)
        mock_consumer = MagicMock()
        type(mock_testhandle).kafka_consumers = PropertyMock(
            side_effect=helper.UninitialisedKafkaConsumerException
        )
        mock_producer = MagicMock()
        type(mock_testhandle).kafka_producer = PropertyMock(return_value=mock_producer)

        helper.teardown_shared_resources()

        mock_consumer.close.assert_not_called()
        mock_producer.flush.assert_not_called()

        delete_all_workflows.assert_called_once()
        mock_deactivate_all_calendars.assert_called_once()

    def test_teardown_with_uninitialised_kafka_producer(
        self,
        mock_testhandle: MagicMock,
        delete_all_workflows: MagicMock,
        mock_deactivate_all_calendars: MagicMock,
    ):
        type(mock_testhandle).use_kafka = PropertyMock(return_value=True)
        mock_consumer = MagicMock()
        type(mock_testhandle).kafka_consumers = PropertyMock(
            return_value={"test_topic": mock_consumer}
        )
        mock_producer = MagicMock()
        type(mock_testhandle).kafka_producer = PropertyMock(
            side_effect=helper.UninitialisedKafkaProducerException
        )

        helper.teardown_shared_resources()

        mock_consumer.close.assert_called_once()
        mock_producer.flush.assert_not_called()

        delete_all_workflows.assert_called_once()
        mock_deactivate_all_calendars.assert_called_once()

    def test_teardown_with_kafka_exception(
        self,
        mock_testhandle: MagicMock,
        delete_all_workflows: MagicMock,
        mock_deactivate_all_calendars: MagicMock,
    ):
        type(mock_testhandle).use_kafka = PropertyMock(return_value=True)
        mock_consumer = MagicMock()
        type(mock_testhandle).kafka_consumers = PropertyMock(
            return_value={"test_topic": mock_consumer}
        )
        mock_producer = MagicMock()
        type(mock_testhandle).kafka_producer = PropertyMock(
            side_effect=helper.confluent_kafka.KafkaException
        )

        helper.teardown_shared_resources()

        mock_consumer.close.assert_called_once()
        mock_producer.flush.assert_not_called()

        delete_all_workflows.assert_called_once()
        mock_deactivate_all_calendars.assert_called_once()

    def test_teardown_in_nokafka_mode(
        self,
        mock_testhandle: MagicMock,
        delete_all_workflows: MagicMock,
        mock_deactivate_all_calendars: MagicMock,
    ):
        type(mock_testhandle).use_kafka = PropertyMock(return_value=False)
        helper.teardown_shared_resources()
        delete_all_workflows.assert_called_once()
        mock_deactivate_all_calendars.assert_called_once()


# Testing Helper Pydantic models
class TestTestProductWithDuplicateProductVersionIDsRaises(TestCase):
    def test_duplicate_product_version_ids_raises(self):
        with self.assertRaises(TestSetupException) as ctx:
            helper.TestProduct(
                product_id="product_id_1",
                product_versions=[
                    helper.TestProductVersion(
                        product_version_id="pv1",
                        path="/path/to/pv1",
                        supported_denominations=["XYZ"],
                        adjustments_versioning_policy=core_api.AdjustmentsVersioningPolicy.LATEST,
                    ),
                    helper.TestProductVersion(
                        product_version_id="pv2",
                        path="/path/to/pv2",
                        supported_denominations=["XYZ"],
                        adjustments_versioning_policy=core_api.AdjustmentsVersioningPolicy.LATEST,
                    ),
                    helper.TestProductVersion(
                        product_version_id="pv1",
                        path="/path/to/pv1",
                        supported_denominations=["XYZ"],
                        adjustments_versioning_policy=core_api.AdjustmentsVersioningPolicy.LATEST,
                    ),
                ],
            )

            self.assertEqual(
                "Each product's product version provided for upload "
                "must have unique product_version_id. "
                "Duplicates found ['pv1']",
                str(ctx.exception),
            )


class TestTestProductVersion(TestCase):
    def test_product_version_defaults(self):
        with_defaults = helper.TestProductVersion(
            product_version_id="pvid",
            path="path",
            supported_denominations=["XYZ"],
        )
        without_defaults = helper.TestProductVersion(
            product_version_id="pvid",
            path="path",
            adjustments_versioning_policy=None,
            display_name="",
            template_params=None,
            supported_denominations=["XYZ"],
            is_internal=False,
        )
        self.assertEqual(
            with_defaults, without_defaults, f"{with_defaults=} does not match {without_defaults=}"
        )
