# standard libs
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.case import TestCase
from unittest.mock import MagicMock, Mock, patch
from zoneinfo import ZoneInfo

# third party
from semantic_version import Version

# inception sdk
import inception_sdk.vault.core_api as core_api
from inception_sdk.test_framework import endtoend
from inception_sdk.test_framework.endtoend.core_api_helper import (
    get_vault_instance_information,
    list_all,
    update_account_schedule_tag,
)
from inception_sdk.test_framework.endtoend.schedule_helper import AccountScheduleTagStatusOverride
from inception_sdk.vault.core_api import (
    AccountIdParameterValue,
    AccountV2Status,
    AccountV2TSide,
    AccountV2Type,
    CreateAccountV2RequestBody,
    CreateAccountV2Response,
    CreateOptions,
    CreateSubAccountRequest,
    CustomerAccountRequestBody,
    DatetimeParameterValue,
    DecimalParameterValue,
    EnumerationParameterValue,
    FlagV1FlagValue,
    GetVaultVersionResponse,
    InternalAccountRequestBody,
    ListAccountAttributeValuesResponse,
    SemanticVersion,
    StringParameterValue,
    SubAccountCreateSubAccount,
    VaultCoreExtension,
)

UTC = ZoneInfo("UTC")


class CoreApiHelperTest(TestCase):
    @patch.object(endtoend.helper, "send_request")
    def test_get_vault_instance_information(self, mock_send_request: Mock):
        mock_send_request.return_value = {
            "version": {"major": 6, "minor": 3, "patch": 1, "label": "-rc3"},
            "pre_release": "pre_release_tag",
            "build": "build_tag",
            "extensions": [
                "VAULT_CORE_EXTENSION_MULTIPLE_PROCESSING_GROUPS",
                "VAULT_CORE_EXTENSION_HIGH_VOLUME_ACCOUNTS",
                "VAULT_CORE_EXTENSION_ATTRIBUTE_BASED_ACCESS_CONTROL",
                "VAULT_CORE_EXTENSION_SUB_ACCOUNTS",
            ],
        }
        vault_instance_information = get_vault_instance_information()
        self.assertEqual(
            GetVaultVersionResponse(
                version=SemanticVersion(major=6, minor=3, patch=1, label="-rc3"),
                pre_release="pre_release_tag",
                build="build_tag",
                extensions=[
                    VaultCoreExtension.MULTIPLE_PROCESSING_GROUPS,
                    VaultCoreExtension.HIGH_VOLUME_ACCOUNTS,
                    VaultCoreExtension.ATTRIBUTE_BASED_ACCESS_CONTROL,
                    VaultCoreExtension.SUB_ACCOUNTS,
                ],
            ),
            vault_instance_information,
        )

    @patch.object(endtoend.helper, "send_request")
    def test_get_vault_instance_information_no_extensions(self, mock_send_request: Mock):
        mock_send_request.return_value = {
            "version": {"major": 6, "minor": 3, "patch": 1, "label": "-rc3"},
            "pre_release": "pre_release_tag",
            "build": "build_tag",
        }
        vault_instance_information = get_vault_instance_information()
        self.assertEqual(
            GetVaultVersionResponse(
                version=SemanticVersion(major=6, minor=3, patch=1, label="-rc3"),
                pre_release="pre_release_tag",
                build="build_tag",
                extensions=[],
            ),
            vault_instance_information,
        )

    @patch.object(endtoend.helper, "send_request")
    def test_update_account_schedule_tag_expected_result_test_pause_at_timestamp(
        self,
        mock_send_request: Mock,
    ):
        tag_id = "ACCOUNT_SCHEDULE_TAG"
        test_pause_at_timestamp = datetime(2021, 1, 1, tzinfo=UTC).isoformat()
        new_tag_state = {"test_pause_at_timestamp": test_pause_at_timestamp}
        mock_send_request.return_value = new_tag_state
        updated_tag = update_account_schedule_tag(
            account_schedule_tag_id=tag_id,
            test_pause_at_timestamp=test_pause_at_timestamp,
        )
        self.assertEqual(updated_tag, new_tag_state)

    @patch.object(endtoend.helper, "send_request")
    def test_update_account_schedule_tag_status_override_to_skipped(
        self,
        mock_send_request: Mock,
    ):
        tag_id = "ACCOUNT_SCHEDULE_TAG"
        test_pause_at_timestamp = datetime(2021, 1, 1, tzinfo=UTC).isoformat()
        start_timestamp = datetime.min.isoformat()
        end_timestamp = datetime.max.isoformat()
        new_tag_state = {
            "test_pause_at_timestamp": test_pause_at_timestamp,
            "schedule_status_override": AccountScheduleTagStatusOverride.SKIPPED,
            "schedule_status_override_start_timestamp": datetime.min.isoformat(),
            "schedule_status_override_end_timestamp": datetime.max.isoformat(),
        }
        mock_send_request.return_value = new_tag_state
        updated_tag = update_account_schedule_tag(
            account_schedule_tag_id=tag_id,
            test_pause_at_timestamp=test_pause_at_timestamp,
            schedule_status_override_start_timestamp=start_timestamp,
            schedule_status_override_end_timestamp=end_timestamp,
            schedule_status_override=AccountScheduleTagStatusOverride.SKIPPED,
        )
        self.assertEqual(updated_tag, new_tag_state)

    def test_list_all_paginates_until_no_more_pages(self):
        @dataclass
        class MockRequest:
            page_token: str

        @dataclass
        class MockResult:
            next_page_token: str
            elements: list[int]

        def mock_api_call(req: MockRequest) -> MockResult:
            if req.page_token == "":
                # first page
                return MockResult(elements=[1], next_page_token="2")
            if req.page_token == "2":
                # second page
                return MockResult(elements=[2], next_page_token="3")
            if req.page_token == "3":
                # third page
                return MockResult(elements=[3], next_page_token="")
            raise Exception("unexpected call")

        result = list_all(
            list_api_call=mock_api_call,
            request=MockRequest(page_token=""),
            element_retriever=lambda r: r.elements,
        )
        self.assertEqual([1, 2, 3], result)


