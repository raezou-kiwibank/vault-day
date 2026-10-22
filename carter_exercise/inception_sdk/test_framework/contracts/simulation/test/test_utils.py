# Copyright @ 2022 Thought Machine Group Limited. All rights reserved.
# standard libs
import io
from datetime import datetime, timezone
from decimal import Decimal
from time import time
from unittest import TestCase, mock
from unittest.mock import MagicMock, Mock, call, mock_open, patch

# inception sdk
import inception_sdk.test_framework.contracts.simulation.utils as utils
from inception_sdk.test_framework.common.balance_helpers import (
    Balance,
    BalanceDimensions,
    NetBalance,
    NetBalanceMismatches,
    NetBalances,
)
from inception_sdk.test_framework.contracts.simulation.data_objects.data_objects import (
    AccountConfig,
    ContractConfig,
    ContractNotificationResourceType,
    ExpectedAccountAttributeValue,
    ExpectedAccountViolation,
    ExpectedContractNotification,
    ExpectedContractViolation,
    ExpectedPostingEnrichments,
    ExpectedPostingViolation,
    SimulationTestScenario,
    SuperviseeConfig,
    SupervisorConfig,
)
from inception_sdk.test_framework.contracts.simulation.utils import (
    SimulationTestCase,
    create_supervisor_config,
    get_account_attribute_values,
    get_account_logs,
    get_balances,
    get_contract_contents,
    get_contract_notifications,
    get_flag_created,
    get_flag_definition_created,
    get_inflight_balances,
    get_internal_account_balances,
    get_logs,
    get_logs_with_timestamp,
    get_net_balances,
    get_num_postings,
    get_plan_assoc_created,
    get_plan_created,
    get_plan_logs,
    get_posting_enrichments,
    get_posting_instruction_batch,
    get_postings,
    get_processed_scheduled_events,
    get_value_and_booking_balances,
    get_violations,
    print_json,
    print_log,
    print_postings,
)
from inception_sdk.vault import core_api

SIMULATOR_RESPONSE_FILE = (
    "inception_sdk/test_framework/contracts/simulation/test/sample_simulator_response"
)
SIMULATOR_RESPONSE_VIOLATIONS_FILE = (
    "inception_sdk/test_framework/contracts/simulation/test/sample_simulator_response_violations"
)
BACKDATED_SIMULATOR_RESPONSE_FILE = (
    "inception_sdk/test_framework/contracts/simulation/test/backdated_simulator_response"
)
SUPERVISOR_RESPONSE_FILE = (
    "inception_sdk/test_framework/contracts/simulation/test/sample_supervisor_response"
)


class TestSimulationTestCase(TestCase):
    def tearDown(self) -> None:
        # The tests modify the class variable intentionally, but this causes test failures
        # depending on the ordering given we assert on dict contents
        SimulationTestCase.smart_contract_path_to_content = {}
        return super().tearDown()

    @patch.object(SimulationTestCase, "load_vault_version")
    @patch.object(SimulationTestCase, "contract_filepaths", ["contract_filepath"])
    @patch.object(SimulationTestCase, "load_output_data")
    @patch.object(SimulationTestCase, "load_input_data")
    @patch.object(SimulationTestCase, "load_test_config")
    @patch.object(utils, "SmartContractRenderer")
    @patch.object(utils, "RendererConfig")
    @patch.object(utils, "is_file_renderable")
    @patch.object(utils, "load_module_from_filepath", MagicMock)
    def test_setup_class_calls_renderer(
        self,
        mock_is_file_renderable: Mock,
        mock_renderer_config: Mock,
        mock_renderer: Mock,
        mock_load_test_config_method: Mock,
        mock_load_input_data_method: Mock,
        mock_load_output_data_method: Mock,
        mock_load_vault_version: Mock,
    ):
        test_rendered_content = "test_rendered_content"

        mock_is_file_renderable.return_value = True
        mock_renderer_instance = Mock()
        mock_renderer.return_value = mock_renderer_instance
        mock_renderer_instance.rendered_contract = test_rendered_content

        SimulationTestCase.setUpClass()

        mock_renderer_config.assert_called_once_with(
            autogen_warning="# Code auto-generated for simulation testing",
            apply_formatting=False,
            use_git=False,
        )
        mock_renderer.assert_called_once()
        mock_renderer_instance.render.assert_called_once_with(write_to_file=False)

        mock_load_test_config_method.assert_called_once()
        mock_load_input_data_method.assert_called_once()
        mock_load_output_data_method.assert_called_once()
        mock_load_vault_version.assert_called_once()

        self.assertDictEqual(
            SimulationTestCase.smart_contract_path_to_content,
            {"contract_filepath": test_rendered_content},
        )

    @patch.object(SimulationTestCase, "load_vault_version")
    @patch.object(
        SimulationTestCase,
        "contract_filepaths",
        ["contract_template_1", "contract_filepath_1", "contract_template_2"],
    )
    @patch.object(SimulationTestCase, "load_output_data")
    @patch.object(SimulationTestCase, "load_input_data")
    @patch.object(SimulationTestCase, "load_test_config")
    @patch.object(utils, "SmartContractRenderer")
    @patch.object(utils, "RendererConfig")
    @patch.object(utils, "is_file_renderable")
    @patch.object(utils, "load_module_from_filepath", MagicMock)
    @patch("builtins.open", new_callable=mock_open, read_data="smart_contract_contents")
    def test_setup_class_calls_renderer_multiple_files(
        self,
        mock_open: Mock,
        mock_is_file_renderable: Mock,
        mock_renderer_config: Mock,
        mock_renderer: Mock,
        mock_load_test_config_method: Mock,
        mock_load_input_data_method: Mock,
        mock_load_output_data_method: Mock,
        mock_load_vault_version: Mock,
    ):
        mock_is_file_renderable.side_effect = [True, False, True]
        mock_renderer_instance = Mock()
        mock_renderer.return_value = mock_renderer_instance
        mock_renderer_instance.rendered_contract = "smart_contract_rendered_contents"

        SimulationTestCase.setUpClass()

        mock_renderer_config.assert_has_calls(
            [
                call(
                    autogen_warning="# Code auto-generated for simulation testing",
                    apply_formatting=False,
                    use_git=False,
                ),
                call(
                    autogen_warning="# Code auto-generated for simulation testing",
                    apply_formatting=False,
                    use_git=False,
                ),
            ]
        )
        self.assertEqual(mock_renderer.call_count, 2)
        mock_renderer_instance.render.assert_has_calls(
            [call(write_to_file=False), call(write_to_file=False)]
        )

        mock_load_test_config_method.assert_called_once()
        mock_load_input_data_method.assert_called_once()
        mock_load_output_data_method.assert_called_once()
        mock_open.assert_called_once()
        mock_load_vault_version.assert_called_once()

        self.assertDictEqual(
            SimulationTestCase.smart_contract_path_to_content,
            {
                "contract_template_1": "smart_contract_rendered_contents",
                "contract_filepath_1": "smart_contract_contents",
                "contract_template_2": "smart_contract_rendered_contents",
            },
        )


