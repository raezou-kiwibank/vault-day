# Copyright @ 2024 Thought Machine Group Limited. All rights reserved.
# standard libs
import json
from datetime import datetime
from unittest import TestCase
from unittest.mock import MagicMock, Mock, call, patch, sentinel
from zoneinfo import ZoneInfo

# third party
from requests import HTTPError, JSONDecodeError, Response

# inception sdk
import inception_sdk.test_framework.contracts.simulation.vault_caller as vault_caller
import inception_sdk.vault.core_api as core_api

UTC = ZoneInfo("UTC")


class TestVaultException(TestCase):
    def test_vault_exception_init(self):
        exception = vault_caller.VaultException(
            vault_error_code=sentinel.vault_error_code,
            message=sentinel.message,
            details=[sentinel.details],
        )
        self.assertEqual(exception.vault_error_code, sentinel.vault_error_code)
        self.assertEqual(exception.message, sentinel.message)
        self.assertEqual(exception.details, [sentinel.details])

    def test_vault_exception_init_no_details(self):
        # Omitted details (defaults to None)
        exception = vault_caller.VaultException(
            vault_error_code=sentinel.vault_error_code,
            message=sentinel.message,
        )
        self.assertEqual(exception.vault_error_code, sentinel.vault_error_code)
        self.assertEqual(exception.message, sentinel.message)
        self.assertEqual(exception.details, [])

    def test_vault_exception_str(self):
        exception = vault_caller.VaultException(
            vault_error_code=sentinel.E1, message=sentinel.M1, details=[sentinel.D1]
        )
        expected_str = (
            "An exception was raised inside Vault:\nError Code: sentinel.E1\n"
            "Message:\nsentinel.M1\nDetails:\n[sentinel.D1]\n"
        )
        self.assertEqual(str(exception), expected_str)

    def test_vault_exception_repr(self):
        exception = vault_caller.VaultException(
            vault_error_code=sentinel.E1, message=sentinel.M1, details=[sentinel.D1]
        )
        expected_repr = (
            "VaultException(vault_error_code=sentinel.E1, message=sentinel.M1, "
            "details=[sentinel.D1])"
        )
        self.assertEqual(repr(exception), expected_repr)

    def test_vault_exception_repr_no_details(self):
        exception = vault_caller.VaultException(sentinel.E1, sentinel.M1)
        self.assertEqual(
            repr(exception),
            "VaultException(vault_error_code=sentinel.E1, message=sentinel.M1, details=[])",
        )

    def test_vault_exception_eq(self):
        exception1 = vault_caller.VaultException(
            vault_error_code=sentinel.E1, message=sentinel.M1, details=[sentinel.D1]
        )
        exception2 = vault_caller.VaultException(
            vault_error_code=sentinel.E1, message=sentinel.M1, details=[sentinel.D1]
        )
        exception3 = vault_caller.VaultException(
            vault_error_code=sentinel.E2, message=sentinel.M1, details=[sentinel.D1]
        )
        exception4 = vault_caller.VaultException(
            vault_error_code=sentinel.E1, message=sentinel.M2, details=[sentinel.D1]
        )
        exception5 = vault_caller.VaultException(
            vault_error_code=sentinel.E1, message=sentinel.M1, details=[sentinel.D2]
        )
        # Check equality when all fields (vault_error_code, message, details) match
        self.assertEqual(exception1, exception2)

        # Check inequality when the vault_error_code differs
        self.assertNotEqual(exception1, exception3)

        # Check inequality when the message differs
        self.assertNotEqual(exception1, exception4)

        # Check inequality when the details differ
        self.assertNotEqual(exception1, exception5)

        # Check inequality when compared against an entirely different type
        self.assertNotEqual(exception1, sentinel.something_else)


