# standard libs
import json
from copy import deepcopy
from datetime import datetime
from decimal import Decimal
from typing import Callable
from unittest import TestCase, skipIf, skipUnless
from unittest.mock import MagicMock, Mock, PropertyMock, call, mock_open, patch, sentinel
from zoneinfo import ZoneInfo

# third party
import requests

# contracts api
import contracts_api

# inception sdk
import inception_sdk.test_framework.endtoend as endtoend
import inception_sdk.vault.core_api as core_api
from inception_sdk.common.python.file_utils import load_file_contents
from inception_sdk.common.test.mocks.kafka import MockConsumer, MockMessage
from inception_sdk.test_framework.endtoend import contracts_helper, core_api_helper
from inception_sdk.test_framework.endtoend.contracts_helper import (
    COMMON_ACCOUNT_SCHEDULE_TAG_PATH,
    ContractNotificationResourceType,
    SetupError,
    get_contract_content_for_e2e,
    prepare_parameters_for_e2e,
)
from inception_sdk.vault.core_api import (
    AccountConstraint,
    AccountConstraintValue,
    AccountV2Status,
    AccountV2TSide,
    AccountV2Type,
    CreateAccountV2Response,
    CreateParameterResourceV1RequestBody,
    DecimalConstraint,
    DecimalConstraintValue,
    InternalAccountRequestBody,
    ParameterResource,
    StringConstraint,
    StringConstraintValue,
)

EXAMPLE_CONTRACT_CONTENTS = load_file_contents(
    "inception_sdk/test_framework/common/test/input/example_contract.py"
)
EXPECTED_E2E_CONTRACT_CONTENTS = load_file_contents(
    "inception_sdk/test_framework/common/test/output/contract_clu_references_replaced.py"
)

EXAMPLE_RENDERED_TEMPLATE = load_file_contents(
    "inception_sdk/test_framework/endtoend/test/unit/input/dummy_rendered_template.txt"
)
EXAMPLE_CONTRACT_NOTIFICATION = load_file_contents(
    "inception_sdk/test_framework/endtoend/test/unit/input/contract_notification.json"
)
EXPECTED_RENDERED_TEMPLATE_AFTER_REPR = load_file_contents(
    "inception_sdk/test_framework/endtoend/test/unit/output/dummy_rendered_template_after_repr.txt"
)
EXPECTED_RENDERED_TEMPLATE_AFTER_REPR_FLEX = load_file_contents(
    "inception_sdk/test_framework/endtoend/test/unit/output/dummy_rendered_template_after_repr_flexible_adjustments.txt"  # noqa: E501
)
UTC = ZoneInfo("UTC")


class TestContractsHelper(TestCase):
    test_product_id = "test_product_id"

    @patch.object(contracts_helper, "SmartContractRenderer")
    @patch.object(contracts_helper, "RendererConfig")
    @patch.object(contracts_helper, "is_file_renderable")
    @patch.object(contracts_helper, "load_module_from_filepath", MagicMock)
    def test_renderer_called_if_source_contract_is_renderable(
        self,
        mock_is_file_renderable: Mock,
        mock_renderer_config: Mock,
        mock_renderer: Mock,
    ):
        test_contract_properties = {
            "path": "test_contract_template_filepath",
            "template_params": {},
        }

        expected_content = "expected_content"

        mock_renderer_instance = Mock()
        mock_renderer.return_value = mock_renderer_instance
        mock_renderer_instance.rendered_contract = expected_content
        mock_is_file_renderable.return_value = True

        actual_content = get_contract_content_for_e2e(
            product_id=self.test_product_id,
            contract_properties=test_contract_properties,
        )
        mock_renderer_config.assert_called_once_with(
            autogen_warning="# Code auto-generated for e2e testing",
            apply_formatting=False,
            use_git=False,
        )
        mock_renderer.assert_called_once()
        mock_renderer_instance.render.assert_called_once_with(write_to_file=False)
        self.assertEqual(actual_content, expected_content)

    @patch("inception_sdk.test_framework.endtoend.contracts_helper.SmartContractRenderer")
    @patch("inception_sdk.test_framework.endtoend.contracts_helper.RendererConfig")
    @patch("inception_sdk.test_framework.endtoend.contracts_helper.load_file_contents")
    def test_renderer_not_called_if_source_contract_absent(
        self, mock_load_file_contents_method: Mock, mock_renderer_config: Mock, mock_renderer: Mock
    ):
        expected_content = "expected_content"

        test_contract_properties = {
            "path": "path_to/test_contract.py",
            "template_params": {},
        }

        mock_renderer_instance = Mock()
        mock_renderer.return_value = mock_renderer_instance
        mock_load_file_contents_method.return_value = expected_content

        actual_content = get_contract_content_for_e2e(
            product_id=self.test_product_id,
            contract_properties=test_contract_properties,
        )

        mock_renderer_config.assert_not_called()
        mock_renderer.assert_not_called()
        mock_renderer_instance.render.assert_not_called()

        self.assertEqual(actual_content, expected_content)

    def test_error_raised_if_neither_path_nor_source_are_provided(self):
        test_contract_properties = {
            "template_params": {},
        }
        with self.assertRaises(NameError) as e:
            get_contract_content_for_e2e(
                product_id=self.test_product_id, contract_properties=test_contract_properties
            )

        self.assertIn(
            "was not specified with a valid 'path' property",
            str(e.exception),
        )

    @patch.object(endtoend, "testhandle")
    def test_wait_for_contract_notification_with_match(self, mock_testhandle):
        type(mock_testhandle).kafka_consumers = PropertyMock(
            return_value={
                contracts_helper.CONTRACT_NOTIFICATIONS_TOPIC: MockConsumer(
                    [MockMessage(value=EXAMPLE_CONTRACT_NOTIFICATION)]
                )
            }
        )
        result = contracts_helper.wait_for_contract_notification(
            notification_type="my_notification_type",
            notification_details={"key": "value"},
            resource_id="my_resource_id",
            resource_type=ContractNotificationResourceType.RESOURCE_ACCOUNT,
        )
        self.assertIsNone(result)

    @patch.object(
        contracts_helper,
        "wait_for_messages",
        Mock(return_value={"another_resource_id_my_notification_type": None}),
    )
    @patch.object(endtoend, "testhandle")
    def test_wait_for_contract_notification_with_no_match(self, mock_testhandle):
        type(mock_testhandle).kafka_consumers = PropertyMock(
            return_value={
                contracts_helper.CONTRACT_NOTIFICATIONS_TOPIC: MockConsumer(
                    [MockMessage(value=EXAMPLE_CONTRACT_NOTIFICATION)]
                )
            }
        )
        with self.assertRaises(Exception) as e:
            contracts_helper.wait_for_contract_notification(
                notification_type="my_notification_type",
                notification_details={"key": "value"},
                resource_id="another_resource_id",
                resource_type=ContractNotificationResourceType.RESOURCE_ACCOUNT,
            )
        self.assertEqual(
            e.exception.args[0],
            "Failed to retrieve 1 notifications "
            "with following id and type: another_resource_id_my_notification_type",
        )


class UpdateContractTest(TestCase):
    maxDiff = None

    @patch.object(endtoend, "testhandle")
    @patch("builtins.open", mock_open(read_data=EXAMPLE_CONTRACT_CONTENTS))
    @patch.object(endtoend.core_api_helper, "create_product_version")
    def test_external_resource_ids_updated(
        self, create_product_version_mock: Mock, mock_testhandle: MagicMock
    ):
        type(mock_testhandle).do_version_check = PropertyMock(return_value=False)
        type(mock_testhandle).default_paused_tag_id = PropertyMock(return_value="E2E_PAUSED_TAG")
        type(mock_testhandle).controlled_schedule_tags = PropertyMock(
            return_value={"TEST_CONTRACT": {"EVENT_WITH_SINGLE_TAG": "E2E_AST_1"}}
        )
        type(mock_testhandle).clu_reference_mappings = PropertyMock(
            return_value={
                # Calendar Id
                "CALENDAR_1": "E2E_CALENDAR_1",
                "CALENDAR_2": "E2E_CALENDAR_2",
                "CALENDAR_3": "E2E_CALENDAR_3",
                # Flag Definition Id
                "ACCOUNT_DORMANT": "E2E_ACCOUNT_DORMANT",
                "REPAYMENT_HOLIDAY": "E2E_REPAYMENT_HOLIDAY",
            },
        )

        contracts_helper.upload_contracts(
            contracts={"TEST_CONTRACT": {"path": "dummy_path", "template_params": {}}}
        )
        updated_contract = create_product_version_mock.call_args_list[0].kwargs["code"]
        self.assertEqual(updated_contract, EXPECTED_E2E_CONTRACT_CONTENTS)


