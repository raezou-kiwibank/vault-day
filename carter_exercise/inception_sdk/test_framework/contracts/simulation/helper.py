# Copyright @ 2021 Thought Machine Group Limited. All rights reserved.

"""
This module exposes easy helper methods for sending each type
of posting instruction and settings flags with minimal effort from the test writer.
However, for posting instruction types these helper methods are kept simple and minimal on purpose,
only exposing a small subset of fields available on each posting instruction
type.
Any more complex Posting Instruction Batches should be constructed by the
test writer out of the base available objects.
"""
# standard libs
import uuid
from copy import deepcopy
from datetime import datetime, timedelta
from decimal import Decimal
from random import randrange
from typing import Sequence
from zoneinfo import ZoneInfo

# third party
from typing_extensions import deprecated

# contracts api
from contracts_api import DateShape, DenominationShape, NumberShape, StringShape

# inception sdk
import inception_sdk.vault.core_api as core_api
import inception_sdk.vault.sim_api.contract_sim as contract_sim
from inception_sdk.common.python.file_utils import load_file_contents
from inception_sdk.test_framework.common.utils import strip_clu_notation
from inception_sdk.test_framework.contracts.files import EMPTY_LIABILITY_CONTRACT
from inception_sdk.test_framework.contracts.simulation.common.helper import (
    create_auth_adjustment_event as create_auth_adjustment_event_common,
    create_auth_adjustment_pi_event as create_auth_adjustment_pi_event_common,
    create_custom_instruction_event as create_custom_instruction_event_common,
    create_custom_instruction_pi_event as create_custom_instruction_pi_event_common,
    create_inbound_authorisation_event as create_inbound_authorisation_event_common,
    create_inbound_authorisation_pi_event as create_inbound_authorisation_pi_event_common,
    create_inbound_hard_settlement_event as create_inbound_hard_settlement_event_common,
    create_inbound_hard_settlement_pi_event as create_inbound_hard_settlement_pi_event_common,
    create_outbound_authorisation_event as create_outbound_authorisation_event_common,
    create_outbound_authorisation_pi_event as create_outbound_authorisation_pi_event_common,
    create_outbound_hard_settlement_event as create_outbound_hard_settlement_event_common,
    create_outbound_hard_settlement_pi_event as create_outbound_hard_settlement_pi_event_common,
    create_pib_event_from_posting_instructions as create_pib_posting_instruction_event_common,
    create_posting_instruction_batch_event as create_posting_instruction_batch_event_common,
    create_release_event as create_release_event_common,
    create_release_pi_event as create_release_pi_event_common,
    create_settlement_event as create_settlement_event_common,
    create_settlement_pi_event as create_settlement_pi_event_common,
    create_transfer_event as create_transfer_event_common,
    create_transfer_pi_event as create_transfer_pi_event_common,
)
from inception_sdk.test_framework.contracts.simulation.data_objects.data_objects import (
    SimulationEvent,
    SimulationTestScenario,
)
from inception_sdk.test_framework.contracts.simulation.data_objects.events.account_events import (
    CreateAccountEvent,
    CreateAccountProductVersionUpdateEvent,
    CreateInstanceParameterUpdateEvent,
    UpdateAccountEvent,
)
from inception_sdk.test_framework.contracts.simulation.data_objects.events.calendar_events import (
    CreateCalendar,
    CreateCalendarEvent,
)
from inception_sdk.test_framework.contracts.simulation.data_objects.events.contract_events import (
    CreateSmartContractModuleVersionsLink,
    CreateTemplateParameterUpdateEvent,
)
from inception_sdk.test_framework.contracts.simulation.data_objects.events.flag_events import (
    CreateFlag,
    CreateFlagDefinition,
)
from inception_sdk.test_framework.contracts.simulation.data_objects.events.parameter_events import (
    CreateGlobalParameterEvent,
    CreateGlobalParameterValue,
    CreateParameterEvent,
    GlobalParameter,
)
from inception_sdk.test_framework.contracts.simulation.data_objects.events.plan_events import (
    CreateAccountPlanAssocEvent,
    CreatePlanEvent,
)
from inception_sdk.vault.core_api import UpdateMask
from inception_sdk.vault.postings.posting_classes import Instruction, PostingInstruction
from inception_sdk.vault.sim_api.contract_sim import ProcessingGroup, UpdateProcessingGroup

UTC = ZoneInfo("UTC")
DEFAULT_PG = "DEFAULT"


def account_to_simulate(
    timestamp,
    account_id,
    contract_version_id=None,
    instance_params=None,
    template_params=None,
    contract_file_path=EMPTY_LIABILITY_CONTRACT,
    create_account=True,
):
    """
    Returns a dictionary with account details and if create_account is set to True
    dictionary key "event" is populated with account creation details.
    :param timestamp: timestamp, the datetime at which the account creation event should be
                      scheduled, auto-created events this must always be populated with sim
                      start time
    :param account_id: str, A unique ID for an account
    :param contract_version_id: str, An optional parameter, which will generate an ID if value
                      set to None.
    :param instance_params: dict, contract instance parameters
    :param template_params: dict, contract template parameters
    :param contract_file_path: str, path to contract file
    :param create_account: bool, if True, "event" key is populated with account creation
                           SimulationEvent
    :return: dict with account and contract related information.
    """

    if instance_params is None:
        instance_params = {}
    if template_params is None:
        template_params = {}

    # Avoid generated id collision. API accepts 64-bit signed int, use positive ints (INC-4048)
    generated_id = str(randrange(0, 2**63))
    smart_contract_version_id = contract_version_id or generated_id
    account_dict = {
        "timestamp": timestamp,
        "contract_file_contents": load_file_contents(contract_file_path),
        "account_id": str(account_id),
        "smart_contract_version_id": smart_contract_version_id,
        "instance_parameters": instance_params,
        "template_parameters": template_params,
        "create_account": create_account,
        "event": {},
    }

    if create_account:
        account_dict["event"] = create_account_instruction(
            timestamp=account_dict["timestamp"],
            account_id=account_dict["account_id"],
            product_id=account_dict["smart_contract_version_id"],
            instance_param_vals=account_dict["instance_parameters"],
        )

    return account_dict


def create_parameter(timestamp: datetime, parameter: core_api.ParameterResource) -> SimulationEvent:
    """
    Returns a SimulationEvent that instructs the simulation to create a parameter.
    All fields are required and metadata is not supported as per documentation
    :param timestamp: the datetime at which the Create parameter will be applied in the simulation.
    :param parameter: the parameter object to be created
    :return: SimulationEvent with a create parameter
    """
    p = deepcopy(parameter)
    p.id = strip_clu_notation(parameter.id)
    return SimulationEvent(
        timestamp,
        CreateParameterEvent(parameter=p).to_dict(),
    )


def create_parameter_value(
    timestamp: datetime,
    parameter_value: contract_sim.CreateParameterValue,
) -> SimulationEvent:
    """
    Returns a SimulationEvent that instructs the simulation to create a parameter value.
    All fields are required and metadata is not supported as per documentation
    :param timestamp: the datetime at which the Create parameter will be applied in the simulation.
    :param parameter_value: the parameter value to be created
    :return: SimulationEvent for creating a parameter value
    """
    pv = deepcopy(parameter_value)
    pv.parameter_id = strip_clu_notation(parameter_value.parameter_id)
    return SimulationEvent(timestamp, pv.sim_instruction())


def update_parameter_value(
    timestamp: datetime, update_parameter_value: contract_sim.UpdateParameterValue
) -> SimulationEvent:
    """
    Returns a SimulationEvent that instructs the simulation to update a parameter.
    All fields are required and metadata is not supported as per documentation
    :param timestamp: the datetime at which the Update parameter will be applied in the simulation.
    :param parameter_value: the parameter value to be updated
    :return: SimulationEvent for creating a parameter value
    """
    return SimulationEvent(timestamp, update_parameter_value.sim_instruction())


def batch_create_parameter_values(
    timestamp: datetime,
    batch_create_parameter_values: contract_sim.BatchCreateParameterValues,
) -> SimulationEvent:
    """
    Returns a SimulationEvent that instructs the simulation to batch create parameter values.
    All fields are required and metadata is not supported as per documentation
    :param timestamp: the datetime at which the Batch Create parameter value will be applied in the
        simulation.
    :param parameter_values: a list of parameter values to be created
    :return: SimulationEvent for batch creating multiple parameter values
    """

    return SimulationEvent(timestamp, batch_create_parameter_values.sim_instruction())


def create_parameter_value_hierarchy_node(
    timestamp: datetime,
    parameter_value_hierarchy_node: contract_sim.CreateParameterValueHierarchyNode,
) -> SimulationEvent:
    """
    Returns a SimulationEvent that instructs the simulation to create a Parameter Value
    Hierarchy Node.
    All fields are required
    :param timestamp: the datetime at which the Create parameter value hierarchy node will be
        applied in the simulation.
    :param parameter_value_hierarchy_node: the parameter value hierarchy node to be created
    :return: SimulationEvent for creating parameter value hierarchy node
    """
    return SimulationEvent(timestamp, parameter_value_hierarchy_node.sim_instruction())


def create_account_instruction(
    timestamp: datetime,
    account_id: str = "",
    product_id: str = "",
    permitted_denominations: list[str] | None = None,
    status: core_api.AccountStatus = core_api.AccountStatus.ACCOUNT_STATUS_UNKNOWN,
    stakeholder_ids: list[str] | None = None,
    instance_param_vals: dict[str, str] | None = None,
    derived_instance_param_vals: dict[str, str] | None = None,
    details: dict[str, str] | None = None,
) -> SimulationEvent:
    """
    Returns a SimulationEvent containing that instructs the simulation to create an account.
    The only required and supported fields are: id, product_version_id and instance_param_vals.
    :param timestamp: the datetime at which the Create account will be applied in the simulation.
    :param account_id: a unique ID for an account. Optional for create requests.
    :param product_id: the ID of the product the account is associated with.
                    Can be obtained using the /v1/products endpoint.
                    Required for create requests if product_version_id is not provided.
    :permitted_denominations: Denominations the account can hold balances in.
                    Must be a subset of the denominations supported by the product version.
    :status: The status of the account.
    :stakeholder_ids: The customer IDs that can access the account. Required for create requests.
    :instance_param_vals: The instance-level parameters for the associated product;
                            a map of the parameter name to value.
    :derived_instance_param_vals:
        The derived instance-level parameters for the associated product
        that have been defined in the account's Smart Contract code;
        a map of the parameter name to value.
    :details: A map of unstructured fields that hold instance-specific account details,
            for example, the source of funds.
    :return: SimulationEvent with a create account event
    """
    return SimulationEvent(
        timestamp,
        CreateAccountEvent(
            id=account_id,
            product_version_id=product_id,
            permitted_denominations=permitted_denominations or [],
            status=status,
            stakeholder_ids=stakeholder_ids or [],
            instance_param_vals=instance_param_vals or {},
            derived_instance_param_vals=derived_instance_param_vals or {},
            details=details or {},
        ).to_dict(),
    )


