from __future__ import annotations

# standard libs
from abc import ABC
from datetime import datetime
from enum import Enum
from typing import Annotated, Any, Sequence, TypeAlias, Union
from zoneinfo import ZoneInfo

# third party
from pydantic import ConfigDict, Field, computed_field, field_validator, model_validator

# inception sdk
from inception_sdk.test_framework.common.date_helper import isoformat
from inception_sdk.vault.pydantic_types import (
    Datetime,
    Decimal_,
    OptionalDatetime,
    OptionalDecimal,
    OptionalZoneInfo,
    VaultBaseModel,
)


class PostingPhase(str, Enum):
    UNKNOWN = "POSTING_PHASE_UNKNOWN"
    PENDING_INCOMING = "POSTING_PHASE_PENDING_INCOMING"
    PENDING_OUTGOING = "POSTING_PHASE_PENDING_OUTGOING"
    COMMITTED = "POSTING_PHASE_COMMITTED"


# Start: accounts API types.
class AccountV2Type(str, Enum):
    ACCOUNT_TYPE_UNKNOWN = "ACCOUNT_TYPE_UNKNOWN"
    ACCOUNT_TYPE_CUSTOMER = "ACCOUNT_TYPE_CUSTOMER"
    ACCOUNT_TYPE_INTERNAL = "ACCOUNT_TYPE_INTERNAL"


class AccountStatus(str, Enum):
    """This is for the /v1/accounts endpoint."""

    ACCOUNT_STATUS_UNKNOWN = "ACCOUNT_STATUS_UNKNOWN"
    ACCOUNT_STATUS_OPEN = "ACCOUNT_STATUS_OPEN"
    ACCOUNT_STATUS_CLOSED = "ACCOUNT_STATUS_CLOSED"
    ACCOUNT_STATUS_CANCELLED = "ACCOUNT_STATUS_CANCELLED"
    ACCOUNT_STATUS_PENDING_CLOSURE = "ACCOUNT_STATUS_PENDING_CLOSURE"
    ACCOUNT_STATUS_PENDING = "ACCOUNT_STATUS_PENDING"


class AccountPlanAssocStatus(str, Enum):
    ACCOUNT_PLAN_ASSOC_STATUS_UNKNOWN = "ACCOUNT_PLAN_ASSOC_STATUS_UNKNOWN"
    ACCOUNT_PLAN_ASSOC_STATUS_ACTIVE = "ACCOUNT_PLAN_ASSOC_STATUS_ACTIVE"
    ACCOUNT_PLAN_ASSOC_STATUS_INACTIVE = "ACCOUNT_PLAN_ASSOC_STATUS_INACTIVE"


class AccountUpdateType(str, Enum):
    INSTANCE_PARAM_VALS_UPDATE = "instance_param_vals_update"
    PRODUCT_VERSION_UPDATE = "product_version_update"
    ACTIVATION_UPDATE = "activation_update"
    CLOSURE_UPDATE = "closure_update"


class AccountV2Status(str, Enum):
    """
    This is for the /v2/accounts endpoint.  Deprecated account status values are not included
    here.  If you wish to use them, get them from the AccountStatus enum.
    """

    ACCOUNT_STATUS_UNKNOWN = "ACCOUNT_STATUS_UNKNOWN"
    ACCOUNT_STATUS_PENDING = "ACCOUNT_STATUS_PENDING"
    ACCOUNT_STATUS_OPENING = "ACCOUNT_STATUS_OPENING"
    ACCOUNT_STATUS_OPEN = "ACCOUNT_STATUS_OPEN"
    ACCOUNT_STATUS_CLOSING = "ACCOUNT_STATUS_CLOSING"
    ACCOUNT_STATUS_CLOSED = "ACCOUNT_STATUS_CLOSED"
    ACCOUNT_STATUS_CANCELLED = "ACCOUNT_STATUS_CANCELLED"
    # Deprecated but never included in the v1 AccountStatus enum:
    ACCOUNT_STATUS_PENDING_OPENING = "ACCOUNT_STATUS_PENDING_OPENING"


class AccountV2TSide(str, Enum):
    """This enum is only for the /v2/accounts endpoint."""

    T_SIDE_UNKNOWN = "T_SIDE_UNKNOWN"
    T_SIDE_ASSET = "T_SIDE_ASSET"
    T_SIDE_LIABILITY = "T_SIDE_LIABILITY"


class BalanceTimeView(str, Enum):
    VALUE = "BALANCE_TIME_VIEW_VALUE"
    BOOKING = "BALANCE_TIME_VIEW_BOOKING"


class ProductVersionCoreTag(str, Enum):
    UNKNOWN = "PRODUCT_VERSION_CORE_TAG_UNKNOWN"
    DEPOSIT = "PRODUCT_VERSION_CORE_TAG_DEPOSIT"
    FIXED_TERM_DEPOSIT = "PRODUCT_VERSION_CORE_TAG_FIXED_TERM_DEPOSIT"
    SAVING = "PRODUCT_VERSION_CORE_TAG_SAVING"
    LOAN = "PRODUCT_VERSION_CORE_TAG_LOAN"
    CREDIT = "PRODUCT_VERSION_CORE_TAG_CREDIT"
    MORTGAGE = "PRODUCT_VERSION_CORE_TAG_MORTGAGE"


class ProductVersionParameterLevel(str, Enum):
    UNKNOWN = "LEVEL_UNKNOWN"
    PRODUCT = "LEVEL_PRODUCT"
    INSTANCE = "LEVEL_INSTANCE"


class ProductVersionParameterUpdatePermission(str, Enum):
    UNKNOWN = "UPDATE_PERMISSION_UNKNOWN"
    FIXED = "UPDATE_PERMISSION_FIXED"
    OPS_EDITABLE = "UPDATE_PERMISSION_OPS_EDITABLE"
    CUSTOMER_EDITABLE = "UPDATE_PERMISSION_CUSTOMER_EDITABLE"
    CUSTOMER_EDITABLE_WITH_OPS_PERMISSION = (
        "UPDATE_PERMISSION_CUSTOMER_EDITABLE_WITH_OPS_PERMISSION"
    )


class Tside(str, Enum):
    UNKNOWN = "TSIDE_UNKNOWN"
    ASSET = "TSIDE_ASSET"
    LIABILITY = "TSIDE_LIABILITY"


class AdjustmentsVersioningPolicy(str, Enum):
    UNKNOWN = "ADJUSTMENTS_VERSIONING_POLICY_UNKNOWN"
    LATEST = "ADJUSTMENTS_VERSIONING_POLICY_LATEST"
    HISTORIC = "ADJUSTMENTS_VERSIONING_POLICY_HISTORIC"


class ProductVersionMigrationStrategy(str, Enum):
    UNKNOWN = "PRODUCT_VERSION_MIGRATION_STRATEGY_UNKNOWN"
    NEW_PRODUCT = "PRODUCT_VERSION_MIGRATION_STRATEGY_NEW_PRODUCT"
    ADD_VERSION = "PRODUCT_VERSION_MIGRATION_STRATEGY_ADD_VERSION"
    ADD_VERSION_APPLY_NEW_USERS = "PRODUCT_VERSION_MIGRATION_STRATEGY_ADD_VERSION_APPLY_NEW_USERS"


class ProductVersionView(str, Enum):
    """Indicates which fields should be included for Product Versions."""

    BASIC = "PRODUCT_VERSION_VIEW_BASIC"
    INCLUDE_TAGS = "PRODUCT_VERSION_VIEW_INCLUDE_TAGS"
    INCLUDE_PARAMETERS = "PRODUCT_VERSION_VIEW_INCLUDE_PARAMETERS"
    INCLUDE_CODE = "PRODUCT_VERSION_VIEW_INCLUDE_CODE"


class VaultCoreExtension(str, Enum):
    ATTRIBUTE_BASED_ACCESS_CONTROL = "VAULT_CORE_EXTENSION_ATTRIBUTE_BASED_ACCESS_CONTROL"
    HIGH_VOLUME_ACCOUNTS = "VAULT_CORE_EXTENSION_HIGH_VOLUME_ACCOUNTS"
    MULTIPLE_PROCESSING_GROUPS = "VAULT_CORE_EXTENSION_MULTIPLE_PROCESSING_GROUPS"
    SCHEDULED_ADJUSTMENTS = "VAULT_CORE_EXTENSION_SCHEDULED_ADJUSTMENTS"
    SUB_ACCOUNTS = "VAULT_CORE_EXTENSION_SUB_ACCOUNTS"


class GetVaultVersionResponse(VaultBaseModel):
    version: SemanticVersion
    pre_release: str
    build: str
    # Defaults to empty list for compatibility with Vault versions < 5.8 since `extensions`
    # key was not in the response.
    extensions: list[VaultCoreExtension] = Field(default_factory=list)


