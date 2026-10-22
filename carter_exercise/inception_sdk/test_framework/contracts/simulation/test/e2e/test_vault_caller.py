# standard libs
import json
import uuid
from datetime import datetime, timedelta, timezone
from dateutil.relativedelta import relativedelta
from zoneinfo import ZoneInfo

# third party
from semantic_version import Version

# contracts api
from contracts_api import DateShape, DenominationShape, NumberShape, StringShape

# inception sdk
import inception_sdk.vault.core_api as core_api
import inception_sdk.vault.sim_api.contract_sim as contract_sim
from inception_sdk.test_framework.common.balance_helpers import BalanceDimensions
from inception_sdk.test_framework.contracts.files import (
    EMPTY_LIABILITY_CONTRACT,
    EMPTY_LIABILITY_CONTRACT_V4,
)
from inception_sdk.test_framework.contracts.simulation.data_objects.data_objects import (
    AccountConfig,
    ContractConfig,
    ContractModuleConfig,
    ExpectedAccountViolation,
    ExpectedRejection,
    ExpectedSchedule,
    ExpectedSubAccountCreateAfterAccountEvent,
    ExpectedSubAccountCreateWithAccountEvent,
    SimulationTestScenario,
    SubAccountConfig,
    SubTest,
    SupervisorConfig,
)
from inception_sdk.test_framework.contracts.simulation.helper import (
    account_to_simulate,
    create_account_instruction,
    create_account_plan_assoc_instruction,
    create_account_product_version_update_instruction,
    create_calendar,
    create_calendar_event,
    create_custom_instruction,
    create_custom_instruction_posting_instruction_event,
    create_flag_event,
    create_global_parameter_instruction,
    create_global_parameter_value_instruction,
    create_inbound_authorisation_posting_instruction_event,
    create_inbound_hard_settlement_instruction,
    create_inbound_hard_settlement_posting_instruction_event,
    create_outbound_hard_settlement_instruction,
    create_outbound_hard_settlement_posting_instruction_event,
    create_parameter_value,
    create_parameter_value_hierarchy_node,
    create_plan_instruction,
    create_settlement_posting_instruction_event,
    create_sub_account_instruction,
    create_transfer_instruction,
    create_transfer_posting_instruction_event,
    update_account_status_pending_closure,
    v2_create_account_instruction,
    v2_update_account_parameter_value_hierarchy_node_id,
    v2_update_account_status,
)
from inception_sdk.test_framework.contracts.simulation.utils import (
    SimulationTestCase,
    get_account_logs,
    get_balances,
    get_calendar_created,
    get_calendar_event_created,
    get_derived_parameters,
    get_flag_created,
    get_flag_definition_created,
    get_logs,
    get_module_link_created,
    get_num_postings,
    get_plan_assoc_created,
    skipForMissingExtension,
    skipForVaultVersionLessThan,
)
from inception_sdk.test_framework.contracts.simulation.vault_caller import VaultException

# Note: A new test config is created with sufficient permissions to access the
#  </core_api.v1.contracts.CoreAPIContracts/SimulateContracts> endpoint
basepath = "inception_sdk/test_framework/contracts/simulation/test"
contract_modules_basepath = "inception_sdk/test_framework/common/contract_modules_examples"
CONTRACT_FULL_FILE = basepath + "/mock_product/full_contract.py"
CONTRACT_FULL_UPDATED_VERSION_FILE = basepath + "/mock_product/full_contract_updated_version.py"
CONTRACT_POSTING_REJECTION = basepath + "/mock_product/expected_posting_rejection_contract.py"
CONTRACT_WITH_SHARED_FUNCTION_FILE = (
    contract_modules_basepath + "/full_contract_with_shared_function.py"
)
CHECKING_CONTRACT_FILE = basepath + "/mock_product/supervised_checking_account.py"
CHECKING_CONTRACT_WITH_MODULES_FILE = (
    basepath + "/mock_product/supervised_checking_account_with_contract_modules.py"
)
SAVINGS_CONTRACT_FILE = basepath + "/mock_product/supervised_savings_deposit_account.py"
SAVINGS_CONTRACT_WITH_MODULES_FILE = (
    basepath + "/mock_product/supervised_savings_deposit_account_with_contract_modules.py"
)
YOUTH_CONTRACT_FILE = basepath + "/mock_product/supervised_youth_account.py"
SUPERVISOR_CONTRACT_FILE = basepath + "/mock_product/supervisor_contract.py"
FLAGS_CONTRACT_FILE = basepath + "/mock_product/set_flags_contract.py"
SUB_ACCOUNT_METADATA_CONTRACT_FILE = basepath + "/mock_product/sub_account_metadata_contract.py"
POST_PARAMETER_CHANGE_HOOK_CONTRACT_FILE = (
    basepath + "/mock_product/simple_post_parameter_hook_execution.py"
)
DEFAULT_CLIENT_BATCH_ID = str(uuid.uuid4())

CONTRACT_MODULES_ALIAS_FILE_MAP_MULTIPLE = {
    "interest": contract_modules_basepath + "/contract_module.py",
    "module_2": contract_modules_basepath + "/contract_module_2.py",
}

CONTRACT_MODULES_ALIAS_FILE_MAP_SINGLE = {
    "interest": contract_modules_basepath + "/contract_module.py",
}