def is_adjustment_correction_point_in_contracts_api() -> bool:
    return "adjustment_correction_point" in {
        attr.name for attr in contracts_api.SmartContractEventType._public_attributes()
    }


class UpdateRenderedContractTest(TestCase):
    @patch.object(contracts_helper.uuid, "uuid4")
    @patch.object(contracts_helper, "get_contract_required_parameter_resources")
    @patch.object(contracts_helper, "create_parameter_definitions")
    @patch.object(endtoend, "testhandle")
    @patch.object(contracts_helper, "SmartContractRenderer")
    @patch.object(endtoend.core_api_helper, "create_product_version")
    @skipIf(
        is_adjustment_correction_point_in_contracts_api(),
        "Test applies to Contracts API versions < 5.11 (without adjustment_correction_point)",
    )
    def test_event_types_replaced_with_repr(
        self,
        mock_create_product_version: MagicMock,
        mock_renderer: MagicMock,
        mock_testhandle: MagicMock,
        mock_create_parameter_definitions: MagicMock,
        mock_get_contract_required_parameter_resources: MagicMock,
        mock_uuid4: MagicMock,
    ) -> None:
        fixed_uuid_mock = MagicMock()
        type(fixed_uuid_mock).hex = PropertyMock(return_value="fixed_uuid")
        mock_uuid4.return_value = fixed_uuid_mock
        mock_get_contract_required_parameter_resources.return_value = []
        mock_create_parameter_definitions.side_effect = None

        mock_renderer_instance = Mock()
        mock_renderer_instance.rendered_contract = EXAMPLE_RENDERED_TEMPLATE
        mock_renderer.return_value = mock_renderer_instance

        type(mock_testhandle).do_version_check = PropertyMock(return_value=False)
        type(mock_testhandle).default_paused_tag_id = PropertyMock(return_value="E2E_PAUSED_TAG")
        type(mock_testhandle).controlled_schedule_tags = PropertyMock(
            return_value={
                "TEST_CONTRACT": {
                    "event_type_1": "PAUSED_DUMMY_event_type_1_tag_1",
                    "event_type_4": "PAUSED_DUMMY_event_type_4_tag_1",
                }
            }
        )

        # The contents of this contract won't affect event type output as we replace the template's
        # event_types with repr and insert this into the rendered contract
        # (i.e. EXAMPLE_RENDERED_TEMPLATE based on the mocks above)
        contracts_helper.upload_contracts(
            contracts={
                "TEST_CONTRACT": {
                    "path": "inception_sdk/test_framework/endtoend/test/unit/input/"
                    "dummy_template.py",
                    "template_params": {},
                }
            }
        )

        updated_contract = mock_create_product_version.call_args_list[0].kwargs["code"]

        # The event_types replacement logic varies slightly based on the Contracts API version.
        # In version 5.11+, SmartContractEventType introduced the `adjustment_correction_point`
        # attribute. This test ensures the correct representation is generated for older
        # versions where this is absent.
        self.assertEqual(
            EXPECTED_RENDERED_TEMPLATE_AFTER_REPR,
            updated_contract,
        )
        mock_create_parameter_definitions.assert_called_with([])

    @patch.object(contracts_helper.uuid, "uuid4")
    @patch.object(contracts_helper, "get_contract_required_parameter_resources")
    @patch.object(contracts_helper, "create_parameter_definitions")
    @patch.object(endtoend, "testhandle")
    @patch.object(contracts_helper, "SmartContractRenderer")
    @patch.object(endtoend.core_api_helper, "create_product_version")
    @skipUnless(
        is_adjustment_correction_point_in_contracts_api(),
        "Test applies to Contracts API versions >= 5.11 (with adjustment_correction_point)",
    )
    def test_event_types_replaced_with_repr_flexible_corrections(
        self,
        mock_create_product_version: MagicMock,
        mock_renderer: MagicMock,
        mock_testhandle: MagicMock,
        mock_create_parameter_definitions: MagicMock,
        mock_get_contract_required_parameter_resources: MagicMock,
        mock_uuid4: MagicMock,
    ) -> None:
        fixed_uuid_mock = MagicMock()
        type(fixed_uuid_mock).hex = PropertyMock(return_value="fixed_uuid")
        mock_uuid4.return_value = fixed_uuid_mock
        mock_get_contract_required_parameter_resources.return_value = []
        mock_create_parameter_definitions.side_effect = None

        mock_renderer_instance = Mock()
        mock_renderer_instance.rendered_contract = EXAMPLE_RENDERED_TEMPLATE
        mock_renderer.return_value = mock_renderer_instance

        type(mock_testhandle).do_version_check = PropertyMock(return_value=False)
        type(mock_testhandle).default_paused_tag_id = PropertyMock(return_value="E2E_PAUSED_TAG")
        type(mock_testhandle).controlled_schedule_tags = PropertyMock(
            return_value={
                "TEST_CONTRACT": {
                    "event_type_1": "PAUSED_DUMMY_event_type_1_tag_1",
                    "event_type_4": "PAUSED_DUMMY_event_type_4_tag_1",
                }
            }
        )

        # The contents of this contract won't affect event type output as we replace the template's
        # event_types with repr and insert this into the rendered contract
        # (i.e. EXAMPLE_RENDERED_TEMPLATE based on the mocks above)
        contracts_helper.upload_contracts(
            contracts={
                "TEST_CONTRACT": {
                    "path": "inception_sdk/test_framework/endtoend/test/unit/input/"
                    "dummy_template.py",
                    "template_params": {},
                }
            }
        )

        updated_contract = mock_create_product_version.call_args_list[0].kwargs["code"]

        # The event_types replacement logic varies slightly based on the Contracts API version.
        # In version 5.11+, SmartContractEventType introduced the `adjustment_correction_point`
        # attribute. This test ensures the correct representation is generated for newer
        # versions where this is present.
        self.assertEqual(
            EXPECTED_RENDERED_TEMPLATE_AFTER_REPR_FLEX,
            updated_contract,
        )
        mock_create_parameter_definitions.assert_called_with([])


