# standard libs
import uuid

# third party
from semantic_version import Version

# inception sdk
import inception_sdk.test_framework.endtoend as endtoend
import inception_sdk.vault.core_api as core_api
from inception_sdk.test_framework.endtoend.helper import TestProduct, TestProductVersion

endtoend.testhandle.PRODUCTS = [
    TestProduct(
        product_id="product_id_1",
        product_versions=[
            TestProductVersion(
                product_version_id="product_version_id_1",
                path="inception_sdk/test_framework/endtoend/test/e2e/input/template/"
                "adjustments_minimal.py",
                supported_denominations=["XYZ"],
                adjustments_versioning_policy=core_api.AdjustmentsVersioningPolicy.LATEST,
            ),
            TestProductVersion(
                product_version_id="product_version_id_2",
                path="inception_sdk/test_framework/endtoend/test/e2e/input/template/"
                "adjustments_minimal_patch.py",
                supported_denominations=["XYZ"],
                adjustments_versioning_policy=core_api.AdjustmentsVersioningPolicy.HISTORIC,
            ),
        ],
    )
]


@endtoend.skipForMissingExtension(
    required_extensions=[core_api.VaultCoreExtension.SCHEDULED_ADJUSTMENTS]
)
@endtoend.skipForVaultVersionLessThan(Version("5.9.0"))
class TestBatchUpdateProductVersionsProductVersion(endtoend.End2Endtest):

    def test_batch_update_adjustments_versioning_policy(self):
        # Get the product version ID
        product_version_id = endtoend.testhandle.product_version_id_to_uploaded_product_version_id[
            "product_version_id_1"
        ]

        # Create the batch update request to set adjustments versioning policy to historic
        product_version_updates = [
            core_api.ProductVersionUpdate(
                product_version=core_api.ProductVersionUpdateProductVersion(
                    id=product_version_id,
                    adjustments_versioning_policy=core_api.AdjustmentsVersioningPolicy.HISTORIC,
                ),
                update_mask=core_api.UpdateMask(paths=["adjustments_versioning_policy"]),
            ),
        ]

        # Perform the batch update
        response = endtoend.core_api_helper.batch_update_product_versions(
            request_id=str(uuid.uuid4()),
            product_version_updates=product_version_updates,
        )

        # Verify the response
        self.assertEqual(len(response.product_versions), 1)
        updated_product_version = response.product_versions[0]
        self.assertEqual(updated_product_version.id, product_version_id)
        self.assertEqual(
            updated_product_version.adjustments_versioning_policy,
            core_api.AdjustmentsVersioningPolicy.HISTORIC,
        )

    def test_batch_update_adjustments_patch_version_id(self):
        # Get the product version ID
        product_version_id = endtoend.testhandle.product_version_id_to_uploaded_product_version_id[
            "product_version_id_1"
        ]

        # Create the batch update request to set adjustments patch version id
        patch_version_id = endtoend.testhandle.product_version_id_to_uploaded_product_version_id[
            "product_version_id_2"
        ]
        product_version_updates = [
            core_api.ProductVersionUpdate(
                product_version=core_api.ProductVersionUpdateProductVersion(
                    id=product_version_id,
                    adjustments_patch_version_id=patch_version_id,
                ),
                update_mask=core_api.UpdateMask(paths=["adjustments_patch_version_id"]),
            ),
        ]

        # Perform the batch update
        response = endtoend.core_api_helper.batch_update_product_versions(
            request_id=str(uuid.uuid4()),
            product_version_updates=product_version_updates,
        )

        # Verify the response
        self.assertEqual(len(response.product_versions), 1)
        updated_product_version = response.product_versions[0]
        self.assertEqual(updated_product_version.id, product_version_id)
        self.assertEqual(
            updated_product_version.adjustments_patch_version_id,
            patch_version_id,
        )

    def test_batch_update_adjustments_versioning_policy_and_patch_version_id(self):
        # Get the product version ID
        product_version_id = endtoend.testhandle.product_version_id_to_uploaded_product_version_id[
            "product_version_id_1"
        ]

        # Create the batch update request to set both adjustments patch version id
        # and policy to historic
        patch_version_id = endtoend.testhandle.product_version_id_to_uploaded_product_version_id[
            "product_version_id_2"
        ]

        product_version_updates = [
            core_api.ProductVersionUpdate(
                product_version=core_api.ProductVersionUpdateProductVersion(
                    id=product_version_id,
                    adjustments_patch_version_id=patch_version_id,
                    adjustments_versioning_policy=core_api.AdjustmentsVersioningPolicy.HISTORIC,
                ),
                update_mask=core_api.UpdateMask(
                    paths=["adjustments_patch_version_id", "adjustments_versioning_policy"]
                ),
            ),
        ]

        # Perform the batch update
        response = endtoend.core_api_helper.batch_update_product_versions(
            request_id=str(uuid.uuid4()),
            product_version_updates=product_version_updates,
        )

        # Verify the response
        self.assertEqual(len(response.product_versions), 1)
        updated_product_version = response.product_versions[0]
        self.assertEqual(updated_product_version.id, product_version_id)
        self.assertEqual(
            updated_product_version.adjustments_patch_version_id,
            patch_version_id,
        )
        self.assertEqual(
            updated_product_version.adjustments_versioning_policy,
            core_api.AdjustmentsVersioningPolicy.HISTORIC,
        )
