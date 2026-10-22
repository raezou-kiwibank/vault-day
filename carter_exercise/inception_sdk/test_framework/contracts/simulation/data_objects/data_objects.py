# Copyright @ 2022 Thought Machine Group Limited. All rights reserved.
# standard libs
import enum
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from zoneinfo import ZoneInfo

# inception sdk
import inception_sdk.vault.core_api as core_api
from inception_sdk.test_framework.common.balance_helpers import NetBalances
from inception_sdk.test_framework.contracts.simulation.data_objects.events.parameter_events import (
    CreateGlobalParameterEvent,
)

# This import guarantees the model is defined before the we extend it in this module
# AttributeValue used by ExpectedAccountAttributeValue inherited from core_api.AccountAttributeValue
from inception_sdk.vault.core_api import AttributeValue  # noqa: F401


@dataclass
class SimulationEvent:
    time: datetime
    event: dict


@dataclass
class SubAccountConfig:
    """
    SubAccountConfig dataclass.
    Modelled on core_api.SubAccount, containing only the fields necessary
    for opening a Sub-Account in simulation.

    :param id: ID of the Sub-Account
    :param type: type of the Sub-Account
    :param status: status of the Sub-Account
    """

    id: str
    type: str
    status: core_api.SubAccountStatus


@dataclass
class AccountConfig:
    instance_params: dict[str, str] | None = None
    parameter_values: dict[str, core_api.ParameterValue] | None = None
    account_id_base: str = "Main account"
    number_of_accounts: int = 1
    permitted_denominations: list[str] = field(default_factory=list)
    sub_accounts: list[SubAccountConfig] | None = None

    def __post_init__(self):
        if self.instance_params is not None and self.parameter_values is not None:
            raise ValueError(
                "Cannot provide both instance_params and parameter_values for account."
            )


@dataclass
class ContractModuleConfig:
    alias: str
    file_path: str
    version_id: str = ""


@dataclass
class ContractConfig:
    template_params: dict[str, str]
    account_configs: list[AccountConfig]
    contract_file_path: str | None = None
    contract_content: str | None = None
    clu_resource_id: str | None = None
    smart_contract_version_id: str = "0"
    linked_contract_modules: list[ContractModuleConfig] | None = None
    global_params: list[CreateGlobalParameterEvent] | None = None

    def __post_init__(self):
        if self.contract_file_path is None and self.contract_content is None:
            raise ValueError("Neither contract_file_path or contract_content has been provided.")


@dataclass
class SupervisorConfig:
    supervisee_contracts: list[ContractConfig]
    supervisor_file_path: str | None = None
    supervisor_contract: str | None = None
    plan_id: str = "1"
    supervisor_contract_version_id: str = "supervisor version 1"
    associate_supervisees_to_plan: bool = True
    global_params: list[CreateGlobalParameterEvent] | None = None

    def __post_init__(self):
        if self.supervisor_file_path is None and self.supervisor_contract is None:
            raise ValueError(
                "Neither supervisor_file_path or supervisor_contract has been provided."
            )


@dataclass
class SuperviseeConfig:
    contract_id: str
    contract_file: str
    account_name: str
    version: str
    instance_parameters: dict
    template_parameters: dict
    instances: int = 1
    linked_contract_modules: list[ContractModuleConfig] | None = None


@dataclass
class ExpectedRejection:
    """
    ExpectedRejection dataclass.
    Set either account_id or plan_id, if both are set a ValueError will be raised.
    Note: plan_id rejections are only available for Vault versions after 5.2.0.

    Deprecated: Use ExpectedAccountViolation, ExpectedPostingViolation, and
    ExpectedContractViolation instead - supported from Vault Core 5.7.0.

    :param timestamp: datetime for expected rejection.
    :param rejection_type: rejection type string.
    :param rejection_reason: rejection reason string.
    :param account_id: Defaults to "Main account" when neither account_id or plan_id is set.
    :param plan_id: plan id string (only to be used after Vault 5.2.0)
    :raises ValueError: Raises ValueError if both account_id and plan_id are set.
    """

    timestamp: datetime
    rejection_type: str
    rejection_reason: str
    account_id: str | None = None
    plan_id: str | None = None

    def __post_init__(self):
        if self.account_id and self.plan_id:
            raise ValueError(
                f"The account_id and plan_id cannot both be set on {self}. "
                f"See ExpectedRejection docstring for more details."
            )

        # Setting account_id default value here for backwards compatibility.
        if self.account_id is None and self.plan_id is None:
            self.account_id = "Main account"


