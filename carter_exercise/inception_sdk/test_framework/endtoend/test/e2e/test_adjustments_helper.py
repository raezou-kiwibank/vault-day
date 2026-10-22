# standard libs
from datetime import datetime
from dateutil.relativedelta import relativedelta
from decimal import Decimal
from unittest.mock import ANY
from zoneinfo import ZoneInfo

# third party
from semantic_version import Version

# inception sdk
import inception_sdk.test_framework.endtoend as endtoend
import inception_sdk.vault.core_api as core_api
from inception_sdk.test_framework.endtoend.balances import BalanceDimensions
from inception_sdk.test_framework.endtoend.test.e2e.input.template import (
    adjustment_template,
    flexible_adjustment_template,
)

TEST_ADJUSTMENTS_CONTRACT = "TEST_ADJUSTMENTS_CONTRACT"
TEST_FLEXIBLE_ADJUSTMENTS_CONTRACT = "TEST_FLEXIBLE_ADJUSTMENTS_CONTRACT"
endtoend.testhandle.PRODUCTS = [
    endtoend.helper.TestProduct(
        product_id=TEST_ADJUSTMENTS_CONTRACT,
        product_versions=[
            endtoend.helper.TestProductVersion(
                product_version_id="v1",
                supported_denominations=["GBP", "USD"],
                path="inception_sdk/test_framework/endtoend/test/e2e/input/template/adjustment_template.py",  # noqa: E501
                template_params={},
            ),
        ],
    ),
    endtoend.helper.TestProduct(
        product_id=TEST_FLEXIBLE_ADJUSTMENTS_CONTRACT,
        product_versions=[
            endtoend.helper.TestProductVersion(
                product_version_id="v2",
                supported_denominations=["GBP", "USD"],
                path="inception_sdk/test_framework/endtoend/test/e2e/input/template/flexible_adjustment_template.py",  # noqa: E501
                template_params={},
            ),
        ],
    ),
]
endtoend.testhandle.TSIDE_TO_INTERNAL_ACCOUNT_ID = {
    core_api.AccountV2TSide.T_SIDE_LIABILITY: ["ACCRUED_INTEREST_ACCOUNT"]
}

OPENING_TIMESTAMP = datetime(2023, 1, 1, tzinfo=ZoneInfo("UTC"))