class CreateAccountV2Test(TestCase):
    def setUp(self):
        customer_account = CustomerAccountRequestBody(
            id="customer_account_id_1",
            smart_contract_version_id="smart_contract_version_id_1",
            stakeholder_ids=["stakeholder_1", "stakeholder_2"],
            alias="alias_2",
            status=AccountV2Status.ACCOUNT_STATUS_OPEN,
            permitted_denominations=["GBP", "USD", "SGD", "AUD", "NZD", "VND", "JPY"],
            details={
                "c": "3",
                "d": "4",
            },
            processing_group_id="p_2",
        )
        sub_accounts: [CreateSubAccountRequest] = [
            CreateSubAccountRequest(
                sub_account=SubAccountCreateSubAccount(
                    type="sub_account_type",
                    status=core_api.SubAccountStatus.SUB_ACCOUNT_STATUS_OPEN,
                )
            )
        ]
        self.create_options = CreateOptions(
            parameter_values={
                "string_param": StringParameterValue(string_value="s_1"),
                "decimal_param": DecimalParameterValue(decimal_value=Decimal(1)),
                "enumeration_param": EnumerationParameterValue(enumeration_value="e_1"),
                "datetime_param": DatetimeParameterValue(
                    date_time_value=datetime(2024, 12, 31, 23, 59, 0, 0, tzinfo=UTC)
                ),
                "account_id_param": AccountIdParameterValue(account_id_value="a_1"),
            },
            sub_accounts=sub_accounts,
        )
        self.customer_account_request = CreateAccountV2RequestBody(
            request_id="customer_account_request_id",
            account=customer_account,
            create_options=self.create_options,
        )
        self.internal_account = InternalAccountRequestBody(
            id="internal_account_id_1",
            alias="alias_1",
            status=AccountV2Status.ACCOUNT_STATUS_OPENING,
            details={
                "a": "1",
                "b": "2",
            },
            processing_group_id="p_1",
            t_side=AccountV2TSide.T_SIDE_ASSET,
        )
        self.internal_account_request = CreateAccountV2RequestBody(
            request_id="internal_account_request_id",
            account=self.internal_account,
        )

    @patch.object(endtoend.core_api_helper, "create_account_v2")
    def test_create_customer_account_v2(self, mock_create_account_v2: MagicMock):
        endtoend.core_api_helper.create_customer_account_v2(
            request_id=self.customer_account_request.request_id,
            account=self.customer_account_request.account,
            create_options=self.customer_account_request.create_options,
        )
        mock_create_account_v2.assert_called_once_with(self.customer_account_request)

    @patch.object(endtoend.core_api_helper, "create_account_v2")
    def test_create_internal_account_v2(self, mock_create_account_v2: MagicMock):
        endtoend.core_api_helper.create_internal_account_v2(
            request_id="internal_account_request_id",
            account=self.internal_account,
        )
        mock_create_account_v2.assert_called_once_with(self.internal_account_request)

    @patch.object(endtoend.helper, "send_request")
    def test_create_account_v2_for_customer(self, mock_send_request: MagicMock):
        mock_send_request.return_value = {
            "id": "customer_account_id_1",
            "type": "ACCOUNT_TYPE_CUSTOMER",
            "smart_contract_version_id": "smart_contract_version_id_1",
            "pending_smart_contract_version_id": "",
            "stakeholder_ids": ["stakeholder_1", "stakeholder_2"],
            "alias": "alias_2",
            "status": "ACCOUNT_STATUS_OPEN",
            "vault_create_timestamp": "2024-03-20T09:22:55.018784Z",
            "source_create_timestamp": "2024-03-20T09:22:55.018784Z",
            "source_open_timestamp": "2024-03-20T09:22:55.018784Z",
            "source_close_timestamp": None,
            "update_timestamp": None,
            "activation_timestamp": None,
            "permitted_denominations": ["GBP", "USD", "SGD", "AUD", "NZD", "VND", "JPY"],
            "details": {"c": "3", "d": "4"},
            "t_side": "T_SIDE_ASSET",
            "contract_update_timestamp": None,
            "processing_group_id": "p_2",
            "tranche_id": "",
            "parameter_value_hierarchy_node_id": "",
            "processing_label": "",
            "create_options_side_effects": {
                "sub_accounts": [
                    {
                        "id": "sub_account_id",
                        "type": "sub_account_type",
                        "name": None,
                        "details": None,
                        "activation_timestamp": "2024-03-20T09:22:55.018784Z",
                        "create_timestamp": "2024-03-20T09:22:55.018784Z",
                        "update_timestamp": "2024-03-20T09:22:55.018784Z",
                        "status": "SUB_ACCOUNT_STATUS_OPEN",
                        "account_id": "customer_account_id_1",
                    }
                ]
            },
        }
        response: CreateAccountV2Response = endtoend.core_api_helper.create_account_v2(
            self.customer_account_request
        )

        expected_response = CreateAccountV2Response(
            id="customer_account_id_1",
            type=AccountV2Type.ACCOUNT_TYPE_CUSTOMER,
            smart_contract_version_id="smart_contract_version_id_1",
            pending_smart_contract_version_id="",
            stakeholder_ids=["stakeholder_1", "stakeholder_2"],
            alias="alias_2",
            status=AccountV2Status.ACCOUNT_STATUS_OPEN,
            vault_create_timestamp=datetime(2024, 3, 20, 9, 22, 55, 18784, tzinfo=UTC),
            source_create_timestamp=datetime(2024, 3, 20, 9, 22, 55, 18784, tzinfo=UTC),
            source_open_timestamp=datetime(2024, 3, 20, 9, 22, 55, 18784, tzinfo=UTC),
            source_close_timestamp=None,
            update_timestamp=None,
            activation_timestamp=None,
            permitted_denominations=["GBP", "USD", "SGD", "AUD", "NZD", "VND", "JPY"],
            details={"c": "3", "d": "4"},
            t_side=AccountV2TSide.T_SIDE_ASSET,
            contract_update_timestamp=None,
            processing_group_id="p_2",
            tranche_id="",
            parameter_value_hierarchy_node_id="",
            processing_label="",
            create_options_side_effects=core_api.CreateOptionsSideEffects(
                sub_accounts=[
                    core_api.SubAccount(
                        id="sub_account_id",
                        type="sub_account_type",
                        name=None,
                        details=None,
                        status=core_api.SubAccountStatus.SUB_ACCOUNT_STATUS_OPEN,
                        activation_timestamp=datetime(2024, 3, 20, 9, 22, 55, 18784, tzinfo=UTC),
                        create_timestamp=datetime(2024, 3, 20, 9, 22, 55, 18784, tzinfo=UTC),
                        update_timestamp=datetime(2024, 3, 20, 9, 22, 55, 18784, tzinfo=UTC),
                        account_id="customer_account_id_1",
                    )
                ]
            ),
        )

        mock_send_request.assert_called_once_with(
            "post", "/v2/accounts", data=self.customer_account_request.model_dump_json()
        )
        self.assertEqual(response, expected_response)

    @patch.object(endtoend.helper, "send_request")
    def test_create_backdated_account_v2_for_customer(self, mock_send_request: MagicMock):
        # GIVEN a request to create a customer Account via the V2 Accounts API
        # GIVEN the Account specifies a backdated activation timestamp
        create_backdated_customer_account_v2_request = CreateAccountV2RequestBody(
            request_id="backdated_customer_account_request_id",
            account=CustomerAccountRequestBody(
                id="backdated_customer_account_id_1",
                smart_contract_version_id="smart_contract_version_id_1",
                stakeholder_ids=["stakeholder_1", "stakeholder_2"],
                alias="alias_2",
                status=AccountV2Status.ACCOUNT_STATUS_OPEN,
                activation_timestamp=datetime(2000, 3, 20, 9, 22, 55, 18784, tzinfo=UTC),
                permitted_denominations=["GBP", "USD", "SGD", "AUD", "NZD", "VND", "JPY"],
                details={
                    "c": "3",
                    "d": "4",
                },
                processing_group_id="p_2",
            ),
            create_options=self.create_options,
        )

        # GIVEN the API response indicates a successfully activated backdated Account
        mock_send_request.return_value = {
            "id": "customer_account_id_1",
            "type": "ACCOUNT_TYPE_CUSTOMER",
            "smart_contract_version_id": "smart_contract_version_id_1",
            "pending_smart_contract_version_id": "",
            "stakeholder_ids": ["stakeholder_1", "stakeholder_2"],
            "alias": "alias_2",
            "status": "ACCOUNT_STATUS_OPEN",
            "vault_create_timestamp": "2024-03-20T09:22:55.018784Z",
            "source_create_timestamp": "2000-03-20T09:22:55.018784Z",
            "source_open_timestamp": "2000-03-20T09:22:55.018784Z",
            "source_close_timestamp": None,
            "update_timestamp": None,
            "activation_timestamp": "2023-03-20T09:22:55.018784Z",
            "permitted_denominations": ["GBP", "USD", "SGD", "AUD", "NZD", "VND", "JPY"],
            "details": {"c": "3", "d": "4"},
            "t_side": "T_SIDE_ASSET",
            "contract_update_timestamp": None,
            "processing_group_id": "p_2",
            "tranche_id": "",
            "parameter_value_hierarchy_node_id": "",
            "processing_label": "",
        }

        # THEN the Pydantic Model is populated correctly
        self.assertEqual(
            endtoend.core_api_helper.create_account_v2(
                create_backdated_customer_account_v2_request,
            ),
            CreateAccountV2Response(
                id="customer_account_id_1",
                type=AccountV2Type.ACCOUNT_TYPE_CUSTOMER,
                smart_contract_version_id="smart_contract_version_id_1",
                pending_smart_contract_version_id="",
                stakeholder_ids=["stakeholder_1", "stakeholder_2"],
                alias="alias_2",
                status=AccountV2Status.ACCOUNT_STATUS_OPEN,
                vault_create_timestamp=datetime(2024, 3, 20, 9, 22, 55, 18784, tzinfo=UTC),
                source_open_timestamp=datetime(2000, 3, 20, 9, 22, 55, 18784, tzinfo=UTC),
                source_create_timestamp=datetime(2000, 3, 20, 9, 22, 55, 18784, tzinfo=UTC),
                source_close_timestamp=None,
                update_timestamp=None,
                activation_timestamp=datetime(2023, 3, 20, 9, 22, 55, 18784, tzinfo=UTC),
                permitted_denominations=["GBP", "USD", "SGD", "AUD", "NZD", "VND", "JPY"],
                details={"c": "3", "d": "4"},
                t_side=AccountV2TSide.T_SIDE_ASSET,
                contract_update_timestamp=None,
                processing_group_id="p_2",
                tranche_id="",
                parameter_value_hierarchy_node_id="",
                processing_label="",
            ),
        )
        # THEN the API is called with the correct request fields populated
        mock_send_request.assert_called_once_with(
            "post",
            "/v2/accounts",
            data=create_backdated_customer_account_v2_request.model_dump_json(),
        )
        return

    @patch.object(endtoend.helper, "send_request")
    def test_create_account_v2_for_internal(self, mock_send_request: MagicMock):
        mock_send_request.return_value = {
            "id": "internal_account_id_1",
            "type": "ACCOUNT_TYPE_INTERNAL",
            "smart_contract_version_id": "",
            "pending_smart_contract_version_id": "",
            "stakeholder_ids": [],
            "alias": "alias_1",
            "status": "ACCOUNT_STATUS_OPEN",
            "vault_create_timestamp": "2024-03-20T09:22:55.018784Z",
            "source_create_timestamp": "2024-03-20T09:22:55.018784Z",
            "source_open_timestamp": "2024-03-20T09:22:55.018784Z",
            "source_close_timestamp": None,
            "update_timestamp": None,
            "activation_timestamp": None,
            "permitted_denominations": [],
            "details": {"a": "1", "b": "2"},
            "t_side": "T_SIDE_ASSET",
            "contract_update_timestamp": None,
            "processing_group_id": "p_1",
            "tranche_id": "",
            "parameter_value_hierarchy_node_id": "",
            "processing_label": "",
        }
        response: CreateAccountV2Response = endtoend.core_api_helper.create_account_v2(
            self.internal_account_request
        )
        expected_response = CreateAccountV2Response(
            id="internal_account_id_1",
            type=AccountV2Type.ACCOUNT_TYPE_INTERNAL,
            smart_contract_version_id="",
            pending_smart_contract_version_id="",
            stakeholder_ids=[],
            alias="alias_1",
            status=AccountV2Status.ACCOUNT_STATUS_OPEN,
            vault_create_timestamp=datetime(2024, 3, 20, 9, 22, 55, 18784, tzinfo=UTC),
            source_create_timestamp=datetime(2024, 3, 20, 9, 22, 55, 18784, tzinfo=UTC),
            source_open_timestamp=datetime(2024, 3, 20, 9, 22, 55, 18784, tzinfo=UTC),
            source_close_timestamp=None,
            update_timestamp=None,
            activation_timestamp=None,
            permitted_denominations=[],
            details={"a": "1", "b": "2"},
            t_side=AccountV2TSide.T_SIDE_ASSET,
            contract_update_timestamp=None,
            processing_group_id="p_1",
            tranche_id="",
            parameter_value_hierarchy_node_id="",
            processing_label="",
        )

        mock_send_request.assert_called_once_with(
            "post", "/v2/accounts", data=self.internal_account_request.model_dump_json()
        )
        self.assertEqual(response, expected_response)


