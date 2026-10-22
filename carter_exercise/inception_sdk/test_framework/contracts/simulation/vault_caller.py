# Copyright @ 2021 - 2024 Thought Machine Group Limited. All rights reserved.
# standard libs
import functools
import json
import logging
import os
import uuid
from datetime import datetime
from dateutil.relativedelta import relativedelta
from typing import Any
from zoneinfo import ZoneInfo

# third party
import requests

# inception sdk
import inception_sdk.vault.contracts.utils as utils
import inception_sdk.vault.core_api as core_api
import inception_sdk.vault.sim_api.contract_sim as contract_sim
from inception_sdk.common.python.file_utils import load_file_contents
from inception_sdk.test_framework.common.utils import replace_clu_dependencies
from inception_sdk.test_framework.contracts.files import (
    EMPTY_ASSET_CONTRACT_V4,
    EMPTY_LIABILITY_CONTRACT_V4,
)
from inception_sdk.test_framework.contracts.simulation.data_objects.data_objects import (
    ContractConfig,
    ContractModuleConfig,
    SimulationEvent,
    SupervisorConfig,
)
from inception_sdk.test_framework.contracts.simulation.helper import (
    account_to_simulate,
    create_calendar,
    create_derived_parameters_instructions,
    create_flag_definition_event,
    create_parameter,
    create_parameter_value,
    create_smart_contract_module_versions_link,
    update_pgtz_instruction,
    v2_create_account_instruction,
)
from inception_sdk.vault.environment import Environment

request_logger = logging.getLogger(".".join([__name__, "sim_test_request_logger"]))
response_logger = logging.getLogger(".".join([__name__, "sim_test_response_logger"]))
request_logger.setLevel(os.environ.get("LOGLEVEL", "INFO"))
response_logger.setLevel(os.environ.get("LOGLEVEL", "INFO"))


class VaultException(Exception):
    def __init__(self, vault_error_code: str, message: str, details: list | None = None):
        self.vault_error_code = vault_error_code
        self.message = message
        # Many errors won't have details, but it can contain useful information
        self.details = details or []

    def __str__(self):
        return (
            "An exception was raised inside Vault:\nError Code: %s\nMessage:\n%s\nDetails:\n%s\n"
            % (self.vault_error_code, self.message, self.details)
        )

    def __eq__(self, other):
        # not using type(self) here because self's type could extend VaultException
        if not isinstance(other, VaultException):
            return False
        return (
            self.vault_error_code == other.vault_error_code
            and self.message == other.message
            and self.details == other.details
        )

    def __repr__(self):
        return (
            f"VaultException(vault_error_code={self.vault_error_code}, message={self.message}, "
            f"details={self.details})"
        )


def _auth_required(func):
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        return func(self, *args, **kwargs)

    return wrapper