@endtoend.skipForMissingExtension(
    required_extensions=[core_api.VaultCoreExtension.SCHEDULED_ADJUSTMENTS]
)
@endtoend.skipForVaultVersionLessThan(Version("5.7.0"))
class TestListAllAdjustments(endtoend.AcceleratedEnd2EndTest):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        endtoend.standard_setup_with_multiple_product_versions()

        customer = endtoend.core_api_helper.create_customer()
        # create an account tied to the Adjustment contract
        cls.account = endtoend.contracts_helper.create_account_v2(
            product_version_id="v1",
            account=core_api.CustomerAccountRequestBody(
                status=core_api.AccountV2Status.ACCOUNT_STATUS_OPEN,
                stakeholder_ids=[customer],
                activation_timestamp=OPENING_TIMESTAMP,
            ),
        )
        # trigger the next two scheduled adjustment jobs and backdate a posting
        # to trigger an adjustment on the second schedule
        endtoend.schedule_helper.trigger_next_schedule_job_and_wait(
            schedule_name=adjustment_template.SCHEDULED_EVENT,
            account_id=cls.account.id,
        )

        backdate_timestamp = cls.account.vault_create_timestamp
        endtoend.postings_helper.inbound_hard_settlement(
            amount=Decimal(1),
            account_id=cls.account.id,
            value_datetime=backdate_timestamp,
            client_batch_id="backdated-batch",
        )

        endtoend.schedule_helper.trigger_next_schedule_job_and_wait(
            schedule_name=adjustment_template.SCHEDULED_EVENT,
            account_id=cls.account.id,
        )

    @endtoend.AcceleratedEnd2EndTest.Decorators.control_schedules(
        {TEST_ADJUSTMENTS_CONTRACT: [adjustment_template.SCHEDULED_EVENT]}
    )
    def test_list_all_adjustments_filter_by_account_ids(self):
        result = endtoend.adjustments_helper.list_all_adjustments(
            account_ids=[self.account.id],
        )

        self.assertEqual(len(result), 2)
        # the endpoint returns a list of matching Adjustments,
        # sorted by descending update_timestamp, so assert resource_adjustment_count=2 first
        self.assertListEqual(
            result,
            [
                core_api.Adjustment.model_construct(
                    id=ANY,
                    resource_adjustment_count=2,
                    account_id=self.account.id,
                    schedule_job_id=ANY,
                    status=core_api.AdjustmentStatus.COMPLETED,
                    error=None,
                    create_timestamp=ANY,
                    update_timestamp=ANY,
                    previous_watermark_timestamp=ANY,
                    timeline_start_timestamp=ANY,
                    timeline_end_timestamp=ANY,
                    correction_posting_instruction_batch_ids=[],
                ),
                core_api.Adjustment.model_construct(
                    id=ANY,
                    resource_adjustment_count=1,
                    account_id=self.account.id,
                    schedule_job_id=ANY,
                    status=core_api.AdjustmentStatus.NO_ADJUSTMENT_REQUIRED,
                    error=None,
                    create_timestamp=ANY,
                    update_timestamp=ANY,
                    previous_watermark_timestamp=ANY,
                    timeline_start_timestamp=ANY,
                    timeline_end_timestamp=ANY,
                    correction_posting_instruction_batch_ids=[],
                ),
            ],
        )

    @endtoend.AcceleratedEnd2EndTest.Decorators.control_schedules(
        {TEST_ADJUSTMENTS_CONTRACT: [adjustment_template.SCHEDULED_EVENT]}
    )
    def test_list_all_adjustments_filter_by_schedule_job_ids(self):
        # fetch the one‐off schedule we triggered so we can retrieve
        # the associated jobs
        one_off_schedule = endtoend.schedule_helper.get_account_schedules(
            account_id=self.account.id, statuses_to_exclude=[]
        )[adjustment_template.SCHEDULED_EVENT]
        self.assertIsNotNone(one_off_schedule)
        print(one_off_schedule)

        jobs = endtoend.core_api_helper.get_jobs(one_off_schedule["id"])
        # ordering isn't guaranteed so sorting by schedule_timestamp increasing
        sorted_jobs = sorted(jobs, key=lambda x: x["schedule_timestamp"])

        job_0_id = sorted_jobs[0]["id"]
        job_1_id = sorted_jobs[1]["id"]

        result = endtoend.adjustments_helper.list_all_adjustments(
            schedule_job_ids=[job_0_id],
        )

        self.assertEqual(len(result), 1)
        self.assertEqual(
            result[0],
            core_api.Adjustment.model_construct(
                id=ANY,
                resource_adjustment_count=ANY,
                account_id=self.account.id,
                schedule_job_id=job_0_id,
                status=core_api.AdjustmentStatus.NO_ADJUSTMENT_REQUIRED,
                error=None,
                create_timestamp=ANY,
                update_timestamp=ANY,
                previous_watermark_timestamp=ANY,
                timeline_start_timestamp=ANY,
                timeline_end_timestamp=ANY,
                correction_posting_instruction_batch_ids=[],
            ),
        )

        result = endtoend.adjustments_helper.list_all_adjustments(
            schedule_job_ids=[job_1_id],
        )

        self.assertEqual(len(result), 1)
        self.assertEqual(
            result[0],
            core_api.Adjustment.model_construct(
                id=ANY,
                resource_adjustment_count=ANY,
                account_id=self.account.id,
                schedule_job_id=job_1_id,
                status=core_api.AdjustmentStatus.COMPLETED,
                error=None,
                create_timestamp=ANY,
                update_timestamp=ANY,
                previous_watermark_timestamp=ANY,
                timeline_start_timestamp=ANY,
                timeline_end_timestamp=ANY,
                correction_posting_instruction_batch_ids=[],
            ),
        )


