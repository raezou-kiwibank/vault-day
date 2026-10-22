from __future__ import annotations

# standard libs
from abc import ABC
from datetime import date
from enum import Enum
from typing import Any, TypeAlias, Union

# third party
from pydantic import BaseModel, Field, computed_field, model_validator
from pydantic.alias_generators import to_snake
from pydantic.functional_serializers import model_serializer

# inception sdk
import inception_sdk.vault.core_api as core_api
from inception_sdk.test_framework.common.date_helper import isoformat
from inception_sdk.vault.pydantic_types import (
    Datetime,
    Decimal_,
    OptionalDatetime,
    OptionalZoneInfo,
    VaultBaseModel,
)


class SimulationInstructionModel(VaultBaseModel):
    def sim_instruction(self) -> dict[str, Any]:
        instruction = to_snake(type(self).__name__)
        return {instruction: self.model_dump()}


class SmartContract(VaultBaseModel):
    code: str
    smart_contract_param_vals: dict[str, str]
    smart_contract_version_id: str


class ExistingContractOrModule(VaultBaseModel):
    id: str


class SupervisorContract(VaultBaseModel):
    code: str
    supervisor_contract_version_id: str


class ContractModule(VaultBaseModel):
    code: str
    contract_module_version_id: str


class IncludeDataTypes(str, Enum):
    UNKNOWN = "UNKNOWN"
    GLOBAL_PARAMETERS = "GLOBAL_PARAMETERS"
    TEMPLATE_PARAMETERS = "TEMPLATE_PARAMETERS"
    CALENDARS = "CALENDARS"


class ExistingAccount(VaultBaseModel):
    account_id: str
    is_internal: bool | None = None


class ExistingProductDataBehaviour(VaultBaseModel):
    include_all: bool
    include_data_types: list[IncludeDataTypes]


class CreateAccount(SimulationInstructionModel):
    product_version_id: str
    id: str
    instance_param_vals: dict[str, str] | None = None


class CreatePlan(SimulationInstructionModel):
    id: str
    supervisor_contract_version_id: str
    processing_group_id: str | None = None
    details: dict[str, str] | None = None


class CreateAccountPlanAssoc(SimulationInstructionModel):
    id: str
    account_id: str
    plan_id: str
    status: core_api.AccountPlanAssocStatus


class InstanceParamValsUpdate(VaultBaseModel):
    instance_param_vals: dict[str, str]


class ScheduleMigrationType(str, Enum):
    SCHEDULE_MIGRATION_TYPE_RECREATE_ALL_SCHEDULES_AND_GROUPS = (
        "SCHEDULE_MIGRATION_TYPE_RECREATE_ALL_SCHEDULES_AND_GROUPS"
    )
    SCHEDULE_MIGRATION_TYPE_PRESERVE_SCHEDULES_IF_NO_GROUP_CHANGES = (
        "SCHEDULE_MIGRATION_TYPE_PRESERVE_SCHEDULES_IF_NO_GROUP_CHANGES"
    )


class ProductVersionUpdate(VaultBaseModel):
    product_version_id: str
    instance_param_vals_to_add: dict[str, str]
    # deprecated as of Vault 4.6.0
    schedule_migration_type: ScheduleMigrationType


class CreateAccountUpdate(ABC, SimulationInstructionModel):
    id: str
    account_id: str
    create_timestamp: Datetime
    last_status_update_timestamp: Datetime
    account_update_batch_id: str

    def sim_instruction(self) -> dict[str, Any]:
        return {"create_account_update": BaseModel.model_dump(self)}


class CreateAccountUpdateWithInstanceParamValsUpdate(CreateAccountUpdate):
    # deprecated as of Vault 5.0.0.
    instance_param_vals_update: InstanceParamValsUpdate


class CreateAccountUpdateWithProductVersionUpdate(CreateAccountUpdate):
    product_version_update: ProductVersionUpdate


class CreateAccountUpdateWithActivationUpdate(CreateAccountUpdate):
    # deprecated as of Vault 5.0.0.  Only needs to be empty dict {}.
    activation_update: dict[None, None] = Field(default_factory=dict)


class CreateAccountUpdateWithClosureUpdate(CreateAccountUpdate):
    # deprecated as of Vault 5.0.0.
    closure_update: dict[None, None] = Field(default_factory=dict)