class Client:
    def __init__(self, *, environment: Environment):
        self.environment = environment
        self._session = requests.Session()
        self._set_session_headers()

    @_auth_required
    def _api_get(
        self, url: str, params: dict[str, Any], timeout: str, debug=False
    ) -> list[dict[str, Any]]:
        response: requests.Response = self._session.get(
            url=self.environment.core_api_url + url,
            params=params,
            headers={"grpc-timeout": timeout},
            stream=debug,
        )
        return self._handle_response(response, debug)

    @_auth_required
    def _api_post(
        self, url: str, payload: dict[str, Any], timeout: str, debug=False
    ) -> list[dict[str, Any]]:
        request_logger.debug(json.dumps(payload))
        response: requests.Response = self._session.post(
            self.environment.core_api_url + url,
            headers={"grpc-timeout": timeout},
            json=payload,
            stream=debug,
        )
        return self._handle_response(response, debug)

    def _handle_response(self, response: requests.Response, debug=False) -> list[dict[str, Any]]:
        try:
            response.raise_for_status()
        except requests.HTTPError as e:
            # Sometimes the simulator returns an unsuccessful http response with just the
            # error message in the response body
            return self._handle_error(response, e)

        try:
            data: list[dict[str, Any]] = []
            # The response for this endpoint is streamed as new line separated JSON.
            for line in response.iter_lines():
                line_json = json.loads(line)
                data.append(line_json)
                response_logger.debug(json.dumps(line_json))
                if line_json.get("error"):
                    # Unlike the HTTPError scenario above, the simulator can also return
                    # a successful http response, but includes an error message at the end of the
                    # streamed lines instead of a result
                    response_logger.warning(
                        "error received from simulation response: \n"
                        f"{json.dumps(line_json,indent=2, separators=(',', ': '))}"
                    )
                    return self._handle_error(line)
            return data
        except requests.HTTPError as e:
            return self._handle_error(response, e)

    @staticmethod
    def _handle_error(response: requests.Response | str, e: Exception | None = None):
        """_summary_
        Handles Sim stream errors.
        :param response: errored Response, which seems to happen if there is just a single error
        returned by the simulation, or an individual streamed message within an overall successful
        Response, which seems to happen if there are normal streamed results followed by an error
        :param e: optional exception to raise from if there is additional context to provide
        :raises json_e: raised if the response cannot be decoded
        :raises VaultException: raised if a Vault error is found within the response
        :raises ValueError: raised if an unhandled error is found within the response
        """

        try:
            if isinstance(response, requests.Response):
                content = response.json()
            else:
                content = json.loads(response)
        except (json.decoder.JSONDecodeError, requests.exceptions.JSONDecodeError) as json_e:
            raise json_e from e

        if "vault_error_code" in content and "message" in content:
            raise VaultException(
                content["vault_error_code"], content["message"], content.get("details")
            ) from e

        raise ValueError(f"Unhandled simulator response: {response}") from e

    def _set_session_headers(self):
        self._session.headers.update(
            self.environment.auth_headers() | {"Content-Type": "application/json"}
        )

    def get_vault_version(self) -> list[dict[str, Any]]:
        response = self._api_get("/v1/vault-version", {}, "5S")
        return response

    def simulate_smart_contract(
        self,
        start_timestamp: datetime,
        end_timestamp: datetime,
        events: list[SimulationEvent],
        timeout: str = "360S",
        supervisor_contract_code: str | None = None,
        supervisor_contract_version_id: str | None = None,
        supervisee_version_id_mapping: dict[str, str] | None = None,
        contract_codes: list[str] | None = None,
        smart_contract_version_ids: list[str] | None = None,
        templates_parameters: list[dict[str, str]] | None = None,
        contract_config: ContractConfig | None = None,
        supervisor_contract_config: SupervisorConfig | None = None,
        account_creation_events: list[dict[str, Any]] | None = None,
        internal_account_ids: list[str] | dict[str, str] | None = None,
        flag_definition_ids: list[str] | None = None,
        calendar_ids: list[str] | None = None,
        parameters: list[core_api.ParameterResource] | None = None,
        globally_owned_parameter_values: (
            dict[str, tuple[core_api.ParameterValue, str | None]] | None
        ) = None,
        output_account_ids: list[str] | None = None,
        output_timestamps: list[datetime] | None = None,
        use_v1_accounts: bool = True,
        default_timezone: ZoneInfo | None = None,
        debug: bool = False,
        # TODO (TM-100096): Add flag for toggling between v1/v2 accounts endpoint
    ):
        adjusted_start_timestamp = start_timestamp
        internal_account_creation_events = []
        account_creation_events = account_creation_events or []
        default_events = []
        contract_codes = contract_codes or []
        smart_contract_version_ids = smart_contract_version_ids or []
        templates_parameters = templates_parameters or []
        flag_definition_ids = flag_definition_ids or []
        calendar_ids = calendar_ids or []
        internal_account_ids = internal_account_ids or []
        contract_modules_to_simulate: list[dict[str, str]] = []
        supervisee_version_id_mapping = supervisee_version_id_mapping or {}

        if internal_account_ids:
            # internal_account_ids is either a list of ids (in which case the accounts will be
            # instantiated as liability accounts) or a dict with id:tside key-value pairs
            if isinstance(internal_account_ids, dict):
                internal_accounts_to_create = internal_account_ids.copy()
            else:
                internal_accounts_to_create = {
                    internal_account_id: "LIABILITY" for internal_account_id in internal_account_ids
                }
            if use_v1_accounts:
                internal_account_creation_events = [
                    account_to_simulate(
                        timestamp=start_timestamp,
                        account_id=account_id,
                        contract_file_path=(
                            EMPTY_ASSET_CONTRACT_V4
                            if tside == "ASSET"
                            else EMPTY_LIABILITY_CONTRACT_V4
                        ),
                    )
                    for account_id, tside in internal_accounts_to_create.items()
                ]
            else:
                # We need to create the internal accounts at -1s since the global parameters might
                # be referring to an account which hasn't been created yet
                if globally_owned_parameter_values:
                    adjusted_start_timestamp = start_timestamp - relativedelta(seconds=1)
                internal_account_creation_events = [
                    {
                        "event": v2_create_account_instruction(
                            timestamp=adjusted_start_timestamp,
                            v2_create_account=contract_sim.V2CreateAccount(
                                account=core_api.InternalAccountRequestBody(
                                    id=account_id,
                                    status=core_api.AccountV2Status.ACCOUNT_STATUS_OPEN,
                                    t_side=(
                                        core_api.AccountV2TSide.T_SIDE_LIABILITY
                                        if tside == "LIABILITY"
                                        else core_api.AccountV2TSide.T_SIDE_ASSET
                                    ),
                                ),
                            ),
                        )
                    }
                    for account_id, tside in internal_accounts_to_create.items()
                ]

        # putting internal account creation events at the front to ensure all events are in
        # chronological order, as mandated by the simulator endpoint
        account_creation_events = internal_account_creation_events + account_creation_events

        if flag_definition_ids:
            for flag_definition_id in flag_definition_ids:
                flag_definition_event = create_flag_definition_event(
                    timestamp=start_timestamp, flag_definition_id=flag_definition_id
                )
                default_events.append(flag_definition_event)
        if calendar_ids:
            for calendar_id in calendar_ids:
                calendar = create_calendar(timestamp=start_timestamp, calendar_id=calendar_id)
                default_events.append(calendar)

        # This is handling customer and internal accounts for v1 and v2 accounts api, so it's
        # possible there is no contract (and hence params or smart contract version) if dealing
        # with a v2 internal account
        for account in account_creation_events:
            if code := account.get("contract_file_contents"):
                contract_codes.append(code)
            if smart_contract_version_id := account.get("smart_contract_version_id"):
                smart_contract_version_ids.append(smart_contract_version_id)
            # the contract can legitimately have no template parameters
            if "template_parameters" in account:
                templates_parameters.append(account["template_parameters"])
            if creation_sim_event := account.get("event"):
                default_events.append(creation_sim_event)

        if supervisor_contract_code is not None:
            if not supervisee_version_id_mapping:
                raise ValueError(
                    "supervisee_version_id_mapping missing or empty for a test using "
                    "supervisor_contract_code"
                )

            supervisor_contract_code = replace_clu_dependencies(
                "UNKNOWN",
                supervisor_contract_code,
                supervisee_version_id_mapping,
                remove_clu_syntax_for_unknown_ids=True,
            )

        final_contract_codes = []

        # The code below makes sure that only parameters related to the smart_contract are created
        # and duplicate parameter creation should not happen
        parameters_to_create: dict[str, core_api.ParameterResource] = {}
        for index, contract in enumerate(contract_codes):
            final_contract_code = replace_clu_dependencies(
                "UNKNOWN", contract, remove_clu_syntax_for_unknown_ids=True
            )
            final_contract_codes.append(final_contract_code)
            related_parameters = utils.get_contract_required_parameter_resources(
                smart_contract_version_ids[index],
                final_contract_code,
                parameters,
            )
            for parameter in related_parameters:
                parameters_to_create[parameter.id] = parameter

        # Parameters need to be created before calling create account hence the -1 second
        # create_account defaults to the start_timestamp hence doesn't need to adjusted.
        if parameters_to_create:
            adjusted_start_timestamp = start_timestamp - relativedelta(seconds=1)
            create_events = [
                create_parameter(adjusted_start_timestamp, p) for p in parameters_to_create.values()
            ]

            if globally_owned_parameter_values:
                for parameter_id, (
                    parameter_value,
                    parameter_value_id,
                ) in globally_owned_parameter_values.items():
                    create_event = create_parameter_value(
                        timestamp=adjusted_start_timestamp,
                        parameter_value=contract_sim.CreateParameterValue(
                            id=parameter_value_id,
                            parameter_id=parameter_id,
                            value=parameter_value,
                            effective_from_timestamp=adjusted_start_timestamp,
                            global_=True,
                        ),
                    )
                    create_events.append(create_event)

            default_events = create_events + default_events

        contract_configs = (
            [contract_config]
            if contract_config
            else (
                supervisor_contract_config.supervisee_contracts
                if supervisor_contract_config
                else []
            )
        )

        (
            contract_module_linking_events,
            contract_modules_to_simulate,
        ) = _create_smart_contract_module_links(start_timestamp, contract_configs)
        default_events.extend(contract_module_linking_events)

        set_default_processing_group_timezone_events: list[SimulationEvent] = (
            [
                update_pgtz_instruction(
                    event_datetime=adjusted_start_timestamp,
                    timezone=default_timezone,
                )
            ]
            if default_timezone
            else []
        )

        payload = self._api_post(
            "/v1/contracts:simulate",
            {
                "start_timestamp": _datetime_to_rfc_3339(adjusted_start_timestamp),
                "end_timestamp": _datetime_to_rfc_3339(end_timestamp),
                "smart_contracts": _smart_contract_to_json(
                    final_contract_codes, templates_parameters, smart_contract_version_ids
                ),
                "supervisor_contracts": _supervisor_contract_to_json(
                    supervisor_contract_code, supervisor_contract_version_id
                ),
                "contract_modules": contract_modules_to_simulate,
                "instructions": [
                    _event_to_json(event)
                    for event in set_default_processing_group_timezone_events
                    + default_events
                    + events
                ],
                "outputs": create_derived_parameters_instructions(
                    output_account_ids, output_timestamps
                ),
            },
            timeout=timeout,
            debug=debug,
        )
        return payload

    def simulate(
        self,
        request: contract_sim.SimulateRequest,
        timeout: str = "360S",
        debug: bool = False,
    ) -> list[dict[str, Any]]:
        return self._api_post(
            "/v1/contracts:simulate",
            request.model_dump(),
            timeout=timeout,
            debug=debug,
        )