def create_account_product_version_update_instruction(
    timestamp: datetime,
    account_id: str,
    product_version_id: str,
) -> SimulationEvent:
    """
    Returns a SimulationEvent containing an instruction to update an account's product version.
    :param timestamp: the datetime at which the account will be updated.
    :param account_id: the unique ID for an account.
    :param product_version_id: the product version ID we're updating the account to.
    Note that the product version with the updated ID will need to be uploaded
    as part of the test set up.
    """
    return SimulationEvent(
        timestamp,
        CreateAccountProductVersionUpdateEvent(
            account_id=account_id, product_version_id=product_version_id
        ).to_dict(),
    )


def update_account_status_pending_closure(timestamp: datetime, account_id: str):
    """
    Returns a SimulationEvent containing instruction to change account status to pending closure.
    :param timestamp: the datetime at which the account pending closure will be applied.
    :param account_id: str, A unique ID for an account
    """
    return SimulationEvent(
        timestamp,
        UpdateAccountEvent(
            account_id=account_id, status=core_api.AccountStatus.ACCOUNT_STATUS_PENDING_CLOSURE
        ).to_dict(),
    )


def create_instance_parameter_change_event(
    timestamp: datetime, account_id: str, **kwargs: str
) -> SimulationEvent:
    """
    Returns a SimulationEvent containing an account update to update instance parameter values.
    :param timestamp: the datetime will be applied in the simulation.
    :param account_id: the account that the update should act on.
    :param **kwargs: keyword arguments of parameters to update, in form of parameter_name=value.
    :return: SimulationEvent with an account update to update instance parameter values.
    """
    return SimulationEvent(
        timestamp,
        CreateInstanceParameterUpdateEvent(account_id, kwargs).to_dict(),
    )


def create_template_parameter_change_event(
    timestamp: datetime, smart_contract_version_id: str = "0", **kwargs: str
) -> SimulationEvent:
    """
    The platform implementation for this can only handle one update per
    instruction, therefore, we are mirroring that constraint and preserve
    the input and output signatures as instance param update events
    """
    if len(kwargs) > 1:
        raise ValueError("template param update can only take in one parameter per event")

    parameter_name, new_parameter_value = next(iter(kwargs.items()))

    return SimulationEvent(
        timestamp,
        CreateTemplateParameterUpdateEvent(
            smart_contract_version_id, parameter_name, new_parameter_value
        ).to_dict(),
    )


def create_global_parameter_instruction(
    timestamp: datetime,
    global_parameter_id: str,
    display_name: str,
    description: str,
    initial_value: str,
    number: NumberShape | None = None,
    str: StringShape | None = None,  # noqa: A002
    denomination: DenominationShape | None = None,
    date: DateShape | None = None,
) -> SimulationEvent:
    """
    Instructs the simulation to create a new global parameter.
    Only one of the number, str, denomination, date parameters needs to be set.
    :param timestamp: the datetime will be applied in the simulation.
    :param global_parameter_id: The GlobalParameter ID.
        Used by Smart Contracts to retrieve values for this parameter.
    :param display_name: A human-readable name.
    :param description: A description of the parameter.
    :param number: used for parameters representing numerical values.
    :param str: used for parameters representing string values.
    :param denomination used for parameters representing denominations.
    :param date: used for parameters representing date values.
    :param initial_value: used to create a GlobalParameterValue
        associated with the newly created GlobalParameter.
    :return: SimulationEvent with a create global parameter
    """
    return SimulationEvent(
        timestamp,
        CreateGlobalParameterEvent(
            GlobalParameter(
                id=global_parameter_id,
                display_name=display_name,
                description=description,
                number=number,
                str=str,
                denomination=denomination,
                date=date,
            ),
            initial_value=initial_value,
        ).to_dict(),
    )


def create_global_parameter_value_instruction(
    timestamp: datetime,
    global_parameter_id: str,
    value: str,
    effective_timestamp: datetime,
) -> SimulationEvent:
    """
    Instructs the simulation to create a new global parameter value.
    :param timestamp: the datetime will be applied in the simulation.
    :param global_parameter_id: The GlobalParameter ID this value belongs to.
    :param value: the new parameter value that we want to create.
    :param effective_timestamp: A timestamp indicating
        when the GlobalParameterValue is effective from.
    :return: SimulationEvent with a create global parameter value
    """
    return SimulationEvent(
        timestamp,
        CreateGlobalParameterValue(
            global_parameter_id=global_parameter_id,
            value=value,
            effective_timestamp=effective_timestamp,
        ).to_dict(),
    )


def create_plan_instruction(
    timestamp: datetime, plan_id: str, supervisor_contract_version_id: str
) -> SimulationEvent:
    """
    Instructs the simulation to create a plan.
    :param timestamp: the datetime at which the create plan will be applied in the simulation.
    :param id: A unique ID for a plan. Optional for create requests. Max length: 36 characters.
    :param supervisor_contract_version_id: The ID of the supervisor contract version.
                                            Required for create requests.
    :return: SimulationEvent with a create account event
    """
    return SimulationEvent(
        timestamp,
        CreatePlanEvent(
            id=plan_id,
            supervisor_contract_version_id=supervisor_contract_version_id,
        ).to_dict(),
    )


def create_account_plan_assoc_instruction(
    timestamp: datetime,
    assoc_id: str,
    account_id: str,
    plan_id: str,
    status: core_api.AccountPlanAssocStatus = (
        core_api.AccountPlanAssocStatus.ACCOUNT_PLAN_ASSOC_STATUS_ACTIVE
    ),
) -> SimulationEvent:
    """
    Instructs the simulation to add an account to a plan for the specified duration.
    :param timestamp: The datetime at which the plan association will be created
    :param assoc_id: A unique ID for the account plan association to create
    :param account_id: The account ID to associate
    :param plan_id: The plan ID to associate to
    :param status: The status of the account plan association.
    :return: SimulationEvent with a create account plan associate event
    """
    return SimulationEvent(
        timestamp,
        CreateAccountPlanAssocEvent(
            id=assoc_id,
            account_id=account_id,
            plan_id=plan_id,
            status=status,
        ).to_dict(),
    )


def create_flag_definition_event(
    timestamp: datetime,
    flag_definition_id: str,
) -> SimulationEvent:
    """
    Returns a SimulationEvent containing that
    instructs the simulation to create flag definition.
    """
    return SimulationEvent(timestamp, CreateFlagDefinition(flag_definition_id).to_dict())


def create_flag_event(
    timestamp: datetime,
    flag_definition_id: str,
    account_id: str,
    expiry_timestamp: datetime | None = None,
    effective_timestamp: datetime | None = None,
    is_backdated: bool = False,
    value: core_api.FlagV1FlagValue = core_api.FlagV1FlagValue.FLAG_VALUE_ON,
) -> SimulationEvent:
    """
    Returns a SimulationEvent containing that
    instructs the simulation to create flag for an account.
    """
    return SimulationEvent(
        timestamp,
        CreateFlag(
            flag_definition_id=flag_definition_id,
            effective_timestamp=(effective_timestamp or timestamp).isoformat(),
            expiry_timestamp=(expiry_timestamp.isoformat() if expiry_timestamp else ""),
            is_backdated=is_backdated,
            value=value,
            account_id=account_id,
        ).to_dict(),
    )


def create_calendar(
    timestamp: datetime,
    calendar_id: str,
) -> SimulationEvent:
    """
    Returns a SimulationEvent containing that
    instructs the simulation to create a calendar.
    """
    return SimulationEvent(
        timestamp,
        CreateCalendar(
            calendar_id,
        ).to_dict(),
    )


def create_calendar_event(
    timestamp: datetime,
    calendar_event_id: str,
    calendar_id: str,
    start_timestamp: datetime,
    end_timestamp: datetime,
) -> SimulationEvent:
    """
    Returns a SimulationEvent containing that
    instructs the simulation to create a Calendar Event.
    """
    return SimulationEvent(
        timestamp,
        CreateCalendarEvent(
            calendar_event_id,
            calendar_id,
            start_timestamp.isoformat(),
            end_timestamp.isoformat(),
        ).to_dict(),
    )


def _transform_posting_key(event):
    """
    Returns a SimulationEvent that rename the posting key
    from posting_instruction_batch to create_posting_instruction_batch
    """
    batch = event.event["posting_instruction_batch"]
    event.event["create_posting_instruction_batch"] = batch
    del event.event["posting_instruction_batch"]
    return event


def create_derived_parameters_instructions(account_ids, timestamps):
    """
    Helper that support simulation of derived parameters
    :param timestamp: The timestamp used to calculate the output.
    :param account_id: The account ID that derived parameters are to be retrieved for.
    :return: a list of requests for data that is to be returned.
    """

    outputs = []

    if timestamps is not None:
        for i in range(len(timestamps)):
            outputs.append(
                {
                    "timestamp": _datetime_to_rfc_3339(timestamps[i]),
                    "derived_params": {"account_id": account_ids[i]},
                }
            )

    return outputs