class CreateFlagV1Test(TestCase):
    def setUp(self):
        self.uuid = uuid.uuid4()
        endtoend.testhandle.vault_version = Version("5.2.0")

    @patch.object(endtoend.helper, "send_request")
    @patch.object(endtoend.core_api_helper.uuid, "uuid4")
    def test_create_account_flag(self, mock_uuid: MagicMock, mock_send_request: MagicMock):
        mock_uuid.return_value = self.uuid
        expected_flag = core_api.CreateFlagV1CreateAccountFlag(
            flag_definition_id="flag_1",
            description="description",
            effective_timestamp=datetime(2024, 12, 31, 23, 59, 59, 999999, tzinfo=UTC),
            expiry_timestamp=datetime(2025, 12, 31, 23, 59, 59, 999999, tzinfo=UTC),
            value=core_api.FlagV1FlagValue.FLAG_VALUE_ON,
            is_backdated=False,
            account_id="account_1",
        )
        # the response is the requested flag with an id populated
        mock_send_request.return_value = expected_flag.model_dump() | {"id": "id"}
        endtoend.core_api_helper.create_flag(
            flag_name="flag_1",
            account_id="account_1",
            description="description",
            effective_timestamp=datetime(2024, 12, 31, 23, 59, 59, 999999, tzinfo=UTC),
            expiry_timestamp=datetime(2025, 12, 31, 23, 59, 59, 999999, tzinfo=UTC),
            is_backdated=False,
            value=FlagV1FlagValue.FLAG_VALUE_ON,
        )
        mock_send_request.assert_called_once_with(
            "post",
            "/v1/flags",
            data=core_api.CreateFlagV1RequestBody(
                request_id=str(self.uuid), flag=expected_flag
            ).model_dump_json(),
        )

    @patch.object(endtoend.helper, "send_request")
    @patch.object(endtoend.core_api_helper.uuid, "uuid4")
    def test_create_customer_flag(self, mock_uuid: MagicMock, mock_send_request: MagicMock):
        mock_uuid.return_value = self.uuid
        expected_flag = core_api.CreateFlagV1CreateCustomerFlag(
            flag_definition_id="flag_1",
            description="description",
            effective_timestamp=datetime(2024, 12, 31, 23, 59, 59, 999999, tzinfo=UTC),
            expiry_timestamp=datetime(2025, 12, 31, 23, 59, 59, 999999, tzinfo=UTC),
            value=core_api.FlagV1FlagValue.FLAG_VALUE_ON,
            is_backdated=False,
            customer_id="customer_1",
        )
        # the response is the requested flag with an id populated
        mock_send_request.return_value = expected_flag.model_dump() | {"id": "id"}
        endtoend.core_api_helper.create_flag(
            flag_name="flag_1",
            customer_id="customer_1",
            description="description",
            effective_timestamp=datetime(2024, 12, 31, 23, 59, 59, 999999, tzinfo=UTC),
            expiry_timestamp=datetime(2025, 12, 31, 23, 59, 59, 999999, tzinfo=UTC),
            is_backdated=False,
            value=FlagV1FlagValue.FLAG_VALUE_ON,
        )
        mock_send_request.assert_called_once_with(
            "post",
            "/v1/flags",
            data=core_api.CreateFlagV1RequestBody(
                request_id=str(self.uuid), flag=expected_flag
            ).model_dump_json(),
        )

    @patch.object(endtoend.helper, "send_request")
    @patch.object(endtoend.core_api_helper.uuid, "uuid4")
    def test_create_payment_device_flag(self, mock_uuid: MagicMock, mock_send_request: MagicMock):
        mock_uuid.return_value = self.uuid
        expected_flag = core_api.CreateFlagV1CreatePaymentDeviceId(
            flag_definition_id="flag_1",
            description="description",
            effective_timestamp=datetime(2024, 12, 31, 23, 59, 59, 999999, tzinfo=UTC),
            expiry_timestamp=datetime(2025, 12, 31, 23, 59, 59, 999999, tzinfo=UTC),
            value=core_api.FlagV1FlagValue.FLAG_VALUE_ON,
            is_backdated=False,
            payment_device_id="payment_device_1",
        )
        # the response is the requested flag with an id populated
        mock_send_request.return_value = expected_flag.model_dump() | {"id": "id"}
        endtoend.core_api_helper.create_flag(
            flag_name="flag_1",
            payment_device_id="payment_device_1",
            description="description",
            effective_timestamp=datetime(2024, 12, 31, 23, 59, 59, 999999, tzinfo=UTC),
            expiry_timestamp=datetime(2025, 12, 31, 23, 59, 59, 999999, tzinfo=UTC),
            is_backdated=False,
            value=FlagV1FlagValue.FLAG_VALUE_ON,
        )
        mock_send_request.assert_called_once_with(
            "post",
            "/v1/flags",
            data=core_api.CreateFlagV1RequestBody(
                request_id=str(self.uuid), flag=expected_flag
            ).model_dump_json(),
        )

    @patch.object(endtoend.helper, "list_resources")
    def test_get_flag(self, mock_list_resources: MagicMock):
        account_ids = ["1", "2"]
        mock_list_resources.return_value = [
            dict(
                id="e2e_flag_definition_id",
                flag_definition_id="flag",
                account_id=i,
                description="description",
                creation_timestamp="2024-01-01T00:00:00.000000Z",
                create_timestamp="2024-01-01T00:00:00.000000Z",
                effective_timestamp="2024-01-01T00:00:00.000000Z",
                expiry_timestamp="2024-01-02T00:00:00.000000Z",
                is_active=True,
                is_backdated=False,
                value=core_api.FlagV1FlagValue.FLAG_VALUE_ON.value,
            )
            for i in account_ids
        ]
        flag_name = "e2e_flag_definition_id"
        effective_timestamp_range_from = datetime(2024, 1, 1, tzinfo=UTC)
        effective_timestamp_range_to = datetime(2024, 1, 2, tzinfo=UTC)
        flag = endtoend.core_api_helper.get_flag(
            flag_name=flag_name,
            account_ids=account_ids,
            effective_timestamp_range_from=effective_timestamp_range_from,
            effective_timestamp_range_to=effective_timestamp_range_to,
        )
        mock_list_resources.assert_called_once_with(
            "flags",
            params={
                "flag_definition_id": "e2e_flag_definition_id",
                "account_ids": account_ids,
                "effective_timestamp_range.from": "2024-01-01T00:00:00+00:00",
                "effective_timestamp_range.to": "2024-01-02T00:00:00+00:00",
            },
        )
        self.assertEquals(flag, mock_list_resources.return_value)