def _datetime_to_rfc_3339(dt):
    timezone_aware = dt.tzinfo is not None and dt.tzinfo.utcoffset(dt) is not None

    if not timezone_aware:
        raise ValueError("The datetime object passed in is not timezone-aware")

    return dt.astimezone().isoformat()


def _event_to_json(event):
    instruction = {
        "timestamp": _datetime_to_rfc_3339(event.time),
    }

    for key in event.event:
        instruction[key] = event.event[key]

    return instruction


def _smart_contract_to_json(
    contract_codes: list[str],
    templates_parameters: list[dict[str, str]],
    smart_contract_version_ids: list[str],
) -> list:
    if len(contract_codes) == len(templates_parameters) == len(smart_contract_version_ids):
        return [
            {
                "code": code,
                "smart_contract_param_vals": template_parameter,
                "smart_contract_version_id": smart_contract_version_id,
            }
            for code, template_parameter, smart_contract_version_id in zip(
                contract_codes, templates_parameters, smart_contract_version_ids
            )
        ]
    else:
        raise ValueError(
            "The length of contract_codes, templates_parameters and "
            + "smart_contract_version_ids must be equal."
        )


def _supervisor_contract_to_json(supervisor_contract_code, supervisor_contract_version_id):
    """
    Helper that support the supervisor contract object. Although this is a list field,
    only one supervisor contract can currently be simulated for each request.
    :param supervisor_contract_code: Source code of the supervisor contract that is to be simulated.
    :param supervisor_contract_version_id: The ID that will be used as the supervisor contract
        version ID in the simulation and can be referenced by the simulation instructions.
    :return: a hypothetical list of supervisor contracts to simulate.
    """
    supervisor_contracts = []
    if supervisor_contract_code is not None:
        supervisor_contracts.append(
            {
                "code": supervisor_contract_code,
                "supervisor_contract_version_id": supervisor_contract_version_id,
            }
        )
    return supervisor_contracts


