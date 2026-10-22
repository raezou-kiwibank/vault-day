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
from inception_sdk.test_framework.common.test.input import expected_parameters_contract
from inception_sdk.test_framework.common.test.input.expected_parameters_contract import (  # noqa: E501
    POST_POSTING_NOTIFICATION as EXPECTED_PARAMS_POST_POSTING_NOTIFICATION,
)
from inception_sdk.test_framework.contracts.files import EMPTY_LIABILITY_CONTRACT_V4
from inception_sdk.test_framework.endtoend.contracts_helper import ContractNotificationResourceType
from inception_sdk.test_framework.endtoend.test.e2e.input.template.parameter_resources_contract import (  # noqa: E501
    ACCOUNT_ID_PARAM,
    DATETIME_PARAM,
    DECIMAL_PARAM,
    ENUMERATION_PARAM,
    POST_POSTING_NOTIFICATION as LEGACY_PARAMS_POST_POSTING_NOTIFICATION,
    STRING_PARAM,
)
from inception_sdk.vault.core_api import (
    AccountConstraint,
    AccountConstraintValue,
    AccountIdParameterValue,
    AccountV2Status,
    AccountV2TSide,
    BatchCreateParameterValueV1RequestBody,
    CreateAccountV2Response,
    CreateOptions,
    CreateParameterValueV1ParameterValue,
    CustomerAccountRequestBody,
    DatetimeConstraint,
    DatetimeConstraintPrecision,
    DatetimeConstraintValue,
    DatetimeParameterValue,
    DecimalConstraint,
    DecimalConstraintValue,
    DecimalParameterValue,
    EnumerationConstraint,
    EnumerationConstraintValue,
    EnumerationParameterValue,
    ParameterResource,
    StringConstraint,
    StringConstraintValue,
    StringParameterValue,
)

UTC = ZoneInfo("UTC")