@patch.object(contracts_helper.uuid, "uuid4")
@patch.object(endtoend.core_api_helper, "create_account_schedule_tag")
@patch.object(endtoend, "testhandle")
class CreateAccountScheduleTagsTest(TestCase):
    maxDiff = None

    def create_account_schedule_tags(self) -> Callable[..., dict[str, str]]:
        return lambda account_schedule_tag_id, **kwargs: {
            "id": f"{account_schedule_tag_id}_uploaded_tag"
        }

    def test_only_create_default_paused_tag_if_no_controlled_schedules(
        self,
        mock_testhandle: MagicMock,
        mock_create_account_schedule_tag: MagicMock,
        mock_uuid4: MagicMock,
    ):
        mock_create_account_schedule_tag.return_value = {"id": "uploaded_id"}

        contracts_helper.create_account_schedule_tags(controlled_schedules={})

        self.assertDictEqual(mock_testhandle.controlled_schedule_tags, {})
        self.assertEqual(mock_testhandle.default_paused_tag_id, "uploaded_id")

    def test_only_create_default_paused_tag_if_upgrades_but_no_controlled_schedules(
        self,
        mock_testhandle: MagicMock,
        mock_create_account_schedule_tag: MagicMock,
        mock_uuid4: MagicMock,
    ):
        mock_create_account_schedule_tag.return_value = {"id": "uploaded_id"}
        mock_testhandle.CONTRACT_VERSION_UPGRADES = {"from_product": "to_product"}
        contracts_helper.create_account_schedule_tags(controlled_schedules={})

        self.assertDictEqual(mock_testhandle.controlled_schedule_tags, {})
        self.assertEqual(mock_testhandle.default_paused_tag_id, "uploaded_id")

    def test_create_tags_for_controlled_schedules(
        self,
        mock_testhandle: MagicMock,
        mock_create_account_schedule_tag: MagicMock,
        mock_uuid4: MagicMock,
    ):
        mock_create_account_schedule_tag.side_effect = self.create_account_schedule_tags()
        mock_uuid4.side_effect = ["uuid_1", "uuid_2", "uuid_3", "uuid_4"]

        contracts_helper.create_account_schedule_tags(
            controlled_schedules={
                "product_1": ["schedule_1", "schedule_2"],
                "product_2": ["schedule_1"],
            }
        )

        self.assertDictEqual(
            mock_testhandle.controlled_schedule_tags,
            {
                "product_1": {
                    "schedule_1": "PAUSED_E2E_TAG_schedule_1_uuid_1_uploaded_tag",
                    "schedule_2": "PAUSED_E2E_TAG_schedule_2_uuid_2_uploaded_tag",
                },
                "product_2": {"schedule_1": "PAUSED_E2E_TAG_schedule_1_uuid_3_uploaded_tag"},
            },
        )
        self.assertEqual(
            mock_testhandle.default_paused_tag_id, "PAUSED_E2E_TAG_DEFAULT_uuid_4_uploaded_tag"
        )

    def test_upgraded_products_preserve_schedule_tags_by_default(
        self,
        mock_testhandle: MagicMock,
        mock_create_account_schedule_tag: MagicMock,
        mock_uuid4: MagicMock,
    ):
        mock_create_account_schedule_tag.side_effect = self.create_account_schedule_tags()
        mock_uuid4.side_effect = ["uuid_1", "uuid_2", "uuid_3"]
        mock_testhandle.CONTRACT_VERSION_UPGRADES = {"from_product": "to_product"}
        contracts_helper.create_account_schedule_tags(
            controlled_schedules={
                "from_product": ["schedule_1", "schedule_2"],
            }
        )

        expected_product_schedule_tags = {
            "schedule_1": "PAUSED_E2E_TAG_schedule_1_uuid_1_uploaded_tag",
            "schedule_2": "PAUSED_E2E_TAG_schedule_2_uuid_2_uploaded_tag",
        }

        self.assertDictEqual(
            mock_testhandle.controlled_schedule_tags,
            {
                "from_product": expected_product_schedule_tags,
                "to_product": expected_product_schedule_tags,
            },
        )
        self.assertEqual(
            mock_testhandle.default_paused_tag_id, "PAUSED_E2E_TAG_DEFAULT_uuid_3_uploaded_tag"
        )

    def test_upgraded_products_schedules_can_still_be_controlled_separately(
        self,
        mock_testhandle: MagicMock,
        mock_create_account_schedule_tag: MagicMock,
        mock_uuid4: MagicMock,
    ):
        mock_create_account_schedule_tag.side_effect = self.create_account_schedule_tags()
        mock_uuid4.side_effect = ["uuid_1", "uuid_2", "uuid_3", "uuid_4"]
        mock_testhandle.CONTRACT_VERSION_UPGRADES = {"from_product": "to_product"}
        # We expect schedule 2's tag to be preserved on to_product, but not schedule 1's
        contracts_helper.create_account_schedule_tags(
            controlled_schedules={
                "from_product": ["schedule_1", "schedule_2"],
                "to_product": ["schedule_1"],
            }
        )

        self.assertDictEqual(
            mock_testhandle.controlled_schedule_tags,
            {
                "from_product": {
                    "schedule_1": "PAUSED_E2E_TAG_schedule_1_uuid_1_uploaded_tag",
                    "schedule_2": "PAUSED_E2E_TAG_schedule_2_uuid_2_uploaded_tag",
                },
                "to_product": {
                    "schedule_1": "PAUSED_E2E_TAG_schedule_1_uuid_3_uploaded_tag",
                    "schedule_2": "PAUSED_E2E_TAG_schedule_2_uuid_2_uploaded_tag",
                },
            },
        )
        self.assertEqual(
            mock_testhandle.default_paused_tag_id, "PAUSED_E2E_TAG_DEFAULT_uuid_4_uploaded_tag"
        )

    @patch.object(endtoend.core_api_helper, "batch_get_account_schedule_tags")
    def test_create_tags_with_conflicting_previously_updated_tag(
        self,
        mock_batch_get_account_schedule_tags: MagicMock,
        mock_testhandle: MagicMock,
        mock_create_account_schedule_tag: MagicMock,
        mock_uuid4: MagicMock,
    ):
        mock_create_account_schedule_tag.side_effect = requests.HTTPError(
            "409 Client Error: Conflict"
        )
        mock_batch_get_account_schedule_tags.return_value = {"PAUSED_E2E_TAG_schedule_1_uuid_1": {}}
        mock_uuid4.side_effect = ["uuid_1", "uuid_2", "uuid_3", "uuid_4"]

        with self.assertRaisesRegex(ValueError, r"Found existing tag"):
            contracts_helper.create_account_schedule_tags(
                controlled_schedules={"product_1": ["schedule_1"]}
            )

    @patch.object(endtoend.core_api_helper, "batch_get_account_schedule_tags")
    def test_create_tags_with_matching_previously_updated_tag(
        self,
        mock_batch_get_account_schedule_tags: MagicMock,
        mock_testhandle: MagicMock,
        mock_create_account_schedule_tag: MagicMock,
        mock_uuid4: MagicMock,
    ):
        # Ensure first attempt fails
        mock_create_account_schedule_tag.side_effect = [
            requests.HTTPError("409 Client Error: Conflict"),
            {"id": "PAUSED_E2E_TAG_DEFAULT_uuid_2_uploaded_tag"},
        ]
        mock_batch_get_account_schedule_tags.return_value = {
            "PAUSED_E2E_TAG_schedule_1_uuid_1": contracts_helper.extract_resource(
                COMMON_ACCOUNT_SCHEDULE_TAG_PATH, "account_schedule_tag"
            )
        }
        mock_uuid4.side_effect = ["uuid_1", "uuid_2"]

        contracts_helper.create_account_schedule_tags(
            controlled_schedules={"product_1": ["schedule_1"]}
        )

        self.assertDictEqual(
            mock_testhandle.controlled_schedule_tags,
            {
                "product_1": {
                    # This the id from the default tag, as per
                    # mock_batch_get_account_schedule_tags.return_value
                    "schedule_1": "PAUSED_E2E_TAG",
                },
            },
        )
        self.assertEqual(
            mock_testhandle.default_paused_tag_id, "PAUSED_E2E_TAG_DEFAULT_uuid_2_uploaded_tag"
        )

    def test_create_tags_with_unknown_error(
        self,
        mock_testhandle: MagicMock,
        mock_create_account_schedule_tag: MagicMock,
        mock_uuid4: MagicMock,
    ):
        mock_create_account_schedule_tag.side_effect = Exception("Unknown")
        mock_uuid4.side_effect = ["uuid_1", "uuid_2", "uuid_3", "uuid_4"]

        with self.assertRaises(Exception) as ctx:
            contracts_helper.create_account_schedule_tags(
                controlled_schedules={"product_1": ["schedule_1"]}
            )
        self.assertEqual(ctx.exception.args[0], "Unknown")


@patch.object(contracts_helper.uuid, "uuid4")
@patch.object(endtoend.core_api_helper, "create_account_schedule_tag")
@patch.object(endtoend, "testhandle")
class CreateAccountScheduleTagsWithProductVersionsTest(TestCase):
    maxDiff = None

    def create_account_schedule_tags(self) -> Callable[..., dict[str, str]]:
        return lambda account_schedule_tag_id, **kwargs: {
            "id": f"{account_schedule_tag_id}_uploaded_tag"
        }

    def test_create_only_default_paused_tag_if_no_controlled_schedules(
        self,
        mock_testhandle: MagicMock,
        mock_create_account_schedule_tag: MagicMock,
        mock_uuid4: MagicMock,
    ):
        mock_create_account_schedule_tag.return_value = {"id": "uploaded_id"}
        mock_testhandle.PRODUCTS = [MagicMock()]

        contracts_helper.create_account_schedule_tags(controlled_schedules={})

        self.assertDictEqual(mock_testhandle.controlled_schedule_tags, {})
        self.assertEqual(mock_testhandle.default_paused_tag_id, "uploaded_id")

    def test_create_tags_for_controlled_schedules_at_product_level(
        self,
        mock_testhandle: MagicMock,
        mock_create_account_schedule_tag: MagicMock,
        mock_uuid4: MagicMock,
    ):
        mock_create_account_schedule_tag.side_effect = self.create_account_schedule_tags()
        mock_uuid4.side_effect = ["uuid_1", "uuid_2", "uuid_3", "uuid_4"]

        # Setup products (though function doesn't rely on them anymore for tagging logic)
        pv1 = MagicMock(product_version_id="product_version_id_1")
        pv2 = MagicMock(product_version_id="product_version_id_2")
        p1 = MagicMock(product_id="product_id_1", product_versions=[pv1, pv2])
        p2 = MagicMock(product_id="product_id_2", product_versions=[MagicMock()])

        mock_testhandle.PRODUCTS = [p1, p2]

        contracts_helper.create_account_schedule_tags(
            controlled_schedules={
                "product_id_1": ["schedule_1", "schedule_2"],
                "product_id_2": ["schedule_1"],
            }
        )
        # Validate same tags are used with product_versions associated to the
        # same product_id
        self.assertDictEqual(
            mock_testhandle.controlled_schedule_tags,
            {
                "product_id_1": {
                    "schedule_1": "PAUSED_E2E_TAG_schedule_1_uuid_1_uploaded_tag",
                    "schedule_2": "PAUSED_E2E_TAG_schedule_2_uuid_2_uploaded_tag",
                },
                "product_id_2": {"schedule_1": "PAUSED_E2E_TAG_schedule_1_uuid_3_uploaded_tag"},
            },
        )
        self.assertEqual(
            mock_testhandle.default_paused_tag_id, "PAUSED_E2E_TAG_DEFAULT_uuid_4_uploaded_tag"
        )

    @patch.object(endtoend.core_api_helper, "batch_get_account_schedule_tags")
    def test_create_tags_with_conflicting_previously_updated_tag(
        self,
        mock_batch_get_account_schedule_tags: MagicMock,
        mock_testhandle: MagicMock,
        mock_create_account_schedule_tag: MagicMock,
        mock_uuid4: MagicMock,
    ):
        mock_create_account_schedule_tag.side_effect = requests.HTTPError(
            "409 Client Error: Conflict"
        )
        pv1 = MagicMock(product_version_id="product_version_id_1")
        p1 = MagicMock(product_id="product_id_1", product_versions=[pv1])

        mock_testhandle.PRODUCTS = [p1]

        mock_batch_get_account_schedule_tags.return_value = {"PAUSED_E2E_TAG_schedule_1_uuid_1": {}}
        mock_uuid4.side_effect = ["uuid_1"]

        with self.assertRaisesRegex(ValueError, r"Found existing tag"):
            contracts_helper.create_account_schedule_tags(
                controlled_schedules={"product_id_1": ["schedule_1"]}
            )

    def test_create_tags_with_unknown_error(
        self,
        mock_testhandle: MagicMock,
        mock_create_account_schedule_tag: MagicMock,
        mock_uuid4: MagicMock,
    ):
        mock_create_account_schedule_tag.side_effect = Exception("Unknown")
        mock_uuid4.side_effect = ["uuid_1"]
        pv1 = MagicMock(product_version_id="product_version_id_1")
        p1 = MagicMock(product_id="product_id_1", product_versions=[pv1])

        mock_testhandle.PRODUCTS = [p1]

        with self.assertRaises(Exception) as ctx:
            contracts_helper.create_account_schedule_tags(
                controlled_schedules={"product_id_1": ["schedule_1"]}
            )
        self.assertEqual(ctx.exception.args[0], "Unknown")