def get_supervisor_setup_events(
    test_scenario: SimulationTestScenario,
) -> list[SimulationEvent]:
    """
        Helper that takes in test scenario config and:
        1. setup events to create supervisor contract
        2. setup events to create the number of supervisee contracts as specified
        3. setup events to create supervisor plan
        4. if configured to be true, link supervisees to plan
    Note:
        supervisee account creation events for the same contract are 1 ms apart
        to make them chronologically distinct
    """

    setup_events = []

    if test_scenario.supervisor_config is None:
        raise ValueError(
            "get_supervisor_setup_events called on test scenario with no supervisor_config"
        )

    # Set up global parameters
    if test_scenario.supervisor_config.global_params:
        setup_events.extend(
            [
                SimulationEvent(time=test_scenario.start, event=g.to_dict())
                for g in test_scenario.supervisor_config.global_params
            ]
        )

    event_time_offset = 0
    supervisee_account_creation_events = {}
    for supervisee_contract in test_scenario.supervisor_config.supervisee_contracts:
        for account_config in supervisee_contract.account_configs:
            for i in range(account_config.number_of_accounts):
                if account_config.account_id_base + str(i) in supervisee_account_creation_events:
                    raise ValueError(
                        "account_id_base must be different for each contract and account type"
                    )
                smart_contract_version_id = supervisee_contract.smart_contract_version_id
                supervisee_account_creation_events[account_config.account_id_base + str(i)] = (
                    create_account_instruction(
                        timestamp=test_scenario.start
                        + timedelta(milliseconds=event_time_offset + i),
                        account_id=account_config.account_id_base + str(i),
                        product_id=smart_contract_version_id,
                        instance_param_vals=account_config.instance_params,
                    )
                    if test_scenario.use_v1_accounts
                    else (
                        v2_create_account_instruction(
                            timestamp=(
                                test_scenario.start + timedelta(milliseconds=event_time_offset + i)
                            ),
                            v2_create_account=contract_sim.V2CreateAccount(
                                account=contract_sim.CustomerAccountRequestBody(
                                    id=account_config.account_id_base + str(i),
                                    smart_contract_version_id=smart_contract_version_id,
                                    status=core_api.AccountV2Status.ACCOUNT_STATUS_OPEN,
                                ),
                                create_options=(
                                    contract_sim.CreateOptions(
                                        parameter_values=account_config.parameter_values
                                    )
                                    if account_config.parameter_values
                                    else None
                                ),
                            ),
                        )
                    )
                )
            event_time_offset += account_config.number_of_accounts

    setup_events.extend(supervisee_account_creation_events.values())

    # Create plan
    event_time_offset += 1
    setup_events.append(
        create_plan_instruction(
            timestamp=test_scenario.start + timedelta(milliseconds=event_time_offset),
            plan_id=test_scenario.supervisor_config.plan_id,
            supervisor_contract_version_id=(
                test_scenario.supervisor_config.supervisor_contract_version_id
            ),
        )
    )
    # Create plan assoc
    if test_scenario.supervisor_config.associate_supervisees_to_plan:
        event_time_offset += 1
        setup_events.extend(
            create_account_plan_assoc_instruction(
                timestamp=test_scenario.start + timedelta(milliseconds=event_time_offset),
                assoc_id="Supervised " + account_id,
                account_id=account_id,
                plan_id=test_scenario.supervisor_config.plan_id,
            )
            for account_id in supervisee_account_creation_events.keys()
        )

    return setup_events


def get_contract_setup_events(
    test_scenario: SimulationTestScenario,
) -> list[SimulationEvent]:
    contract_setup_events: list[SimulationEvent] = []

    if test_scenario.contract_config is None:
        raise ValueError(
            "get_contract_setup_events called on test scenario with no contract_config"
        )

    contract_config = test_scenario.contract_config

    # Set up global parameters
    if contract_config.global_params:
        contract_setup_events.extend(
            [
                SimulationEvent(time=test_scenario.start, event=g.to_dict())
                for g in contract_config.global_params
            ]
        )

    account_config = contract_config.account_configs[0]
    instance_params = account_config.instance_params
    param_values = account_config.parameter_values
    sub_accounts = account_config.sub_accounts

    if test_scenario.use_v1_accounts:
        if instance_params is None and param_values is not None:
            raise ValueError(
                "Cannot use parameter_values with V1 accounts, use instance_params instead"
            )
        if sub_accounts is not None:
            raise ValueError("Cannot use Sub-Accounts with V1 accounts, use V2 accounts instead")
        # TODO (TM-100096): Add deprecation notice
        create_account_instr = create_account_instruction(
            timestamp=test_scenario.start,
            account_id=account_config.account_id_base,
            product_id=contract_config.smart_contract_version_id,
            instance_param_vals=instance_params,
        )
    else:
        if param_values is None and account_config.instance_params is not None:
            raise ValueError(
                "Cannot use instance_params with V2 accounts, use parameter_values instead"
            )
        if test_scenario.globally_owned_parameter_values and contract_config.global_params:
            raise ValueError(
                "Cannot use globally owned parameter values with legacy global parameters"
            )

        create_sub_account_requests: list[contract_sim.CreateSubAccount] = [
            contract_sim.CreateSubAccount(
                sub_account=core_api.SubAccountCreateSubAccount(
                    id=sub_account.id,
                    type=sub_account.type,
                    status=sub_account.status,
                    account_id=account_config.account_id_base,
                )
            )
            for sub_account in sub_accounts or []
        ]

        create_account_instr = v2_create_account_instruction(
            timestamp=test_scenario.start,
            v2_create_account=contract_sim.V2CreateAccount(
                account=contract_sim.CustomerAccountRequestBody(
                    id=account_config.account_id_base,
                    smart_contract_version_id=contract_config.smart_contract_version_id,
                    status=core_api.AccountV2Status.ACCOUNT_STATUS_OPEN,
                    permitted_denominations=account_config.permitted_denominations,
                ),
                create_options=(
                    contract_sim.CreateOptions(
                        parameter_values=param_values,
                        sub_accounts=create_sub_account_requests,
                    )
                    if (param_values or sub_accounts)
                    else None
                ),
            ),
        )

    contract_setup_events.append(create_account_instr)

    return contract_setup_events


def create_smart_contract_module_versions_link(
    timestamp: datetime,
    link_id: str,
    smart_contract_version_id: str,
    alias_to_contract_module_version_id: dict[str, str],
) -> SimulationEvent:
    """
    Returns a SimulationEvent containing that
    instructs the simulation to create a Smart Contract Module Version Link.
    """
    return SimulationEvent(
        timestamp,
        CreateSmartContractModuleVersionsLink(
            link_id,
            smart_contract_version_id,
            alias_to_contract_module_version_id,
        ).to_dict(),
    )


def v2_create_account_instruction(
    timestamp: datetime,
    v2_create_account: contract_sim.V2CreateAccount,
) -> SimulationEvent:
    create_options = _strip_clu_notation_from_create_options(v2_create_account.create_options)
    v2_create_account = contract_sim.V2CreateAccount(
        account=v2_create_account.account, create_options=create_options
    )
    return SimulationEvent(timestamp, v2_create_account.sim_instruction())


def create_sub_account_instruction(
    event_datetime: datetime,
    sub_account_id: str,
    sub_account_type: str,
    status: core_api.SubAccountStatus,
    account_id: str,
    request_id: str | None = None,
    name: str | None = None,
    details: dict[str, str] | None = None,
) -> SimulationEvent:
    """
    Instructs the simulation to create a Sub-Account on an existing Account.

    :param event_datetime: the datetime at which the Sub-Account creation will be applied in the
        simulation.
    :param sub_account_id: the ID of the Sub-Account being created.
    :param sub_account_type: the type of the Sub-Account being created. Must be in the contract's
        metadata.
    :param status: the new status to be applied to the Sub-Account.
    :param account_id: the ID of the parent Account of the Sub-Account.
    :param request_id: optional, the request ID of the instruction.
        Each create_sub_account_instruction must have a unique request_id
    :param name: optional, the name of the Sub-Account.
    :param details: optional, dictionary of additional details of Sub-Account.
    :return: a simulation event for creating a Sub-Account.
    """
    return SimulationEvent(
        time=event_datetime,
        event=contract_sim.CreateSubAccount(
            request_id=request_id,
            sub_account=core_api.SubAccountCreateSubAccount(
                id=sub_account_id,
                type=sub_account_type,
                account_id=account_id,
                status=status,
                name=name,
                details=details,
            ),
        ).sim_instruction(),
    )


def _strip_clu_notation_from_create_options(
    create_options: contract_sim.CreateOptions | None = None,
) -> contract_sim.CreateOptions | None:
    if not create_options:
        return create_options

    create_options_parameter_values = {
        strip_clu_notation(id): parameter_value
        for id, parameter_value in (create_options.parameter_values or {}).items()
    }
    return contract_sim.CreateOptions(
        parameter_values=create_options_parameter_values, sub_accounts=create_options.sub_accounts
    )


def _v2_update_account_instruction(
    timestamp: datetime,
    v2_update_account: contract_sim.V2UpdateAccount,
) -> SimulationEvent:
    return SimulationEvent(timestamp, v2_update_account.sim_instruction())


def v2_update_account_status(
    timestamp: datetime,
    account_id: str,
    status: core_api.AccountV2Status,
) -> SimulationEvent:
    return _v2_update_account_instruction(
        timestamp=timestamp,
        v2_update_account=contract_sim.V2UpdateAccount(
            account=contract_sim.UpdateAccountV2Account(id_=account_id, status=status),
            update_mask=core_api.UpdateMask(paths=["status"]),
        ),
    )


def v2_update_account_smart_contract_version_id(
    timestamp: datetime,
    account_id: str,
    # Can this be a string directly or does it need to be inferred from ContractConfig?
    smart_contract_version_id: str,
) -> SimulationEvent:
    return _v2_update_account_instruction(
        timestamp=timestamp,
        v2_update_account=contract_sim.V2UpdateAccount(
            account=contract_sim.UpdateAccountV2Account(
                id_=account_id, smart_contract_version_id=smart_contract_version_id
            ),
            update_mask=core_api.UpdateMask(paths=["smart_contract_version_id"]),
        ),
    )


def v2_update_account_parameter_value_hierarchy_node_id(
    timestamp: datetime,
    account_id: str,
    parameter_value_hierarchy_node_id: str,
) -> SimulationEvent:
    """
    Returns a SimulationEvent that instructs the simulation to update the Parameter Value
    Hierarchy Node of a V2 account.
    All fields are required
    :param timestamp: the datetime at which the Update Account V2 will be applied in the simulation.
    :param account_id: the v2 account ID whose parameter value hierarchy node association needs
        to be updated.
    :param parameter_value_hierarchy_node: the parameter value hierarchy node ID to be
        associated to the V2 account. Can be empty to disassociate to from the parameter value
        hierarchy.
    :return: SimulationEvent for updating a v2 account's parameter value hierarchy node association.
    """
    return _v2_update_account_instruction(
        timestamp=timestamp,
        v2_update_account=contract_sim.V2UpdateAccount(
            account=contract_sim.UpdateAccountV2Account(
                id_=account_id,
                parameter_value_hierarchy_node_id=parameter_value_hierarchy_node_id,
            ),
            update_mask=core_api.UpdateMask(paths=["parameter_value_hierarchy_node_id"]),
        ),
    )


def _datetime_to_rfc_3339(dt):
    timezone_aware = dt.tzinfo is not None and dt.tzinfo.utcoffset(dt) is not None

    if not timezone_aware:
        raise ValueError("The datetime object passed in is not timezone-aware")

    return dt.astimezone().isoformat()


def list_account_attribute_values(
    timestamp: datetime,
    list_account_attribute_values: contract_sim.ListAccountAttributeValues,
) -> SimulationEvent:
    return SimulationEvent(time=timestamp, event=list_account_attribute_values.sim_instruction())