class ListBalancesLiveRequest(VaultBaseModel):
    account_id: str
    view: BalanceTimeView = BalanceTimeView.VALUE
    addresses: list[str] | None = None
    page_token: str | None = None
    page_size: int


class _BalanceV2(VaultBaseModel):
    amount: Decimal_
    total_debit: Decimal_
    total_credit: Decimal_
    account_id: str
    account_address: str
    phase: PostingPhase
    asset: str
    denomination: str
    sub_account_id: str = ""


class LiveBalanceV2(_BalanceV2):
    pass


class BalanceV2(_BalanceV2):
    timestamp: Datetime


class EndBalanceV2(_BalanceV2):
    # As of 5.8, EndBalance has a non-None timestamp for balances maturing in the future
    # and a None timestamp for balances that have already matured / were never valued in the future
    timestamp: OptionalDatetime = None


class ListBalancesLiveResponse(VaultBaseModel):
    balances: list[LiveBalanceV2]
    previous_page_token: str
    next_page_token: str


class ListBalancesEndRequest(VaultBaseModel):
    account_id: str
    view: BalanceTimeView = BalanceTimeView.VALUE
    snapshot_timestamp: OptionalDatetime = None
    page_token: str | None = None
    page_size: int


class ListBalancesEndResponse(VaultBaseModel):
    balances: list[EndBalanceV2]
    snapshot_timestamp: OptionalDatetime
    previous_page_token: str
    next_page_token: str


class ListBalancesSeriesRequest(VaultBaseModel):
    account_id: str
    start_timestamp: Datetime
    end_timestamp: OptionalDatetime = None
    snapshot_timestamp: OptionalDatetime = None
    addresses: list[str] | None = None
    view: BalanceTimeView = BalanceTimeView.VALUE
    page_token: str | None = None
    page_size: int


class ListBalancesSeriesResponse(VaultBaseModel):
    balances: list[BalanceV2]
    snapshot_timestamp: OptionalDatetime
    previous_page_token: str
    next_page_token: str


class _CreateAccountV2Account(ABC, VaultBaseModel):
    """
    This class is only for the /v2/accounts endpoint.
    """

    status: AccountV2Status
    id: str | None = None
    alias: str | None = None
    details: dict[str, str] | None = None
    processing_group_id: str | None = None


class CustomerAccountRequestBody(_CreateAccountV2Account):
    """
    Attributes for customer /v2/accounts create requests
    """

    smart_contract_version_id: str | None = None
    stakeholder_ids: list[str]
    permitted_denominations: list[str] | None = None
    activation_timestamp: OptionalDatetime = None  # Only supported in Vault 5.7+
    parameter_value_hierarchy_node_id: str | None = None

    @computed_field()
    def type(self) -> AccountV2Type:
        return AccountV2Type.ACCOUNT_TYPE_CUSTOMER


class InternalAccountRequestBody(_CreateAccountV2Account):
    """
    Attributes for internal /v2/accounts create requests
    """

    t_side: AccountV2TSide = AccountV2TSide.T_SIDE_LIABILITY
    processing_label: str | None = None

    @computed_field()
    def type(self) -> AccountV2Type:
        return AccountV2Type.ACCOUNT_TYPE_INTERNAL


class StringParameterValue(VaultBaseModel):
    string_value: str

    def __str__(self) -> str:
        return self.string_value


class DecimalParameterValue(VaultBaseModel):
    decimal_value: Decimal_

    def __str__(self) -> str:
        return str(self.decimal_value)


class EnumerationParameterValue(VaultBaseModel):
    enumeration_value: str

    def __str__(self) -> str:
        return self.enumeration_value


class DatetimeParameterValue(VaultBaseModel):
    """
    UTC date with hour and minute components.  Seconds-precision is not supported by the smart
    contracts language. For a Parameter Resource created with date_time_constraint and DAY
    precision, the Parameter Value time components must all be 0. For a Parameter Resource
    created with MINUTE precision the hour and minute components can be non-zero. An Instance
    Parameter with a DateShape corresponds to a Parameter Resource with date_time_constraint
    and DAY precision.
    """

    date_time_value: Datetime

    @field_validator("date_time_value")
    @classmethod
    def check_no_seconds(cls, v: datetime) -> datetime:
        if v.second != 0 or v.microsecond != 0:
            raise ValueError("The highest granularity for date_time_value is minutes")
        return v

    def __str__(self) -> str:
        return isoformat(self.date_time_value)


class AccountIdParameterValue(VaultBaseModel):
    account_id_value: str

    def __str__(self) -> str:
        return self.account_id_value


ParameterValue: TypeAlias = Union[
    AccountIdParameterValue,
    DatetimeParameterValue,
    DecimalParameterValue,
    EnumerationParameterValue,
    StringParameterValue,
]


class CreateOptions(VaultBaseModel):
    """
    Create options when creating a V2 Account.
    """

    parameter_values: dict[str, ParameterValue] | None = None
    sub_accounts: list[CreateSubAccountRequest] | None = None


class CreateAccountV2RequestBody(VaultBaseModel):
    request_id: str
    account: CustomerAccountRequestBody | InternalAccountRequestBody
    # create_options only applies to Customer Accounts
    create_options: CreateOptions | None = None


class Account(VaultBaseModel):
    id: str
    type: AccountV2Type
    smart_contract_version_id: str
    pending_smart_contract_version_id: str
    stakeholder_ids: list[str]
    alias: str
    status: AccountV2Status
    vault_create_timestamp: Datetime
    source_create_timestamp: Datetime
    source_open_timestamp: OptionalDatetime = None
    source_close_timestamp: OptionalDatetime = None
    update_timestamp: OptionalDatetime = None
    activation_timestamp: OptionalDatetime = None
    permitted_denominations: list[str]
    details: dict[str, str]
    t_side: AccountV2TSide
    contract_update_timestamp: OptionalDatetime = None
    # Multiple Processing Groups are only available as an Extension
    processing_group_id: str
    # Internal only
    # TODO(TM-137278) Remove tranche_id.
    tranche_id: str
    parameter_value_hierarchy_node_id: str | None = None
    # These fields may not be populated at all as they are enterprise-only
    processing_label: str | None = None


class CreateOptionsSideEffects(VaultBaseModel):
    """
    Contains the results of the side effects of the CreateOptions passed in via the CreateAccount
    request.
    """

    sub_accounts: list[SubAccount]


class CreateAccountV2Response(Account):
    """
    This class holds a success response from the /v2/accounts endpoint.
    """

    create_options_side_effects: CreateOptionsSideEffects | None = None


class UpdateAccountV2Account(VaultBaseModel):
    smart_contract_version_id: str | None = None
    stakeholder_ids: list[str] | None = None
    status: AccountV2Status | None = None
    parameter_value_hierarchy_node_id: str | None = None
    alias: str | None = None
    processing_label: str | None = None
    details: dict[str, str] | None = None

    @model_validator(mode="before")
    @classmethod
    def validate_model(cls, data: Any) -> Any:
        """
        Check that only one of the updatable fields is updated
        """
        if isinstance(data, dict):
            cls.one_of_validator(
                data=data,
                field_names=[
                    "smart_contract_version_id",
                    "stakeholder_ids",
                    "status",
                    "parameter_value_hierarchy_node_id",
                    "alias",
                    "processing_label",
                    "details",
                ],
            )

        return data


class UpdateMask(VaultBaseModel):
    paths: list[str]


class UpdateAccountV2RequestBody(VaultBaseModel):
    request_id: str
    account: UpdateAccountV2Account
    update_mask: UpdateMask


# End: accounts API types.
# Start: sub-accounts API types.


class SubAccountStatus(str, Enum):
    """
    Enum of the Status of a Sub-Account.
    """

    # This status exists to avoid an empty request unintentionally setting an undesired status.
    # A Sub-Account will never have this status.
    SUB_ACCOUNT_STATUS_UNKNOWN = "SUB_ACCOUNT_STATUS_UNKNOWN"
    SUB_ACCOUNT_STATUS_PENDING = "SUB_ACCOUNT_STATUS_PENDING"
    SUB_ACCOUNT_STATUS_OPENING = "SUB_ACCOUNT_STATUS_OPENING"
    SUB_ACCOUNT_STATUS_OPEN = "SUB_ACCOUNT_STATUS_OPEN"
    SUB_ACCOUNT_STATUS_CANCELLED = "SUB_ACCOUNT_STATUS_CANCELLED"
    SUB_ACCOUNT_STATUS_CLOSING = "SUB_ACCOUNT_STATUS_CLOSING"
    SUB_ACCOUNT_STATUS_CLOSED = "SUB_ACCOUNT_STATUS_CLOSED"


