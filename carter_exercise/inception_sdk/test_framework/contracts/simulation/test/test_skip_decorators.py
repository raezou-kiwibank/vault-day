# standard libs
from typing import Callable
from unittest import SkipTest, TestCase
from unittest.mock import Mock

# third party
from semantic_version import Version

# inception sdk
from inception_sdk.common.exceptions import TestSetupException
from inception_sdk.test_framework.contracts.simulation.utils import (
    SimulationTestCase,
    skipForMissingExtension,
    skipForVaultVersion,
    skipForVaultVersionGreaterThan,
    skipForVaultVersionLessThan,
)
from inception_sdk.vault.core_api import VaultCoreExtension


class SkipDecoratorTestCase(TestCase):
    vault_version: Version
    vault_extensions: list[VaultCoreExtension]

    def assertSkips(self, test_method: Callable, skip_message: str | None = None):
        with self.assertRaises(SkipTest) as cm:
            test_method(self)
        if skip_message is not None:
            self.assertEqual(str(cm.exception), skip_message)

    def assertDoesntSkip(self, test_method: Callable):
        try:
            test_method(self)
        except SkipTest:
            self.fail("SkipTest exception raised, but this test should not skip")


class TestSkipForVaultVersion(SkipDecoratorTestCase):
    def test_skip_for_vault_version_less_than_skips_when_less(self):
        self.vault_version = Version("5.6.0")

        @skipForVaultVersionLessThan(Version("5.7.0"))
        def test_method(self):
            return True

        self.assertSkips(
            test_method,
            "Vault version 5.7.0 or higher is required",
        )

    def test_skip_for_vault_version_less_than_with_custom_reason(self):
        self.vault_version = Version("5.6.0")

        @skipForVaultVersionLessThan(Version("5.7.0"), reason="Custom reason for less than.")
        def test_method(self):
            return True

        self.assertSkips(
            test_method,
            "Custom reason for less than.",
        )

    def test_skip_for_vault_version_less_than_does_not_skip_when_equal_or_greater(self):
        self.vault_version = Version("5.7.0")

        @skipForVaultVersionLessThan(Version("5.7.0"))
        def test_method(self):
            return True

        self.assertDoesntSkip(test_method)

        self.vault_version = Version("5.8.0")
        self.assertDoesntSkip(test_method)

    def test_skip_for_vault_version_greater_than_skips_when_greater(self):
        self.vault_version = Version("5.8.0")

        @skipForVaultVersionGreaterThan(Version("5.7.0"))
        def test_method(self):
            return True

        self.assertSkips(
            test_method,
            "Vault version 5.7.0 or lower is required",
        )

    def test_skip_for_vault_version_greater_than_with_custom_reason(self):
        self.vault_version = Version("5.8.0")

        @skipForVaultVersionGreaterThan(Version("5.7.0"), reason="Custom reason for greater than.")
        def test_method(self):
            return True

        self.assertSkips(
            test_method,
            "Custom reason for greater than.",
        )

    def test_skip_for_vault_version_greater_than_does_not_skip_when_equal_or_lower(self):
        self.vault_version = Version("5.7.0")

        @skipForVaultVersionGreaterThan(Version("5.7.0"))
        def test_method(self):
            return True

        self.assertDoesntSkip(test_method)

        self.vault_version = Version("5.6.0")
        self.assertDoesntSkip(test_method)

    def test_skip_for_vault_version_skips_with_callback_when_matching_condition(self):
        self.vault_version = Version("5.7.0")

        @skipForVaultVersion(lambda v: v == Version("5.7.0"), reason="Exact version match.")
        def test_method(self):
            return True

        self.assertSkips(test_method, "Exact version match.")

    def test_skip_for_vault_version_does_not_skip_with_callback_when_not_matching_condition(self):
        self.vault_version = Version("5.8.0")

        @skipForVaultVersion(lambda v: v == Version("5.7.0"))
        def test_method(self):
            return True

        self.assertDoesntSkip(test_method)

    def test_skip_for_vault_version_skips_without_callback(self):
        self.vault_version = Version("5.7.0")

        @skipForVaultVersion(reason="Always skip.")
        def test_method(self):
            return True

        self.assertSkips(test_method, "Always skip.")

    def test_skip_for_all_vault_versions(self):
        self.vault_version = Version("6.3.1-rc3")

        @skipForVaultVersion()
        def test_method(self):
            return True

        self.assertSkips(test_method, "This test should be skipped for all versions of Vault.")

    def test_does_not_skip_for_vault_version_below(self):
        self.vault_version = Version("6.3.1-rc3")

        @skipForVaultVersion(lambda v: v < Version("4.0.0"))
        def test_method(self):
            return True

        self.assertDoesntSkip(test_method)

    def test_does_not_skip_for_vault_version_above(self):
        self.vault_version = Version("6.3.1-rc3")

        @skipForVaultVersion(lambda v: v > Version("9.0.0"))
        def test_method(self):
            return True

        self.assertDoesntSkip(test_method)

    def test_skip_for_vault_version_below(self):
        self.vault_version = Version("6.3.1-rc3")

        @skipForVaultVersion(lambda v: v < Version("9.0.0"))
        def test_method(self):
            return True

        self.assertSkips(test_method, "This test should be skipped for Vault v6.3.1-rc3.")

    def test_skip_for_vault_version_above(self):
        self.vault_version = Version("6.3.1-rc3")

        @skipForVaultVersion(lambda v: v > Version("4.0.0"))
        def test_method(self):
            return True

        self.assertSkips(test_method, "This test should be skipped for Vault v6.3.1-rc3.")

    def test_decorated_method_returns_result(self):
        self.vault_version = Version("5.7.0")

        @skipForVaultVersionLessThan(Version("5.6.0"))
        def test_method(self):
            return "executed"

        self.assertEqual(test_method(self), "executed")

    def test_decorator_with_simulation_test_case_instance(self):
        mock_sim_case = Mock(spec=SimulationTestCase)
        mock_sim_case.vault_version = Version("5.6.0")

        @skipForVaultVersionLessThan(Version("5.7.0"))
        def test_method(ref):
            return True

        test_method(mock_sim_case)
        mock_sim_case.skipTest.assert_called_once_with("Vault version 5.7.0 or higher is required")