## Create SimulationEvents containing a Posting Instruction Batch
## where Value and Booking timestamps are set at the Posting
## Instruction Batch level (deprecated).
@deprecated(
    """
    PIB-level timestamps are deprecated as of Vault 5.5.
    Use `create_auth_adjustment_posting_instruction_event` instead with PI-level timestamps.
    """
)
def create_auth_adjustment_instruction(
    event_datetime: datetime,
    client_transaction_id: str,
    amount: Decimal | str | None = None,
    replacement_amount: Decimal | str | None = None,
    instruction_details: dict[str, str] | None = None,
    batch_details: dict[str, str] | None = None,
    client_batch_id: str = "",
    value_timestamp: datetime | None = None,
    booking_timestamp: datetime | None = None,
) -> SimulationEvent:
    """
    Creates a SimulationEvent for a Posting Instruction Batch with an AuthorisationAdjustment
    where Value and Booking timestamps are set at the Posting Instruction Batch level.

    :param event_datetime: the datetime at which the Posting Instruction Batch
        will be applied in the simulation.
    :param client_transaction_id: the ID of the client transaction this posting
        instruction is creating or mutating.
    :param amount: delta amount to be sent. Cannot be used in conjunction with `replacement_amount`.
    :param replacement_amount: new total authorised amount. Cannot be used in
        conjunction with `amount`.
    :param instruction_details: An optional mapping containing instruction level metadata.
    :param batch_details: A dictionary containing batch level metadata.
    :param client_batch_id: An id which allows related PostingInstructions
        to be associated with each other.
    :param value_timestamp: Optional value timestamp at which the Posting Instruction Batch
        will be applied in the simulation. If "None" defaults to event_datetime.
    :param booking_timestamp: Optional timestamp at which all committed postings within the Posting
        Instruction Batch are considered to be booked. Defaults to the generated insertion_timestamp
    :return: SimulationEvent with an AuthorisationAdjustment Posting Instruction Batch.
    """
    return _transform_posting_key(
        create_auth_adjustment_event_common(
            value_datetime=event_datetime,
            amount=amount,
            replacement_amount=replacement_amount,
            client_transaction_id=client_transaction_id,
            instruction_details=instruction_details,
            batch_details=batch_details,
            client_batch_id=client_batch_id,
            pib_timestamp=value_timestamp,
            booking_datetime=booking_timestamp,
        )
    )


@deprecated(
    """
    PIB-level timestamps are deprecated as of Vault 5.5.
    Use `create_custom_instruction_posting_instruction_event` instead with PI-level timestamps.
    """
)
def create_custom_instruction(
    amount: str,
    debtor_target_account_id: str,
    creditor_target_account_id: str,
    debtor_target_account_address: str,
    creditor_target_account_address: str,
    event_datetime: datetime,
    client_transaction_id: str = "",
    denomination: str | None = None,
    instruction_details: dict[str, str] | None = None,
    batch_details: dict[str, str] | None = None,
    client_batch_id: str = "",
    value_timestamp: datetime | None = None,
    booking_timestamp: datetime | None = None,
    debtor_target_sub_account_id: str | None = None,
    creditor_target_sub_account_id: str | None = None,
) -> SimulationEvent:
    """
    Creates a SimulationEvent for a Posting Instruction Batch with a CustomInstruction
    where Value and Booking timestamps are set at the Posting Instruction Batch level.

    :param amount: string representation of the amount to be sent
    :param debtor_target_account_id: account from which the money should be debited
    :param creditor_target_account_id: account to which the money should be credited to
    :param debtor_target_account_address: address from which the money should be debited
    :param creditor_target_account_address: address to which the money should be credited to
    :param event_datetime: the datetime at which the Posting Instruction Batch
        will be applied in the simulation
    :param client_transaction_id: the ID of the client transaction this posting
        instruction is creating or mutating.
    :param denomination: the denomination the posting instruction will be in.
    :param instruction_details: An optional mapping containing instruction level metadata.
    :param batch_details: A dictionary containing batch level metadata.
    :param client_batch_id: An id which allows related PostingInstructions
        to be associated with each other.
    :param value_timestamp: Optional value timestamp at which the Posting Instruction Batch
        will be applied in the simulation. If "None" defaults to event_datetime.
    :param booking_timestamp: Optional timestamp at which all committed postings within the Posting
        Instruction Batch are considered to be booked. Defaults to the generated insertion_timestamp
    :param debtor_target_sub_account_id: Optional Sub-Account ID targeting a specific
        debtor Sub-Account.
    :param creditor_target_sub_account_id: Optional Sub-Account ID targeting a specific
        creditor Sub-Account.
    :return: SimulationEvent with a CustomInstruction Posting Instruction Batch.
    """
    return _transform_posting_key(
        create_custom_instruction_event_common(
            amount=amount,
            debtor_target_account_id=debtor_target_account_id,
            creditor_target_account_id=creditor_target_account_id,
            debtor_target_account_address=debtor_target_account_address,
            creditor_target_account_address=creditor_target_account_address,
            value_datetime=event_datetime,
            client_transaction_id=client_transaction_id,
            denomination=denomination,
            instruction_details=instruction_details,
            batch_details=batch_details,
            client_batch_id=client_batch_id,
            pib_timestamp=value_timestamp,
            booking_datetime=booking_timestamp,
            debtor_target_sub_account_id=debtor_target_sub_account_id,
            creditor_target_sub_account_id=creditor_target_sub_account_id,
        )
    )


@deprecated(
    """
    PIB-level timestamps are deprecated as of Vault 5.5.
    Use `create_inbound_authorisation_posting_instruction_event` instead with PI-level timestamps.
    """
)
def create_inbound_authorisation_instruction(
    amount: str,
    event_datetime: datetime,
    target_account_id: str | None = None,
    internal_account_id: str | None = None,
    denomination: str | None = None,
    client_transaction_id: str = "",
    instruction_details: dict[str, str] | None = None,
    batch_details: dict[str, str] | None = None,
    client_batch_id: str = "",
    value_timestamp: datetime | None = None,
    booking_timestamp: datetime | None = None,
    target_account_address: str | None = None,
    asset: str | None = None,
    target_sub_account_id: str | None = None,
) -> SimulationEvent:
    """
    Creates a SimulationEvent for a Posting Instruction Batch with an InboundAuthorisation
    where Value and Booking timestamps are set at the Posting Instruction Batch level.

    :param amount: string representation of the amount to be sent.
    :param event_datetime: the datetime at which the event will be applied in the simulation
    :param target_account_id: Target customer account id for posting instruction
    :param internal_account_id: internal account id for posting instruction
    :param denomination: the denomination the posting instruction will be in.
    :param client_transaction_id: the ID of the client transaction this posting
        instruction is creating or mutating.
    :param instruction_details: An optional mapping containing instruction level metadata.
    :param batch_details: A dictionary containing batch level metadata.
    :param client_batch_id: An id which allows related PostingInstructions
        to be associated with each other.
    :param value_timestamp: Optional value timestamp at which the Posting Instruction Batch
        will be applied in the simulation. If "None" defaults to event_datetime.
    :param booking_timestamp: Optional timestamp at which all committed postings within the Posting
        Instruction Batch are considered to be booked. Defaults to the generated insertion_timestamp
    :param target_account_address: Optional the address of the account being targetted.
        If the target_sub_account_id is set, the target_account_address for that
        Sub-Account ID must be set.
    :param asset: asset type of the financial movement
    :param target_sub_account_id: Optional Sub-Account ID targeting a specific Sub-Account.
    :return: SimulationEvent with an InboundAuthorisation Posting Instruction Batch.
    """
    return _transform_posting_key(
        create_inbound_authorisation_event_common(
            amount=amount,
            value_datetime=event_datetime,
            denomination=denomination,
            client_transaction_id=client_transaction_id,
            instruction_details=instruction_details,
            batch_details=batch_details,
            client_batch_id=client_batch_id,
            target_account_id=target_account_id,
            internal_account_id=internal_account_id,
            pib_timestamp=value_timestamp,
            booking_datetime=booking_timestamp,
            target_account_address=target_account_address,
            asset=asset,
            target_sub_account_id=target_sub_account_id,
        )
    )


@deprecated(
    """
    PIB-level timestamps are deprecated as of Vault 5.5.
    Use `create_inbound_hard_settlement_posting_instruction_event` instead with PI-level timestamps.
    """
)
def create_inbound_hard_settlement_instruction(
    amount: str,
    event_datetime: datetime,
    target_account_id: str | None = None,
    internal_account_id: str | None = None,
    denomination: str | None = None,
    client_transaction_id: str = "",
    instruction_details: dict[str, str] | None = None,
    batch_details: dict[str, str] | None = None,
    client_batch_id: str = "",
    value_timestamp: datetime | None = None,
    booking_timestamp: datetime | None = None,
    target_account_address: str | None = None,
    asset: str | None = None,
    target_sub_account_id: str | None = None,
) -> SimulationEvent:
    """
    Creates a SimulationEvent for a Posting Instruction Batch with an InboundHardSettlement
    where Value and Booking timestamps are set at the Posting Instruction Batch level.

    :param amount: string representation of the amount to be sent.
    :param event_datetime: the datetime at which the event will be applied in the simulation.
    :param target_account_id: Target customer account id for posting instruction
    :param internal_account_id: internal account id for posting instruction
    :param denomination: the denomination the posting instruction will be in.
    :param client_transaction_id: the ID of the client transaction this posting
        instruction is creating or mutating.
    :param instruction_details: An optional mapping containing instruction level metadata.
    :param batch_details: A dictionary containing batch level metadata.
    :param client_batch_id: An id which allows related PostingInstructions
        to be associated with each other.
    :param value_timestamp: Optional value timestamp at which the Posting Instruction Batch
        will be applied in the simulation. If "None" defaults to event_datetime.
    :param booking_timestamp: Optional timestamp at which all committed postings within the Posting
        Instruction Batch are considered to be booked. Defaults to the generated insertion_timestamp
    :param target_account_address: account address to which the money should be sent
    :param asset: asset type of the financial movement
    :param target_sub_account_id: Optional Sub-Account ID targeting a specific Sub-Account.
    :return: SimulationEvent with an InboundHardSettlement Posting Instruction Batch.
    """
    return _transform_posting_key(
        create_inbound_hard_settlement_event_common(
            amount=amount,
            value_datetime=event_datetime,
            denomination=denomination,
            client_transaction_id=client_transaction_id,
            instruction_details=instruction_details,
            batch_details=batch_details,
            client_batch_id=client_batch_id,
            target_account_id=target_account_id,
            internal_account_id=internal_account_id,
            pib_timestamp=value_timestamp,
            booking_datetime=booking_timestamp,
            target_account_address=target_account_address,
            asset=asset,
            target_sub_account_id=target_sub_account_id,
        )
    )


