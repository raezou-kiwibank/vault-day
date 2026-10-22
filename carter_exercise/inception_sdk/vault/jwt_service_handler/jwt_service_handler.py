# standard libs
from typing import Iterable

# third party
import requests


class VaultTestJWTServiceHandler:
    """
    This JWT Service Handler is designed to work with the test-only jwt service that is
    deployed to certain vault environments.
    """

    def __init__(self, config: dict[str, str]):

        if url := config.get("jwt_issuer_endpoint_url"):
            self.jwt_endpoint_url = url
        else:
            raise ValueError(
                "Configuration dict is missing key `jwt_issuer_endpoint_url`"
                " or has an empty value"
            )
        self.kid = "default"
        self.session = requests.Session()

    def get_token(self, scopes: Iterable[str]) -> str:

        request = {
            "kid": self.kid,
            "claims": {
                "scp": scopes,
            },
        }

        response: requests.Response = self.session.post(self.jwt_endpoint_url, json=request)
        try:
            response.raise_for_status()
        except requests.HTTPError as e:
            raise ValueError(
                "Error requesting token from Vault Test JWT Service: " + str(response.content)
            ) from e

        # Our test jwt service only has access tokens, no refresh tokens
        return response.json()["token"]
