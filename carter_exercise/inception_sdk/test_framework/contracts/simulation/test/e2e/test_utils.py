# standard libs
from datetime import datetime
from dateutil.relativedelta import relativedelta
from decimal import Decimal
from unittest import skip
from zoneinfo import ZoneInfo

# third party
from semantic_version import Version

# inception sdk
import inception_sdk.test_framework.contracts.simulation.errors as sim_errors
import inception_sdk.vault.core_api as core_api
import inception_sdk.vault.sim_api.contract_sim as sim
from inception_sdk.test_framework.common.balance_helpers import BalanceDimensions
from inception_sdk.test_framework.common.constants import ASSET
from inception_sdk.test_framework.common.test.input import account_attribute_value_contract
from inception_sdk.test_framework.common.utils import replace_clu_dependencies
from inception_sdk.test_framework.contracts.files import (
    EMPTY_ASSET_CONTRACT_V4,
    EMPTY_LIABILITY_CONTRACT_V4,
)
from inception_sdk.test_framework.contracts.simulation.data_objects.data_objects import (
    AccountConfig,
    ContractConfig,
    ContractNotificationResourceType,
    ExpectedAccountAttributeValue,
    ExpectedAccountViolation,
    ExpectedContractError,
    ExpectedContractNotification,
    ExpectedContractViolation,
    ExpectedPostingViolation,
    ExpectedRejection,
    ExpectedSchedule,
    SimulationTestScenario,
    SubTest,
    SupervisorConfig,
)
from inception_sdk.test_framework.contracts.simulation.helper import (
    create_inbound_hard_settlement_instruction,
    create_inbound_hard_settlement_posting_instruction_event,
    create_instance_parameter_change_event,
    create_outbound_hard_settlement_instruction,
    create_parameter_resource_mapping,
    list_account_attribute_values,
    update_account_status_pending_closure,
    update_parameter_value,
    v2_update_account_smart_contract_version_id,
    v2_update_account_status,
)
from inception_sdk.test_framework.contracts.simulation.test.mock_product import (
    expected_schedule_supervisee_contract,
    expected_schedule_supervisor_contract,
    parameter_rejection_contract,
)
from inception_sdk.test_framework.contracts.simulation.utils import (
    MAIN_ACCOUNT,
    SimulationTestCase,
    skipForVaultVersionLessThan,
)

UTC = ZoneInfo("UTC")

mock_product_dir = "inception_sdk/test_framework/contracts/simulation/test/mock_product/"
common_mock_product_dir = "inception_sdk/test_framework/common/test/input/"
PARAM_REJECTION_CONTRACT_FILE_PATH = mock_product_dir + "parameter_rejection_contract.py"
EXPECTED_SCHEDULE_SUPERVISEE_CONTRACT_FILE_PATH = (
    mock_product_dir + "expected_schedule_supervisee_contract.py"
)
EXPECTED_SCHEDULE_SUPERVISOR_CONTRACT_FILE_PATH = (
    mock_product_dir + "expected_schedule_supervisor_contract.py"
)
POSTING_REJECTION_SUPERVISEE_CONTRACT_FILE_PATH = (
    mock_product_dir + "posting_rejection_supervisee_contract.py"
)
POSTING_REJECTION_SUPERVISOR_CONTRACT_FILE_PATH = (
    mock_product_dir + "posting_rejection_supervisor_contract.py"
)
EXPECTED_ACTIVATION_REJECTION_CONTRACT_FILE_PATH = (
    mock_product_dir + "expected_activation_rejection_contract.py"
)
EXPECTED_CONVERSION_REJECTION_CONTRACT_FILE_PATH = (
    mock_product_dir + "expected_conversion_rejection_contract.py"
)
EXPECTED_DEACTIVATION_REJECTION_CONTRACT_FILE_PATH = (
    mock_product_dir + "expected_deactivation_rejection_contract.py"
)
EXPECTED_ERROR_FILE_PATH = mock_product_dir + "expected_error_contract.py"
EXPECTED_EXCEPTION_CONTRACT_FILE_PATH = mock_product_dir + "expected_exception_contract.py"
SIMPLE_MODULE = mock_product_dir + "simple_module.py"
SIMPLE_SMART_CONTRACT_WITH_CONTRACT_MODULES = (
    mock_product_dir + "simple_smart_contract_with_contract_modules.py"
)
SIMPLE_SUPERVISOR = mock_product_dir + "simple_supervisor.py"
ACCOUNT_ATTRIBUTE_VALUE_CONTRACT_FILE_PATH = (
    common_mock_product_dir + "account_attribute_value_contract.py"
)


class TestExtractParameters(SimulationTestCase):
    account_id_base = MAIN_ACCOUNT
    parameter_resource_dirs = ["inception_sdk/test_framework/common/test/input/parameters"]
    CONTRACT_FILE_PATH = "inception_sdk/test_framework/common/test/input/expected_parameters_contract.py"  # noqa: E501
    contract_filepaths = [CONTRACT_FILE_PATH, EMPTY_LIABILITY_CONTRACT_V4]

    def get_simulation_test_scenario(
        self,
        start,
        end,
        sub_tests,
        parameters=None,
        template_params=None,
        instance_params=None,
        internal_accounts=None,
        debug=False,
    ):
        if parameters is None:
            parameters = self.parameters
        contract_config = ContractConfig(
            contract_content=self.smart_contract_path_to_content,
            template_params=template_params or {},
            account_configs=[
                AccountConfig(
                    instance_params=instance_params or {},
                    account_id_base=self.account_id_base,
                )
            ],
        )
        return SimulationTestScenario(
            start=start,
            end=end,
            sub_tests=sub_tests,
            contract_config=contract_config,
            internal_accounts=internal_accounts,
            parameters=parameters,
            debug=debug,
        )

    def test_extracted_parameters_are_created(self):
        # Check that the parameters are extracted correctly
        self.assertListEqual(
            sorted(self.parameters, key=lambda x: x.id),
            [
                core_api.ParameterResource(
                    id="SOME_ACCOUNT_PARAMETER_RESOURCE",
                    constraint=core_api.AccountConstraint(
                        account_constraint=core_api.AccountConstraintValue()
                    ),
                    metadata={"description": "account parameter"},
                ),
                core_api.ParameterResource(
                    id="SOME_DATETIME_PARAMETER_RESOURCE",
                    constraint=core_api.DatetimeConstraint(
                        date_time_constraint=core_api.DatetimeConstraintValue(
                            precision=core_api.DatetimeConstraintPrecision.MINUTE,
                            earliest=datetime(2020, 1, 1, tzinfo=UTC),
                            latest=datetime(2040, 1, 1, tzinfo=UTC),
                        )
                    ),
                    metadata={"description": "datetime parameter"},
                ),
                core_api.ParameterResource(
                    id="SOME_DECIMAL_PARAMETER_RESOURCE",
                    constraint=core_api.DecimalConstraint(
                        decimal_constraint=core_api.DecimalConstraintValue(
                            min_value=Decimal(0),
                            max_value=Decimal(100),
                        )
                    ),
                    metadata={"description": "decimal parameter"},
                ),
                core_api.ParameterResource(
                    id="SOME_ENUMERATION_PARAMETER_RESOURCE",
                    constraint=core_api.EnumerationConstraint(
                        enumeration_constraint=core_api.EnumerationConstraintValue(
                            permitted_values=["green", "gold", "red"]
                        )
                    ),
                    metadata={"description": "enumeration parameter"},
                ),
                core_api.ParameterResource(
                    id="SOME_STRING_PARAMETER_RESOURCE",
                    constraint=core_api.StringConstraint(
                        string_constraint=core_api.StringConstraintValue(
                            min_length=1, max_length=100
                        )
                    ),
                    metadata={"description": "string parameter"},
                ),
            ],
        )
        self.smart_contract_path_to_content = self.smart_contract_path_to_content[
            self.CONTRACT_FILE_PATH
        ]
        start = datetime(year=2023, month=12, day=31, hour=23, tzinfo=ZoneInfo("UTC"))
        end = start + relativedelta(days=2)

        test_scenario = self.get_simulation_test_scenario(
            parameters=self.parameters,
            start=start,
            end=end,
            internal_accounts={"1": ASSET},
            sub_tests=[],
            instance_params={
                "SOME_ACCOUNT_PARAMETER_RESOURCE": "1",
                "SOME_ENUMERATION_PARAMETER_RESOURCE": "red",
                "SOME_DECIMAL_PARAMETER_RESOURCE": "0",
                "SOME_STRING_PARAMETER_RESOURCE": "123",
                "SOME_DATETIME_PARAMETER_RESOURCE": "2025-01-01",
            },
        )

        res = self.run_test_scenario(test_scenario)
        str_res = str(res)
        for parameter in self.parameters:
            search_string = f'created parameter "{parameter.id}"'
            self.assertIn(search_string, str_res)