@deprecated(
    """
    PIB-level timestamps are deprecated as of Vault 5.5.
    Use `create_outbound_authorisation_posting_instruction_event` instead with PI-level timestamps.
    """
)
def create_outbound_authorisation_instruction(
    amount: str,
    event_datetime: datetime,
    target_account_id: str | None = None,
    internal_account_id: str | None = None,
    denomination: str | None = None,
    client_transaction_id: str = "",
    instruction_details: dict[str, str] | None = None,
    batch_details: dict[str, str] | None = None,
    client_batch_id: str = "",
    value_timestamp: datetime | None = None,
    booking_timestamp: datetime | None = None,
    target_account_address: str | None = None,
    asset: str | None = None,
    target_sub_account_id: str | None = None,
) -> SimulationEvent:
    """
    Creates a SimulationEvent for a Posting Instruction Batch with an OutboundAuthorisation
    where Value and Booking timestamps are set at the Posting Instruction Batch level.

    :param amount: string representation of the amount to be sent.
    :param event_datetime: the datetime at which the event will be applied in the simulation.
    :param target_account_id: Target customer account id for posting instruction
    :param internal_account_id: internal account id for posting instruction
    :param denomination: the denomination the posting instruction will be in.
    :param client_transaction_id: the ID of the client transaction this posting
        instruction is creating or mutating.
    :param instruction_details: An optional mapping containing instruction level metadata.
    :param batch_details: A dictionary containing batch level metadata.
    :param client_batch_id: An id which allows related PostingInstructions
        to be associated with each other.
    :param value_timestamp: Optional value timestamp at which the Posting Instruction Batch
        will be applied in the simulation. If "None" defaults to event_datetime.
    :param booking_timestamp: Optional timestamp at which all committed postings within the Posting
        Instruction Batch are considered to be booked. Defaults to the generated insertion_timestamp
    :param target_account_address: Optional the address of the account being targetted.
        If the target_sub_account_id is set, the target_account_address for that
        Sub-Account ID must be set.
    :param asset: asset type of the financial movement
    :param target_sub_account_id: Optional Sub-Account ID targeting a specific Sub-Account.
    :return: SimulationEvent with an OutboundAuthorisation Posting Instruction Batch.
    """
    return _transform_posting_key(
        create_outbound_authorisation_event_common(
            amount=amount,
            value_datetime=event_datetime,
            denomination=denomination,
            client_transaction_id=client_transaction_id,
            instruction_details=instruction_details,
            batch_details=batch_details,
            client_batch_id=client_batch_id,
            target_account_id=target_account_id,
            internal_account_id=internal_account_id,
            pib_timestamp=value_timestamp,
            target_sub_account_id=target_sub_account_id,
            target_account_address=target_account_address,
            asset=asset,
            booking_datetime=booking_timestamp,
        )
    )


@deprecated(
    """
    PIB-level timestamps are deprecated as of Vault 5.5.
    Use `create_outbound_hard_settlement_posting_instruction_event` instead
    with PI-level timestamps.
    """
)
def create_outbound_hard_settlement_instruction(
    amount: str,
    event_datetime: datetime,
    target_account_id: str | None = None,
    internal_account_id: str | None = None,
    denomination: str | None = None,
    client_transaction_id: str = "",
    instruction_details: dict[str, str] | None = None,
    batch_details: dict[str, str] | None = None,
    client_batch_id: str = "",
    value_timestamp: datetime | None = None,
    booking_timestamp: datetime | None = None,
    target_account_address: str | None = None,
    asset: str | None = None,
    advice: bool | None = None,
    target_sub_account_id: str | None = None,
) -> SimulationEvent:
    """
    Creates a SimulationEvent for a Posting Instruction Batch with an OutboundHardSettlement
    where Value and Booking timestamps are set at the Posting Instruction Batch level.

    :param amount: string representation of the amount to be sent.
    :param event_datetime: the datetime at which the event will be applied in the simulation.
    :param target_account_id: Target customer account id for posting instruction
    :param internal_account_id: internal account id for posting instruction
    :param denomination: the denomination the posting instruction will be in.
    :param client_transaction_id: the ID of the client transaction this posting
        instruction is creating or mutating.
    :param instruction_details: An optional mapping containing instruction level metadata.
    :param batch_details: A dictionary containing batch level metadata.
    :param client_batch_id: An id which allows related PostingInstructions
        to be associated with each other.
    :param value_timestamp: Optional value timestamp at which the Posting Instruction Batch
        will be applied in the simulation. If "None" defaults to event_datetime.
    :param booking_timestamp: Optional timestamp at which all committed postings within the Posting
        Instruction Batch are considered to be booked. Defaults to the generated insertion_timestamp
    :param target_account_address: Optional the address of the account being targetted.
        If the target_sub_account_id is set, the target_account_address for that
        Sub-Account ID must be set.
    :param asset: asset type of the financial movement
    :param advice: if true, the amount will be authorised regardless of balance check
    :param target_sub_account_id: Optional Sub-Account ID targeting a specific Sub-Account.
    :return: SimulationEvent with an OutboundHardSettlement Posting Instruction Batch.
    """
    return _transform_posting_key(
        create_outbound_hard_settlement_event_common(
            amount=amount,
            value_datetime=event_datetime,
            denomination=denomination,
            client_transaction_id=client_transaction_id,
            instruction_details=instruction_details,
            batch_details=batch_details,
            client_batch_id=client_batch_id,
            target_account_id=target_account_id,
            internal_account_id=internal_account_id,
            pib_timestamp=value_timestamp,
            advice=advice,
            target_account_address=target_account_address,
            asset=asset,
            booking_datetime=booking_timestamp,
            target_sub_account_id=target_sub_account_id,
        )
    )


@deprecated(
    """
    PIB-level timestamps are deprecated as of Vault 5.5.
    Use `create_release_posting_instruction_event` instead with PI-level timestamps.
    """
)
def create_release_event(
    client_transaction_id: str,
    event_datetime: datetime,
    instruction_details: dict[str, str] | None = None,
    batch_details: dict[str, str] | None = None,
    client_batch_id: str = "",
    value_timestamp: datetime | None = None,
    require_pre_posting_hook_execution: bool = False,
    booking_timestamp: datetime | None = None,
) -> SimulationEvent:
    """
    Creates a SimulationEvent for a Posting Instruction Batch with a Release
    where Value and Booking timestamps are set at the Posting Instruction Batch level.

    :param client_transaction_id: the ID of the client transaction this posting
        instruction is creating or mutating.
    :param event_datetime: the datetime at which the event will be applied in the simulation.
    :param instruction_details: An optional mapping containing instruction level metadata.
    :param batch_details: A dictionary containing batch level metadata.
    :param client_batch_id: An id which allows related PostingInstructions
        to be associated with each other.
    :param value_timestamp: Optional value timestamp at which the Posting Instruction Batch
        will be applied in the simulation. If "None" defaults to event_datetime.
    :param require_pre_posting_hook_execution: A boolean that can ensure the pre-posting hook
        is executed when the release is processed
    :param booking_timestamp: Optional timestamp at which all committed postings within the Posting
        Instruction Batch are considered to be booked. Defaults to the generated insertion_timestamp
    :return: SimulationEvent with a Release Posting Instruction Batch.
    """
    return _transform_posting_key(
        create_release_event_common(
            client_transaction_id=client_transaction_id,
            value_datetime=event_datetime,
            instruction_details=instruction_details,
            batch_details=batch_details,
            client_batch_id=client_batch_id,
            pib_timestamp=value_timestamp,
            require_pre_posting_hook_execution=require_pre_posting_hook_execution,
            booking_datetime=booking_timestamp,
        )
    )


@deprecated(
    """
    PIB-level timestamps are deprecated as of Vault 5.5.
    Use `create_settlement_posting_instruction_event` instead with PI-level timestamps.
    """
)
def create_settlement_event(
    amount: str,
    client_transaction_id: str,
    event_datetime: datetime,
    instruction_details: dict[str, str] | None = None,
    batch_details: dict[str, str] | None = None,
    client_batch_id: str = "",
    final: bool = False,
    value_timestamp: datetime | None = None,
    require_pre_posting_hook_execution: bool = False,
    booking_timestamp: datetime | None = None,
) -> SimulationEvent:
    """
    Creates a SimulationEvent for a Posting Instruction Batch with a Settlement
    where Value and Booking timestamps are set at the Posting Instruction Batch level.

    :param amount: string representation of the amount to be sent.
    :param client_transaction_id: the ID of the client transaction this posting
        instruction is creating or mutating.
    :param event_datetime: the datetime at which the event will be applied in the simulation.
    :param instruction_details: An optional mapping containing instruction level metadata.
    :param batch_details: A dictionary containing batch level metadata.
    :param client_batch_id: An id which allows related PostingInstructions
        to be associated with each other.
    :param final: If true, any remaining amount authorised for the client_transaction_id will
        be released. Defaults to false.
    :param value_timestamp: Optional value timestamp at which the Posting Instruction Batch
        will be applied in the simulation. If "None" defaults to event_datetime.
    :param require_pre_posting_hook_execution: A boolean that can ensure the pre-posting hook
        is executed when the settlement is processed
    :param booking_timestamp: Optional timestamp at which all committed postings within the Posting
        Instruction Batch are considered to be booked. Defaults to the generated insertion_timestamp
    :return: SimulationEvent with a Settlement Posting Instruction Batch.
    """
    return _transform_posting_key(
        create_settlement_event_common(
            amount=amount,
            client_transaction_id=client_transaction_id,
            value_datetime=event_datetime,
            instruction_details=instruction_details,
            batch_details=batch_details,
            client_batch_id=client_batch_id,
            final=final,
            pib_timestamp=value_timestamp,
            require_pre_posting_hook_execution=require_pre_posting_hook_execution,
            booking_datetime=booking_timestamp,
        )
    )