@patch("inception_sdk.test_framework.contracts.simulation.vault_caller.requests.Session")
class TestClientErrorHandling(TestCase):
    def test_simulator_response_error(self, mock_Session: MagicMock):
        response = MagicMock(
            name="mock_Response",
            spec=Response,
            raise_for_status=MagicMock(side_effect=HTTPError),
            json=MagicMock(side_effect=lambda: {}),
        )
        mock_Session.side_effect = lambda: MagicMock(
            name="mock_session", post=MagicMock(return_value=response)
        )

        with self.assertRaisesRegexp(ValueError, r"Unhandled simulator response"):
            vault_caller.Client(
                environment=MagicMock(name="mock_environment")
            ).simulate_smart_contract(
                start_timestamp=datetime(2020, 1, 1, tzinfo=ZoneInfo("UTC")),
                end_timestamp=datetime(2020, 1, 2, tzinfo=ZoneInfo("UTC")),
                events=[],
            )

    def test_simulator_response_error_with_vault_error(self, mock_Session: MagicMock):
        response = MagicMock(
            name="mock_Response",
            spec=Response,
            raise_for_status=MagicMock(side_effect=HTTPError),
            json=MagicMock(
                side_effect=lambda: {
                    "vault_error_code": sentinel.vault_error_code,
                    "message": sentinel.message,
                }
            ),
        )
        mock_Session.side_effect = lambda: MagicMock(
            name="mock_session", post=MagicMock(return_value=response)
        )

        with self.assertRaises(vault_caller.VaultException):
            vault_caller.Client(
                environment=MagicMock(name="mock_environment")
            ).simulate_smart_contract(
                start_timestamp=datetime(2020, 1, 1, tzinfo=ZoneInfo("UTC")),
                end_timestamp=datetime(2020, 1, 2, tzinfo=ZoneInfo("UTC")),
                events=[],
            )

    def test_simulator_response_error_with_invalid_json(self, mock_Session: MagicMock):
        def error_raiser():
            raise JSONDecodeError(sentinel.msg, "", 0)

        response = MagicMock(
            name="mock_Response",
            spec=Response,
            raise_for_status=MagicMock(side_effect=HTTPError),
            json=MagicMock(side_effect=error_raiser),
        )
        mock_Session.side_effect = lambda: MagicMock(
            name="mock_session", post=MagicMock(return_value=response)
        )

        with self.assertRaises(JSONDecodeError):
            vault_caller.Client(
                environment=MagicMock(name="mock_environment")
            ).simulate_smart_contract(
                start_timestamp=datetime(2020, 1, 1, tzinfo=ZoneInfo("UTC")),
                end_timestamp=datetime(2020, 1, 2, tzinfo=ZoneInfo("UTC")),
                events=[],
            )

    def test_simulator_response_ok_but_error_message_in_stream(self, mock_Session: MagicMock):
        response = MagicMock(
            name="mock_Response",
            spec=Response,
            raise_for_status=MagicMock(),
            iter_lines=MagicMock(
                return_value=[
                    json.dumps(
                        {
                            "vault_error_code": "000.000.000",
                            "message": "error_message",
                            "error": "error",
                        }
                    )
                ]
            ),
        )
        mock_Session.side_effect = lambda: MagicMock(
            name="mock_session", post=MagicMock(return_value=response)
        )

        with self.assertRaises(vault_caller.VaultException) as ctx:
            vault_caller.Client(
                environment=MagicMock(name="mock_environment")
            ).simulate_smart_contract(
                start_timestamp=datetime(2020, 1, 1, tzinfo=ZoneInfo("UTC")),
                end_timestamp=datetime(2020, 1, 2, tzinfo=ZoneInfo("UTC")),
                events=[],
            )
        self.assertEqual(
            ctx.exception,
            vault_caller.VaultException(vault_error_code="000.000.000", message="error_message"),
        )