class ProcessingGroupTest(TestCase):
    @patch.object(endtoend.helper, "send_request")
    def test_get_processing_group(self, mock_send_request: MagicMock):
        mock_send_request.return_value = dict(
            id="my_processing_group_id",
            timezone="Europe/London",
            status="PROCESSING_GROUP_STATUS_ACTIVE",
            create_timestamp="2020-01-01T00:00:00+00:00",
            update_timestamp="2020-01-02T00:00:00+00:00",
            minimum_observation_timestamp="2020-01-03T00:00:00+00:00",
        )
        output = endtoend.core_api_helper.get_processing_group("my_processing_group_id")
        self.assertEqual(
            output,
            core_api.ProcessingGroup(
                id="my_processing_group_id",
                timezone=ZoneInfo("Europe/London"),
                status=core_api.ProcessingGroupStatus.ACTIVE,
                create_timestamp=datetime(2020, 1, 1, tzinfo=UTC),
                update_timestamp=datetime(2020, 1, 2, tzinfo=UTC),
                minimum_observation_timestamp=datetime(2020, 1, 3, tzinfo=UTC),
            ),
        )
        mock_send_request.assert_called_once_with(
            "get", "/v1/processing-groups/my_processing_group_id"
        )

    @patch.object(endtoend.helper, "send_request")
    def test_update_processing_group(self, mock_send_request: MagicMock):
        mock_send_request.return_value = dict(
            id="my_processing_group_id",
            timezone="Europe/London",
            status="PROCESSING_GROUP_STATUS_PAUSED",
            create_timestamp="2020-01-01T00:00:00+00:00",
            update_timestamp="2020-01-02T00:00:00+00:00",
            minimum_observation_timestamp="2020-01-03T00:00:00+00:00",
        )
        update_request = core_api.UpdateProcessingGroupRequestBody(
            request_id="request_id",
            update_mask=core_api.UpdateMask(paths=["status"]),
            processing_group=core_api.ProcessingGroupUpdate(
                status=core_api.ProcessingGroupStatus.PAUSED
            ),
            minimum_observation_timestamp_update_options=(
                core_api.MinimumObservationTimestampUpdateOptions(
                    schedules_observe_balances_at_unpause_time=True
                )
            ),
        )
        output = endtoend.core_api_helper.update_processing_group(
            "my_processing_group_id", update_request
        )
        self.assertEqual(
            output,
            core_api.ProcessingGroup(
                id="my_processing_group_id",
                timezone=ZoneInfo("Europe/London"),
                status=core_api.ProcessingGroupStatus.PAUSED,
                create_timestamp=datetime(2020, 1, 1, tzinfo=UTC),
                update_timestamp=datetime(2020, 1, 2, tzinfo=UTC),
                minimum_observation_timestamp=datetime(2020, 1, 3, tzinfo=UTC),
            ),
        )
        mock_send_request.assert_called_once_with(
            "put",
            "/v1/processing-groups/my_processing_group_id",
            data=update_request.model_dump_json(),
        )

    @patch.object(endtoend.helper, "list_resources")
    def test_list_processing_group(self, mock_list_resources: MagicMock):
        mock_list_resources.return_value = [
            dict(
                id="my_processing_group_id",
                timezone="Europe/London",
                status="PROCESSING_GROUP_STATUS_ACTIVE",
                create_timestamp="2020-01-01T00:00:00+00:00",
                update_timestamp="2020-01-02T00:00:00+00:00",
                minimum_observation_timestamp="2020-01-03T00:00:00+00:00",
            ),
            dict(
                id="my_processing_group_id_2",
                timezone="",
                status="PROCESSING_GROUP_STATUS_PAUSED",
                create_timestamp="2020-01-01T00:00:00+00:00",
                update_timestamp="2020-01-02T00:00:00+00:00",
                minimum_observation_timestamp="2020-01-03T00:00:00+00:00",
            ),
        ]
        output = endtoend.core_api_helper.list_processing_groups()
        self.assertListEqual(
            output,
            [
                core_api.ProcessingGroup(
                    id="my_processing_group_id",
                    timezone=ZoneInfo("Europe/London"),
                    status=core_api.ProcessingGroupStatus.ACTIVE,
                    create_timestamp=datetime(2020, 1, 1, tzinfo=UTC),
                    update_timestamp=datetime(2020, 1, 2, tzinfo=UTC),
                    minimum_observation_timestamp=datetime(2020, 1, 3, tzinfo=UTC),
                ),
                core_api.ProcessingGroup(
                    id="my_processing_group_id_2",
                    timezone=None,
                    status=core_api.ProcessingGroupStatus.PAUSED,
                    create_timestamp=datetime(2020, 1, 1, tzinfo=UTC),
                    update_timestamp=datetime(2020, 1, 2, tzinfo=UTC),
                    minimum_observation_timestamp=datetime(2020, 1, 3, tzinfo=UTC),
                ),
            ],
        )
        mock_list_resources.assert_called_once_with("processing-groups")