class SubAccount(VaultBaseModel):
    """
    Model for Sub-Account objects, with all fields, returned from various endpoints
    """

    id: str | None
    type: str
    name: str | None
    details: dict[str, str] | None
    activation_timestamp: OptionalDatetime = None
    create_timestamp: OptionalDatetime = None
    update_timestamp: OptionalDatetime = None
    status: SubAccountStatus
    account_id: str


class ListSubAccountsRequest(VaultBaseModel):
    """
    Request for GET /v1/sub-accounts endpoint
    """

    account_id: str
    status: SubAccountStatus | None = None
    type: str | None = None
    page_size: int
    page_token: str | None = None


class ListSubAccountsResponse(VaultBaseModel):
    """
    Response for GET /v1/sub-accounts endpoint
    """

    sub_accounts: list[SubAccount]
    previous_page_token: str
    next_page_token: str


class SubAccountCreateSubAccount(VaultBaseModel):
    """
    Sub-Account model for create operations.

    Includes the subset of the fields of the `SubAccount` model that can be
    specified in a create request.
    """

    id: str | None = None
    type: str
    name: str | None = None
    details: dict[str, str] | None = None
    account_id: str | None = None

    # Only present in requests to POST /v1/sub-accounts; not used in CreateOptions.
    status: SubAccountStatus = SubAccountStatus.SUB_ACCOUNT_STATUS_UNKNOWN


class CreateSubAccountRequest(VaultBaseModel):
    """
    Request for POST /v1/sub-accounts endpoint
    """

    # Only present in requests to POST /v1/sub-accounts; not used in CreateOptions.
    request_id: str | None = None
    sub_account: SubAccountCreateSubAccount


class SubAccountUpdateSubAccount(VaultBaseModel):
    """
    Sub-Account model for update operations.

    Includes the subset of the fields of the `SubAccount` model that can be
    specified in an update request.
    """

    name: str | None = None
    details: dict[str, str] | None = None
    status: SubAccountStatus | None = None


class UpdateSubAccountRequest(VaultBaseModel):
    """
    Request for PUT /v1/sub-accounts/{sub_account.id} endpoint.
    """

    # path parameters
    sub_account_id: str | None
    # body parameters
    request_id: str
    sub_account: SubAccountUpdateSubAccount
    update_mask: UpdateMask

    @model_validator(mode="after")
    def validate_update_mask_fields(self) -> UpdateSubAccountRequest:
        """
        Validates that only allowed fields are specified in the update_mask.
        :return: Original UpdateSubAccountRequest passed in.
        :raises ValueError: The update_mask has unknown fields in it, or if it contains "status"
        and any other field.
        """
        allowed_fields = set(SubAccountUpdateSubAccount.model_fields.keys())
        invalid_fields = sorted(set(self.update_mask.paths) - set(allowed_fields))
        if invalid_fields:
            raise ValueError(
                f"Invalid fields in update_mask: {invalid_fields}. "
                f"Only the following fields can be updated: "
                f"{allowed_fields}"
            )

        if "status" in self.update_mask.paths:
            paths_without_status = [path for path in self.update_mask.paths if path != "status"]
            if paths_without_status:
                raise ValueError(
                    f"Invalid fields in update_mask: {paths_without_status} "
                    "status must be updated in isolation."
                )
        return self


class BatchGetSubAccountsRequest(VaultBaseModel):
    """
    Request for GET /v1/sub-accounts:batchGet endpoint.
    """

    ids: list[str]

    @model_validator(mode="after")
    def validate_ids_list(self) -> BatchGetSubAccountsRequest:
        """
        Validates that the number of Sub-Account IDs doesn't exceed the maximum (100).
        :return: Original BatchGetSubAccountsRequest object passed in.
        :raises ValueError: The number of Sub-Account IDs to BatchGet exceeds the limit.
        """
        maximum_allowed_ids = 100
        if len(self.ids) > maximum_allowed_ids:
            raise ValueError(
                f"Invalid number of IDs: {len(self.ids)}"
                f"Maximum number of allowable IDs: {maximum_allowed_ids}"
            )
        return self


class BatchGetSubAccountsResponse(VaultBaseModel):
    """Response for GET /v1/sub-accounts:batchGet endpoint"""

    sub_accounts: dict[str, SubAccount]


# End: sub-accounts API types.
# Start: parameter resources and parameter values.


class StringConstraintValue(VaultBaseModel):
    min_length: int = 0
    max_length: int = 0


class StringConstraint(VaultBaseModel):
    string_constraint: StringConstraintValue


class NumberValueType(str, Enum):
    NOT_SPECIFIED = "NUMBER_FIELD_DISPLAY_STYLE_NOT_SPECIFIED"
    PLAIN = "NUMBER_FIELD_DISPLAY_STYLE_PLAIN"
    PERCENTAGE = "NUMBER_FIELD_DISPLAY_STYLE_PERCENTAGE"
    MONEY = "NUMBER_FIELD_DISPLAY_STYLE_MONEY"
    MONTHS = "NUMBER_FIELD_DISPLAY_STYLE_MONTHS"


class DecimalConstraintValue(VaultBaseModel):
    min_value: OptionalDecimal | None = None
    max_value: OptionalDecimal | None = None


class DecimalConstraint(VaultBaseModel):
    decimal_constraint: DecimalConstraintValue


class EnumerationConstraintValue(VaultBaseModel):
    permitted_values: list[str]


class EnumerationConstraint(VaultBaseModel):
    enumeration_constraint: EnumerationConstraintValue


class DateValueType(str, Enum):
    UNKNOWN = "DATE_TYPE_UNKNOWN"
    RELATIVE = "DATE_TYPE_RELATIVE"
    ABSOLUTE = "DATE_TYPE_ABSOLUTE"


class DatetimeConstraintPrecision(str, Enum):
    MINUTE = "MINUTE"
    DAY = "DAY"


class DatetimeConstraintValue(VaultBaseModel):
    precision: DatetimeConstraintPrecision = DatetimeConstraintPrecision.MINUTE
    earliest: OptionalDatetime = None
    latest: OptionalDatetime = None


class DatetimeConstraint(VaultBaseModel):
    date_time_constraint: DatetimeConstraintValue


class AccountConstraintValue(VaultBaseModel):
    """The account constraint object has no fields, according to the Core API spec."""


class AccountConstraint(VaultBaseModel):
    account_constraint: AccountConstraintValue


class AbstractParameterResource(VaultBaseModel):
    # We may need to refine this class further and distinguish between Create and Get/List
    # due to differences in how default/unset values are represented, but this isn't
    # particularly useful yet

    id: str
    constraint: (
        AccountConstraint
        | DatetimeConstraint
        | DecimalConstraint
        | EnumerationConstraint
        | StringConstraint
    )


class ParameterResource(AbstractParameterResource):
    metadata: dict[str, str] | None = None


class CreateParameterResourceV1RequestBody(VaultBaseModel):
    request_id: str
    parameter: ParameterResource


class CreateParameterValueV1ParameterValue(VaultBaseModel):
    parameter_id: str
    value: ParameterValue
    effective_from_timestamp: OptionalDatetime = None
    cancel_timestamp: OptionalDatetime = None
    is_backdated: bool = False
    account_id: str | None = None
    global_: bool | None = Field(default=None, serialization_alias="global")
    parameter_value_hierarchy_node_id: str | None = None

    @model_validator(mode="before")
    @classmethod
    def validate_model(cls, data: Any) -> Any:
        """
        Check that only one field is populated out of account_id,
        global_ and parameter_value_hierarchy_node_id.
        Return the data if it is not a dictionary.
        """
        if isinstance(data, dict):
            cls.one_of_validator(
                data=data,
                field_names=["account_id", "global_", "parameter_value_hierarchy_node_id"],
            )

        return data


class BatchCreateParameterValueV1RequestBody(VaultBaseModel):
    request_id: str
    parameter_values: list[CreateParameterValueV1ParameterValue]


class BatchGetParameterResourceV1ResponseBody(VaultBaseModel):
    # We may need to refine this further and distinguish between Create and Get/List, but it
    # isn't particularly useful yet
    parameters: dict[str, ParameterResource]


class ParameterValueResource(VaultBaseModel):
    id: str
    parameter_id: str
    create_timestamp: Datetime
    update_timestamp: OptionalDatetime = None
    effective_from_timestamp: OptionalDatetime = None
    effective_to_timestamp: OptionalDatetime = None
    is_cancelled: bool = False
    is_backdated: bool = False
    value: ParameterValue
    cancel_timestamp: OptionalDatetime = None


class UpdateParameterValueV1RequestBody(VaultBaseModel):
    request_id: str
    parameter_value: UpdateParameterValueV1ParameterValue
    update_mask: UpdateMask
    is_cancelled_update_options: IsCancelledUpdateOptions | None = None