class TestCheckParameterChangeRejections(SimulationTestCase):
    account_id_base = MAIN_ACCOUNT
    contract_filepaths = [PARAM_REJECTION_CONTRACT_FILE_PATH]

    def get_simulation_test_scenario(
        self,
        start,
        end,
        sub_tests,
        template_params=None,
        instance_params=None,
        internal_accounts=None,
        debug=False,
    ):
        contract_config = ContractConfig(
            contract_content=self.smart_contract_path_to_content[
                PARAM_REJECTION_CONTRACT_FILE_PATH
            ],
            template_params=template_params or {},
            account_configs=[
                AccountConfig(
                    instance_params=instance_params or {},
                    account_id_base=self.account_id_base,
                )
            ],
        )
        return SimulationTestScenario(
            start=start,
            end=end,
            sub_tests=sub_tests,
            contract_config=contract_config,
            internal_accounts=internal_accounts,
            debug=debug,
        )

    def test_restricted_parameter_change(self):
        start = datetime(year=2024, month=1, day=1, tzinfo=ZoneInfo("UTC"))
        rejected_datetime = start + relativedelta(seconds=1)
        accepted_datetime = rejected_datetime + relativedelta(seconds=1)
        end = accepted_datetime + relativedelta(seconds=1)

        instance_params = {
            parameter_rejection_contract.PARAM_REJECTED: "rejected",
            parameter_rejection_contract.PARAM_ACCEPTED: "accepted",
        }

        sub_tests = [
            SubTest(
                description="Reject restricted parameter change",
                events=[
                    create_instance_parameter_change_event(
                        timestamp=rejected_datetime,
                        account_id=self.account_id_base,
                        rejected_param="rejected",
                    ),
                ],
                expected_parameter_change_rejections=[
                    ExpectedRejection(
                        rejected_datetime,
                        account_id=self.account_id_base,
                        rejection_type="AgainstTermsAndConditions",
                        rejection_reason=(
                            f"Changes to {parameter_rejection_contract.PARAM_REJECTED} "
                            f"are not allowed."
                        ),
                    )
                ],
            ),
            SubTest(
                description="Accept non restricted parameter change",
                events=[
                    create_instance_parameter_change_event(
                        timestamp=accepted_datetime,
                        account_id=self.account_id_base,
                        accepted_param="new_value",
                    ),
                ],
                expected_parameter_change_rejections=[],
            ),
        ]

        test_scenario = self.get_simulation_test_scenario(
            start=start,
            end=end,
            sub_tests=sub_tests,
            instance_params=instance_params,
        )

        self.run_test_scenario(test_scenario)


class TestExpectedContractError(SimulationTestCase):
    account_id_base = f"{MAIN_ACCOUNT} "
    contract_filepaths = [EXPECTED_EXCEPTION_CONTRACT_FILE_PATH]

    def get_simulation_test_scenario(
        self,
        start,
        end,
        sub_tests,
        template_params=None,
        instance_params=None,
        internal_accounts=None,
        debug=False,
        use_v1_accounts=False,
    ):
        contract_config = ContractConfig(
            contract_content=self.smart_contract_path_to_content[
                EXPECTED_EXCEPTION_CONTRACT_FILE_PATH
            ],
            template_params=template_params or {},
            account_configs=[
                AccountConfig(
                    instance_params=instance_params,
                    account_id_base=self.account_id_base,
                )
            ],
        )
        return SimulationTestScenario(
            start=start,
            end=end,
            sub_tests=sub_tests,
            contract_config=contract_config,
            internal_accounts=internal_accounts,
            debug=debug,
            use_v1_accounts=use_v1_accounts,
        )

    @skipForVaultVersionLessThan(
        Version("5.4.0"),
        "Prior to Vault 5.4.0, Contract Simulation did not support ASv2, "
        "Contract Error Simulation Support have not been implemented.",
    )
    def test_expected_contract_error(self):
        start = datetime(year=2024, month=1, day=1, tzinfo=ZoneInfo("UTC"))
        end = start + relativedelta(seconds=1)

        sub_tests = [
            SubTest(
                description="Check Account Activation Rejection",
                expected_contract_errors=[
                    ExpectedContractError(
                        timestamp=start,
                        account_id=self.account_id_base,
                        exception_type="InvalidOperation",
                    )
                ],
            ),
        ]

        test_scenario = self.get_simulation_test_scenario(
            sub_tests=sub_tests,
            start=start,
            end=end,
            use_v1_accounts=False,
        )

        self.run_test_scenario(test_scenario)


class TestCheckAccountActivationRejections(SimulationTestCase):
    account_id_base = f"{MAIN_ACCOUNT} "
    contract_filepaths = [EXPECTED_ACTIVATION_REJECTION_CONTRACT_FILE_PATH]

    def get_simulation_test_scenario(
        self,
        start,
        end,
        sub_tests,
        template_params=None,
        instance_params=None,
        internal_accounts=None,
        debug=False,
        use_v1_accounts=False,
    ):
        contract_config = ContractConfig(
            contract_content=self.smart_contract_path_to_content[
                EXPECTED_ACTIVATION_REJECTION_CONTRACT_FILE_PATH
            ],
            template_params=template_params or {},
            account_configs=[
                AccountConfig(
                    instance_params=instance_params,
                    account_id_base=self.account_id_base,
                )
            ],
        )
        return SimulationTestScenario(
            start=start,
            end=end,
            sub_tests=sub_tests,
            contract_config=contract_config,
            internal_accounts=internal_accounts,
            debug=debug,
            use_v1_accounts=use_v1_accounts,
        )

    @skipForVaultVersionLessThan(
        Version("5.4.0"),
        "Prior to Vault 5.4.0, Contract Simulation did not support ASv2, "
        "Account Activation Rejections have not been implemented.",
    )
    def test_expected_account_activation_rejection(self):
        start = datetime(year=2024, month=1, day=1, tzinfo=ZoneInfo("UTC"))
        end = start + relativedelta(seconds=1)

        sub_tests = [
            SubTest(
                description="Check Account Activation Rejection",
                expected_account_activation_rejections=[
                    ExpectedRejection(
                        timestamp=start,
                        rejection_type="AGAINST TNC",
                        rejection_reason="Account Activation Failed.",
                    )
                ],
            )
        ]

        test_scenario = self.get_simulation_test_scenario(
            sub_tests=sub_tests,
            start=start,
            end=end,
            use_v1_accounts=False,
        )
        self.run_test_scenario(test_scenario)


class TestCheckAccountConversionRejections(SimulationTestCase):
    account_id_base = f"{MAIN_ACCOUNT} "
    contract_filepaths = [EXPECTED_CONVERSION_REJECTION_CONTRACT_FILE_PATH]

    def get_simulation_test_scenario(
        self,
        start,
        end,
        sub_tests,
        template_params=None,
        instance_params=None,
        internal_accounts=None,
        debug=False,
        use_v1_accounts=False,
    ):
        contract_config = ContractConfig(
            contract_content=self.smart_contract_path_to_content[
                EXPECTED_CONVERSION_REJECTION_CONTRACT_FILE_PATH
            ],
            template_params=template_params or {},
            account_configs=[
                AccountConfig(
                    instance_params=instance_params,
                    account_id_base=self.account_id_base,
                )
            ],
        )
        return SimulationTestScenario(
            start=start,
            end=end,
            sub_tests=sub_tests,
            contract_config=contract_config,
            internal_accounts=internal_accounts,
            debug=debug,
            use_v1_accounts=use_v1_accounts,
        )

    @skipForVaultVersionLessThan(
        Version("5.4.0"),
        "Prior to Vault 5.4.0, Contract Simulation did not support ASv2, "
        "Account Conversion Rejections have not been implemented.",
    )
    def test_expected_account_conversion_rejection(self):
        start = datetime(year=2024, month=1, day=1, tzinfo=ZoneInfo("UTC"))
        end = start + relativedelta(seconds=1)

        sub_tests = [
            SubTest(
                description="Check Account Conversion Rejection",
                events=[
                    v2_update_account_smart_contract_version_id(
                        timestamp=start + relativedelta(seconds=1),
                        account_id="Main account ",
                        smart_contract_version_id="0",
                    )
                ],
                expected_account_conversion_rejections=[
                    ExpectedRejection(
                        timestamp=start + relativedelta(seconds=1),
                        rejection_type="AGAINST TNC",
                        rejection_reason="Account Conversion Failed.",
                    )
                ],
            )
        ]

        test_scenario = self.get_simulation_test_scenario(
            sub_tests=sub_tests,
            start=start,
            end=end,
            use_v1_accounts=False,
        )

        self.run_test_scenario(test_scenario)


class TestCheckAccountDeactivationRejections(SimulationTestCase):
    account_id_base = f"{MAIN_ACCOUNT} "
    contract_filepaths = [EXPECTED_DEACTIVATION_REJECTION_CONTRACT_FILE_PATH]

    def get_simulation_test_scenario(
        self,
        start,
        end,
        sub_tests,
        template_params=None,
        instance_params=None,
        internal_accounts=None,
        debug=False,
        use_v1_accounts=False,
    ):
        contract_config = ContractConfig(
            contract_content=self.smart_contract_path_to_content[
                EXPECTED_DEACTIVATION_REJECTION_CONTRACT_FILE_PATH
            ],
            template_params=template_params or {},
            account_configs=[
                AccountConfig(
                    instance_params=instance_params,
                    account_id_base=self.account_id_base,
                )
            ],
        )
        return SimulationTestScenario(
            start=start,
            end=end,
            sub_tests=sub_tests,
            contract_config=contract_config,
            internal_accounts=internal_accounts,
            debug=debug,
            use_v1_accounts=use_v1_accounts,
        )

    @skipForVaultVersionLessThan(
        Version("5.4.0"),
        "Prior to Vault 5.4.0, Contract Simulation did not support ASv2, "
        "Account Deactivation Rejections have not been implemented.",
    )
    def test_expected_account_deactivation_rejection(self):
        start = datetime(year=2024, month=1, day=1, tzinfo=ZoneInfo("UTC"))
        end = start + relativedelta(seconds=2)

        sub_tests = [
            SubTest(
                description="Check Account Deactivation Rejection",
                events=[
                    v2_update_account_status(
                        timestamp=start + relativedelta(seconds=1),
                        account_id="Main account ",
                        status=core_api.AccountV2Status.ACCOUNT_STATUS_CLOSED,
                    )
                ],
                expected_account_deactivation_rejections=[
                    ExpectedRejection(
                        timestamp=start + relativedelta(seconds=1),
                        rejection_type="AGAINST TNC",
                        rejection_reason="Account Deactivation Failed.",
                    )
                ],
            )
        ]

        test_scenario = self.get_simulation_test_scenario(
            sub_tests=sub_tests,
            start=start,
            end=end,
            use_v1_accounts=False,
        )
        self.run_test_scenario(test_scenario)