class TestSkipForMissingExtension(SkipDecoratorTestCase):
    def test_raises_error_if_vault_version_below_5_8(self):
        self.vault_version = Version("4.3.1-rc3")
        self.vault_extensions = [
            VaultCoreExtension.SUB_ACCOUNTS,
            VaultCoreExtension.SCHEDULED_ADJUSTMENTS,
        ]

        @skipForMissingExtension(
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

    def test_does_not_skip_if_required_extensions_enabled(self):
        self.vault_version = Version("6.3.1-rc3")
        self.vault_extensions = [
            VaultCoreExtension.MULTIPLE_PROCESSING_GROUPS,
            VaultCoreExtension.HIGH_VOLUME_ACCOUNTS,
            VaultCoreExtension.SUB_ACCOUNTS,
            VaultCoreExtension.ATTRIBUTE_BASED_ACCESS_CONTROL,
            VaultCoreExtension.SCHEDULED_ADJUSTMENTS,
        ]

        @skipForMissingExtension(
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

    def test_does_skip_if_all_required_extensions_not_enabled(self):
        self.vault_version = Version("6.3.1-rc3")
        self.vault_extensions = []

        @skipForMissingExtension(
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

    def test_does_skip_if_some_required_extensions_not_enabled(self):
        self.vault_version = Version("6.3.1-rc3")
        self.vault_extensions = [
            VaultCoreExtension.HIGH_VOLUME_ACCOUNTS,
        ]

        @skipForMissingExtension(
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

    def test_decorated_method_returns_result(self):
        self.vault_version = Version("6.3.1-rc3")
        self.vault_extensions = [VaultCoreExtension.SUB_ACCOUNTS]

        @skipForMissingExtension([VaultCoreExtension.SUB_ACCOUNTS])
        def test_func(self):
            return "executed"

        self.assertEqual(test_func(self), "executed")

    def test_decorator_with_simulation_test_case_instance(self):
        mock_sim_case = Mock(spec=SimulationTestCase)
        mock_sim_case.vault_version = Version("6.3.1-rc3")
        mock_sim_case.vault_extensions = []

        @skipForMissingExtension([VaultCoreExtension.SUB_ACCOUNTS])
        def test_func(ref):
            return True

        test_func(mock_sim_case)
        mock_sim_case.skipTest.assert_called_once_with(
            "This test requires ['SUB_ACCOUNTS'] extensions to be enabled but the environment "
            "has [] extensions enabled. Missing required extensions: ['SUB_ACCOUNTS']."
        )


class VaultVersionApiTest(SimulationTestCase):
    skip_assertion_msg = "The decorator on this test case should cause it to be skipped."

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

    def test_version(self):
        vaultVersion = self.vault_version
        self.assertIsInstance(vaultVersion.major, int)
        self.assertIsInstance(vaultVersion.minor, int)
        self.assertIsInstance(vaultVersion.patch, int)
        self.assertIsInstance(vaultVersion, Version)
        self.assertGreater(vaultVersion, Version(major=0, minor=0, patch=0))

    # Core local returns the year as the major version, hence why the version here is so large.
    @skipForVaultVersion(
        lambda v: v < Version("10000.0.0"),
        "Test that skipping works for Vault versions < 10000.0.0.",
    )
    def test_skip_by_vault_version_below(self):
        self.assertFalse(True, VaultVersionApiTest.skip_assertion_msg)

    @skipForVaultVersion(
        lambda v: v > Version("0.0.0"), "Test that skipping works for Vault versions > 0.0.0."
    )
    def test_skip_by_vault_version_above(self):
        self.assertFalse(True, VaultVersionApiTest.skip_assertion_msg)

    @skipForVaultVersion(
        reason="Test that all versions of Vault can be skipped if the skip condition "
        "is omitted from the decorator."
    )
    def test_skip_for_all_vault_versions(self):
        self.assertFalse(True, VaultVersionApiTest.skip_assertion_msg)

    @skipForVaultVersionLessThan(
        Version("10000.0.0"),
        "Test that skipping works for Vault versions less than 10000.0.0.",
    )
    def test_skip_by_vault_version_less_than(self):
        self.assertFalse(True, VaultVersionApiTest.skip_assertion_msg)

    @skipForVaultVersionGreaterThan(
        Version("0.0.0"),
        "Test that skipping works for Vault versions greater than 0.0.0.",
    )
    def test_skip_by_vault_version_greater_than(self):
        self.assertFalse(True, VaultVersionApiTest.skip_assertion_msg)