@dataclass
class ExpectedContractError:
    """
    ExpectedContractError dataclass.

    :param timestamp: datetime for expected contract error.
    :param account_id: id of the account in which the contract error is thrown.
    :param exception_type: optional exception type string.
    """

    timestamp: datetime
    account_id: str
    exception_type: str = ""


@dataclass
class ExpectedSchedule:
    run_times: list[datetime]
    event_id: str
    account_id: str = ""
    plan_id: str = ""
    count: int | None = None

    def __post_init__(self):
        if not (self.account_id) and not (self.plan_id) or (self.account_id and self.plan_id):
            raise ValueError(f"Exactly one of account_id and plan_id must set on {self}. ")


@dataclass
class ExpectedDerivedParameter:
    timestamp: datetime
    account_id: str = "Main account"
    name: str = ""
    value: str = ""


class ContractNotificationResourceType(enum.Enum):
    RESOURCE_ACCOUNT = "RESOURCE_ACCOUNT"
    RESOURCE_PLAN = "RESOURCE_PLAN"


@dataclass
class ExpectedContractNotification:
    timestamp: datetime
    notification_type: str
    notification_details: dict[str, str]
    resource_id: str
    resource_type: ContractNotificationResourceType


@dataclass
class ExpectedPostingEnrichments:
    """
    ExpectedPostingEnrichments dataclass.

    :param account_id: id of the account associated with the enrichment details.
    :param enrichment_details: metadata from pre-posting hook.
    """

    account_id: str
    enrichment_details: dict[str, str]


@dataclass
class ExpectedAccountViolation:
    account_violation: core_api.AccountViolation
    client_transaction_id: str | None = None


@dataclass
class ExpectedContractViolation:
    contract_violation: core_api.ContractViolation
    client_transaction_id: str | None = None


@dataclass
class ExpectedPostingViolation:
    posting_violation: core_api.PostingViolation
    client_transaction_id: str | None = None


class ExpectedAccountAttributeValue(core_api.AccountAttributeValue):
    # This class is used for assertions in SubTest which has the same fields as a
    # Core API Account Attribute Value

    def to_core_api_model(self):
        # This method is used to convert to the Core API model for equality comparison,
        # as Pydantic model equality requires objects to be of the same type.
        return core_api.AccountAttributeValue(**self.model_dump())


@dataclass
class ExpectedSubAccountEvent(ABC):
    """
    ExpectedSubAccountEvent dataclass
    Abstract Base Class extended by different Sub-Account scenarios,
    used to assert on expected values in a SubTest

    :param timestamp: exact datetime the event was processed
    :param parent_account_id: expected id of the parent Account
    :param sub_account_id: expected Sub-Account id
    """

    timestamp: datetime
    parent_account_id: str
    sub_account_id: str

    @property
    @abstractmethod
    def expected_log_pattern(self) -> re.Pattern:
        """Returns the compiled regex pattern expected for this event."""
        pass


@dataclass
class ExpectedSubAccountCreateWithAccountEvent(ExpectedSubAccountEvent):
    """
    ExpectedSubAccountCreateWithAccountEvent dataclass
    Used to assert on the event of creating a Sub-Account on an Account
    as part of the Account's creation, with the create_options field

    :param timestamp: exact datetime the event was processed
    :param parent_account_id: expected id of the parent Account
    :param sub_account_id: expected Sub-Account id
    """

    @property
    def expected_log_pattern(self) -> re.Pattern:
        parent_escaped = re.escape(self.parent_account_id)
        sub_escaped = re.escape(self.sub_account_id)

        pattern = (
            f'created account "{parent_escaped}" '
            # handles when multiple Sub-Accounts are in the create sub-accounts list
            f"created sub-accounts \\[(.*?){sub_escaped}(.*?)\\]"
        )

        return re.compile(pattern)