class UpdateParameterValueV1Test(TestCase):
    def setUp(self):
        self.uuid = uuid.uuid4()
        endtoend.testhandle.vault_version = Version("5.1.0")

    @patch.object(endtoend.helper, "send_request")
    @patch.object(endtoend.core_api_helper.uuid, "uuid4")
    def test_update_parameter_value_is_cancelled(
        self, mock_uuid: MagicMock, mock_send_request: MagicMock
    ):
        mock_uuid.return_value = self.uuid

        parameter_value_id = "parameter_value_id_str"
        parameter_id = "parameter_id_str"
        parameter_value = StringParameterValue(string_value="s_1")

        mock_send_request.return_value = dict(
            id=parameter_value_id,
            parameter_id=parameter_id,
            create_timestamp="2024-01-01T00:00:00.000000Z",
            update_timestamp="2024-01-01T00:00:00.000000Z",
            effective_from_timestamp="2024-01-01T00:00:00.000000Z",
            effective_to_timestamp="2024-01-02T00:00:00.000000Z",
            cancel_timestamp="2024-01-02T00:00:00.000000Z",
            is_cancelled=True,
            is_backdated=False,
            value=parameter_value,
        )
        update_request = core_api.UpdateParameterValueV1RequestBody(
            request_id=str(self.uuid),
            parameter_value=core_api.UpdateParameterValueV1ParameterValue(is_cancelled=True),
            update_mask=core_api.UpdateMask(paths=["is_cancelled"]),
            is_cancelled_update_options=core_api.IsCancelledUpdateOptions(
                skip_pre_parameter_change_hook=True
            ),
        )
        output = endtoend.core_api_helper.update_parameter_value(
            parameter_value_id=parameter_value_id,
            effective_to_timestamp=None,
            is_cancelled=True,
            skip_pre_parameter_change_hook=True,
        )
        self.assertEqual(
            output,
            core_api.ParameterValueResource(
                id=parameter_value_id,
                parameter_id=parameter_id,
                create_timestamp=datetime(2024, 1, 1, tzinfo=UTC),
                update_timestamp=datetime(2024, 1, 1, tzinfo=UTC),
                effective_from_timestamp=datetime(2024, 1, 1, tzinfo=UTC),
                effective_to_timestamp=datetime(2024, 1, 2, tzinfo=UTC),
                cancel_timestamp=datetime(2024, 1, 2, tzinfo=UTC),
                is_cancelled=True,
                is_backdated=False,
                value=parameter_value,
            ),
        )
        mock_send_request.assert_called_once_with(
            "put",
            "/v1/parameter-values/" + parameter_value_id,
            data=update_request.model_dump_json(),
        )

    @patch.object(endtoend.helper, "send_request")
    @patch.object(endtoend.core_api_helper.uuid, "uuid4")
    def test_update_parameter_value_effective_to_timestamp(
        self, mock_uuid: MagicMock, mock_send_request: MagicMock
    ):
        mock_uuid.return_value = self.uuid

        parameter_value_id = "parameter_value_id_str"
        parameter_id = "parameter_id_str"
        parameter_value = StringParameterValue(string_value="s_1")

        mock_send_request.return_value = dict(
            id=parameter_value_id,
            parameter_id=parameter_id,
            create_timestamp="2024-01-01T00:00:00.000000Z",
            update_timestamp="2024-01-01T00:00:00.000000Z",
            effective_from_timestamp="2024-01-01T00:00:00.000000Z",
            effective_to_timestamp="2024-12-31T23:59:00.000000Z",
            cancel_timestamp="2024-01-02T00:00:00.000000Z",
            is_backdated=False,
            value=parameter_value,
        )
        update_request = core_api.UpdateParameterValueV1RequestBody(
            request_id=str(self.uuid),
            parameter_value=core_api.UpdateParameterValueV1ParameterValue(
                effective_to_timestamp=datetime(2024, 12, 31, 23, 59, 0, 0, tzinfo=UTC)
            ),
            update_mask=core_api.UpdateMask(paths=["effective_to_timestamp"]),
            is_cancelled_update_options=core_api.IsCancelledUpdateOptions(
                skip_pre_parameter_change_hook=True
            ),
        )
        output = endtoend.core_api_helper.update_parameter_value(
            parameter_value_id=parameter_value_id,
            effective_to_timestamp=datetime(2024, 12, 31, 23, 59, 0, 0, tzinfo=UTC),
            skip_pre_parameter_change_hook=True,
        )
        self.assertEqual(
            output,
            core_api.ParameterValueResource(
                id=parameter_value_id,
                parameter_id=parameter_id,
                create_timestamp=datetime(2024, 1, 1, tzinfo=UTC),
                update_timestamp=datetime(2024, 1, 1, tzinfo=UTC),
                effective_from_timestamp=datetime(2024, 1, 1, tzinfo=UTC),
                effective_to_timestamp=datetime(2024, 12, 31, 23, 59, tzinfo=UTC),
                cancel_timestamp=datetime(2024, 1, 2, tzinfo=UTC),
                is_cancelled=False,
                is_backdated=False,
                value=parameter_value,
            ),
        )
        mock_send_request.assert_called_once_with(
            "put",
            "/v1/parameter-values/" + parameter_value_id,
            data=update_request.model_dump_json(),
        )

    @patch.object(endtoend.helper, "list_resources")
    def test_list_parameter_values(self, mock_list_resources: MagicMock):
        mock_list_resources.return_value = [
            dict(
                id="parameter_value_id_str",
                parameter_id="parameter_id_str",
                create_timestamp="2020-01-01T00:00:00+00:00",
                update_timestamp="2020-01-02T00:00:00+00:00",
                effective_from_timestamp="2024-01-01T00:00:00.000000Z",
                effective_to_timestamp="2024-01-02T00:00:00.000000Z",
                cancel_timestamp="2024-01-02T00:00:00.000000Z",
                is_cancelled=False,
                is_backdated=False,
                value=StringParameterValue(string_value="s_1"),
            ),
            dict(
                id="parameter_value_id_dcm",
                parameter_id="parameter_id_dcm",
                create_timestamp="2020-01-01T00:00:00+00:00",
                update_timestamp="2020-01-02T00:00:00+00:00",
                effective_from_timestamp="2024-01-01T00:00:00.000000Z",
                effective_to_timestamp="2024-01-02T00:00:00.000000Z",
                cancel_timestamp="2024-01-02T00:00:00.000000Z",
                is_cancelled=False,
                is_backdated=False,
                value=DecimalParameterValue(decimal_value=Decimal(1)),
            ),
        ]
        output = endtoend.core_api_helper.get_parameter_values(
            parameter_ids=["parameter_value_id_str", "parameter_value_id_dcm"]
        )
        get_request = {
            "parameter_ids": ["parameter_value_id_str", "parameter_value_id_dcm"],
            "account_ids": [],
            "effective_timestamp_range.from": None,
            "effective_timestamp_range.to": None,
        }
        self.assertListEqual(
            output,
            [
                core_api.ParameterValueResource(
                    id="parameter_value_id_str",
                    parameter_id="parameter_id_str",
                    create_timestamp=datetime(2020, 1, 1, tzinfo=UTC),
                    update_timestamp=datetime(2020, 1, 2, tzinfo=UTC),
                    effective_from_timestamp=datetime(2024, 1, 1, tzinfo=UTC),
                    effective_to_timestamp=datetime(2024, 1, 2, tzinfo=UTC),
                    cancel_timestamp=datetime(2024, 1, 2, tzinfo=UTC),
                    is_cancelled=False,
                    is_backdated=False,
                    value=StringParameterValue(string_value="s_1"),
                ),
                core_api.ParameterValueResource(
                    id="parameter_value_id_dcm",
                    parameter_id="parameter_id_dcm",
                    create_timestamp=datetime(2020, 1, 1, tzinfo=UTC),
                    update_timestamp=datetime(2020, 1, 2, tzinfo=UTC),
                    effective_from_timestamp=datetime(2024, 1, 1, tzinfo=UTC),
                    effective_to_timestamp=datetime(2024, 1, 2, tzinfo=UTC),
                    cancel_timestamp=datetime(2024, 1, 2, tzinfo=UTC),
                    is_cancelled=False,
                    is_backdated=False,
                    value=DecimalParameterValue(decimal_value=Decimal(1)),
                ),
            ],
        )
        mock_list_resources.assert_called_once_with("parameter-values", params=get_request)

    def test_update_is_cancelled_exception_raised_on_pre_5_1(self):
        endtoend.testhandle.vault_version = Version("5.0.0")

        with self.assertRaises(ValueError) as ex:
            endtoend.core_api_helper.update_parameter_value(
                parameter_value_id="parameter_value_id_str",
                effective_to_timestamp=None,
                is_cancelled=True,
                skip_pre_parameter_change_hook=True,
            )
        self.assertEqual(
            ex.exception.args[0],
            "The /v1/parameter-values endpoint only supports is_cancelled and "
            "skip_pre_parameter_change_hook on Vault 5.1 and above.",
        )


