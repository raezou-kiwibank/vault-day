# standard libs
import uuid
from datetime import datetime
from dateutil.relativedelta import relativedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

# third party
from semantic_version import Version

# inception sdk
import inception_sdk.test_framework.endtoend as endtoend
import inception_sdk.vault.core_api as core_api
from inception_sdk.test_framework.endtoend.balances import BalanceDimensions
from inception_sdk.test_framework.endtoend.helper import TestProduct, TestProductVersion
from inception_sdk.test_framework.endtoend.test.e2e.input.template import (
    adjustments_product_version_1,
)

# GIVEN product p1 with multiple versions pv1, pv2
PATH = "inception_sdk/test_framework/endtoend/test/e2e/input/template/"
PARAMS_PATH = "inception_sdk/test_framework/endtoend/test/e2e/input/parameters"
ADJUSTMENTS_INTERNAL_ACCOUNT = "ADJUSTMENTS_INTERNAL"
DUMMY_CONTRA_ACCOUNT = "DUMMY_CONTRA"
PRODUCT_ID = "adjustment_test_product"
endtoend.testhandle.PRODUCTS = [
    TestProduct(
        product_id=PRODUCT_ID,
        product_versions=[
            TestProductVersion(
                product_version_id="pv1",
                path=PATH + "adjustments_product_version_1.py",
                supported_denominations=["XYZ"],
                adjustments_versioning_policy=core_api.AdjustmentsVersioningPolicy.HISTORIC,
            ),
            TestProductVersion(
                product_version_id="pv2",
                path=PATH + "adjustments_product_version_2.py",
                supported_denominations=["XYZ"],
                adjustments_versioning_policy=core_api.AdjustmentsVersioningPolicy.HISTORIC,
            ),
        ],
    )
]

endtoend.testhandle.PARAMETER_RESOURCE_DIRS = [PARAMS_PATH]
endtoend.testhandle.TSIDE_TO_INTERNAL_ACCOUNT_ID = {
    core_api.AccountV2TSide.T_SIDE_LIABILITY: [ADJUSTMENTS_INTERNAL_ACCOUNT, DUMMY_CONTRA_ACCOUNT],
}
OPENING_TIMESTAMP = datetime(2023, 1, 1, tzinfo=ZoneInfo("UTC"))


@endtoend.skipForMissingExtension(
    required_extensions=[core_api.VaultCoreExtension.SCHEDULED_ADJUSTMENTS]
)
@endtoend.skipForVaultVersionLessThan(Version("5.9.0"))
class TestHistoricAdjustmentVersioning(endtoend.AcceleratedEnd2EndTest):

    @endtoend.AcceleratedEnd2EndTest.Decorators.control_schedules(
        {PRODUCT_ID: ["SCHEDULED_EVENT_1"]}
    )
    def test_historic_adjustment_uses_correct_pv2_logic(self):
        endtoend.standard_setup_with_multiple_product_versions()

        # GIVEN customer c1 with account a1 created at t0 with pv1
        # GIVEN backdated posting crediting 1 GBP at time t0 triggered at time t3
        # GIVEN pv1 patched by pv2 at time t2
        #
        # time            0----1----2----3----4---->
        # pv1             [---------)
        # pv2                       [-------------->
        # a1 open         x
        # patched                   x
        # schedule             o              x
        # adjustment      [-------------------)
        # adj-post-hook        x
        # posting sent    +1             x
        internal_account = adjustments_product_version_1.PARAM_ADJUSTMENTS_INTERNAL_ACCOUNT
        customer_id = endtoend.core_api_helper.create_customer()
        account = endtoend.contracts_helper.create_account_v2(
            product_version_id="pv1",
            account=core_api.CustomerAccountRequestBody(
                smart_contract_version_id="pv1",
                status=core_api.AccountV2Status.ACCOUNT_STATUS_OPEN,
                stakeholder_ids=[customer_id],
                activation_timestamp=OPENING_TIMESTAMP,
            ),
            create_options=core_api.CreateOptions(
                parameter_values={
                    internal_account: core_api.AccountIdParameterValue(
                        account_id_value=ADJUSTMENTS_INTERNAL_ACCOUNT
                    )
                }
            ),
        )
        account_id = account.id

        # Trigger the first schedule, no adjustment expected at time t1
        job_1 = endtoend.schedule_helper.trigger_next_schedule_job_or_raise(
            resource_id=account_id,
            schedule_name="SCHEDULED_EVENT_1",
            resource_type=endtoend.schedule_helper.ResourceType.ACCOUNT,
        )
        endtoend.adjustments_helper.wait_for_adjustment_event(
            account_id=account_id,
            target_status=core_api.AdjustmentStatus.NO_ADJUSTMENT_REQUIRED,
            target_resource_adjustment_count=1,
        )
        endtoend.schedule_helper.wait_for_schedule_job(job=job_1)

        # WHEN pv1 is updated to be patched by pv2 at time t2
        pv1_id = endtoend.testhandle.product_version_id_to_uploaded_product_version_id["pv1"]
        pv2_id = endtoend.testhandle.product_version_id_to_uploaded_product_version_id["pv2"]
        endtoend.core_api_helper.batch_update_product_versions(
            request_id=str(uuid.uuid4()),
            product_version_updates=[
                core_api.ProductVersionUpdate(
                    product_version=core_api.ProductVersionUpdateProductVersion(
                        id=pv1_id,
                        adjustments_patch_version_id=pv2_id,
                    ),
                    update_mask=core_api.UpdateMask(paths=["adjustments_patch_version_id"]),
                ),
            ],
        )

        # WHEN a backdated posting of 1 GBP is inserted at t3, valued at t0
        backdated_pib_id = endtoend.postings_helper.inbound_hard_settlement(
            account_id=account_id,
            amount=Decimal("1"),
            denomination="GBP",
            value_datetime=OPENING_TIMESTAMP + relativedelta(seconds=2),
            client_batch_id="backdated-batch",
        )

        backdated_pib = endtoend.postings_helper.get_posting_batch(pib_id=backdated_pib_id)
        self.assertEqual(backdated_pib["status"], "POSTING_INSTRUCTION_BATCH_STATUS_ACCEPTED")

        # Trigger the second schedule, asserts that adjustment completes at time t4
        job_2 = endtoend.schedule_helper.trigger_next_schedule_job_or_raise(
            resource_id=account_id,
            schedule_name="SCHEDULED_EVENT_1",
            resource_type=endtoend.schedule_helper.ResourceType.ACCOUNT,
        )
        endtoend.adjustments_helper.wait_for_adjustment_event(
            account_id=account_id,
            target_status=core_api.AdjustmentStatus.RUNNING,
            target_resource_adjustment_count=2,
        )

        endtoend.adjustments_helper.wait_for_adjustment_event(
            account_id=account_id,
            target_status=core_api.AdjustmentStatus.COMPLETED,
            target_resource_adjustment_count=2,
        )

        endtoend.schedule_helper.wait_for_schedule_job(job=job_2)
        # THEN since pv1 is patched by pv2 it will resolve with pv2 contract
        # i.e. fee is charged at 20 GBP from pv2, not 10 GBP from pv1
        # Hence, balance is: 1 + 20 = 21 GBP
        endtoend.balances_helper.wait_for_account_balances(
            account_id=account_id,
            expected_balances=[(BalanceDimensions(address="DEFAULT", denomination="GBP"), "21")],
        )