@deprecated(
    """
    PIB-level timestamps are deprecated as of Vault 5.5.
    Use `create_transfer_posting_instruction_event` instead with PI-level timestamps.
    """
)
def create_transfer_instruction(
    amount: str,
    event_datetime: datetime,
    creditor_target_account_id: str,
    debtor_target_account_id: str,
    denomination: str = "",
    client_transaction_id: str = "",
    instruction_details: dict[str, str] | None = None,
    batch_details: dict[str, str] | None = None,
    client_batch_id: str = "",
    value_timestamp: datetime | None = None,
    booking_timestamp: datetime | None = None,
    debtor_target_sub_account_id: str | None = None,
    creditor_target_sub_account_id: str | None = None,
    debtor_target_account_address: str | None = None,
    creditor_target_account_address: str | None = None,
) -> SimulationEvent:
    """
    Creates a SimulationEvent for a Posting Instruction Batch with a Transfer
    where Value and Booking timestamps are set at the Posting Instruction Batch level.

    :param amount: string representation of the amount to be sent.
    :param event_datetime: the datetime at which the event will be applied in the simulation.
    :param creditor_target_account_id: account to credit for Transfer.
    :param debtor_target_account_id: account to debit for Transfer.
    :param denomination: the denomination the posting instruction will be in.
    :param client_transaction_id: the ID of the client transaction this posting
        instruction is creating or mutating.
    :param instruction_details: An optional mapping containing instruction level metadata.
    :param batch_details: A dictionary containing batch level metadata.
    :param client_batch_id: An id which allows related PostingInstructions
        to be associated with each other.
    :param value_timestamp: Optional value timestamp at which the Posting Instruction Batch
        will be applied in the simulation. If "None" defaults to event_datetime.
    :param booking_timestamp: Optional timestamp at which all committed postings within the Posting
        Instruction Batch are considered to be booked. Defaults to the generated insertion_timestamp
    :param debtor_target_sub_account_id: Optional Sub-Account ID targeting a specific
        debtor Sub-Account.
    :param creditor_target_sub_account_id: Optional Sub-Account ID targeting a specific
        creditor Sub-Account.
    :param debtor_target_account_address: Optional address targeting a specific debtor address.
    :param creditor_target_account_address: Optional address targeting a specific creditor address.
    :return: SimulationEvent with a Transfer Posting Instruction Batch.
    """
    return _transform_posting_key(
        create_transfer_event_common(
            amount=amount,
            value_datetime=event_datetime,
            creditor_target_account_id=creditor_target_account_id,
            debtor_target_account_id=debtor_target_account_id,
            denomination=denomination,
            client_transaction_id=client_transaction_id,
            instruction_details=instruction_details,
            batch_details=batch_details,
            client_batch_id=client_batch_id,
            pib_timestamp=value_timestamp,
            booking_datetime=booking_timestamp,
            debtor_target_sub_account_id=debtor_target_sub_account_id,
            creditor_target_sub_account_id=creditor_target_sub_account_id,
            debtor_target_account_address=debtor_target_account_address,
            creditor_target_account_address=creditor_target_account_address,
        )
    )


@deprecated(
    """
    PIB-level timestamps are deprecated as of Vault 5.5.
    Use `create_pib_from_posting_instructions` instead with PI-level timestamps.
    """
)
def create_posting_instruction_batch(
    instructions: list[Instruction],
    event_datetime: datetime,
    client_transaction_id: str = "",
    instruction_details: dict[str, str] | None = None,
    batch_details: dict[str, str] | None = None,
    client_batch_id: str = "",
    value_timestamp: datetime | None = None,
) -> SimulationEvent:
    """
    Creates a SimulationEvent containing a Posting Instruction Batch
    instructing any number of Instructions passed in as an argument.
    Posting Instruction level fields cannot be set here.

    :param instructions: list of Instructions to be included in the PIB.
    :param event_datetime: the datetime at which the event will be applied in the simulation.
    :param client_transaction_id: the ID of the client transaction this posting
        instruction is creating or mutating.
    :param instruction_details: An optional mapping containing instruction level metadata.
    :param batch_details: A dictionary containing batch level metadata.
    :param client_batch_id: An id which allows related PostingInstructions
        to be associated with each other.
    :param value_timestamp: Optional value timestamp at which the Posting Instruction Batch
        will be applied in the simulation. If "None" defaults to event_datetime.
    :return: SimulationEvent with a Posting Instruction Batch.
    """
    return _transform_posting_key(
        create_posting_instruction_batch_event_common(
            instructions,
            event_datetime,
            client_transaction_id=client_transaction_id,
            instruction_details=instruction_details,
            batch_details=batch_details,
            client_batch_id=client_batch_id,
            pib_timestamp=value_timestamp,
        )
    )


## Create SimulationEvents containing a Posting Instruction Batch
## where Posting Instruction level fields can be explicitly defined.
## Value and Booking timestamps are set at the Posting Instruction level.
def create_auth_adjustment_posting_instruction_event(
    event_datetime: datetime,
    client_transaction_id: str,
    amount: Decimal | str | None = None,
    replacement_amount: Decimal | str | None = None,
    advice: bool = False,
    instruction_details: dict[str, str] | None = None,
    override: bool = False,
    value_timestamp: datetime | None = None,
    booking_timestamp: datetime | None = None,
    client_id: str = "",
    client_batch_id: str = "",
    batch_details: dict[str, str] | None = None,
) -> SimulationEvent:
    """
    Creates a SimulationEvent for a Posting Instruction Batch with an AuthorisationAdjustment
    where Posting Instruction level fields can be explicitly defined.

    :param event_datetime: the datetime at which the event will be applied in the simulation.
    :param client_transaction_id: the ID of the client transaction this posting
        instruction is creating or mutating.
    :param amount: delta amount to be sent. Cannot be used in conjunction with `replacement_amount`.
    :param replacement_amount: new total authorised amount. Cannot be used in
        conjunction with `amount`.
    :param advice: If true, the posting instruction is not applied to the ledger and does not
        affect account balances. Defaults to false.
    :param instruction_details: An optional mapping containing instruction level metadata.
    :param override: If true, allows to override certain checks for this Posting Instruction.
        Defaults to false.
    :param value_timestamp: Optional timestamp at which the Posting Instruction.
        will be applied in the simulation. Defaults to the generated insertion_timestamp.
    :param booking_timestamp: Optional timestamp at which all committed postings within the Posting
        Instruction are considered to be booked. Defaults to the generated insertion_timestamp.
    :param client_id: An id to uniquely identify a client entity across the platform.
    :param client_batch_id: An id which allows related Posting Instructions
        to be associated with each other.
    :param batch_details: A dictionary containing batch level metadata.
    :return: SimulationEvent containing a Posting Instruction Batch with a single
        AuthorisationAdjustment Posting Instruction.
    """
    return _transform_posting_key(
        create_auth_adjustment_pi_event_common(
            event_datetime=event_datetime,
            client_transaction_id=client_transaction_id,
            amount=amount,
            replacement_amount=replacement_amount,
            advice=advice,
            instruction_details=instruction_details,
            override=override,
            value_timestamp=value_timestamp,
            booking_timestamp=booking_timestamp,
            client_id=client_id,
            client_batch_id=client_batch_id,
            batch_details=batch_details,
        )
    )


def create_custom_instruction_posting_instruction_event(
    event_datetime: datetime,
    amount: str,
    denomination: str,
    debtor_target_account_id: str,
    creditor_target_account_id: str,
    debtor_target_account_address: str | None = None,
    creditor_target_account_address: str | None = None,
    asset: str | None = None,
    phase: str | None = None,
    client_transaction_id: str = "",
    instruction_details: dict[str, str] | None = None,
    override: bool = False,
    value_timestamp: datetime | None = None,
    booking_timestamp: datetime | None = None,
    client_id: str = "",
    client_batch_id: str = "",
    batch_details: dict[str, str] | None = None,
    debtor_target_sub_account_id: str | None = None,
    creditor_target_sub_account_id: str | None = None,
) -> SimulationEvent:
    """
    Creates a SimulationEvent for a Posting Instruction Batch with a CustomInstruction
    where Posting Instruction level fields can be explicitly defined.

    :param event_datetime: the datetime at which the event will be applied in the simulation.
    :param amount: string representation of the amount to be sent.
    :param denomination: the denomination the posting instruction will be in.
    :param debtor_target_account_id: account from which the money should be debited.
    :param creditor_target_account_id: account to which the money should be credited to.
    :param debtor_target_account_address: Optional account address from which the money
        should be debited.
    :param creditor_target_account_address: Optional account address to which the money
        should be credited to.
    :param asset: Optional asset value of the posting.
    :param phase: refers to the stage of the posting in the transaction lifecycle.
    :param client_transaction_id: the ID of the client transaction this posting
        instruction is creating or mutating.
    :param instruction_details: An optional mapping containing instruction level metadata.
    :param override: If true, allows to override certain checks for this Posting Instruction.
        Defaults to false.
    :param value_timestamp: Optional timestamp at which the Posting Instruction
        will be applied in the simulation. Defaults to the generated insertion_timestamp.
    :param booking_timestamp: Optional timestamp at which all committed postings within the Posting
        Instruction are considered to be booked. Defaults to the generated insertion_timestamp.
    :param client_id: An id to uniquely identify a client entity across the platform.
    :param client_batch_id: An id which allows related Posting Instructions
        to be associated with each other.
    :param batch_details: A dictionary containing batch level metadata.
    :param debtor_target_sub_account_id: Optional Sub-Account ID targeting a specific
        debtor Sub-Account.
    :param creditor_target_sub_account_id: Optional Sub-Account ID targeting a specific
        creditor Sub-Account.
    :return: SimulationEvent containing a Posting Instruction Batch with a single
        CustomInstruction Posting Instruction.
    """
    return _transform_posting_key(
        create_custom_instruction_pi_event_common(
            event_datetime=event_datetime,
            amount=amount,
            denomination=denomination,
            debtor_target_account_id=debtor_target_account_id,
            creditor_target_account_id=creditor_target_account_id,
            debtor_target_account_address=debtor_target_account_address,
            creditor_target_account_address=creditor_target_account_address,
            asset=asset,
            phase=phase,
            client_transaction_id=client_transaction_id,
            instruction_details=instruction_details,
            override=override,
            value_timestamp=value_timestamp,
            booking_timestamp=booking_timestamp,
            client_id=client_id,
            client_batch_id=client_batch_id,
            batch_details=batch_details,
            debtor_target_sub_account_id=debtor_target_sub_account_id,
            creditor_target_sub_account_id=creditor_target_sub_account_id,
        )
    )