class TestCheckPostingRejections(SimulationTestCase):
    account_id_base = f"{MAIN_ACCOUNT} "
    internal_accounts = {"DEFAULT_INTERNAL_ACCOUNT": "LIABILITY"}

    @classmethod
    def setUpClass(cls):
        cls.contract_filepaths = [
            POSTING_REJECTION_SUPERVISEE_CONTRACT_FILE_PATH,
            POSTING_REJECTION_SUPERVISOR_CONTRACT_FILE_PATH,
        ]
        cls.DEFAULT_SUPERVISEE_VERSION_IDS = {
            "supervisee": "1000",
        }

        super().setUpClass()

    def get_default_supervisor_config(self):
        supervisee_config = ContractConfig(
            template_params={},
            account_configs=[
                AccountConfig(
                    instance_params={},
                    account_id_base=self.account_id_base,
                    number_of_accounts=1,
                )
            ],
            contract_content=self.smart_contract_path_to_content[
                POSTING_REJECTION_SUPERVISEE_CONTRACT_FILE_PATH
            ],
            clu_resource_id="supervisee",
            smart_contract_version_id="1000",
        )

        supervisor_config = SupervisorConfig(
            supervisor_contract=self.smart_contract_path_to_content[
                POSTING_REJECTION_SUPERVISOR_CONTRACT_FILE_PATH
            ],
            supervisee_contracts=[supervisee_config],
            supervisor_contract_version_id="supervisor version 1",
            plan_id="1",
        )

        return supervisor_config

    @skipForVaultVersionLessThan(
        Version("5.2.0"),
        "Prior to Vault 5.2.0 only account id is used for expected rejections.",
    )
    def test_expected_posting_rejection_with_plan_id(self):
        start = datetime(year=2024, month=1, day=1, tzinfo=ZoneInfo("UTC"))
        rejected_datetime = start + relativedelta(seconds=1)
        accepted_datetime = start + relativedelta(seconds=2)
        end = accepted_datetime + relativedelta(seconds=1)

        sub_tests = [
            SubTest(
                description="Check posting rejection against plan id",
                events=[
                    create_outbound_hard_settlement_instruction(
                        amount="1000",
                        event_datetime=rejected_datetime,
                        target_account_id=f"{self.account_id_base}0",
                        internal_account_id="DEFAULT_INTERNAL_ACCOUNT",
                        denomination="GBP",
                    )
                ],
                expected_posting_rejections=[
                    ExpectedRejection(
                        timestamp=start + relativedelta(seconds=1),
                        rejection_type="AgainstTermsAndConditions",
                        rejection_reason="supervisor rejection",
                        # check with plan id
                        plan_id="1",
                    ),
                ],
            ),
            SubTest(
                description="Accept posting with force_override set to true",
                events=[
                    create_outbound_hard_settlement_instruction(
                        amount="1000",
                        event_datetime=accepted_datetime,
                        target_account_id=f"{self.account_id_base}0",
                        internal_account_id="DEFAULT_INTERNAL_ACCOUNT",
                        denomination="GBP",
                        instruction_details={"force_override": "true"},
                    )
                ],
                expected_balances_at_ts={
                    accepted_datetime: {
                        f"{self.account_id_base}0": [
                            (BalanceDimensions(denomination="GBP"), Decimal("1000")),
                        ],
                    },
                },
            ),
        ]

        test_scenario = SimulationTestScenario(
            sub_tests=sub_tests,
            start=start,
            end=end,
            supervisor_config=self.get_default_supervisor_config(),
            internal_accounts=self.internal_accounts,
        )

        self.run_test_scenario(test_scenario)

    def test_expected_posting_rejection_with_account_id(self):
        start = datetime(year=2024, month=1, day=1, tzinfo=ZoneInfo("UTC"))
        rejected_datetime = start + relativedelta(seconds=1)
        accepted_datetime = start + relativedelta(seconds=2)
        end = accepted_datetime + relativedelta(seconds=1)

        sub_tests = [
            SubTest(
                description="Check posting rejection against account id",
                events=[
                    create_outbound_hard_settlement_instruction(
                        amount="1000",
                        event_datetime=rejected_datetime,
                        target_account_id=self.account_id_base,
                        internal_account_id="DEFAULT_INTERNAL_ACCOUNT",
                        denomination="GBP",
                    )
                ],
                expected_posting_rejections=[
                    ExpectedRejection(
                        timestamp=rejected_datetime,
                        rejection_type="AgainstTermsAndConditions",
                        rejection_reason="supervisee rejection",
                        # check with account id
                        account_id=self.account_id_base,
                    )
                ],
            ),
            SubTest(
                description="Accept posting with force_override set to true",
                events=[
                    create_outbound_hard_settlement_instruction(
                        amount="1000",
                        event_datetime=accepted_datetime,
                        target_account_id=self.account_id_base,
                        internal_account_id="DEFAULT_INTERNAL_ACCOUNT",
                        denomination="GBP",
                        instruction_details={"force_override": "true"},
                    )
                ],
                expected_balances_at_ts={
                    accepted_datetime: {
                        self.account_id_base: [
                            (BalanceDimensions(denomination="GBP"), Decimal("1000")),
                        ],
                    },
                },
            ),
        ]

        contract_config = ContractConfig(
            template_params={},
            account_configs=[
                AccountConfig(
                    instance_params={},
                    account_id_base=self.account_id_base,
                    number_of_accounts=1,
                )
            ],
            contract_content=self.smart_contract_path_to_content[
                POSTING_REJECTION_SUPERVISEE_CONTRACT_FILE_PATH
            ],
            clu_resource_id="supervisee",
            smart_contract_version_id="1000",
        )
        test_scenario = SimulationTestScenario(
            start=start,
            end=end,
            sub_tests=sub_tests,
            contract_config=contract_config,
            internal_accounts=self.internal_accounts,
        )

        self.run_test_scenario(test_scenario)


class TestExpectedExceptions(SimulationTestCase):
    account_id_base = MAIN_ACCOUNT
    contract_filepaths = [EXPECTED_ERROR_FILE_PATH]
    default_instance_params: dict[str, str] = {"test_param": "test_value"}

    def get_simulation_test_scenario(
        self,
        start,
        end,
        sub_tests,
        template_params=None,
        instance_params=None,
        internal_accounts=None,
        debug=False,
    ):
        contract_config = ContractConfig(
            contract_content=self.smart_contract_path_to_content[EXPECTED_ERROR_FILE_PATH],
            template_params=template_params or {},
            account_configs=[
                AccountConfig(
                    instance_params=(
                        instance_params
                        if instance_params is not None
                        else self.default_instance_params
                    ),
                    account_id_base=self.account_id_base,
                )
            ],
        )
        return SimulationTestScenario(
            start=start,
            end=end,
            sub_tests=sub_tests,
            contract_config=contract_config,
            internal_accounts=internal_accounts,
            debug=debug,
        )

    def test_non_existent_parameter(self):
        """
        Checks error handling when a parameter value is provided on account creation
        for a parameter that doesn't exist
        """
        start = datetime(year=2024, month=1, day=1, tzinfo=ZoneInfo("UTC"))
        rejected_datetime = start + relativedelta(seconds=1)
        accepted_datetime = rejected_datetime + relativedelta(seconds=1)
        end = accepted_datetime + relativedelta(seconds=1)

        instance_params = {**self.default_instance_params, "non_existent_param": "dummy"}

        sub_tests = []

        test_scenario = self.get_simulation_test_scenario(
            start=start,
            end=end,
            sub_tests=sub_tests,
            instance_params=instance_params,
        )

        self.run_test_scenario(
            test_scenario,
            expected_simulation_error=sim_errors.AccountCreatedWithNonExistentInstanceParameter(
                "non_existent_param"
            ),
        )

    def test_non_existent_parameter_update(self):
        """
        Checks error handling when a parameter value is provided in an account update
        for a parameter that doesn't exist
        """
        start = datetime(year=2024, month=1, day=1, tzinfo=ZoneInfo("UTC"))
        rejected_datetime = start + relativedelta(seconds=1)
        accepted_datetime = rejected_datetime + relativedelta(seconds=1)
        end = accepted_datetime + relativedelta(seconds=1)

        sub_tests = [
            SubTest(
                description="Change nonexistent parameter after account creation",
                events=[
                    create_instance_parameter_change_event(
                        timestamp=rejected_datetime,
                        account_id=self.account_id_base,
                        non_existent_param="dummy",
                    ),
                ],
            )
        ]

        test_scenario = self.get_simulation_test_scenario(
            start=start,
            end=end,
            sub_tests=sub_tests,
        )

        self.run_test_scenario(
            test_scenario,
            expected_simulation_error=sim_errors.UpdateToNonExistentInstanceParameter(
                "non_existent_param"
            ),
        )

    def test_deactivation_error(self):
        start = datetime(year=2024, month=1, day=1, tzinfo=ZoneInfo("UTC"))
        closure_time = start + relativedelta(seconds=1)
        end = closure_time + relativedelta(seconds=1)

        sub_tests = [
            SubTest(
                description="Attempt closure that will fail",
                events=[
                    update_account_status_pending_closure(
                        timestamp=closure_time,
                        account_id=self.account_id_base,
                    ),
                ],
            )
        ]

        test_scenario = self.get_simulation_test_scenario(
            start=start,
            end=end,
            sub_tests=sub_tests,
        )

        self.run_test_scenario(
            test_scenario,
            expected_simulation_error=sim_errors.DeactivationFailure(
                account_id=self.account_id_base, reason_suffix="always fail"
            ),
        )

    def test_missing_parameter_value(self):
        start = datetime(year=2024, month=1, day=1, tzinfo=ZoneInfo("UTC"))
        rejected_datetime = start + relativedelta(seconds=1)
        accepted_datetime = rejected_datetime + relativedelta(seconds=1)
        end = accepted_datetime + relativedelta(seconds=1)

        test_scenario = self.get_simulation_test_scenario(
            start=start,
            end=end,
            sub_tests=[],
            # Parameter value is missing for test_param
            instance_params={},
        )

        self.run_test_scenario(
            test_scenario,
            expected_simulation_error=sim_errors.MissingInstanceParameterValue("test_param"),
        )


