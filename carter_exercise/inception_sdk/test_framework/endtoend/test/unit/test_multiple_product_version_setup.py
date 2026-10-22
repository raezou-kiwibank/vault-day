# standard libs
import unittest
from unittest.mock import MagicMock, patch, sentinel

# inception sdk
import inception_sdk.test_framework.endtoend as endtoend


class TestMultipleProductVersionSetup(unittest.TestCase):
    @patch("inception_sdk.test_framework.endtoend.core_api_helper.init_postings_api_client")
    @patch("inception_sdk.test_framework.endtoend.contracts_helper.upload_contracts_from_products")
    @patch("inception_sdk.test_framework.endtoend.set_e2e_ids")
    @patch("inception_sdk.test_framework.endtoend.extract_parameters")
    @patch(
        "inception_sdk.test_framework.endtoend.contracts_helper.create_required_internal_accounts"
    )
    @patch("inception_sdk.test_framework.endtoend.contracts_helper.create_calendars")
    @patch("inception_sdk.test_framework.endtoend.contracts_helper.create_flag_definitions")
    @patch("inception_sdk.test_framework.endtoend.contracts_helper.create_account_schedule_tags")
    def test_setup_orchestration(
        self,
        mock_create_account_schedule_tags,
        mock_create_flag_definitions,
        mock_create_calendars,
        mock_create_required_internal_accounts,
        mock_extract_parameters,
        mock_set_e2e_ids,
        mock_upload_contracts_from_products,
        mock_init_postings_api_client,
    ):
        # GIVEN: A mock product setup
        endtoend.testhandle.PRODUCTS = [sentinel.product]
        endtoend.testhandle.FLAG_DEFINITIONS = sentinel.flag_definitions
        endtoend.testhandle.CALENDARS = sentinel.calendars
        endtoend.testhandle.TSIDE_TO_INTERNAL_ACCOUNT_ID = sentinel.tside_to_internal_account_id
        mock_parameter = MagicMock(id="param_id")
        mock_e2e_parameter = MagicMock(id="e2e_param_id")
        mock_extract_parameters.return_value = [mock_parameter]
        mock_set_e2e_ids.return_value = [mock_e2e_parameter]

        # WHEN: Executing the new setup helper
        endtoend.standard_setup_with_multiple_product_versions()

        # THEN: Verify account schedule tags created
        mock_create_account_schedule_tags.assert_called_once()

        # THEN: Verify flags, calendars and internal accounts
        mock_create_flag_definitions.assert_called_with(sentinel.flag_definitions)
        mock_create_calendars.assert_called_with(sentinel.calendars)
        mock_create_required_internal_accounts.assert_called_with(
            sentinel.tside_to_internal_account_id
        )

        # THEN: Verify parameters handled
        mock_extract_parameters.assert_called_once()
        mock_set_e2e_ids.assert_called_once_with([mock_parameter])

        # THEN: Verify the specific multi-product upload is triggered
        mock_upload_contracts_from_products.assert_called_once_with(
            [sentinel.product], [mock_e2e_parameter]
        )

        # THEN: Verify postings api client initialised
        mock_init_postings_api_client.assert_called_once()

    @patch("inception_sdk.test_framework.endtoend.helper.teardown_shared_resources")
    @patch("inception_sdk.test_framework.endtoend.contracts_helper.create_account_schedule_tags")
    def test_setup_runs_teardown_if_error(
        self,
        mock_create_account_schedule_tags,
        mock_teardown_shared_resources,
    ):
        # GIVEN: A mock product setup to raise error
        mock_create_account_schedule_tags.side_effect = Exception("Unknown")

        # WHEN: Executing the standard setup helper
        with self.assertRaises(Exception) as ctx:
            endtoend.standard_setup_with_multiple_product_versions()

        # THEN: Verify teardown called
        mock_teardown_shared_resources.assert_called_once()

        # THEN: The original error is raised
        self.assertEqual(ctx.exception.args[0], "Unknown")