@endtoend.skipForMissingExtension(
    required_extensions=[core_api.VaultCoreExtension.SCHEDULED_ADJUSTMENTS]
)
@endtoend.skipForVaultVersionLessThan(Version("5.7.0"))
class TestBatchGetAdjustments(endtoend.End2Endtest):
    def test_batch_get_adjustments(self):
        customer = endtoend.core_api_helper.create_customer()
        account = endtoend.contracts_helper.create_account_v2(
            product_version_id="v1",
            account=core_api.CustomerAccountRequestBody(
                status=core_api.AccountV2Status.ACCOUNT_STATUS_OPEN,
                stakeholder_ids=[customer],
                activation_timestamp=OPENING_TIMESTAMP,
            ),
        )

        # trigger the next scheduled adjustment job
        triggered_job = endtoend.schedule_helper.trigger_next_schedule_job_and_wait(
            schedule_name=adjustment_template.SCHEDULED_EVENT,
            account_id=account.id,
        )
        self.assertIsNotNone(triggered_job)

        adjustments = endtoend.adjustments_helper.list_all_adjustments(
            account_ids=[account.id],
        )
        self.assertEqual(len(adjustments), 1)
        adjustment_id = adjustments[0].id

        result = endtoend.adjustments_helper.batch_get_adjustments(
            request=core_api.BatchGetAdjustmentsRequest(ids=[adjustment_id])
        )
        self.assertEqual(
            result.adjustments.get(adjustment_id),
            core_api.Adjustment.model_construct(
                id=adjustment_id,
                resource_adjustment_count=ANY,
                account_id=account.id,
                schedule_job_id=ANY,
                status=core_api.AdjustmentStatus.NO_ADJUSTMENT_REQUIRED,
                error=None,
                create_timestamp=ANY,
                update_timestamp=ANY,
                previous_watermark_timestamp=ANY,
                timeline_start_timestamp=ANY,
                timeline_end_timestamp=ANY,
                correction_posting_instruction_batch_ids=[],
            ),
        )


@endtoend.skipForMissingExtension(
    required_extensions=[core_api.VaultCoreExtension.SCHEDULED_ADJUSTMENTS]
)
@endtoend.skipForVaultVersionLessThan(Version("5.7.0"))
class TestWaitForAdjustmentEvents(endtoend.AcceleratedEnd2EndTest):
    def test_wait_for_multiple_adjustment_events(self):
        endtoend.standard_setup_with_multiple_product_versions()
        customer = endtoend.core_api_helper.create_customer()
        account = endtoend.contracts_helper.create_account_v2(
            product_version_id="v1",
            account=core_api.CustomerAccountRequestBody(
                status=core_api.AccountV2Status.ACCOUNT_STATUS_OPEN,
                stakeholder_ids=[customer],
                activation_timestamp=OPENING_TIMESTAMP,
            ),
        )

        endtoend.schedule_helper.trigger_next_schedule_job_and_wait(
            schedule_name=adjustment_template.SCHEDULED_EVENT,
            account_id=account.id,
        )
        endtoend.adjustments_helper.wait_for_adjustment_event(
            account_id=account.id,
            target_status=core_api.AdjustmentStatus.NO_ADJUSTMENT_REQUIRED,
            target_resource_adjustment_count=1,
        )

        backdate_timestamp = account.vault_create_timestamp
        backdated_pib_id = endtoend.postings_helper.inbound_hard_settlement(
            amount=Decimal(1),
            account_id=account.id,
            value_datetime=backdate_timestamp,
            client_batch_id="backdated-batch",
        )
        backdated_pib = endtoend.postings_helper.get_posting_batch(pib_id=backdated_pib_id)
        self.assertEqual(backdated_pib["status"], "POSTING_INSTRUCTION_BATCH_STATUS_ACCEPTED")

        endtoend.schedule_helper.trigger_next_schedule_job_and_wait(
            schedule_name=adjustment_template.SCHEDULED_EVENT,
            account_id=account.id,
        )

        endtoend.adjustments_helper.wait_for_adjustment_event(
            account_id=account.id,
            target_status=core_api.AdjustmentStatus.RUNNING,
            target_resource_adjustment_count=2,
        )
        endtoend.adjustments_helper.wait_for_adjustment_event(
            account_id=account.id,
            target_status=core_api.AdjustmentStatus.COMPLETED,
            target_resource_adjustment_count=2,
        )