class BatchGetProductTest(TestCase):
    @patch.object(endtoend.helper, "send_request")
    def test_batch_get_product(self, mock_send_request: MagicMock):

        mock_send_request.return_value = {
            "products": {
                "product_1": {
                    "id": "product_1",
                    "display_name": "product_1_name",
                    "is_internal": False,
                    "current_version_id": "4",
                }
            }
        }

        response = endtoend.core_api_helper.batch_get_products(
            core_api.BatchGetProductsRequest(ids=["product_1"])
        )

        mock_send_request.assert_called_once_with(
            "get", "/v1/products:batchGet", params={"ids": ["product_1"]}
        )

        self.assertEquals(
            response,
            core_api.BatchGetProductsResponse(
                products={
                    "product_1": core_api.Product(
                        id="product_1",
                        display_name="product_1_name",
                        is_internal=False,
                        current_version_id="4",
                    ),
                }
            ),
        )


class BatchGetPostingInstructionBatchesTest(TestCase):
    @patch.object(endtoend.helper, "send_request")
    def test_batch_get_posting_instruction_batches(self, mock_send_request: MagicMock):
        mock_send_request.return_value = {
            "posting_instruction_batches": {
                "batch_1": {
                    "id": "batch_1",
                    "create_request_id": "req-id-1",
                    "client_id": "client-id",
                    "client_batch_id": "batch-id",
                    "status": "POSTING_INSTRUCTION_BATCH_STATUS_ACCEPTED",
                    "insertion_timestamp": "2020-01-01T00:00:00Z",
                    "source_insertion_timestamp": "2020-01-01T00:00:00Z",
                    "posting_instructions": [],
                }
            }
        }

        response = endtoend.core_api_helper.batch_get_posting_instruction_batches(
            core_api.BatchGetPostingInstructionBatchesRequest(ids=["batch_1"])
        )

        mock_send_request.assert_called_once_with(
            "get",
            "/v1/posting-instruction-batches:batchGet",
            params={"ids": ["batch_1"]},
        )

        self.assertEqual(
            response,
            core_api.BatchGetPostingInstructionBatchesResponse(
                posting_instruction_batches={
                    "batch_1": core_api.CommittedPostingInstructionBatch(
                        id="batch_1",
                        create_request_id="req-id-1",
                        client_id="client-id",
                        client_batch_id="batch-id",
                        status=core_api.PostingInstructionBatchStatus.ACCEPTED,
                        insertion_timestamp=datetime(2020, 1, 1, tzinfo=UTC),
                        source_insertion_timestamp=datetime(2020, 1, 1, tzinfo=UTC),
                        posting_instructions=[],
                    )
                }
            ),
        )