class IsCancelledUpdateOptions(VaultBaseModel):
    skip_pre_parameter_change_hook: bool | None = None


class UpdateParameterValueV1ParameterValue(VaultBaseModel):
    """
    :param id: Optional. This model does not require the field on the e2e framework,
    as it's passed in the request url. However the simulation framework expects in
    the request body.
    """

    id: str | None = None
    effective_to_timestamp: OptionalDatetime = None
    is_cancelled: bool | None = None


# End: parameter resources and parameter values.
# Start: parameter value hierarchy.


class ParameterValueHierarchyNode(VaultBaseModel):
    id: str
    name: str
    parent_id: str = ""
    parent_path: list[str] = []
    depth: int
    metadata: dict[str, str] | None = None
    create_timestamp: Datetime
    update_timestamp: Datetime


class CreateParameterValueHierarchyNode(VaultBaseModel):
    id: str
    name: str
    parent_id: str = ""
    metadata: dict[str, str] | None = None


class CreateParameterValueHierarchyNodeRequestBody(VaultBaseModel):
    request_id: str
    parameter_value_hierarchy_node: CreateParameterValueHierarchyNode


# End: parameter value hierarchy.
# Start: flags API types.
class FlagV1FlagValue(str, Enum):
    FLAG_VALUE_ON = "FLAG_VALUE_ON"
    FLAG_VALUE_OFF = "FLAG_VALUE_OFF"


class CreateFlagV1Flag(VaultBaseModel):
    """
    Model for flags to create with no output only fields (e.g. id)
    :flag_definition_id: This corresponds to the flag_definition_id in the API.
    :description: Metadata for the flag.
    :effective_timestamp: When the flag should start being applied.
    :expiry_timestamp: When the flag should stop being applied.
    :is_backdated: This is new in Vault 5.2.  Supply it if effective_timestamp is earlier than the
    flag's creation date.
    :value: The flag will behave as True in the smart contract when set to
    FlagValue.FLAG_VALUE_ON; False when set to FlagValue.FLAG_VALUE_OFF.
    """

    flag_definition_id: str
    description: str | None
    effective_timestamp: OptionalDatetime = None
    expiry_timestamp: OptionalDatetime = None
    is_backdated: bool | None = None
    value: FlagV1FlagValue


class FlagV1Flag(CreateFlagV1Flag):
    """
    Model for flags to create with no output only fields (e.g. id)
    :id: the id of the created flag, output only
    """

    id: str


class CreateFlagV1CreateAccountFlag(CreateFlagV1Flag):
    """
    :account_id: account_id for an account flag.
    """

    account_id: str


class CreateFlagV1CreateCustomerFlag(CreateFlagV1Flag):
    """
    :customer_id: customer_id for a customer flag.
    """

    customer_id: str


class CreateFlagV1CreatePaymentDeviceId(CreateFlagV1Flag):
    """
    :payment_device_id: payment_device_id for a payment device flag.
    """

    payment_device_id: str


class FlagV1AccountFlag(FlagV1Flag):
    """
    Model for created flags with an id
    :account_id: account_id for an account flag.
    """

    account_id: str


class FlagV1CustomerFlag(FlagV1Flag):
    """
    Model for created flags with an id
    :customer_id: customer_id for a customer flag.
    """

    customer_id: str


class FlagV1PaymentDeviceFlag(FlagV1Flag):
    """
    Model for created flags with an id
    :payment_device_id: payment_device_id for a payment device flag.
    """

    payment_device_id: str


class CreateFlagV1RequestBody(VaultBaseModel):
    request_id: str
    # We don't use the base CreateFlagV1Flag class as this causes issues with serialising and
    # validating
    flag: (
        CreateFlagV1CreateAccountFlag
        | CreateFlagV1CreateCustomerFlag
        | CreateFlagV1CreatePaymentDeviceId
    )


# End: flags API types.


class CalendarEventStatus(str, Enum):
    BOTH = "BOTH"
    ONLY_TRUE = "ONLY_TRUE"
    ONLY_FALSE = "ONLY_FALSE"


class ProcessingGroupStatus(str, Enum):
    ACTIVE = "PROCESSING_GROUP_STATUS_ACTIVE"
    PAUSED = "PROCESSING_GROUP_STATUS_PAUSED"


class MinimumObservationTimestampUpdateOptions(VaultBaseModel):
    schedules_observe_balances_at_unpause_time: bool


class ProcessingGroup(VaultBaseModel):
    id: str
    status: ProcessingGroupStatus
    create_timestamp: Datetime
    timezone: OptionalZoneInfo = None
    update_timestamp: OptionalDatetime = None
    minimum_observation_timestamp: OptionalDatetime = None


class ProcessingGroupUpdate(VaultBaseModel):
    status: ProcessingGroupStatus
    timezone: OptionalZoneInfo = None


class UpdateProcessingGroupRequestBody(VaultBaseModel):
    request_id: str
    update_mask: UpdateMask
    processing_group: ProcessingGroupUpdate
    minimum_observation_timestamp_update_options: MinimumObservationTimestampUpdateOptions


class CreateProcessingGroup(VaultBaseModel):
    id: str
    # We do not need custom validators from str to ZoneInfo because this model is strictly
    # for requests. All responses should use the `ProcessingGroup` model, which has the
    # relevant validators in place.
    timezone: ZoneInfo
    description: str | None = None


class CreateProcessingGroupRequestBody(VaultBaseModel):
    request_id: str
    processing_group: CreateProcessingGroup


class PlanStatus(str, Enum):
    UNKNOWN = "PLAN_STATUS_UNKNOWN"
    PENDING = "PLAN_STATUS_PENDING"
    OPEN = "PLAN_STATUS_OPEN"
    CLOSED = "PLAN_STATUS_CLOSED"


class AccountPlanAssoc(VaultBaseModel):
    id: str
    account_id: str
    plan_id: str
    status: AccountPlanAssocStatus
    create_timestamp: OptionalDatetime = None
    start_timestamp: OptionalDatetime = None
    end_timestamp: OptionalDatetime = None


class Plan(VaultBaseModel):
    id: str
    supervisor_contract_version_id: str
    status: PlanStatus
    processing_group_id: str | None = None
    create_timestamp: OptionalDatetime = None
    opening_timestamp: OptionalDatetime = None
    activation_completed_timestamp: OptionalDatetime = None
    closing_timestamp: OptionalDatetime = None
    closure_completed_timestamp: OptionalDatetime = None
    details: dict[str, str] | None = None


class PostingInstructionBatchStatus(str, Enum):
    ACCEPTED = "POSTING_INSTRUCTION_BATCH_STATUS_ACCEPTED"
    REJECTED = "POSTING_INSTRUCTION_BATCH_STATUS_REJECTED"
    UNKNOWN = "POSTING_INSTRUCTION_BATCH_STATUS_UNKNOWN"


class OrderByDirection(str, Enum):
    ASC = "ORDER_BY_ASC"
    DESC = "ORDER_BY_DESC"


class Override(VaultBaseModel):
    restrictions: OverrideRestrictions


class OverrideRestrictions(VaultBaseModel):
    all: bool
    restriction_set_ids: list[str]


class TransactionCode(VaultBaseModel):
    domain: str
    family: str
    subfamily: str


class TargetAccount(VaultBaseModel):
    account_id: str | None = None
    payment_device_token: str | None = None

    @model_validator(mode="before")
    @classmethod
    def validate_model(cls, data: Any) -> Any:
        if isinstance(data, dict):
            cls.one_of_validator(
                data=data,
                field_names=["account_id", "payment_device_token"],
            )
        return data


class AdjustmentAmount(VaultBaseModel):
    amount: Decimal_ | None = None
    replacement_amount: Decimal_ | None = None

    @model_validator(mode="before")
    @classmethod
    def validate_model(cls, data: Any) -> Any:
        if isinstance(data, dict):
            cls.one_of_validator(
                data=data,
                field_names=["amount", "replacement_amount"],
            )
        return data


class Balance(VaultBaseModel):
    id: str
    account_id: str
    account_address: str
    phase: PostingPhase
    asset: str
    denomination: str
    posting_instruction_batch_id: str
    value_time: Datetime
    amount: Decimal_
    total_debit: Decimal_
    total_credit: Decimal_


class LiveBalances(VaultBaseModel):
    account_id: str
    value_balances: list[BalanceV2]
    booking_balances: list[BalanceV2]


class Posting(VaultBaseModel):
    credit: bool
    amount: str
    denomination: str
    account_id: str
    account_address: str
    asset: str
    phase: PostingPhase
    sub_account_id: str = ""
    # This already defaults to "" for Vault Core >= 5.4, but providing a default here provides
    # backwards-compatibility (e.g. client on Vault < 5.4, or tests instantiating the class that
    # don't care about labels)
    internal_account_processing_label: str = ""