def create_inbound_authorisation_posting_instruction_event(
    event_datetime: datetime,
    client_transaction_id: str,
    amount: str,
    denomination: str,
    target_account_id: str | None = None,
    internal_account_id: str | None = None,
    advice: bool | None = None,
    target_account_address: str | None = None,
    asset: str | None = None,
    instruction_details: dict[str, str] | None = None,
    override: bool = False,
    value_timestamp: datetime | None = None,
    booking_timestamp: datetime | None = None,
    client_id: str = "",
    client_batch_id: str = "",
    batch_details: dict[str, str] | None = None,
    target_sub_account_id: str | None = None,
) -> SimulationEvent:
    """
    Creates a SimulationEvent for a Posting Instruction Batch with an InboundAuthorisation
    where Posting Instruction level fields can be explicitly defined.

    :param event_datetime: the datetime at which the event will be applied in the simulation.
    :param client_transaction_id: the ID of the client transaction this posting
        instruction is creating or mutating.
    :param amount: string representation of the amount to be sent.
    :param denomination: the denomination the posting instruction will be in.
    :param target_account_id: Target customer account id for posting instruction.
    :param internal_account_id: internal account id for posting instruction.
    :param advice: If true, the posting instruction is not applied to the ledger and does not
        affect account balances. Defaults to false.
    :param target_account_address: account address to which the money should be sent.
    :param asset: asset type of the financial movement.
    :param instruction_details: An optional mapping containing instruction level metadata.
    :param override: If true, allows to override certain checks for this Posting Instruction.
        Defaults to false.
    :param value_timestamp: Optional timestamp at which the Posting Instruction.
        will be applied in the simulation. Defaults to the generated insertion_timestamp.
    :param booking_timestamp: Optional timestamp at which all committed postings within the Posting
        Instruction are considered to be booked. Defaults to the generated insertion_timestamp.
    :param client_id: An id to uniquely identify a client entity across the platform.
    :param client_batch_id: An id which allows related Posting Instructions
        to be associated with each other.
    :param batch_details: A dictionary containing batch level metadata.
    :param target_sub_account_id: Optional Sub-Account ID targeting a specific Sub-Account.
    :return: SimulationEvent containing a Posting Instruction Batch with a single
        InboundAuthorisation Posting Instruction.
    """
    return _transform_posting_key(
        create_inbound_authorisation_pi_event_common(
            event_datetime=event_datetime,
            client_transaction_id=client_transaction_id,
            amount=amount,
            denomination=denomination,
            target_account_id=target_account_id,
            internal_account_id=internal_account_id,
            advice=advice,
            target_account_address=target_account_address,
            asset=asset,
            instruction_details=instruction_details,
            override=override,
            value_timestamp=value_timestamp,
            booking_timestamp=booking_timestamp,
            client_id=client_id,
            client_batch_id=client_batch_id,
            batch_details=batch_details,
            target_sub_account_id=target_sub_account_id,
        )
    )


def create_inbound_hard_settlement_posting_instruction_event(
    event_datetime: datetime,
    amount: str,
    denomination: str,
    target_account_id: str | None = None,
    internal_account_id: str | None = None,
    advice: bool | None = None,
    target_account_address: str | None = None,
    asset: str | None = None,
    client_transaction_id: str = "",
    instruction_details: dict[str, str] | None = None,
    override: bool = False,
    value_timestamp: datetime | None = None,
    booking_timestamp: datetime | None = None,
    client_id: str = "",
    client_batch_id: str = "",
    batch_details: dict[str, str] | None = None,
    target_sub_account_id: str | None = None,
) -> SimulationEvent:
    """
    Creates a SimulationEvent for a Posting Instruction Batch with an InboundHardSettlement
    where Posting Instruction level fields can be explicitly defined.

    :param event_datetime: the datetime at which the event will be applied in the simulation.
    :param amount: string representation of the amount to be sent.
    :param denomination: the denomination the posting instruction will be in.
    :param target_account_id: Target customer account id for posting instruction.
    :param internal_account_id: internal account id for posting instruction.
    :param advice: If true, the posting instruction is not applied to the ledger and does not
        affect account balances. Defaults to false.
    :param target_account_address: account address to which the money should be sent.
    :param asset: asset type of the financial movement.
    :param client_transaction_id: the ID of the client transaction this posting
        instruction is creating or mutating.
    :param instruction_details: An optional mapping containing instruction level metadata.
    :param override: If true, allows to override certain checks for this Posting Instruction.
        Defaults to false.
    :param value_timestamp: Optional timestamp at which the Posting Instruction.
        will be applied in the simulation. Defaults to the generated insertion_timestamp.
    :param booking_timestamp: Optional timestamp at which all committed postings within the Posting
        Instruction are considered to be booked. Defaults to the generated insertion_timestamp.
    :param client_id: An id to uniquely identify a client entity across the platform.
    :param client_batch_id: An id which allows related Posting Instructions
        to be associated with each other.
    :param batch_details: A dictionary containing batch level metadata.
    :param target_sub_account_id: Optional Sub-Account ID targeting a specific Sub-Account.
    :return: SimulationEvent containing a Posting Instruction Batch with a single
        InboundHardSettlement Posting Instruction.
    """
    return _transform_posting_key(
        create_inbound_hard_settlement_pi_event_common(
            event_datetime=event_datetime,
            amount=amount,
            denomination=denomination,
            target_account_id=target_account_id,
            internal_account_id=internal_account_id,
            advice=advice,
            target_account_address=target_account_address,
            asset=asset,
            client_transaction_id=client_transaction_id,
            instruction_details=instruction_details,
            override=override,
            value_timestamp=value_timestamp,
            booking_timestamp=booking_timestamp,
            client_id=client_id,
            client_batch_id=client_batch_id,
            batch_details=batch_details,
            target_sub_account_id=target_sub_account_id,
        )
    )


def create_outbound_authorisation_posting_instruction_event(
    event_datetime: datetime,
    client_transaction_id: str,
    amount: str,
    denomination: str,
    target_account_id: str | None = None,
    internal_account_id: str | None = None,
    advice: bool | None = None,
    target_account_address: str | None = None,
    asset: str | None = None,
    instruction_details: dict[str, str] | None = None,
    override: bool = False,
    value_timestamp: datetime | None = None,
    booking_timestamp: datetime | None = None,
    client_id: str = "",
    client_batch_id: str = "",
    batch_details: dict[str, str] | None = None,
    target_sub_account_id: str | None = None,
) -> SimulationEvent:
    """
    Creates a SimulationEvent for a Posting Instruction Batch with an OutboundAuthorisation
    where Posting Instruction level fields can be explicitly defined.

    :param event_datetime: the datetime at which the event will be applied in the simulation.
    :param client_transaction_id: the ID of the client transaction this posting
        instruction is creating or mutating.
    :param amount: string representation of the amount to be sent.
    :param denomination: the denomination the posting instruction will be in.
    :param target_account_id: Target customer account id for posting instruction.
    :param internal_account_id: internal account id for posting instruction.
    :param advice: If true, the posting instruction is not applied to the ledger and does not
        affect account balances. Defaults to false.
    :param target_account_address: account address to which the money should be sent.
    :param asset: asset type of the financial movement.
    :param instruction_details: An optional mapping containing instruction level metadata.
    :param override: If true, allows to override certain checks for this Posting Instruction.
        Defaults to false.
    :param value_timestamp: Optional timestamp at which the Posting Instruction.
        will be applied in the simulation. Defaults to the generated insertion_timestamp.
    :param booking_timestamp: Optional timestamp at which all committed postings within the Posting
        Instruction are considered to be booked. Defaults to the generated insertion_timestamp.
    :param client_id: An id to uniquely identify a client entity across the platform.
    :param client_batch_id: An id which allows related Posting Instructions
        to be associated with each other.
    :param batch_details: A dictionary containing batch level metadata.
    :param target_sub_account_id: Optional Sub-Account ID targeting a specific Sub-Account.
    :return: SimulationEvent containing a Posting Instruction Batch with a single
        OutboundAuthorisation Posting Instruction.
    """
    return _transform_posting_key(
        create_outbound_authorisation_pi_event_common(
            event_datetime=event_datetime,
            client_transaction_id=client_transaction_id,
            amount=amount,
            denomination=denomination,
            target_account_id=target_account_id,
            internal_account_id=internal_account_id,
            advice=advice,
            target_account_address=target_account_address,
            asset=asset,
            instruction_details=instruction_details,
            override=override,
            value_timestamp=value_timestamp,
            booking_timestamp=booking_timestamp,
            client_id=client_id,
            client_batch_id=client_batch_id,
            batch_details=batch_details,
            target_sub_account_id=target_sub_account_id,
        )
    )


def create_outbound_hard_settlement_posting_instruction_event(
    event_datetime: datetime,
    amount: str,
    denomination: str,
    target_account_id: str | None = None,
    internal_account_id: str | None = None,
    advice: bool | None = None,
    target_account_address: str | None = None,
    asset: str | None = None,
    client_transaction_id: str = "",
    instruction_details: dict[str, str] | None = None,
    override: bool = False,
    value_timestamp: datetime | None = None,
    booking_timestamp: datetime | None = None,
    client_id: str = "",
    client_batch_id: str = "",
    batch_details: dict[str, str] | None = None,
    target_sub_account_id: str | None = None,
) -> SimulationEvent:
    """
    Creates a SimulationEvent for a Posting Instruction Batch with an OutboundHardSettlement
    where Posting Instruction level fields can be explicitly defined.

    :param event_datetime: the datetime at which the event will be applied in the simulation.
    :param amount: string representation of the amount to be sent.
    :param denomination: the denomination the posting instruction will be in.
    :param target_account_id: Target customer account id for posting instruction.
    :param internal_account_id: internal account id for posting instruction.
    :param advice: If true, the posting instruction is not applied to the ledger and does not
        affect account balances. Defaults to false.
    :param target_account_address: account address to which the money should be sent.
    :param asset: asset type of the financial movement.
    :param client_transaction_id: the ID of the client transaction this posting
        instruction is creating or mutating.
    :param instruction_details: An optional mapping containing instruction level metadata.
    :param override: If true, allows to override certain checks for this Posting Instruction.
        Defaults to false.
    :param value_timestamp: Optional timestamp at which the Posting Instruction.
        will be applied in the simulation. Defaults to the generated insertion_timestamp.
    :param booking_timestamp: Optional timestamp at which all committed postings within the Posting
        Instruction are considered to be booked. Defaults to the generated insertion_timestamp.
    :param client_id: An id to uniquely identify a client entity across the platform.
    :param client_batch_id: An id which allows related Posting Instructions
        to be associated with each other.
    :param batch_details: A dictionary containing batch level metadata.
    :param target_sub_account_id: Optional Sub-Account ID targeting a specific Sub-Account.
    :return: SimulationEvent containing a Posting Instruction Batch with a single
        OutboundHardSettlement Posting Instruction.
    """
    return _transform_posting_key(
        create_outbound_hard_settlement_pi_event_common(
            event_datetime=event_datetime,
            amount=amount,
            denomination=denomination,
            target_account_id=target_account_id,
            internal_account_id=internal_account_id,
            advice=advice,
            target_account_address=target_account_address,
            asset=asset,
            client_transaction_id=client_transaction_id,
            instruction_details=instruction_details,
            override=override,
            value_timestamp=value_timestamp,
            booking_timestamp=booking_timestamp,
            client_id=client_id,
            client_batch_id=client_batch_id,
            batch_details=batch_details,
            target_sub_account_id=target_sub_account_id,
        )
    )


