# standard libs
import logging
import os
from datetime import datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

# third party
from semantic_version import Version

# inception sdk
import inception_sdk.test_framework.endtoend as endtoend
import inception_sdk.vault.core_api as core_api

log = logging.getLogger(__name__)
logging.basicConfig(
    level=os.environ.get("LOGLEVEL", "INFO"),
    format="%(asctime)s.%(msecs)03d - %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
UTC = ZoneInfo("UTC")
TEST_ACCOUNT_ATTRIBUTE_CONTRACT = "test_account_attribute_contract"
endtoend.testhandle.CONTRACTS = {
    TEST_ACCOUNT_ATTRIBUTE_CONTRACT: {
        "path": "inception_sdk/test_framework/common/test/input/"
        "account_attribute_value_contract.py",
        "template_params": {},
    }
}


class TestListAccountAttributes(endtoend.End2Endtest):
    @endtoend.skipForVaultVersionLessThan(Version("5.4.0"))
    def test_list_account_attributes(self):
        effective_timestamp = datetime(2025, 1, 1, tzinfo=UTC)
        datetime_attribute_value = datetime(2025, 2, 2, tzinfo=UTC)

        customer = endtoend.core_api_helper.create_customer()
        account1 = endtoend.contracts_helper.create_account_v2(
            product_id=TEST_ACCOUNT_ATTRIBUTE_CONTRACT,
            account=core_api.CustomerAccountRequestBody(
                status=core_api.AccountV2Status.ACCOUNT_STATUS_OPEN,
                stakeholder_ids=[customer],
            ),
        )
        account_attribute_values_response = (
            endtoend.accounts_helper.get_all_account_attribute_values(
                account_ids=[account1.id],
                attribute_names=[
                    "string_attribute",
                    "decimal_attribute",
                    "date_time_attribute",
                ],
                effective_timestamps=[effective_timestamp],
            )
        )

        self.assertEqual(
            account_attribute_values_response,
            [
                core_api.AccountAttributeValue(
                    account_id=account1.id,
                    attribute_name="date_time_attribute",
                    effective_timestamp=effective_timestamp,
                    value=core_api.AttributeValue(
                        date_time_value=core_api.AttributeDateTimeValue(
                            value=datetime_attribute_value
                        )
                    ),
                ),
                core_api.AccountAttributeValue(
                    account_id=account1.id,
                    attribute_name="decimal_attribute",
                    effective_timestamp=effective_timestamp,
                    value=core_api.AttributeValue(
                        decimal_value=core_api.AttributeDecimalValue(value=Decimal("1234"))
                    ),
                ),
                core_api.AccountAttributeValue(
                    account_id=account1.id,
                    attribute_name="string_attribute",
                    effective_timestamp=effective_timestamp,
                    value=core_api.AttributeValue(
                        string_value=core_api.AttributeStringValue(value="string_attribute_value")
                    ),
                ),
            ],
        )