class TestExpectedSchedules(SimulationTestCase):
    account_id_base = f"{MAIN_ACCOUNT} "

    @classmethod
    def setUpClass(cls):
        cls.contract_filepaths = [
            EXPECTED_SCHEDULE_SUPERVISEE_CONTRACT_FILE_PATH,
            EXPECTED_SCHEDULE_SUPERVISOR_CONTRACT_FILE_PATH,
        ]
        cls.DEFAULT_SUPERVISEE_VERSION_IDS = {
            "supervisee": "1000",
        }

        super().setUpClass()

    def get_default_supervisor_config(self):
        supervisee_config = ContractConfig(
            template_params={},
            account_configs=[
                AccountConfig(
                    instance_params={},
                    account_id_base=self.account_id_base,
                    number_of_accounts=1,
                )
            ],
            contract_content=self.smart_contract_path_to_content[
                EXPECTED_SCHEDULE_SUPERVISEE_CONTRACT_FILE_PATH
            ],
            clu_resource_id="supervisee",
            smart_contract_version_id="1000",
        )

        supervisor_config = SupervisorConfig(
            supervisor_contract=self.smart_contract_path_to_content[
                EXPECTED_SCHEDULE_SUPERVISOR_CONTRACT_FILE_PATH
            ],
            supervisee_contracts=[supervisee_config],
            supervisor_contract_version_id="supervisor version 1",
            plan_id="1",
        )

        return supervisor_config

    def test_expected_schedules(self):
        start = datetime(year=2023, month=12, day=31, hour=23, tzinfo=ZoneInfo("UTC"))
        end = start + relativedelta(days=2)

        sub_tests = [
            SubTest(
                description="Check schedules are processed as expected",
                expected_schedules=[
                    ExpectedSchedule(
                        run_times=[
                            datetime(2024, 1, 1, 1, tzinfo=ZoneInfo("UTC")),
                            datetime(2024, 1, 2, 1, tzinfo=ZoneInfo("UTC")),
                        ],
                        event_id=expected_schedule_supervisor_contract.NON_OVERRIDING_EVENT,
                        plan_id="1",
                    ),
                    ExpectedSchedule(
                        run_times=[
                            datetime(2024, 1, 1, tzinfo=ZoneInfo("UTC")),
                            datetime(2024, 1, 2, tzinfo=ZoneInfo("UTC")),
                        ],
                        event_id=expected_schedule_supervisor_contract.OVERRIDING_EVENT,
                        plan_id="1",
                    ),
                    # These still appear in sim logs so we can test accordingly, but they won't
                    # result in hook execution
                    ExpectedSchedule(
                        run_times=[
                            datetime(2024, 1, 1, 2, tzinfo=ZoneInfo("UTC")),
                            datetime(2024, 1, 2, 2, tzinfo=ZoneInfo("UTC")),
                        ],
                        event_id=expected_schedule_supervisee_contract.EVENT_TO_OVERRIDE,
                        account_id="Main account 0",
                    ),
                    ExpectedSchedule(
                        run_times=[
                            datetime(2024, 1, 1, 3, tzinfo=ZoneInfo("UTC")),
                            datetime(2024, 1, 2, 3, tzinfo=ZoneInfo("UTC")),
                        ],
                        event_id=expected_schedule_supervisee_contract.EVENT_TO_LEAVE,
                        account_id="Main account 0",
                    ),
                ],
            ),
        ]

        test_scenario = SimulationTestScenario(
            sub_tests=sub_tests,
            start=start,
            end=end,
            supervisor_config=self.get_default_supervisor_config(),
            internal_accounts=self.internal_accounts,
        )

        self.run_test_scenario(test_scenario)


class TestSimulateRequest(SimulationTestCase):
    account_id_base = MAIN_ACCOUNT
    contract_filepaths = [
        EMPTY_ASSET_CONTRACT_V4,
    ]

    def _get_base_sim_request(self):
        return sim.SimulateRequest(
            start_timestamp=datetime(2024, 1, 1, tzinfo=UTC),
            end_timestamp=datetime(2024, 1, 2, tzinfo=UTC),
        )

    def test_simulate_simple_contract(self):
        smart_contracts = [
            sim.SmartContract(
                code=replace_clu_dependencies(
                    "UNKNOWN",
                    self.smart_contract_path_to_content[EMPTY_ASSET_CONTRACT_V4],
                    {},
                    remove_clu_syntax_for_unknown_ids=True,
                ),
                smart_contract_param_vals=dict(),
                smart_contract_version_id="1",
            )
        ]
        instructions = [
            sim.Instruction(
                timestamp=datetime(2024, 1, 2, tzinfo=UTC),
                instruction=sim.CreateAccount(
                    product_version_id="1",
                    id=self.account_id_base,
                ),
            )
        ]
        request = self._get_base_sim_request()
        request.smart_contracts = smart_contracts
        request.instructions = instructions
        res = self.run_simulation_test(request, [])
        logs = [logs for r in res for logs in r["result"]["logs"]]
        self.assertIn('created account "Main account"', logs)

    def test_simulate_supervised_contract(self):
        smart_contracts = [
            sim.SmartContract(
                code=self.smart_contract_path_to_content[EMPTY_ASSET_CONTRACT_V4],
                smart_contract_param_vals=dict(),
                smart_contract_version_id="1",
            )
        ]
        supervisor_contracts = [
            sim.SupervisorContract(
                code=replace_clu_dependencies(
                    "UNKNOWN",
                    self.read_smart_contract(SIMPLE_SUPERVISOR),
                    {"supervisee_version_id": "1"},
                    remove_clu_syntax_for_unknown_ids=True,
                ),
                supervisor_contract_version_id="supervisor_id_1",
            )
        ]
        instructions = [
            sim.Instruction(
                timestamp=datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC),
                instruction=sim.CreateAccount(
                    product_version_id="1",
                    id=self.account_id_base,
                ),
            ),
            sim.Instruction(
                timestamp=datetime(2024, 1, 1, 0, 0, 1, tzinfo=UTC),
                instruction=sim.CreatePlan(
                    id="plan_id_1",
                    supervisor_contract_version_id="supervisor_id_1",
                ),
            ),
            sim.Instruction(
                timestamp=datetime(2024, 1, 1, 0, 0, 2, tzinfo=UTC),
                instruction=sim.CreateAccountPlanAssoc(
                    id="assoc_id_1",
                    account_id=self.account_id_base,
                    plan_id="plan_id_1",
                    status=core_api.AccountPlanAssocStatus.ACCOUNT_PLAN_ASSOC_STATUS_ACTIVE,
                ),
            ),
        ]
        request = self._get_base_sim_request()
        request.smart_contracts = smart_contracts
        request.supervisor_contracts = supervisor_contracts
        request.instructions = instructions
        res = self.run_simulation_test(request, [])
        logs = [logs for r in res for logs in r["result"]["logs"]]
        self.assertIn('created account "Main account"', logs)
        self.assertIn(
            'created account plan association for account "Main account" and plan "plan_id_1"', logs
        )

    def test_simulate_contract_with_contract_modules(self):
        smart_contracts = [
            sim.SmartContract(
                code=self.read_smart_contract(SIMPLE_SMART_CONTRACT_WITH_CONTRACT_MODULES),
                smart_contract_param_vals=dict(),
                smart_contract_version_id="1",
            )
        ]
        contract_modules = [
            sim.ContractModule(
                code=self.read_smart_contract(SIMPLE_MODULE),
                contract_module_version_id="contract_module_id_1",
            )
        ]
        instructions = [
            sim.Instruction(
                timestamp=datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC),
                instruction=sim.CreateSmartContractModuleVersionsLink(
                    smart_contract_version_id="1",
                    alias_to_contract_module_version_id={"simple_module": "contract_module_id_1"},
                ),
            ),
            sim.Instruction(
                timestamp=datetime(2024, 1, 1, 0, 0, 1, tzinfo=UTC),
                instruction=sim.CreateAccount(
                    product_version_id="1",
                    id=self.account_id_base,
                ),
            ),
        ]
        request = self._get_base_sim_request()
        request.smart_contracts = smart_contracts
        request.contract_modules = contract_modules
        request.instructions = instructions

        sub_tests = [
            SubTest(
                description="Sub tests.",
                expected_balances_at_ts={},
                expected_schedules=[],
                expected_posting_rejections=[],
                expected_parameter_change_rejections=[],
                expected_derived_parameters=[],
                expected_contract_notifications=[
                    ExpectedContractNotification(
                        timestamp=datetime(2024, 1, 1, 0, 0, 1, tzinfo=UTC),
                        notification_type="activation_notification",
                        notification_details={
                            "msg": "Contract module value is 'simple value'.",
                        },
                        resource_id=self.account_id_base,
                        resource_type=ContractNotificationResourceType.RESOURCE_ACCOUNT,
                    )
                ],
            )
        ]
        res = self.run_simulation_test(request, sub_tests)
        logs = [logs for r in res for logs in r["result"]["logs"]]
        self.assertRegex(
            logs[0], 'created smart contract module versions link with id "[0-9a-f-]{36}"'
        )
        self.assertIn('created account "Main account"', logs)

    @skip("TODO.")
    def test_existing_contracts_and_modules(self):
        # TODO
        pass