class CreateContractNotificationTest(TestCase):
    @patch.object(contracts_helper.uuid, "uuid4")
    @patch.object(contracts_helper, "produce_message")
    @patch.object(endtoend, "testhandle")
    def test_create_contract_notification(
        self, mock_testhandle: MagicMock, mock_produce_message: MagicMock, mock_uuid_4: MagicMock
    ):
        # we're ultimately mocking uuid.uuid4().hex, so we need uuid.uuid() to return a mock
        # with a property mock for the .hex property
        # can't use sentinels because they're not json serialisable
        mock_uuid = MagicMock()
        type(mock_uuid).hex = PropertyMock(return_value="my_uuid")
        mock_uuid_4.return_value = mock_uuid
        mock_producer = MagicMock(name="kafka_producer")
        type(mock_testhandle).kafka_producer = PropertyMock(return_value=mock_producer)
        contracts_helper.send_contract_notification(
            notification_details={"my": "details"},
            notification_type="type",
            resource_id="id",
            resource_type=contracts_helper.ContractNotificationResourceType.RESOURCE_ACCOUNT,
        )

        mock_uuid_4.assert_called_once()
        mock_produce_message.assert_called_once_with(
            mock_producer,
            contracts_helper.CONTRACT_NOTIFICATIONS_TOPIC,
            json.dumps(
                {
                    "event_id": "my_uuid",
                    "notification_type": "type",
                    "resource_id": "id",
                    "resource_type": (
                        contracts_helper.ContractNotificationResourceType.RESOURCE_ACCOUNT.value
                    ),
                    "notification_details": {"my": "details"},
                }
            ),
        )


@patch.dict(
    "inception_sdk.test_framework.endtoend.testhandle.internal_contract_pid_to_uploaded_pid",
    {sentinel.contract: sentinel.product_id},
)
@patch.object(core_api_helper, "create_internal_account")
class CreateInternalAccountTest(TestCase):
    maxDiff = None

    def test_create_internal_account_with_composite_id_over_length_limit(
        self, mock_create_internal_account: MagicMock
    ):
        with self.assertRaises(SetupError) as e:
            contracts_helper.create_internal_account(
                account_id="TEST_INTERNAL_NAME_OVER_30_CHARS",
                contract=sentinel.contract,
                accounting_tside="TSIDE_ASSET",
                details=sentinel.details,
            )

        self.assertIn(
            "Internal account id e2e_A_TEST_INTERNAL_NAME_OVER_30_CHARS is longer than 36 "
            "characters.",
            str(e.exception),
        )

        mock_create_internal_account.assert_not_called()

    def test_create_internal_account_without_composite_id_over_length_limit(
        self, mock_create_internal_account: MagicMock
    ):
        with self.assertRaises(SetupError) as e:
            contracts_helper.create_internal_account(
                account_id="TEST_INTERNAL_NAME_OVER_36_CHARS12345",
                contract=sentinel.contract,
                accounting_tside="TSIDE_ASSET",
                details=sentinel.details,
                use_composite_id=False,
            )

        self.assertIn(
            "Internal account id TEST_INTERNAL_NAME_OVER_36_CHARS12345 is longer than 36 "
            "characters.",
            str(e.exception),
        )

        mock_create_internal_account.assert_not_called()

    @patch.dict(
        "inception_sdk.test_framework.endtoend.testhandle.internal_account_id_to_uploaded_id", {}
    )
    def test_create_internal_account_under_length_limit_with_composite_id(
        self, mock_create_internal_account: MagicMock
    ):
        mock_create_internal_account.return_value = sentinel.account
        result = contracts_helper.create_internal_account(
            account_id="TEST_INTERNAL_NAME_EQUAL_MAX_L",
            contract=sentinel.contract,
            accounting_tside="TSIDE_ASSET",
            details=sentinel.details,
        )
        self.assertEqual(result, sentinel.account)
        mock_create_internal_account.assert_called_once_with(
            request_id="e2e_A_TEST_INTERNAL_NAME_EQUAL_MAX_L",
            internal_account_id="e2e_A_TEST_INTERNAL_NAME_EQUAL_MAX_L",
            product_id=sentinel.product_id,
            accounting_tside="TSIDE_ASSET",
            details=sentinel.details,
        )
        self.assertDictEqual(
            endtoend.testhandle.internal_account_id_to_uploaded_id,
            {"TEST_INTERNAL_NAME_EQUAL_MAX_L": "e2e_A_TEST_INTERNAL_NAME_EQUAL_MAX_L"},
        )

    @patch.dict(
        "inception_sdk.test_framework.endtoend.testhandle.internal_account_id_to_uploaded_id", {}
    )
    def test_create_internal_account_under_length_limit_without_composite_id(
        self,
        mock_create_internal_account: MagicMock,
    ):
        mock_create_internal_account.return_value = sentinel.account
        result = contracts_helper.create_internal_account(
            account_id="TEST_INTERNAL_NAME_EQUAL_MAX_L",
            contract=sentinel.contract,
            accounting_tside="TSIDE_ASSET",
            details=sentinel.details,
            use_composite_id=False,
        )
        self.assertEqual(result, sentinel.account)
        mock_create_internal_account.assert_called_once_with(
            request_id="TEST_INTERNAL_NAME_EQUAL_MAX_L",
            internal_account_id="TEST_INTERNAL_NAME_EQUAL_MAX_L",
            product_id=sentinel.product_id,
            accounting_tside="TSIDE_ASSET",
            details=sentinel.details,
        )
        self.assertDictEqual(
            endtoend.testhandle.internal_account_id_to_uploaded_id,
            {"TEST_INTERNAL_NAME_EQUAL_MAX_L": "TEST_INTERNAL_NAME_EQUAL_MAX_L"},
        )


