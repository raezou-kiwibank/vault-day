# standard libs
from os import path
from unittest import TestCase

# third party
import requests

# inception sdk
from inception_sdk.common.config import extract_environments_from_config
from inception_sdk.common.python.flag_utils import parse_flags
from inception_sdk.vault.jwt_service_handler import VaultTestJWTServiceHandler


class TestVaultJWTServiceHandler(TestCase):

    def test_get_token(self):
        parse_flags(allow_unknown=True)
        # This forces the default e2e env to have jwt config using VaultTestJWTServiceHandler
        # but alternatively we'd leak env details out with our releases.
        env, _ = extract_environments_from_config("inception-development")
        if env.auth.jwt is None:
            self.fail(f"Environment config for {env.name} doesn't have jwt auth config")
        if not isinstance(env.auth.jwt.handler, VaultTestJWTServiceHandler):
            self.fail(f"Environment config for {env.name} doesn't use VaultTestJWTServiceHandler")
        token = env.auth.jwt.handler.get_token(scopes=["core:read"])
        session = requests.sessions.Session()

        session.headers.update({"Authorization": "Bearer " + token})

        response = session.get(path.join(env.core_api_url, "v1/vault-version"))
        self.assertEqual(response.status_code, 200)

        # the requested scope is read-only so this should error
        response: requests.Response = session.post(path.join(env.core_api_url, "v1/accounts"))
        self.assertEqual(response.status_code, 403)