class TestAccountsV2InstanceParameters(SimulationTestCase):
    account_id_base = MAIN_ACCOUNT
    parameter_resource_dirs = ["inception_sdk/test_framework/common/test/input/parameters"]
    CONTRACT_FILE_PATH = "inception_sdk/test_framework/contracts/simulation/test/mock_product/example_contract_with_instance_parameters.py"  # noqa: E501
    contract_filepaths = [CONTRACT_FILE_PATH, EMPTY_LIABILITY_CONTRACT_V4]

    def get_simulation_test_scenario(
        self,
        start,
        end,
        sub_tests,
        parameters=None,
        template_params=None,
        instance_params=None,
        parameter_values=None,
        internal_accounts=None,
        use_v1_accounts=True,
        debug=False,
    ):
        if parameters is None:
            parameters = self.parameters
        contract_config = ContractConfig(
            contract_content=self.smart_contract_path_to_content,
            template_params=template_params or {},
            account_configs=[
                AccountConfig(
                    parameter_values=parameter_values,
                    account_id_base=self.account_id_base,
                    permitted_denominations=["GBP"],
                )
            ],
        )
        return SimulationTestScenario(
            start=start,
            end=end,
            sub_tests=sub_tests,
            contract_config=contract_config,
            internal_accounts=internal_accounts,
            parameters=parameters,
            use_v1_accounts=use_v1_accounts,
            debug=True,
        )

    @skipForVaultVersionLessThan(
        Version("5.4.0"),
        "Prior to Vault 5.4.0, Contract Simulation did not support ASv2.",
    )
    def test_v2_account_creation_with_instance_parameters(self):
        self.smart_contract_path_to_content = self.smart_contract_path_to_content[
            self.CONTRACT_FILE_PATH
        ]
        start = datetime(year=2023, month=12, day=31, hour=23, tzinfo=ZoneInfo("UTC"))
        end = start + relativedelta(days=2)

        test_scenario = self.get_simulation_test_scenario(
            parameters=self.parameters,
            start=start,
            end=end,
            internal_accounts={"1": ASSET},
            sub_tests=[],
            parameter_values={
                "denomination": core_api.StringParameterValue(string_value="XOR"),
                "interest_rate": core_api.DecimalParameterValue(decimal_value=Decimal("0.19")),
            },
            use_v1_accounts=False,
        )

        res = self.run_test_scenario(test_scenario)
        str_res = str(res)

        self.assertIn('created account "Main account"', str_res)


