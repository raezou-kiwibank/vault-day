# standard libs
from unittest import TestCase
from unittest.mock import MagicMock, PropertyMock, patch, sentinel

# inception sdk
import inception_sdk.vault.environment as environment
from inception_sdk.vault.environment import (
    Auth,
    ConfigurationException,
    Environment,
    JWTAuth,
    ServiceAccount,
    load_environment,
)


@patch.object(environment, "Environment")
class TestLoadEnvironment(TestCase):

    def test_backwards_compatibility_with_old_auth(self, mock_Environment):
        mock_environment_instance = MagicMock()
        mock_Environment.return_value = mock_environment_instance
        self.assertEqual(
            environment.load_environment(
                name="test",
                env_definition={
                    "service_account_id": sentinel.sa_id,
                    "service_account_name": sentinel.sa_name,
                    "access_token": sentinel.sa_token,
                    "kafka": {},
                },
            ),
            mock_environment_instance,
        )
        mock_Environment.assert_called_once_with(
            name="test",
            auth=Auth(service_account=ServiceAccount(token=sentinel.sa_token), jwt=None),
            kafka_config={},
        )

    def test_new_auth(self, mock_Environment):
        mock_environment_instance = MagicMock()
        mock_Environment.return_value = mock_environment_instance
        self.assertEqual(
            load_environment(
                name="test",
                env_definition={
                    "access_token": sentinel.sa_token,
                    "auth": {"service_account": {"token": sentinel.other_token}},
                    "kafka": {},
                },
            ),
            mock_environment_instance,
        )
        mock_Environment.assert_called_once_with(
            name="test",
            auth=Auth(service_account=ServiceAccount(token=sentinel.other_token), jwt=None),
            kafka_config={},
        )


class TestAuth(TestCase):

    def test_auth_with_missing_config(self):
        with self.assertRaises(ConfigurationException):
            Auth(service_account=None, jwt=None)

    def test_auth_with_both_config(self):
        self.assertIsNotNone(
            Auth(
                service_account=ServiceAccount(token="a"),
                jwt=JWTAuth(
                    sentinel.jwt_handler,
                ),
            )
        )

    @patch.object(ServiceAccount, "from_dict")
    def test_auth_service_account_from_dict(self, mock_from_dict):
        mock_from_dict.return_value = ServiceAccount(token=sentinel.token)
        self.assertEqual(
            Auth.from_dict(input={"service_account": {"token": sentinel.token}}),
            Auth(service_account=ServiceAccount(token=sentinel.token), jwt=None),
        )

    @patch.object(JWTAuth, "from_dict")
    def test_auth_jwt_from_dict(self, mock_from_dict):
        mock_from_dict.return_value = JWTAuth(sentinel.jwt_handler)
        self.assertEqual(
            Auth.from_dict(
                input={"jwt": {"handler_class": sentinel.handler_class, "config": sentinel.config}}
            ),
            Auth(service_account=None, jwt=JWTAuth(sentinel.jwt_handler)),
        )


class TestServiceAccount(TestCase):

    def test_service_account_from_dict(self):
        self.assertEqual(
            ServiceAccount.from_dict({"token": sentinel.token}),
            ServiceAccount(token=sentinel.token),
        )


class TestJWTAuth(TestCase):

    def test_jwt_auth_from_dict(self):
        with patch.object(environment, "load_object") as load_object:
            load_object.return_value = MagicMock(return_value=sentinel.jwt_handler)
            self.assertEqual(
                JWTAuth.from_dict(
                    input={"handler_class": sentinel.handler_class, "config": sentinel.config}
                ),
                JWTAuth(handler=sentinel.jwt_handler, scopes=environment.DEFAULT_CORE_API_SCOPES),
            )

    def test_jwt_auth_from_dict_with_non_default_scopes(self):
        with patch.object(environment, "load_object") as load_object:
            load_object.return_value = MagicMock(return_value=sentinel.jwt_handler)
            self.assertEqual(
                JWTAuth.from_dict(
                    input={
                        "handler_class": sentinel.handler_class,
                        "config": sentinel.config,
                        "scopes": sentinel.custom_scopes,
                    }
                ),
                JWTAuth(handler=sentinel.jwt_handler, scopes=sentinel.custom_scopes),
            )

    def test_jwt_class_load_error(self):
        with patch.object(environment, "load_object") as load_object:
            load_object.side_effect = AttributeError
            with self.assertRaises(ConfigurationException):
                JWTAuth.from_dict(
                    {"handler_class": sentinel.handler_class, "config": sentinel.config}
                )


