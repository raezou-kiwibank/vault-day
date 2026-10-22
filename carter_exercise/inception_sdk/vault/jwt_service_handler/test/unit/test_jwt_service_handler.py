# standard libs
from unittest import TestCase
from unittest.mock import MagicMock, patch, sentinel

# third party
import requests

# inception sdk
import inception_sdk.vault.jwt_service_handler.jwt_service_handler as jwt_service_handler
from inception_sdk.vault.jwt_service_handler import VaultTestJWTServiceHandler


class TestVaultJWTServiceHandler(TestCase):

    def test_handler_with_invalid_config(self):
        with self.assertRaises(ValueError) as ctx:
            VaultTestJWTServiceHandler({"wrong_config": sentinel.endpoint_url})
        self.assertEqual(
            ctx.exception.args[0],
            "Configuration dict is missing key `jwt_issuer_endpoint_url` or has an empty value",
        )

    @patch.object(jwt_service_handler.requests, "Session")
    def test_get_token(self, mock_session):
        mock_session_instance = MagicMock(
            name="mock_session",
            post=MagicMock(
                return_value=MagicMock(
                    raise_for_status=MagicMock(),
                    json=MagicMock(return_value={"token": "token_contents"}),
                )
            ),
        )

        mock_session.return_value = mock_session_instance

        handler = VaultTestJWTServiceHandler({"jwt_issuer_endpoint_url": sentinel.endpoint_url})

        self.assertEqual(handler.get_token(scopes=sentinel.scopes), "token_contents")
        mock_session_instance.post.assert_called_once_with(
            sentinel.endpoint_url, json={"kid": "default", "claims": {"scp": sentinel.scopes}}
        )

    @patch.object(jwt_service_handler.requests, "Session")
    def test_get_token_with_error(self, mock_session):
        mock_session_instance = MagicMock(
            name="mock_session",
            post=MagicMock(
                return_value=MagicMock(
                    raise_for_status=MagicMock(side_effect=requests.HTTPError),
                )
            ),
        )

        mock_session.return_value = mock_session_instance

        handler = VaultTestJWTServiceHandler({"jwt_issuer_endpoint_url": sentinel.endpoint_url})
        with self.assertRaises(ValueError) as ctx:
            handler.get_token(scopes=sentinel.scopes)
        self.assertIn("Error requesting token from Vault Test JWT Service", ctx.exception.args[0])
