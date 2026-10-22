# standard libs
import logging
import os
import uuid
from datetime import datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

# third party
from semantic_version import Version

# inception sdk
import inception_sdk.test_framework.endtoend as endtoend
from inception_sdk.test_framework.endtoend import skipForVaultVersion
from inception_sdk.test_framework.endtoend.contracts_helper import ContractNotificationResourceType
from inception_sdk.test_framework.endtoend.test.e2e.input.template.flags_contract import (
    SOME_NOTIFICATION,
)
from inception_sdk.vault.core_api import AccountV2Status, CustomerAccountRequestBody

log = logging.getLogger(__name__)
logging.basicConfig(
    level=os.environ.get("LOGLEVEL", "INFO"),
    format="%(asctime)s.%(msecs)03d - %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
FLAGS_CONTRACT = "flags_contract"
DO_SOMETHING_FLAG_ID = "DO_SOMETHING_FLAG"
endtoend.testhandle.CONTRACTS = {
    FLAGS_CONTRACT: {
        "path": "inception_sdk/test_framework/endtoend/test/e2e/input/template/"
        "flags_contract.py",
        "template_params": {},
    },
}
endtoend.testhandle.FLAG_DEFINITIONS = {
    DO_SOMETHING_FLAG_ID: "inception_sdk/test_framework/endtoend/test/e2e/input/flags/"
    "do_something_flag.resource.yaml",
}

UTC = ZoneInfo("UTC")


class TestFlagsV1(endtoend.End2Endtest):
    """
    Test backdated flags, introduced in Vault 5.2, and flags effective immediately.
    """

    def test_flags_v1(self):
        customer = endtoend.core_api_helper.create_customer()
        customer_account_v2 = endtoend.contracts_helper.create_account_v2(
            product_id=FLAGS_CONTRACT,
            account=CustomerAccountRequestBody(
                id=str(uuid.uuid4()),
                status=AccountV2Status.ACCOUNT_STATUS_OPEN,
                stakeholder_ids=[customer],
            ),
        )
        endtoend.contracts_helper.create_flag(
            flag_definition_id=DO_SOMETHING_FLAG_ID,
            account_id=customer_account_v2.id,
            description="Do something.",
        )
        flag = endtoend.contracts_helper.get_flag(DO_SOMETHING_FLAG_ID)
        self.assertEquals(len(flag), 1)
        self.assertEquals(flag[0]["account_id"], customer_account_v2.id)
        self.assertTrue(flag[0]["is_active"])

        pib_id = endtoend.postings_helper.inbound_hard_settlement(
            amount=Decimal(1),
            account_id=customer_account_v2.id,
            internal_account_id="DUMMY_CONTRA",
        )
        pib = endtoend.postings_helper.get_posting_batch(pib_id=pib_id)
        self.assertEqual(pib["status"], "POSTING_INSTRUCTION_BATCH_STATUS_ACCEPTED")

        endtoend.contracts_helper.wait_for_contract_notification(
            notification_type=SOME_NOTIFICATION,
            notification_details={DO_SOMETHING_FLAG_ID: "True"},
            resource_id=customer_account_v2.id,
            resource_type=ContractNotificationResourceType.RESOURCE_ACCOUNT,
        )

    @skipForVaultVersion(lambda v: v < Version("5.2.0"))
    def test_backdated_flags_v1(self):
        flag_effective_timestamp = datetime(2020, 1, 1, tzinfo=UTC)
        posting_timestamp = datetime(2020, 1, 2, tzinfo=UTC)
        flag_expiry_timestamp = datetime(2020, 1, 3, tzinfo=UTC)
        customer = endtoend.core_api_helper.create_customer()
        customer_account_v2 = endtoend.contracts_helper.create_account_v2(
            product_id=FLAGS_CONTRACT,
            account=CustomerAccountRequestBody(
                id=str(uuid.uuid4()),
                status=AccountV2Status.ACCOUNT_STATUS_OPEN,
                stakeholder_ids=[customer],
            ),
        )
        endtoend.contracts_helper.create_flag(
            flag_definition_id=DO_SOMETHING_FLAG_ID,
            account_id=customer_account_v2.id,
            description="Do something.",
            effective_timestamp=flag_effective_timestamp,
            expiry_timestamp=flag_expiry_timestamp,
            is_backdated=True,
        )
        flag = endtoend.contracts_helper.get_flag(
            DO_SOMETHING_FLAG_ID,
            effective_timestamp_range_from=flag_effective_timestamp,
            effective_timestamp_range_to=flag_expiry_timestamp,
        )
        self.assertEquals(len(flag), 1)
        self.assertEquals(flag[0]["account_id"], customer_account_v2.id)
        self.assertFalse(flag[0]["is_active"])
        self.assertTrue(flag[0]["is_backdated"])
        pib_id = endtoend.postings_helper.inbound_hard_settlement(
            amount=Decimal(1),
            account_id=customer_account_v2.id,
            internal_account_id="DUMMY_CONTRA",
            value_datetime=posting_timestamp,
        )
        pib = endtoend.postings_helper.get_posting_batch(pib_id=pib_id)
        self.assertEqual(pib["status"], "POSTING_INSTRUCTION_BATCH_STATUS_ACCEPTED")

        endtoend.contracts_helper.wait_for_contract_notification(
            notification_type=SOME_NOTIFICATION,
            notification_details={DO_SOMETHING_FLAG_ID: "True"},
            resource_id=customer_account_v2.id,
            resource_type=ContractNotificationResourceType.RESOURCE_ACCOUNT,
        )

    @skipForVaultVersion(lambda v: v >= Version("5.2.0"))
    def test_validation_of_backdated_flag_feature_support(self):
        with self.assertRaises(ValueError) as e:
            endtoend.core_api_helper.create_flag(
                flag_name="",
                account_id="",
                is_backdated=True,
            )
        self.assertEqual(
            str(e.exception.args[0]),
            "The /v1/flags endpoint only supports is_backdated on Vault 5.2 and above.",
        )

    def test_updated_flag(self):
        """Test setting a flag, then deactivating it before it gets read."""
        customer = endtoend.core_api_helper.create_customer()
        customer_account_v2 = endtoend.contracts_helper.create_account_v2(
            product_id=FLAGS_CONTRACT,
            account=CustomerAccountRequestBody(
                id=str(uuid.uuid4()),
                status=AccountV2Status.ACCOUNT_STATUS_OPEN,
                stakeholder_ids=[customer],
            ),
        )
        do_something_flag_response = endtoend.contracts_helper.create_flag(
            flag_definition_id=DO_SOMETHING_FLAG_ID,
            account_id=customer_account_v2.id,
            description="Do something.",
        )
        if do_something_flag_response.id:
            endtoend.core_api_helper.remove_flag(do_something_flag_response.id)
        pib_id = endtoend.postings_helper.inbound_hard_settlement(
            amount=Decimal(1),
            account_id=customer_account_v2.id,
            internal_account_id="DUMMY_CONTRA",
        )
        pib = endtoend.postings_helper.get_posting_batch(pib_id=pib_id)
        self.assertEqual(pib["status"], "POSTING_INSTRUCTION_BATCH_STATUS_ACCEPTED")

        endtoend.contracts_helper.wait_for_contract_notification(
            notification_type=SOME_NOTIFICATION,
            notification_details={DO_SOMETHING_FLAG_ID: "undefined"},
            resource_id=customer_account_v2.id,
            resource_type=ContractNotificationResourceType.RESOURCE_ACCOUNT,
        )