class ClientTest(SimulationTestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract_empty = EMPTY_LIABILITY_CONTRACT
        cls.contract_full = CONTRACT_FULL_FILE
        cls.contract_full_updated_version = CONTRACT_FULL_UPDATED_VERSION_FILE
        cls.contract_with_contract_module = CONTRACT_WITH_SHARED_FUNCTION_FILE
        cls.checking_contract = CHECKING_CONTRACT_FILE
        cls.checking_contract_with_modules = CHECKING_CONTRACT_WITH_MODULES_FILE
        cls.savings_contract_with_modules = SAVINGS_CONTRACT_WITH_MODULES_FILE
        cls.savings_contract = SAVINGS_CONTRACT_FILE
        cls.youth_contract = YOUTH_CONTRACT_FILE
        supervisor_contract = SUPERVISOR_CONTRACT_FILE
        cls.flags_contract = FLAGS_CONTRACT_FILE
        cls.contract_posting_rejection = CONTRACT_POSTING_REJECTION

        with open(supervisor_contract, encoding="utf-8") as smart_contract_file:
            cls.supervisor_contract_contents = smart_contract_file.read()

        super().setUpClass()

    def test_unchallenged_deposit(self):
        start = datetime(year=2019, month=1, day=1, tzinfo=timezone.utc)
        end = datetime(year=2019, month=1, day=2, tzinfo=timezone.utc)
        template_params = {}
        instance_params = {}

        main_account = account_to_simulate(
            timestamp=start,
            account_id="Main account",
            instance_params=instance_params,
            template_params=template_params,
            contract_file_path=self.contract_empty,
        )

        events = []

        events.append(
            create_inbound_hard_settlement_instruction(
                amount="1000",
                event_datetime=start,
                denomination="GBP",
                client_transaction_id="123456",
                instruction_details={"description": "test2"},
                batch_details={"description": "test"},
                client_batch_id="123",
            )
        )

        res = self.client.simulate_smart_contract(
            start_timestamp=start,
            end_timestamp=end,
            events=events,
            account_creation_events=[main_account],
            internal_account_ids=["1"],
        )

        self.assertEqual(get_num_postings(res), 1)

    def test_wrong_denomination_with_parameter_deposit(self):
        start = datetime(year=2019, month=1, day=1, tzinfo=timezone.utc)
        end = datetime(year=2019, month=1, day=2, tzinfo=timezone.utc)
        template_params = {
            "denomination": "GBP",
            "overdraft_limit": "0",
            "overdraft_fee": "0",
            "gross_interest_rate": "0",
        }
        instance_params = {"interest_payment_day": "1"}

        events = []

        main_account = account_to_simulate(
            timestamp=start,
            account_id="Main account",
            instance_params=instance_params,
            template_params=template_params,
            contract_file_path=self.contract_full,
        )

        events.append(
            create_inbound_hard_settlement_instruction(
                amount="1000",
                event_datetime=start,
                denomination="EUR",
                client_transaction_id="Visa",
                instruction_details={"description": "test2"},
                batch_details={"description": "test"},
                client_batch_id="123",
            )
        )

        res = self.client.simulate_smart_contract(
            start_timestamp=start,
            end_timestamp=end,
            events=events,
            account_creation_events=[main_account],
            internal_account_ids=["1"],
        )
        # No valid postings were made
        self.assertEqual(get_num_postings(res), 0)
        # The event log contains the error we expect to be raised by an invalid currency
        self.assertIn(
            (
                'account "Main account" rejected with rejection type "WrongDenomination" '
                'and reason "Transactions must be in GBP only."'
            ),
            get_account_logs(res),
        )

    def test_fee_applied_on_withdrawal(self):
        start = datetime(year=2019, month=1, day=1, tzinfo=timezone.utc)
        end = datetime(year=2019, month=1, day=2, tzinfo=timezone.utc)
        template_params = {
            "denomination": "GBP",
            "overdraft_limit": "100",
            "overdraft_fee": "20",
            "gross_interest_rate": "0",
        }
        instance_params = {"interest_payment_day": "1"}

        events = []
        main_account = account_to_simulate(
            timestamp=start,
            account_id="Main account",
            instance_params=instance_params,
            template_params=template_params,
            contract_file_path=self.contract_full,
        )

        events.append(
            create_outbound_hard_settlement_instruction(
                amount="110",
                event_datetime=start + relativedelta(hours=1),
                denomination="GBP",
                client_transaction_id="123456",
                instruction_details={"description": "test2"},
                batch_details={"description": "test"},
                client_batch_id="123",
            )
        )

        res = self.client.simulate_smart_contract(
            start_timestamp=start,
            end_timestamp=end,
            events=events,
            account_creation_events=[main_account],
            internal_account_ids=["1"],
        )
        balances = get_balances(res)["Main account"]
        self.assertEqual(balances.at(start)[BalanceDimensions()].net, 0)
        self.assertEqual(balances.latest()[BalanceDimensions()].net, -130)

    def test_supervisor_contract(self):
        # this test provides output for sample_supervisor_response
        start = datetime(year=2020, month=5, day=1, tzinfo=timezone.utc)
        end = datetime(year=2020, month=7, day=1, tzinfo=timezone.utc)

        youth_template_params = {"denomination": "USD", "zero_bal_timeout": "10"}

        youth_instance_params = {"statement_day": "1", "orphaned": "no"}

        checking_template_params = {
            "denomination": "USD",
            "maintenance_fee": "25.00",
            "internal_maintenance_fee_account": "1",
            "minimum_daily_checking_balance": "1500.00",
            "minimum_combined_balance": "5000.00",
            "minimum_monthly_deposit": "1000.00",
            "overdraft_fee": "10.00",
            "internal_overdraft_fee_account": "1",
            "overdraft_fee_accrual": "NO",
            "overdraft_buffer": "0.00",
        }
        checking_instance_params = {
            "overdraft_limit": "2000",
            "debit_card_coverage": "YES",
            "maintenance_fee_check_day": "28",
        }

        savings_instance_params = {"interest_application_day": "5"}
        savings_template_params = {
            "denomination": "USD",
            # 'gross_interest_rate': '0.149',
            "gross_interest_rate_tiers": json.dumps(
                {"high": "0.15", "medium": "0.10", "low": "0.01", "DEFAULT": "0.149"}
            ),
            "minimum_deposit": "0.01",
            "maximum_daily_deposit": "1000",
            "minimum_withdrawal": "0.01",
            "maximum_daily_withdrawal": "1000",
            "maximum_balance": "10000",
            "monthly_transaction_hard_limit": "6",
            "monthly_transaction_soft_limit": "5",
            "monthly_transaction_notification_limit": "4",
            "monthly_transaction_charge": "15",
            "promotion_rate": "0",
            "check_hold_percentage_tiers": json.dumps(
                {
                    "customer_tier_high": "0.40",
                    "customer_tier_medium": "0.50",
                    "customer_tier_low": "0.60",
                    "DEFAULT": "0.60",
                }
            ),
        }

        events = []

        checking_account = account_to_simulate(
            timestamp=start,
            account_id="Checking Account",
            # IDs need to align with supervisor, these can't be autogenerated
            contract_version_id="1",
            instance_params=checking_instance_params,
            template_params=checking_template_params,
            contract_file_path=self.checking_contract,
        )
        savings_account = account_to_simulate(
            timestamp=start,
            account_id="Savings Account",
            # IDs need to align with supervisor, these can't be autogenerated
            contract_version_id="2",
            instance_params=savings_instance_params,
            template_params=savings_template_params,
            contract_file_path=self.savings_contract,
        )
        youth_account = account_to_simulate(
            timestamp=start,
            account_id="Youth Account",
            # IDs need to align with supervisor, these can't be autogenerated
            contract_version_id="3",
            instance_params=youth_instance_params,
            template_params=youth_template_params,
            contract_file_path=self.youth_contract,
        )

        # To see balances on both checking and saving account
        events.append(
            create_inbound_hard_settlement_instruction(
                "900",
                start + timedelta(days=10),
                denomination="USD",
                target_account_id="Savings Account",
                client_transaction_id="123456",
                instruction_details={"description": "test2"},
                batch_details={"description": "test"},
                client_batch_id="123",
            )
        )

        # Create plan
        events.append(
            create_plan_instruction(
                timestamp=start + timedelta(days=11),
                plan_id="1",
                supervisor_contract_version_id="116",
            )
        )

        # Create plan assoc
        events.append(
            create_account_plan_assoc_instruction(
                timestamp=start + timedelta(days=11),
                assoc_id="Supervised checking account",
                account_id="Checking Account",
                plan_id="1",
            )
        )

        events.append(
            create_account_plan_assoc_instruction(
                timestamp=start + timedelta(days=11),
                assoc_id="Supervised savings account",
                account_id="Savings Account",
                plan_id="1",
            )
        )

        res = self.client.simulate_smart_contract(
            supervisor_contract_code=self.supervisor_contract_contents,
            supervisee_version_id_mapping={
                "checking": "1",
                "savings": "2",
                "youth": "3",
            },
            supervisor_contract_version_id="116",
            start_timestamp=start,
            end_timestamp=end,
            events=events,
            account_creation_events=[savings_account, checking_account, youth_account],
            internal_account_ids=["1"],
        )

        self.assertEqual(get_num_postings(res, "Savings Account"), 2)
        self.assertEqual(get_num_postings(res, "Checking Account"), 2)
        self.assertEqual(get_num_postings(res, "Main account"), 0)
        self.assertEqual(get_num_postings(res, "1"), 4)

    def test_supervisor_contract_no_mapping(self):
        # this test checks validation for supervisor tests with missing mappings
        start = datetime(year=2020, month=5, day=1, tzinfo=timezone.utc)
        end = datetime(year=2020, month=7, day=1, tzinfo=timezone.utc)
        with self.assertRaises(ValueError) as ctx:
            self.client.simulate_smart_contract(
                supervisor_contract_code=self.supervisor_contract_contents,
                supervisee_version_id_mapping=None,
                supervisor_contract_version_id="116",
                start_timestamp=start,
                end_timestamp=end,
                events=[],
            )
        self.assertEqual(
            ctx.exception.args[0],
            "supervisee_version_id_mapping missing or empty for a test using "
            "supervisor_contract_code",
        )

    def test_wrong_denomination_deposit(self):
        start = datetime(year=2019, month=1, day=1, tzinfo=timezone.utc)
        end = datetime(year=2019, month=1, day=2, tzinfo=timezone.utc)
        template_params = {
            "denomination": "GBP",
            "overdraft_limit": "0",
            "overdraft_fee": "0",
            "gross_interest_rate": "0",
        }
        instance_params = {"interest_payment_day": "1"}
        events = []

        main_account = account_to_simulate(
            timestamp=start,
            account_id="Main account",
            instance_params=instance_params,
            template_params=template_params,
            contract_file_path=self.contract_full,
        )

        events.append(
            create_inbound_hard_settlement_instruction(
                amount="1000",
                event_datetime=start,
                denomination="EUR",
                client_transaction_id="123456",
                instruction_details={"description": "test2"},
                batch_details={"description": "test"},
                client_batch_id="123",
            )
        )
        res = self.client.simulate_smart_contract(
            start_timestamp=start,
            end_timestamp=end,
            events=events,
            account_creation_events=[main_account],
            internal_account_ids=["1"],
        )

        # No valid postings were made
        self.assertEqual(get_num_postings(res), 0)
        # The event log contains the error we expect to be raised by an invalid currency
        self.assertIn(
            'account "Main account" rejected with rejection type "WrongDenomination" and reason '
            '"Transactions must be in GBP only."',
            get_account_logs(res),
        )

    def test_set_flag(self):
        start = datetime(year=2019, month=1, day=1, tzinfo=timezone.utc)
        end = datetime(year=2019, month=1, day=2, tzinfo=timezone.utc)

        main_account = account_to_simulate(
            timestamp=start,
            account_id="Main account",
            contract_file_path=self.flags_contract,
        )

        events = []
        events.append(
            create_flag_event(
                flag_definition_id="flag_value_on",
                timestamp=start,
                expiry_timestamp=end,
                account_id="Main account",
            )
        )
        events.append(
            create_flag_event(
                flag_definition_id="flag_value_off_then_on",
                timestamp=start,
                expiry_timestamp=end,
                value=core_api.FlagV1FlagValue.FLAG_VALUE_OFF,
                account_id="Main account",
            )
        )
        events.append(
            create_flag_event(
                flag_definition_id="flag_backdated",
                timestamp=start + relativedelta(hours=2),
                effective_timestamp=start + relativedelta(hours=1),
                expiry_timestamp=end,
                is_backdated=True,
                account_id="Main account",
            )
        )
        events.append(
            create_flag_event(
                flag_definition_id="flag_value_off_then_on",
                timestamp=start + relativedelta(hours=3),
                expiry_timestamp=end,
                value=core_api.FlagV1FlagValue.FLAG_VALUE_ON,
                account_id="Main account",
            )
        )
        res = self.client.simulate_smart_contract(
            start_timestamp=start,
            end_timestamp=end,
            events=events,
            account_creation_events=[main_account],
            flag_definition_ids=["flag_value_on", "flag_backdated", "flag_value_off_then_on"],
            output_account_ids=["Main account"] * 3,
            output_timestamps=[
                start,
                start + relativedelta(hours=2, minutes=30),
                start + relativedelta(hours=3, minutes=30),
            ],
        )

        # successfully create flag definition
        result_logs = get_logs(res)
        account_logs = get_account_logs(res)
        for flag_definition_id in ["flag_value_on", "flag_backdated", "flag_value_off_then_on"]:
            self.assertIn(f'created flag definition "{flag_definition_id}"', result_logs)

            flag_definition_created = get_flag_definition_created(res, flag_definition_id)
            self.assertTrue(flag_definition_created)

            # successfully create flag for main account
            self.assertIn(
                f'created flag with definition "{flag_definition_id}" for account "Main account"',
                account_logs,
            )

            flag_created = get_flag_created(res, flag_definition_id)
            self.assertTrue(flag_created)

        # validate correct flags are active at correct times
        # start -> only flag_value_on active
        derived_params = get_derived_parameters(res)["Main account"].at(start)
        self.assertEqual(derived_params["flag_value_on_parameter"], "True")
        self.assertEqual(derived_params["flag_backdated_parameter"], "False")
        self.assertEqual(derived_params["flag_value_off_then_on_parameter"], "False")

        # start + 2h30min -> flag_value_on and flag_backdated active
        derived_params = get_derived_parameters(res)["Main account"].at(
            start + relativedelta(hours=2, minutes=30)
        )
        self.assertEqual(derived_params["flag_value_on_parameter"], "True")
        self.assertEqual(derived_params["flag_backdated_parameter"], "True")
        self.assertEqual(derived_params["flag_value_off_then_on_parameter"], "False")

        # start + 3h30min -> all flags active
        derived_params = get_derived_parameters(res)["Main account"].at(
            start + relativedelta(hours=3, minutes=30)
        )
        self.assertEqual(derived_params["flag_value_on_parameter"], "True")
        self.assertEqual(derived_params["flag_backdated_parameter"], "True")
        self.assertEqual(derived_params["flag_value_off_then_on_parameter"], "True")

    def test_single_response(self):
        start = datetime(year=2019, month=1, day=1, tzinfo=timezone.utc)
        end = datetime(year=2019, month=1, day=2, tzinfo=timezone.utc)
        events = []

        # simulate_smart_contracts already has 1 event defined by default
        res = self.client.simulate_smart_contract(
            start_timestamp=start,
            end_timestamp=end,
            events=events,
            internal_account_ids=["1"],
        )

        self.assertEqual(len(res), 1)

        logs = get_logs(res)
        self.assertIn('created account "1"', logs)

    def test_large_response(self):
        # this test provides output for sample_simulator_response
        start = datetime(year=2019, month=1, day=1, tzinfo=timezone.utc)
        end = datetime(year=2019, month=3, day=2, tzinfo=timezone.utc)
        template_params = {
            "denomination": "GBP",
            "overdraft_limit": "100",
            "overdraft_fee": "20",
            "gross_interest_rate": "0",
        }
        instance_params = {"interest_payment_day": "1"}

        main_account = account_to_simulate(
            timestamp=start,
            account_id="Main account",
            instance_params=instance_params,
            template_params=template_params,
            contract_file_path=self.contract_full,
        )

        events = []

        events.append(
            create_outbound_hard_settlement_instruction(
                amount="110",
                event_datetime=start,
                denomination="GBP",
                client_transaction_id="123456",
                instruction_details={"description": "test2"},
                batch_details={"description": "test"},
                client_batch_id="123",
            )
        )

        events.append(
            create_flag_event(
                flag_definition_id="debug_flag",
                timestamp=start,
                expiry_timestamp=start + timedelta(days=5),
                account_id="Main account",
            )
        )

        events.append(
            create_inbound_hard_settlement_instruction(
                amount="1000",
                event_datetime=start + timedelta(days=10),
                denomination="GBP",
                client_transaction_id="Visa2",
                instruction_details={"description": "test2"},
                batch_details={"description": "test"},
                client_batch_id="1232",
            )
        )

        events.append(
            create_inbound_hard_settlement_instruction(
                amount="350",
                event_datetime=start + timedelta(days=20),
                denomination="EUR",
                client_transaction_id="Visa3",
                instruction_details={"description": "test2"},
                batch_details={"description": "test"},
                client_batch_id="1233",
            )
        )

        events.append(
            create_inbound_hard_settlement_instruction(
                amount="160",
                event_datetime=start + timedelta(days=30),
                denomination="GBP",
                client_transaction_id="Visa4",
                instruction_details={"description": "test2"},
                batch_details={"description": "test"},
                client_batch_id="1234",
            )
        )

        events.append(
            create_inbound_hard_settlement_instruction(
                amount="100",
                event_datetime=start + timedelta(days=30),
                denomination="GBP",
                client_transaction_id="Visa5",
                instruction_details={"description": "test2"},
                batch_details={"description": "test"},
                client_batch_id="1235",
            )
        )

        res = self.client.simulate_smart_contract(
            start_timestamp=start,
            end_timestamp=end,
            events=events,
            account_creation_events=[main_account],
            internal_account_ids=["1"],
            flag_definition_ids=["debug_flag"],
        )

        balances = get_balances(res)["Main account"]
        self.assertEqual(balances.at(start)[BalanceDimensions()].net, -130)
        self.assertEqual(balances.latest()[BalanceDimensions()].net, 1130)

    def test_violation_responses(self):
        # this test provides output for sample_simulator_response_violations
        start = datetime(year=2019, month=1, day=1, tzinfo=timezone.utc)
        end = datetime(year=2019, month=1, day=31, tzinfo=timezone.utc)

        main_account = account_to_simulate(
            timestamp=start,
            account_id="Main account",
            contract_file_path=self.contract_posting_rejection,
        )

        events = []

        events.append(
            create_inbound_hard_settlement_instruction(
                amount="1",
                event_datetime=start,
                denomination="GBP",
                client_transaction_id="1",
                client_batch_id="1",
            )
        )

        # wrong denomination
        events.append(
            create_inbound_hard_settlement_instruction(
                amount="2",
                event_datetime=start + timedelta(days=1),
                denomination="USD",
                client_transaction_id="2",
                client_batch_id="2",
            )
        )

        # duplicate client transaction ID
        events.append(
            create_inbound_hard_settlement_instruction(
                amount="3",
                event_datetime=start + timedelta(days=2),
                denomination="GBP",
                client_transaction_id="1",
                client_batch_id="1",
            )
        )

        # non-existent account
        events.append(
            create_inbound_hard_settlement_instruction(
                target_account_id="invalid account ID",
                amount="4",
                event_datetime=start + timedelta(days=3),
                denomination="GBP",
                client_transaction_id="4",
                client_batch_id="4",
            )
        )

        res = self.client.simulate_smart_contract(
            start_timestamp=start,
            end_timestamp=end,
            events=events,
            account_creation_events=[main_account],
            internal_account_ids=["1"],
        )

        balances = get_balances(res)["Main account"]
        self.assertEqual(balances.at(start)[BalanceDimensions()].net, 1)
        self.assertEqual(balances.latest()[BalanceDimensions()].net, 1)

    def test_manual_event(self):
        start = datetime(year=2019, month=1, day=1, tzinfo=timezone.utc)
        end = datetime(year=2019, month=1, day=2, tzinfo=timezone.utc)

        main_account = account_to_simulate(
            timestamp=start,
            account_id="Main account",
            contract_file_path=self.contract_empty,
        )

        template_params = {
            "denomination": "GBP",
            "overdraft_limit": "100",
            "overdraft_fee": "20",
            "gross_interest_rate": "0",
        }
        instance_params = {"interest_payment_day": "1"}

        manual_account = account_to_simulate(
            timestamp=start + timedelta(minutes=5),
            account_id="Manual account",
            instance_params=instance_params,
            template_params=template_params,
            contract_file_path=self.contract_full,
            create_account=False,
        )

        events = []

        events.append(
            create_inbound_hard_settlement_instruction(
                amount="1000",
                event_datetime=start,
                denomination="GBP",
                client_transaction_id="123456",
                instruction_details={"description": "test2"},
                batch_details={"description": "test"},
                client_batch_id="123",
            )
        )

        events.append(
            create_account_instruction(
                timestamp=manual_account["timestamp"],
                account_id=manual_account["account_id"],
                product_id=manual_account["smart_contract_version_id"],
                instance_param_vals=manual_account["instance_parameters"],
            )
        )

        res = self.client.simulate_smart_contract(
            start_timestamp=start,
            end_timestamp=end,
            events=events,
            smart_contract_version_ids=[manual_account["smart_contract_version_id"]],
            templates_parameters=[manual_account["template_parameters"]],
            contract_codes=[manual_account["contract_file_contents"]],
            account_creation_events=[main_account],
            internal_account_ids=["1"],
        )

        self.assertIn('created account "Manual account"', get_account_logs(res, "Manual account"))
        self.assertEqual(get_num_postings(res), 1)

    def test_failed_response(self):
        start = datetime(year=2019, month=1, day=1, tzinfo=timezone.utc)
        end = datetime(year=2019, month=1, day=2, tzinfo=timezone.utc)

        main_account = account_to_simulate(
            timestamp=start - timedelta(minutes=1),
            account_id="Main account",
            contract_file_path=self.contract_empty,
        )

        with self.assertRaises(VaultException) as ex:
            self.client.simulate_smart_contract(
                start_timestamp=start,
                end_timestamp=end,
                events=[],
                account_creation_events=[main_account],
            )

        self.assertIn("Instructions must be after or equal to the start time", str(ex.exception))

    def test_posting_instructions(self):
        start = datetime(year=2019, month=1, day=1, tzinfo=timezone.utc)
        end = datetime(year=2019, month=1, day=2, tzinfo=timezone.utc)

        main_account = account_to_simulate(start, "Main account")

        events = [
            create_inbound_hard_settlement_instruction(
                amount="1",
                event_datetime=start + timedelta(minutes=1),
                denomination="GBP",
                client_transaction_id="IHS_POSTING",
                instruction_details={"description": "IHS"},
                batch_details={"description": "IHS_BATCH_DETAILS"},
                client_batch_id="IHS_BATCH_ID",
            ),
            create_outbound_hard_settlement_instruction(
                amount="1",
                event_datetime=start + timedelta(minutes=2),
                denomination="GBP",
                client_transaction_id="OHS_POSTING",
                instruction_details={"description": "OHS"},
                batch_details={"description": "OHS_BATCH_DETAILS"},
                client_batch_id="OHS_BATCH_ID",
            ),
            create_transfer_instruction(
                amount="2",
                creditor_target_account_id="Main account",
                debtor_target_account_id="2",
                event_datetime=start + timedelta(minutes=3),
                denomination="GBP",
                client_transaction_id="TRANSFER_POSTING",
                instruction_details={"description": "TRANSFER"},
                batch_details={"description": "TRANSFER_BATCH_DETAILS"},
                client_batch_id="TRANSFER_BATCH_ID",
            ),
            create_custom_instruction(
                amount="3",
                creditor_target_account_id="Main account",
                debtor_target_account_id="2",
                creditor_target_account_address="DEFAULT",
                debtor_target_account_address="DEFAULT",
                event_datetime=start + timedelta(minutes=4),
                denomination="GBP",
                client_transaction_id="CUSTOM_INSTRUCTION_POSTING",
                instruction_details={"description": "CUSTOM_INSTRUCTION"},
                batch_details={"description": "CUSTOM_INSTRUCTION_BATCH_DETAILS"},
                client_batch_id="CUSTOM_INSTRUCTION_BATCH_ID",
            ),
        ]

        res = self.client.simulate_smart_contract(
            start_timestamp=start,
            end_timestamp=end,
            events=events,
            internal_account_ids=["1", "2"],
            account_creation_events=[main_account],
        )

        self.assertEqual(get_num_postings(res, "Main account"), 4)
        self.assertEqual(get_num_postings(res, "2"), 2)

        balances = get_balances(res)
        main_balances = balances["Main account"]
        internal_balances = balances["2"]
        self.assertEqual(main_balances.at(start + timedelta(minutes=1))[BalanceDimensions()].net, 1)
        self.assertEqual(main_balances.at(start + timedelta(minutes=2))[BalanceDimensions()].net, 0)
        self.assertEqual(main_balances.at(start + timedelta(minutes=3))[BalanceDimensions()].net, 2)
        self.assertEqual(main_balances.at(start + timedelta(minutes=4))[BalanceDimensions()].net, 5)
        self.assertEqual(
            internal_balances.at(start + timedelta(minutes=5))[BalanceDimensions()].net,
            -5,
        )

    def test_posting_instruction_events(self):
        start = datetime(year=2019, month=1, day=1, tzinfo=timezone.utc)
        end = datetime(year=2019, month=1, day=2, tzinfo=timezone.utc)

        main_account = account_to_simulate(start, "Main account")

        events = [
            create_inbound_hard_settlement_posting_instruction_event(
                amount="1",
                event_datetime=start + timedelta(minutes=1),
                denomination="GBP",
                client_transaction_id="IHS_POSTING",
                instruction_details={"description": "IHS"},
                batch_details={"description": "IHS_BATCH_DETAILS"},
                client_batch_id="IHS_BATCH_ID",
            ),
            create_outbound_hard_settlement_posting_instruction_event(
                amount="1",
                event_datetime=start + timedelta(minutes=2),
                denomination="GBP",
                client_transaction_id="OHS_POSTING",
                instruction_details={"description": "OHS"},
                batch_details={"description": "OHS_BATCH_DETAILS"},
                client_batch_id="OHS_BATCH_ID",
            ),
            create_transfer_posting_instruction_event(
                amount="2",
                creditor_target_account_id="Main account",
                debtor_target_account_id="2",
                event_datetime=start + timedelta(minutes=3),
                denomination="GBP",
                client_transaction_id="TRANSFER_POSTING",
                instruction_details={"description": "TRANSFER"},
                batch_details={"description": "TRANSFER_BATCH_DETAILS"},
                client_batch_id="TRANSFER_BATCH_ID",
            ),
            create_custom_instruction_posting_instruction_event(
                amount="3",
                creditor_target_account_id="Main account",
                debtor_target_account_id="2",
                phase="POSTING_PHASE_COMMITTED",
                creditor_target_account_address="DEFAULT",
                debtor_target_account_address="DEFAULT",
                event_datetime=start + timedelta(minutes=4),
                denomination="GBP",
                client_transaction_id="CUSTOM_INSTRUCTION_POSTING",
                instruction_details={"description": "CUSTOM_INSTRUCTION"},
                batch_details={"description": "CUSTOM_INSTRUCTION_BATCH_DETAILS"},
                client_batch_id="CUSTOM_INSTRUCTION_BATCH_ID",
            ),
        ]

        res = self.client.simulate_smart_contract(
            start_timestamp=start,
            end_timestamp=end,
            events=events,
            internal_account_ids=["1", "2"],
            account_creation_events=[main_account],
        )

        self.assertEqual(get_num_postings(res, "Main account"), 4)
        self.assertEqual(get_num_postings(res, "2"), 2)

        balances = get_balances(res)
        main_balances = balances["Main account"]
        internal_balances = balances["2"]
        self.assertEqual(main_balances.at(start + timedelta(minutes=1))[BalanceDimensions()].net, 1)
        self.assertEqual(main_balances.at(start + timedelta(minutes=2))[BalanceDimensions()].net, 0)
        self.assertEqual(main_balances.at(start + timedelta(minutes=3))[BalanceDimensions()].net, 2)
        self.assertEqual(main_balances.at(start + timedelta(minutes=4))[BalanceDimensions()].net, 5)
        self.assertEqual(
            internal_balances.at(start + timedelta(minutes=5))[BalanceDimensions()].net,
            -5,
        )

    def test_derived_parameters(self):
        start = datetime(year=2019, month=1, day=1, tzinfo=timezone.utc)
        end = datetime(year=2019, month=1, day=2, tzinfo=timezone.utc)
        template_params = {
            "denomination": "GBP",
            "overdraft_limit": "0",
            "overdraft_fee": "0",
            "gross_interest_rate": "0",
        }
        instance_params = {"interest_payment_day": "1"}

        main_account = account_to_simulate(
            timestamp=start,
            account_id="Main account",
            instance_params=instance_params,
            template_params=template_params,
            contract_file_path=self.contract_full,
        )

        events = []

        events.append(
            create_inbound_hard_settlement_instruction(
                amount="1000",
                event_datetime=start,
                denomination="GBP",
                client_transaction_id="123456",
                instruction_details={"description": "test2"},
                batch_details={"description": "test"},
                client_batch_id="123",
            )
        )

        res = self.client.simulate_smart_contract(
            start_timestamp=start,
            end_timestamp=end,
            events=events,
            account_creation_events=[main_account],
            internal_account_ids=["1"],
            output_account_ids=["Main account"],
            output_timestamps=[start],
        )

        # Acceptance criteria:
        # Get the derived parameter
        derived_params = get_derived_parameters(res)["Main account"].at(start)
        self.assertEqual(derived_params["days_past_due"], "10")
        expected_end_date = derived_params["expected_end_date"]
        self.assertEqual(expected_end_date, "2020-12-22")

    def test_query_internal_account_balances(self):
        start = datetime(year=2019, month=1, day=1, tzinfo=timezone.utc)
        end = datetime(year=2019, month=1, day=2, tzinfo=timezone.utc)

        main_account = account_to_simulate(start, "Main account")

        events = [
            create_inbound_hard_settlement_instruction(
                amount="1",
                event_datetime=start + timedelta(minutes=1),
                denomination="GBP",
                client_transaction_id="IHS_POSTING_PART_1",
                instruction_details={"description": "IHS"},
                batch_details={"description": "IHS_BATCH_DETAILS"},
                client_batch_id="IHS_BATCH_ID_PART_1",
                internal_account_id="internal_asset_account_1",
            ),
            create_outbound_hard_settlement_instruction(
                amount="2",
                event_datetime=start + timedelta(minutes=2),
                denomination="GBP",
                client_transaction_id="OHS_POSTING_PART_1",
                instruction_details={"description": "OHS"},
                batch_details={"description": "OHS_BATCH_DETAILS"},
                client_batch_id="OHS_BATCH_ID_PART_1",
                internal_account_id="internal_asset_account_2",
            ),
            create_transfer_instruction(
                amount="3",
                creditor_target_account_id="Main account",
                debtor_target_account_id="internal_asset_account_3",
                event_datetime=start + timedelta(minutes=3),
                denomination="GBP",
                client_transaction_id="TRANSFER_POSTING_PART_1",
                instruction_details={"description": "TRANSFER"},
                batch_details={"description": "TRANSFER_BATCH_DETAILS"},
                client_batch_id="TRANSFER_BATCH_ID_PART_1",
            ),
            create_inbound_hard_settlement_instruction(
                amount="4",
                event_datetime=start + timedelta(minutes=4),
                denomination="GBP",
                client_transaction_id="IHS_POSTING_PART_2",
                instruction_details={"description": "IHS"},
                batch_details={"description": "IHS_BATCH_DETAILS"},
                client_batch_id="IHS_BATCH_ID_PART_2",
                internal_account_id="internal_liability_account_1",
            ),
            create_outbound_hard_settlement_instruction(
                amount="5",
                event_datetime=start + timedelta(minutes=5),
                denomination="GBP",
                client_transaction_id="OHS_POSTING_PART_2",
                instruction_details={"description": "OHS"},
                batch_details={"description": "OHS_BATCH_DETAILS"},
                client_batch_id="OHS_BATCH_ID_PART_2",
                internal_account_id="internal_liability_account_2",
            ),
            create_transfer_instruction(
                amount="6",
                creditor_target_account_id="Main account",
                debtor_target_account_id="internal_liability_account_3",
                event_datetime=start + timedelta(minutes=6),
                denomination="GBP",
                client_transaction_id="TRANSFER_POSTING_PART_2",
                instruction_details={"description": "TRANSFER"},
                batch_details={"description": "TRANSFER_BATCH_DETAILS"},
                client_batch_id="TRANSFER_BATCH_ID_PART_2",
            ),
        ]

        res = self.client.simulate_smart_contract(
            start_timestamp=start,
            end_timestamp=end,
            events=events,
            internal_account_ids={
                "internal_asset_account_1": "ASSET",
                "internal_asset_account_2": "ASSET",
                "internal_asset_account_3": "ASSET",
                "internal_liability_account_1": "LIABILITY",
                "internal_liability_account_2": "LIABILITY",
                "internal_liability_account_3": "LIABILITY",
            },
            account_creation_events=[main_account],
        )

        self.assertEqual(get_num_postings(res, "Main account"), 6)
        balances = get_balances(res)
        self.assertEqual(balances["internal_asset_account_1"].latest()[BalanceDimensions()].net, 1)
        self.assertEqual(balances["internal_asset_account_2"].latest()[BalanceDimensions()].net, -2)
        self.assertEqual(balances["internal_asset_account_3"].latest()[BalanceDimensions()].net, 3)
        self.assertEqual(
            balances["internal_liability_account_1"].latest()[BalanceDimensions()].net,
            -4,
        )
        self.assertEqual(
            balances["internal_liability_account_2"].latest()[BalanceDimensions()].net,
            5,
        )
        self.assertEqual(
            balances["internal_liability_account_3"].latest()[BalanceDimensions()].net,
            -6,
        )

    def test_create_calendar_and_events(self):
        start = datetime(year=2019, month=1, day=1, tzinfo=timezone.utc)
        end = datetime(year=2019, month=1, day=2, tzinfo=timezone.utc)

        main_account = account_to_simulate(
            timestamp=start,
            account_id="Main account",
            contract_file_path=self.contract_empty,
        )

        events = []
        events.extend(
            [
                create_calendar(
                    timestamp=start,
                    calendar_id="TEST_CALENDAR",
                ),
                create_calendar_event(
                    timestamp=start,
                    calendar_event_id="TEST_EVENT",
                    calendar_id="TEST_CALENDAR",
                    start_timestamp=start,
                    end_timestamp=end,
                ),
            ]
        )

        res = self.client.simulate_smart_contract(
            start_timestamp=start,
            end_timestamp=end,
            events=events,
            account_creation_events=[main_account],
        )
        result_logs = get_logs(res)
        # Successfully create calendar
        self.assertIn('created calendar with id "TEST_CALENDAR"', result_logs)
        # Successfully create calendar event
        self.assertIn('created calendar event for calendar "TEST_CALENDAR"', result_logs)

    def test_check_schedule_processed(self):
        start = datetime(year=2021, month=1, day=1, tzinfo=timezone.utc)
        end = start + timedelta(days=1, hours=5)
        template_params = {
            "denomination": "GBP",
            "overdraft_limit": "0",
            "overdraft_fee": "0",
            "gross_interest_rate": "0",
        }
        instance_params = {"interest_payment_day": "1"}

        main_account = account_to_simulate(
            timestamp=start,
            account_id="Main account",
            instance_params=instance_params,
            template_params=template_params,
            contract_file_path=self.contract_full,
        )
        events = [
            create_inbound_hard_settlement_instruction(
                event_datetime=start + timedelta(hours=1),
                target_account_id="Main account",
                amount="1000",
                denomination="USD",
            )
        ]
        res = self.client.simulate_smart_contract(
            start_timestamp=start,
            end_timestamp=end,
            events=events,
            account_creation_events=[main_account],
            internal_account_ids=["1"],
        )

        scheduled_time = datetime(year=2021, month=1, day=2, tzinfo=timezone.utc)
        event_id = "ACCRUE_INTEREST"
        account_id = "Main account"
        msg = "cannot find processed schedule with"

        expected_schedule_runs = [
            ExpectedSchedule(
                run_times=[start, scheduled_time],
                event_id=event_id,
                account_id=account_id,
                count=2,
            )
        ]
        self.check_schedule_processed(expected_schedule_runs, res)

        schedule_runs_with_wrong_time = [
            ExpectedSchedule(
                run_times=[datetime(year=2021, month=1, day=1, hour=3, tzinfo=timezone.utc)],
                event_id=event_id,
                account_id=account_id,
            )
        ]

        with self.assertRaises(AssertionError) as ex:
            self.check_schedule_processed(schedule_runs_with_wrong_time, res, msg)

        self.assertIn(
            f"{msg}: {[datetime(year=2021, month=1, day=1, hour=3, tzinfo=timezone.utc)]}",
            str(ex.exception),
        )

        false_schedule_runs = [
            # wrong account
            ExpectedSchedule(
                run_times=[scheduled_time],
                event_id=event_id,
                account_id="Wrong account",
            ),
            # wrong event
            ExpectedSchedule(
                run_times=[scheduled_time],
                event_id="LOSING_INTEREST",
                account_id=account_id,
            ),
        ]

        with self.assertRaises(AssertionError) as ex:
            self.check_schedule_processed(false_schedule_runs, res, msg)

        self.assertIn(f"{msg}: {[scheduled_time, scheduled_time]}", str(ex.exception))

    def test_check_schedule_processed_in_default_pg_tz(self):
        """
        Set the Default Processing Group Timezone (DPGTZ) and check that the schedules are created
        in that timezone.
        """
        sydney_tz = ZoneInfo("Australia/Sydney")
        # Simulation window in Sydney time: 2021-01-01 10:00 to 2021-01-03 10:00
        start = datetime(year=2021, month=1, day=1, hour=10, tzinfo=sydney_tz)
        end = datetime(year=2021, month=1, day=3, hour=10, tzinfo=sydney_tz)
        template_params = {
            "denomination": "GBP",
            "overdraft_limit": "0",
            "overdraft_fee": "0",
            "gross_interest_rate": "0",
        }
        instance_params = {"interest_payment_day": "1"}

        main_account = account_to_simulate(
            timestamp=start,
            account_id="Main account",
            instance_params=instance_params,
            template_params=template_params,
            contract_file_path=self.contract_full,
        )
        events = [
            create_inbound_hard_settlement_instruction(
                event_datetime=start + timedelta(hours=1),
                target_account_id="Main account",
                amount="1000",
                denomination="USD",
            )
        ]
        res = self.client.simulate_smart_contract(
            start_timestamp=start,
            end_timestamp=end,
            events=events,
            account_creation_events=[main_account],
            internal_account_ids=["1"],
            default_timezone=sydney_tz,
        )

        # Expected Sydney runs:
        # 1. midnight = 2021-01-02 00:00:00 Sydney = 2021-01-01 13:00:00 UTC
        # 2. midnight = 2021-01-03 00:00:00 Sydney = 2021-01-02 13:00:00 UTC

        scheduled_time_1 = datetime(year=2021, month=1, day=2, hour=0, tzinfo=sydney_tz)
        scheduled_time_2 = datetime(year=2021, month=1, day=3, hour=0, tzinfo=sydney_tz)
        event_id = "ACCRUE_INTEREST"
        account_id = "Main account"

        # check_schedule_processed expects UTC datetimes for matching against ISO strings
        expected_schedule_runs = [
            ExpectedSchedule(
                run_times=[
                    scheduled_time_1.astimezone(timezone.utc),
                    scheduled_time_2.astimezone(timezone.utc),
                ],
                event_id=event_id,
                account_id=account_id,
                count=2,
            )
        ]
        self.check_schedule_processed(expected_schedule_runs, res)

    def test_account_update_close_triggers_close_code_outstanding_balance(self):
        start = datetime(year=2019, month=1, day=1, tzinfo=timezone.utc)
        end = datetime(year=2019, month=1, day=2, tzinfo=timezone.utc)
        template_params = {
            "denomination": "GBP",
            "overdraft_limit": "0",
            "overdraft_fee": "10",
            "gross_interest_rate": "0",
        }
        instance_params = {"interest_payment_day": "1"}

        main_account = account_to_simulate(
            timestamp=start,
            account_id="Main account",
            instance_params=instance_params,
            template_params=template_params,
            contract_file_path=self.contract_full,
        )

        events = []

        events.append(
            create_outbound_hard_settlement_instruction(
                amount="110",
                event_datetime=start,
                denomination="GBP",
                client_transaction_id="123456",
                instruction_details={"description": "test2"},
                batch_details={"description": "test"},
                client_batch_id="123",
            )
        )

        events.append(
            update_account_status_pending_closure(
                timestamp=(start + timedelta(minutes=10)), account_id="Main account"
            )
        )

        with self.assertRaises(VaultException) as ex:
            self.client.simulate_smart_contract(
                start_timestamp=start,
                end_timestamp=end,
                events=events,
                account_creation_events=[main_account],
                internal_account_ids=["1"],
                debug=True,
            )

        self.assertIn("Cannot close account until account balance nets to 0", str(ex.exception))

    def test_global_parameter(self):
        start = datetime(year=2021, month=1, day=1, tzinfo=timezone.utc)
        end = datetime(year=2021, month=1, day=2, tzinfo=timezone.utc)
        template_params = {
            "denomination": "GBP",
            "overdraft_limit": "0",
            "overdraft_fee": "0",
            "gross_interest_rate": "0",
        }
        instance_params = {"interest_payment_day": "1"}

        main_account = account_to_simulate(
            timestamp=start,
            account_id="Main account",
            instance_params=instance_params,
            template_params=template_params,
            contract_file_path=self.contract_full,
        )

        events = [
            create_global_parameter_instruction(
                timestamp=start,
                global_parameter_id="global_interest_rate",
                display_name="Global yearly interest rate",
                description="Global yearly interest rate",
                number=NumberShape(),
                initial_value="1.20491",
            ),
            create_global_parameter_value_instruction(
                timestamp=start,
                global_parameter_id="global_interest_rate",
                value="1.20493",
                effective_timestamp=start + timedelta(hours=1),
            ),
            create_global_parameter_instruction(
                timestamp=start + timedelta(hours=2),
                global_parameter_id="denomination",
                display_name="Denomination",
                description="Denomination",
                denomination=DenominationShape(permitted_denominations=["GBP"]),
                initial_value="GBP",
            ),
            create_global_parameter_instruction(
                timestamp=start + timedelta(hours=3),
                global_parameter_id="example_str_parameter",
                display_name="Example str parameter",
                description="Example str parameter",
                str=StringShape(),
                initial_value="Example str",
            ),
            create_global_parameter_instruction(
                timestamp=start + timedelta(hours=4),
                global_parameter_id="example_date_parameter",
                display_name="Example date parameter",
                description="Example date parameter",
                date=DateShape(),
                initial_value=str((start + timedelta(hours=5)).date()),
            ),
        ]

        res = self.client.simulate_smart_contract(
            start_timestamp=start,
            end_timestamp=end,
            events=events,
            account_creation_events=[main_account],
        )

        result_logs = get_logs(res)
        # successfully created global parameter of type "number"
        self.assertIn('created global parameter "global_interest_rate"', result_logs)

        # successfully initiated global parameter value
        self.assertIn(
            'created value "1.20491" for global parameter "global_interest_rate"',
            result_logs,
        )

        # successfully updated global parameter value
        self.assertIn(
            'created value "1.20493" for global parameter "global_interest_rate"',
            result_logs,
        )

        # successfully created global parameter of type "denomination"
        self.assertIn('created global parameter "denomination"', result_logs)

        # successfully initiated global parameter value
        self.assertIn(
            'created value "GBP" for global parameter "denomination"',
            result_logs,
        )

        # successfully created global parameter of type "str"
        self.assertIn('created global parameter "example_str_parameter"', result_logs)

        # successfully initiated global parameter value
        self.assertIn(
            'created value "Example str" for global parameter "example_str_parameter"',
            result_logs,
        )

        # successfully created global parameter of type "date"
        self.assertIn('created global parameter "example_date_parameter"', result_logs)

        # successfully initiated global parameter value
        self.assertIn(
            'created value "2021-01-01" for global parameter "example_date_parameter"',
            result_logs,
        )

    def test_account_product_version_update_triggers_upgrade_code(self):
        start = datetime(year=2021, month=1, day=1, tzinfo=timezone.utc)
        end = datetime(year=2021, month=1, day=2, tzinfo=timezone.utc)
        template_params = {
            "denomination": "GBP",
            "overdraft_limit": "0",
            "overdraft_fee": "0",
            "gross_interest_rate": "0",
        }
        instance_params = {"interest_payment_day": "1"}

        with open(self.contract_full, encoding="utf-8") as smart_contract_file:
            contract_full_contents = smart_contract_file.read()
        with open(self.contract_full_updated_version, encoding="utf-8") as smart_contract_file:
            contract_full_updated_version_contents = smart_contract_file.read()

        events = [
            create_account_instruction(
                timestamp=start,
                account_id="Main account",
                product_id="1000",
                instance_param_vals=instance_params,
            ),
            create_account_product_version_update_instruction(
                timestamp=start + timedelta(hours=1),
                account_id="Main account",
                product_version_id="1001",
            ),
        ]
        res = self.client.simulate_smart_contract(
            contract_codes=[
                contract_full_contents,
                contract_full_updated_version_contents,
            ],
            smart_contract_version_ids=["1000", "1001"],
            start_timestamp=start,
            end_timestamp=end,
            templates_parameters=[template_params, template_params],
            events=events,
        )

        self.assertIn(
            'updated account "Main account" smart contract version to "1001"',
            get_account_logs(res),
        )

    def test_contract_module_gets_executed(self):
        start = datetime(year=2021, month=1, day=1, tzinfo=timezone.utc)
        end = datetime(year=2021, month=1, day=2, tzinfo=timezone.utc)

        template_params = {"denomination": "GBP", "interest_rate": "1"}
        internal_account_id = "1"

        main_account = account_to_simulate(
            timestamp=start,
            account_id="Main account",
            contract_file_path=self.contract_with_contract_module,
            template_params=template_params,
        )

        contract_modules = [
            ContractModuleConfig(alias, file_path)
            for (alias, file_path) in CONTRACT_MODULES_ALIAS_FILE_MAP_MULTIPLE.items()
        ]

        contract_config = ContractConfig(
            contract_file_path=self.contract_with_contract_module,
            template_params=template_params,
            smart_contract_version_id=main_account["smart_contract_version_id"],
            account_configs=[
                AccountConfig(
                    instance_params={},
                    account_id_base="Main account",
                )
            ],
            linked_contract_modules=contract_modules,
        )

        events = [
            create_inbound_hard_settlement_instruction(
                event_datetime=start + timedelta(hours=1),
                target_account_id="Main account",
                amount="1000",
                denomination="GBP",
            ),
        ]

        res = self.client.simulate_smart_contract(
            start_timestamp=start,
            end_timestamp=end,
            events=events,
            account_creation_events=[main_account],
            internal_account_ids=[internal_account_id],
            contract_config=contract_config,
        )

        balances = get_balances(res)

        # if interest gets accrued correctly, the accrued value should be
        # 1/365 = 0.003 (contract module has 3 decimals) * 1000 = 3
        # internal account dispersed 1000 at the beginning, so current value is -997
        self.assertEqual(balances[internal_account_id].latest()[BalanceDimensions()].net, -997)

        self.assertTrue(
            get_module_link_created(
                res,
                ["interest", "module_2"],
                smart_contract_version_id=main_account["smart_contract_version_id"],
            )
        )

    def test_contract_module_scenario(self):
        start = datetime(year=2021, month=1, day=1, tzinfo=timezone.utc)
        end = datetime(year=2021, month=1, day=2, tzinfo=timezone.utc)

        template_params = {"denomination": "GBP", "interest_rate": "1"}
        smart_contract_version_id = "1"
        internal_accounts = {"1": "LIABILITY"}

        contract_modules = [
            ContractModuleConfig(alias, file_path)
            for (alias, file_path) in CONTRACT_MODULES_ALIAS_FILE_MAP_MULTIPLE.items()
        ]

        contract_config = ContractConfig(
            contract_file_path=self.contract_with_contract_module,
            template_params=template_params,
            smart_contract_version_id=smart_contract_version_id,
            account_configs=[
                AccountConfig(
                    instance_params={},
                    account_id_base="Main account",
                )
            ],
            linked_contract_modules=contract_modules,
        )

        deposit_event = create_inbound_hard_settlement_instruction(
            "1000.00", start + timedelta(hours=1), denomination="GBP"
        )

        sub_tests = [
            # if interest gets accrued correctly, the accrued value should be
            # 1/365 = 0.003 (contract module has 3 decimals) * 1000 = 3
            # internal account dispersed 1000 at the beginning, so current value is -997
            SubTest(
                description="accrual check",
                events=[deposit_event],
                expected_balances_at_ts={
                    end: {"1": [(BalanceDimensions(denomination="GBP"), "-997.00")]}
                },
            )
        ]

        test_scenario = SimulationTestScenario(
            start=start,
            end=end,
            sub_tests=sub_tests,
            contract_config=contract_config,
            internal_accounts=internal_accounts,
        )
        res = self.run_test_scenario(test_scenario)

        self.assertTrue(
            get_module_link_created(
                res,
                ["interest", "module_2"],
                smart_contract_version_id="1",
            )
        )

    def test_supervisor_contract_one_supervisee_with_contract_modules(self):
        start = datetime(year=2020, month=5, day=1, tzinfo=timezone.utc)
        end = datetime(year=2020, month=7, day=1, tzinfo=timezone.utc)

        youth_template_params = {"denomination": "USD", "zero_bal_timeout": "10"}

        youth_instance_params = {"statement_day": "1", "orphaned": "no"}

        checking_template_params = {
            "denomination": "USD",
            "maintenance_fee": "25.00",
            "internal_maintenance_fee_account": "1",
            "minimum_daily_checking_balance": "1500.00",
            "minimum_combined_balance": "5000.00",
            "minimum_monthly_deposit": "1000.00",
            "overdraft_fee": "10.00",
            "internal_overdraft_fee_account": "1",
            "overdraft_fee_accrual": "NO",
            "overdraft_buffer": "0.00",
        }
        checking_instance_params = {
            "overdraft_limit": "2000",
            "debit_card_coverage": "YES",
            "maintenance_fee_check_day": "28",
        }

        savings_instance_params = {"interest_application_day": "5"}
        savings_template_params = {
            "denomination": "USD",
            # 'gross_interest_rate': '0.149',
            "gross_interest_rate_tiers": json.dumps(
                {"high": "0.15", "medium": "0.10", "low": "0.01", "DEFAULT": "0.149"}
            ),
            "minimum_deposit": "0.01",
            "maximum_daily_deposit": "1000",
            "minimum_withdrawal": "0.01",
            "maximum_daily_withdrawal": "1000",
            "maximum_balance": "10000",
            "monthly_transaction_hard_limit": "6",
            "monthly_transaction_soft_limit": "5",
            "monthly_transaction_notification_limit": "4",
            "monthly_transaction_charge": "15",
            "promotion_rate": "0",
            "check_hold_percentage_tiers": json.dumps(
                {
                    "customer_tier_high": "0.40",
                    "customer_tier_medium": "0.50",
                    "customer_tier_low": "0.60",
                    "DEFAULT": "0.60",
                }
            ),
        }

        contract_modules = [
            ContractModuleConfig(alias, file_path)
            for (alias, file_path) in CONTRACT_MODULES_ALIAS_FILE_MAP_SINGLE.items()
        ]

        ca_account_configs = [
            AccountConfig(
                account_id_base="checking ",
                instance_params=checking_instance_params,
            )
        ]
        ca_account_contract = ContractConfig(
            clu_resource_id="checking",
            contract_file_path=self.checking_contract_with_modules,
            template_params=checking_template_params,
            smart_contract_version_id="1",
            account_configs=ca_account_configs,
            linked_contract_modules=contract_modules,
        )

        sa_account_configs = [
            AccountConfig(
                account_id_base="savings ",
                instance_params=savings_instance_params,
            )
        ]
        sa_account_contract = ContractConfig(
            clu_resource_id="savings",
            contract_file_path=self.savings_contract,
            template_params=savings_template_params,
            smart_contract_version_id="2",
            account_configs=sa_account_configs,
        )

        youth_account_configs = [
            AccountConfig(
                account_id_base="youth ",
                instance_params=youth_instance_params,
            )
        ]
        youth_account_contract = ContractConfig(
            clu_resource_id="youth",
            contract_file_path=self.youth_contract,
            template_params=youth_template_params,
            smart_contract_version_id="3",
            account_configs=youth_account_configs,
        )

        supervisee_contracts = [
            ca_account_contract,
            sa_account_contract,
            youth_account_contract,
        ]
        supervisor_config = SupervisorConfig(
            supervisor_file_path=SUPERVISOR_CONTRACT_FILE,
            supervisee_contracts=supervisee_contracts,
        )

        sub_tests = [
            SubTest(
                description="inbound hard settlement to saving account",
                events=[
                    create_inbound_hard_settlement_instruction(
                        amount="900",
                        event_datetime=start + timedelta(days=10),
                        target_account_id="checking 0",
                        internal_account_id="1",
                        denomination="GBP",
                    ),
                ],
            ),
            SubTest(
                description="check balances",
                expected_balances_at_ts={
                    start
                    + timedelta(days=10, hours=1): {
                        "savings 0": [
                            (BalanceDimensions(), "0"),
                        ],
                        "checking 0": [
                            (BalanceDimensions(), "0"),
                        ],
                        "youth 0": [
                            (BalanceDimensions(), "0"),
                        ],
                    }
                },
                expected_posting_rejections=[
                    ExpectedRejection(
                        start + timedelta(days=10),
                        account_id="checking 0",
                        rejection_type="WrongDenomination",
                        rejection_reason="Cannot make transactions in given denomination; "
                        "transactions must be in USD",
                    )
                ],
            ),
        ]

        test_scenario = SimulationTestScenario(
            sub_tests=sub_tests,
            start=start,
            end=end,
            supervisor_config=supervisor_config,
            internal_accounts=["1"],
        )

        res = self.run_test_scenario(test_scenario)

        self.assertTrue(get_plan_assoc_created(res, plan_id="1", account_id="savings 0"))
        self.assertTrue(get_plan_assoc_created(res, plan_id="1", account_id="checking 0"))
        self.assertTrue(get_plan_assoc_created(res, plan_id="1", account_id="youth 0"))
        self.assertTrue(get_module_link_created(res, ["interest"], smart_contract_version_id="1"))

    def test_multiple_supervisees_on_supervisor_plan_with_contract_modules(self):
        start = datetime(year=2020, month=5, day=1, tzinfo=timezone.utc)
        end = datetime(year=2020, month=7, day=1, tzinfo=timezone.utc)

        youth_template_params = {"denomination": "USD", "zero_bal_timeout": "10"}

        youth_instance_params = {"statement_day": "1", "orphaned": "no"}

        checking_template_params = {
            "denomination": "USD",
            "maintenance_fee": "25.00",
            "internal_maintenance_fee_account": "1",
            "minimum_daily_checking_balance": "1500.00",
            "minimum_combined_balance": "5000.00",
            "minimum_monthly_deposit": "1000.00",
            "overdraft_fee": "10.00",
            "internal_overdraft_fee_account": "1",
            "overdraft_fee_accrual": "NO",
            "overdraft_buffer": "0.00",
        }
        checking_instance_params = {
            "overdraft_limit": "2000",
            "debit_card_coverage": "YES",
            "maintenance_fee_check_day": "28",
        }

        savings_instance_params = {"interest_application_day": "5"}
        savings_template_params = {
            "denomination": "USD",
            # 'gross_interest_rate': '0.149',
            "gross_interest_rate_tiers": json.dumps(
                {"high": "0.15", "medium": "0.10", "low": "0.01", "DEFAULT": "0.149"}
            ),
            "minimum_deposit": "0.01",
            "maximum_daily_deposit": "1000",
            "minimum_withdrawal": "0.01",
            "maximum_daily_withdrawal": "1000",
            "maximum_balance": "10000",
            "monthly_transaction_hard_limit": "6",
            "monthly_transaction_soft_limit": "5",
            "monthly_transaction_notification_limit": "4",
            "monthly_transaction_charge": "15",
            "promotion_rate": "0",
            "check_hold_percentage_tiers": json.dumps(
                {
                    "customer_tier_high": "0.40",
                    "customer_tier_medium": "0.50",
                    "customer_tier_low": "0.60",
                    "DEFAULT": "0.60",
                }
            ),
        }

        contract_modules_savings = [
            ContractModuleConfig(alias, file_path)
            for (alias, file_path) in CONTRACT_MODULES_ALIAS_FILE_MAP_MULTIPLE.items()
        ]
        contract_modules_checking = [
            ContractModuleConfig(alias, file_path)
            for (alias, file_path) in CONTRACT_MODULES_ALIAS_FILE_MAP_SINGLE.items()
        ]

        ca_account_configs = [
            AccountConfig(
                account_id_base="checking ",
                instance_params=checking_instance_params,
                number_of_accounts=2,
            )
        ]
        ca_account_contract = ContractConfig(
            clu_resource_id="checking",
            contract_file_path=self.checking_contract_with_modules,
            template_params=checking_template_params,
            smart_contract_version_id="1",
            account_configs=ca_account_configs,
            linked_contract_modules=contract_modules_checking,
        )

        sa_account_configs = [
            AccountConfig(
                account_id_base="savings ",
                instance_params=savings_instance_params,
            )
        ]
        sa_account_contract = ContractConfig(
            clu_resource_id="savings",
            contract_file_path=self.savings_contract_with_modules,
            template_params=savings_template_params,
            smart_contract_version_id="2",
            account_configs=sa_account_configs,
            linked_contract_modules=contract_modules_savings,
        )

        youth_account_configs = [
            AccountConfig(
                account_id_base="youth ",
                instance_params=youth_instance_params,
            )
        ]
        youth_account_contract = ContractConfig(
            clu_resource_id="youth",
            contract_file_path=self.youth_contract,
            template_params=youth_template_params,
            smart_contract_version_id="3",
            account_configs=youth_account_configs,
        )

        supervisee_contracts = [
            ca_account_contract,
            sa_account_contract,
            youth_account_contract,
        ]
        supervisor_config = SupervisorConfig(
            supervisor_file_path=SUPERVISOR_CONTRACT_FILE,
            supervisee_contracts=supervisee_contracts,
        )

        sub_tests = [
            SubTest(
                description="inbound hard settlement to accounts",
                events=[
                    create_inbound_hard_settlement_instruction(
                        amount="900",
                        event_datetime=start + timedelta(days=10),
                        target_account_id="checking 0",
                        internal_account_id="1",
                        denomination="GBP",
                    ),
                    create_inbound_hard_settlement_instruction(
                        amount="900",
                        event_datetime=start + timedelta(days=10),
                        target_account_id="checking 1",
                        internal_account_id="1",
                        denomination="GBP",
                    ),
                    create_inbound_hard_settlement_instruction(
                        amount="900",
                        event_datetime=start + timedelta(days=10),
                        target_account_id="savings 0",
                        internal_account_id="1",
                        denomination="GBP",
                    ),
                ],
            ),
            SubTest(
                description="check balances",
                expected_balances_at_ts={
                    start
                    + timedelta(days=10, hours=1): {
                        "savings 0": [
                            (BalanceDimensions(), "0"),
                        ],
                        "checking 0": [
                            (BalanceDimensions(), "0"),
                        ],
                        "checking 1": [(BalanceDimensions(), "0")],
                        "youth 0": [
                            (BalanceDimensions(), "0"),
                        ],
                    }
                },
                expected_posting_rejections=[
                    ExpectedRejection(
                        start + timedelta(days=10),
                        account_id="checking 0",
                        rejection_type="WrongDenomination",
                        rejection_reason="Cannot make transactions in given denomination; "
                        "transactions must be in USD",
                    ),
                    ExpectedRejection(
                        start + timedelta(days=10),
                        account_id="checking 1",
                        rejection_type="WrongDenomination",
                        rejection_reason="Cannot make transactions in given denomination; "
                        "transactions must be in USD",
                    ),
                    ExpectedRejection(
                        start + timedelta(days=10),
                        account_id="savings 0",
                        rejection_type="WrongDenomination",
                        rejection_reason="Cannot make transactions in given denomination; "
                        "transactions must be in USD",
                    ),
                ],
            ),
        ]

        test_scenario = SimulationTestScenario(
            sub_tests=sub_tests,
            start=start,
            end=end,
            supervisor_config=supervisor_config,
            internal_accounts=["1"],
        )

        res = self.run_test_scenario(test_scenario)

        self.assertTrue(get_plan_assoc_created(res, plan_id="1", account_id="savings 0"))
        self.assertTrue(get_plan_assoc_created(res, plan_id="1", account_id="checking 0"))
        self.assertTrue(get_plan_assoc_created(res, plan_id="1", account_id="checking 1"))
        self.assertTrue(get_plan_assoc_created(res, plan_id="1", account_id="youth 0"))

        self.assertTrue(get_module_link_created(res, ["interest"], smart_contract_version_id="1"))
        self.assertTrue(
            get_module_link_created(res, ["interest", "module_2"], smart_contract_version_id="2")
        )

    def test_set_default_flag_definition_ids(self):
        start = datetime(year=2019, month=1, day=1, tzinfo=timezone.utc)
        end = datetime(year=2019, month=1, day=2, tzinfo=timezone.utc)

        # create multiple flag definition ids
        flag_definition_ids = ["flag_definition_1", "flag_definition_2"]

        contract_config = ContractConfig(
            contract_file_path=self.contract_empty,
            template_params={},
            account_configs=[
                AccountConfig(
                    instance_params={},
                    account_id_base="Main account",
                )
            ],
        )

        sub_tests = [
            SubTest(
                description="Set Flag 1 to Main Account",
                events=[
                    create_flag_event(
                        flag_definition_id="flag_definition_1",
                        timestamp=start,
                        expiry_timestamp=end,
                        account_id="Main account",
                    ),
                ],
            ),
        ]

        test_scenario = SimulationTestScenario(
            start=start,
            end=end,
            sub_tests=sub_tests,
            contract_config=contract_config,
            flag_definition_ids=flag_definition_ids,
        )

        res = self.run_test_scenario(test_scenario)

        # successfully create flag definition
        flag_definition_created = get_flag_definition_created(res, "flag_definition_1")
        self.assertTrue(flag_definition_created)
        flag_definition_created = get_flag_definition_created(res, "flag_definition_2")
        self.assertTrue(flag_definition_created)

        # checking that a flag was created for main account, using flag definition 1
        flag_created = get_flag_created(res, "flag_definition_1")
        self.assertTrue(flag_created)

        # flag definition id 2 was created but flag was not create for main account
        flag_created = get_flag_created(res, "flag_definition_2")
        self.assertFalse(flag_created)

    def test_set_default_calendar_ids(self):
        start = datetime(year=2019, month=1, day=1, tzinfo=timezone.utc)
        end = datetime(year=2019, month=1, day=2, tzinfo=timezone.utc)

        # create multiple calendar ids
        calendar_ids = ["calendar_id_1", "calendar_id_2"]

        contract_config = ContractConfig(
            contract_file_path=self.contract_empty,
            template_params={},
            account_configs=[
                AccountConfig(
                    instance_params={},
                    account_id_base="Main account",
                )
            ],
        )

        sub_tests = [
            SubTest(
                description="Create Calendar Event for Calendar ID calendar_id_1",
                events=[
                    create_calendar_event(
                        timestamp=start,
                        calendar_event_id="TEST_CALENDAR",
                        calendar_id="calendar_id_1",
                        start_timestamp=start,
                        end_timestamp=end,
                    )
                ],
            ),
        ]

        test_scenario = SimulationTestScenario(
            start=start,
            end=end,
            sub_tests=sub_tests,
            contract_config=contract_config,
            calendar_ids=calendar_ids,
        )

        res = self.run_test_scenario(test_scenario)

        # successfully create calendar
        calendar_created = get_calendar_created(res, "calendar_id_1")
        self.assertTrue(calendar_created)
        calendar_created = get_calendar_created(res, "calendar_id_2")
        self.assertTrue(calendar_created)

        # checking that a calendar event was created using calendar 1
        calendar_event_created = get_calendar_event_created(res, "calendar_id_1")
        self.assertTrue(calendar_event_created)

        # calendar for id 2 was created but calendar event was not
        calendar_event_created = get_calendar_event_created(res, "calendar_id_2")
        self.assertFalse(calendar_event_created)

    def test_create_parameters(self):
        start = datetime(year=2019, month=1, day=1, tzinfo=timezone.utc)
        end = datetime(year=2019, month=1, day=2, tzinfo=timezone.utc)
        expected_parameter_id = "new_string_param_test"
        contract_codes = [
            "from contracts_api import ExpectedParameter \n"
            "version = '1.0.0'\n"
            "api = '4.0.0'\n"
            f"expected_parameters = [ ExpectedParameter(id='{expected_parameter_id}')]"
        ]
        parameter = core_api.ParameterResource(
            id=expected_parameter_id,
            constraint=core_api.StringConstraint(
                string_constraint=core_api.StringConstraintValue(min_length=1, max_length=100)
            ),
        )
        res = self.client.simulate_smart_contract(
            start_timestamp=start,
            end_timestamp=end,
            events=[],
            parameters=[parameter],
            contract_codes=contract_codes,
            smart_contract_version_ids=["1"],
            templates_parameters=[{}],
        )

        self.assertEqual(
            res[-1]["result"]["logs"], [f'created parameter "{expected_parameter_id}"']
        )

    def test_create_parameters_with_missing_expected_parameter(self):
        start = datetime(year=2019, month=1, day=1, tzinfo=timezone.utc)
        end = datetime(year=2019, month=1, day=2, tzinfo=timezone.utc)
        missing_expected_parameter = "missing_string_param_test"
        product_id_version = "1"
        contract_codes = [
            "from contracts_api import ExpectedParameter \n"
            "api = '4.0.0'\n"
            "version = '1.0.0'\n"
            f"expected_parameters = [ ExpectedParameter(id='{missing_expected_parameter}')]"
        ]
        parameter = core_api.ParameterResource(
            id="new_string_param_test",
            constraint=core_api.StringConstraint(
                string_constraint=core_api.StringConstraintValue(min_length=1, max_length=100)
            ),
        )
        with self.assertRaises(ValueError) as ex:
            self.client.simulate_smart_contract(
                start_timestamp=start,
                end_timestamp=end,
                events=[],
                parameters=[parameter],
                contract_codes=contract_codes,
                smart_contract_version_ids=[product_id_version],
            )
        self.assertIn(
            f"The expected parameter resources {missing_expected_parameter} are "
            + f"not supplied for the product id {product_id_version}.",
            str(ex.exception),
        )

    def test_create_parameters_is_empty(self):
        start = datetime(year=2019, month=1, day=1, tzinfo=timezone.utc)
        end = datetime(year=2019, month=1, day=2, tzinfo=timezone.utc)
        res = self.client.simulate_smart_contract(
            start_timestamp=start, end_timestamp=end, events=[], parameters=[]
        )
        self.assertEqual(res, [])

        res = self.client.simulate_smart_contract(
            start_timestamp=start,
            end_timestamp=end,
            events=[],
        )
        self.assertEqual(res, [])

    def test_create_only_necessary_parameters(self):
        start = datetime(year=2019, month=1, day=1, tzinfo=timezone.utc)
        end = datetime(year=2019, month=1, day=2, tzinfo=timezone.utc)
        expected_parameter_id = "new_string_param_test"
        extra_parameter_id = "new_unused_string_param_test"
        product_id = "1"
        contract_codes = [
            "from contracts_api import ExpectedParameter \n"
            "version = '1.0.0'\n"
            "api = '4.0.0'\n"
            f"expected_parameters = [ ExpectedParameter(id='{expected_parameter_id}')]"
        ]
        parameter = core_api.ParameterResource(
            id=expected_parameter_id,
            constraint=core_api.StringConstraint(
                string_constraint=core_api.StringConstraintValue(min_length=1, max_length=100)
            ),
        )
        unused_parameter = core_api.ParameterResource(
            id=extra_parameter_id,
            constraint=core_api.StringConstraint(
                string_constraint=core_api.StringConstraintValue(min_length=1, max_length=100)
            ),
        )

        res = self.client.simulate_smart_contract(
            start_timestamp=start,
            end_timestamp=end,
            events=[],
            parameters=[parameter, unused_parameter],
            contract_codes=contract_codes,
            smart_contract_version_ids=[product_id],
            templates_parameters=[{}],
        )
        search_str = f'created parameter "{extra_parameter_id}"'
        self.assertEqual(
            res[-1]["result"]["logs"], [f'created parameter "{expected_parameter_id}"']
        )
        self.assertNotIn(str(res), search_str)


class SubAccountsTest(SimulationTestCase):
    @classmethod
    def setUpClass(cls):
        cls.sub_account_metadata_contract = SUB_ACCOUNT_METADATA_CONTRACT_FILE
        super().setUpClass()

    @skipForVaultVersionLessThan(Version("5.11.0"))
    @skipForMissingExtension(required_extensions=[core_api.VaultCoreExtension.SUB_ACCOUNTS])
    def test_opening_sub_accounts(self):
        start = datetime(year=2026, month=1, day=1, tzinfo=timezone.utc)
        end = start + relativedelta(minutes=6)

        parent_account_id = "parent_account_id"
        sub_account_id_save = "sub_account_id_save"
        sub_account_id_permitted_address = "sub_account_id_permitted_address"
        sub_account_id_independent = "sub_account_id_independent"

        contract_config = ContractConfig(
            contract_file_path=self.sub_account_metadata_contract,
            template_params={},
            smart_contract_version_id="1",
            account_configs=[
                AccountConfig(
                    account_id_base=parent_account_id,
                    permitted_denominations=["GBP"],
                    sub_accounts=[
                        SubAccountConfig(
                            id=sub_account_id_save,
                            type="SAVE",
                            status=core_api.SubAccountStatus.SUB_ACCOUNT_STATUS_OPEN,
                        ),
                        SubAccountConfig(
                            id=sub_account_id_permitted_address,
                            type="PERMITTED_ADDRESS_SUB_ACCOUNT",
                            status=core_api.SubAccountStatus.SUB_ACCOUNT_STATUS_OPEN,
                        ),
                    ],
                )
            ],
        )

        sub_tests = [
            SubTest(
                description="check Sub-Accounts opened on parent Account with create_options",
                expected_sub_accounts=[
                    ExpectedSubAccountCreateWithAccountEvent(
                        timestamp=start,
                        parent_account_id=parent_account_id,
                        sub_account_id=sub_account_id_save,
                    ),
                    ExpectedSubAccountCreateWithAccountEvent(
                        timestamp=start,
                        parent_account_id=parent_account_id,
                        sub_account_id=sub_account_id_permitted_address,
                    ),
                ],
            ),
            SubTest(
                description="check Sub-Account is opened separate to parent Account",
                events=[
                    create_sub_account_instruction(
                        event_datetime=start + relativedelta(minutes=1),
                        sub_account_id=sub_account_id_independent,
                        sub_account_type="SAVE",
                        status=core_api.SubAccountStatus.SUB_ACCOUNT_STATUS_OPEN,
                        account_id=parent_account_id,
                    )
                ],
                expected_sub_accounts=[
                    ExpectedSubAccountCreateAfterAccountEvent(
                        timestamp=start + relativedelta(minutes=1),
                        parent_account_id=parent_account_id,
                        sub_account_id=sub_account_id_independent,
                    )
                ],
            ),
            SubTest(
                description="Account address is not permitted",
                events=[
                    create_outbound_hard_settlement_posting_instruction_event(
                        amount="100",
                        event_datetime=start + relativedelta(minutes=2),
                        target_account_id=parent_account_id,
                        target_sub_account_id=sub_account_id_permitted_address,
                        target_account_address="INVALID_ACCOUNT_ADDRESS",
                        internal_account_id="DEFAULT_INTERNAL_ACCOUNT",
                        denomination="GBP",
                        client_transaction_id="address not permitted ID",
                    )
                ],
                expected_account_violations={
                    start
                    + relativedelta(minutes=2): [
                        ExpectedAccountViolation(
                            account_violation=core_api.AccountViolation(
                                account_id=parent_account_id,
                                sub_account_id=sub_account_id_permitted_address,
                                type=core_api.AccountViolationType.ADDRESS_NOT_PERMITTED,
                            )
                        )
                    ]
                },
            ),
            SubTest(
                description="Sub-Account ID does not exist",
                events=[
                    create_outbound_hard_settlement_posting_instruction_event(
                        amount="100",
                        event_datetime=start + relativedelta(minutes=3),
                        target_account_id=parent_account_id,
                        target_sub_account_id="non_existent_sub_account",
                        internal_account_id="DEFAULT_INTERNAL_ACCOUNT",
                        denomination="GBP",
                        client_transaction_id="invalid Sub-Account ID",
                    )
                ],
                expected_account_violations={
                    start
                    + relativedelta(minutes=3): [
                        ExpectedAccountViolation(
                            account_violation=core_api.AccountViolation(
                                account_id=parent_account_id,
                                sub_account_id="non_existent_sub_account",
                                type=core_api.AccountViolationType.SUB_ACCOUNT_NOT_PRESENT,
                            )
                        )
                    ]
                },
            ),
            SubTest(
                description="Sub-Account status is invalid",
                events=[
                    v2_update_account_status(
                        timestamp=start + relativedelta(minutes=4),
                        account_id=parent_account_id,
                        status=core_api.AccountV2Status.ACCOUNT_STATUS_CLOSED,
                    ),
                    create_outbound_hard_settlement_posting_instruction_event(
                        amount="100",
                        event_datetime=start + relativedelta(minutes=5),
                        target_account_id=parent_account_id,
                        target_sub_account_id=sub_account_id_save,
                        internal_account_id="DEFAULT_INTERNAL_ACCOUNT",
                        denomination="GBP",
                        client_transaction_id="transaction against closed Sub-Account ID",
                    ),
                ],
                expected_account_violations={
                    start
                    + relativedelta(minutes=5): [
                        ExpectedAccountViolation(
                            account_violation=core_api.AccountViolation(
                                account_id=parent_account_id,
                                sub_account_id=sub_account_id_save,
                                type=core_api.AccountViolationType.SUB_ACCOUNT_STATUS_INVALID,
                            )
                        )
                    ]
                },
            ),
        ]

        test_scenario = SimulationTestScenario(
            start=start,
            end=end,
            sub_tests=sub_tests,
            contract_config=contract_config,
            internal_accounts={"DEFAULT_INTERNAL_ACCOUNT": "LIABILITY"},
            use_v1_accounts=False,
        )

        self.run_test_scenario(test_scenario)


class ParameterValueHierarchy(SimulationTestCase):
    @classmethod
    def setUpClass(cls):
        cls.post_parameter_change_hook_contract = POST_PARAMETER_CHANGE_HOOK_CONTRACT_FILE
        super().setUpClass()

    @skipForVaultVersionLessThan(
        Version("5.8.0"),
        "Prior to Vault 5.8.0, Contract Simulation did not support"
        "creation of Parameter Hierarchy Value Hierarchy Nodes "
        "and associating accounts",
    )
    def test_v2_account_parameter_value_hierarchy_node_association(self):
        start = datetime(year=2019, month=1, day=1, tzinfo=timezone.utc)
        end = start + relativedelta(minutes=20)
        # GIVEN a Smart Contract scv1 which defines:
        # - ExpectedParameter p1 which explicitly trigger post
        #   parameter hook execution
        # - Empty PostParameterChangeHook
        with open(
            self.post_parameter_change_hook_contract, encoding="utf-8"
        ) as smart_contract_file:
            post_parameter_change_hook_contract_contents = smart_contract_file.read()
        smart_contract_version_id = "18"
        expected_parameter_id = "expected-parameter-id"
        hierarchy_node_id_1 = "pvhn-1"
        node_name_1 = "node 1"
        param_value_1 = "node-value-1"
        hierarchy_node_id_2 = "pvhn-2"
        node_name_2 = "node 2"
        param_value_2 = "node-value-2"
        account_id_1 = "account-post-param-hook-1"
        # GIVEN a Parameter p1
        expected_parameter = core_api.ParameterResource(
            id=expected_parameter_id,
            constraint=core_api.StringConstraint(
                string_constraint=core_api.StringConstraintValue(
                    min_length=1,
                    max_length=100,
                )
            ),
        )

        parameter_value_1 = contract_sim.CreateParameterValue(
            parameter_id=expected_parameter_id,
            value=core_api.StringParameterValue(string_value=param_value_1),
            parameter_value_hierarchy_node_id=hierarchy_node_id_1,
        )

        parameter_value_2 = contract_sim.CreateParameterValue(
            parameter_id=expected_parameter_id,
            value=core_api.StringParameterValue(string_value=param_value_2),
            parameter_value_hierarchy_node_id=hierarchy_node_id_2,
        )

        pvhn_1 = contract_sim.CreateParameterValueHierarchyNode(
            parameter_value_hierarchy_node=core_api.CreateParameterValueHierarchyNode(
                id=hierarchy_node_id_1,
                name=node_name_1,
            ),
        )

        pvhn_2 = contract_sim.CreateParameterValueHierarchyNode(
            parameter_value_hierarchy_node=core_api.CreateParameterValueHierarchyNode(
                id=hierarchy_node_id_2,
                name=node_name_2,
                parent_id=hierarchy_node_id_1,
            ),
        )

        events = [
            # GIVEN Parameter Value Hierarchy Node pvhn1
            create_parameter_value_hierarchy_node(
                timestamp=start + relativedelta(seconds=1),
                parameter_value_hierarchy_node=pvhn_1,
            ),
            # GIVEN Parameter Value Hierarchy Node pvhn2, parented by pvhn1
            create_parameter_value_hierarchy_node(
                timestamp=start + relativedelta(seconds=2),
                parameter_value_hierarchy_node=pvhn_2,
            ),
            # GIVEN an Account a1, on scv1 and pvhn1
            v2_create_account_instruction(
                timestamp=start + relativedelta(seconds=3),
                v2_create_account=contract_sim.V2CreateAccount(
                    account=contract_sim.CustomerAccountRequestBody(
                        id=account_id_1,
                        smart_contract_version_id=smart_contract_version_id,
                        status=core_api.AccountV2Status.ACCOUNT_STATUS_OPEN,
                        parameter_value_hierarchy_node_id=hierarchy_node_id_1,
                        permitted_denominations=["GBP"],
                    ),
                    create_options=None,
                ),
            ),
            # GIVEN a Parameter Value pv1 for Parameter p1,
            # owned by pvhn1 is created at t4
            create_parameter_value(
                timestamp=start + relativedelta(seconds=4),
                parameter_value=parameter_value_1,
            ),
            # AND a1 is updated to be associated with pvhn2
            v2_update_account_parameter_value_hierarchy_node_id(
                timestamp=start + relativedelta(seconds=5),
                account_id=account_id_1,
                parameter_value_hierarchy_node_id=hierarchy_node_id_2,
            ),
            # AND a Parameter Value pv1 for Parameter p1,
            # owned by pvhn2 is created at t6
            create_parameter_value(
                timestamp=start + relativedelta(seconds=6),
                parameter_value=parameter_value_2,
            ),
        ]

        res = self.client.simulate_smart_contract(
            start_timestamp=start,
            end_timestamp=end,
            events=events,
            parameters=[expected_parameter],
            contract_codes=[post_parameter_change_hook_contract_contents],
            smart_contract_version_ids=[smart_contract_version_id],
            templates_parameters=[{}],
        )
        str_res = str(res)
        search_strings = [
            f'created parameter "{expected_parameter_id}"',
            f'created parameter value hierarchy node "{node_name_1}" '
            f'with id "{hierarchy_node_id_1}", with '
            f"no parent node (root node)",
            f'created parameter value hierarchy node "{node_name_2}" '
            f'with id "{hierarchy_node_id_2}", with '
            f'parent node id "{hierarchy_node_id_1}"',
            f'created account "{account_id_1}"',
            f"'created value \\'string_value:\"{param_value_1}\"\\' "
            f'owned by parameter value hierarchy node "{hierarchy_node_id_1}" '
            f'for parameter "{expected_parameter_id}"\']',
            # THEN the Post Parameter Hook Execution is triggered for a1
            # at t9 (t4 + 5s offset due to pvhn1 parameter value change).
            f'processed account parameter change for account "{account_id_1}"',
            # THEN no Post Parameter Hook Execution is triggered since value
            # didn't change and pvhn2 inherits value from pvhn1.
            f"'created value \\'string_value:\"{param_value_2}\"\\' "
            f'owned by parameter value hierarchy node "{hierarchy_node_id_2}" '
            f'for parameter "{expected_parameter_id}"\']',
            # THEN the Post Parameter Hook Execution is triggered for a1
            # at t11 (t6 + 5s offset due to pvhn2 parameter value change).
            f'processed account parameter change for account "{account_id_1}"',
        ]
        for search_string in search_strings:
            self.assertIn(search_string, str_res)


class FutureDatedPostingsTest(SimulationTestCase):
    def test_successful_fdp_request(self):
        start = datetime(year=2025, month=1, day=1, tzinfo=timezone.utc)
        end = start + timedelta(days=3)

        account_id = "Main account"
        internal_account_id = "1"
        main_account = account_to_simulate(
            timestamp=start,
            account_id=account_id,
            contract_file_path=EMPTY_LIABILITY_CONTRACT_V4,
        )

        events = [
            create_inbound_hard_settlement_posting_instruction_event(
                amount="10",
                denomination="GBP",
                event_datetime=start + timedelta(minutes=1),
                value_timestamp=start + timedelta(minutes=2),
                booking_timestamp=start + timedelta(minutes=2),
                client_transaction_id="FUTURE_IHS",
                client_batch_id="IHS_BATCH_ID",
                target_account_id=account_id,
                internal_account_id=internal_account_id,
            ),
            create_outbound_hard_settlement_posting_instruction_event(
                amount="2",
                denomination="GBP",
                event_datetime=start + timedelta(minutes=3),
                value_timestamp=start + timedelta(minutes=4),
                booking_timestamp=start + timedelta(minutes=4),
                client_transaction_id="FUTURE_OHS",
                client_batch_id="OHS_BATCH_ID",
                target_account_id=account_id,
                internal_account_id=internal_account_id,
            ),
            create_outbound_hard_settlement_posting_instruction_event(
                amount="100",
                denomination="GBP",
                event_datetime=start + timedelta(minutes=5),
                client_transaction_id="ANY_OHS",
                client_batch_id="ANY_BATCH_ID",
                target_account_id=account_id,
                internal_account_id=internal_account_id,
            ),
        ]

        res = self.client.simulate_smart_contract(
            start_timestamp=start,
            end_timestamp=end,
            events=events,
            internal_account_ids=[internal_account_id],
            account_creation_events=[main_account],
        )
        self.assertEqual(get_num_postings(res, account_id), 3)
        self.assertEqual(get_num_postings(res, internal_account_id), 3)

        balances = get_balances(res)
        main_balances = balances[account_id]
        internal_balances = balances[internal_account_id]

        # since future-dated postings aren't visible in balances until after their value timestamp,
        # balances are asserted at given times reflecting this behaviour.
        self.assertEqual(main_balances.at(start + timedelta(minutes=1))[BalanceDimensions()].net, 0)
        self.assertEqual(
            main_balances.at(start + timedelta(minutes=3))[BalanceDimensions()].net, 10
        )
        self.assertEqual(
            main_balances.at(start + timedelta(minutes=5))[BalanceDimensions()].net, -92
        )
        self.assertEqual(
            internal_balances.at(start + timedelta(minutes=5))[BalanceDimensions()].net, 92
        )

    def test_mixed_pi_level_value_timestamps_successful(self):
        start = datetime(year=2025, month=1, day=1, tzinfo=timezone.utc)
        end = start + timedelta(days=2)

        account_id = "Main account"
        internal_account_id = "1"
        main_account = account_to_simulate(
            timestamp=start,
            account_id=account_id,
            contract_file_path=EMPTY_LIABILITY_CONTRACT_V4,
        )

        events = [
            # PI level value timestamp in the past
            create_inbound_hard_settlement_posting_instruction_event(
                amount="10",
                denomination="GBP",
                event_datetime=start + timedelta(minutes=1),
                value_timestamp=start - timedelta(days=1),
                client_transaction_id="PAST_TS",
                target_account_id=account_id,
                internal_account_id=internal_account_id,
            ),
            # PI level value timestamp in the future
            create_transfer_posting_instruction_event(
                amount="2",
                denomination="GBP",
                creditor_target_account_id=account_id,
                debtor_target_account_id=internal_account_id,
                event_datetime=start + timedelta(minutes=3),
                value_timestamp=start + timedelta(days=1),
                client_transaction_id="FUTURE_TS",
            ),
            # PI level value timestamp unset
            create_outbound_hard_settlement_posting_instruction_event(
                amount="5",
                denomination="GBP",
                event_datetime=start + timedelta(days=1, hours=3),
                client_transaction_id="UNSET_TS",
                target_account_id=account_id,
                internal_account_id=internal_account_id,
            ),
        ]

        res = self.client.simulate_smart_contract(
            start_timestamp=start,
            end_timestamp=end,
            events=events,
            internal_account_ids=[internal_account_id],
            account_creation_events=[main_account],
        )

        self.assertEqual(get_num_postings(res, account_id), 3)
        balances = get_balances(res)[account_id]
        self.assertEqual(balances.at(start + timedelta(minutes=1))[BalanceDimensions()].net, 10)
        self.assertEqual(balances.at(start + timedelta(minutes=3))[BalanceDimensions()].net, 10)
        self.assertEqual(
            balances.at(start + timedelta(days=1, hours=3))[BalanceDimensions()].net, 7
        )

    def test_mix_pibs_with_pib_level_and_pi_level_value_timestamps_successful(self):
        start = datetime(year=2025, month=1, day=1, tzinfo=timezone.utc)
        end = start + timedelta(days=3)

        account_id = "Main account"
        internal_account_id = "1"
        main_account = account_to_simulate(
            timestamp=start,
            account_id=account_id,
            contract_file_path=EMPTY_LIABILITY_CONTRACT_V4,
        )

        events = [
            create_inbound_authorisation_posting_instruction_event(
                amount="1",
                event_datetime=start + timedelta(minutes=1),
                denomination="GBP",
                client_transaction_id="FUTURE_VALUE_DT_ON_PI",
                client_batch_id="IAUTH_BATCH_ID",
                value_timestamp=start + timedelta(days=1),  # PI level
                booking_timestamp=start + timedelta(days=1),
                target_account_id=account_id,
                internal_account_id=internal_account_id,
            ),
            create_settlement_posting_instruction_event(
                amount="1",
                event_datetime=start + timedelta(minutes=2),
                client_transaction_id="FUTURE_VALUE_DT_ON_PI",
                value_timestamp=start + timedelta(days=1, minutes=1),  # PI level
                booking_timestamp=start + timedelta(days=1, minutes=1),
            ),
            create_inbound_hard_settlement_instruction(
                amount="12",
                event_datetime=start + timedelta(days=1, hours=4),
                denomination="GBP",
                client_transaction_id="VALUE_DT_ON_PIB",
                batch_details={"description": "IHS_BATCH_DETAILS"},
                value_timestamp=start + timedelta(days=1, hours=4),  # PIB-level
                target_account_id=account_id,
                internal_account_id=internal_account_id,
            ),
        ]

        res = self.client.simulate_smart_contract(
            start_timestamp=start,
            end_timestamp=end,
            events=events,
            internal_account_ids=[internal_account_id],
            account_creation_events=[main_account],
        )
        self.assertEqual(get_num_postings(res, account_id), 4)
        self.assertEqual(get_num_postings(res, internal_account_id), 4)

        balances = get_balances(res)
        main_balances = balances[account_id]
        internal_balances = balances[internal_account_id]
        self.assertEqual(main_balances.at(start + timedelta(minutes=2))[BalanceDimensions()].net, 0)
        self.assertEqual(
            main_balances.at(start + timedelta(days=1, hours=4))[BalanceDimensions()].net, 13
        )
        self.assertEqual(
            internal_balances.at(start + timedelta(days=1, hours=4))[BalanceDimensions()].net, -13
        )


class HelperTest(SimulationTestCase):
    def test_smart_contract_to_json_rejected(self):
        start = datetime(year=2019, month=1, day=1, tzinfo=timezone.utc)
        end = datetime(year=2019, month=1, day=2, tzinfo=timezone.utc)

        expected_output = (
            "The length of contract_codes, templates_parameters and "
            + "smart_contract_version_ids must be equal."
        )

        with self.assertRaises(ValueError) as e:
            self.client.simulate_smart_contract(
                start_timestamp=start,
                end_timestamp=end,
                events=[],
                templates_parameters=[{}, {}, {}],
            )

        self.assertEqual(str(e.exception), expected_output)