class UtilsTest(SimulationTestCase):
    """
    This tests the integration test utils.
    """

    def setUp(self):
        self._started_at = time()
        sim_res_file = SIMULATOR_RESPONSE_FILE
        sim_res_violations_file = SIMULATOR_RESPONSE_VIOLATIONS_FILE
        supervisor_res_file = SUPERVISOR_RESPONSE_FILE
        backdated_sim_res_file = BACKDATED_SIMULATOR_RESPONSE_FILE

        with open(sim_res_file, "r", encoding="utf-8") as simulator_response_file:
            self.sample_res = eval(simulator_response_file.read())

        with open(sim_res_violations_file, "r", encoding="utf-8") as res_file:
            self.sample_res_with_violations = eval(res_file.read())

        with open(backdated_sim_res_file, "r", encoding="utf-8") as simulator_response_file:
            self.backdated_sample_res = eval(simulator_response_file.read())

        with open(supervisor_res_file, "r", encoding="utf-8") as simulator_response_file:
            self.supervisor_res = eval(simulator_response_file.read())

    def test_get_live_balances_v2(self):
        expected_time = datetime(2019, 1, 1, tzinfo=timezone.utc)
        result = get_net_balances(self.sample_res)

        self.assertIn(expected_time, result)
        account_balances = result[expected_time]

        expected_balances = NetBalances(
            value_net_balances=[
                NetBalance(
                    account_address="DEFAULT",
                    account_id="1",
                    amount=Decimal("110"),
                    asset="COMMERCIAL_BANK_MONEY",
                    denomination="GBP",
                    phase=core_api.PostingPhase.COMMITTED,
                ),
                NetBalance(
                    account_address="DEFAULT",
                    account_id="Main account",
                    amount=Decimal("-110"),
                    asset="COMMERCIAL_BANK_MONEY",
                    denomination="GBP",
                    phase=core_api.PostingPhase.COMMITTED,
                ),
                NetBalance(
                    account_address="DEFAULT",
                    account_id="1",
                    amount=Decimal("130"),
                    asset="COMMERCIAL_BANK_MONEY",
                    denomination="GBP",
                    phase=core_api.PostingPhase.COMMITTED,
                ),
                NetBalance(
                    account_address="DEFAULT",
                    account_id="Main account",
                    amount=Decimal("-130"),
                    asset="COMMERCIAL_BANK_MONEY",
                    denomination="GBP",
                    phase=core_api.PostingPhase.COMMITTED,
                ),
            ],
            booking_net_balances=[
                NetBalance(
                    account_address="DEFAULT",
                    account_id="1",
                    amount=Decimal("110"),
                    asset="COMMERCIAL_BANK_MONEY",
                    denomination="GBP",
                    phase=core_api.PostingPhase.COMMITTED,
                ),
                NetBalance(
                    account_address="DEFAULT",
                    account_id="Main account",
                    amount=Decimal("-110"),
                    asset="COMMERCIAL_BANK_MONEY",
                    denomination="GBP",
                    phase=core_api.PostingPhase.COMMITTED,
                ),
                NetBalance(
                    account_address="DEFAULT",
                    account_id="1",
                    amount=Decimal("130"),
                    asset="COMMERCIAL_BANK_MONEY",
                    denomination="GBP",
                    phase=core_api.PostingPhase.COMMITTED,
                ),
                NetBalance(
                    account_address="DEFAULT",
                    account_id="Main account",
                    amount=Decimal("-130"),
                    asset="COMMERCIAL_BANK_MONEY",
                    denomination="GBP",
                    phase=core_api.PostingPhase.COMMITTED,
                ),
            ],
        )

        self.assertEqual(account_balances, expected_balances)

    def test_check_live_balances_v2_matching(self):
        test_time = datetime(2026, 8, 27, 12, 0, 0, tzinfo=timezone.utc)

        actual_account_balance = NetBalances(
            value_net_balances=[
                NetBalance(
                    account_id="acc_1",
                    account_address="DEFAULT",
                    phase=core_api.PostingPhase.COMMITTED,
                    asset="COMMERCIAL_BANK_MONEY",
                    denomination="GBP",
                    amount=Decimal("100.50"),
                )
            ],
            booking_net_balances=[],
        )

        expected_account_balance = NetBalances(
            value_net_balances=[
                NetBalance(
                    account_id="acc_1",
                    account_address="DEFAULT",
                    phase=core_api.PostingPhase.COMMITTED,
                    asset="COMMERCIAL_BANK_MONEY",
                    denomination="GBP",
                    amount=Decimal("100.50"),
                )
            ],
            booking_net_balances=[],
        )

        # Should pass without raising exceptions
        self.assertIsNone(
            self.check_live_balances_v2(
                expected_balances={test_time: expected_account_balance},
                actual_balances={test_time: actual_account_balance},
            )
        )

    def test_check_balances_v2_mismatched(self):
        test_time = datetime(2026, 8, 27, 12, 0, 0, tzinfo=timezone.utc)

        actual_account_balance = NetBalances(
            value_net_balances=[
                NetBalance(
                    account_id="acc_1",
                    account_address="DEFAULT",
                    phase=core_api.PostingPhase.COMMITTED,
                    asset="COMMERCIAL_BANK_MONEY",
                    denomination="GBP",
                    amount=Decimal("100.50"),
                )
            ],
            booking_net_balances=[],
        )

        # Expected is different amount
        expected_account_balance = NetBalances(
            value_net_balances=[
                NetBalance(
                    account_id="acc_1",
                    account_address="DEFAULT",
                    phase=core_api.PostingPhase.COMMITTED,
                    asset="COMMERCIAL_BANK_MONEY",
                    denomination="GBP",
                    amount=Decimal("200.00"),
                )
            ],
            booking_net_balances=[],
        )

        with self.assertRaises(AssertionError) as ctx:
            self.check_live_balances_v2(
                expected_balances={test_time: expected_account_balance},
                actual_balances={test_time: actual_account_balance},
            )

        expected_mismatches = {
            test_time: {
                "acc_1": NetBalanceMismatches(
                    expected_value_balances=expected_account_balance.value_net_balances,
                    expected_booking_balances=[],
                    actual_value_balances=actual_account_balance.value_net_balances,
                    actual_booking_balances=[],
                )
            }
        }
        self.assertEqual(str(ctx.exception), f"expected values not found: {expected_mismatches}")

    def test_get_balances_for_undefined_dimensions(self):
        balances = get_balances(res=self.sample_res)
        internal_balances = balances["1"]

        date = datetime(2019, 1, 1, minute=1, tzinfo=timezone.utc)
        self.assertEqual(internal_balances.before(date)[BalanceDimensions("XYZ")].net, Decimal("0"))

    def test_get_value_and_booking_balances_for_undefined_account(self):
        value_balances, booking_balances = get_value_and_booking_balances(res=self.sample_res)
        xyz_balances = value_balances["xyz"]
        date = datetime(2019, 1, 1, minute=1, tzinfo=timezone.utc)
        self.assertEqual(xyz_balances.at(date)[BalanceDimensions()].net, Decimal("0"))

        xyz_balances = booking_balances["xyz"]
        date = datetime(2019, 1, 1, minute=1, tzinfo=timezone.utc)
        self.assertEqual(xyz_balances.at(date)[BalanceDimensions()].net, Decimal("0"))

    def test_get_internal_balances_for_undefined_internal_account(self):
        value_balances = get_internal_account_balances(
            res=self.sample_res, internal_accounts={"1": "LIABILITY"}
        )
        xyz_balances = value_balances["xyz"]
        date = datetime(2019, 1, 1, minute=1, tzinfo=timezone.utc)
        self.assertEqual(xyz_balances.at(date)[BalanceDimensions()].net, Decimal("0"))

    def test_get_balances_for_undefined_date(self):
        balances = get_balances(res=self.sample_res)
        main_balances = balances["Main account"]
        date = datetime(2018, 1, 1, minute=1, tzinfo=timezone.utc)
        self.assertEqual(main_balances.at(date)[BalanceDimensions()].net, Decimal("0"))

    def test_get_value_and_booking_balances_for_undefined_date(self):
        value_balances, booking_balances = get_value_and_booking_balances(res=self.sample_res)
        main_balances = value_balances["Main account"]
        date = datetime(2018, 1, 1, minute=1, tzinfo=timezone.utc)
        self.assertEqual(main_balances.at(date)[BalanceDimensions()].net, Decimal("0"))

        main_balances = booking_balances["Main account"]
        date = datetime(2018, 1, 1, minute=1, tzinfo=timezone.utc)
        self.assertEqual(main_balances.at(date)[BalanceDimensions()].net, Decimal("0"))

    def test_get_internal_balances_for_undefined_date(self):
        value_balances = get_internal_account_balances(
            res=self.sample_res, internal_accounts={"1": "LIABILITY"}
        )
        internal_value_balances = value_balances["1"]
        date = datetime(2018, 1, 1, minute=1, tzinfo=timezone.utc)
        self.assertEqual(internal_value_balances.at(date)[BalanceDimensions()].net, Decimal("0"))

    def test_get_balances_before_without_backdating(self):
        balances = get_balances(res=self.sample_res)
        main_balances = balances["Main account"]
        internal_balances = balances["1"]

        date = datetime(2019, 1, 1, minute=1, tzinfo=timezone.utc)
        self.assertEqual(main_balances.before(date)[BalanceDimensions()].net, Decimal("-130"))
        self.assertEqual(internal_balances.before(date)[BalanceDimensions()].net, Decimal("130"))

    def test_get_value_and_booking_balances_before_without_backdating(self):
        value_balances, booking_balances = get_value_and_booking_balances(res=self.sample_res)

        main_balances = value_balances["Main account"]
        internal_balances = value_balances["1"]
        date = datetime(2019, 1, 1, minute=1, tzinfo=timezone.utc)
        self.assertEqual(main_balances.before(date)[BalanceDimensions()].net, Decimal("-130"))
        self.assertEqual(internal_balances.before(date)[BalanceDimensions()].net, Decimal("130"))

        main_balances = booking_balances["Main account"]
        internal_balances = booking_balances["1"]
        date = datetime(2019, 1, 1, minute=1, tzinfo=timezone.utc)
        self.assertEqual(main_balances.before(date)[BalanceDimensions()].net, Decimal("-130"))
        self.assertEqual(internal_balances.before(date)[BalanceDimensions()].net, Decimal("130"))

    def test_get_internal_balances_before_without_backdating(self):
        value_balances = get_internal_account_balances(
            res=self.sample_res, internal_accounts={"1": "LIABILITY"}
        )
        internal_value_balances = value_balances["1"]

        date = datetime(2019, 1, 1, minute=1, tzinfo=timezone.utc)
        self.assertEqual(
            internal_value_balances.before(date)[BalanceDimensions()].net, Decimal("130")
        )

    def test_get_balances_at_without_backdating(self):
        balances = get_balances(res=self.sample_res)
        main_balances = balances["Main account"]
        internal_balances = balances["1"]

        date = datetime(2019, 1, 1, minute=1, tzinfo=timezone.utc)
        self.assertEqual(main_balances.at(date)[BalanceDimensions()].net, Decimal("-130"))
        self.assertEqual(internal_balances.at(date)[BalanceDimensions()].net, Decimal("130"))

    def test_get_value_and_booking_balances_at_without_backdating(self):
        value_balances, booking_balances = get_value_and_booking_balances(res=self.sample_res)

        main_balances = value_balances["Main account"]
        internal_balances = value_balances["1"]
        date = datetime(2019, 1, 1, minute=1, tzinfo=timezone.utc)
        self.assertEqual(main_balances.at(date)[BalanceDimensions()].net, Decimal("-130"))
        self.assertEqual(internal_balances.at(date)[BalanceDimensions()].net, Decimal("130"))

        main_balances = booking_balances["Main account"]
        internal_balances = booking_balances["1"]
        date = datetime(2019, 1, 1, minute=1, tzinfo=timezone.utc)
        self.assertEqual(main_balances.at(date)[BalanceDimensions()].net, Decimal("-130"))
        self.assertEqual(internal_balances.at(date)[BalanceDimensions()].net, Decimal("130"))

    def test_get_internal_balances_at_without_backdating(self):
        value_balances = get_internal_account_balances(
            res=self.sample_res, internal_accounts={"1": "LIABILITY"}
        )
        internal_value_balances = value_balances["1"]

        date = datetime(2019, 1, 1, minute=1, tzinfo=timezone.utc)
        self.assertEqual(internal_value_balances.at(date)[BalanceDimensions()].net, Decimal("130"))

    def test_get_balances_latest_without_backdating(self):
        balances = get_balances(res=self.sample_res)
        main_balances = balances["Main account"]
        internal_balances = balances["1"]

        self.assertEqual(main_balances.latest()[BalanceDimensions()].net, Decimal("1130"))
        self.assertEqual(internal_balances.latest()[BalanceDimensions()].net, Decimal("-1130"))

    def test_get_value_and_booking_balances_latest_without_backdating(self):
        value_balances, booking_balances = get_value_and_booking_balances(res=self.sample_res)

        main_balances = value_balances["Main account"]
        internal_balances = value_balances["1"]
        self.assertEqual(main_balances.latest()[BalanceDimensions()].net, Decimal("1130"))
        self.assertEqual(internal_balances.latest()[BalanceDimensions()].net, Decimal("-1130"))

        main_balances = booking_balances["Main account"]
        internal_balances = booking_balances["1"]
        self.assertEqual(main_balances.latest()[BalanceDimensions()].net, Decimal("1130"))
        self.assertEqual(internal_balances.latest()[BalanceDimensions()].net, Decimal("-1130"))

    def test_get_internal_balances_atest_without_backdating(self):
        value_balances = get_internal_account_balances(
            res=self.sample_res, internal_accounts={"1": "LIABILITY"}
        )
        internal_value_balances = value_balances["1"]

        self.assertEqual(
            internal_value_balances.latest()[BalanceDimensions()].net, Decimal("-1130")
        )

    def test_get_inflight_balances_with_pib_level_timestamp(self):
        pib_timestamp = "2026-01-01T00:00:00Z"
        internal_accounts = {"Main account": "LIABILITY"}
        pibs = [
            {
                "value_timestamp": pib_timestamp,
                "posting_instructions": [
                    {
                        "committed_postings": [
                            {
                                "account_id": "Main account",
                                "amount": "14",
                                "credit": True,
                                "account_address": "DEFAULT",
                                "asset": "COMMERCIAL_BANK_MONEY",
                                "denomination": "GBP",
                                "phase": "POSTING_PHASE_COMMITTED",
                            }
                        ]
                    }
                ],
            }
        ]
        expected_balances = {
            "Main account": {
                datetime(2026, 1, 1, tzinfo=timezone.utc): (
                    BalanceDimensions(
                        address="DEFAULT",
                        asset="COMMERCIAL_BANK_MONEY",
                        denomination="GBP",
                        phase="POSTING_PHASE_COMMITTED",
                    ),
                    Balance(credit=Decimal("14"), debit=Decimal("0"), net=Decimal("14")),
                )
            }
        }
        actual_balances = get_inflight_balances(pibs, internal_accounts)
        self.assertEqual(actual_balances, expected_balances)

    def test_get_inflight_balances_with_pi_level_timestamp(self):
        pi_timestamp = "2026-01-01T00:00:00Z"
        internal_accounts = {"Main account": "LIABILITY"}
        pibs = [
            {
                "value_timestamp": None,
                "posting_instructions": [
                    {
                        "value_timestamp": pi_timestamp,
                        "committed_postings": [
                            {
                                "account_id": "Main account",
                                "amount": "6",
                                "credit": True,
                                "account_address": "DEFAULT",
                                "asset": "COMMERCIAL_BANK_MONEY",
                                "denomination": "GBP",
                                "phase": "POSTING_PHASE_COMMITTED",
                            }
                        ],
                    }
                ],
            }
        ]
        expected_balances = {
            "Main account": {
                datetime(2026, 1, 1, tzinfo=timezone.utc): (
                    BalanceDimensions(
                        address="DEFAULT",
                        asset="COMMERCIAL_BANK_MONEY",
                        denomination="GBP",
                        phase="POSTING_PHASE_COMMITTED",
                    ),
                    Balance(credit=Decimal("6"), debit=Decimal("0"), net=Decimal("6")),
                )
            }
        }
        actual_balances = get_inflight_balances(pibs, internal_accounts)
        self.assertEqual(actual_balances, expected_balances)

    def test_get_inflight_balances_with_no_pib_or_pi_timestamp_raises(self):
        internal_accounts = {"Main account": "LIABILITY"}
        pibs = [
            {
                "value_timestamp": None,
                "posting_instructions": [
                    {
                        "value_timestamp": None,
                        "committed_postings": [
                            {
                                "account_id": "Main account",
                                "amount": "101",
                                "credit": True,
                                "account_address": "DEFAULT",
                                "asset": "COMMERCIAL_BANK_MONEY",
                                "denomination": "GBP",
                                "phase": "POSTING_PHASE_COMMITTED",
                            }
                        ],
                    }
                ],
            }
        ]
        with self.assertRaises(ValueError) as ctx:
            get_inflight_balances(pibs, internal_accounts)
        self.assertIn(
            "Simulation response is malformed: `value_timestamp` is not set on either PI or PIB "
            "level.",
            str(ctx.exception),
        )

    def test_get_flag_definition_created(self):
        is_flag_created = get_flag_definition_created(
            res=self.sample_res, flag_definition_id="debug_flag"
        )

        self.assertTrue(is_flag_created)

    def test_get_flag_created(self):
        is_flag_applied_to_account = get_flag_created(
            res=self.sample_res,
            flag_definition_id="debug_flag",
            account_id="Main account",
        )

        self.assertTrue(is_flag_applied_to_account)

    def test_get_logs(self):
        logs = get_logs(res=self.sample_res)
        self.assertIn("created account", logs)
        self.assertIn("processed scheduled event", logs)

    def test_get_account_logs(self):
        account_logs_main = get_account_logs(res=self.sample_res, account_id="Main account")

        self.assertNotIn('account "1"', account_logs_main)
        self.assertIn('account "Main account"', account_logs_main)

        account_logs_1 = get_account_logs(res=self.sample_res, account_id="1")

        self.assertNotIn('account "Main account"', account_logs_1)
        self.assertIn('account "1"', account_logs_1)
        account_logs_supervisor = get_account_logs(
            res=self.supervisor_res, account_id="Savings Account"
        )

        self.assertNotIn('account "Checking Account"', account_logs_supervisor)
        self.assertIn('account "Savings Account"', account_logs_supervisor)

    def test_get_plan_logs(self):
        plan_logs_main = get_plan_logs(res=self.supervisor_res, plan_id="1")

        self.assertIn('plan "1"', plan_logs_main)
        self.assertIn('created plan "1"', plan_logs_main)
        self.assertIn(
            'created account plan association for account "Checking Account"',
            plan_logs_main,
        )
        self.assertNotIn('created account "Checking Account"', plan_logs_main)

    def test_get_plan_created(self):
        plan_created = get_plan_created(res=self.supervisor_res, plan_id="1")

        self.assertTrue(plan_created)

        plan_not_existing_id = get_plan_created(
            res=self.supervisor_res, plan_id="1", supervisor_version_id="5"
        )

        self.assertFalse(plan_not_existing_id)

    def test_get_plan_assoc_created(self):
        checking_account_plan_created = get_plan_assoc_created(
            res=self.supervisor_res, plan_id="1", account_id="Checking Account"
        )

        self.assertTrue(checking_account_plan_created)

        savings_account_plan_created = get_plan_assoc_created(
            res=self.supervisor_res, plan_id="1", account_id="Savings Account"
        )

        self.assertTrue(savings_account_plan_created)

        plan_not_created = get_plan_assoc_created(
            res=self.supervisor_res, plan_id="1", account_id="Youth Account"
        )

        self.assertFalse(plan_not_created)

    def test_get_logs_with_timestamp(self):
        all_logs = get_logs_with_timestamp(res=self.sample_res)
        timestamp_1 = datetime(year=2019, month=1, day=1, tzinfo=timezone.utc)
        timestamp_2 = datetime(year=2019, month=1, day=21, tzinfo=timezone.utc)

        self.assertIn("created flag definition", "".join(all_logs[timestamp_1]))
        self.assertNotIn("Transactions must be in GBP only.", "".join(all_logs[timestamp_1]))
        self.assertIn("Transactions must be in GBP only.", "".join(all_logs[timestamp_2]))

    def test_get_default_postings(self):
        postings = get_postings(res=self.sample_res)

        first_posting = postings[0]
        last_posting = postings[-1]

        self.assertEqual(first_posting["account_id"], "Main account")
        self.assertEqual(first_posting["account_address"], "DEFAULT")

        self.assertEqual(last_posting["account_id"], "Main account")
        self.assertEqual(last_posting["account_address"], "DEFAULT")

        postings_supervisor = get_postings(res=self.supervisor_res, account_id="Savings Account")

        first_posting = postings_supervisor[0]
        last_posting = postings_supervisor[-1]

        self.assertEqual(first_posting["account_id"], "Savings Account")
        self.assertEqual(first_posting["account_address"], "DEFAULT")

        self.assertEqual(last_posting["account_id"], "Savings Account")
        self.assertEqual(last_posting["account_address"], "DEFAULT")

    def test_get_posting_instruction_batch_at_with_one_result(self):
        account_id = "Main account"
        pibs = get_posting_instruction_batch(
            res=self.sample_res, event_type="outbound_hard_settlement"
        )

        self.assertListEqual(
            pibs[account_id].at(datetime(2019, 1, 1, tzinfo=timezone.utc)),
            [
                {
                    "asset": "",
                    "amount": "110",
                    "denomination": "GBP",
                    "target_account": {"account_id": "Main account"},
                    "internal_account_id": "1",
                    "advice": False,
                    "target_account_id": "Main account",
                    "target_account_address": "",
                    "internal_account_processing_label": "",
                }
            ],
        )

    def test_get_posting_instruction_batch_at_with_multiple_results(self):
        account_id = "Main account"
        pibs = get_posting_instruction_batch(
            res=self.sample_res, event_type="inbound_hard_settlement"
        )

        self.assertListEqual(
            pibs[account_id].at(datetime(2019, 3, 3, tzinfo=timezone.utc)),
            [
                {
                    "advice": False,
                    "asset": "",
                    "amount": "160",
                    "denomination": "GBP",
                    "target_account_id": "Main account",
                    "internal_account_id": "1",
                    "internal_account_processing_label": "",
                    "target_account": {"account_id": "Main account"},
                    "target_account_address": "",
                },
                {
                    "advice": False,
                    "asset": "",
                    "amount": "100",
                    "denomination": "GBP",
                    "target_account_id": "Main account",
                    "internal_account_id": "1",
                    "internal_account_processing_label": "",
                    "target_account": {"account_id": "Main account"},
                    "target_account_address": "",
                },
            ],
        )

    def test_get_posting_instruction_batch_latest(self):
        account_id = "Main account"
        pibs = get_posting_instruction_batch(
            res=self.sample_res, event_type="inbound_hard_settlement"
        )

        self.assertListEqual(
            pibs[account_id].latest(),
            [
                {
                    "advice": False,
                    "asset": "",
                    "amount": "160",
                    "denomination": "GBP",
                    "target_account_id": "Main account",
                    "internal_account_id": "1",
                    "internal_account_processing_label": "",
                    "target_account": {"account_id": "Main account"},
                    "target_account_address": "",
                },
                {
                    "advice": False,
                    "asset": "",
                    "amount": "100",
                    "denomination": "GBP",
                    "target_account_id": "Main account",
                    "internal_account_id": "1",
                    "internal_account_processing_label": "",
                    "target_account": {"account_id": "Main account"},
                    "target_account_address": "",
                },
            ],
        )

    def test_get_posting_instruction_batch_all(self):
        account_id = "Main account"
        pibs = get_posting_instruction_batch(
            res=self.sample_res, event_type="inbound_hard_settlement"
        )

        self.assertEqual(len(pibs[account_id].all()), 2)

    def test_get_posting_instruction_batch_before(self):
        account_id = "Main account"
        pibs = get_posting_instruction_batch(
            res=self.sample_res, event_type="inbound_hard_settlement"
        )

        self.assertEqual(
            len(pibs[account_id].before(datetime(2019, 1, 11, tzinfo=timezone.utc))), 0
        )
        self.assertEqual(
            len(pibs[account_id].before(datetime(2019, 1, 12, tzinfo=timezone.utc))), 1
        )

    def test_get_posting_instruction_batch_with_no_results(self):
        pibs = get_posting_instruction_batch(res=self.sample_res, event_type="INVALID")

        self.assertEqual(len(pibs), 0)

    def test_get_num_default_postings(self):
        num_postings = get_num_postings(
            res=self.sample_res, balance_dimensions=BalanceDimensions(address="DEFAULT")
        )
        self.assertEqual(num_postings, 5)

    def test_get_processed_scheduled_events(self):
        scheduled_events_timestamp = get_processed_scheduled_events(
            res=self.sample_res, event_id="ACCRUE_INTEREST", account_id="Main account"
        )

        self.assertEqual("2019-01-01T00:00:00Z", scheduled_events_timestamp[0])
        self.assertEqual("2019-01-02T00:00:00Z", scheduled_events_timestamp[1])
        self.assertEqual("2019-03-02T00:00:00Z", scheduled_events_timestamp[-1])

        supervised_events_timestamp = get_processed_scheduled_events(
            res=self.supervisor_res,
            event_id="PUBLISH_COMBINED_EXTRACT",
            plan_id="1",
        )

        self.assertEqual("2020-05-12T23:59:00Z", supervised_events_timestamp[0])
        self.assertEqual("2020-05-13T23:59:00Z", supervised_events_timestamp[1])
        self.assertEqual("2020-06-30T23:59:00Z", supervised_events_timestamp[-1])

    def test_get_contract_notifications(self):
        notifications = get_contract_notifications(res=self.sample_res)
        self.assertEqual(
            notifications,
            {
                "Main account": {
                    "overdraft_limit": (
                        [
                            (
                                datetime(2019, 1, 1, tzinfo=timezone.utc),
                                {
                                    "notification_type": "overdraft_limit",
                                    "resource_id": "Main account",
                                    "resource_type": "RESOURCE_ACCOUNT",
                                    "notification_details": {"exceeded": "false"},
                                },
                            ),
                            (
                                datetime(2019, 1, 11, tzinfo=timezone.utc),
                                {
                                    "notification_type": "overdraft_limit",
                                    "resource_id": "Main account",
                                    "resource_type": "RESOURCE_ACCOUNT",
                                    "notification_details": {"exceeded": "false"},
                                },
                            ),
                            (
                                datetime(2019, 1, 31, tzinfo=timezone.utc),
                                {
                                    "notification_type": "overdraft_limit",
                                    "resource_id": "Main account",
                                    "resource_type": "RESOURCE_ACCOUNT",
                                    "notification_details": {"exceeded": "false"},
                                },
                            ),
                            (
                                datetime(2019, 1, 31, tzinfo=timezone.utc),
                                {
                                    "notification_type": "overdraft_limit",
                                    "resource_id": "Main account",
                                    "resource_type": "RESOURCE_ACCOUNT",
                                    "notification_details": {"exceeded": "false"},
                                },
                            ),
                        ]
                    )
                }
            },
        )

    def test_check_account_violations_no_violations_at_provided_timestamp(self):
        account_violations, _, _ = get_violations(self.sample_res_with_violations)
        with self.assertRaises(AssertionError) as ctx:
            self.check_account_violations(
                expected_account_violations={
                    datetime(3000, 1, 1, tzinfo=timezone.utc): [
                        ExpectedAccountViolation(
                            account_violation=core_api.AccountViolation(
                                account_id="invalid account ID",
                                type=core_api.AccountViolationType.ACCOUNT_NOT_PRESENT,
                                payment_device_token="",
                                internal_account_processing_label="",
                            )
                        )
                    ],
                },
                account_violations=account_violations,
            )
        self.assertIn(
            "No account violations found at timestamp '3000-01-01 00:00:00+00:00'.\\n"
            "Expected: [AccountViolation(account_id='invalid account ID', "
            "payment_device_token='', type='ACCOUNT_VIOLATION_ACCOUNT_NOT_PRESENT', "
            "internal_account_processing_label='', sub_account_id='')] "
            "Got: None",
            str(ctx.exception),
        )

    def test_check_account_violations_no_violations_for_provided_client_transaction_id(self):
        account_violations, _, _ = get_violations(self.sample_res_with_violations)
        with self.assertRaises(AssertionError) as ctx:
            self.check_account_violations(
                expected_account_violations={
                    datetime(2019, 1, 4, tzinfo=timezone.utc): [
                        ExpectedAccountViolation(
                            account_violation=core_api.AccountViolation(
                                account_id="invalid account ID",
                                type=core_api.AccountViolationType.ACCOUNT_NOT_PRESENT,
                                payment_device_token="",
                                internal_account_processing_label="",
                            ),
                            client_transaction_id="txid",
                        )
                    ],
                },
                account_violations=account_violations,
            )
        self.assertIn(
            "No account violations for client transaction ID txid at 2019-01-04 00:00:00+00:00.\\n"
            "Expected: account_id='invalid account ID' payment_device_token='' "
            "type='ACCOUNT_VIOLATION_ACCOUNT_NOT_PRESENT' internal_account_processing_label='' "
            "sub_account_id='' "
            "Got: {'4': [AccountViolation(account_id='invalid account ID', "
            "payment_device_token='', type='ACCOUNT_VIOLATION_ACCOUNT_NOT_PRESENT', "
            "internal_account_processing_label='', sub_account_id='')]}",
            str(ctx.exception),
        )

    def test_check_account_violations_no_matching_violations_for_provided_client_transaction_id(
        self,
    ):
        account_violations, _, _ = get_violations(self.sample_res_with_violations)
        with self.assertRaises(AssertionError) as ctx:
            self.check_account_violations(
                expected_account_violations={
                    datetime(2019, 1, 4, tzinfo=timezone.utc): [
                        ExpectedAccountViolation(
                            account_violation=core_api.AccountViolation(
                                account_id="other account ID",
                                type=core_api.AccountViolationType.ACCOUNT_NOT_PRESENT,
                                payment_device_token="",
                                internal_account_processing_label="",
                            ),
                            client_transaction_id="4",
                        )
                    ],
                },
                account_violations=account_violations,
            )
        self.assertIn(
            "Expected account violation for client transaction ID 4 at 2019-01-04 00:00:00+00:00 "
            "not found.\\n"
            "Expected: account_id='other account ID' payment_device_token='' "
            "type='ACCOUNT_VIOLATION_ACCOUNT_NOT_PRESENT' internal_account_processing_label='' "
            "sub_account_id='' "
            "Got: [AccountViolation(account_id='invalid account ID', payment_device_token='', "
            "type='ACCOUNT_VIOLATION_ACCOUNT_NOT_PRESENT', "
            "internal_account_processing_label='', sub_account_id='')]",
            str(ctx.exception),
        )

    def test_check_account_violations_no_matching_violations(self):
        account_violations, _, _ = get_violations(self.sample_res_with_violations)
        with self.assertRaises(AssertionError) as ctx:
            self.check_account_violations(
                expected_account_violations={
                    datetime(2019, 1, 4, tzinfo=timezone.utc): [
                        ExpectedAccountViolation(
                            account_violation=core_api.AccountViolation(
                                account_id="other account ID",
                                type=core_api.AccountViolationType.ACCOUNT_NOT_PRESENT,
                                payment_device_token="",
                                internal_account_processing_label="",
                            ),
                        )
                    ],
                },
                account_violations=account_violations,
            )
        self.assertIn(
            "Expected account violation not found in actual account violations:\\n"
            "Expected: account_id='other account ID' payment_device_token='' "
            "type='ACCOUNT_VIOLATION_ACCOUNT_NOT_PRESENT' internal_account_processing_label='' "
            "sub_account_id='' "
            "Got: {'4': [AccountViolation(account_id='invalid account ID', "
            "payment_device_token='', type='ACCOUNT_VIOLATION_ACCOUNT_NOT_PRESENT', "
            "internal_account_processing_label='', "
            "sub_account_id='')]}",
            str(ctx.exception),
        )

    def test_check_account_violations_matching_violations(self):
        account_violations, _, _ = get_violations(self.sample_res_with_violations)

        # does not raise an exception
        self.check_account_violations(
            expected_account_violations={
                datetime(2019, 1, 4, tzinfo=timezone.utc): [
                    ExpectedAccountViolation(
                        account_violation=core_api.AccountViolation(
                            account_id="invalid account ID",
                            type=core_api.AccountViolationType.ACCOUNT_NOT_PRESENT,
                            payment_device_token="",
                            internal_account_processing_label="",
                        ),
                    )
                ],
            },
            account_violations=account_violations,
        )

    def test_check_account_violations_matching_violations_with_client_transaction_id(self):
        account_violations, _, _ = get_violations(self.sample_res_with_violations)

        # does not raise an exception
        self.check_account_violations(
            expected_account_violations={
                datetime(2019, 1, 4, tzinfo=timezone.utc): [
                    ExpectedAccountViolation(
                        account_violation=core_api.AccountViolation(
                            account_id="invalid account ID",
                            type=core_api.AccountViolationType.ACCOUNT_NOT_PRESENT,
                            payment_device_token="",
                            internal_account_processing_label="",
                        ),
                        client_transaction_id="4",
                    )
                ],
            },
            account_violations=account_violations,
        )

    def test_check_account_violations_some_matching_violations_and_some_not_matching(self):
        account_violations, _, _ = get_violations(self.sample_res_with_violations)

        with self.assertRaises(AssertionError):
            self.check_account_violations(
                expected_account_violations={
                    datetime(2019, 1, 4, tzinfo=timezone.utc): [
                        ExpectedAccountViolation(
                            account_violation=core_api.AccountViolation(
                                account_id="invalid account ID",
                                type=core_api.AccountViolationType.ACCOUNT_NOT_PRESENT,
                                payment_device_token="",
                                internal_account_processing_label="",
                            ),
                        ),
                        ExpectedAccountViolation(
                            account_violation=core_api.AccountViolation(
                                account_id="some other account ID",
                                type=core_api.AccountViolationType.ACCOUNT_NOT_PRESENT,
                                payment_device_token="",
                                internal_account_processing_label="",
                            ),
                            client_transaction_id="some ID",
                        ),
                    ],
                },
                account_violations=account_violations,
            )

    def test_check_contract_violations_no_violations_at_provided_timestamp(self):
        _, contract_violations, _ = get_violations(self.sample_res_with_violations)
        with self.assertRaises(AssertionError) as ctx:
            self.check_contract_violations(
                expected_contract_violations={
                    datetime(3000, 1, 1, tzinfo=timezone.utc): [
                        ExpectedContractViolation(
                            contract_violation=core_api.ContractViolation(
                                account_id="Main account",
                                plan_id="",
                                reason="Transactions must be in GBP only.",
                                violation_type=(
                                    core_api.ContractExecutionViolationType.WRONG_DENOMINATION
                                ),
                                type=core_api.ContractViolationType.TC_BREACH,
                            ),
                        )
                    ],
                },
                contract_violations=contract_violations,
            )
        self.assertIn(
            "No contract violations found at timestamp '3000-01-01 00:00:00+00:00'.\\n"
            "Expected: [ContractViolation(account_id='Main account', plan_id='', "
            "reason='Transactions must be in GBP only.', "
            "type='CONTRACT_VIOLATION_BREACH_TERMS_AND_CONDITIONS', "
            "violation_type='CONTRACT_EXECUTION_VIOLATION_WRONG_DENOMINATION', "
            "sub_account_id='')] "
            "Got: None",
            str(ctx.exception),
        )

    def test_check_contract_violations_no_violations_for_provided_client_transaction_id(self):
        _, contract_violations, _ = get_violations(self.sample_res_with_violations)
        with self.assertRaises(AssertionError) as ctx:
            self.check_contract_violations(
                expected_contract_violations={
                    datetime(2019, 1, 2, tzinfo=timezone.utc): [
                        ExpectedContractViolation(
                            contract_violation=core_api.ContractViolation(
                                account_id="Main account",
                                plan_id="",
                                reason="Transactions must be in GBP only.",
                                violation_type=(
                                    core_api.ContractExecutionViolationType.WRONG_DENOMINATION
                                ),
                                type=core_api.ContractViolationType.TC_BREACH,
                            ),
                            client_transaction_id="invalid",
                        )
                    ],
                },
                contract_violations=contract_violations,
            )
        self.assertIn(
            "No contract violations for client transaction ID invalid at "
            "2019-01-02 00:00:00+00:00.\\n"
            "Expected: account_id='Main account' plan_id='' "
            "reason='Transactions must be in GBP only.' "
            "type='CONTRACT_VIOLATION_BREACH_TERMS_AND_CONDITIONS' "
            "violation_type='CONTRACT_EXECUTION_VIOLATION_WRONG_DENOMINATION' "
            "sub_account_id='' "
            "Got: {'2': [ContractViolation(account_id='Main account', plan_id='', "
            "reason='Transactions must be in GBP only.', "
            "type='CONTRACT_VIOLATION_BREACH_TERMS_AND_CONDITIONS', "
            "violation_type='CONTRACT_EXECUTION_VIOLATION_WRONG_DENOMINATION', "
            "sub_account_id='')]}",
            str(ctx.exception),
        )

    def test_check_contract_violations_no_matching_violations_for_provided_client_transaction_id(
        self,
    ):
        _, contract_violations, _ = get_violations(self.sample_res_with_violations)
        with self.assertRaises(AssertionError) as ctx:
            self.check_contract_violations(
                expected_contract_violations={
                    datetime(2019, 1, 2, tzinfo=timezone.utc): [
                        ExpectedContractViolation(
                            contract_violation=core_api.ContractViolation(
                                account_id="Main account",
                                plan_id="",
                                reason="Some other reason.",
                                violation_type=(
                                    core_api.ContractExecutionViolationType.WRONG_DENOMINATION
                                ),
                                type=core_api.ContractViolationType.TC_BREACH,
                            ),
                            client_transaction_id="2",
                        )
                    ],
                },
                contract_violations=contract_violations,
            )
        self.assertIn(
            "Expected contract violation for client transaction ID 2 at 2019-01-02 00:00:00+00:00 "
            "not found.\\n"
            "Expected: account_id='Main account' plan_id='' reason='Some other reason.' "
            "type='CONTRACT_VIOLATION_BREACH_TERMS_AND_CONDITIONS' "
            "violation_type='CONTRACT_EXECUTION_VIOLATION_WRONG_DENOMINATION' "
            "sub_account_id='' "
            "Got: [ContractViolation(account_id='Main account', plan_id='', "
            "reason='Transactions must be in GBP only.', "
            "type='CONTRACT_VIOLATION_BREACH_TERMS_AND_CONDITIONS', "
            "violation_type='CONTRACT_EXECUTION_VIOLATION_WRONG_DENOMINATION', "
            "sub_account_id='')]",
            str(ctx.exception),
        )

    def test_check_contract_violations_no_matching_violations(self):
        _, contract_violations, _ = get_violations(self.sample_res_with_violations)
        with self.assertRaises(AssertionError) as ctx:
            self.check_contract_violations(
                expected_contract_violations={
                    datetime(2019, 1, 2, tzinfo=timezone.utc): [
                        ExpectedContractViolation(
                            contract_violation=core_api.ContractViolation(
                                account_id="Main account",
                                plan_id="",
                                reason="Some other reason.",
                                violation_type=(
                                    core_api.ContractExecutionViolationType.WRONG_DENOMINATION
                                ),
                                type=core_api.ContractViolationType.TC_BREACH,
                            ),
                        )
                    ],
                },
                contract_violations=contract_violations,
            )
        self.assertIn(
            "Expected contract violation not found in actual contract violations:\\n"
            "Expected: account_id='Main account' plan_id='' reason='Some other reason.' "
            "type='CONTRACT_VIOLATION_BREACH_TERMS_AND_CONDITIONS' "
            "violation_type='CONTRACT_EXECUTION_VIOLATION_WRONG_DENOMINATION' "
            "sub_account_id='' "
            "Got: {'2': [ContractViolation(account_id='Main account', plan_id='', "
            "reason='Transactions must be in GBP only.', "
            "type='CONTRACT_VIOLATION_BREACH_TERMS_AND_CONDITIONS', "
            "violation_type='CONTRACT_EXECUTION_VIOLATION_WRONG_DENOMINATION', "
            "sub_account_id='')]}",
            str(ctx.exception),
        )

    def test_check_contract_violations_matching_violations(self):
        _, contract_violations, _ = get_violations(self.sample_res_with_violations)

        # does not raise an exception
        self.check_contract_violations(
            expected_contract_violations={
                datetime(2019, 1, 2, tzinfo=timezone.utc): [
                    ExpectedContractViolation(
                        contract_violation=core_api.ContractViolation(
                            account_id="Main account",
                            plan_id="",
                            reason="Transactions must be in GBP only.",
                            violation_type=(
                                core_api.ContractExecutionViolationType.WRONG_DENOMINATION
                            ),
                            type=core_api.ContractViolationType.TC_BREACH,
                        ),
                    )
                ],
            },
            contract_violations=contract_violations,
        )

    def test_check_contract_violations_matching_violations_with_client_transaction_id(self):
        _, contract_violations, _ = get_violations(self.sample_res_with_violations)

        # does not raise an exception
        self.check_contract_violations(
            expected_contract_violations={
                datetime(2019, 1, 2, tzinfo=timezone.utc): [
                    ExpectedContractViolation(
                        contract_violation=core_api.ContractViolation(
                            account_id="Main account",
                            plan_id="",
                            reason="Transactions must be in GBP only.",
                            violation_type=(
                                core_api.ContractExecutionViolationType.WRONG_DENOMINATION
                            ),
                            type=core_api.ContractViolationType.TC_BREACH,
                        ),
                        client_transaction_id="2",
                    )
                ],
            },
            contract_violations=contract_violations,
        )

    def test_check_contract_violations_some_matching_violations_and_some_not_matching(self):
        _, contract_violations, _ = get_violations(self.sample_res_with_violations)

        with self.assertRaises(AssertionError):
            self.check_contract_violations(
                expected_contract_violations={
                    datetime(2019, 1, 2, tzinfo=timezone.utc): [
                        ExpectedContractViolation(
                            contract_violation=core_api.ContractViolation(
                                account_id="Main account",
                                plan_id="",
                                reason="Transactions must be in GBP only.",
                                violation_type=(
                                    core_api.ContractExecutionViolationType.WRONG_DENOMINATION
                                ),
                                type=core_api.ContractViolationType.TC_BREACH,
                            ),
                        ),
                        ExpectedContractViolation(
                            contract_violation=core_api.ContractViolation(
                                account_id="Main account",
                                plan_id="",
                                reason="Some other reason.",
                                violation_type=(
                                    core_api.ContractExecutionViolationType.WRONG_DENOMINATION
                                ),
                                type=core_api.ContractViolationType.TC_BREACH,
                            ),
                            client_transaction_id="some ID",
                        ),
                    ],
                },
                contract_violations=contract_violations,
            )

    def test_check_posting_violations_no_violations_for_provided_client_transaction_id(self):
        _, _, posting_violations = get_violations(self.sample_res_with_violations)
        with self.assertRaises(AssertionError) as ctx:
            self.check_posting_violations(
                expected_posting_violations={
                    datetime(2019, 1, 3, tzinfo=timezone.utc): [
                        ExpectedPostingViolation(
                            posting_violation=core_api.PostingViolation(
                                type=(
                                    core_api.PostingViolationType.CLIENT_TRANSACTION_ALREADY_EXISTS
                                ),
                            ),
                            client_transaction_id="invalid",
                        )
                    ],
                },
                posting_violations=posting_violations,
            )
        self.assertIn(
            "No posting violations for client transaction ID invalid at "
            "2019-01-03 00:00:00+00:00.\\n"
            "Expected: type='POSTING_VIOLATION_CLIENT_TRANSACTION_ALREADY_EXISTS' "
            "Got: {'1': [PostingViolation("
            "type='POSTING_VIOLATION_CLIENT_TRANSACTION_ALREADY_EXISTS')]}",
            str(ctx.exception),
        )

    def test_check_posting_violations_no_violations_at_provided_timestamp(self):
        _, _, posting_violations = get_violations(self.sample_res_with_violations)
        with self.assertRaises(AssertionError) as ctx:
            self.check_posting_violations(
                expected_posting_violations={
                    datetime(3000, 1, 1, tzinfo=timezone.utc): [
                        ExpectedPostingViolation(
                            posting_violation=core_api.PostingViolation(
                                type=(
                                    core_api.PostingViolationType.CLIENT_TRANSACTION_ALREADY_EXISTS
                                ),
                            ),
                        )
                    ],
                },
                posting_violations=posting_violations,
            )
        self.assertIn(
            "No posting violations found at timestamp '3000-01-01 00:00:00+00:00'.\\n"
            "Expected: [PostingViolation("
            "type='POSTING_VIOLATION_CLIENT_TRANSACTION_ALREADY_EXISTS')] "
            "Got: None",
            str(ctx.exception),
        )

    def test_check_posting_violations_no_matching_violations_for_provided_client_transaction_id(
        self,
    ):
        _, _, posting_violations = get_violations(self.sample_res_with_violations)
        with self.assertRaises(AssertionError) as ctx:
            violation_type = core_api.PostingViolationType.CLIENT_TRANSACTION_INVALID_OPERATION
            self.check_posting_violations(
                expected_posting_violations={
                    datetime(2019, 1, 3, tzinfo=timezone.utc): [
                        ExpectedPostingViolation(
                            posting_violation=core_api.PostingViolation(
                                type=violation_type,
                            ),
                            client_transaction_id="1",
                        )
                    ],
                },
                posting_violations=posting_violations,
            )
        self.assertIn(
            "Expected posting violation for client transaction ID 1 at 2019-01-03 00:00:00+00:00 "
            "not found.\\n"
            "Expected: type='POSTING_VIOLATION_CLIENT_TRANSACTION_INVALID_OPERATION' "
            "Got: [PostingViolation(type='POSTING_VIOLATION_CLIENT_TRANSACTION_ALREADY_EXISTS')]",
            str(ctx.exception),
        )

    def test_check_posting_violations_no_matching_violations(self):
        _, _, posting_violations = get_violations(self.sample_res_with_violations)
        with self.assertRaises(AssertionError) as ctx:
            violation_type = core_api.PostingViolationType.CLIENT_TRANSACTION_INVALID_OPERATION
            self.check_posting_violations(
                expected_posting_violations={
                    datetime(2019, 1, 3, tzinfo=timezone.utc): [
                        ExpectedPostingViolation(
                            posting_violation=core_api.PostingViolation(
                                type=violation_type,
                            ),
                        )
                    ],
                },
                posting_violations=posting_violations,
            )
        self.assertIn(
            "Expected posting violation not found in actual posting violations:\\n"
            "Expected: type='POSTING_VIOLATION_CLIENT_TRANSACTION_INVALID_OPERATION' "
            "Got: {'1': [PostingViolation("
            "type='POSTING_VIOLATION_CLIENT_TRANSACTION_ALREADY_EXISTS')]}",
            str(ctx.exception),
        )

    def test_check_posting_violations_matching_violations(self):
        _, _, posting_violations = get_violations(self.sample_res_with_violations)

        # does not raise an exception
        self.check_posting_violations(
            expected_posting_violations={
                datetime(2019, 1, 3, tzinfo=timezone.utc): [
                    ExpectedPostingViolation(
                        posting_violation=core_api.PostingViolation(
                            type=core_api.PostingViolationType.CLIENT_TRANSACTION_ALREADY_EXISTS,
                        ),
                    )
                ],
            },
            posting_violations=posting_violations,
        )

    def test_check_posting_violations_with_some_matching_violations_and_some_not_matching(self):
        _, _, posting_violations = get_violations(self.sample_res_with_violations)

        with self.assertRaises(AssertionError):
            self.check_posting_violations(
                expected_posting_violations={
                    datetime(2019, 1, 3, tzinfo=timezone.utc): [
                        ExpectedPostingViolation(
                            posting_violation=core_api.PostingViolation(
                                type=(
                                    core_api.PostingViolationType.CLIENT_TRANSACTION_ALREADY_EXISTS
                                ),
                            ),
                        ),
                        ExpectedPostingViolation(
                            posting_violation=core_api.PostingViolation(
                                type=(
                                    core_api.PostingViolationType.CLIENT_TRANSACTION_ALREADY_EXISTS
                                ),
                            ),
                            client_transaction_id="some ID",
                        ),
                    ],
                },
                posting_violations=posting_violations,
            )

    def test_check_posting_violations_matching_violations_with_client_transaction_id(self):
        _, _, posting_violations = get_violations(self.sample_res_with_violations)

        # does not raise an exception
        self.check_posting_violations(
            expected_posting_violations={
                datetime(2019, 1, 3, tzinfo=timezone.utc): [
                    ExpectedPostingViolation(
                        posting_violation=core_api.PostingViolation(
                            type=core_api.PostingViolationType.CLIENT_TRANSACTION_ALREADY_EXISTS,
                        ),
                        client_transaction_id="1",
                    )
                ],
            },
            posting_violations=posting_violations,
        )

    def test_check_account_attributes_unmatched_account_id_account_attributes(self):
        account_attribute_values = get_account_attribute_values(self.sample_res)
        with self.assertRaises(AssertionError):
            self.check_account_attribute_values(
                expected_account_attribute_values=[
                    ExpectedAccountAttributeValue(
                        account_id="Other account",
                        attribute_name="string_attribute",
                        effective_timestamp=datetime(2019, 3, 2, 0, 1, 0, tzinfo=timezone.utc),
                        value=core_api.AttributeValue(
                            string_value=core_api.AttributeStringValue(value="string_value")
                        ),
                    )
                ],
                account_attribute_values_by_account=account_attribute_values,
            )

    def test_check_account_attributes_unmatched_effective_timestamp_account_attributes(self):
        account_attribute_values = get_account_attribute_values(self.sample_res)
        with self.assertRaises(AssertionError):
            self.check_account_attribute_values(
                expected_account_attribute_values=[
                    ExpectedAccountAttributeValue(
                        account_id="Main account",
                        attribute_name="string_attribute",
                        effective_timestamp=datetime(2026, 12, 11, 10, 9, 8, tzinfo=timezone.utc),
                        value=core_api.AttributeValue(
                            string_value=core_api.AttributeStringValue(value="string_value")
                        ),
                    )
                ],
                account_attribute_values_by_account=account_attribute_values,
            )

    def test_check_account_attributes_unmatched_attribute_name_account_attributes(self):
        account_attribute_values = get_account_attribute_values(self.sample_res)
        with self.assertRaises(AssertionError):
            self.check_account_attribute_values(
                expected_account_attribute_values=[
                    ExpectedAccountAttributeValue(
                        account_id="Main account",
                        attribute_name="non_string_attribute",
                        effective_timestamp=datetime(2019, 3, 2, 0, 1, 0, tzinfo=timezone.utc),
                        value=core_api.AttributeValue(
                            string_value=core_api.AttributeStringValue(value="string_value")
                        ),
                    )
                ],
                account_attribute_values_by_account=account_attribute_values,
            )

    def test_check_account_attributes_unmatched_attribute_value_account_attributes(self):
        account_attribute_values = get_account_attribute_values(self.sample_res)
        with self.assertRaises(AssertionError) as ctx:
            self.check_account_attribute_values(
                expected_account_attribute_values=[
                    ExpectedAccountAttributeValue(
                        account_id="Main account",
                        attribute_name="string_attribute",
                        effective_timestamp=datetime(2019, 3, 2, 0, 1, 0, tzinfo=timezone.utc),
                        value=core_api.AttributeValue(
                            string_value=core_api.AttributeStringValue(
                                value="different_string_value"
                            )
                        ),
                    )
                ],
                account_attribute_values_by_account=account_attribute_values,
            )
        self.assertIn("expected values not found", str(ctx.exception))

    def test_check_account_attributes_matching_account_attributes(self):
        account_attribute_values = get_account_attribute_values(self.sample_res)
        self.assertIsNone(
            self.check_account_attribute_values(
                expected_account_attribute_values=[
                    ExpectedAccountAttributeValue(
                        account_id="Main account",
                        attribute_name="string_attribute",
                        effective_timestamp=datetime(2019, 3, 2, 0, 1, 0, tzinfo=timezone.utc),
                        value=core_api.AttributeValue(
                            string_value=core_api.AttributeStringValue(
                                value="string_attribute_value"
                            )
                        ),
                    )
                ],
                account_attribute_values_by_account=account_attribute_values,
            )
        )

    def test_check_contract_notifications_match(self):
        notifications = get_contract_notifications(self.sample_res)
        self.assertIsNone(
            self.check_contract_notifications(
                expected_contract_notifications=[
                    ExpectedContractNotification(
                        datetime(2019, 1, 31, tzinfo=timezone.utc),
                        "overdraft_limit",
                        notification_details={"exceeded": "false"},
                        resource_id="Main account",
                        resource_type=ContractNotificationResourceType.RESOURCE_ACCOUNT,
                    )
                ],
                contract_notifications=notifications,
            )
        )

    def test_check_contract_notifications_partial_match(self):
        notifications = get_contract_notifications(self.sample_res)
        with self.assertRaises(AssertionError) as ctx:
            self.check_contract_notifications(
                expected_contract_notifications=[
                    ExpectedContractNotification(
                        timestamp=datetime(2019, 1, 31, tzinfo=timezone.utc),
                        notification_type="overdraft_limit",
                        # these details don't match
                        notification_details={"some_other_key": "some_other_value"},
                        resource_id="Main account",
                        resource_type=ContractNotificationResourceType.RESOURCE_ACCOUNT,
                    )
                ],
                contract_notifications=notifications,
            )
        self.assertIn(
            "Notification found for type and resource id but with different details: "
            "{'exceeded': 'false'}.\\nExpected {'some_other_key': 'some_other_value'}",
            str(ctx.exception),
        )

    def test_check_contract_notifications_no_match(self):
        notifications = get_contract_notifications(self.sample_res)
        with self.assertRaises(AssertionError) as ctx:
            self.check_contract_notifications(
                expected_contract_notifications=[
                    ExpectedContractNotification(
                        # wrong time so we get no match at all
                        timestamp=datetime(2019, 3, 5, minute=1, tzinfo=timezone.utc),
                        notification_type="my_notification",
                        notification_details={"some_other_key": "some_other_value"},
                        resource_id="Easy Access Saver Account",
                        resource_type=ContractNotificationResourceType.RESOURCE_ACCOUNT,
                    )
                ],
                contract_notifications=notifications,
            )
        self.assertIn(
            "No notification found for this type and resource id at 2019-03-05 00:01:00+00:00'",
            str(ctx.exception),
        )

    def test_get_posting_enrichments(self):
        enrichments = get_posting_enrichments(res=self.sample_res)
        self.assertEqual(enrichments, {"Main account": {"key": "value"}})

    def test_check_posting_enrichments_match(self):
        enrichments = get_posting_enrichments(self.sample_res)
        self.assertIsNone(
            self.check_posting_enrichments(
                expected_posting_enrichments=[
                    ExpectedPostingEnrichments(
                        account_id="Main account",
                        enrichment_details={"key": "value"},
                    )
                ],
                posting_enrichments=enrichments,
            )
        )

    def test_check_posting_enrichments_partial_match(self):
        enrichments = get_posting_enrichments(self.sample_res)
        with self.assertRaises(AssertionError) as ctx:
            self.check_posting_enrichments(
                expected_posting_enrichments=[
                    ExpectedPostingEnrichments(
                        account_id="Main account",
                        # wrong details
                        enrichment_details={"fake-key": "fake-value"},
                    )
                ],
                posting_enrichments=enrichments,
            )
        self.assertIn(
            "Mismatch for resource id 'Main account':\\nExpected: {'fake-key': 'fake-value'}\\n"
            "Actual:   {'key': 'value'}",
            str(ctx.exception),
        )

    def test_check_posting_enrichments_no_match(self):
        enrichments = get_posting_enrichments(self.sample_res)
        with self.assertRaises(AssertionError) as ctx:
            self.check_posting_enrichments(
                expected_posting_enrichments=[
                    ExpectedPostingEnrichments(
                        # wrong account id so no match at all
                        account_id="Sub account",
                        enrichment_details={"key": "value"},
                    )
                ],
                posting_enrichments=enrichments,
            )
        self.assertIn(
            "No enrichments found for resource id 'Sub account'",
            str(ctx.exception),
        )

    def test_print_json(self):
        output = sys_stdout(print_json, "debug", self.sample_res)

        self.assertIn("debug", output)
        self.assertIn("account_notes", output)
        self.assertIn("balances", output)

    def test_print_postings(self):
        output = sys_stdout(print_postings, res=self.sample_res)

        self.assertIn("account_address", output)
        self.assertNotIn("balances", output)

    def test_print_log(self):
        output = sys_stdout(print_log, res=self.sample_res)
        self.assertIn("flag", output)
        self.assertNotIn("1030", output)

    def test_run_test_scenario_no_configs(self):
        with self.assertRaises(ValueError) as ctx:
            self.run_test_scenario(
                SimulationTestScenario(
                    sub_tests=[], start=datetime(2020, 1, 1), end=datetime(2020, 1, 2)
                )
            )
        self.assertEqual(
            ctx.exception.args[0], "Test scenario must have supervisor or contract config!"
        )

    @mock.patch.object(utils, "compile_chrono_events")
    @mock.patch.object(utils, "load_file_contents")
    def test_run_test_scenario_supervisor_config_default_accounts_v1(
        self, load_file_contents_mock, compile_chrono_events_mock
    ):
        compile_chrono_events_mock.return_value = [], []
        load_file_contents_mock.side_effect = lambda x: x + "_contents"
        supervisor_config = SupervisorConfig(
            supervisor_file_path="supervisor_contract_file_path",
            supervisor_contract_version_id="supervisor_contract_version_id",
            supervisee_contracts=[
                ContractConfig(
                    clu_resource_id="contract_id_1",
                    contract_file_path="contract_file_1",
                    template_params={},
                    smart_contract_version_id="contract_id_1_version",
                    account_configs=[
                        AccountConfig(
                            account_id_base="contract_id_1_account",
                            instance_params={},
                            number_of_accounts=1,
                        )
                    ],
                ),
                ContractConfig(
                    clu_resource_id="contract_id_2",
                    contract_file_path="contract_file_2",
                    template_params={},
                    smart_contract_version_id="contract_id_2_version",
                    account_configs=[
                        AccountConfig(
                            account_id_base="contract_id_2_account",
                            instance_params={},
                            number_of_accounts=2,
                        )
                    ],
                ),
            ],
        )
        with mock.patch.object(self, "client") as client_mock:
            client_mock.simulate_smart_contract.return_value = []
            self.run_test_scenario(
                SimulationTestScenario(
                    sub_tests=[],
                    start=datetime(2020, 1, 1),
                    end=datetime(2020, 1, 2),
                    supervisor_config=supervisor_config,
                )
            )
        client_mock.simulate_smart_contract.assert_called_with(
            start_timestamp=datetime(2020, 1, 1),
            end_timestamp=datetime(2020, 1, 2),
            supervisor_contract_code="supervisor_contract_file_path_contents",
            supervisor_contract_version_id="supervisor_contract_version_id",
            supervisee_version_id_mapping={
                "contract_id_1": "contract_id_1_version",
                "contract_id_2": "contract_id_2_version",
            },
            contract_codes=["contract_file_1_contents", "contract_file_2_contents"],
            smart_contract_version_ids=["contract_id_1_version", "contract_id_2_version"],
            templates_parameters=[{}, {}],
            internal_account_ids=None,
            flag_definition_ids=None,
            calendar_ids=None,
            supervisor_contract_config=supervisor_config,
            contract_config=None,
            events=[],
            parameters=[],
            output_account_ids=[],
            output_timestamps=[],
            debug=False,
            use_v1_accounts=True,
            globally_owned_parameter_values=None,
            default_timezone=None,
        )

    @mock.patch.object(utils, "compile_chrono_events")
    @mock.patch.object(utils, "load_file_contents")
    def test_run_test_scenario_supervisor_config_explicit_accounts_v1(
        self, load_file_contents_mock, compile_chrono_events_mock
    ):
        compile_chrono_events_mock.return_value = [], []
        load_file_contents_mock.side_effect = lambda x: x + "_contents"
        supervisor_config = SupervisorConfig(
            supervisor_file_path="supervisor_contract_file_path",
            supervisor_contract_version_id="supervisor_contract_version_id",
            supervisee_contracts=[
                ContractConfig(
                    clu_resource_id="contract_id_1",
                    contract_file_path="contract_file_1",
                    template_params={},
                    smart_contract_version_id="contract_id_1_version",
                    account_configs=[
                        AccountConfig(
                            account_id_base="contract_id_1_account",
                            instance_params={},
                            number_of_accounts=1,
                        )
                    ],
                ),
                ContractConfig(
                    clu_resource_id="contract_id_2",
                    contract_file_path="contract_file_2",
                    template_params={},
                    smart_contract_version_id="contract_id_2_version",
                    account_configs=[
                        AccountConfig(
                            account_id_base="contract_id_2_account",
                            instance_params={},
                            number_of_accounts=2,
                        )
                    ],
                ),
            ],
        )
        with mock.patch.object(self, "client") as client_mock:
            client_mock.simulate_smart_contract.return_value = []
            self.run_test_scenario(
                SimulationTestScenario(
                    sub_tests=[],
                    start=datetime(2020, 1, 1),
                    end=datetime(2020, 1, 2),
                    supervisor_config=supervisor_config,
                    use_v1_accounts=True,
                )
            )
        client_mock.simulate_smart_contract.assert_called_with(
            start_timestamp=datetime(2020, 1, 1),
            end_timestamp=datetime(2020, 1, 2),
            supervisor_contract_code="supervisor_contract_file_path_contents",
            supervisor_contract_version_id="supervisor_contract_version_id",
            supervisee_version_id_mapping={
                "contract_id_1": "contract_id_1_version",
                "contract_id_2": "contract_id_2_version",
            },
            contract_codes=["contract_file_1_contents", "contract_file_2_contents"],
            smart_contract_version_ids=["contract_id_1_version", "contract_id_2_version"],
            templates_parameters=[{}, {}],
            internal_account_ids=None,
            flag_definition_ids=None,
            calendar_ids=None,
            supervisor_contract_config=supervisor_config,
            contract_config=None,
            events=[],
            parameters=[],
            output_account_ids=[],
            output_timestamps=[],
            debug=False,
            use_v1_accounts=True,
            globally_owned_parameter_values=None,
            default_timezone=None,
        )

    @mock.patch.object(utils, "compile_chrono_events")
    @mock.patch.object(utils, "load_file_contents")
    def test_run_test_scenario_supervisor_config_explicit_accounts_v2(
        self, load_file_contents_mock, compile_chrono_events_mock
    ):
        compile_chrono_events_mock.return_value = [], []
        load_file_contents_mock.side_effect = lambda x: x + "_contents"
        supervisor_config = SupervisorConfig(
            supervisor_file_path="supervisor_contract_file_path",
            supervisor_contract_version_id="supervisor_contract_version_id",
            supervisee_contracts=[
                ContractConfig(
                    clu_resource_id="contract_id_1",
                    contract_file_path="contract_file_1",
                    template_params={},
                    smart_contract_version_id="contract_id_1_version",
                    account_configs=[
                        AccountConfig(
                            account_id_base="contract_id_1_account",
                            instance_params={},
                            number_of_accounts=1,
                        )
                    ],
                ),
                ContractConfig(
                    clu_resource_id="contract_id_2",
                    contract_file_path="contract_file_2",
                    template_params={},
                    smart_contract_version_id="contract_id_2_version",
                    account_configs=[
                        AccountConfig(
                            account_id_base="contract_id_2_account",
                            instance_params={},
                            number_of_accounts=2,
                        )
                    ],
                ),
            ],
        )
        with mock.patch.object(self, "client") as client_mock:
            client_mock.simulate_smart_contract.return_value = []
            self.run_test_scenario(
                SimulationTestScenario(
                    sub_tests=[],
                    start=datetime(2020, 1, 1),
                    end=datetime(2020, 1, 2),
                    supervisor_config=supervisor_config,
                    use_v1_accounts=False,
                )
            )
        client_mock.simulate_smart_contract.assert_called_with(
            start_timestamp=datetime(2020, 1, 1),
            end_timestamp=datetime(2020, 1, 2),
            supervisor_contract_code="supervisor_contract_file_path_contents",
            supervisor_contract_version_id="supervisor_contract_version_id",
            supervisee_version_id_mapping={
                "contract_id_1": "contract_id_1_version",
                "contract_id_2": "contract_id_2_version",
            },
            contract_codes=["contract_file_1_contents", "contract_file_2_contents"],
            smart_contract_version_ids=["contract_id_1_version", "contract_id_2_version"],
            templates_parameters=[{}, {}],
            internal_account_ids=None,
            flag_definition_ids=None,
            calendar_ids=None,
            supervisor_contract_config=supervisor_config,
            contract_config=None,
            events=[],
            parameters=[],
            output_account_ids=[],
            output_timestamps=[],
            debug=False,
            use_v1_accounts=False,
            globally_owned_parameter_values=None,
            default_timezone=None,
        )