def _create_smart_contract_module_links(
    start: datetime, contract_configs: list[ContractConfig]
) -> tuple[list[SimulationEvent], list[dict[str, str]]]:
    events: list[SimulationEvent] = []
    contract_modules_to_simulate: list[dict[str, str]] = []
    existing_contract_modules: list[ContractModuleConfig] = []
    for contract_config in contract_configs:
        alias_to_sc_version_id = {}
        if contract_config.linked_contract_modules:
            for contract_module in contract_config.linked_contract_modules:
                existing_module_version_id = get_existing_module_version_id(
                    contract_module, existing_contract_modules
                )
                if existing_module_version_id is not None:
                    contract_module_version_id = existing_module_version_id

                else:
                    contract_module_code = load_file_contents(contract_module.file_path)
                    contract_module_version_id = str(uuid.uuid4())
                    contract_module.version_id = contract_module_version_id

                    existing_contract_modules.append(contract_module)

                    details = {
                        "code": contract_module_code,
                        "contract_module_version_id": contract_module_version_id,
                    }
                    contract_modules_to_simulate.append(details)

                alias_to_sc_version_id[contract_module.alias] = contract_module_version_id

            aliases_as_str = "_".join(alias_to_sc_version_id.keys())
            events.append(
                create_smart_contract_module_versions_link(
                    timestamp=start,
                    link_id=f"sim_link_modules_{aliases_as_str}_with_contract_"
                    f"{contract_config.smart_contract_version_id}",
                    smart_contract_version_id=contract_config.smart_contract_version_id,
                    alias_to_contract_module_version_id=alias_to_sc_version_id,
                )
            )
    return events, contract_modules_to_simulate


def get_existing_module_version_id(
    contract_module: ContractModuleConfig,
    existing_contract_modules: list[ContractModuleConfig],
):
    for existing_module in existing_contract_modules:
        if contract_module.file_path == existing_module.file_path:
            return existing_module.version_id