@patch.object(core_api_helper, "create_internal_account_v2")
class CreateInternalAccountV2Test(TestCase):
    maxDiff = None

    def test_create_internal_account_v2_with_composite_id_over_length_limit(
        self, mock_create_internal_account_v2: MagicMock
    ):
        with self.assertRaises(SetupError) as e:
            contracts_helper.create_internal_account_v2(
                account_id="TEST_INTERNAL_NAME_OVER_30_CHARS",
                t_side=AccountV2TSide.T_SIDE_ASSET,
                details=sentinel.details,
            )

        self.assertIn(
            "Internal account id e2e_A_TEST_INTERNAL_NAME_OVER_30_CHARS is longer than 36 "
            "characters. Please use an internal account id that is up to 30 characters long if "
            "using a composite id or 36 otherwise.",
            str(e.exception),
        )

        mock_create_internal_account_v2.assert_not_called()

    def test_create_internal_account_v2_without_composite_id_over_length_limit(
        self, mock_create_internal_account_v2: MagicMock
    ):
        with self.assertRaises(SetupError) as e:
            contracts_helper.create_internal_account_v2(
                account_id="TEST_INTERNAL_NAME_OVER_36_CHARS12345",
                t_side=AccountV2TSide.T_SIDE_ASSET,
                details=sentinel.details,
                use_composite_id=False,
            )

        self.assertIn(
            "Internal account id TEST_INTERNAL_NAME_OVER_36_CHARS12345 is longer than 36 "
            "characters. Please use an internal account id that is up to 30 characters long if "
            "using a composite id or 36 otherwise.",
            str(e.exception),
        )

        mock_create_internal_account_v2.assert_not_called()

    @patch.dict(
        "inception_sdk.test_framework.endtoend.testhandle.internal_account_id_to_uploaded_id", {}
    )
    def test_create_internal_account_v2_under_length_limit_with_composite_id(
        self, mock_create_internal_account_v2: MagicMock
    ):
        mock_create_internal_account_v2.return_value = sentinel.account
        result = contracts_helper.create_internal_account_v2(
            account_id="TEST_INTERNAL_NAME_EQUAL_MAX_L",
            t_side=AccountV2TSide.T_SIDE_ASSET,
            details={"sentinel": "dict"},
        )
        self.assertEqual(result, sentinel.account)
        mock_create_internal_account_v2.assert_called_once_with(
            request_id="e2e_A_TEST_INTERNAL_NAME_EQUAL_MAX_L",
            account=InternalAccountRequestBody(
                id="e2e_A_TEST_INTERNAL_NAME_EQUAL_MAX_L",
                status=AccountV2Status.ACCOUNT_STATUS_OPEN,
                details={"sentinel": "dict"},
                t_side=AccountV2TSide.T_SIDE_ASSET,
            ),
        )
        self.assertDictEqual(
            endtoend.testhandle.internal_account_id_to_uploaded_id,
            {"TEST_INTERNAL_NAME_EQUAL_MAX_L": "e2e_A_TEST_INTERNAL_NAME_EQUAL_MAX_L"},
        )

    @patch.dict(
        "inception_sdk.test_framework.endtoend.testhandle.internal_account_id_to_uploaded_id", {}
    )
    def test_create_internal_account_v2_under_length_limit_without_composite_id(
        self,
        mock_create_internal_account: MagicMock,
    ):
        mock_create_internal_account.return_value = sentinel.account
        result = contracts_helper.create_internal_account_v2(
            account_id="TEST_INTERNAL_NAME_EQUAL_MAX_L",
            t_side=AccountV2TSide.T_SIDE_ASSET,
            details={"sentinel": "dict"},
            use_composite_id=False,
        )
        self.assertEqual(result, sentinel.account)
        mock_create_internal_account.assert_called_once_with(
            request_id="TEST_INTERNAL_NAME_EQUAL_MAX_L",
            account=InternalAccountRequestBody(
                id="TEST_INTERNAL_NAME_EQUAL_MAX_L",
                status=AccountV2Status.ACCOUNT_STATUS_OPEN,
                details={"sentinel": "dict"},
                t_side=AccountV2TSide.T_SIDE_ASSET,
            ),
        )
        self.assertDictEqual(
            endtoend.testhandle.internal_account_id_to_uploaded_id,
            {"TEST_INTERNAL_NAME_EQUAL_MAX_L": "TEST_INTERNAL_NAME_EQUAL_MAX_L"},
        )


@patch.dict(
    "inception_sdk.test_framework.endtoend.testhandle.contract_pid_to_uploaded_pid",
    {"product_id": "mapped_product_id"},
)
@patch.object(contracts_helper.uuid, "uuid4", MagicMock(return_value="unique_id"))
@patch.object(endtoend.helper, "send_request")
class CreateAccountTest(TestCase):
    maxDiff = None

    def test_create_account_with_unknown_product_id(self, mock_send_request: MagicMock):
        with self.assertRaises(NameError) as e:
            contracts_helper.create_account(
                customer="customer_id",
                contract="unknown_product_id",
            )

        self.assertIn(
            "Contract ID: unknown_product_id not found. "
            "Is it specified in endtoend.testhandle.CONTRACTS?",
            str(e.exception),
        )

        mock_send_request.assert_not_called()

    def test_create_account_with_unknown_product_id_and_force_id(
        self, mock_send_request: MagicMock
    ):

        contracts_helper.create_account(
            customer="customer_id",
            contract="unknown_product_id",
            force_contract_id=True,
            wait_for_activation=False,
        )

        mock_send_request.assert_called_once_with(
            "post",
            "/v1/accounts",
            data=json.dumps(
                {
                    "request_id": "unique_id",
                    "account": {
                        "product_id": "unknown_product_id",
                        "stakeholder_ids": ["customer_id"],
                        "instance_param_vals": None,
                        "permitted_denominations": ["GBP"],
                        "status": "ACCOUNT_STATUS_OPEN",
                        "details": {"accounts_api_version": "v1"},
                        "opening_timestamp": None,
                    },
                }
            ),
        )

    def test_create_account_with_known_product_id(self, mock_send_request: MagicMock):

        contracts_helper.create_account(
            customer="customer_id",
            contract="product_id",
            wait_for_activation=False,
        )

        mock_send_request.assert_called_once_with(
            "post",
            "/v1/accounts",
            data=json.dumps(
                {
                    "request_id": "unique_id",
                    "account": {
                        "product_id": "mapped_product_id",
                        "stakeholder_ids": ["customer_id"],
                        "instance_param_vals": None,
                        "permitted_denominations": ["GBP"],
                        "status": "ACCOUNT_STATUS_OPEN",
                        "details": {"accounts_api_version": "v1"},
                        "opening_timestamp": None,
                    },
                }
            ),
        )


@patch.dict(
    "inception_sdk.test_framework.endtoend.testhandle.contract_pid_to_uploaded_pid",
    {"product_id": "mapped_product_id"},
)
@patch.dict(
    "inception_sdk.test_framework.endtoend.testhandle.contract_pid_to_uploaded_product_version_id",
    {"product_id": "uploaded_product_version_id"},
)
@patch.object(contracts_helper.uuid, "uuid4", MagicMock(return_value="unique_id"))
@patch.object(endtoend.core_api_helper, "create_customer_account_v2")
class CreateAccountV2Test(TestCase):
    maxDiff = None

    def test_create_account_with_unknown_product_id(
        self, mock_create_customer_account_v2: MagicMock
    ):
        with self.assertRaises(NameError) as e:
            contracts_helper.create_account_v2(
                product_id="unknown_product_id",
                account=sentinel.account,
            )

        self.assertIn(
            "Product ID: unknown_product_id not found. "
            "Is it specified in endtoend.testhandle.CONTRACTS?",
            str(e.exception),
        )

        mock_create_customer_account_v2.assert_not_called()

    def test_create_account_with_known_product_id(self, mock_create_customer_account_v2: MagicMock):

        original_account = core_api.CustomerAccountRequestBody(
            status=core_api.AccountV2Status.ACCOUNT_STATUS_OPEN, stakeholder_ids=["stakeholder_id"]
        )
        amended_account = deepcopy(original_account)
        amended_account.smart_contract_version_id = "uploaded_product_version_id"
        amended_account.details = {"accounts_api_version": "v2"}

        contracts_helper.create_account_v2(product_id="product_id", account=original_account)

        mock_create_customer_account_v2.assert_called_once_with(
            request_id="unique_id", account=amended_account, create_options=None
        )


@patch.dict(
    "inception_sdk.test_framework.endtoend.testhandle."
    "product_version_id_to_uploaded_product_version_id",
    {"product_version_id": "uploaded_product_version_id"},
)
@patch.object(contracts_helper.uuid, "uuid4", MagicMock(return_value="unique_id"))
@patch.object(endtoend.core_api_helper, "create_customer_account_v2")
class CreateAccountV2WithProductVersionIDTest(TestCase):
    maxDiff = None

    def test_create_account_with_unknown_product_id(
        self, mock_create_customer_account_v2: MagicMock
    ):
        with self.assertRaises(NameError) as e:
            contracts_helper.create_account_v2(
                product_version_id="unknown_product_version_id",
                account=sentinel.account,
            )

        self.assertIn(
            "Product version ID: unknown_product_version_id not found. "
            "Is it specified in endtoend.testhandle.PRODUCTS?",
            str(e.exception),
        )

        mock_create_customer_account_v2.assert_not_called()

    def test_create_account_with_known_product_id(self, mock_create_customer_account_v2: MagicMock):

        original_account = core_api.CustomerAccountRequestBody(
            status=core_api.AccountV2Status.ACCOUNT_STATUS_OPEN, stakeholder_ids=["stakeholder_id"]
        )
        amended_account = deepcopy(original_account)
        amended_account.smart_contract_version_id = "uploaded_product_version_id"
        amended_account.details = {"accounts_api_version": "v2"}

        contracts_helper.create_account_v2(
            product_version_id="product_version_id",
            account=original_account,
        )

        mock_create_customer_account_v2.assert_called_once_with(
            request_id="unique_id", account=amended_account, create_options=None
        )


