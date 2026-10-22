# standard libs
import logging
import os
from datetime import datetime
from dateutil.relativedelta import relativedelta
from zoneinfo import ZoneInfo

# inception sdk
import inception_sdk.test_framework.common.date_helper as date_helper
import inception_sdk.test_framework.endtoend as endtoend
from inception_sdk.test_framework.endtoend.test.e2e.input.template import (
    three_off_schedule_template,
)

UTC = ZoneInfo("UTC")
log = logging.getLogger(__name__)
logging.basicConfig(
    level=os.environ.get("LOGLEVEL", "INFO"),
    format="%(asctime)s.%(msecs)03d - %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
TEST_CONTRACT = "test_contract"
endtoend.testhandle.CONTRACTS = {
    TEST_CONTRACT: {
        "path": "inception_sdk/test_framework/endtoend/test/e2e/input/template/"
        "three_off_schedule_template.py",
        "template_params": {},
    },
}


class TestTriggerandWaitForJobsUntil(endtoend.AcceleratedEnd2EndTest):

    @endtoend.AcceleratedEnd2EndTest.Decorators.control_schedules(
        {TEST_CONTRACT: [three_off_schedule_template.THRICE_EVENT]}
    )
    def test_trigger_and_wait_until(self):
        endtoend.standard_setup()
        customer_id = endtoend.core_api_helper.create_customer()

        opening_timestamp = datetime(2023, 1, 1, tzinfo=UTC)
        first_run_timestamp = opening_timestamp + relativedelta(minutes=0)
        second_run_timestamp = opening_timestamp + relativedelta(minutes=25)
        third_run_timestamp = opening_timestamp + relativedelta(minutes=50)

        # Test via v1 accounts as we can't backdate v2 accounts
        customer_account = endtoend.contracts_helper.create_account(
            customer=customer_id,
            contract=TEST_CONTRACT,
            opening_timestamp=opening_timestamp,
        )

        triggered_jobs = endtoend.schedule_helper.trigger_and_wait_for_schedule_jobs_until(
            schedule_name=three_off_schedule_template.THRICE_EVENT,
            resource_id=customer_account["id"],
            resource_type=endtoend.schedule_helper.ResourceType.ACCOUNT,
            trigger_until=second_run_timestamp,
        )

        # as a precaution we also confirm we haven't accidentally triggered three schedules by
        # checking schedule and jobs
        one_off_schedule = endtoend.schedule_helper.get_account_schedules(
            account_id=customer_account["id"], statuses_to_exclude=[]
        )[three_off_schedule_template.THRICE_EVENT]

        self.assertEqual(
            date_helper.isoparse(one_off_schedule["next_run_timestamp"]), third_run_timestamp
        )
        self.assertTrue(len(endtoend.core_api_helper.get_jobs(one_off_schedule["id"])) == 2)

        self.assertListEqual(
            triggered_jobs,
            [
                endtoend.schedule_helper.Job(
                    tag_id=endtoend.testhandle.controlled_schedule_tags[TEST_CONTRACT][
                        three_off_schedule_template.THRICE_EVENT
                    ],
                    schedule_id=one_off_schedule["id"],
                    effective_date=first_run_timestamp,
                ),
                endtoend.schedule_helper.Job(
                    tag_id=endtoend.testhandle.controlled_schedule_tags[TEST_CONTRACT][
                        three_off_schedule_template.THRICE_EVENT
                    ],
                    schedule_id=one_off_schedule["id"],
                    effective_date=second_run_timestamp,
                ),
            ],
        )