## Instruction types
class CustomInstruction(VaultBaseModel):
    postings: list[Posting]


class _InstructionWithInternalAccount(VaultBaseModel):
    internal_account_id: str | None = None
    internal_account_processing_label: str | None = None

    @model_validator(mode="before")
    @classmethod
    def validate_model(cls, data: Any) -> Any:
        if isinstance(data, dict):
            cls.one_of_validator(
                data=data,
                field_names=[
                    "internal_account_id",
                    "internal_account_processing_label",
                ],
            )
        return data


class OutboundAuthorisation(_InstructionWithInternalAccount):
    amount: Decimal_
    target_account: TargetAccount
    denomination: str
    advice: bool = False
    target_account_address: str | None = None
    asset: str | None = None
    target_sub_account_id: str | None = None

    @model_validator(mode="after")
    def validate_target_sub_account_id(self) -> OutboundAuthorisation:
        """
        The target Sub-Account ID of the instruction requires the `target_account` field to
        be set with an `account_id`. If supplied (i.e. not None), the instruction targets the
        provided Sub-Account ID associated to the provided account. Otherwise, it targets
        the provided account.
        """
        if self.target_sub_account_id is not None and not self.target_account.account_id:
            raise ValueError(
                "target_account's account_id must be set if `target_sub_account_id` is not None"
            )
        return self


class InboundAuthorisation(_InstructionWithInternalAccount):
    amount: Decimal_
    target_account: TargetAccount
    denomination: str
    advice: bool = False
    target_account_address: str | None = None
    asset: str | None = None
    target_sub_account_id: str | None = None

    @model_validator(mode="after")
    def validate_target_sub_account_id(self) -> InboundAuthorisation:
        """
        The target Sub-Account ID of the instruction requires the `target_account` field to
        be set with an `account_id`. If supplied (i.e. not None), the instruction targets the
        provided Sub-Account ID associated to the provided account. Otherwise, it targets
        the provided account.
        """
        if self.target_sub_account_id is not None and not self.target_account.account_id:
            raise ValueError(
                "target_account's account_id must be set if `target_sub_account_id` is not None"
            )
        return self


class AuthorisationAdjustment(VaultBaseModel):
    adjustment_amount: AdjustmentAmount
    advice: bool = False


class OutboundHardSettlement(_InstructionWithInternalAccount):
    amount: Decimal_
    target_account: TargetAccount
    denomination: str
    advice: bool = False
    target_account_address: str | None = None
    asset: str | None = None
    target_sub_account_id: str | None = None

    @model_validator(mode="after")
    def validate_target_sub_account_id(self) -> OutboundHardSettlement:
        """
        The target Sub-Account ID of the instruction requires the `target_account` field to
        be set with an `account_id`. If supplied (i.e. not None), the instruction targets the
        provided Sub-Account ID associated to the provided account. Otherwise, it targets
        the provided account.
        """
        if self.target_sub_account_id is not None and not self.target_account.account_id:
            raise ValueError(
                "target_account's account_id must be set if `target_sub_account_id` is not None"
            )
        return self


class InboundHardSettlement(_InstructionWithInternalAccount):
    amount: Decimal_
    target_account: TargetAccount
    denomination: str
    advice: bool = False
    target_account_address: str | None = None
    asset: str | None = None
    target_sub_account_id: str | None = None

    @model_validator(mode="after")
    def validate_target_sub_account_id(self) -> InboundHardSettlement:
        """
        The target Sub-Account ID of the instruction requires the `target_account` field to
        be set with an `account_id`. If supplied (i.e. not None), the instruction targets
        the provided Sub-Account ID associated to the provided account. Otherwise, it targets
        the provided account.
        """
        if self.target_sub_account_id is not None and not self.target_account.account_id:
            raise ValueError(
                "target_account's account_id must be set if `target_sub_account_id` is not None"
            )
        return self


class Transfer(VaultBaseModel):
    amount: Decimal_
    creditor_target_account: TargetAccount
    debtor_target_account: TargetAccount
    denomination: str
    debtor_target_sub_account_id: str | None = None
    creditor_target_sub_account_id: str | None = None
    debtor_target_account_address: str | None = None
    creditor_target_account_address: str | None = None

    @model_validator(mode="after")
    def validate_model(self) -> Transfer:
        if (self.creditor_target_sub_account_id and not self.creditor_target_account_address) or (
            not self.creditor_target_sub_account_id and self.creditor_target_account_address
        ):
            raise ValueError(
                """
                If `creditor_target_sub_account_id` is provided, the creditor_target_account_address
                field must be set. If `creditor_target_sub_account_id` is not provided, the
                creditor field must not be set by the user.
                """
            )
        if (self.debtor_target_sub_account_id and not self.debtor_target_account_address) or (
            not self.debtor_target_sub_account_id and self.debtor_target_account_address
        ):
            raise ValueError(
                """
                If `debtor_target_sub_account_id` is provided, the `debtor_target_account_address`
                field must be set. If `debtor_target_sub_account_id` is not provided, the
                `debtor_target_account_address` field must not be set by the user.
                """
            )

        return self


class Settlement(VaultBaseModel):
    amount: Decimal_ | None = None
    denomination: str | None = None
    final: bool = False
    require_pre_posting_hook_execution: bool = False
    # These fields are output only
    internal_account_id: str | None = None
    internal_account_processing_label: str | None = None
    target_account_id: str | None = None
    target_account_address: str | None = None
    asset: str | None = None
    target_sub_account_id: str | None = None


class Release(VaultBaseModel):
    amount: Decimal_ | None = None
    denomination: str | None = None
    require_pre_posting_hook_execution: bool = False
    # These fields are output only
    target_account_id: str | None = None
    internal_account_id: str | None = None
    internal_account_processing_label: str | None = None
    target_account_address: str | None = None
    asset: str | None = None
    target_sub_account_id: str | None = None


## Request types
class PostingInstruction(VaultBaseModel):
    client_transaction_id: str
    instruction_details: dict[str, str] | None = None
    override: Override | None = None
    transaction_code: TransactionCode | None = None
    value_timestamp: OptionalDatetime = None
    booking_timestamp: OptionalDatetime = None

    # Instruction type options — only one should be populated
    custom_instruction: CustomInstruction | None = None
    inbound_authorisation: InboundAuthorisation | None = None
    outbound_authorisation: OutboundAuthorisation | None = None
    authorisation_adjustment: AuthorisationAdjustment | None = None
    inbound_hard_settlement: InboundHardSettlement | None = None
    outbound_hard_settlement: OutboundHardSettlement | None = None
    transfer: Transfer | None = None
    settlement: Settlement | None = None
    release: Release | None = None

    @model_validator(mode="before")
    @classmethod
    def validate_model(cls, data: Any) -> Any:
        if isinstance(data, dict):
            cls.one_of_validator(
                data=data,
                field_names=[
                    "custom_instruction",
                    "inbound_authorisation",
                    "outbound_authorisation",
                    "authorisation_adjustment",
                    "inbound_hard_settlement",
                    "outbound_hard_settlement",
                    "transfer",
                    "settlement",
                    "release",
                ],
            )
        return data


class PostingInstructionBatch(VaultBaseModel):
    client_id: str
    client_batch_id: str
    posting_instructions: Sequence[PostingInstruction]
    batch_details: dict[str, str] | None = None
    value_timestamp: OptionalDatetime = None
    booking_timestamp: OptionalDatetime = None


class CreatePostingInstructionBatchRequest(VaultBaseModel):
    """
    :request_id: A unique ID used for idempotency.
    :dry_run: If true, no PostingInstructionBatch will be created and no
            PostingInstructionBatchCreatedEvent will be published to the event topic.
    :posting_instruction_batch: The PIB to be created.
    :shard_key: Optional key used as a best-effort lock to prevent
        CreatePostingInstructionBatchRequest with the same shard_key from racing each other.
    """

    request_id: str
    dry_run: bool = False
    posting_instruction_batch: PostingInstructionBatch
    # TTL is not supported by sync postings API
    shard_key: str = ""


class ListPostingInstructionBatchesRequest(VaultBaseModel):
    """
    :page_size: The maximum number of results to retrieve.
    :page_token: Optional token of the page to retrieve results from.
    :order_by_direction: Optional direction to order results in, by `value_timestamp`.
        Defaults to descending order.
    :account_ids: Optional list of accounts IDs to filter PIBs by.
    :client_batch_ids: Optional list of client batch IDs to filter PIBs by.
    :payment_device_tokens: Optional list of payment device tokens to filter PIBs by.
    :client_transaction_ids: Optional list of client transaction IDs to filter PIBs by.
    :start_time: Optional datetime representing the earliest PIB creation to be returned
        (inclusive).
    :end_time: Optional datetime representing the latest PIB creation to be returned (exclusive).
    """

    page_size: int
    page_token: str | None = None
    order_by_direction: OrderByDirection = OrderByDirection.DESC
    account_ids: list[str] | None = None
    client_batch_ids: list[str] | None = None
    payment_device_tokens: list[str] | None = None
    client_transaction_ids: list[str] | None = None
    start_time: OptionalDatetime = None
    end_time: OptionalDatetime = None