@dataclass
class ExpectedSubAccountCreateAfterAccountEvent(ExpectedSubAccountEvent):
    """
    ExpectedSubAccountCreateAfterAccountEvent dataclass
    Used to assert on the event of creating a Sub-Account on an Account after
    the Account has been created

    :param timestamp: exact datetime the event was processed
    :param parent_account_id: expected id of the parent Account
    :param sub_account_id: expected Sub-Account id
    """

    @property
    def expected_log_pattern(self) -> re.Pattern:
        parent_escaped = re.escape(self.parent_account_id)
        sub_escaped = re.escape(self.sub_account_id)

        pattern = f"created sub-account {sub_escaped} for account {parent_escaped}"

        return re.compile(pattern)


@dataclass
class SubTest:
    description: str
    expected_balances_at_ts: dict | None = None
    expected_value_balances_at_ts: dict | None = None
    expected_booking_balances_at_ts: dict | None = None
    expected_net_balances: dict[datetime, NetBalances] | None = None
    expected_schedules: list[ExpectedSchedule] | None = None
    expected_account_activation_rejections: list[ExpectedRejection] | None = None
    expected_account_conversion_rejections: list[ExpectedRejection] | None = None
    expected_account_deactivation_rejections: list[ExpectedRejection] | None = None
    expected_posting_rejections: list[ExpectedRejection] | None = None
    expected_parameter_change_rejections: list[ExpectedRejection] | None = None
    expected_derived_parameters: list[ExpectedDerivedParameter] | None = None
    expected_contract_notifications: list[ExpectedContractNotification] | None = None
    expected_contract_errors: list[ExpectedContractError] | None = None
    expected_posting_enrichments: list[ExpectedPostingEnrichments] | None = None
    expected_account_violations: dict[datetime, list[ExpectedAccountViolation]] | None = None
    expected_contract_violations: dict[datetime, list[ExpectedContractViolation]] | None = None
    expected_posting_violations: dict[datetime, list[ExpectedPostingViolation]] | None = None
    expected_account_attribute_values: list[ExpectedAccountAttributeValue] | None = None
    expected_sub_accounts: list[ExpectedSubAccountEvent] | None = None
    events: list[SimulationEvent] | None = None


@dataclass
class SimulationTestScenario:
    sub_tests: list[SubTest]
    start: datetime
    end: datetime
    contract_config: ContractConfig | None = None
    supervisor_config: SupervisorConfig | None = None
    internal_accounts: dict | None = None
    flag_definition_ids: list[str] | None = None
    calendar_ids: list[str] | None = None
    parameters: list[core_api.ParameterResource] | None = None
    debug: bool = False
    # Adding explicit flag for usage of Accounts V1
    # Defaulting to True to not break existing tests, this will be switched to
    # False in a future release where clients will then need to explicitly
    # use Accounts V1
    use_v1_accounts: bool = True
    # Mapping of parameter_id to tuple (parameter_value, parameter_value_id).
    # If the global parameter will be updated during the test, the parameter_value_id
    # must be set to a UUID which is then included in the update instruction.
    globally_owned_parameter_values: (
        dict[str, tuple[core_api.ParameterValue, str | None]] | None
    ) = None
    default_timezone: ZoneInfo | None = None

    def __post_init__(self):
        if self.use_v1_accounts:
            for sub_test in self.sub_tests:
                if sub_test.expected_contract_errors:
                    raise ValueError("Contract Errors are not supported for v1 Accounts.")
                if (
                    sub_test.expected_account_activation_rejections
                    or sub_test.expected_account_conversion_rejections
                    or sub_test.expected_account_deactivation_rejections
                ):
                    raise ValueError(
                        "The following features are not supported for v1 Accounts: "
                        "Account Activation Rejections, "
                        "Account Conversion Rejections, "
                        "Account Deactivation Rejections."
                    )