class CreateParameterValueHierarchyTest(TestCase):
    @patch.object(endtoend.helper, "send_request")
    def test_create_parameter_value_hierarchy_node_creation(self, mock_send_request: MagicMock):
        request_id = "create_pvh_node_request_id"
        mock_send_request.return_value = core_api.ParameterValueHierarchyNode(
            id="id",
            name="name",
            parent_id="parent_id",
            parent_path=["parent_path"],
            depth=1,
            metadata={"": ""},
            create_timestamp=datetime(2024, 1, 1, tzinfo=UTC),
            update_timestamp=datetime(2024, 1, 1, tzinfo=UTC),
        )

        parameter_value_hierarchy_node = core_api.CreateParameterValueHierarchyNode(
            id="id", name="name", parent_id="parent_id", metadata={"key": "value"}
        )

        create_request = core_api.CreateParameterValueHierarchyNodeRequestBody(
            request_id=request_id, parameter_value_hierarchy_node=parameter_value_hierarchy_node
        )
        endtoend.core_api_helper.create_parameter_value_hierarchy_node(
            request_id=request_id, parameter_value_hierarchy_node=parameter_value_hierarchy_node
        )
        mock_send_request.assert_called_once_with(
            "post", "/v1/parameter-value-hierarchy-nodes", data=create_request.model_dump_json()
        )


class ListProductVersionsTest(TestCase):
    @patch.object(endtoend.helper, "send_request")
    def test_list_product_versions(self, mock_send_request: MagicMock):
        mock_send_request.return_value = dict(
            product_versions=[],
            next_page_token="next_page",
            previous_page_token="prev_page",
        )

        request = core_api.ListProductVersionsRequestBody(
            product_id=str(uuid.uuid4()),
            view=core_api.ProductVersionView.BASIC,
            page_size=2,
            page_token=None,
        )

        endtoend.core_api_helper.list_product_versions(request=request)

        mock_send_request.assert_called_once_with(
            method="get",
            path="/v1/product-versions",
            params=request.model_dump(),
        )


class CreateProductVersionWithValidationTest(TestCase):
    @patch.object(endtoend.helper, "send_request")
    def test_create_product_version_with_validation_success(self, mock_send_request: MagicMock):
        # GIVEN product version pv1
        request_id = "request_id"
        product_version = core_api.ProductVersion(
            id="fixed_term_deposit_v1_0_0",
            product_id="fixed_term_deposit",
            display_name="Fixed Term Deposit Product v1.0.0",
            display_version_number=core_api.SemanticVersion(
                major=1, minor=0, patch=0, label="Release Candidate"
            ),
            description="A product for a fixed term deposit account.",
            summary="High-level summary of the product version.",
            tags=["savings", "term_deposit"],
            core_tags=[
                core_api.ProductVersionCoreTag.FIXED_TERM_DEPOSIT,
                core_api.ProductVersionCoreTag.DEPOSIT,
            ],
            is_current=True,
            code="print('Fixed Term Deposit Contract Code')",
            params=[
                core_api.ProductVersionParameter(
                    name="interest_rate",
                    display_name="Annual Interest Rate",
                    description="The interest rate applied to the deposit.",
                    value="0.035",
                    default_value="0.03",
                    effective_timestamp=datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC),
                    level=core_api.ProductVersionParameterLevel.PRODUCT,
                    update_permission=core_api.ProductVersionParameterUpdatePermission.FIXED,
                    derived=False,
                    is_optional=False,
                    number=core_api.ParamNumberField(
                        value_type=core_api.NumberValueType.PERCENTAGE,
                        min_value=Decimal("0.005"),
                        max_value=Decimal("0.10"),
                        step=Decimal("0.0001"),
                    ),
                    account=None,
                    values=None,
                    denomination=None,
                    date=None,
                    str_=None,
                ),
            ],
            address_details=[
                core_api.ProductVersionAddressDetails(
                    address_name="DEFAULT",
                    description="The default account address for balances.",
                    tags=["account_balances"],
                )
            ],
            attributes=[
                core_api.ProductVersionAttribute(
                    name="customer_segment",
                    data_type=core_api.AttributeType(
                        string_type=core_api.AttributeStringType(),
                    ),
                )
            ],
            contracts_language_api_version=core_api.SemanticVersion(
                major=4, minor=1, patch=0, label=""
            ),
            contract_module_details=core_api.ContractModuleDetails(
                alias_to_shared_function_details={
                    "key": core_api.SharedFunctionDetails(
                        shared_functions=[
                            core_api.SharedFunction(
                                name="share_func_1",
                                args=[
                                    core_api.SharedFunctionArgs(
                                        name="name",
                                        type="string",
                                    )
                                ],
                                return_type="string",
                            ),
                        ]
                    )
                }
            ),
            expected_parameters=[
                core_api.ExpectedParameter(
                    parameter_id="INTEREST_RATE",
                    is_optional=False,
                    triggers_pre_parameter_change_hook=False,
                    triggers_post_parameter_change_hook=True,
                )
            ],
            high_volume_eligibility=core_api.HighVolumeEligibility(ledger=False),
            notification_types=["ACCRUE_INTEREST_NOTIFICATION"],
            parameter_id_by_instance_parameter_name={
                "interest_rate": "INTEREST_RATE",
                "term_length": "TERM_LENGTH",
            },
            adjustments_versioning_policy=core_api.AdjustmentsVersioningPolicy.LATEST,
            adjustments_patch_version_id="fixed_term_deposit_v0_1_0_patch",
            supported_denominations=["GBP", "USD"],
            tside=core_api.Tside.LIABILITY,
            create_timestamp=datetime(2024, 3, 20, 10, 0, 0, tzinfo=UTC),
        )
        params = [
            core_api.CreateProductVersionParameter(
                name="interest_rate",
                value="0.035",
            )
        ]
        migration_strategy = core_api.ProductVersionMigrationStrategy.NEW_PRODUCT
        is_internal = False

        create_request = core_api.CreateProductVersionRequestBody(
            request_id=request_id,
            product_version=core_api.CreateProductVersionRequestProductVersion(
                product_id=product_version.product_id,
                display_name=product_version.display_name,
                description=product_version.description,
                summary=product_version.summary,
                tags=product_version.tags,
                core_tags=product_version.core_tags,
                code=product_version.code,
                params=params,
                high_volume_eligibility=product_version.high_volume_eligibility,
                supported_denominations=product_version.supported_denominations,
                adjustments_versioning_policy=product_version.adjustments_versioning_policy,
            ),
            migration_strategy=migration_strategy,
            is_internal=is_internal,
        )

        mock_send_request.return_value = product_version.model_dump()

        # WHEN create product version with validation is called
        actual = endtoend.core_api_helper.create_product_version_with_validation(
            request_id=request_id,
            product_id=product_version.product_id,
            code=product_version.code,
            is_internal=is_internal,
            migration_strategy=migration_strategy,
            display_name=product_version.display_name,
            description=product_version.description,
            summary=product_version.summary,
            tags=product_version.tags,
            core_tags=product_version.core_tags,
            params=params,
            high_volume_eligibility=product_version.high_volume_eligibility,
            supported_denominations=product_version.supported_denominations,
            adjustments_versioning_policy=product_version.adjustments_versioning_policy,
        )

        # THEN a single request made to POST /v1/product-versions and response
        # is a valid ProductVersion model
        mock_send_request.assert_called_once_with(
            method="post", path="/v1/product-versions", data=create_request.model_dump_json()
        )
        self.assertEqual(
            product_version,
            actual,
        )