class TestHelper(TestCase):
    def test_smart_contract_to_json_accepted(self):
        expected_output = [
            {
                "code": "code_1",
                "smart_contract_param_vals": {"1": "1"},
                "smart_contract_version_id": "version_1",
            },
            {
                "code": "code_2",
                "smart_contract_param_vals": {"2": "2"},
                "smart_contract_version_id": "version_2",
            },
            {
                "code": "code_3",
                "smart_contract_param_vals": {"3": "3"},
                "smart_contract_version_id": "version_3",
            },
        ]
        result = vault_caller._smart_contract_to_json(
            contract_codes=["code_1", "code_2", "code_3"],
            templates_parameters=[{"1": "1"}, {"2": "2"}, {"3": "3"}],
            smart_contract_version_ids=["version_1", "version_2", "version_3"],
        )
        self.assertEqual(expected_output, result)

    def test_smart_contract_to_json_accepted_empty_len(self):
        expected_output = []
        result = vault_caller._smart_contract_to_json(
            contract_codes=[], templates_parameters=[], smart_contract_version_ids=[]
        )
        self.assertEqual(expected_output, result)

    def test_smart_contract_to_json_rejected_incorrect_code_len(self):
        expected_output = (
            "The length of contract_codes, templates_parameters "
            + "and smart_contract_version_ids must be equal."
        )
        with self.assertRaises(ValueError) as e:
            vault_caller._smart_contract_to_json(
                contract_codes=[
                    "code_1",
                ],
                templates_parameters=[{"1": "1"}, {"2": "2"}, {"3": "3"}],
                smart_contract_version_ids=["version_1", "version_2", "version_3"],
            )

        self.assertEqual(str(e.exception), expected_output)

    def test_smart_contract_to_json_rejected_incorrect_param_len(self):
        expected_output = (
            "The length of contract_codes, templates_parameters "
            + "and smart_contract_version_ids must be equal."
        )
        with self.assertRaises(ValueError) as e:
            vault_caller._smart_contract_to_json(
                contract_codes=["code_1", "code_2", "code_3"],
                templates_parameters=[{"1": "1"}, {"2": "2"}, {"3": "3"}, {"4": "4"}],
                smart_contract_version_ids=["version_1", "version_2", "version_3"],
            )

        self.assertEqual(str(e.exception), expected_output)

    def test_smart_contract_to_json_rejected_incorrect_version_len(self):
        expected_output = (
            "The length of contract_codes, templates_parameters "
            + "and smart_contract_version_ids must be equal."
        )
        with self.assertRaises(ValueError) as e:
            vault_caller._smart_contract_to_json(
                contract_codes=[],
                templates_parameters=[],
                smart_contract_version_ids=["version_1", "version_2", "version_3"],
            )

        self.assertEqual(str(e.exception), expected_output)

    @patch.object(vault_caller, "replace_clu_dependencies")
    @patch.object(vault_caller.utils, "get_contract_required_parameter_resources")
    @patch.object(vault_caller, "create_parameter")
    @patch.object(vault_caller, "_create_smart_contract_module_links")
    @patch.object(vault_caller, "_datetime_to_rfc_3339")
    @patch.object(vault_caller, "_smart_contract_to_json")
    @patch.object(vault_caller, "_supervisor_contract_to_json")
    @patch.object(vault_caller, "_event_to_json")
    @patch.object(vault_caller, "create_derived_parameters_instructions")
    @patch.object(vault_caller.Client, "_api_post")
    def test_simulator_create_parameter_creation_with_duplicates(
        self,
        mock_api_post: MagicMock,
        mock_create_derived_parameters_instructions: MagicMock,
        mock_event_to_json: MagicMock,
        mock_supervisor_contract_to_json: MagicMock,
        mock_smart_contract_to_json: MagicMock,
        mock_datetime_to_rfc_3339: MagicMock,
        mock_create_smart_contract_module_links: MagicMock,
        mock_create_parameter: MagicMock,
        mock_get_contract_required_parameter_resources: MagicMock,
        mock_replace_clu_dependencies: MagicMock,
    ):
        adjusted_start_timestamp = datetime(2019, 12, 31, 23, 59, 59, tzinfo=ZoneInfo("UTC"))
        end_timestamp = datetime(2020, 1, 2, tzinfo=ZoneInfo("UTC"))
        repeated_parameter_id = "new_string_param_test"
        another_create_parameter_id = "another_create_parameter_id"
        final_contract_codes = ["modified contract code"]
        smart_contract_version_ids = ["1"]
        templates_parameters: list[dict[str, str]] | None = [{}]
        repeated_parameter_resource = core_api.ParameterResource(
            id=repeated_parameter_id,
            constraint=core_api.StringConstraint(
                string_constraint=core_api.StringConstraintValue(min_length=1, max_length=100)
            ),
        )

        another_create_parameter_resource = core_api.ParameterResource(
            id=another_create_parameter_id,
            constraint=core_api.StringConstraint(
                string_constraint=core_api.StringConstraintValue(min_length=1, max_length=100)
            ),
        )
        parameters = [
            repeated_parameter_resource,
            repeated_parameter_resource,
            repeated_parameter_resource,
            # Will be created since its part of an SC
            another_create_parameter_resource,
            # Will not be created not part of any SC.
            core_api.ParameterResource(
                id="not_created_parameter_id",
                constraint=core_api.StringConstraint(
                    string_constraint=core_api.StringConstraintValue(min_length=1, max_length=100)
                ),
            ),
        ]
        # The mocks below do not matter for this test
        mock_api_post.return_value = []
        mock_create_derived_parameters_instructions.return_value = []
        mock_event_to_json.return_value = {}
        mock_supervisor_contract_to_json.return_value = ""
        mock_smart_contract_to_json.return_value = []
        mock_datetime_to_rfc_3339.return_value = adjusted_start_timestamp
        mock_create_smart_contract_module_links.return_value = ([], [])
        mock_create_parameter.return_value = None

        # The mocks below will affect our test
        mock_get_contract_required_parameter_resources.return_value = [
            repeated_parameter_resource,
            another_create_parameter_resource,
        ]
        mock_replace_clu_dependencies.side_effect = final_contract_codes

        vault_caller.Client(environment=MagicMock(name="mock_environment")).simulate_smart_contract(
            start_timestamp=datetime(2020, 1, 1, tzinfo=ZoneInfo("UTC")),
            end_timestamp=end_timestamp,
            events=[],
            parameters=parameters,
            contract_codes=[
                "from contracts_api import ExpectedParameter \n"
                "version = '1.0.0'\n"
                "api = '4.0.0'\n"
                f"expected_parameters = [ "
                f"ExpectedParameter(id='{repeated_parameter_resource.id}'),  "
                f"ExpectedParameter(id='{another_create_parameter_resource.id}')"
                "]"
            ],
            smart_contract_version_ids=smart_contract_version_ids,
            templates_parameters=templates_parameters,
        )
        self.assertEqual(mock_create_parameter.call_count, 2)
        # Create parameter must be called before start_timestamp so its -1 second
        mock_create_parameter.assert_has_calls(
            [
                call(
                    adjusted_start_timestamp,
                    repeated_parameter_resource,
                ),
                call(
                    adjusted_start_timestamp,
                    another_create_parameter_resource,
                ),
            ]
        )
        mock_datetime_to_rfc_3339.assert_has_calls(
            [call(adjusted_start_timestamp), call(end_timestamp)]
        )
        # Must verify that replace_clu_dependencies has modified the original SC
        mock_smart_contract_to_json.assert_called_once_with(
            final_contract_codes, [{}], smart_contract_version_ids
        )

    @patch.object(vault_caller, "replace_clu_dependencies")
    @patch.object(vault_caller.utils, "get_contract_required_parameter_resources")
    @patch.object(vault_caller, "create_parameter")
    @patch.object(vault_caller, "_create_smart_contract_module_links")
    @patch.object(vault_caller, "_datetime_to_rfc_3339")
    @patch.object(vault_caller, "_smart_contract_to_json")
    @patch.object(vault_caller, "_supervisor_contract_to_json")
    @patch.object(vault_caller, "_event_to_json")
    @patch.object(vault_caller, "create_derived_parameters_instructions")
    @patch.object(vault_caller.Client, "_api_post")
    def test_simulator_no_parameters_created(
        self,
        mock_api_post: MagicMock,
        mock_create_derived_parameters_instructions: MagicMock,
        mock_event_to_json: MagicMock,
        mock_supervisor_contract_to_json: MagicMock,
        mock_smart_contract_to_json: MagicMock,
        mock_datetime_to_rfc_3339: MagicMock,
        mock_create_smart_contract_module_links: MagicMock,
        mock_create_parameter: MagicMock,
        mock_get_contract_required_parameter_resources: MagicMock,
        mock_replace_clu_dependencies: MagicMock,
    ):
        start_timestamp = datetime(2020, 1, 1, tzinfo=ZoneInfo("UTC"))
        end_timestamp = datetime(2020, 1, 2, tzinfo=ZoneInfo("UTC"))
        final_contract_codes = ["modified contract code"]
        smart_contract_version_ids = ["1"]
        templates_parameters: list[dict[str, str]] | None = [{}]
        # The mocks below do not matter for this test
        mock_api_post.return_value = []
        mock_create_derived_parameters_instructions.return_value = []
        mock_event_to_json.return_value = {}
        mock_supervisor_contract_to_json.return_value = ""
        mock_smart_contract_to_json.return_value = []
        mock_datetime_to_rfc_3339.return_value = start_timestamp
        mock_create_smart_contract_module_links.return_value = ([], [])
        mock_create_parameter.return_value = None

        # The mocks below will affect our test
        mock_get_contract_required_parameter_resources.return_value = []
        mock_replace_clu_dependencies.side_effect = final_contract_codes

        vault_caller.Client(environment=MagicMock(name="mock_environment")).simulate_smart_contract(
            start_timestamp=start_timestamp,
            end_timestamp=end_timestamp,
            events=[],
            parameters=[],
            contract_codes=[
                "from contracts_api import ExpectedParameter \n"
                "version = '1.0.0'\n"
                "api = '4.0.0'\n"
                "expected_parameters = []"
            ],
            smart_contract_version_ids=smart_contract_version_ids,
            templates_parameters=templates_parameters,
        )
        mock_create_parameter.assert_not_called()
        # Must have the same start_timestamp since no parameter was created
        mock_datetime_to_rfc_3339.assert_has_calls([call(start_timestamp), call(end_timestamp)])
        # Must verify that replace_clu_dependencies has modified the original SC
        mock_smart_contract_to_json.assert_called_once_with(
            final_contract_codes, [{}], smart_contract_version_ids
        )