class TestAuthentication(TestCase):

    def test_authenticate_with_service_account(self):
        mock_auth = MagicMock(spec=ServiceAccount)
        env = Environment(
            name="test",
            core_api_url="core_api_url",
            auth=Auth(service_account=mock_auth),
        )
        env.authenticate()
        mock_auth.assert_not_called()

    def test_authenticate_with_jwt(self):
        mock_auth = MagicMock(spec=JWTAuth)
        env = Environment(
            name="test",
            core_api_url="core_api_url",
            auth=Auth(jwt=mock_auth),
        )
        env.authenticate()
        mock_auth.refresh_jwt.assert_called_once()

    def test_auth_headers_with_service_account(self):
        self.assertDictEqual(
            Environment(
                name="test",
                core_api_url="core_api_url",
                auth=Auth(service_account=ServiceAccount(token="sa_token")),
            ).auth_headers(),
            {"X-Auth-Token": "sa_token"},
        )

    def test_auth_headers_with_jwt(self):
        self.assertDictEqual(
            Environment(
                name="test",
                core_api_url="core_api_url",
                auth=Auth(
                    jwt=JWTAuth(handler=sentinel.handler, token="jwt"),
                ),
            ).auth_headers(),
            {"Authorization": "Bearer jwt"},
        )

    def test_auth_headers_with_jwt_and_no_token_refreshes_token(self):
        mock_handler = MagicMock(get_token=MagicMock(return_value="jwt"))
        self.assertDictEqual(
            Environment(
                name="test",
                core_api_url="core_api_url",
                auth=Auth(
                    jwt=JWTAuth(handler=mock_handler),
                ),
            ).auth_headers(),
            {"Authorization": "Bearer jwt"},
        )
        mock_handler.get_token.assert_called_once_with(scopes=environment.DEFAULT_CORE_API_SCOPES)

    def test_auth_headers_with_jwt_and_no_token_refreshes_token_custom_scopes(self):
        mock_handler = MagicMock(get_token=MagicMock(return_value="jwt"))
        self.assertDictEqual(
            Environment(
                name="test",
                core_api_url="core_api_url",
                auth=Auth(
                    jwt=JWTAuth(handler=mock_handler, scopes=sentinel.custom_scopes),
                ),
            ).auth_headers(),
            {"Authorization": "Bearer jwt"},
        )
        mock_handler.get_token.assert_called_once_with(scopes=sentinel.custom_scopes)

    def test_auth_headers_with_jwt_and_service_account(self):
        self.assertDictEqual(
            Environment(
                name="test",
                core_api_url="core_api_url",
                auth=Auth(
                    service_account=ServiceAccount(token="sa_token"),
                    jwt=JWTAuth(handler=sentinel.handler, token="jwt"),
                ),
            ).auth_headers(),
            {"Authorization": "Bearer jwt"},
        )

    def test_auth_headers_with_no_auth(self):
        mock_auth = MagicMock()
        type(mock_auth).jwt = PropertyMock(return_value=None)
        type(mock_auth).service_account = PropertyMock(return_value=None)
        with self.assertRaises(ConfigurationException):
            Environment(
                name="test",
                core_api_url="core_api_url",
                auth=mock_auth,
            ).auth_headers()

    def test_workflow_auth_headers_with_service_account(self):
        self.assertDictEqual(
            Environment(
                name="test",
                core_api_url="core_api_url",
                auth=Auth(service_account=ServiceAccount(token="sa_token")),
            ).workflow_auth_headers(),
            {"X-Auth-Token": "sa_token"},
        )

    def test_workflow_auth_headers_with_jwt(self):
        with self.assertRaises(ConfigurationException):
            Environment(
                name="test",
                core_api_url="core_api_url",
                auth=Auth(
                    jwt=JWTAuth(handler=sentinel.handler, token="jwt"),
                ),
            ).workflow_auth_headers()

    def test_workflow_auth_headers_with_service_account_and_jwt(self):
        self.assertDictEqual(
            Environment(
                name="test",
                core_api_url="core_api_url",
                auth=Auth(
                    service_account=ServiceAccount(token="sa_token"),
                    jwt=JWTAuth(handler=sentinel.handler, token="jwt"),
                ),
            ).workflow_auth_headers(),
            {"X-Auth-Token": "sa_token"},
        )


class TestEnvironment(TestCase):

    def test_environment_with_workflow_api_but_no_corresponding_auth(self):
        with self.assertRaises(ConfigurationException):
            Environment(
                name="test",
                core_api_url="core_api_url",
                workflow_api_url="workflow_api_url",
                auth=Auth(
                    jwt=JWTAuth(handler=sentinel.handler, token="jwt"),
                ),
            )