class TestAccountsV2ExpectedParameters(SimulationTestCase):
    account_id_base = MAIN_ACCOUNT
    parameter_resource_dirs = ["inception_sdk/test_framework/common/test/input/parameters"]
    CONTRACT_FILE_PATH = "inception_sdk/test_framework/common/test/input/expected_parameters_contract.py"  # noqa: E501
    contract_filepaths = [CONTRACT_FILE_PATH, EMPTY_LIABILITY_CONTRACT_V4]

    def get_simulation_test_scenario(
        self,
        start,
        end,
        sub_tests,
        parameters=None,
        template_params=None,
        instance_params=None,
        parameter_values=None,
        globally_owned_parameter_values=None,
        internal_accounts=None,
        use_v1_accounts=True,
        debug=False,
    ):
        if parameters is None:
            parameters = self.parameters
        contract_config = ContractConfig(
            contract_content=self.smart_contract_path_to_content,
            template_params=template_params or {},
            account_configs=[
                AccountConfig(
                    parameter_values=parameter_values or {},
                    account_id_base=self.account_id_base,
                    permitted_denominations=["GBP"],
                )
            ],
        )
        return SimulationTestScenario(
            start=start,
            end=end,
            sub_tests=sub_tests,
            contract_config=contract_config,
            internal_accounts=internal_accounts,
            parameters=parameters,
            globally_owned_parameter_values=globally_owned_parameter_values or {},
            use_v1_accounts=use_v1_accounts,
            debug=True,
        )

    @skipForVaultVersionLessThan(
        Version("5.4.0"),
        "Prior to Vault 5.4.0, Contract Simulation did not support ASv2.",
    )
    def test_v2_account_creation_with_expected_parameters(self):
        # Check that the parameters are extracted correctly
        self.assertListEqual(
            sorted(self.parameters, key=lambda x: x.id),
            [
                core_api.ParameterResource(
                    id="SOME_ACCOUNT_PARAMETER_RESOURCE",
                    constraint=core_api.AccountConstraint(
                        account_constraint=core_api.AccountConstraintValue()
                    ),
                    metadata={"description": "account parameter"},
                ),
                core_api.ParameterResource(
                    id="SOME_DATETIME_PARAMETER_RESOURCE",
                    constraint=core_api.DatetimeConstraint(
                        date_time_constraint=core_api.DatetimeConstraintValue(
                            precision=core_api.DatetimeConstraintPrecision.MINUTE,
                            earliest=datetime(2020, 1, 1, tzinfo=UTC),
                            latest=datetime(2040, 1, 1, tzinfo=UTC),
                        )
                    ),
                    metadata={"description": "datetime parameter"},
                ),
                core_api.ParameterResource(
                    id="SOME_DECIMAL_PARAMETER_RESOURCE",
                    constraint=core_api.DecimalConstraint(
                        decimal_constraint=core_api.DecimalConstraintValue(
                            min_value=Decimal(0),
                            max_value=Decimal(100),
                        )
                    ),
                    metadata={"description": "decimal parameter"},
                ),
                core_api.ParameterResource(
                    id="SOME_ENUMERATION_PARAMETER_RESOURCE",
                    constraint=core_api.EnumerationConstraint(
                        enumeration_constraint=core_api.EnumerationConstraintValue(
                            permitted_values=["green", "gold", "red"]
                        )
                    ),
                    metadata={"description": "enumeration parameter"},
                ),
                core_api.ParameterResource(
                    id="SOME_STRING_PARAMETER_RESOURCE",
                    constraint=core_api.StringConstraint(
                        string_constraint=core_api.StringConstraintValue(
                            min_length=1, max_length=100
                        )
                    ),
                    metadata={"description": "string parameter"},
                ),
            ],
        )

        self.smart_contract_path_to_content = self.smart_contract_path_to_content[
            self.CONTRACT_FILE_PATH
        ]

        start = datetime(year=2023, month=12, day=31, hour=23, tzinfo=ZoneInfo("UTC"))
        end = start + relativedelta(days=2)

        sub_tests = [
            SubTest(
                description="Convert account",
                events=[
                    v2_update_account_smart_contract_version_id(
                        timestamp=start + relativedelta(seconds=1),
                        account_id="Main account",
                        smart_contract_version_id="0",
                    )
                ],
            ),
            SubTest(
                description="Update account status to closed",
                events=[
                    v2_update_account_status(
                        timestamp=start + relativedelta(seconds=2),
                        account_id="Main account",
                        status=core_api.AccountV2Status.ACCOUNT_STATUS_CLOSED,
                    )
                ],
            ),
        ]

        test_scenario = self.get_simulation_test_scenario(
            parameters=self.parameters,
            start=start,
            end=end,
            internal_accounts={"1": ASSET},
            sub_tests=sub_tests,
            parameter_values={
                "SOME_ACCOUNT_PARAMETER_RESOURCE": core_api.AccountIdParameterValue(
                    account_id_value="1"
                ),
                "SOME_ENUMERATION_PARAMETER_RESOURCE": core_api.EnumerationParameterValue(
                    enumeration_value="red"
                ),
                "SOME_DECIMAL_PARAMETER_RESOURCE": core_api.DecimalParameterValue(
                    decimal_value=Decimal("1")
                ),
                "SOME_STRING_PARAMETER_RESOURCE": core_api.StringParameterValue(string_value="123"),
                "SOME_DATETIME_PARAMETER_RESOURCE": core_api.DatetimeParameterValue(
                    date_time_value=datetime(2025, 1, 1, tzinfo=ZoneInfo("UTC"))
                ),
            },
            use_v1_accounts=False,
        )

        res = self.run_test_scenario(test_scenario)
        str_res = str(res)

        self.assertIn('created parameter "SOME_ACCOUNT_PARAMETER_RESOURCE"', str_res)
        self.assertIn('created parameter "SOME_ENUMERATION_PARAMETER_RESOURCE"', str_res)
        self.assertIn('created parameter "SOME_DECIMAL_PARAMETER_RESOURCE"', str_res)
        self.assertIn('created parameter "SOME_STRING_PARAMETER_RESOURCE"', str_res)
        self.assertIn('created parameter "SOME_DATETIME_PARAMETER_RESOURCE"', str_res)

        self.assertIn('created account "Main account"', str_res)
        self.assertIn('converted account "Main account" to smart contract version "0"', str_res)
        self.assertIn('closed account "Main account"', str_res)

    @skipForVaultVersionLessThan(
        Version("5.4.0"),
        "Prior to Vault 5.4.0, Contract Simulation did not support ASv2.",
    )
    def test_v2_account_creation_with_expected_parameters_clu_syntax(self):
        self.smart_contract_path_to_content = self.smart_contract_path_to_content[
            self.CONTRACT_FILE_PATH
        ]

        start = datetime(year=2023, month=12, day=31, hour=23, tzinfo=ZoneInfo("UTC"))
        end = start + relativedelta(days=2)

        sub_tests = [
            SubTest(
                description="Convert account",
                events=[
                    v2_update_account_smart_contract_version_id(
                        timestamp=start + relativedelta(seconds=1),
                        account_id="Main account",
                        smart_contract_version_id="0",
                    )
                ],
            ),
            SubTest(
                description="Update account status to closed",
                events=[
                    v2_update_account_status(
                        timestamp=start + relativedelta(seconds=2),
                        account_id="Main account",
                        status=core_api.AccountV2Status.ACCOUNT_STATUS_CLOSED,
                    )
                ],
            ),
        ]

        test_scenario = self.get_simulation_test_scenario(
            parameters=self.parameters,
            start=start,
            end=end,
            internal_accounts={"1": ASSET},
            sub_tests=sub_tests,
            parameter_values={
                "&{SOME_ACCOUNT_PARAMETER_RESOURCE}": core_api.AccountIdParameterValue(
                    account_id_value="1"
                ),
                "&{SOME_ENUMERATION_PARAMETER_RESOURCE}": core_api.EnumerationParameterValue(
                    enumeration_value="red"
                ),
                "&{SOME_DECIMAL_PARAMETER_RESOURCE}": core_api.DecimalParameterValue(
                    decimal_value=Decimal("1")
                ),
                "&{SOME_STRING_PARAMETER_RESOURCE}": core_api.StringParameterValue(
                    string_value="123"
                ),
                "&{SOME_DATETIME_PARAMETER_RESOURCE}": core_api.DatetimeParameterValue(
                    date_time_value=datetime(2025, 1, 1, tzinfo=ZoneInfo("UTC"))
                ),
            },
            use_v1_accounts=False,
        )

        res = self.run_test_scenario(test_scenario)
        str_res = str(res)

        self.assertIn('created parameter "SOME_ACCOUNT_PARAMETER_RESOURCE"', str_res)
        self.assertIn('created parameter "SOME_ENUMERATION_PARAMETER_RESOURCE"', str_res)
        self.assertIn('created parameter "SOME_DECIMAL_PARAMETER_RESOURCE"', str_res)
        self.assertIn('created parameter "SOME_STRING_PARAMETER_RESOURCE"', str_res)
        self.assertIn('created parameter "SOME_DATETIME_PARAMETER_RESOURCE"', str_res)

        self.assertIn('created account "Main account"', str_res)
        self.assertIn('converted account "Main account" to smart contract version "0"', str_res)
        self.assertIn('closed account "Main account"', str_res)

    def test_v2_expected_parameters_global_create_and_update(self):
        # Create and update globally owned parameters
        self.smart_contract_path_to_content = self.smart_contract_path_to_content[
            self.CONTRACT_FILE_PATH
        ]
        start = datetime(year=2023, month=12, day=31, hour=23, tzinfo=ZoneInfo("UTC"))
        end = start + relativedelta(days=2)

        globally_owned_parameter_values: dict[str, core_api.ParameterValue] = {
            "SOME_ACCOUNT_PARAMETER_RESOURCE": core_api.AccountIdParameterValue(
                account_id_value="1"
            ),
            "SOME_ENUMERATION_PARAMETER_RESOURCE": core_api.EnumerationParameterValue(
                enumeration_value="red"
            ),
            "SOME_DECIMAL_PARAMETER_RESOURCE": core_api.DecimalParameterValue(
                decimal_value=Decimal("1")
            ),
            "SOME_STRING_PARAMETER_RESOURCE": core_api.StringParameterValue(string_value="123"),
            "SOME_DATETIME_PARAMETER_RESOURCE": core_api.DatetimeParameterValue(
                date_time_value=datetime(2025, 1, 1, tzinfo=ZoneInfo("UTC"))
            ),
        }

        # Define the parameter_value_ids beforehand so they can be used.
        globally_owned_parameter_value_mapping = create_parameter_resource_mapping(
            globally_owned_parameter_values
        )

        string_parameter_value_id = globally_owned_parameter_value_mapping[
            "SOME_STRING_PARAMETER_RESOURCE"
        ][1]

        new_parameter_value = sim.UpdateParameterValue(
            parameter_value=core_api.UpdateParameterValueV1ParameterValue(
                id=string_parameter_value_id,
                effective_to_timestamp=start + relativedelta(seconds=5),
                is_cancelled=False,
            ),
            update_mask=core_api.UpdateMask(paths=["effective_to_timestamp"]),
        )

        sub_tests = [
            SubTest(
                description="Update parameter",
                events=[
                    update_parameter_value(
                        timestamp=start + relativedelta(seconds=2),
                        update_parameter_value=new_parameter_value,
                    )
                ],
            )
        ]

        test_scenario = self.get_simulation_test_scenario(
            parameters=self.parameters,
            start=start,
            end=end,
            internal_accounts={"1": ASSET},
            sub_tests=sub_tests,
            parameter_values={},
            globally_owned_parameter_values=globally_owned_parameter_value_mapping,
            use_v1_accounts=False,
        )
        res = self.run_test_scenario(test_scenario)
        str_res = str(res)

        # 1. Assert that all the parameters are created
        self.assertIn('created parameter "SOME_ACCOUNT_PARAMETER_RESOURCE"', str_res)
        self.assertIn('created parameter "SOME_ENUMERATION_PARAMETER_RESOURCE"', str_res)
        self.assertIn('created parameter "SOME_DECIMAL_PARAMETER_RESOURCE"', str_res)
        self.assertIn('created parameter "SOME_STRING_PARAMETER_RESOURCE"', str_res)
        self.assertIn('created parameter "SOME_DATETIME_PARAMETER_RESOURCE"', str_res)

        # 2. Assert that all parameter values were created and owned globally
        self.assertIn(
            "created value \\'date_time_value:{seconds:1735689600}\\' owned globally for parameter "
            '"SOME_DATETIME_PARAMETER_RESOURCE"',
            str_res,
        )
        self.assertIn(
            "created value \\'string_value:\"123\"\\' owned globally for parameter "
            '"SOME_STRING_PARAMETER_RESOURCE"',
            str_res,
        )
        self.assertIn(
            "created value \\'decimal_value:\"1\"\\' owned globally for parameter "
            '"SOME_DECIMAL_PARAMETER_RESOURCE"',
            str_res,
        )
        self.assertIn(
            "created value \\'enumeration_value:\"red\"\\' owned globally for parameter "
            '"SOME_ENUMERATION_PARAMETER_RESOURCE"',
            str_res,
        )
        self.assertIn(
            "created value \\'account_id_value:\"1\"\\' owned globally for parameter "
            '"SOME_ACCOUNT_PARAMETER_RESOURCE"',
            str_res,
        )

        # 3. Create an account that uses these parameters and update the parameter
        self.assertIn('created account "Main account"', str_res)

        expected_log = (
            f'updated parameter value "{string_parameter_value_id}" '
            f'for parameter "SOME_STRING_PARAMETER_RESOURCE" with Global owner "global"'
        )
        self.assertIn(expected_log, str_res)

    def test_v2_expected_parameters_mixed_create_and_update_with_clu_syntax(self):
        # Create and update global and account parameters
        self.smart_contract_path_to_content = self.smart_contract_path_to_content[
            self.CONTRACT_FILE_PATH
        ]
        start = datetime(year=2023, month=12, day=31, hour=23, tzinfo=ZoneInfo("UTC"))
        end = start + relativedelta(days=2)

        parameter_values: dict[str, core_api.ParameterValue] = {
            "&{SOME_ACCOUNT_PARAMETER_RESOURCE}": core_api.AccountIdParameterValue(
                account_id_value="1"
            ),
            "SOME_ENUMERATION_PARAMETER_RESOURCE": core_api.EnumerationParameterValue(
                enumeration_value="red"
            ),
        }

        globally_owned_parameter_values: dict[str, core_api.ParameterValue] = {
            "&{SOME_DECIMAL_PARAMETER_RESOURCE}": core_api.DecimalParameterValue(
                decimal_value=Decimal("1")
            ),
            "SOME_STRING_PARAMETER_RESOURCE": core_api.StringParameterValue(string_value="123"),
            "SOME_DATETIME_PARAMETER_RESOURCE": core_api.DatetimeParameterValue(
                date_time_value=datetime(2025, 1, 1, tzinfo=ZoneInfo("UTC"))
            ),
        }

        # Define the parameter_value_ids beforehand so they can be used.
        globally_owned_parameter_value_mapping = create_parameter_resource_mapping(
            globally_owned_parameter_values
        )

        string_parameter_value_id = globally_owned_parameter_value_mapping[
            "SOME_STRING_PARAMETER_RESOURCE"
        ][1]

        new_parameter_value = sim.UpdateParameterValue(
            parameter_value=core_api.UpdateParameterValueV1ParameterValue(
                id=string_parameter_value_id,
                effective_to_timestamp=start + relativedelta(seconds=5),
                is_cancelled=False,
            ),
            update_mask=core_api.UpdateMask(paths=["effective_to_timestamp"]),
        )

        sub_tests = [
            SubTest(
                description="Update parameter",
                events=[
                    update_parameter_value(
                        timestamp=start + relativedelta(seconds=2),
                        update_parameter_value=new_parameter_value,
                    )
                ],
            )
        ]

        test_scenario = self.get_simulation_test_scenario(
            parameters=self.parameters,
            start=start,
            end=end,
            internal_accounts={"1": ASSET},
            sub_tests=sub_tests,
            parameter_values=parameter_values,
            globally_owned_parameter_values=globally_owned_parameter_value_mapping,
            use_v1_accounts=False,
        )
        res = self.run_test_scenario(test_scenario)
        str_res = str(res)

        # 1. Assert that all the parameters are created
        self.assertIn('created parameter "SOME_ACCOUNT_PARAMETER_RESOURCE"', str_res)
        self.assertIn('created parameter "SOME_ENUMERATION_PARAMETER_RESOURCE"', str_res)
        self.assertIn('created parameter "SOME_DECIMAL_PARAMETER_RESOURCE"', str_res)
        self.assertIn('created parameter "SOME_STRING_PARAMETER_RESOURCE"', str_res)
        self.assertIn('created parameter "SOME_DATETIME_PARAMETER_RESOURCE"', str_res)

        # 2. Assert that all globally owned parameter values are created
        self.assertIn(
            "created value \\'date_time_value:{seconds:1735689600}\\' owned globally for parameter "
            '"SOME_DATETIME_PARAMETER_RESOURCE"',
            str_res,
        )
        self.assertIn(
            "created value \\'string_value:\"123\"\\' owned globally for parameter "
            '"SOME_STRING_PARAMETER_RESOURCE"',
            str_res,
        )
        self.assertIn(
            "created value \\'decimal_value:\"1\"\\' owned globally for parameter "
            '"SOME_DECIMAL_PARAMETER_RESOURCE"',
            str_res,
        )

        # 3. Create an account that uses these parameters and update the parameter
        self.assertIn('created account "Main account"', str_res)

        expected_log = (
            f'updated parameter value "{string_parameter_value_id}" '
            f'for parameter "SOME_STRING_PARAMETER_RESOURCE" with Global owner "global"'
        )
        self.assertIn(expected_log, str_res)


