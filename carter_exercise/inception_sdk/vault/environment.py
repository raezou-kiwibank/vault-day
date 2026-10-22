# standard libs
import json
import logging
import os
from dataclasses import dataclass, field
from typing import Any, Protocol, Type

# inception sdk
from inception_sdk.common.exceptions import ConfigurationException
from inception_sdk.common.python.file_utils import load_file_contents, load_object

log = logging.getLogger(__name__)
logging.basicConfig(
    level=os.environ.get("LOGLEVEL", "INFO"),
    format="%(asctime)s.%(msecs)03d - %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

DEFAULT_CORE_API_SCOPES = [
    "core:read",
    "data_loader:read",
    # this is contract simulation
    "core.contracts:execute",
    # We control write scopes more granularly, as we don't want to allow
    # more sensitive access like service account creation
    "core.account_schedule_tags:write",
    "core.account_updates:write",
    "core.accounts:write",
    "core.calendar_events:write",
    "core.calendars:write",
    "core.contract_module_versions:write",
    "core.contract_modules:write",
    "core.customers:write",
    "core.flag_definitions:write",
    "core.flags:write",
    "core.global_parameter_values:write",
    "core.global_parameters:write",
    "core.internal_accounts:write",
    "core.parameter_value_hierarchy_nodes:write",
    "core.parameter_values:write",
    "core.parameters:write",
    "core.payment_device_links:write",
    "core.payment_devices:write",
    "core.plan_updates:write",
    "core.plans:write",
    "core.posting_instruction_batches:write",
    "core.postings_api_clients:write",
    "core.processing_groups:write",
    "core.product_versions:write",
    "core.restriction_set_definition_versions:write",
    "core.restriction_sets:write",
    "core.smart_contract_module_versions_links:write",
    "core.sub_accounts:write",
    "core.supervisor_contract_versions:write",
    "core.supervisor_contracts:write",
]


@dataclass
class ServiceAccount:
    token: str = ""

    def auth_headers(self) -> dict[str, str]:
        return {"X-Auth-Token": self.token}

    @staticmethod
    def from_dict(input: dict[str, str]):
        return ServiceAccount(token=input["token"])


class JWTIssuerHandler(Protocol):

    def __init__(self, config: dict[str, str]): ...

    def get_token(self, scopes: list[str]) -> str: ...


@dataclass
class JWTAuth:
    handler: JWTIssuerHandler
    scopes: list[str] = field(default_factory=lambda: DEFAULT_CORE_API_SCOPES)
    token: str = ""

    def refresh_jwt(self):
        self.token = self.handler.get_token(scopes=self.scopes)

    def auth_headers(self) -> dict[str, str]:
        if not self.token:
            self.refresh_jwt()
        return {"Authorization": "Bearer " + self.token}

    @staticmethod
    def from_dict(input: dict[str, Any]):
        handler_class_path = input["handler_class"]
        config = input["config"]
        scopes = input.get("scopes", DEFAULT_CORE_API_SCOPES)
        try:
            handler_class: Type[JWTIssuerHandler] = load_object(handler_class_path)  # type: ignore
        except (AttributeError, ModuleNotFoundError) as e:
            raise ConfigurationException(
                f"Could not load JWT Handler class from {handler_class_path}"
            ) from e
        handler: JWTIssuerHandler = handler_class(config=config)
        return JWTAuth(handler=handler, scopes=scopes)


@dataclass
class Auth:
    service_account: ServiceAccount | None = None
    jwt: JWTAuth | None = None

    def __post_init__(self):
        # We have to allow both since workflows only support service account auth
        if self.service_account is None and self.jwt is None:
            raise ConfigurationException(
                "At least one of auth.service_account or auth.jwt must be specified in config"
            )

    @staticmethod
    def from_dict(input: dict[str, dict[str, str]]):
        service_account = None
        jwt = None
        if service_account_dict := input.get("service_account"):
            service_account = ServiceAccount.from_dict(service_account_dict)
        if jwt_dict := input.get("jwt"):
            jwt = JWTAuth.from_dict(jwt_dict)
        return Auth(service_account=service_account, jwt=jwt)


@dataclass
class Environment:
    name: str
    auth: Auth
    core_api_url: str
    ops_dash_url: str | None = None
    data_loader_api_url: str | None = None
    workflow_api_url: str | None = None
    kafka_config: dict[str, bool | int | str] = field(default_factory=dict)

    def __post_init__(self):
        if self.workflow_api_url and not self.auth.service_account:
            raise ConfigurationException(
                f"Environment {self.name} specifies a workflow api url without "
                "service account authentication. Workflows only support service "
                "account authentication"
            )

    def authenticate(self) -> None:
        if self.auth.jwt is not None:
            self.auth.jwt.refresh_jwt()

    def workflow_auth_headers(self) -> dict[str, str]:
        if self.auth.service_account:
            return self.auth.service_account.auth_headers()
        else:
            raise ConfigurationException(
                f"No service account authentication configured for environment {self.name}. "
                "Workflows only support service account authentication"
            )

    def auth_headers(self) -> dict[str, str]:
        if self.auth.jwt:
            return self.auth.jwt.auth_headers()
        elif self.auth.service_account:
            return self.auth.service_account.auth_headers()
        else:
            raise ConfigurationException(
                f"No authentication configured for environment {self.name}"
            )


def load_environment(name: str, env_definition: dict) -> Environment:
    kafka_config = env_definition.pop("kafka", {})

    # Left for backwards compatibility to support old config input
    service_account_token = env_definition.pop("access_token", None)
    env_definition.pop("service_account_id", None)
    env_definition.pop("service_account_name", None)
    env_definition.pop("cluster", None)
    env_definition.pop("namespace", None)
    env_definition.pop("prometheus_api_url", None)

    auth = env_definition.pop("auth", None)
    if auth is None and service_account_token:
        auth = {"service_account": {"token": service_account_token}}
    env = Environment(
        name=name,
        auth=Auth.from_dict(auth),
        kafka_config=kafka_config,
        **env_definition,
    )

    return env


def load_environments(file_path: str) -> dict[str, Environment]:
    """
    Load multiple environments from a JSON file. Expects the JSON file to be a dictionary of
    environment_name -> env_config
    :param file_path: path to the JSON file
    :return: environments, initialised from JSON file contents
    """

    environments = {
        env_name: load_environment(env_name, env_definition=env)
        for env_name, env in json.loads(load_file_contents(file_path)).items()
    }

    return environments