class UpdateAccount(SimulationInstructionModel):
    id: str
    status: core_api.AccountStatus


# Accounts V2
AccountV2Status = core_api.AccountV2Status
AccountV2Type = core_api.AccountV2Type
ParameterValue = core_api.ParameterValue


class CreateSubAccount(SimulationInstructionModel):
    # No differences with CreateSubAccountRequest from core api
    request_id: str | None = None
    sub_account: core_api.SubAccountCreateSubAccount


class CreateOptions(SimulationInstructionModel):
    parameter_values: dict[str, ParameterValue] | None = None
    sub_accounts: list[CreateSubAccount] | None = None


class CustomerAccountRequestBody(core_api._CreateAccountV2Account):
    # Differences with core api CustomerAccountRequestBody:
    # - no stakeholders in sim, so stakeholder_ids is removed
    smart_contract_version_id: str | None = None
    permitted_denominations: list[str] | None = None
    parameter_value_hierarchy_node_id: str | None = None

    @computed_field()
    def type(self) -> core_api.AccountV2Type:
        return AccountV2Type.ACCOUNT_TYPE_CUSTOMER


InternalAccountRequestBody = core_api.InternalAccountRequestBody


class V2CreateAccount(SimulationInstructionModel):
    account: CustomerAccountRequestBody | InternalAccountRequestBody
    create_options: CreateOptions | None = None


class UpdateAccountV2Account(VaultBaseModel):
    # Differences with core api:
    # - no stakeholders in sim, so stakeholder_ids is removed
    # - core_api model doesn't have account id as this is a path parameter on the endpoint
    # so `id_` is added
    # - no alias in sim, so alias is removed
    # - no details in sim, so details is removed
    id_: str = Field(serialization_alias="id")  # avoiding conflicts with python built ins
    smart_contract_version_id: str | None = None
    parameter_value_hierarchy_node_id: str | None = None
    status: AccountV2Status | None = None
    processing_label: str | None = None


class V2UpdateAccount(SimulationInstructionModel):
    account: UpdateAccountV2Account
    update_mask: core_api.UpdateMask


## Start: Simulation Request instructions types for postings.
class Restrictions(VaultBaseModel):
    all: bool | None = None
    restriction_set_ids: list[str] | None = None


class Override(VaultBaseModel):
    restrictions: Restrictions


class TransactionCode(VaultBaseModel):
    domain: str
    family: str
    subfamily: str


class TargetAccount(VaultBaseModel):
    account_id: str


class Authorisation(ABC, VaultBaseModel):
    amount: Decimal_
    denomination: str
    target_account: TargetAccount
    internal_account_id: str
    advice: bool
    target_account_address: str
    asset: str
    target_sub_account_id: str | None = None


class OutboundAuthorisation(Authorisation):
    pass


class InboundAuthorisation(Authorisation):
    pass


class AuthorisationAdjustment(VaultBaseModel):
    advice: bool
    amount: Decimal_
    replacement_amount: Decimal_


class Settlement(VaultBaseModel):
    amount: Decimal_ | None = None
    final: bool
    require_pre_posting_hook_execution: bool | None = None


class Release(VaultBaseModel):
    require_pre_posting_hook_execution: bool | None = None


class HardSettlement(ABC, VaultBaseModel):
    amount: Decimal_
    denomination: str
    target_account: TargetAccount
    internal_account_id: str
    advice: bool
    target_account_address: str
    asset: str
    target_sub_account_id: str | None = None


class InboundHardSettlement(HardSettlement):
    pass


class OutboundHardSettlement(HardSettlement):
    pass


class Transfer(VaultBaseModel):
    amount: Decimal_
    denomination: str
    debtor_target_account: TargetAccount
    creditor_target_account: TargetAccount
    debtor_target_sub_account_id: str | None = None
    creditor_target_sub_account_id: str | None = None
    debtor_target_account_address: str | None = None
    creditor_target_account_address: str | None = None


class Posting(VaultBaseModel):
    credit: bool
    amount: Decimal_
    denomination: str
    account_id: str
    account_address: str
    asset: str
    phase: core_api.PostingPhase
    sub_account_id: str = ""