@endtoend.skipForMissingExtension(
    required_extensions=[core_api.VaultCoreExtension.SCHEDULED_ADJUSTMENTS]
)
@endtoend.skipForVaultVersionLessThan(Version("5.11.0"), truncate_level="patch")
class TestFlexibleAdjustments(endtoend.AcceleratedEnd2EndTest):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        endtoend.standard_setup_with_multiple_product_versions()

        cls.customer = endtoend.core_api_helper.create_customer()

    @endtoend.AcceleratedEnd2EndTest.Decorators.control_schedules(
        {
            TEST_FLEXIBLE_ADJUSTMENTS_CONTRACT: [
                flexible_adjustment_template.ADJUSTMENT_EVENT,
                flexible_adjustment_template.SCHEDULED_EVENT,
            ],
        }
    )
    def test_flexible_adjustments(self):

        account = endtoend.contracts_helper.create_account_v2(
            product_version_id="v2",
            account=core_api.CustomerAccountRequestBody(
                status=core_api.AccountV2Status.ACCOUNT_STATUS_OPEN,
                stakeholder_ids=[self.customer],
                activation_timestamp=OPENING_TIMESTAMP,
            ),
        )

        ihs_pib_id = endtoend.postings_helper.inbound_hard_settlement(
            amount=Decimal(1000),
            account_id=account.id,
            value_datetime=OPENING_TIMESTAMP + relativedelta(seconds=1),
            client_batch_id="backdated-batch-flexible",
        )
        ihs_pib = endtoend.postings_helper.get_posting_batch(pib_id=ihs_pib_id)
        self.assertEqual(ihs_pib["status"], "POSTING_INSTRUCTION_BATCH_STATUS_ACCEPTED")

        endtoend.schedule_helper.trigger_next_schedule_job_and_wait(
            schedule_name=flexible_adjustment_template.ADJUSTMENT_EVENT,
            account_id=account.id,
        )

        endtoend.schedule_helper.trigger_next_schedule_job_and_wait(
            schedule_name=flexible_adjustment_template.SCHEDULED_EVENT,
            account_id=account.id,
        )

        endtoend.schedule_helper.trigger_next_schedule_job_and_wait(
            schedule_name=flexible_adjustment_template.ADJUSTMENT_EVENT,
            account_id=account.id,
        )

        endtoend.schedule_helper.trigger_next_schedule_job_and_wait(
            schedule_name=flexible_adjustment_template.SCHEDULED_EVENT,
            account_id=account.id,
        )

        endtoend.balances_helper.wait_for_account_balances(
            account_id=account.id,
            expected_balances=[
                (BalanceDimensions(address="DEFAULT", denomination="GBP"), "1000"),
                (BalanceDimensions(address="ACCRUED_INTEREST_PAYABLE", denomination="GBP"), "10"),
            ],
        )

        backdated_pib_id = endtoend.postings_helper.inbound_hard_settlement(
            amount=Decimal(500),
            account_id=account.id,
            value_datetime=OPENING_TIMESTAMP + relativedelta(seconds=1),
            client_batch_id="backdated-batch-flexible",
        )
        backdated_pib = endtoend.postings_helper.get_posting_batch(pib_id=backdated_pib_id)
        self.assertEqual(backdated_pib["status"], "POSTING_INSTRUCTION_BATCH_STATUS_ACCEPTED")

        endtoend.schedule_helper.trigger_next_schedule_job_and_wait(
            schedule_name=flexible_adjustment_template.ADJUSTMENT_EVENT,
            account_id=account.id,
        )

        endtoend.schedule_helper.trigger_next_schedule_job_and_wait(
            schedule_name=flexible_adjustment_template.SCHEDULED_EVENT,
            account_id=account.id,
        )

        # Wait for the RUNNING and COMPLETED state of adjustment count 3
        endtoend.adjustments_helper.wait_for_adjustment_event(
            account_id=account.id,
            target_status=core_api.AdjustmentStatus.RUNNING,
            target_resource_adjustment_count=3,
        )
        endtoend.adjustments_helper.wait_for_adjustment_event(
            account_id=account.id,
            target_status=core_api.AdjustmentStatus.COMPLETED,
            target_resource_adjustment_count=3,
        )

        correction_pibs = endtoend.adjustments_helper.get_correction_posting_instruction_batches(
            account_id=account.id,
            resource_adjustment_count=3,
        )
        self.assertEqual(len(correction_pibs), 1)
        pib = correction_pibs[0]
        self.assertEqual(pib.status, core_api.PostingInstructionBatchStatus.ACCEPTED)

        expected_value_timestamp = datetime(2023, 1, 1, 23, 59, 59, tzinfo=ZoneInfo("UTC"))
        expected_booking_timestamp = datetime(2023, 1, 2, 23, 59, 59, tzinfo=ZoneInfo("UTC"))
        self.assertEqual(pib.value_timestamp, expected_value_timestamp)
        self.assertEqual(pib.booking_timestamp, expected_booking_timestamp)

        actual_postings = list(pib.posting_instructions[0].committed_postings)
        expected_postings = [
            core_api.Posting(
                credit=False,
                amount="5",
                account_id=endtoend.testhandle.internal_account_id_to_uploaded_id[
                    "ACCRUED_INTEREST_ACCOUNT"
                ],
                denomination="GBP",
                phase=core_api.PostingPhase.COMMITTED,
                account_address="DEFAULT",
                asset="COMMERCIAL_BANK_MONEY",
            ),
            core_api.Posting(
                credit=True,
                amount="5",
                account_id=account.id,
                denomination="GBP",
                phase=core_api.PostingPhase.COMMITTED,
                account_address="ACCRUED_INTEREST_PAYABLE",
                asset="COMMERCIAL_BANK_MONEY",
            ),
        ]
        self.assertCountEqual(actual_postings, expected_postings)

        endtoend.balances_helper.wait_for_account_balances(
            account_id=account.id,
            expected_balances=[
                (BalanceDimensions(address="DEFAULT", denomination="GBP"), "1500"),
                (BalanceDimensions(address="ACCRUED_INTEREST_PAYABLE", denomination="GBP"), "30"),
            ],
        )

        endtoend.schedule_helper.trigger_next_schedule_job_and_wait(
            schedule_name=flexible_adjustment_template.ADJUSTMENT_EVENT,
            account_id=account.id,
        )

        endtoend.schedule_helper.trigger_next_schedule_job_and_wait(
            schedule_name=flexible_adjustment_template.SCHEDULED_EVENT,
            account_id=account.id,
        )

        endtoend.balances_helper.wait_for_account_balances(
            account_id=account.id,
            expected_balances=[
                (BalanceDimensions(address="DEFAULT", denomination="GBP"), "1500"),
                (BalanceDimensions(address="ACCRUED_INTEREST_PAYABLE", denomination="GBP"), "45"),
            ],
        )
