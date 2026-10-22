# inception sdk
import inception_sdk.test_framework.endtoend as endtoend
import inception_sdk.vault.core_api as core_api
from inception_sdk.test_framework.endtoend.helper import TestProduct, TestProductVersion

# GIVEN: A product with multiple versions using the new schema
# This triggers standard_setup_with_multiple_product_versions in setUpClass
PATH_DIR = "inception_sdk/test_framework/endtoend/test/e2e/input/template"
endtoend.testhandle.PRODUCTS = [
    TestProduct(
        product_id="product_id_1",
        product_versions=[
            TestProductVersion(
                product_version_id="product_version_id_1",
                path=PATH_DIR + "/adjustments_minimal.py",
                supported_denominations=["XYZ"],
                adjustments_versioning_policy=core_api.AdjustmentsVersioningPolicy.LATEST,
            ),
            TestProductVersion(
                product_version_id="product_version_id_2",
                path=PATH_DIR + "/adjustments_minimal_patch.py",
                supported_denominations=["XYZ"],
                adjustments_versioning_policy=core_api.AdjustmentsVersioningPolicy.HISTORIC,
            ),
        ],
    ),
]


@endtoend.skipForMissingExtension(
    required_extensions=[core_api.VaultCoreExtension.SCHEDULED_ADJUSTMENTS]
)
class MultipleVersionMappingTest(endtoend.End2Endtest):
    def test_testhandle_state_validation(self):
        """
        Verifies that the TestInstance contains the expected mappings after setup.
        """

        # 1. Verify user product_version -> Vault product_version_id mapping
        # Both versions should be registered in the new mapping dictionary
        self.assertIn(
            "product_version_id_1",
            endtoend.testhandle.product_version_id_to_uploaded_product_version_id,
        )
        self.assertIn(
            "product_version_id_2",
            endtoend.testhandle.product_version_id_to_uploaded_product_version_id,
        )

        new_product_version_uploaded_id = (
            endtoend.testhandle.product_version_id_to_uploaded_product_version_id[
                "product_version_id_1"
            ]
        )
        patch_product_version_uploaded_id = (
            endtoend.testhandle.product_version_id_to_uploaded_product_version_id[
                "product_version_id_2"
            ]
        )

        self.assertNotEqual(
            new_product_version_uploaded_id,
            patch_product_version_uploaded_id,
            "Each version must have a unique Vault ID",
        )

        # User defined product_version_id should be different to uploaded product_version_id
        self.assertNotEqual(
            "product_version_id_1",
            new_product_version_uploaded_id,
        )
        self.assertNotEqual(
            "product_version_id_2",
            patch_product_version_uploaded_id,
        )

        # 2. Verify user product_id -> Vault product_version_id mapping
        self.assertIn("product_id_1", endtoend.testhandle.contract_pid_to_uploaded_pid)

        # 3. Verify CLU Reference Mapping Integration
        # Ensure the new versions are available for dependency resolution
        self.assertEqual(
            endtoend.testhandle.clu_reference_mappings["product_version_id_1"],
            new_product_version_uploaded_id,
        )
        self.assertEqual(
            endtoend.testhandle.clu_reference_mappings["product_version_id_2"],
            patch_product_version_uploaded_id,
        )

    def test_product_container_isolation(self):
        """
        Verifies that both versions belong to the same E2E Product container.
        """
        # The E2E Product ID (e.g. e2e_multi_version_product_hash) should be consistent
        e2e_pid = endtoend.testhandle.contract_pid_to_uploaded_pid["product_id_1"]
        self.assertTrue(e2e_pid.startswith("e2e_product_id_1"))

        # Verify both versions in Vault belong to this same container
        new_product_version_details = endtoend.core_api_helper.get_product_version(
            endtoend.testhandle.product_version_id_to_uploaded_product_version_id[
                "product_version_id_1"
            ]
        )
        patch_product_version_details = endtoend.core_api_helper.get_product_version(
            endtoend.testhandle.product_version_id_to_uploaded_product_version_id[
                "product_version_id_2"
            ]
        )

        self.assertEqual(new_product_version_details["product_id"], e2e_pid)
        self.assertEqual(patch_product_version_details["product_id"], e2e_pid)