def sys_stdout(func, *args, **kwargs):
    with patch("sys.stdout", new=io.StringIO()) as sys_out:
        func(*args, **kwargs)
        return sys_out.getvalue()


class TestGetContractContents(TestCase):
    def test_get_prepopulated_contract_content(self):
        test_content = "some_content"
        contract_configs = [
            ContractConfig(template_params={}, account_configs=[], contract_content=test_content)
        ]
        contents = get_contract_contents(contract_configs)
        self.assertEqual(contents, [test_content])

    @patch("inception_sdk.test_framework.contracts.simulation.utils.load_file_contents")
    def test_get_file_contract_content(self, mock_load_file_contents_method: Mock):
        test_content = "some_content"
        mock_load_file_contents_method.return_value = test_content

        contract_configs = [
            ContractConfig(template_params={}, account_configs=[], contract_file_path="some_path")
        ]
        contents = get_contract_contents(contract_configs)
        self.assertEqual(contents, [test_content])


class TestDataObjects(TestCase):
    def test_contract_config_must_have_at_least_one_source(self):
        with self.assertRaises(ValueError) as e:
            ContractConfig(template_params={}, account_configs=[])

        self.assertEqual(
            str(e.exception),
            "Neither contract_file_path or contract_content has been provided.",
        )

    def test_create_supervisor_config(self):
        supervisee_1 = SuperviseeConfig(
            contract_id="contract_id_1",
            contract_file="contract_file_1",
            account_name="Account 1",
            version="1",
            instance_parameters={"a": "1"},
            template_parameters={"b": "2"},
            instances=3,
        )

        supervisee_2 = SuperviseeConfig(
            contract_id="contract_id_2",
            contract_file="contract_file_2",
            account_name="Account 1",
            version="2",
            instance_parameters={"c": "3"},
            template_parameters={"d": "4"},
            instances=4,
        )

        supervisor_contract = "supervisor_contract"
        supervisor_contract_version_id = "supervisor_contract_version_id"

        supervisor_config = create_supervisor_config(
            supervisor_contract=supervisor_contract,
            supervisor_contract_version_id=supervisor_contract_version_id,
            supervisees=[supervisee_1, supervisee_2],
        )

        # check supervisor config
        self.assertIsInstance(supervisor_config, SupervisorConfig)

        self.assertEqual(supervisor_config.supervisor_file_path, supervisor_contract)
        self.assertEqual(
            supervisor_config.supervisor_contract_version_id,
            supervisor_contract_version_id,
        )

        # check supervisee contracts
        self.assertEqual(len(supervisor_config.supervisee_contracts), 2)

        # check supervisee contract configs
        expected_supervisee_contracts = [supervisee_1, supervisee_2]
        for i, supervisee_contract in enumerate(supervisor_config.supervisee_contracts):
            self.assertEqual(
                supervisee_contract.clu_resource_id, expected_supervisee_contracts[i].contract_id
            )
            self.assertEqual(
                supervisee_contract.contract_file_path,
                expected_supervisee_contracts[i].contract_file,
            )
            self.assertDictEqual(
                supervisee_contract.template_params,
                expected_supervisee_contracts[i].template_parameters,
            )
            self.assertEqual(
                supervisee_contract.smart_contract_version_id,
                expected_supervisee_contracts[i].version,
            )
            self.assertEqual(len(supervisee_contract.account_configs), 1)

            supervisee_contract_account = supervisee_contract.account_configs[0]
            self.assertEqual(
                supervisee_contract_account.account_id_base,
                f"{expected_supervisee_contracts[i].account_name} ",
            )
            self.assertDictEqual(
                supervisee_contract_account.instance_params,
                expected_supervisee_contracts[i].instance_parameters,
            )
            self.assertEqual(
                supervisee_contract_account.number_of_accounts,
                expected_supervisee_contracts[i].instances,
            )