class UpdateProductVersionParams(TestCase):

    @patch.object(endtoend.helper, "send_request")
    def test_update_product_version_params_success(self, mock_send_request: MagicMock):
        product_version_id = "product-1"
        # Validation of effective_timestamp to not be backdated so we dynamically create a dt
        now = datetime.now(UTC)
        tomorrow = now + timedelta(days=1)

        mock_send_request.return_value = {
            "id": product_version_id,
            "product_id": "product_id",
            "display_name": None,
            "display_version_number": {
                "major": 1,
                "minor": 0,
                "patch": 0,
                "label": "Release Candidate",
            },
            "description": None,
            "summary": None,
            "tags": None,
            "core_tags": None,
            "is_current": True,
            "code": "print('Fixed Term Deposit Contract Code')",
            "params": [
                {
                    "name": "param1",
                    "display_name": "param 1",
                    "description": "cool param",
                    "value": "0.05",
                    "default_value": "0.03",
                    "effective_timestamp": tomorrow.isoformat(),
                    "level": "LEVEL_PRODUCT",
                    "update_permission": "UPDATE_PERMISSION_FIXED",
                    "derived": False,
                    "is_optional": False,
                    "denomination": None,
                    "account": None,
                    "date": None,
                    "str": None,
                    "values": None,
                    "number": {
                        "value_type": "NUMBER_FIELD_DISPLAY_STYLE_PERCENTAGE",
                        "min_value": "0.005",
                        "max_value": "0.10",
                        "step": "0.0001",
                    },
                },
            ],
            "address_details": [],
            "attributes": [],
            "contracts_language_api_version": {"major": 4, "minor": 1, "patch": 0, "label": ""},
            "contract_module_details": None,
            "expected_parameters": [],
            "high_volume_eligibility": None,
            "notification_types": [],
            "parameter_id_by_instance_parameter_name": {},
            "adjustments_versioning_policy": "ADJUSTMENTS_VERSIONING_POLICY_LATEST",
            "adjustments_patch_version_id": "fixed_term_deposit_v0_1_0_patch",
            "supported_denominations": ["GBP"],
            "tside": "TSIDE_LIABILITY",
            "create_timestamp": "2024-03-20T10:00:00+00:00",
        }

        update_request = core_api.UpdateProductVersionParamsRequestBody(
            product_version_id="product-1",
            request_id="req-1",
            items_to_add=[
                core_api.UpdateProductVersionParams(
                    name="param1",
                    value="0.05",
                    effective_timestamp=tomorrow,
                )
            ],
            items_to_remove=[],
        )

        endtoend.core_api_helper.update_product_version_params(update_request)

        mock_send_request.assert_called_once_with(
            method="put",
            path=f"/v1/product-versions/{product_version_id}:updateParams",
            data=update_request.model_dump_json(),
        )


class ListProductVersionTimeseriesTest(TestCase):

    @patch.object(endtoend.helper, "send_request")
    def test_list_product_version_timeseries_success(self, mock_send_request: MagicMock):
        product_version_id = "123"
        tomorrow = datetime.now(UTC) + timedelta(days=1)
        mock_send_request.return_value = {
            "product_version_param_timeseries": [
                {
                    "param_name": "foo",
                    "values": [{"value": "1", "effective_from_timestamp": tomorrow.isoformat()}],
                }
            ]
        }

        endtoend.core_api_helper.list_product_version_timeseries(
            product_version_id=product_version_id
        )

        mock_send_request.assert_called_once_with(
            method="get",
            path=f"/v1/product-versions/{product_version_id}:paramTimeseries",
        )


class AccountAttributeTest(TestCase):
    @patch.object(endtoend.helper, "send_request")
    def test_list_account_attributes_one_account_and_attribute(self, mock_send_request: MagicMock):
        mock_send_request.return_value = ListAccountAttributeValuesResponse(
            account_attribute_values=[
                core_api.AccountAttributeValue(
                    account_id="account_1",
                    attribute_name="attribute_1",
                    effective_timestamp=datetime(2024, 1, 1, tzinfo=UTC),
                    value=core_api.AttributeValue(
                        string_value=core_api.AttributeStringValue(value="attribute_value")
                    ),
                )
            ],
            previous_page_token="",
            next_page_token="",
        )

        response = endtoend.core_api_helper.list_account_attributes(
            request=core_api.ListAccountAttributeValuesRequest(
                account_ids=["account_1"],
                attribute_names=["attribute_1"],
                effective_timestamps=[datetime(2024, 1, 1, tzinfo=UTC)],
                page_size=100,
            )
        )

        mock_send_request.assert_called_once_with(
            method="get",
            path="/v1/account-attribute-values",
            params={
                "account_ids": ["account_1"],
                "attribute_names": ["attribute_1"],
                "effective_timestamps": ["2024-01-01T00:00:00+00:00"],
                "page_size": 100,
            },
        )

        self.assertEquals(
            response,
            ListAccountAttributeValuesResponse(
                account_attribute_values=[
                    core_api.AccountAttributeValue(
                        account_id="account_1",
                        attribute_name="attribute_1",
                        effective_timestamp=datetime(2024, 1, 1, tzinfo=UTC),
                        value=core_api.AttributeValue(
                            string_value=core_api.AttributeStringValue(value="attribute_value")
                        ),
                    )
                ],
                previous_page_token="",
                next_page_token="",
            ),
        )

    @patch.object(endtoend.helper, "send_request")
    def test_list_account_attributes_no_effective_timestamp(self, mock_send_request: MagicMock):
        mock_send_request.return_value = ListAccountAttributeValuesResponse(
            account_attribute_values=[
                core_api.AccountAttributeValue(
                    account_id="account_1",
                    attribute_name="attribute_1",
                    effective_timestamp=datetime(2026, 1, 1, tzinfo=UTC),
                    value=core_api.AttributeValue(
                        string_value=core_api.AttributeStringValue(value="attribute_value")
                    ),
                )
            ],
            previous_page_token="",
            next_page_token="",
        )

        response = endtoend.core_api_helper.list_account_attributes(
            request=core_api.ListAccountAttributeValuesRequest(
                account_ids=["account_1"],
                attribute_names=["attribute_1"],
                page_size=100,
            )
        )

        mock_send_request.assert_called_once_with(
            method="get",
            path="/v1/account-attribute-values",
            params={
                "account_ids": ["account_1"],
                "attribute_names": ["attribute_1"],
                "page_size": 100,
            },
        )

        self.assertEquals(
            response,
            ListAccountAttributeValuesResponse(
                account_attribute_values=[
                    core_api.AccountAttributeValue(
                        account_id="account_1",
                        attribute_name="attribute_1",
                        effective_timestamp=datetime(2026, 1, 1, tzinfo=UTC),
                        value=core_api.AttributeValue(
                            string_value=core_api.AttributeStringValue(value="attribute_value")
                        ),
                    )
                ],
                previous_page_token="",
                next_page_token="",
            ),
        )