class CustomInstruction(VaultBaseModel):
    postings: list[Posting]


class PostingInstruction(VaultBaseModel):
    client_transaction_id: str
    # deprecated as of Vault 4.0.0
    pics: list[str] | None = None
    instruction_details: dict[str, str] | None = None
    override: Override | None = None
    transaction_code: TransactionCode | None = None
    batch_details: dict[str, str] | None = None
    value_timestamp: OptionalDatetime = None
    booking_timestamp: OptionalDatetime = None
    # Posting types.  Only one of these should be populated.
    outbound_authorisation: OutboundAuthorisation | None = None
    inbound_authorisation: InboundAuthorisation | None = None
    authorisation_adjustment: AuthorisationAdjustment | None = None
    settlement: Settlement | None = None
    release: Release | None = None
    inbound_hard_settlement: InboundHardSettlement | None = None
    outbound_hard_settlement: OutboundHardSettlement | None = None
    transfer: Transfer | None = None
    custom_instruction: CustomInstruction | None = None

    @model_validator(mode="before")
    @classmethod
    def validate_model(cls, data: Any) -> Any:
        """
        Check that only one field is populated out of all the posting types.".
        """
        if isinstance(data, dict):
            cls.one_of_validator(
                data,
                field_names=[
                    "outbound_authorisation",
                    "inbound_authorisation",
                    "authorisation_adjustment",
                    "settlement",
                    "release",
                    "inbound_hard_settlement",
                    "outbound_hard_settlement",
                    "transfer",
                    "custom_instruction",
                ],
            )

        return data


class CreatePostingInstructionBatch(SimulationInstructionModel):
    client_id: str
    client_batch_id: str
    posting_instructions: list[PostingInstruction]


class NumberType(VaultBaseModel):
    value_type: core_api.NumberValueType
    min_value: Decimal_
    max_value: Decimal_
    step: Decimal_


class StringType(VaultBaseModel):
    pass


class DenominationType(VaultBaseModel):
    permitted_denominations: list[str]


class DateValue(VaultBaseModel):
    year: int
    month: int
    day: int

    @model_serializer
    def serialize_model(self):
        return date(self.year, self.month, self.day).isoformat()


class DateType(VaultBaseModel):
    # deprecated as of Vault 3.0.0.
    type: core_api.DateValueType | None = None
    start: DateValue
    end: DateValue


class GlobalParameter(VaultBaseModel):
    id: str
    display_name: str
    description: str
    number: NumberType | None = None
    str_: StringType | None = Field(default=None, serialization_alias="str")
    denomination: DenominationType | None = None
    date_: DateType | None = Field(default=None, serialization_alias="date")

    @model_validator(mode="before")
    @classmethod
    def validate_model(cls, data: Any) -> Any:
        """
        Check that only one field is populated out of "number", "str_", "denomination",
        and "date_".
        """
        if isinstance(data, dict):
            cls.one_of_validator(data, field_names=["number", "str_", "denomination", "date_"])

        return data


class CreateGlobalParameter(SimulationInstructionModel):
    global_parameter: GlobalParameter
    initial_value: str


class CreateGlobalParameterValue(SimulationInstructionModel):
    global_parameter_id: str
    value: str
    effective_timestamp: Datetime


class CreateFlagDefinition(SimulationInstructionModel):
    id: str


class CreateFlag(ABC, SimulationInstructionModel):
    def sim_instruction(self) -> dict[str, Any]:
        return {"create_flag": BaseModel.model_dump(self)}


class CreateFlagForAccount(core_api.CreateFlagV1CreateAccountFlag, CreateFlag):
    pass


class CreateFlagForCustomer(core_api.CreateFlagV1CreateCustomerFlag, CreateFlag):
    pass


class CreateFlagForPaymentDevice(core_api.CreateFlagV1CreatePaymentDeviceId, CreateFlag):
    pass


class UpdateSmartContractParam(SimulationInstructionModel):
    smart_contract_version_id: str
    parameter_name: str
    new_parameter_value: str


class CreateParameter(core_api.AbstractParameterResource, SimulationInstructionModel):
    pass


