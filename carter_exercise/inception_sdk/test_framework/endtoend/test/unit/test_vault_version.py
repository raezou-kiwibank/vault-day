# standard libs
from unittest import TestCase
from unittest.mock import MagicMock, patch

# third party
from semantic_version import Version

# inception sdk
import inception_sdk.test_framework.endtoend as endtoend
from inception_sdk.test_framework.endtoend import core_api_helper
from inception_sdk.vault.core_api import (
    GetVaultVersionResponse,
    SemanticVersion,
    VaultCoreExtension,
)


class TestVaultVersion(TestCase):
    @patch.object(core_api_helper, "get_vault_instance_information")
    def test_set_vault_instance_information(
        self,
        mock_get_vault_instance_information: MagicMock,
    ):
        # construct mocks
        mock_get_vault_instance_information.return_value = GetVaultVersionResponse(
            version=SemanticVersion(major=4, minor=3, patch=1, label="-rc3"),
            pre_release="pre_release_tag",
            build="build_tag",
            extensions=[
                VaultCoreExtension.MULTIPLE_PROCESSING_GROUPS,
                VaultCoreExtension.HIGH_VOLUME_ACCOUNTS,
            ],
        )

        # run function to set vault version and enabled extensions on testhandle
        endtoend.helper.set_vault_instance_information()

        # assertions
        self.assertEqual(endtoend.testhandle.vault_version, Version("4.3.1-rc3"))
        self.assertEqual(
            endtoend.testhandle.enabled_extensions,
            [
                VaultCoreExtension.MULTIPLE_PROCESSING_GROUPS,
                VaultCoreExtension.HIGH_VOLUME_ACCOUNTS,
            ],
        )
