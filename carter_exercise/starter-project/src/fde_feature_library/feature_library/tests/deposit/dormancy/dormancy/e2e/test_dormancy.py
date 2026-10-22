# standard libs
from datetime import datetime
from json import dumps
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
from dateutil.relativedelta import relativedelta

# inception sdk
from inception_sdk.test_framework import endtoend
from inception_sdk.vault.core_api import (
    AccountV2Status,
    CreateOptions,
    CustomerAccountRequestBody,
    FlagV1FlagValue,
    StringParameterValue,
)

# e2e
import tests.deposit.dormancy.dormancy.e2e.accounts as accounts
import tests.deposit.dormancy.dormancy.e2e.parameters as parameters
import tests.deposit.dormancy.dormancy.simulation.dimensions as dimensions

# tests
from tests.common.test_denomination import DEFAULT_DENOMINATION

UTC = ZoneInfo("UTC")
SMART_CONTRACT = "tests/deposit/dormancy/dormancy/smart_contract.py"


@pytest.mark.e2e
class DormancyE2ETest(endtoend.AcceleratedEnd2EndTest):
    @classmethod
    def setUpClass(cls):
        endtoend.testhandle.CONTRACTS = {
            "DORMANCY_SC": {
                "path": str(Path(SMART_CONTRACT)),
                "template_params": {},
            },
        }
        endtoend.testhandle.TSIDE_TO_INTERNAL_ACCOUNT_ID = accounts.internal_accounts_tside
        endtoend.testhandle.PARAMETER_RESOURCE_DIRS = [
            str(Path("src/feature_library/common/parameter_resource_defs")),
            str(Path("src/feature_library/deposit/dormancy/parameter_resource_defs")),
        ]
        endtoend.testhandle.FLAG_DEFINITIONS = {
            "ACCOUNT_DORMANT": str(
                Path("tests/deposit/dormancy/dormancy/e2e/flag_defs/account_dormant.resource.yaml")
            )
        }
        super().setUpClass()

    def test_postings_rejected_when_account_dormant(self):
        endtoend.standard_setup()
        opening_date = datetime(2026, 1, 1, tzinfo=UTC)

        customer_id = endtoend.core_api_helper.create_customer()

        # Update parameter values with the mapped flag ID
        import feature_library.deposit.dormancy.dormancy as dormancy_module

        parameter_values = parameters.parameter_values.copy()
        parameter_values[dormancy_module.DORMANCY_FLAGS_PARAM_ID] = StringParameterValue(
            string_value=dumps([endtoend.testhandle.flag_definition_id_mapping["ACCOUNT_DORMANT"]])
        )

        customer_account = endtoend.contracts_helper.create_account_v2(
            product_id="DORMANCY_SC",
            account=CustomerAccountRequestBody(
                status=AccountV2Status.ACCOUNT_STATUS_OPEN,
                stakeholder_ids=[customer_id],
                activation_timestamp=opening_date,
            ),
            create_options=CreateOptions(
                parameter_values=parameter_values,
            ),
        )

        # Postings accepted when account is NOT dormant
        endtoend.postings_helper.inbound_hard_settlement(
            amount="100.00",
            denomination=DEFAULT_DENOMINATION,
            instruction_details={"description": "Initial deposit"},
            account_id=customer_account.id,
            internal_account_id=accounts.INTERNAL_ACCOUNT,
            value_datetime=opening_date + relativedelta(hours=1),
        )

        # Set dormant flag
        endtoend.contracts_helper.create_flag(
            flag_definition_id="ACCOUNT_DORMANT",
            account_id=customer_account.id,
            effective_timestamp=opening_date + relativedelta(hours=2),
            is_backdated=True,
        )

        # Postings rejected when account IS dormant
        rejection_id = endtoend.postings_helper.inbound_hard_settlement(
            amount="50.00",
            denomination=DEFAULT_DENOMINATION,
            instruction_details={"description": "Deposit attempt when dormant"},
            account_id=customer_account.id,
            internal_account_id=accounts.INTERNAL_ACCOUNT,
            value_datetime=opening_date + relativedelta(hours=3),
        )
        pib = endtoend.postings_helper.get_posting_batch(rejection_id)
        self.assertEqual(pib["status"], "POSTING_INSTRUCTION_BATCH_STATUS_REJECTED")

        # Remove dormant flag and clear balance for teardown
        # We "remove" by setting value to OFF
        endtoend.contracts_helper.create_flag(
            flag_definition_id="ACCOUNT_DORMANT",
            account_id=customer_account.id,
            effective_timestamp=opening_date + relativedelta(hours=4),
            is_backdated=True,
            value=FlagV1FlagValue.FLAG_VALUE_OFF,
        )

        endtoend.postings_helper.outbound_hard_settlement(
            amount="100.00",
            denomination=DEFAULT_DENOMINATION,
            instruction_details={"description": "Clear balance"},
            account_id=customer_account.id,
            internal_account_id=accounts.INTERNAL_ACCOUNT,
            value_datetime=opening_date + relativedelta(hours=5),
        )
        endtoend.balances_helper.wait_for_account_balances(
            account_id=customer_account.id,
            expected_balances=[
                (dimensions.BalanceDimensions(denomination=DEFAULT_DENOMINATION), "0"),
            ],
        )