class TestSubstituteE2eIdsOnCreateOptions(TestCase):
    maxDiff = None

    @patch.dict(
        endtoend.testhandle.parameter_resource_id_to_uploaded_id,
        {
            "a": "e2e_a",
            "b": "e2e_b",
            "c": "e2e_c",
        },
    )
    def test_create_options_with_some_supplied_parameter_resource_ids(self):
        actual_result = contracts_helper.substitute_e2e_ids_on_create_options(
            create_options=core_api.CreateOptions(
                parameter_values=dict(
                    a=core_api.AccountIdParameterValue(account_id_value="1"),
                    b=core_api.DatetimeParameterValue(
                        date_time_value=datetime(2222, 2, 2, tzinfo=UTC)
                    ),
                    c=core_api.DecimalParameterValue(decimal_value=Decimal("3.0")),
                    d=core_api.EnumerationParameterValue(enumeration_value="4"),
                    e=core_api.StringParameterValue(string_value="5"),
                )
            ),
        )
        expected_result = core_api.CreateOptions(
            # In the mocked parameter_resource_id_to_uploaded_id only (a), (b), and (c) of the
            # parameter ids were supplied, so parameters (d) and (e) should simply be returned
            # as themselves.
            parameter_values=dict(
                e2e_a=core_api.AccountIdParameterValue(account_id_value="1"),
                e2e_b=core_api.DatetimeParameterValue(
                    date_time_value=datetime(2222, 2, 2, tzinfo=UTC)
                ),
                e2e_c=core_api.DecimalParameterValue(decimal_value=Decimal("3.0")),
                d=core_api.EnumerationParameterValue(enumeration_value="4"),
                e=core_api.StringParameterValue(string_value="5"),
            )
        )

        self.assertEqual(expected_result, actual_result)

    @patch.dict(
        endtoend.testhandle.parameter_resource_id_to_uploaded_id,
        {
            "a": "e2e_a",
            "b": "e2e_b",
            "c": "e2e_c",
        },
    )
    def test_create_options_with_clu_syntax_parameter_resource_ids(self):
        actual_result = contracts_helper.substitute_e2e_ids_on_create_options(
            create_options=core_api.CreateOptions(
                parameter_values={
                    "&{a}": core_api.AccountIdParameterValue(account_id_value="1"),
                    "&{b}": core_api.DatetimeParameterValue(
                        date_time_value=datetime(2222, 2, 2, tzinfo=UTC)
                    ),
                    "c": core_api.DecimalParameterValue(decimal_value=Decimal("3.0")),
                    "d": core_api.EnumerationParameterValue(enumeration_value="4"),
                    "e": core_api.StringParameterValue(string_value="5"),
                }
            ),
        )
        expected_result = core_api.CreateOptions(
            # In the mocked parameter_resource_id_to_uploaded_id only (a), (b), and (c) of the
            # parameter ids were supplied, so parameters (d) and (e) should simply be returned
            # as themselves.
            parameter_values=dict(
                e2e_a=core_api.AccountIdParameterValue(account_id_value="1"),
                e2e_b=core_api.DatetimeParameterValue(
                    date_time_value=datetime(2222, 2, 2, tzinfo=UTC)
                ),
                e2e_c=core_api.DecimalParameterValue(decimal_value=Decimal("3.0")),
                d=core_api.EnumerationParameterValue(enumeration_value="4"),
                e=core_api.StringParameterValue(string_value="5"),
            )
        )

        self.assertEqual(expected_result, actual_result)

    @patch.dict(
        endtoend.testhandle.parameter_resource_id_to_uploaded_id,
        {
            "a": "e2e_a",
            "b": "e2e_b",
            "c": "e2e_c",
        },
    )
    @patch.dict(
        endtoend.testhandle.internal_account_id_to_uploaded_id,
        {
            "1": "e2e_1",
        },
    )
    def test_create_options_with_mapped_account_id_parameters(self):
        actual_result = contracts_helper.substitute_e2e_ids_on_create_options(
            create_options=core_api.CreateOptions(
                parameter_values=dict(
                    a=core_api.AccountIdParameterValue(account_id_value="1"),
                    b=core_api.DatetimeParameterValue(
                        date_time_value=datetime(2222, 2, 2, tzinfo=UTC)
                    ),
                    c=core_api.DecimalParameterValue(decimal_value=Decimal("3.0")),
                    d=core_api.EnumerationParameterValue(enumeration_value="4"),
                    e=core_api.StringParameterValue(string_value="5"),
                )
            ),
        )
        expected_result = core_api.CreateOptions(
            # In the mocked parameter_resource_id_to_uploaded_id only (a), (b), and (c) of the
            # parameter ids were supplied, so parameters (d) and (e) should simply be returned
            # as themselves.
            parameter_values=dict(
                e2e_a=core_api.AccountIdParameterValue(account_id_value="e2e_1"),
                e2e_b=core_api.DatetimeParameterValue(
                    date_time_value=datetime(2222, 2, 2, tzinfo=UTC)
                ),
                e2e_c=core_api.DecimalParameterValue(decimal_value=Decimal("3.0")),
                d=core_api.EnumerationParameterValue(enumeration_value="4"),
                e=core_api.StringParameterValue(string_value="5"),
            )
        )

        self.assertEqual(expected_result, actual_result)

    def test_create_options_none(self):
        actual_result = contracts_helper.substitute_e2e_ids_on_create_options(None)
        expected_result = None
        self.assertEqual(expected_result, actual_result)


@patch.dict(
    endtoend.testhandle.parameter_resource_id_to_uploaded_id,
    {
        "a": "e2e_a",
        "c": "e2e_c",
    },
)
@patch.object(endtoend.core_api_helper, "batch_create_parameter_values")
class TestBatchCreateParameterValues(TestCase):

    def test_batch_create_parameter_values(self, mock_batch_create_parameter_values: MagicMock):
        mock_batch_create_parameter_values.return_value = {}

        input = core_api.BatchCreateParameterValueV1RequestBody(
            request_id="request_1",
            parameter_values=[
                core_api.CreateParameterValueV1ParameterValue(
                    parameter_id="a",
                    value=core_api.StringParameterValue(string_value="1"),
                    effective_from_timestamp=datetime(2024, 1, 1, tzinfo=UTC),
                    cancel_timestamp=datetime(2024, 1, 2, tzinfo=UTC),
                    is_backdated=True,
                    account_id="account_1",
                ),
                core_api.CreateParameterValueV1ParameterValue(
                    parameter_id="b",
                    value=core_api.StringParameterValue(string_value="2"),
                    effective_from_timestamp=datetime(2024, 1, 1, tzinfo=UTC),
                    cancel_timestamp=datetime(2024, 1, 2, tzinfo=UTC),
                    is_backdated=True,
                    account_id="account_1",
                ),
                core_api.CreateParameterValueV1ParameterValue(
                    parameter_id="&{c}",
                    value=core_api.StringParameterValue(string_value="3"),
                    effective_from_timestamp=datetime(2024, 1, 1, tzinfo=UTC),
                    cancel_timestamp=datetime(2024, 1, 2, tzinfo=UTC),
                    is_backdated=True,
                    account_id="account_1",
                ),
            ],
        )
        actual_result = endtoend.contracts_helper.batch_create_parameter_values(
            parameter_values=input
        )
        expected_called_with = deepcopy(input)
        expected_called_with.parameter_values[0].parameter_id = "e2e_a"
        expected_called_with.parameter_values[1].parameter_id = "b"
        expected_called_with.parameter_values[2].parameter_id = "e2e_c"

        mock_batch_create_parameter_values.assert_called_with(expected_called_with)
        self.assertEqual(mock_batch_create_parameter_values.return_value, actual_result)