class TestPostingInstructionBatchCreatedEvents(SimulationTestCase):
    account_id_base = f"{MAIN_ACCOUNT} "
    internal_accounts = {"DEFAULT_INTERNAL_ACCOUNT": "LIABILITY"}

    @classmethod
    def setUpClass(cls):
        cls.contract_filepaths = [
            POSTING_REJECTION_SUPERVISEE_CONTRACT_FILE_PATH,
            POSTING_REJECTION_SUPERVISOR_CONTRACT_FILE_PATH,
        ]
        cls.DEFAULT_SUPERVISEE_VERSION_IDS = {
            "supervisee": "1000",
        }

        super().setUpClass()

    def get_default_supervisor_config(self):
        supervisee_config = ContractConfig(
            template_params={},
            account_configs=[
                AccountConfig(
                    instance_params={},
                    account_id_base=self.account_id_base,
                    number_of_accounts=1,
                )
            ],
            contract_content=self.smart_contract_path_to_content[
                POSTING_REJECTION_SUPERVISEE_CONTRACT_FILE_PATH
            ],
            clu_resource_id="supervisee",
            smart_contract_version_id="1000",
        )

        supervisor_config = SupervisorConfig(
            supervisor_contract=self.smart_contract_path_to_content[
                POSTING_REJECTION_SUPERVISOR_CONTRACT_FILE_PATH
            ],
            supervisee_contracts=[supervisee_config],
            supervisor_contract_version_id="supervisor version 1",
            plan_id="1",
        )

        return supervisor_config

    @skipForVaultVersionLessThan(
        Version("5.7.0"),
        "PostingInstructionBatchCreatedEvents are only supported in Vault Core 5.7+",
    )
    def test_expected_contract_violation_with_plan_id(self):
        start = datetime(year=2024, month=1, day=1, tzinfo=ZoneInfo("UTC"))
        rejected_datetime = start + relativedelta(seconds=1)
        accepted_datetime = start + relativedelta(seconds=2)
        end = accepted_datetime + relativedelta(seconds=1)

        sub_tests = [
            SubTest(
                description="Check posting rejection against plan id",
                events=[
                    create_outbound_hard_settlement_instruction(
                        amount="1000",
                        event_datetime=rejected_datetime,
                        target_account_id=f"{self.account_id_base}0",
                        internal_account_id="DEFAULT_INTERNAL_ACCOUNT",
                        denomination="GBP",
                    )
                ],
                expected_contract_violations={
                    rejected_datetime: [
                        ExpectedContractViolation(
                            contract_violation=core_api.ContractViolation(
                                account_id="",
                                plan_id="1",
                                reason="supervisor rejection",
                                type=core_api.ContractViolationType.TC_BREACH,
                                violation_type=core_api.ContractExecutionViolationType.TC_BREACH,
                            )
                        )
                    ],
                },
            ),
            SubTest(
                description="Accept posting with force_override set to true",
                events=[
                    create_outbound_hard_settlement_instruction(
                        amount="1000",
                        event_datetime=accepted_datetime,
                        target_account_id=f"{self.account_id_base}0",
                        internal_account_id="DEFAULT_INTERNAL_ACCOUNT",
                        denomination="GBP",
                        instruction_details={"force_override": "true"},
                    )
                ],
                expected_balances_at_ts={
                    accepted_datetime: {
                        f"{self.account_id_base}0": [
                            (BalanceDimensions(denomination="GBP"), Decimal("1000")),
                        ],
                    },
                },
            ),
        ]

        test_scenario = SimulationTestScenario(
            sub_tests=sub_tests,
            start=start,
            end=end,
            supervisor_config=self.get_default_supervisor_config(),
            internal_accounts=self.internal_accounts,
        )

        self.run_test_scenario(test_scenario)

    @skipForVaultVersionLessThan(
        Version("5.7.0"),
        "PostingInstructionBatchCreatedEvents are only supported in Vault Core 5.7+",
    )
    def test_expected_contract_rejection_with_account_id(self):
        start = datetime(year=2024, month=1, day=1, tzinfo=ZoneInfo("UTC"))
        rejected_datetime = start + relativedelta(seconds=1)
        accepted_datetime = start + relativedelta(seconds=2)
        end = accepted_datetime + relativedelta(seconds=1)

        sub_tests = [
            SubTest(
                description="Check posting rejection against account id",
                events=[
                    create_outbound_hard_settlement_instruction(
                        amount="1000",
                        event_datetime=rejected_datetime,
                        target_account_id=self.account_id_base,
                        internal_account_id="DEFAULT_INTERNAL_ACCOUNT",
                        denomination="GBP",
                    )
                ],
                expected_contract_violations={
                    rejected_datetime: [
                        ExpectedContractViolation(
                            contract_violation=core_api.ContractViolation(
                                account_id=self.account_id_base,
                                reason="supervisee rejection",
                                type=core_api.ContractViolationType.TC_BREACH,
                                violation_type=core_api.ContractExecutionViolationType.TC_BREACH,
                            )
                        )
                    ],
                },
            ),
            SubTest(
                description="Accept posting with force_override set to true",
                events=[
                    create_outbound_hard_settlement_instruction(
                        amount="1000",
                        event_datetime=accepted_datetime,
                        target_account_id=self.account_id_base,
                        internal_account_id="DEFAULT_INTERNAL_ACCOUNT",
                        denomination="GBP",
                        instruction_details={"force_override": "true"},
                    )
                ],
                expected_balances_at_ts={
                    accepted_datetime: {
                        self.account_id_base: [
                            (BalanceDimensions(denomination="GBP"), Decimal("1000")),
                        ],
                    },
                },
            ),
        ]

        contract_config = ContractConfig(
            template_params={},
            account_configs=[
                AccountConfig(
                    instance_params={},
                    account_id_base=self.account_id_base,
                    number_of_accounts=1,
                )
            ],
            contract_content=self.smart_contract_path_to_content[
                POSTING_REJECTION_SUPERVISEE_CONTRACT_FILE_PATH
            ],
            clu_resource_id="supervisee",
            smart_contract_version_id="1000",
        )
        test_scenario = SimulationTestScenario(
            start=start,
            end=end,
            sub_tests=sub_tests,
            contract_config=contract_config,
            internal_accounts=self.internal_accounts,
        )

        self.run_test_scenario(test_scenario)

    @skipForVaultVersionLessThan(
        Version("5.7.0"),
        "PostingInstructionBatchCreatedEvents are only supported in Vault Core 5.7+",
    )
    def test_expected_posting_rejection(self):
        start = datetime(year=2024, month=1, day=1, tzinfo=ZoneInfo("UTC"))
        accepted_datetime = start + relativedelta(seconds=1)
        rejected_datetime = start + relativedelta(seconds=2)
        end = accepted_datetime + relativedelta(seconds=1)

        sub_tests = [
            SubTest(
                description="Duplicate client transaction ID",
                events=[
                    create_outbound_hard_settlement_instruction(
                        amount="1000",
                        event_datetime=accepted_datetime,
                        target_account_id=self.account_id_base,
                        internal_account_id="DEFAULT_INTERNAL_ACCOUNT",
                        denomination="GBP",
                        instruction_details={"force_override": "true"},
                        client_transaction_id="duplicated ID",
                    ),
                    create_outbound_hard_settlement_instruction(
                        amount="1000",
                        event_datetime=rejected_datetime,
                        target_account_id=self.account_id_base,
                        internal_account_id="DEFAULT_INTERNAL_ACCOUNT",
                        instruction_details={"force_override": "true"},
                        denomination="GBP",
                        client_transaction_id="duplicated ID",
                    ),
                ],
                expected_posting_violations={
                    rejected_datetime: [
                        ExpectedPostingViolation(
                            posting_violation=core_api.PostingViolation(
                                type=core_api.PostingViolationType.CLIENT_TRANSACTION_ALREADY_EXISTS
                            )
                        )
                    ],
                },
            ),
        ]

        contract_config = ContractConfig(
            template_params={},
            account_configs=[
                AccountConfig(
                    instance_params={},
                    account_id_base=self.account_id_base,
                    number_of_accounts=1,
                )
            ],
            contract_content=self.smart_contract_path_to_content[
                POSTING_REJECTION_SUPERVISEE_CONTRACT_FILE_PATH
            ],
            clu_resource_id="supervisee",
            smart_contract_version_id="1000",
        )
        test_scenario = SimulationTestScenario(
            start=start,
            end=end,
            sub_tests=sub_tests,
            contract_config=contract_config,
            internal_accounts=self.internal_accounts,
        )

        self.run_test_scenario(test_scenario)

    @skipForVaultVersionLessThan(
        Version("5.7.0"),
        "PostingInstructionBatchCreatedEvents are only supported in Vault Core 5.7+",
    )
    def test_expected_account_rejection(self):
        start = datetime(year=2024, month=1, day=1, tzinfo=ZoneInfo("UTC"))
        accepted_datetime = start + relativedelta(seconds=1)
        rejected_datetime = start + relativedelta(seconds=2)
        end = accepted_datetime + relativedelta(seconds=1)

        sub_tests = [
            SubTest(
                description="Account ID does not exist",
                events=[
                    create_outbound_hard_settlement_instruction(
                        amount="1000",
                        event_datetime=rejected_datetime,
                        target_account_id="Invalid account ID",
                        internal_account_id="DEFAULT_INTERNAL_ACCOUNT",
                        denomination="GBP",
                        client_transaction_id="duplicated ID",
                    ),
                ],
                expected_account_violations={
                    rejected_datetime: [
                        ExpectedAccountViolation(
                            account_violation=core_api.AccountViolation(
                                account_id="Invalid account ID",
                                type=core_api.AccountViolationType.ACCOUNT_NOT_PRESENT,
                            )
                        )
                    ],
                },
            ),
        ]

        contract_config = ContractConfig(
            template_params={},
            account_configs=[
                AccountConfig(
                    instance_params={},
                    account_id_base=self.account_id_base,
                    number_of_accounts=1,
                )
            ],
            contract_content=self.smart_contract_path_to_content[
                POSTING_REJECTION_SUPERVISEE_CONTRACT_FILE_PATH
            ],
            clu_resource_id="supervisee",
            smart_contract_version_id="1000",
        )
        test_scenario = SimulationTestScenario(
            start=start,
            end=end,
            sub_tests=sub_tests,
            contract_config=contract_config,
            internal_accounts=self.internal_accounts,
        )

        self.run_test_scenario(test_scenario)