class CreateParameterValue(
    core_api.CreateParameterValueV1ParameterValue, SimulationInstructionModel
):
    """
    :param id: Optional. parameter_value.id is generated during creation and
    is required for update requests. In the e2e framework, this is handled
    automatically, so there's no need to manually provide it. However, the
    simulation framework performs creation and update in a single call and
    doesn’t return the generated id. As a result, the parameter_value.id must
    be manually created or defined beforehand when using the simulation endpoint.
    """

    id: str | None = None


class BatchCreateParameterValues(SimulationInstructionModel):
    # Differences with core api:
    # - no request_id
    parameter_values: list[core_api.CreateParameterValueV1ParameterValue]


class UpdateParameterValue(SimulationInstructionModel):
    parameter_value: core_api.UpdateParameterValueV1ParameterValue
    update_mask: core_api.UpdateMask


class CreateParameterValueHierarchyNode(SimulationInstructionModel):
    # Differences with core api:
    # - no request_id
    parameter_value_hierarchy_node: core_api.CreateParameterValueHierarchyNode


class CreateCalendar(SimulationInstructionModel):
    id: str
    display_name: str
    description: str


class CreateCalendarEvent(SimulationInstructionModel):
    id: str
    calendar_id: str
    start_timestamp: Datetime
    end_timestamp: Datetime


class CreateSmartContractModuleVersionsLink(SimulationInstructionModel):
    smart_contract_version_id: str
    alias_to_contract_module_version_id: dict[str, str]


class ProcessingGroup(VaultBaseModel):
    id: str
    timezone: OptionalZoneInfo
    status: core_api.ProcessingGroupStatus | None = None


class UpdateProcessingGroup(SimulationInstructionModel):
    processing_group: ProcessingGroup
    update_mask: core_api.UpdateMask
    # TODO (TM-127875): understand how these work in Sim before exposing them.
    # minimum_observation_timestamp_update_options: (
    #     core_api.MinimumObservationTimestampUpdateOptions | None
    # ) = None


class ListAccountAttributeValues(
    core_api._ListAccountAttributeValuesRequest, SimulationInstructionModel
):
    pass


SimulationInstruction: TypeAlias = Union[
    BatchCreateParameterValues,
    CreateAccount,
    CreateAccountPlanAssoc,
    CreateAccountUpdateWithActivationUpdate,
    CreateAccountUpdateWithClosureUpdate,
    CreateAccountUpdateWithInstanceParamValsUpdate,
    CreateAccountUpdateWithProductVersionUpdate,
    CreateCalendar,
    CreateCalendarEvent,
    CreateFlagDefinition,
    CreateFlagForAccount,
    CreateFlagForCustomer,
    CreateFlagForPaymentDevice,
    CreateGlobalParameter,
    CreateGlobalParameterValue,
    CreateParameter,
    CreateParameterValue,
    CreateParameterValueHierarchyNode,
    CreatePlan,
    CreatePostingInstructionBatch,
    CreatePostingInstructionBatch,
    CreateSmartContractModuleVersionsLink,
    CreateSubAccount,
    UpdateAccount,
    UpdateParameterValue,
    UpdateProcessingGroup,
    UpdateSmartContractParam,
    V2CreateAccount,
    V2UpdateAccount,
]


class Instruction(VaultBaseModel):
    timestamp: Datetime
    instruction: SimulationInstruction

    @model_serializer()
    def serialize_model(self):
        return {"timestamp": isoformat(self.timestamp)} | self.instruction.sim_instruction()


class DerivedParams(VaultBaseModel):
    account_id: str


class Output(VaultBaseModel):
    timestamp: Datetime
    derived_params: DerivedParams


class SimulateRequest(VaultBaseModel):
    start_timestamp: Datetime
    end_timestamp: Datetime
    smart_contracts: list[SmartContract] | None = None
    existing_smart_contracts: list[ExistingContractOrModule] | None = None
    supervisor_contracts: list[SupervisorContract] | None = None
    existing_supervisor_contracts: list[ExistingContractOrModule] | None = None
    contract_modules: list[ContractModule] | None = None
    existing_contract_modules: list[ExistingContractOrModule] | None = None
    existing_accounts: list[ExistingAccount] | None = None
    existing_product_data_behaviour: ExistingProductDataBehaviour | None = None
    instructions: list[Instruction] | None = None
    outputs: list[Output] | None = None