log = logging.getLogger(__name__)
logging.basicConfig(
    level=os.environ.get("LOGLEVEL", "INFO"),
    format="%(asctime)s.%(msecs)03d - %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
EXPECTED_PARAMETERS_CONTRACT = "expected_parameters_contract"
PARAMETER_RESOURCES_CONTRACT = "parameter_resources_contract"
EMPTY_CONTRACT = "empty_contract"
endtoend.testhandle.CONTRACTS = {
    EXPECTED_PARAMETERS_CONTRACT: {
        "path": "inception_sdk/test_framework/common/test/input/expected_parameters_contract.py",
        "template_params": {},
    },
    PARAMETER_RESOURCES_CONTRACT: {
        "path": "inception_sdk/test_framework/endtoend/test/e2e/input/template/"
        "parameter_resources_contract.py",
        "template_params": {},
    },
    EMPTY_CONTRACT: {
        "path": EMPTY_LIABILITY_CONTRACT_V4,
        "template_params": {},
    },
}
TEST_INTERNAL_ACCOUNT = "TEST_INTERNAL_ACCOUNT"
endtoend.testhandle.TSIDE_TO_INTERNAL_ACCOUNT_ID = {
    AccountV2TSide.T_SIDE_LIABILITY: [TEST_INTERNAL_ACCOUNT]
}
endtoend.testhandle.PARAMETER_RESOURCE_DIRS = [
    "inception_sdk/test_framework/common/test/input/parameters"
]


class TestParameterResourcesV1(endtoend.End2Endtest):
    """
    Test creating parameters, parameter values
    """

    @classmethod
    def setUpClass(cls):
        cls.start_date = str(datetime.now().date())
        super().setUpClass()

    def _create_random_blank_account(self, customer) -> CreateAccountV2Response:
        return endtoend.contracts_helper.create_account_v2(
            product_id=EMPTY_CONTRACT,
            account=CustomerAccountRequestBody(
                id=(str(uuid.uuid4())),
                status=AccountV2Status.ACCOUNT_STATUS_OPEN,
                stakeholder_ids=[customer],
            ),
        )

    def test_account_owned_parameter_values_with_legacy_parameters(self):
        """
        Create an account with account owned parameters values but legacy contract parameters.Prove
        that the parameters have these values by emitting them as a notification from the
        post-posting hook. Change the parameter values and prove that the update has completed by
        re-emitting them as another notification from the post-posting hook.
        """
        customer = endtoend.core_api_helper.create_customer()
        blank_account_1 = self._create_random_blank_account(customer)
        blank_account_2 = self._create_random_blank_account(customer)
        parameter_values = {
            STRING_PARAM.name: StringParameterValue(string_value="original_value"),
            DECIMAL_PARAM.name: DecimalParameterValue(decimal_value=Decimal("3.14")),
            ENUMERATION_PARAM.name: EnumerationParameterValue(enumeration_value="gold"),
            DATETIME_PARAM.name: DatetimeParameterValue(
                date_time_value=datetime(2024, 12, 31, tzinfo=UTC)
            ),
            ACCOUNT_ID_PARAM.name: AccountIdParameterValue(account_id_value=blank_account_1.id),
        }
        customer_account_v2 = endtoend.contracts_helper.create_account_v2(
            product_id=PARAMETER_RESOURCES_CONTRACT,
            account=CustomerAccountRequestBody(
                id=str(uuid.uuid4()),
                status=AccountV2Status.ACCOUNT_STATUS_OPEN,
                stakeholder_ids=[customer],
            ),
            create_options=CreateOptions(parameter_values=parameter_values),
        )
        pib_id = endtoend.postings_helper.inbound_hard_settlement(
            amount=Decimal(1),
            account_id=customer_account_v2.id,
            internal_account_id="DUMMY_CONTRA",
        )
        pib = endtoend.postings_helper.get_posting_batch(pib_id=pib_id)
        self.assertEqual(pib["status"], "POSTING_INSTRUCTION_BATCH_STATUS_ACCEPTED")

        endtoend.contracts_helper.wait_for_contract_notification(
            notification_type=LEGACY_PARAMS_POST_POSTING_NOTIFICATION,
            # Vault sorts the resulting notification details after they have been returned from
            # the smart contract, beyond the control of the smart contract author.
            notification_details={k: str(v) for k, v in sorted(parameter_values.items())},
            resource_id=customer_account_v2.id,
            resource_type=ContractNotificationResourceType.RESOURCE_ACCOUNT,
        )
        new_parameter_values = [
            CreateParameterValueV1ParameterValue(
                parameter_id=STRING_PARAM.name,
                value=StringParameterValue(string_value="new_value"),
                account_id=customer_account_v2.id,
            ),
            CreateParameterValueV1ParameterValue(
                parameter_id=DECIMAL_PARAM.name,
                value=DecimalParameterValue(decimal_value=Decimal("2.72")),
                account_id=customer_account_v2.id,
            ),
            CreateParameterValueV1ParameterValue(
                parameter_id=ENUMERATION_PARAM.name,
                value=EnumerationParameterValue(enumeration_value="green"),
                account_id=customer_account_v2.id,
            ),
            CreateParameterValueV1ParameterValue(
                parameter_id=DATETIME_PARAM.name,
                value=DatetimeParameterValue(date_time_value=datetime(2025, 1, 26, tzinfo=UTC)),
                account_id=customer_account_v2.id,
            ),
            CreateParameterValueV1ParameterValue(
                parameter_id=ACCOUNT_ID_PARAM.name,
                value=AccountIdParameterValue(account_id_value=blank_account_2.id),
                account_id=customer_account_v2.id,
            ),
        ]
        endtoend.core_api_helper.batch_create_parameter_values(
            BatchCreateParameterValueV1RequestBody(
                request_id=str(uuid.uuid4()),
                parameter_values=new_parameter_values,
            )
        )
        pib_id = endtoend.postings_helper.inbound_hard_settlement(
            amount=Decimal(1),
            account_id=customer_account_v2.id,
            internal_account_id="DUMMY_CONTRA",
        )
        pib = endtoend.postings_helper.get_posting_batch(pib_id=pib_id)
        self.assertEqual(pib["status"], "POSTING_INSTRUCTION_BATCH_STATUS_ACCEPTED")

        endtoend.contracts_helper.wait_for_contract_notification(
            notification_type=LEGACY_PARAMS_POST_POSTING_NOTIFICATION,
            # Vault sorts the resulting notification details after they have been returned from
            # the smart contract, beyond the control of the smart contract author.
            notification_details={
                p.parameter_id: str(p.value)
                for p in sorted(new_parameter_values, key=lambda p: p.parameter_id)
            },
            resource_id=customer_account_v2.id,
            resource_type=ContractNotificationResourceType.RESOURCE_ACCOUNT,
        )

    def test_parameter_resource_extracted_uploaded_and_mapped(self):
        id_map = endtoend.testhandle.parameter_resource_id_to_uploaded_id
        expected_parameters = {
            "SOME_ACCOUNT_PARAMETER_RESOURCE": ParameterResource(
                id=id_map["SOME_ACCOUNT_PARAMETER_RESOURCE"],
                constraint=AccountConstraint(account_constraint=AccountConstraintValue()),
                metadata={"description": "account parameter"},
            ),
            "SOME_DATETIME_PARAMETER_RESOURCE": ParameterResource(
                id=id_map["SOME_DATETIME_PARAMETER_RESOURCE"],
                constraint=DatetimeConstraint(
                    date_time_constraint=DatetimeConstraintValue(
                        precision=DatetimeConstraintPrecision.MINUTE,
                        earliest=datetime(2020, 1, 1, tzinfo=UTC),
                        latest=datetime(2040, 1, 1, tzinfo=UTC),
                    )
                ),
                metadata={"description": "datetime parameter"},
            ),
            "SOME_DECIMAL_PARAMETER_RESOURCE": ParameterResource(
                id=id_map["SOME_DECIMAL_PARAMETER_RESOURCE"],
                constraint=DecimalConstraint(
                    decimal_constraint=DecimalConstraintValue(
                        min_value=Decimal(0),
                        max_value=Decimal(100),
                    )
                ),
                metadata={"description": "decimal parameter"},
            ),
            "SOME_ENUMERATION_PARAMETER_RESOURCE": ParameterResource(
                id=id_map["SOME_ENUMERATION_PARAMETER_RESOURCE"],
                constraint=EnumerationConstraint(
                    enumeration_constraint=EnumerationConstraintValue(
                        permitted_values=["green", "gold", "red"]
                    )
                ),
                metadata={"description": "enumeration parameter"},
            ),
            "SOME_STRING_PARAMETER_RESOURCE": ParameterResource(
                id=id_map["SOME_STRING_PARAMETER_RESOURCE"],
                constraint=StringConstraint(
                    string_constraint=StringConstraintValue(min_length=1, max_length=100)
                ),
                metadata={"description": "string parameter"},
            ),
        }

        expected_parameter_mapping = {
            original_id: resource.id for original_id, resource in expected_parameters.items()
        }

        self.assertEqual(
            expected_parameter_mapping,
            endtoend.testhandle.parameter_resource_id_to_uploaded_id,
        )

        created_parameters = endtoend.contracts_helper.batch_get_parameter_resources(
            ids=expected_parameters.keys()
        ).parameters
        self.assertDictEqual(created_parameters, expected_parameters)

    def test_account_owned_parameter_values(self):
        """
        Create an account with expected parameters each having an initial value.  Prove that the
        parameters have these values by emitting them as a notification from the post-posting hook.
        Change the parameter values and prove that the update has completed by re-emitting them as
        another notification from the post-posting hook.
        """
        id_map = endtoend.testhandle.parameter_resource_id_to_uploaded_id

        customer = endtoend.core_api_helper.create_customer()
        account_1 = self._create_random_blank_account(customer)
        account_2 = self._create_random_blank_account(customer)

        parameter_values = {
            "SOME_STRING_PARAMETER_RESOURCE": StringParameterValue(string_value="original_value"),
            "SOME_DECIMAL_PARAMETER_RESOURCE": DecimalParameterValue(decimal_value=Decimal("3.14")),
            "SOME_ENUMERATION_PARAMETER_RESOURCE": EnumerationParameterValue(
                enumeration_value="gold"
            ),
            "SOME_DATETIME_PARAMETER_RESOURCE": DatetimeParameterValue(
                date_time_value=datetime(2024, 12, 31, tzinfo=UTC)
            ),
            "SOME_ACCOUNT_PARAMETER_RESOURCE": AccountIdParameterValue(
                account_id_value=account_1.id
            ),
        }
        customer_account_v2 = endtoend.contracts_helper.create_account_v2(
            product_id=EXPECTED_PARAMETERS_CONTRACT,
            account=CustomerAccountRequestBody(
                id=str(uuid.uuid4()),
                status=AccountV2Status.ACCOUNT_STATUS_OPEN,
                stakeholder_ids=[customer],
            ),
            create_options=CreateOptions(parameter_values=parameter_values),
        )
        pib_id = endtoend.postings_helper.inbound_hard_settlement(
            amount=Decimal(1),
            account_id=customer_account_v2.id,
            internal_account_id="DUMMY_CONTRA",
        )
        pib = endtoend.postings_helper.get_posting_batch(pib_id=pib_id)
        self.assertEqual(pib["status"], "POSTING_INSTRUCTION_BATCH_STATUS_ACCEPTED")

        endtoend.contracts_helper.wait_for_contract_notification(
            notification_type=EXPECTED_PARAMS_POST_POSTING_NOTIFICATION,
            # Vault sorts the resulting notification details after they have been returned from
            # the smart contract, beyond the control of the smart contract author.
            notification_details=dict(
                sorted({id_map.get(k, k): str(v) for k, v in parameter_values.items()}.items())
            ),
            resource_id=customer_account_v2.id,
            resource_type=ContractNotificationResourceType.RESOURCE_ACCOUNT,
        )

        new_parameter_values = [
            CreateParameterValueV1ParameterValue(
                parameter_id="SOME_STRING_PARAMETER_RESOURCE",
                value=StringParameterValue(string_value="new_value"),
                account_id=customer_account_v2.id,
            ),
            CreateParameterValueV1ParameterValue(
                parameter_id="SOME_DECIMAL_PARAMETER_RESOURCE",
                value=DecimalParameterValue(decimal_value=Decimal("2.72")),
                account_id=customer_account_v2.id,
            ),
            CreateParameterValueV1ParameterValue(
                parameter_id="SOME_ENUMERATION_PARAMETER_RESOURCE",
                value=EnumerationParameterValue(enumeration_value="green"),
                account_id=customer_account_v2.id,
            ),
            CreateParameterValueV1ParameterValue(
                parameter_id="SOME_DATETIME_PARAMETER_RESOURCE",
                value=DatetimeParameterValue(date_time_value=datetime(2025, 1, 26, tzinfo=UTC)),
                account_id=customer_account_v2.id,
            ),
            CreateParameterValueV1ParameterValue(
                parameter_id="SOME_ACCOUNT_PARAMETER_RESOURCE",
                value=AccountIdParameterValue(account_id_value=account_2.id),
                account_id=customer_account_v2.id,
            ),
        ]
        endtoend.contracts_helper.batch_create_parameter_values(
            BatchCreateParameterValueV1RequestBody(
                request_id=str(uuid.uuid4()),
                parameter_values=new_parameter_values,
            )
        )
        pib_id = endtoend.postings_helper.inbound_hard_settlement(
            amount=Decimal(1),
            account_id=customer_account_v2.id,
            internal_account_id="DUMMY_CONTRA",
        )
        pib = endtoend.postings_helper.get_posting_batch(pib_id=pib_id)
        self.assertEqual(pib["status"], "POSTING_INSTRUCTION_BATCH_STATUS_ACCEPTED")

        endtoend.contracts_helper.wait_for_contract_notification(
            notification_type=EXPECTED_PARAMS_POST_POSTING_NOTIFICATION,
            # Vault sorts the resulting notification details after they have been returned from
            # the smart contract, beyond the control of the smart contract author.
            notification_details=dict(
                sorted(
                    {
                        id_map.get(p.parameter_id, p.parameter_id): str(p.value)
                        for p in new_parameter_values
                    }.items()
                )
            ),
            resource_id=customer_account_v2.id,
            resource_type=ContractNotificationResourceType.RESOURCE_ACCOUNT,
        )

    def test_account_owned_parameter_values_clu_syntax(self):
        """
        Create an account with expected parameters each having an initial value.  Prove that the
        parameters have these values by emitting them as a notification from the post-posting hook.
        Change the parameter values and prove that the update has completed by re-emitting them as
        another notification from the post-posting hook.

        This test is to mimic when a contract writer references the
        CLU notation ID directly from the contract.
        """
        id_map = endtoend.testhandle.parameter_resource_id_to_uploaded_id

        customer = endtoend.core_api_helper.create_customer()
        account_1 = self._create_random_blank_account(customer)
        account_2 = self._create_random_blank_account(customer)

        clu_mapping = {
            expected_parameters_contract.STRING_EXPECTED_PARAM.id: (
                "SOME_STRING_PARAMETER_RESOURCE"
            ),
            expected_parameters_contract.DECIMAL_EXPECTED_PARAM.id: (
                "SOME_DECIMAL_PARAMETER_RESOURCE"
            ),
            expected_parameters_contract.ENUMERATION_EXPECTED_PARAM.id: (
                "SOME_ENUMERATION_PARAMETER_RESOURCE"
            ),
            expected_parameters_contract.DATETIME_EXPECTED_PARAM.id: (
                "SOME_DATETIME_PARAMETER_RESOURCE"
            ),
            expected_parameters_contract.ACCOUNT_ID_EXPECTED_PARAM.id: (
                "SOME_ACCOUNT_PARAMETER_RESOURCE"
            ),
        }

        # these IDs use the CLU syntax, so should be stripped in the create_account_v2 call
        parameter_values = {
            expected_parameters_contract.STRING_EXPECTED_PARAM.id: StringParameterValue(
                string_value="original_value"
            ),
            expected_parameters_contract.DECIMAL_EXPECTED_PARAM.id: DecimalParameterValue(
                decimal_value=Decimal("3.14")
            ),
            expected_parameters_contract.ENUMERATION_EXPECTED_PARAM.id: EnumerationParameterValue(
                enumeration_value="gold"
            ),
            expected_parameters_contract.DATETIME_EXPECTED_PARAM.id: DatetimeParameterValue(
                date_time_value=datetime(2024, 12, 31, tzinfo=UTC)
            ),
            expected_parameters_contract.ACCOUNT_ID_EXPECTED_PARAM.id: AccountIdParameterValue(
                account_id_value=account_1.id
            ),
        }
        customer_account_v2 = endtoend.contracts_helper.create_account_v2(
            product_id=EXPECTED_PARAMETERS_CONTRACT,
            account=CustomerAccountRequestBody(
                id=str(uuid.uuid4()),
                status=AccountV2Status.ACCOUNT_STATUS_OPEN,
                stakeholder_ids=[customer],
            ),
            create_options=CreateOptions(parameter_values=parameter_values),
        )
        pib_id = endtoend.postings_helper.inbound_hard_settlement(
            amount=Decimal(1),
            account_id=customer_account_v2.id,
            internal_account_id="DUMMY_CONTRA",
        )
        pib = endtoend.postings_helper.get_posting_batch(pib_id=pib_id)
        self.assertEqual(pib["status"], "POSTING_INSTRUCTION_BATCH_STATUS_ACCEPTED")

        endtoend.contracts_helper.wait_for_contract_notification(
            notification_type=EXPECTED_PARAMS_POST_POSTING_NOTIFICATION,
            # Vault sorts the resulting notification details after they have been returned from
            # the smart contract, beyond the control of the smart contract author.
            notification_details=dict(
                sorted(
                    {
                        id_map.get(clu_mapping[k], clu_mapping[k]): str(v)
                        for k, v in parameter_values.items()
                    }.items()
                )
            ),
            resource_id=customer_account_v2.id,
            resource_type=ContractNotificationResourceType.RESOURCE_ACCOUNT,
        )

        new_parameter_values = [
            CreateParameterValueV1ParameterValue(
                parameter_id=expected_parameters_contract.STRING_EXPECTED_PARAM.id,
                value=StringParameterValue(string_value="new_value"),
                account_id=customer_account_v2.id,
            ),
            CreateParameterValueV1ParameterValue(
                parameter_id=expected_parameters_contract.DECIMAL_EXPECTED_PARAM.id,
                value=DecimalParameterValue(decimal_value=Decimal("2.72")),
                account_id=customer_account_v2.id,
            ),
            CreateParameterValueV1ParameterValue(
                parameter_id=expected_parameters_contract.ENUMERATION_EXPECTED_PARAM.id,
                value=EnumerationParameterValue(enumeration_value="green"),
                account_id=customer_account_v2.id,
            ),
            CreateParameterValueV1ParameterValue(
                parameter_id=expected_parameters_contract.DATETIME_EXPECTED_PARAM.id,
                value=DatetimeParameterValue(date_time_value=datetime(2025, 1, 26, tzinfo=UTC)),
                account_id=customer_account_v2.id,
            ),
            CreateParameterValueV1ParameterValue(
                parameter_id=expected_parameters_contract.ACCOUNT_ID_EXPECTED_PARAM.id,
                value=AccountIdParameterValue(account_id_value=account_2.id),
                account_id=customer_account_v2.id,
            ),
        ]
        endtoend.contracts_helper.batch_create_parameter_values(
            BatchCreateParameterValueV1RequestBody(
                request_id=str(uuid.uuid4()),
                parameter_values=new_parameter_values,
            )
        )
        pib_id = endtoend.postings_helper.inbound_hard_settlement(
            amount=Decimal(1),
            account_id=customer_account_v2.id,
            internal_account_id="DUMMY_CONTRA",
        )
        pib = endtoend.postings_helper.get_posting_batch(pib_id=pib_id)
        self.assertEqual(pib["status"], "POSTING_INSTRUCTION_BATCH_STATUS_ACCEPTED")

        endtoend.contracts_helper.wait_for_contract_notification(
            notification_type=EXPECTED_PARAMS_POST_POSTING_NOTIFICATION,
            # Vault sorts the resulting notification details after they have been returned from
            # the smart contract, beyond the control of the smart contract author.
            notification_details=dict(
                sorted(
                    {
                        id_map.get(clu_mapping[p.parameter_id], clu_mapping[p.parameter_id]): str(
                            p.value
                        )
                        for p in new_parameter_values
                    }.items()
                )
            ),
            resource_id=customer_account_v2.id,
            resource_type=ContractNotificationResourceType.RESOURCE_ACCOUNT,
        )

    def test_account_owned_parameter_values_with_internal_account_mapping(self):
        """
        Create an account with account owned parameters values.  Prove that the
        parameters have these values by emitting them as a notification from the post-posting hook.
        Change the parameter values and prove that the update has completed by re-emitting them as
        another notification from the post-posting hook.
        """
        customer = endtoend.core_api_helper.create_customer()
        parameter_values = {
            STRING_PARAM.name: StringParameterValue(string_value="original_value"),
            DECIMAL_PARAM.name: DecimalParameterValue(decimal_value=Decimal("3.14")),
            ENUMERATION_PARAM.name: EnumerationParameterValue(enumeration_value="gold"),
            DATETIME_PARAM.name: DatetimeParameterValue(
                date_time_value=datetime(2024, 12, 31, tzinfo=UTC)
            ),
            # We use the unmapped id here to check that create_account_v2 does mapping for us
            ACCOUNT_ID_PARAM.name: AccountIdParameterValue(account_id_value=TEST_INTERNAL_ACCOUNT),
        }
        expected_parameter_values = parameter_values | {
            # We use the mapped id here since create_account_v2 should have done the mapping for us
            ACCOUNT_ID_PARAM.name: AccountIdParameterValue(
                account_id_value=endtoend.testhandle.internal_account_id_to_uploaded_id[
                    TEST_INTERNAL_ACCOUNT
                ]
            ),
        }
        customer_account_v2 = endtoend.contracts_helper.create_account_v2(
            product_id=PARAMETER_RESOURCES_CONTRACT,
            account=CustomerAccountRequestBody(
                id=str(uuid.uuid4()),
                status=AccountV2Status.ACCOUNT_STATUS_OPEN,
                stakeholder_ids=[customer],
            ),
            create_options=CreateOptions(parameter_values=parameter_values),
        )
        pib_id = endtoend.postings_helper.inbound_hard_settlement(
            amount=Decimal(1),
            account_id=customer_account_v2.id,
            internal_account_id="DUMMY_CONTRA",
        )
        pib = endtoend.postings_helper.get_posting_batch(pib_id=pib_id)
        self.assertEqual(pib["status"], "POSTING_INSTRUCTION_BATCH_STATUS_ACCEPTED")

        endtoend.contracts_helper.wait_for_contract_notification(
            notification_type=EXPECTED_PARAMS_POST_POSTING_NOTIFICATION,
            # Vault sorts the resulting notification details after they have been returned from
            # the smart contract, beyond the control of the smart contract author.
            notification_details={k: str(v) for k, v in sorted(expected_parameter_values.items())},
            resource_id=customer_account_v2.id,
            resource_type=ContractNotificationResourceType.RESOURCE_ACCOUNT,
        )

    # TODO(INC-10429): Adding Test Scenario for Update Parameter Value
    # effective_to_timestamp for Vault Version 5.0 and above
    @endtoend.skipForVaultVersionLessThan(Version("5.1.0"))
    def test_update_parameter_value_v1_is_cancelled(self):
        """
        The test scenario is as below:
        parameter value A for parameter 1 created from Date 1
        parameter value B for parameter 1 created from Date 2 in the future
        cancel parameter value B
        """
        customer = endtoend.core_api_helper.create_customer()
        blank_account_1 = self._create_random_blank_account(customer)
        parameter_values = {
            "SOME_STRING_PARAMETER_RESOURCE": StringParameterValue(string_value="original_value"),
            "SOME_DECIMAL_PARAMETER_RESOURCE": DecimalParameterValue(decimal_value=Decimal("3.14")),
            "SOME_ENUMERATION_PARAMETER_RESOURCE": EnumerationParameterValue(
                enumeration_value="gold"
            ),
            "SOME_DATETIME_PARAMETER_RESOURCE": DatetimeParameterValue(
                date_time_value=datetime(2024, 12, 31, tzinfo=UTC)
            ),
            "SOME_ACCOUNT_PARAMETER_RESOURCE": AccountIdParameterValue(
                account_id_value=blank_account_1.id
            ),
        }
        customer_account_v2 = endtoend.contracts_helper.create_account_v2(
            product_id=EXPECTED_PARAMETERS_CONTRACT,
            account=CustomerAccountRequestBody(
                status=AccountV2Status.ACCOUNT_STATUS_OPEN,
                stakeholder_ids=[customer],
            ),
            create_options=CreateOptions(parameter_values=parameter_values),
        )

        new_parameter_values = [
            CreateParameterValueV1ParameterValue(
                parameter_id="SOME_STRING_PARAMETER_RESOURCE",
                value=StringParameterValue(string_value="new_value"),
                account_id=customer_account_v2.id,
                effective_from_timestamp=datetime(2040, 12, 31, tzinfo=UTC),
            ),
        ]
        parameter_values = endtoend.contracts_helper.batch_create_parameter_values(
            BatchCreateParameterValueV1RequestBody(
                request_id=str(uuid.uuid4()),
                parameter_values=new_parameter_values,
            )
        )

        # parameter_values is expected to be a list, as this scenario only updating 1
        # parameter_value hence it was the only value return. For multiple parameter
        # values update, test writer to determine which exact parameter value id to
        # update, because it may have multiple values.
        parameter_value_id = parameter_values["parameter_values"][0]["id"]

        parameter_value_update_respond = endtoend.core_api_helper.update_parameter_value(
            parameter_value_id=parameter_value_id,
            is_cancelled=True,
            skip_pre_parameter_change_hook=True,
        )

        self.assertEqual(
            True,
            parameter_value_update_respond.is_cancelled,
        )

    def test_get_parameter_values(self):
        id_map = endtoend.testhandle.parameter_resource_id_to_uploaded_id

        customer = endtoend.core_api_helper.create_customer()
        dummy_account = self._create_random_blank_account(customer)

        parameter_values = {
            "SOME_STRING_PARAMETER_RESOURCE": StringParameterValue(string_value="string_value"),
            "SOME_DECIMAL_PARAMETER_RESOURCE": DecimalParameterValue(decimal_value=Decimal("50")),
            "SOME_ENUMERATION_PARAMETER_RESOURCE": EnumerationParameterValue(
                enumeration_value="green"
            ),
            "SOME_DATETIME_PARAMETER_RESOURCE": DatetimeParameterValue(
                date_time_value=datetime(2023, 12, 31, tzinfo=UTC)
            ),
            "SOME_ACCOUNT_PARAMETER_RESOURCE": AccountIdParameterValue(
                account_id_value=dummy_account.id
            ),
        }
        account = endtoend.contracts_helper.create_account_v2(
            product_id=EXPECTED_PARAMETERS_CONTRACT,
            account=CustomerAccountRequestBody(
                id=str(uuid.uuid4()),
                status=AccountV2Status.ACCOUNT_STATUS_OPEN,
                stakeholder_ids=[customer],
            ),
            create_options=CreateOptions(parameter_values=parameter_values),
        )

        parameter_ids = list(parameter_values.keys())

        result = endtoend.contracts_helper.get_parameter_values(
            parameter_ids=parameter_ids, account_ids=[account.id]
        )
        # assert that all parameter values were fetched for the given account
        expected_parameter_ids = {id_map[id] for id in parameter_ids}
        fetched_parameter_ids = {p.parameter_id for p in result}
        self.assertSetEqual(fetched_parameter_ids, expected_parameter_ids)

    def test_get_parameter_values_clu_syntax(self):
        id_map = endtoend.testhandle.parameter_resource_id_to_uploaded_id

        customer = endtoend.core_api_helper.create_customer()
        dummy_account = self._create_random_blank_account(customer)

        # these IDs use the CLU syntax, so should be stripped in the create_account_v2 call
        parameter_values = {
            expected_parameters_contract.STRING_EXPECTED_PARAM.id: StringParameterValue(
                string_value="string_value"
            ),
            expected_parameters_contract.DECIMAL_EXPECTED_PARAM.id: DecimalParameterValue(
                decimal_value=Decimal("50")
            ),
            expected_parameters_contract.ENUMERATION_EXPECTED_PARAM.id: EnumerationParameterValue(
                enumeration_value="green"
            ),
            expected_parameters_contract.DATETIME_EXPECTED_PARAM.id: DatetimeParameterValue(
                date_time_value=datetime(2023, 12, 31, tzinfo=UTC)
            ),
            expected_parameters_contract.ACCOUNT_ID_EXPECTED_PARAM.id: AccountIdParameterValue(
                account_id_value=dummy_account.id
            ),
        }
        account = endtoend.contracts_helper.create_account_v2(
            product_id=EXPECTED_PARAMETERS_CONTRACT,
            account=CustomerAccountRequestBody(
                id=str(uuid.uuid4()),
                status=AccountV2Status.ACCOUNT_STATUS_OPEN,
                stakeholder_ids=[customer],
            ),
            create_options=CreateOptions(parameter_values=parameter_values),
        )

        parameter_ids = list(parameter_values.keys())
        result = endtoend.contracts_helper.get_parameter_values(
            parameter_ids=parameter_ids, account_ids=[account.id]
        )
        # assert that all parameter values were fetched for the given account
        expected_parameter_ids = {
            id_map[id]
            for id in [
                "SOME_ACCOUNT_PARAMETER_RESOURCE",
                "SOME_DATETIME_PARAMETER_RESOURCE",
                "SOME_DECIMAL_PARAMETER_RESOURCE",
                "SOME_ENUMERATION_PARAMETER_RESOURCE",
                "SOME_STRING_PARAMETER_RESOURCE",
            ]
        }
        fetched_parameter_ids = {p.parameter_id for p in result}
        self.assertSetEqual(fetched_parameter_ids, expected_parameter_ids)

    def test_create_parameter_value_hierarchy_owned_parameter_values(self):
        """
        Create an account with one of them owned by a Parameter Value Hierarch.  Prove that the
        parameters have these values by emitting them as a notification from the post-posting hook.
        """
        id_map = endtoend.testhandle.parameter_resource_id_to_uploaded_id

        customer = endtoend.core_api_helper.create_customer()
        account_1 = self._create_random_blank_account(customer)

        parameter_value_hierarchy_node_id = str(uuid.uuid4())
        endtoend.core_api_helper.create_parameter_value_hierarchy_node(
            request_id=str(uuid.uuid4()),
            parameter_value_hierarchy_node=endtoend.core_api_helper.CreateParameterValueHierarchyNode(  # noqa: E501
                id=parameter_value_hierarchy_node_id,
                name="PARAMETER_VALUE_HIERARCHY_" + str(uuid.uuid4()),
                parent_id="",
                metadata={},
            ),
        )

        pvh_owned_parameters = {
            "SOME_STRING_PARAMETER_RESOURCE": StringParameterValue(string_value="original_value")
        }
        endtoend.core_api_helper.batch_create_parameter_values(
            BatchCreateParameterValueV1RequestBody(
                request_id=str(uuid.uuid4()),
                parameter_values=[
                    CreateParameterValueV1ParameterValue(
                        parameter_id=endtoend.testhandle.parameter_resource_id_to_uploaded_id[
                            "SOME_STRING_PARAMETER_RESOURCE"
                        ],
                        parameter_value_hierarchy_node_id=parameter_value_hierarchy_node_id,
                        value=pvh_owned_parameters["SOME_STRING_PARAMETER_RESOURCE"],
                    )
                ],
            )
        )

        parameter_values = {
            "SOME_DECIMAL_PARAMETER_RESOURCE": DecimalParameterValue(decimal_value=Decimal("3.14")),
            "SOME_ENUMERATION_PARAMETER_RESOURCE": EnumerationParameterValue(
                enumeration_value="gold"
            ),
            "SOME_DATETIME_PARAMETER_RESOURCE": DatetimeParameterValue(
                date_time_value=datetime(2024, 12, 31, tzinfo=UTC)
            ),
            "SOME_ACCOUNT_PARAMETER_RESOURCE": AccountIdParameterValue(
                account_id_value=account_1.id
            ),
        }
        customer_account_v2 = endtoend.contracts_helper.create_account_v2(
            product_id=EXPECTED_PARAMETERS_CONTRACT,
            account=CustomerAccountRequestBody(
                id=str(uuid.uuid4()),
                status=AccountV2Status.ACCOUNT_STATUS_OPEN,
                stakeholder_ids=[customer],
                parameter_value_hierarchy_node_id=parameter_value_hierarchy_node_id,
            ),
            create_options=CreateOptions(parameter_values=parameter_values),
        )
        pib_id = endtoend.postings_helper.inbound_hard_settlement(
            amount=Decimal("1"),
            account_id=customer_account_v2.id,
            internal_account_id="DUMMY_CONTRA",
        )
        pib = endtoend.postings_helper.get_posting_batch(pib_id=pib_id)
        self.assertEqual(pib["status"], "POSTING_INSTRUCTION_BATCH_STATUS_ACCEPTED")

        expected_parameter_values = parameter_values | pvh_owned_parameters

        endtoend.contracts_helper.wait_for_contract_notification(
            notification_type=EXPECTED_PARAMS_POST_POSTING_NOTIFICATION,
            # Vault sorts the resulting notification details after they have been returned from
            # the smart contract, beyond the control of the smart contract author.
            notification_details=dict(
                sorted(
                    {id_map.get(k, k): str(v) for k, v in expected_parameter_values.items()}.items()
                )
            ),
            resource_id=customer_account_v2.id,
            resource_type=ContractNotificationResourceType.RESOURCE_ACCOUNT,
        )

    def test_update_account_to_use_new_parameter_value_hierarchy_owned_parameter_values(self):
        """
        Create an account with one of the parameter values owned by a Parameter Value Hierarchy.
        Prove that the parameters have these values by emitting them as a notification from the
        post-posting hook.
        Update the parameter value hierarchy and prove that the parameters have these values by
        emitting them as a notification from the post-posting hook.
        """
        id_map = endtoend.testhandle.parameter_resource_id_to_uploaded_id

        customer = endtoend.core_api_helper.create_customer()
        account_1 = self._create_random_blank_account(customer)

        parameter_value_hierarchy_node_a_id = str(uuid.uuid4())
        endtoend.core_api_helper.create_parameter_value_hierarchy_node(
            request_id=str(uuid.uuid4()),
            parameter_value_hierarchy_node=endtoend.core_api_helper.CreateParameterValueHierarchyNode(  # noqa: E501
                id=parameter_value_hierarchy_node_a_id,
                name="PARAMETER_VALUE_HIERARCHY_A_" + str(uuid.uuid4()),
                parent_id="",
                metadata={},
            ),
        )

        pvh_owned_parameters_a = {
            "SOME_STRING_PARAMETER_RESOURCE": StringParameterValue(string_value="original_value")
        }
        endtoend.core_api_helper.batch_create_parameter_values(
            BatchCreateParameterValueV1RequestBody(
                request_id=str(uuid.uuid4()),
                parameter_values=[
                    CreateParameterValueV1ParameterValue(
                        parameter_id=endtoend.testhandle.parameter_resource_id_to_uploaded_id[
                            "SOME_STRING_PARAMETER_RESOURCE"
                        ],
                        parameter_value_hierarchy_node_id=parameter_value_hierarchy_node_a_id,
                        value=pvh_owned_parameters_a["SOME_STRING_PARAMETER_RESOURCE"],
                    )
                ],
            )
        )

        parameter_value_hierarchy_node_b_id = str(uuid.uuid4())
        endtoend.core_api_helper.create_parameter_value_hierarchy_node(
            request_id=str(uuid.uuid4()),
            parameter_value_hierarchy_node=endtoend.core_api_helper.CreateParameterValueHierarchyNode(  # noqa: E501
                id=parameter_value_hierarchy_node_b_id,
                name="PARAMETER_VALUE_HIERARCHY_B_" + str(uuid.uuid4()),
                parent_id="",
                metadata={},
            ),
        )

        pvh_owned_parameters_b = {
            "SOME_STRING_PARAMETER_RESOURCE": StringParameterValue(string_value="new_value")
        }
        endtoend.core_api_helper.batch_create_parameter_values(
            BatchCreateParameterValueV1RequestBody(
                request_id=str(uuid.uuid4()),
                parameter_values=[
                    CreateParameterValueV1ParameterValue(
                        parameter_id=endtoend.testhandle.parameter_resource_id_to_uploaded_id[
                            "SOME_STRING_PARAMETER_RESOURCE"
                        ],
                        parameter_value_hierarchy_node_id=parameter_value_hierarchy_node_b_id,
                        value=pvh_owned_parameters_b["SOME_STRING_PARAMETER_RESOURCE"],
                    )
                ],
            )
        )

        parameter_values = {
            "SOME_DECIMAL_PARAMETER_RESOURCE": DecimalParameterValue(decimal_value=Decimal("3.14")),
            "SOME_ENUMERATION_PARAMETER_RESOURCE": EnumerationParameterValue(
                enumeration_value="gold"
            ),
            "SOME_DATETIME_PARAMETER_RESOURCE": DatetimeParameterValue(
                date_time_value=datetime(2024, 12, 31, tzinfo=UTC)
            ),
            "SOME_ACCOUNT_PARAMETER_RESOURCE": AccountIdParameterValue(
                account_id_value=account_1.id
            ),
        }
        customer_account_v2 = endtoend.contracts_helper.create_account_v2(
            product_id=EXPECTED_PARAMETERS_CONTRACT,
            account=CustomerAccountRequestBody(
                id=str(uuid.uuid4()),
                status=AccountV2Status.ACCOUNT_STATUS_OPEN,
                stakeholder_ids=[customer],
                parameter_value_hierarchy_node_id=parameter_value_hierarchy_node_a_id,
            ),
            create_options=CreateOptions(parameter_values=parameter_values),
        )
        pib_id = endtoend.postings_helper.inbound_hard_settlement(
            amount=Decimal("1"),
            account_id=customer_account_v2.id,
            internal_account_id="DUMMY_CONTRA",
        )
        pib = endtoend.postings_helper.get_posting_batch(pib_id=pib_id)
        self.assertEqual(pib["status"], "POSTING_INSTRUCTION_BATCH_STATUS_ACCEPTED")

        expected_parameter_values = parameter_values | pvh_owned_parameters_a

        endtoend.contracts_helper.wait_for_contract_notification(
            notification_type=EXPECTED_PARAMS_POST_POSTING_NOTIFICATION,
            # Vault sorts the resulting notification details after they have been returned from
            # the smart contract, beyond the control of the smart contract author.
            notification_details=dict(
                sorted(
                    {id_map.get(k, k): str(v) for k, v in expected_parameter_values.items()}.items()
                )
            ),
            resource_id=customer_account_v2.id,
            resource_type=ContractNotificationResourceType.RESOURCE_ACCOUNT,
        )

        endtoend.core_api_helper.update_account_v2(
            account_id=customer_account_v2.id,
            parameter_value_hierarchy_node_id=parameter_value_hierarchy_node_b_id,
        )
        pib_id = endtoend.postings_helper.inbound_hard_settlement(
            amount=Decimal("1"),
            account_id=customer_account_v2.id,
            internal_account_id="DUMMY_CONTRA",
        )
        pib = endtoend.postings_helper.get_posting_batch(pib_id=pib_id)
        self.assertEqual(pib["status"], "POSTING_INSTRUCTION_BATCH_STATUS_ACCEPTED")

        expected_parameter_values = parameter_values | pvh_owned_parameters_b

        endtoend.contracts_helper.wait_for_contract_notification(
            notification_type=EXPECTED_PARAMS_POST_POSTING_NOTIFICATION,
            # Vault sorts the resulting notification details after they have been returned from
            # the smart contract, beyond the control of the smart contract author.
            notification_details=dict(
                sorted(
                    {id_map.get(k, k): str(v) for k, v in expected_parameter_values.items()}.items()
                )
            ),
            resource_id=customer_account_v2.id,
            resource_type=ContractNotificationResourceType.RESOURCE_ACCOUNT,
        )