class TestExpectedAccountAttributeValues(SimulationTestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract_filepaths = [
            ACCOUNT_ATTRIBUTE_VALUE_CONTRACT_FILE_PATH,
        ]

        super().setUpClass()

    def test_account_attribute_values(self):
        start = datetime(year=2024, month=1, day=1, tzinfo=UTC)
        account_attribute_value_request_datetime = start + relativedelta(seconds=1)
        end = start + relativedelta(seconds=3)

        sub_tests = [
            SubTest(
                description="Check string, decimal, and datetime account attribute values",
                events=[
                    list_account_attribute_values(
                        timestamp=account_attribute_value_request_datetime,
                        list_account_attribute_values=sim.ListAccountAttributeValues(
                            account_ids=[MAIN_ACCOUNT],
                            attribute_names=[
                                account_attribute_value_contract.STRING_ATTRIBUTE_NAME,
                                account_attribute_value_contract.DECIMAL_ATTRIBUTE_NAME,
                                account_attribute_value_contract.DATE_TIME_ATTRIBUTE_NAME,
                            ],
                            effective_timestamps=[account_attribute_value_request_datetime],
                        ),
                    )
                ],
                expected_account_attribute_values=[
                    ExpectedAccountAttributeValue(
                        account_id=MAIN_ACCOUNT,
                        attribute_name=account_attribute_value_contract.STRING_ATTRIBUTE_NAME,
                        effective_timestamp=account_attribute_value_request_datetime,
                        value=core_api.AttributeValue(
                            string_value=core_api.AttributeStringValue(
                                value="string_attribute_value"
                            )
                        ),
                    ),
                    ExpectedAccountAttributeValue(
                        account_id=MAIN_ACCOUNT,
                        attribute_name=account_attribute_value_contract.DECIMAL_ATTRIBUTE_NAME,
                        effective_timestamp=account_attribute_value_request_datetime,
                        value=core_api.AttributeValue(
                            decimal_value=core_api.AttributeDecimalValue(value=Decimal("1234"))
                        ),
                    ),
                    ExpectedAccountAttributeValue(
                        account_id=MAIN_ACCOUNT,
                        attribute_name=account_attribute_value_contract.DATE_TIME_ATTRIBUTE_NAME,
                        effective_timestamp=account_attribute_value_request_datetime,
                        value=core_api.AttributeValue(
                            date_time_value=core_api.AttributeDateTimeValue(
                                value=datetime(2025, 2, 2, tzinfo=ZoneInfo("UTC"))
                            )
                        ),
                    ),
                ],
            ),
        ]

        contract_config = ContractConfig(
            contract_content=self.smart_contract_path_to_content[
                ACCOUNT_ATTRIBUTE_VALUE_CONTRACT_FILE_PATH
            ],
            template_params={},
            account_configs=[AccountConfig()],
        )
        test_scenario = SimulationTestScenario(
            sub_tests=sub_tests,
            start=start,
            end=end,
            contract_config=contract_config,
            use_v1_accounts=False,
        )
        self.run_test_scenario(test_scenario)


class TestGetInflightBalances(SimulationTestCase):
    account_id_base = MAIN_ACCOUNT
    internal_account_1 = "1"
    internal_account_2 = "2"

    default_internal_accounts = {
        internal_account_1: "LIABILITY",
        internal_account_2: "LIABILITY",
    }
    default_balance_dimension = BalanceDimensions(denomination="GBP")

    contract_filepaths = [
        "inception_sdk/test_framework/contracts/simulation/test/mock_product/internal_accounts_v2_balances_contract.py"  # noqa: E501
    ]

    def get_simulation_test_scenario(
        self,
        start,
        end,
        sub_tests,
        internal_accounts=None,
        use_v1_accounts=False,
    ):
        contract_config = ContractConfig(
            contract_content=self.smart_contract_path_to_content[self.contract_filepaths[0]],
            template_params={},
            account_configs=[
                AccountConfig(
                    account_id_base=self.account_id_base,
                )
            ],
        )

        return SimulationTestScenario(
            start=start,
            end=end,
            sub_tests=sub_tests,
            contract_config=contract_config,
            internal_accounts=internal_accounts or self.default_internal_accounts,
            use_v1_accounts=use_v1_accounts,
        )

    def test_get_inflight_balances_pib_and_pi_timestamps(self):
        start = datetime(year=2025, month=6, day=14, hour=10, tzinfo=ZoneInfo("UTC"))
        end = start + relativedelta(seconds=3)

        pib_timestamp = start + relativedelta(seconds=1)
        pi_timestamp = start + relativedelta(seconds=2)

        sub_tests = [
            SubTest(
                description="PIBs with PIB-level timestamp and PI-level timestamp",
                events=[
                    # PIB-level timestamp
                    create_inbound_hard_settlement_instruction(
                        amount="10",
                        target_account_id=self.account_id_base,
                        internal_account_id=self.internal_account_1,
                        denomination="GBP",
                        event_datetime=pib_timestamp,
                        value_timestamp=pib_timestamp,
                    ),
                    # PI-level timestamp
                    create_inbound_hard_settlement_posting_instruction_event(
                        amount="20",
                        target_account_id=self.account_id_base,
                        internal_account_id=self.internal_account_1,
                        denomination="GBP",
                        event_datetime=pi_timestamp,
                        value_timestamp=pi_timestamp,
                    ),
                ],
                expected_balances_at_ts={
                    # Initial balance from activation: -100
                    # After PIB (10): -110
                    # After PI (20): -130
                    pib_timestamp: {
                        self.internal_account_1: [
                            (self.default_balance_dimension, Decimal("-110"))
                        ],
                        self.internal_account_2: [(self.default_balance_dimension, Decimal("50"))],
                    },
                    pi_timestamp: {
                        self.internal_account_1: [
                            (self.default_balance_dimension, Decimal("-130"))
                        ],
                        self.internal_account_2: [(self.default_balance_dimension, Decimal("50"))],
                    },
                },
            ),
        ]

        test_scenario = self.get_simulation_test_scenario(
            start=start,
            end=end,
            sub_tests=sub_tests,
            use_v1_accounts=False,
        )
        self.run_test_scenario(test_scenario)