class BatchGetPostingInstructionBatchesRequest(VaultBaseModel):
    """
    :ids: A list of Posting Instruction Batch IDs to retrieve.
    """

    ids: list[str]


class BatchGetPostingInstructionBatchesResponse(VaultBaseModel):
    """
    :posting_instruction_batches: Retrieved map of Posting Instruction Batches keyed by ID.
    """

    posting_instruction_batches: dict[str, CommittedPostingInstructionBatch]


## Response types
class CreatePostingInstructionBatchResponse(VaultBaseModel):
    """
    :posting_instruction_batch: The created PIB.
    :balances: A list of all live balances for the account.
    """

    posting_instruction_batch: CommittedPostingInstructionBatch
    balances: Sequence[Balance]
    live_balances: list[LiveBalances]


class ListPostingInstructionBatchesResponse(VaultBaseModel):
    """
    :posting_instruction_batches: A list of posting instruction batches that
        match the applied filters.
    :previous_page_token: The pagination token to retrieve the previous page of results.
    :next_page_token: The pagination token to retrieve the next page of results.
    """

    posting_instruction_batches: Sequence[CommittedPostingInstructionBatch]
    previous_page_token: str
    next_page_token: str


class CommittedPostingInstructionBatch(VaultBaseModel):
    # output only fields set by Vault
    id: str
    create_request_id: str
    client_id: str
    client_batch_id: str
    batch_details: dict[str, str] | None = None
    value_timestamp: OptionalDatetime = None
    booking_timestamp: OptionalDatetime = None
    status: PostingInstructionBatchStatus
    error: PostingInstructionBatchError | None = None
    insertion_timestamp: Datetime
    source_insertion_timestamp: Datetime
    posting_instructions: Sequence[CommittedPostingInstruction]


class CommittedPostingInstruction(VaultBaseModel):
    # output only fields set by Vault
    id: str
    posting_instruction_batch_id: str
    client_transaction_id: str
    instruction_details: dict[str, str] | None = None
    value_timestamp: Datetime
    booking_timestamp: Datetime
    booking_localised_date_time: str | None = None
    enrichments: dict[str, dict[str, str]] | None = None
    insertion_timestamp: Datetime
    source_insertion_timestamp: Datetime
    committed_postings: Sequence[Posting]
    posting_violations: Sequence[PostingViolation]
    account_violations: Sequence[AccountViolation]
    restriction_violations: Sequence[RestrictionViolation]
    contract_violations: Sequence[ContractViolation]


## Violation types
class AccountViolation(VaultBaseModel):
    # This will preserve any config from the VaultBaseModel and simply override frozen to true.
    model_config = ConfigDict(frozen=True)

    account_id: str = ""
    payment_device_token: str = ""
    type: AccountViolationType
    internal_account_processing_label: str = ""
    sub_account_id: str = ""


class RestrictionViolation(VaultBaseModel):
    restriction_set_id: str
    account_id: str = ""
    payment_device_id: str = ""
    customer_id: str = ""
    requires_review: bool = False
    type: RestrictionViolationType


class ContractViolation(VaultBaseModel):
    # This will preserve any config from the VaultBaseModel and simply override frozen to true.
    model_config = ConfigDict(frozen=True)

    account_id: str = ""
    plan_id: str = ""
    reason: str = ""
    type: Annotated[ContractViolationType, Field(deprecated=True)]
    violation_type: ContractExecutionViolationType
    sub_account_id: str = ""


## Violation Enum types
class PostingInstructionBatchError(VaultBaseModel):
    type: PostingInstructionBatchErrorType
    message: str


class PostingInstructionBatchErrorType(str, Enum):
    INVALID_ARGUMENT = "POSTING_INSTRUCTION_BATCH_ERROR_TYPE_INVALID_ARGUMENT"
    INTERNAL = "POSTING_INSTRUCTION_BATCH_ERROR_TYPE_INTERNAL"
    SERVICE_UNAVAILABLE = "POSTING_INSTRUCTION_BATCH_ERROR_TYPE_SERVICE_UNAVAILABLE"
    ABORTED = "POSTING_INSTRUCTION_BATCH_ERROR_TYPE_ABORTED"


class PostingViolation(VaultBaseModel):
    # This will preserve any config from the VaultBaseModel and simply override frozen to true.
    model_config = ConfigDict(frozen=True)

    type: PostingViolationType


class PostingViolationType(str, Enum):
    CLIENT_TRANSACTION_ALREADY_EXISTS = "POSTING_VIOLATION_CLIENT_TRANSACTION_ALREADY_EXISTS"
    CLIENT_TRANSACTION_DOES_NOT_EXIST = "POSTING_VIOLATION_CLIENT_TRANSACTION_DOES_NOT_EXIST"
    AUTH_WITH_NEGATIVE_AMOUNT = (
        "POSTING_VIOLATION_ADJUSTMENT_YIELDS_AUTHORISATION_WITH_NEGATIVE_AMOUNT"
    )
    CLIENT_TRANSACTION_CLOSED = "POSTING_VIOLATION_CLIENT_TRANSACTION_CLOSED"
    CLIENT_TRANSACTION_INVALID_OPERATION = "POSTING_VIOLATION_CLIENT_TRANSACTION_INVALID_OPERATION"


class AccountViolationType(str, Enum):
    ACCOUNT_NOT_PRESENT = "ACCOUNT_VIOLATION_ACCOUNT_NOT_PRESENT"
    ACCOUNT_STATUS_INVALID = "ACCOUNT_VIOLATION_ACCOUNT_STATUS_INVALID"
    UNSUPPORTED_DENOMINATION = "ACCOUNT_VIOLATION_UNSUPPORTED_DENOMINATION"
    PAYMENT_DEVICE_INVALID = "ACCOUNT_VIOLATION_PAYMENT_DEVICE_INVALID"
    MULTIPLE_PROCESSING_GROUPS = "ACCOUNT_VIOLATION_MULTIPLE_PROCESSING_GROUPS"
    INTERNAL_ACCOUNT_PROCESSING_LABEL_NOT_PRESENT = (
        "ACCOUNT_VIOLATION_INTERNAL_ACCOUNT_PROCESSING_LABEL_NOT_PRESENT"
    )
    SUB_ACCOUNT_NOT_PRESENT = "ACCOUNT_VIOLATION_SUB_ACCOUNT_NOT_PRESENT"
    SUB_ACCOUNT_STATUS_INVALID = "ACCOUNT_VIOLATION_SUB_ACCOUNT_STATUS_INVALID"
    ADDRESS_NOT_PERMITTED = "ACCOUNT_VIOLATION_ADDRESS_NOT_PERMITTED"
    VALUE_OR_BOOKING_TIMESTAMP_BEFORE_SUB_ACCOUNT_ACTIVATION = (
        "ACCOUNT_VIOLATION_VALUE_OR_BOOKING_TIMESTAMP_BEFORE_SUB_ACCOUNT_ACTIVATION"
    )


class RestrictionViolationType(str, Enum):
    UNKNOWN = "RESTRICTION_VIOLATION_TYPE_UNKNOWN"
    PREVENT_CREDITS = "RESTRICTION_VIOLATION_TYPE_PREVENT_CREDITS"
    PREVENT_DEBITS = "RESTRICTION_VIOLATION_TYPE_PREVENT_DEBITS"
    REVIEW_CREDITS = "RESTRICTION_VIOLATION_TYPE_REVIEW_CREDITS"
    REVIEW_DEBITS = "RESTRICTION_VIOLATION_TYPE_REVIEW_DEBITS"
    LIMIT_CREDITS = "RESTRICTION_VIOLATION_TYPE_LIMIT_CREDITS"
    LIMIT_DEBITS = "RESTRICTION_VIOLATION_TYPE_LIMIT_DEBITS"


class ContractViolationType(str, Enum):
    TC_BREACH = "CONTRACT_VIOLATION_BREACH_TERMS_AND_CONDITIONS"
    INSUFFICIENT_FUNDS = "CONTRACT_VIOLATION_INSUFFICIENT_FUNDS"


