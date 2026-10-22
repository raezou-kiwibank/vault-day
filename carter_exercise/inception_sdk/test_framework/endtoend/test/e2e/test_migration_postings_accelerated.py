# standard libs
import logging
import os
import uuid
from datetime import datetime
from decimal import Decimal
from typing import cast
from zoneinfo import ZoneInfo

# inception sdk
import inception_sdk.test_framework.endtoend as endtoend
from inception_sdk.test_framework.common.balance_helpers import (
    DEFAULT_DENOMINATION,
    BalanceDimensions,
)
from inception_sdk.test_framework.endtoend.test.e2e.input.template.schedule_add_1_template import (
    ONCE_ONLY_EVENT,
    SCHEDULE_DELTA,
)
from inception_sdk.vault.postings.posting_classes import (
    InboundAuthorisation,
    InboundHardSettlement,
    MigrationPostingInstructionBatchRequest,
    PostingInstruction,
    PostingInstructionBatch,
    Settlement,
)

log = logging.getLogger(__name__)
logging.basicConfig(
    level=os.environ.get("LOGLEVEL", "INFO"),
    format="%(asctime)s.%(msecs)03d - %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

TEST_CONTRACT = "test_contract"
SCHEDULE_ADD_1_TEMPLATE = "schedule_add_1_template"
endtoend.testhandle.CONTRACTS = {
    TEST_CONTRACT: {
        "path": "inception_sdk/test_framework/endtoend/test/e2e/input/template/"
        "contract_template.py",
        "template_params": {},
    },
    SCHEDULE_ADD_1_TEMPLATE: {
        "path": "inception_sdk/test_framework/endtoend/test/e2e/input/template/"
        "schedule_add_1_template.py",
        "template_params": {},
    },
}


class TestMigrationPostings(endtoend.AcceleratedEnd2EndTest):
    @classmethod
    def setUpClass(cls):
        # Force the framework to route all posting helper calls to use the async path
        endtoend.testhandle.use_kafka = True
        endtoend.testhandle.use_sync_postings = False
        super().setUpClass()

    @endtoend.AcceleratedEnd2EndTest.Decorators.control_schedules(
        {SCHEDULE_ADD_1_TEMPLATE: [ONCE_ONLY_EVENT]}
    )
    def test_migration_pib_request(self):
        endtoend.standard_setup()
        cust_id = endtoend.core_api_helper.create_customer()
        opening_timestamp = datetime(2024, 3, 6, 9, tzinfo=ZoneInfo("UTC"))
        account = endtoend.contracts_helper.create_account(
            customer=cust_id,
            contract=SCHEDULE_ADD_1_TEMPLATE,
            status="ACCOUNT_STATUS_OPEN",
            opening_timestamp=opening_timestamp,
        )
        # This timestamp is set to midnight the day before the opening_timestamp, to show
        # that the Postings Migration API can accept backdated postings.
        timestamp = datetime(2024, 3, 5, 9, 0, 0, 0, tzinfo=ZoneInfo("UTC"))
        pib_request = MigrationPostingInstructionBatchRequest(
            request_id=str(uuid.uuid4()),
            posting_instruction_batch=PostingInstructionBatch(
                posting_instructions=[
                    PostingInstruction(
                        InboundHardSettlement(
                            amount=Decimal(1),
                            target_account_id=account["id"],
                            denomination=DEFAULT_DENOMINATION,
                        ),
                        client_transaction_id=None,
                        instruction_details=None,
                        override=False,
                    ),
                ],
                value_timestamp=timestamp,
                booking_timestamp=timestamp,
            ),
            source_insert_timestamp=timestamp,
            account_sequence_number=1,
            target_account_id=account["id"],
        )
        endtoend.postings_helper.send_migration_postings_request(
            producer=endtoend.testhandle.kafka_producer,
            pib_request=pib_request,
        )
        endtoend.postings_helper.wait_for_migration_posting_responses(
            request_ids={pib_request.request_id},
            statuses={"POSTING_INSTRUCTION_BATCH_STATUS_ACCEPTED"},
        )
        account_schedules = endtoend.schedule_helper.get_account_schedules(account_id=account["id"])
        once_only_event_tags = cast(list[str], account_schedules[ONCE_ONLY_EVENT]["tags"])
        self.assertListEqual(
            once_only_event_tags,
            [
                endtoend.testhandle.controlled_schedule_tags[SCHEDULE_ADD_1_TEMPLATE][
                    ONCE_ONLY_EVENT
                ],
            ],
        )
        endtoend.schedule_helper.trigger_next_schedule_job_and_wait(
            schedule_name=ONCE_ONLY_EVENT,
            account_id=account["id"],
            effective_date=opening_timestamp + SCHEDULE_DELTA,
        )
        default_balance_dim = BalanceDimensions()
        endtoend.balances_helper.wait_for_account_balances(
            account_id=account["id"],
            expected_balances=[
                (default_balance_dim, str(Decimal(4))),
            ],
            description="Check that the schedule has incremented balance.",
        )

    """Tests our migration posting error response behaviour. Contract tests don't typically trigger
    this intentionally, as it is usually a mistake on the test writer or contract writer side, so
    we do not have any consistent usage that we can rely on to flag any breaking changes.
    """

    def test_migration_pib_response_error_handling(self):
        endtoend.standard_setup()
        cust_id = endtoend.core_api_helper.create_customer()
        account = endtoend.contracts_helper.create_account(
            customer=cust_id,
            contract=TEST_CONTRACT,
            status="ACCOUNT_STATUS_OPEN",
        )
        now = datetime.now(tz=ZoneInfo("UTC"))
        auth_request = MigrationPostingInstructionBatchRequest(
            request_id=str(uuid.uuid4()),
            posting_instruction_batch=PostingInstructionBatch(
                posting_instructions=[
                    PostingInstruction(
                        instruction=InboundAuthorisation(
                            amount=Decimal(-1),
                            target_account_id=account["id"],
                            denomination=DEFAULT_DENOMINATION,
                        )
                    )
                ],
                value_timestamp=now,
                booking_timestamp=now,
            ),
            source_insert_timestamp=now,
            account_sequence_number=1,
            target_account_id=account["id"],
        )
        # This will always trigger an error as it violates Postings API validation
        with self.assertRaises(ValueError) as auth_exception:
            endtoend.postings_helper.send_and_wait_for_posting_instruction_batch(
                pib_request=auth_request,
            )

        self.assertRegex(
            auth_exception.exception.args[0],
            r"Posting pib_request.request_id='[\d\-\w]+' resulted in error={'type': "
            r"'POSTING_INSTRUCTION_BATCH_ERROR_TYPE_INVALID_ARGUMENT', ",
        )
        # Fix the amount in the PIB to be a positive value.
        auth_request.posting_instruction_batch.posting_instructions[0].instruction.amount = Decimal(
            1
        )
        endtoend.postings_helper.send_and_wait_for_posting_instruction_batch(
            pib_request=auth_request,
        )

        now = datetime.now(tz=ZoneInfo("UTC"))
        settlement_request = MigrationPostingInstructionBatchRequest(
            request_id=str(uuid.uuid4()),
            posting_instruction_batch=PostingInstructionBatch(
                posting_instructions=[
                    PostingInstruction(
                        instruction=Settlement(
                            amount=Decimal(1),
                            final=True,
                        ),
                        client_transaction_id="non-existent-cti",
                    ),
                ],
                value_timestamp=now,
                booking_timestamp=now,
            ),
            source_insert_timestamp=now,
            account_sequence_number=2,
            target_account_id=account["id"],
        )
        with self.assertRaises(ValueError) as settlement_exception:
            endtoend.postings_helper.send_and_wait_for_posting_instruction_batch(
                pib_request=settlement_request,
            )
        self.assertRegex(
            settlement_exception.exception.args[0],
            r"Posting pib_request.request_id='[\d\-\w]+' resulted in error={'type': "
            r"'POSTING_INSTRUCTION_BATCH_ERROR_TYPE_INTERNAL', ",
        )