@patch.object(endtoend.contracts_helper, "_does_internal_account_exist")
@patch.object(endtoend.contracts_helper, "create_internal_account_v2")
class CreateRequiredInternalAccounts(TestCase):
    def setUp(self):
        self.internal_account_id = "internal_account_id"
        self.e2e_composite_id = "e2e_A_" + self.internal_account_id
        self.t_side = AccountV2TSide.T_SIDE_ASSET

        def create_internal_account_v2(
            account_id: str,
            t_side: AccountV2TSide,
            details: dict[str, str] | None = None,
            use_composite_id: bool = True,
        ):
            details = details or {}
            return CreateAccountV2Response(
                id=(
                    endtoend.contracts_helper._composite_internal_account_v2_id(
                        account_id=account_id, t_side=t_side
                    )
                    if use_composite_id
                    else account_id
                ),
                type=AccountV2Type.ACCOUNT_TYPE_INTERNAL,
                smart_contract_version_id="",
                pending_smart_contract_version_id="",
                stakeholder_ids=[],
                alias="",
                status=AccountV2Status.ACCOUNT_STATUS_OPEN,
                vault_create_timestamp=datetime(2024, 1, 1, tzinfo=ZoneInfo("UTC")),
                source_create_timestamp=datetime(2024, 1, 1, tzinfo=ZoneInfo("UTC")),
                source_open_timestamp=None,
                source_close_timestamp=None,
                update_timestamp=None,
                activation_timestamp=datetime(2024, 1, 1, tzinfo=ZoneInfo("UTC")),
                permitted_denominations=["AUD", "NZD"],
                details=details,
                t_side=t_side,
                contract_update_timestamp=None,
                processing_group_id="DEFAULT",
                tranche_id="",
                parameter_value_hierarchy_node_id="",
                processing_label="",
            )

        self.create_internal_account = create_internal_account_v2
        self.default_expected_calls = [
            call(
                account_id=endtoend.contracts_helper.DUMMY_CONTRA,
                t_side=AccountV2TSide.T_SIDE_LIABILITY,
            ),
            call(
                account_id=endtoend.contracts_helper.DEFAULT_REQUIRED_INTERNAL_ACCOUNTS_DICT[
                    AccountV2TSide.T_SIDE_LIABILITY
                ][0],
                t_side=AccountV2TSide.T_SIDE_LIABILITY,
                use_composite_id=False,
            ),
        ]

    def test_existing_account_not_recreated(
        self,
        mock_create_internal_account_v2: MagicMock,
        mock_does_internal_account_exist: MagicMock,
    ):
        mock_create_internal_account_v2.side_effect = self.create_internal_account

        def _does_internal_account_exist(internal_account_id):
            return internal_account_id in [self.internal_account_id, self.e2e_composite_id]

        mock_does_internal_account_exist.side_effect = _does_internal_account_exist
        endtoend.contracts_helper.create_required_internal_accounts(
            {self.t_side: [self.internal_account_id]}
        )
        mock_create_internal_account_v2.assert_has_calls(self.default_expected_calls)

    def test_internal_account_doesnt_exist(
        self, mock_create_internal_account_v2, mock_does_internal_account_exist
    ):
        mock_create_internal_account_v2.side_effect = self.create_internal_account

        def _does_internal_account_exist(internal_account_id):
            return False

        mock_does_internal_account_exist.side_effect = _does_internal_account_exist
        endtoend.contracts_helper.create_required_internal_accounts(
            {self.t_side: [self.internal_account_id]}
        )
        mock_create_internal_account_v2.assert_has_calls(
            [
                call(
                    account_id=self.internal_account_id,
                    t_side=self.t_side,
                ),
            ]
            + self.default_expected_calls
        )

    def test_defaults_always_created(
        self, mock_create_internal_account_v2, mock_does_internal_account_exist
    ):
        mock_create_internal_account_v2.side_effect = self.create_internal_account

        def _does_internal_account_exist(internal_account_id):
            return False

        mock_does_internal_account_exist.side_effect = _does_internal_account_exist
        endtoend.contracts_helper.create_required_internal_accounts(dict())
        mock_create_internal_account_v2.assert_has_calls(self.default_expected_calls)


class PrepareParametersForE2ETest(TestCase):
    parameters = {
        "param_1": "value_1",
        "param_2": "value_2",
        "param_3": {"key_1": "value_1", "key_2": "value_2"},
    }

    def test_handle_internal_account_parameters(self):
        self.assertDictEqual(
            prepare_parameters_for_e2e(
                parameters=self.parameters,
                internal_account_param_mapping={"param_1": "e2e_value_1"},
            ),
            {
                "param_1": {"internal_account_key": "e2e_value_1"},
                "param_2": "value_2",
                "param_3": {"key_1": "value_1", "key_2": "value_2"},
            },
        )

    def test_handle_flag_parameters(self):
        self.assertDictEqual(
            prepare_parameters_for_e2e(
                parameters=self.parameters,
                flag_param_mapping={"param_2": ["e2e_value_2"]},
            ),
            {
                "param_1": "value_1",
                "param_2": {"flag_key": ["e2e_value_2"]},
                "param_3": {"key_1": "value_1", "key_2": "value_2"},
            },
        )

    def test_handle_nested_internal_account_parameters(self):
        self.assertDictEqual(
            prepare_parameters_for_e2e(
                parameters=self.parameters,
                nested_internal_account_param_mapping={
                    "param_3": {"key_1": "e2e_value_1", "key_2": "e2e_value_2"}
                },
            ),
            {
                "param_1": "value_1",
                "param_2": "value_2",
                "param_3": {
                    "nested_internal_account_keys": {
                        "key_1": {"internal_account_key": "e2e_value_1"},
                        "key_2": {"internal_account_key": "e2e_value_2"},
                    }
                },
            },
        )

    def test_handle_mixture_of_parameters(self):
        self.assertDictEqual(
            prepare_parameters_for_e2e(
                parameters=self.parameters,
                internal_account_param_mapping={"param_1": "e2e_value_1"},
                nested_internal_account_param_mapping={
                    "param_3": {"key_1": "e2e_value_1", "key_2": "e2e_value_2"}
                },
                flag_param_mapping={"param_2": ["e2e_value_2"]},
            ),
            {
                "param_1": {"internal_account_key": "e2e_value_1"},
                "param_2": {"flag_key": ["e2e_value_2"]},
                "param_3": {
                    "nested_internal_account_keys": {
                        "key_1": {"internal_account_key": "e2e_value_1"},
                        "key_2": {"internal_account_key": "e2e_value_2"},
                    }
                },
            },
        )


class CreateParameterDefinitionsTest(TestCase):
    @patch.object(endtoend.core_api_helper, "create_parameter_resource")
    def test_create_single_parameter_resource(
        self,
        mock_create_parameter_resource: MagicMock,
    ):
        # construct values
        parameter_resource = ParameterResource(
            id="some_parameter",
            constraint=StringConstraint(string_constraint=StringConstraintValue()),
        )

        # run function
        contracts_helper.create_parameter_definitions([parameter_resource])

        # assertions
        mock_create_parameter_resource.assert_called_once_with(
            CreateParameterResourceV1RequestBody(
                request_id=parameter_resource.id,
                parameter=parameter_resource,
            )
        )

    @patch.object(endtoend.core_api_helper, "create_parameter_resource")
    def test_create_multiple_parameter_resource(
        self,
        mock_create_parameter_resource: MagicMock,
    ):
        # construct values
        mock_create_parameter_resource.return_value = None
        parameter_resources = [
            ParameterResource(
                id="account_parameter_id",
                constraint=AccountConstraint(account_constraint=AccountConstraintValue()),
            ),
            ParameterResource(
                id="decimal_parameter_id",
                constraint=DecimalConstraint(decimal_constraint=DecimalConstraintValue()),
            ),
        ]

        # run function
        contracts_helper.create_parameter_definitions(parameter_resources)

        # assertions
        mock_create_parameter_resource.assert_has_calls(
            calls=[
                call(
                    CreateParameterResourceV1RequestBody(
                        request_id=p.id,
                        parameter=p,
                    ),
                )
                for p in parameter_resources
            ]
        )


@patch.dict(
    endtoend.testhandle.parameter_resource_id_to_uploaded_id,
    {"param_id_1": "e2e_param_id_1", "param_id_2": "e2e_param_id_2"},
)
@patch.object(endtoend.core_api_helper, "batch_get_parameter_resources")
class BatchGetParameter(TestCase):
    def test_batch_get_parameter(self, mock_batch_get_parameter_resources: MagicMock):
        contracts_helper.batch_get_parameter_resources(ids=["&{param_id_1}", "param_id_2"])
        mock_batch_get_parameter_resources.assert_called_once_with(
            ["e2e_param_id_1", "e2e_param_id_2"]
        )


@patch.dict(
    endtoend.testhandle.parameter_resource_id_to_uploaded_id,
    {"param_id_1": "e2e_param_id_1", "param_id_2": "e2e_param_id_2"},
)
@patch.object(endtoend.core_api_helper, "get_parameter_values")
class BatchGetParameterValues(TestCase):
    def test_get_parameter_values(self, mock_get_parameter_values: MagicMock):
        mock_get_parameter_values.return_value = sentinel.result
        result = contracts_helper.get_parameter_values(
            parameter_ids=["&{param_id_1}", "param_id_2"], account_ids=["account_id"]
        )
        mock_get_parameter_values.assert_called_once_with(
            parameter_ids=["e2e_param_id_1", "e2e_param_id_2"],
            account_ids=["account_id"],
            effective_timestamp_range_from=None,
            effective_timestamp_range_to=None,
        )
        self.assertEqual(result, sentinel.result)