class ContractExecutionViolationType(str, Enum):
    UNKNOWN = "CONTRACT_EXECUTION_VIOLATION_UNKNOWN"
    TC_BREACH = "CONTRACT_EXECUTION_VIOLATION_BREACH_TERMS_AND_CONDITIONS"
    INSUFFICIENT_FUNDS = "CONTRACT_EXECUTION_VIOLATION_INSUFFICIENT_FUNDS"
    WRONG_DENOMINATION = "CONTRACT_EXECUTION_VIOLATION_WRONG_DENOMINATION"
    CLIENT_CUSTOM_REASON = "CONTRACT_EXECUTION_VIOLATION_CLIENT_CUSTOM_REASON"


class AdjustmentStatus(str, Enum):
    UNKNOWN = "STATUS_UNKNOWN"
    PENDING = "STATUS_PENDING"
    RUNNING = "STATUS_RUNNING"
    COMPLETED = "STATUS_COMPLETED"
    NO_ADJUSTMENT_REQUIRED = "STATUS_NO_ADJUSTMENT_REQUIRED"
    ERROR = "STATUS_ERROR"


class AdjustmentError(VaultBaseModel):
    # output only fields set by Vault
    message: str
    code: ErrorCode
    details: dict[str, str] | None = None


class ErrorCode(str, Enum):
    OK = "OK"
    CANCELLED = "CANCELLED"
    UNKNOWN = "UNKNOWN"
    INVALID_ARGUMENT = "INVALID_ARGUMENT"
    DEADLINE_EXCEEDED = "DEADLINE_EXCEEDED"
    NOT_FOUND = "NOT_FOUND"
    ALREADY_EXISTS = "ALREADY_EXISTS"
    PERMISSION_DENIED = "PERMISSION_DENIED"
    UNAUTHENTICATED = "UNAUTHENTICATED"
    RESOURCE_EXHAUSTED = "RESOURCE_EXHAUSTED"
    FAILED_PRECONDITION = "FAILED_PRECONDITION"
    ABORTED = "ABORTED"
    OUT_OF_RANGE = "OUT_OF_RANGE"
    UNIMPLEMENTED = "UNIMPLEMENTED"
    INTERNAL = "INTERNAL"
    UNAVAILABLE = "UNAVAILABLE"
    DATA_LOSS = "DATA_LOSS"


class Adjustment(VaultBaseModel):
    # output only fields set by Vault
    """
    :id: Unique UUID generated for the Adjustment.
    :schedule_job_id: ID of the Schedule Job which created this Adjustment.
    :resource_adjustment_count: The number of Adjustments created for the Account.
    :account_id: ID of the account that is the target of the Adjustment.
    :status: Current processing status.
    :error: Error details if this Adjustment failed.
    :create_timestamp: Datetime at which this Adjustment was created.
    :update_timestamp: Datetime of the most recent status update of this Adjustment.
    :previous_watermark_timestamp: Lower time bound for applied Adjustments (inclusive).
    :timeline_start_timestamp: Lower time bound for fetching related events.
    :timeline_end_timestamp: Upper time bound for fetching related events.
    :correction_posting_instruction_batch_ids: IDs of PIBs created as result of this Adjustment.
    """

    id: str
    schedule_job_id: str
    resource_adjustment_count: int
    account_id: str
    status: AdjustmentStatus
    error: AdjustmentError | None = None
    create_timestamp: Datetime
    update_timestamp: Datetime
    previous_watermark_timestamp: OptionalDatetime = None
    timeline_start_timestamp: OptionalDatetime = None
    timeline_end_timestamp: Datetime
    correction_posting_instruction_batch_ids: list[str] | None = None


class ListAdjustmentsRequest(VaultBaseModel):
    """
    :page_size: The maximum number of results to retrieve.
    :page_token: Optional token of the page to retrieve results from.
    :account_ids: Filter Adjustments by account ID. Exclusive with
        `schedule_job_ids`; one of the two is required.
    :schedule_job_ids: Filter Adjustments by the job ID that triggered them.
        Exclusive with `account_ids`; one of the two is required.
    """

    page_size: int
    page_token: str | None = None
    account_ids: list[str] | None = None
    schedule_job_ids: list[str] | None = None

    @model_validator(mode="before")
    @classmethod
    def validate_model(cls, data: Any) -> Any:
        if isinstance(data, dict):
            cls.one_of_validator(
                data=data,
                field_names=["account_ids", "schedule_job_ids"],
            )
        return data


class ListAdjustmentsResponse(VaultBaseModel):
    """
    :adjustments: A list of Adjustments that match the applied filters. Ordered by
        descending update_timestamp, then by resource ID.
    :previous_page_token: The pagination token to retrieve the previous page of results.
    :next_page_token: The pagination token to retrieve the next page of results.
    """

    adjustments: Sequence[Adjustment]
    previous_page_token: str
    next_page_token: str


class BatchGetAdjustmentsRequest(VaultBaseModel):
    """
    :ids: A list of Adjustment IDs.
    """

    ids: list[str]


class BatchGetAdjustmentsResponse(VaultBaseModel):
    """
    :adjustments: Retrieved map of Adjustments keyed by ID.
    """

    adjustments: dict[str, Adjustment]


class BulkRetryAdjustmentsRequest(VaultBaseModel):
    """
    :retry_requests: A list of retry Adjustment requests.
    """

    retry_requests: list[AdjustmentsRetryRequest]


class AdjustmentsRetryRequest(VaultBaseModel):
    """
    :request_id: Unique ID for the retry request.
    :id: The ID of the Adjustment.
    """

    request_id: str
    id: str


class BulkRetryAdjustmentsResponse(VaultBaseModel):
    """
    :errors: Errors raised against any retry requests.
    """

    errors: dict[str, AdjustmentError]


# Product Version Types
class Product(VaultBaseModel):
    id: str
    display_name: str
    is_internal: bool
    current_version_id: str


class BatchGetProductsRequest(VaultBaseModel):
    ids: list[str]


class BatchGetProductsResponse(VaultBaseModel):
    products: dict[str, Product]


class ParamNumberField(VaultBaseModel):
    """The number field object describes the range of accepted values and step."""

    value_type: NumberValueType
    min_value: Decimal_
    max_value: Decimal_
    step: Decimal_


class ParamAccountField(VaultBaseModel):
    """The account field object has no fields, according to the Core API spec."""


class ParamValueChoiceField(VaultBaseModel):
    """The value choice field contains a list of choices for this parameter."""

    value_choices: list[ValueChoice]


class ValueChoice(VaultBaseModel):
    value: str
    display_name: str


class ParamDenominationField(VaultBaseModel):
    """The denomination field contains a list of accepted denominations for this parameter."""

    permitted_denomination: list[str]


class DateType(VaultBaseModel):
    year: int
    month: int
    day: int


class ParamDateField(VaultBaseModel):
    """The date field describes the date type and range for this parameter."""

    type: DateValueType
    start: DateType
    end: DateType


class ParamStringField(VaultBaseModel):
    """The string field object has no fields, according to the Core API spec."""


class ProductVersionParameter(VaultBaseModel):
    name: str
    display_name: str
    description: str
    value: str
    default_value: str
    effective_timestamp: Datetime
    level: ProductVersionParameterLevel
    update_permission: ProductVersionParameterUpdatePermission
    derived: bool
    is_optional: bool

    # Parameter types - only one should be populated
    number: ParamNumberField | None = None
    account: ParamAccountField | None = None
    values: ParamValueChoiceField | None = None
    denomination: ParamDenominationField | None = None
    date: ParamDateField | None = None
    str_: ParamStringField | None = Field(default=None, serialization_alias="str")

    @model_validator(mode="before")
    @classmethod
    def validate_model(cls, data: Any) -> Any:
        if isinstance(data, dict):
            cls.one_of_validator(
                data=data,
                field_names=[
                    "number",
                    "account",
                    "values",
                    "denomination",
                    "date",
                    "str",  # should match key/alias here
                ],
            )
        return data


class AttributeDecimalType(VaultBaseModel):
    """The attribute decimal type object has no fields, according to the Core API spec."""


class AttributeDatetimeType(VaultBaseModel):
    """The attribute datetime type object has no fields, according to the Core API spec."""


class AttributeStringType(VaultBaseModel):
    """The attribute string type object has no fields, according to the Core API spec."""


class AttributeType(VaultBaseModel):
    decimal_type: AttributeDecimalType | None = None
    datetime_type: AttributeDatetimeType | None = None
    string_type: AttributeStringType | None = None

    @model_validator(mode="before")
    @classmethod
    def validate_model(cls, data: Any) -> Any:
        if isinstance(data, dict):
            cls.one_of_validator(
                data=data,
                field_names=[
                    "decimal_type",
                    "datetime_type",
                    "string_type",
                ],
            )
        return data


class ProductVersionAttribute(VaultBaseModel):
    name: str
    data_type: AttributeType