def create_release_posting_instruction_event(
    event_datetime: datetime,
    client_transaction_id: str,
    require_pre_posting_hook_execution: bool = False,
    instruction_details: dict[str, str] | None = None,
    override: bool = False,
    value_timestamp: datetime | None = None,
    booking_timestamp: datetime | None = None,
    client_id: str = "",
    client_batch_id: str = "",
    batch_details: dict[str, str] | None = None,
) -> SimulationEvent:
    """
    Creates a SimulationEvent for a Posting Instruction Batch with a Release
    where Posting Instruction level fields can be explicitly defined.

    :param event_datetime: the datetime at which the event will be applied in the simulation.
    :param client_transaction_id: the ID of the client transaction this posting
        instruction is creating or mutating.
    :param require_pre_posting_hook_execution: If true, this ensures the pre-posting hook
        is executed when the settlement is processed. Defaults to false.
    :param instruction_details: An optional mapping containing instruction level metadata.
    :param override: If true, allows to override certain checks for this Posting Instruction.
        Defaults to false.
    :param value_timestamp: Optional timestamp at which the Posting Instruction.
        will be applied in the simulation. Defaults to the generated insertion_timestamp.
    :param booking_timestamp: Optional timestamp at which all committed postings within the Posting
        Instruction are considered to be booked. Defaults to the generated insertion_timestamp.
    :param client_id: An id to uniquely identify a client entity across the platform.
    :param client_batch_id: An id which allows related Posting Instructions
        to be associated with each other.
    :param batch_details: A dictionary containing batch level metadata.
    :return: SimulationEvent containing a Posting Instruction Batch with a single
        Release Posting Instruction.
    """
    return _transform_posting_key(
        create_release_pi_event_common(
            event_datetime=event_datetime,
            client_transaction_id=client_transaction_id,
            require_pre_posting_hook_execution=require_pre_posting_hook_execution,
            instruction_details=instruction_details,
            override=override,
            value_timestamp=value_timestamp,
            booking_timestamp=booking_timestamp,
            client_id=client_id,
            client_batch_id=client_batch_id,
            batch_details=batch_details,
        )
    )


def create_settlement_posting_instruction_event(
    event_datetime: datetime,
    client_transaction_id: str,
    amount: str,
    final: bool = False,
    require_pre_posting_hook_execution: bool = False,
    instruction_details: dict[str, str] | None = None,
    override: bool = False,
    value_timestamp: datetime | None = None,
    booking_timestamp: datetime | None = None,
    client_id: str = "",
    client_batch_id: str = "",
    batch_details: dict[str, str] | None = None,
) -> SimulationEvent:
    """
    Creates a SimulationEvent for a Posting Instruction Batch with a Settlement
    where Posting Instruction level fields can be explicitly defined.

    :param event_datetime: the datetime at which the event will be applied in the simulation.
    :param client_transaction_id: the ID of the client transaction this posting
        instruction is creating or mutating.
    :param amount: string representation of the amount to be sent.
    :param final: If true, any remaining amount authorised for the client_transaction_id will
        be released. Defaults to false.
    :param require_pre_posting_hook_execution: If true, this ensures the pre-posting hook
        is executed when the settlement is processed. Defaults to false.
    :param instruction_details: An optional mapping containing instruction level metadata.
    :param override: If true, allows to override certain checks for this Posting Instruction.
        Defaults to false.
    :param value_timestamp: Optional timestamp at which the Posting Instruction.
        will be applied in the simulation. Defaults to the generated insertion_timestamp.
    :param booking_timestamp: Optional timestamp at which all committed postings within the Posting
        Instruction are considered to be booked. Defaults to the generated insertion_timestamp.
    :param client_id: An id to uniquely identify a client entity across the platform.
    :param client_batch_id: An id which allows related Posting Instructions
        to be associated with each other.
    :param batch_details: A dictionary containing batch level metadata.
    :return: SimulationEvent containing a Posting Instruction Batch with a single
        Settlement Posting Instruction.
    """
    return _transform_posting_key(
        create_settlement_pi_event_common(
            event_datetime=event_datetime,
            client_transaction_id=client_transaction_id,
            amount=amount,
            final=final,
            require_pre_posting_hook_execution=require_pre_posting_hook_execution,
            instruction_details=instruction_details,
            override=override,
            value_timestamp=value_timestamp,
            booking_timestamp=booking_timestamp,
            client_id=client_id,
            client_batch_id=client_batch_id,
            batch_details=batch_details,
        )
    )


def create_transfer_posting_instruction_event(
    event_datetime: datetime,
    amount: str,
    denomination: str,
    debtor_target_account_id: str,
    creditor_target_account_id: str,
    client_transaction_id: str = "",
    instruction_details: dict[str, str] | None = None,
    override: bool = False,
    value_timestamp: datetime | None = None,
    booking_timestamp: datetime | None = None,
    client_id: str = "",
    client_batch_id: str = "",
    batch_details: dict[str, str] | None = None,
    debtor_target_sub_account_id: str | None = None,
    creditor_target_sub_account_id: str | None = None,
    debtor_target_account_address: str | None = None,
    creditor_target_account_address: str | None = None,
) -> SimulationEvent:
    """
    Creates a SimulationEvent for a Posting Instruction Batch with a Transfer
    where Posting Instruction level fields can be explicitly defined.

    :param event_datetime: the datetime at which the event will be applied in the simulation.
    :param amount: string representation of the amount to be sent.
    :param denomination: the denomination the posting instruction will be in.
    :param debtor_target_account_id: account to debit for Transfer.
    :param creditor_target_account_id: account to credit for Transfer.
    :param client_transaction_id: the ID of the client transaction this posting
        instruction is creating or mutating.
    :param instruction_details: An optional mapping containing instruction level metadata.
    :param override: If true, allows to override certain checks for this Posting Instruction.
        Defaults to false.
    :param value_timestamp: Optional timestamp at which the Posting Instruction
        will be applied in the simulation. Defaults to the generated insertion_timestamp.
    :param booking_timestamp: Optional timestamp at which all committed postings within the Posting
        Instruction are considered to be booked. Defaults to the generated insertion_timestamp.
    :param client_id: An id to uniquely identify a client entity across the platform.
    :param client_batch_id: An id which allows related Posting Instructions
        to be associated with each other.
    :param batch_details: A dictionary containing batch level metadata.
    :param debtor_target_sub_account_id: Optional Sub-Account ID targeting a specific
        debtor Sub-Account.
    :param creditor_target_sub_account_id: Optional Sub-Account ID targeting a specific
        creditor Sub-Account.
    :param debtor_target_account_address: Optional address targeting a specific debtor address.
    :param creditor_target_account_address: Optional address targeting a specific creditor address.
    :return: SimulationEvent containing a Posting Instruction Batch with a single
        Transfer Posting Instruction.
    """
    return _transform_posting_key(
        create_transfer_pi_event_common(
            event_datetime=event_datetime,
            amount=amount,
            denomination=denomination,
            debtor_target_account_id=debtor_target_account_id,
            creditor_target_account_id=creditor_target_account_id,
            client_transaction_id=client_transaction_id,
            instruction_details=instruction_details,
            override=override,
            value_timestamp=value_timestamp,
            booking_timestamp=booking_timestamp,
            client_id=client_id,
            client_batch_id=client_batch_id,
            batch_details=batch_details,
            debtor_target_sub_account_id=debtor_target_sub_account_id,
            creditor_target_sub_account_id=creditor_target_sub_account_id,
            debtor_target_account_address=debtor_target_account_address,
            creditor_target_account_address=creditor_target_account_address,
        )
    )


def create_pib_from_posting_instructions(
    instructions: Sequence[PostingInstruction],
    event_datetime: datetime,
    batch_details: dict[str, str] | None = None,
    client_batch_id: str = "",
) -> SimulationEvent:
    """
    Creates a SimulationEvent containing a Posting Instruction Batch
    instructing any number of Posting Instructions passed in as an argument,
    allowing Posting Instruction level fields to be explicitly defined.

    :param instructions: list of Posting Instructions to be included in the PIB.
    :param event_datetime: the datetime at which the event will be applied in the simulation.
    :param batch_details: A dictionary containing batch level metadata.
    :param client_batch_id: An id which allows related PostingInstructions
        to be associated with each other.
    :return: SimulationEvent with a Posting Instruction Batch.
    """
    return _transform_posting_key(
        create_pib_posting_instruction_event_common(
            instructions=instructions,
            event_datetime=event_datetime,
            batch_details=batch_details,
            client_batch_id=client_batch_id,
        )
    )


def create_parameter_resource_mapping(
    globally_owned_parameter_values: dict[str, core_api.ParameterValue],
) -> dict[str, tuple[core_api.ParameterValue, str]]:
    """
    Create the mapping of parameter_id to tuple (parameter_value, parameter_value_id)
    where parameter_value_id is a uuid.

    For parameter values created via account creation in simulation test,
    the parameter_value_id cannot be inferred (or passed in beforehand) and hence the simulation
    request cannot use update_parameter_value to modify the parameter value.

    :param globally_owned_parameter_values: mapping of {parameter_id: parameter_value} for
        globally owned parameter values to be created
    :return: mapping of parameter_id to tuple (parameter_value, parameter_value_id)
    """

    return {
        parameter_id: (parameter_value, str(uuid.uuid4()))
        for parameter_id, parameter_value in globally_owned_parameter_values.items()
    }


def update_pgtz_instruction(
    event_datetime: datetime,
    timezone: ZoneInfo = UTC,
    processing_group: str = DEFAULT_PG,
) -> SimulationEvent:
    """
    Returns a Simulation instruction event to update the Processing Group Time Zone (PGTZ).

    :param event_datetime: the datetime at which the PGTZ update will be applied in the simulation.
    :param timezone: the new timezone for the processing group.
    :param processing_group: the ID of the processing group to update.
    :return: SimulationEvent with an instruction to update the processing group timezone.
    """
    instruction = UpdateProcessingGroup(
        processing_group=ProcessingGroup(
            id=processing_group,
            timezone=timezone,
        ),
        update_mask=UpdateMask(paths=["timezone"]),
    )
    return SimulationEvent(
        time=event_datetime,
        event=instruction.sim_instruction(),
    )