@patch.dict(
    endtoend.testhandle.flag_definition_id_mapping,
    {"my_flag_definition_id": "e2e_flag_definition_id"},
)
@patch.object(endtoend.core_api_helper, "create_flag")
class CreateFlagTest(TestCase):
    def test_create_flag_account_level(self, mock_create_flag: MagicMock):
        contracts_helper.create_flag(
            flag_definition_id="my_flag_definition_id",
            account_id=sentinel.account_id,
        )
        mock_create_flag.assert_called_once_with(
            flag_name="e2e_flag_definition_id",
            account_id=sentinel.account_id,
            description=None,
            effective_timestamp=None,
            expiry_timestamp=None,
            is_backdated=None,
            value=contracts_helper.FlagV1FlagValue.FLAG_VALUE_ON,
        )

    def test_create_flag_customer_level(self, mock_create_flag: MagicMock):
        contracts_helper.create_flag(
            flag_definition_id="my_flag_definition_id",
            customer_id=sentinel.customer_id,
        )
        mock_create_flag.assert_called_once_with(
            flag_name="e2e_flag_definition_id",
            customer_id=sentinel.customer_id,
            description=None,
            effective_timestamp=None,
            expiry_timestamp=None,
            is_backdated=None,
            value=contracts_helper.FlagV1FlagValue.FLAG_VALUE_ON,
        )

    def test_create_flag_payment_device_level(self, mock_create_flag: MagicMock):
        contracts_helper.create_flag(
            flag_definition_id="my_flag_definition_id",
            payment_device_id=sentinel.payment_device_id,
        )
        mock_create_flag.assert_called_once_with(
            flag_name="e2e_flag_definition_id",
            payment_device_id=sentinel.payment_device_id,
            description=None,
            effective_timestamp=None,
            expiry_timestamp=None,
            is_backdated=None,
            value=contracts_helper.FlagV1FlagValue.FLAG_VALUE_ON,
        )

    def test_create_flag_no_defaults(self, mock_create_flag: MagicMock):
        contracts_helper.create_flag(
            flag_definition_id="my_flag_definition_id",
            payment_device_id=sentinel.payment_device_id,
            description=sentinel.description,
            effective_timestamp=sentinel.effective_timestamp,
            expiry_timestamp=sentinel.expiry_timestamp,
            is_backdated=sentinel.is_backdated,
            value=sentinel.value,
        )
        mock_create_flag.assert_called_once_with(
            flag_name="e2e_flag_definition_id",
            payment_device_id=sentinel.payment_device_id,
            description=sentinel.description,
            effective_timestamp=sentinel.effective_timestamp,
            expiry_timestamp=sentinel.expiry_timestamp,
            is_backdated=sentinel.is_backdated,
            value=sentinel.value,
        )


@patch.object(endtoend.helper, "list_resources")
@patch.dict(
    endtoend.testhandle.flag_definition_id_mapping,
    {"my_flag_definition_id": "e2e_flag_definition_id"},
)
class GetFlagTest(TestCase):
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
                value=contracts_helper.FlagV1FlagValue.FLAG_VALUE_ON.value,
            )
            for i in account_ids
        ]
        flag_name = "my_flag_definition_id"
        effective_timestamp_range_from = datetime(2024, 1, 1, tzinfo=ZoneInfo("UTC"))
        effective_timestamp_range_to = datetime(2024, 1, 2, tzinfo=ZoneInfo("UTC"))
        flag = endtoend.contracts_helper.get_flag(
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
        self.assertEqual(flag, mock_list_resources.return_value)


class BatchGetProducts(TestCase):

    @patch.dict(
        endtoend.testhandle.contract_pid_to_uploaded_pid,
        {"my_product_id": "e2e_product_id"},
    )
    @patch.object(endtoend.core_api_helper, "batch_get_products")
    def test_ids_mapped_correctly(self, mock_batch_get_products: MagicMock):
        mock_batch_get_products.return_value = core_api.BatchGetProductsResponse(
            products={
                "e2e_product_id": core_api.Product(
                    id="e2e_product_id",
                    display_name="name",
                    is_internal=False,
                    current_version_id="123",
                )
            }
        )
        response = contracts_helper.batch_get_products(
            core_api.BatchGetProductsRequest(ids=["my_product_id"])
        )
        self.assertEqual(
            response,
            core_api.BatchGetProductsResponse(
                products={
                    # both occurrences of id should be mapped, nothing else
                    "my_product_id": core_api.Product(
                        id="my_product_id",
                        display_name="name",
                        is_internal=False,
                        current_version_id="123",
                    )
                }
            ),
        )
        # request product ids should be mapped too
        mock_batch_get_products.assert_called_once_with(
            core_api.BatchGetProductsRequest(ids=["e2e_product_id"])
        )

    @patch.object(endtoend.core_api_helper, "batch_get_products")
    def test_request_product_id_not_in_mapping_raises(self, mock_batch_get_products: MagicMock):
        # as the testhandle dict is not patched, it is empty so no product ids should be accepted
        with self.assertRaises(ValueError):
            contracts_helper.batch_get_products(
                core_api.BatchGetProductsRequest(ids=["my_product_id"])
            )
        mock_batch_get_products.assert_not_called()

    @patch.dict(
        endtoend.testhandle.contract_pid_to_uploaded_pid,
        {"my_product_id": "e2e_product_id"},
    )
    @patch.object(endtoend.core_api_helper, "batch_get_products")
    def test_response_product_id_not_in_mapping_raises(self, mock_batch_get_products: MagicMock):
        mock_batch_get_products.return_value = core_api.BatchGetProductsResponse(
            products={
                "random_id": core_api.Product(
                    id="random_id",
                    display_name="name",
                    is_internal=False,
                    current_version_id="123",
                )
            }
        )
        with self.assertRaises(ValueError):
            contracts_helper.batch_get_products(
                core_api.BatchGetProductsRequest(ids=["my_product_id"])
            )


class SanitiseTemplateParams(TestCase):

    def test_none_params_returns_empty_dict(self):
        self.assertEquals(contracts_helper.sanitise_template_parameters(None), {})

    def test_empty_params_returns_empty_dict(self):
        self.assertEquals(contracts_helper.sanitise_template_parameters({}), {})

    def test_empty_mappings_returns_same_input(self):
        self.assertEquals(
            contracts_helper.sanitise_template_parameters(sentinel.input), sentinel.input
        )

    def test_map_internal_account(self):
        self.assertEquals(
            contracts_helper.sanitise_template_parameters(
                parameters={"my_param": {"internal_account_key": "internal_account_1"}},
                internal_account_id_to_uploaded_id={
                    "internal_account_1": "mapped_internal_account_1"
                },
            ),
            {"my_param": "mapped_internal_account_1"},
        )

    def test_map_nested_internal_account(self):
        self.assertEquals(
            contracts_helper.sanitise_template_parameters(
                parameters={
                    "my_param": {
                        "nested_internal_account_keys": {
                            "key_1": {"internal_account_key": "internal_account_1"},
                            "key_2": {"internal_account_key": "internal_account_2"},
                        }
                    }
                },
                internal_account_id_to_uploaded_id={
                    "internal_account_1": "mapped_internal_account_1",
                    "internal_account_2": "mapped_internal_account_2",
                },
            ),
            {
                "my_param": json.dumps(
                    {"key_1": "mapped_internal_account_1", "key_2": "mapped_internal_account_2"}
                )
            },
        )

    def test_map_list_of_flag_definitions(self):
        self.assertEquals(
            contracts_helper.sanitise_template_parameters(
                parameters={"my_param": {"flag_key": ["flag_id", "flag_id_2"]}},
                flag_definition_id_mapping={
                    "flag_id": "mapped_flag_id",
                    "flag_id_2": "mapped_flag_id_2",
                },
            ),
            {"my_param": json.dumps(["mapped_flag_id", "mapped_flag_id_2"])},
        )

    def test_map_map_of_flag_definitions(self):
        self.assertEquals(
            contracts_helper.sanitise_template_parameters(
                parameters={"my_param": {"flag_key": {"flag_id": "xyz", "flag_id_2": "abc"}}},
                flag_definition_id_mapping={
                    "flag_id": "mapped_flag_id",
                    "flag_id_2": "mapped_flag_id_2",
                },
            ),
            {"my_param": json.dumps({"mapped_flag_id": "xyz", "mapped_flag_id_2": "abc"})},
        )