class SimulationVaultCallerTest(TestCase):
    @patch("inception_sdk.test_framework.contracts.simulation.vault_caller._event_to_json")
    @patch(
        "inception_sdk.test_framework.contracts.simulation.vault_caller"
        "._create_smart_contract_module_links"
    )
    @patch("inception_sdk.test_framework.contracts.simulation.vault_caller.update_pgtz_instruction")
    @patch("inception_sdk.test_framework.contracts.simulation.vault_caller._datetime_to_rfc_3339")
    def test_simulate_smart_contract_instruction_ordering(
        self,
        mock_datetime_to_rfc_3339,
        mock_update_pgtz_instruction,
        mock_create_smart_contract_module_links,
        mock_event_to_json,
    ):
        mock_datetime_to_rfc_3339.return_value = "2023-01-01T00:00:00Z"
        mock_update_pgtz_instruction.return_value = sentinel.pgtz_event
        # This will be added to default_events
        mock_create_smart_contract_module_links.return_value = ([sentinel.default_event], [])
        mock_event_to_json.side_effect = lambda x: f"json_{x}"

        # Mock Client environment and _api_post
        mock_env = Mock()
        mock_env.core_api_url = "http://vault"
        mock_env.auth_headers.return_value = {}
        client = vault_caller.Client(environment=mock_env)
        client._api_post = Mock()

        # Call simulate_smart_contract
        start_ts = datetime(2023, 1, 1, tzinfo=ZoneInfo("UTC"))
        end_ts = datetime(2023, 1, 2, tzinfo=ZoneInfo("UTC"))
        events = [sentinel.event1, sentinel.event2]

        client.simulate_smart_contract(
            start_timestamp=start_ts,
            end_timestamp=end_ts,
            events=events,
            default_timezone=ZoneInfo("UTC"),
        )

        # Verify ordering
        # instructions = set_default_processing_group_timezone_events + default_events + events
        expected_instructions = [
            "json_sentinel.pgtz_event",  # set_default_processing_group_timezone_events
            "json_sentinel.default_event",  # default_events
            "json_sentinel.event1",  # events
            "json_sentinel.event2",
        ]

        client._api_post.assert_called_once()
        payload = client._api_post.call_args[0][1]
        self.assertEqual(payload["instructions"], expected_instructions)