class ProductVersionAddressDetails(VaultBaseModel):
    address_name: str
    description: str
    tags: list[str]


class SemanticVersion(VaultBaseModel):
    major: int
    minor: int
    patch: int
    label: str

    @property
    def version_string(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}{self.label}"


class SharedFunctionArgs(VaultBaseModel):
    name: str
    type: str


class SharedFunction(VaultBaseModel):
    name: str
    args: list[SharedFunctionArgs]
    return_type: str


class SharedFunctionDetails(VaultBaseModel):
    shared_functions: list[SharedFunction]


class ContractModuleDetails(VaultBaseModel):
    alias_to_shared_function_details: dict[str, SharedFunctionDetails]


class ExpectedParameter(VaultBaseModel):
    parameter_id: str
    is_optional: bool
    triggers_pre_parameter_change_hook: bool
    triggers_post_parameter_change_hook: bool


class HighVolumeEligibility(VaultBaseModel):
    ledger: bool


class ProductVersion(VaultBaseModel):
    id: str
    product_id: str
    display_name: str | None = None
    display_version_number: SemanticVersion
    description: str | None = None
    summary: str | None = None
    tags: list[str] | None = None
    core_tags: list[ProductVersionCoreTag] | None = None
    is_current: bool
    code: str
    params: list[ProductVersionParameter] | None = None
    address_details: list[ProductVersionAddressDetails]
    attributes: list[ProductVersionAttribute]
    contracts_language_api_version: SemanticVersion
    contract_module_details: ContractModuleDetails | None = None
    expected_parameters: list[ExpectedParameter]
    high_volume_eligibility: HighVolumeEligibility | None = None
    notification_types: list[str]
    parameter_id_by_instance_parameter_name: dict[str, str]
    adjustments_versioning_policy: AdjustmentsVersioningPolicy | None = None
    adjustments_patch_version_id: str | None = None
    supported_denominations: list[str]
    tside: Tside
    create_timestamp: Datetime


class ProductVersionUpdateProductVersion(VaultBaseModel):
    """
    Product version model for update operations.

    Includes the subset of the fields of the `ProductVersion` model that can be
    specified in an update request.
    """

    id: str
    adjustments_versioning_policy: AdjustmentsVersioningPolicy | None = None
    adjustments_patch_version_id: str | None = None


_PRODUCT_VERSION_UPDATE_MUTABLE_FIELDS: list[str] = [
    "adjustments_patch_version_id",
    "adjustments_versioning_policy",
]


class ProductVersionUpdate(VaultBaseModel):
    """
    Model for updating a product version in a batch update request.

    Only the fields in `_PRODUCT_VERSION_UPDATE_MUTABLE_FIELDS` can be updated
    """

    product_version: ProductVersionUpdateProductVersion
    update_mask: UpdateMask

    @model_validator(mode="after")
    def validate_update_mask_fields(self) -> ProductVersionUpdate:
        """
        Validate that only allowed fields are specified in the update_mask.
        """
        invalid_fields = sorted(
            set(self.update_mask.paths) - set(_PRODUCT_VERSION_UPDATE_MUTABLE_FIELDS)
        )
        if invalid_fields:
            raise ValueError(
                f"Invalid fields in update_mask: {invalid_fields}. "
                f"Only the following fields can be updated: "
                f"{_PRODUCT_VERSION_UPDATE_MUTABLE_FIELDS}"
            )
        return self


class ListProductVersionsRequestBody(VaultBaseModel):
    product_id: str
    view: ProductVersionView | None = None
    page_size: int
    page_token: str | None = None


class ListProductVersionsResponse(VaultBaseModel):
    product_versions: list[ProductVersion]
    previous_page_token: str
    next_page_token: str


class CreateProductVersionParameter(VaultBaseModel):
    """
    Parameter model for create product version requests.

    Includes the subset of the fields of the `ProductVersionParameter` model that can be
    specified in a create request.
    """

    name: str
    value: str


class CreateProductVersionRequestProductVersion(VaultBaseModel):
    """
    Product version model for create product version requests.

    Includes the subset of the fields of the `ProductVersion` model that can be
    specified in a create request.
    """

    product_id: str
    display_name: str | None = None
    description: str | None = None
    summary: str | None = None
    tags: list[str] | None = None
    core_tags: list[ProductVersionCoreTag] | None = None
    code: str
    params: list[CreateProductVersionParameter] | None = None
    high_volume_eligibility: HighVolumeEligibility | None = None
    supported_denominations: list[str] | None = None
    adjustments_versioning_policy: AdjustmentsVersioningPolicy | None = None


class CreateProductVersionRequestBody(VaultBaseModel):
    request_id: str
    product_version: CreateProductVersionRequestProductVersion
    migration_strategy: ProductVersionMigrationStrategy | None = None
    is_internal: bool

    @model_validator(mode="after")
    def check_supported_denominations_exists_non_internal(self) -> CreateProductVersionRequestBody:
        if not self.is_internal and not self.product_version.supported_denominations:
            raise ValueError(
                "`product_version.supported_denominations` is required for non-internal products"
            )
        return self


class BatchUpdateProductVersionsRequestBody(VaultBaseModel):
    """
    Request body for `POST /v1/product-versions:batchUpdate` endpoint.
    """

    request_id: str
    product_version_updates: list[ProductVersionUpdate]


class BatchUpdateProductVersionsResponse(VaultBaseModel):
    """
    Response for `POST /v1/product-versions:batchUpdate` endpoint.
    """

    product_versions: list[ProductVersion]


class BatchGetProductVersionsRequest(VaultBaseModel):
    """Request for batch getting product versions."""

    ids: list[str]
    view: ProductVersionView | None = None


class BatchGetProductVersionsResponse(VaultBaseModel):
    """Response from batch getting product versions."""

    product_versions: dict[str, ProductVersion]


class UpdateProductVersionParams(VaultBaseModel):
    """
    Model for updating product version params.

    Effective timestamp must be formatted as RFC3339 timestamp and not set in the past. If missing,
    will default to the current time. The `value` field is nullable because it is not required in
    the list of `items_to_remove` when making a request to update a param.
    """

    name: str
    value: str | None = None
    effective_timestamp: OptionalDatetime = None


class UpdateProductVersionParamsRequestBody(VaultBaseModel):
    """Request body for `POST /v1/product-versions/{product_version_id}:updateParams endpoint."""

    product_version_id: str
    request_id: str
    items_to_add: list[UpdateProductVersionParams]
    items_to_remove: list[UpdateProductVersionParams]

    @model_validator(mode="after")
    def validate_items(self) -> UpdateProductVersionParamsRequestBody:
        if self.items_to_add and not self._has_value_field_populated(self.items_to_add):
            raise ValueError("`items_to_add.value` is required")
        if self.items_to_remove and self._has_value_field_populated(self.items_to_remove):
            raise ValueError("`items_to_remove.value` is not required")
        return self

    def _has_value_field_populated(self, items: list[UpdateProductVersionParams]) -> bool:
        for item in items:
            if not item.value:
                return False
        return True


class ProductVersionParamTimeseriesValue(VaultBaseModel):
    value: str
    effective_from_timestamp: Datetime


class ProductVersionParamTimeseries(VaultBaseModel):
    param_name: str
    values: list[ProductVersionParamTimeseriesValue]


class ProductVersionParamTimeseriesResponse(VaultBaseModel):
    product_version_param_timeseries: list[ProductVersionParamTimeseries]


class _ListAccountAttributeValuesRequest(VaultBaseModel):
    account_ids: list[str]
    attribute_names: list[str]
    effective_timestamps: list[Datetime] | None = None


class ListAccountAttributeValuesRequest(_ListAccountAttributeValuesRequest, VaultBaseModel):
    page_size: int
    page_token: str | None = None


class ListAccountAttributeValuesResponse(VaultBaseModel):
    account_attribute_values: list[AccountAttributeValue]
    previous_page_token: str
    next_page_token: str


class AccountAttributeValue(VaultBaseModel):
    account_id: str
    attribute_name: str
    effective_timestamp: Datetime
    value: AttributeValue


class AttributeValue(VaultBaseModel):
    string_value: AttributeStringValue | None = None
    decimal_value: AttributeDecimalValue | None = None
    date_time_value: AttributeDateTimeValue | None = None

    @model_validator(mode="before")
    @classmethod
    def validate_model(cls, data: Any) -> Any:
        if isinstance(data, dict):
            cls.one_of_validator(
                data=data,
                field_names=[
                    "string_value",
                    "decimal_value",
                    "date_time_value",
                ],
            )
        return data


class AttributeStringValue(VaultBaseModel):
    value: str


class AttributeDecimalValue(VaultBaseModel):
    value: Decimal_


class AttributeDateTimeValue(VaultBaseModel):
    value: Datetime
