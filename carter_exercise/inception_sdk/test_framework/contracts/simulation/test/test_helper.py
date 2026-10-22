# standard libs
from datetime import datetime
from unittest import TestCase
from unittest.mock import MagicMock, Mock, patch, sentinel
from zoneinfo import ZoneInfo

# inception sdk
import inception_sdk.test_framework.contracts.simulation.helper as simulation_helper
import inception_sdk.vault.core_api as core_api
import inception_sdk.vault.sim_api.contract_sim as contract_sim
from inception_sdk.test_framework.contracts.simulation.data_objects.data_objects import (
    AccountConfig,
    ContractConfig,
    SimulationEvent,
    SimulationTestScenario,
)
from inception_sdk.vault.core_api import StringParameterValue

UTC = ZoneInfo("UTC")


class SimulationHelperTest(TestCase):
    def setUp(self):
        self.maxDiff = None

    @patch.object(simulation_helper, "create_auth_adjustment_event_common", autospec=True)
    def test_create_auth_adjustment_instruction(
        self, mock_create_auth_adjustment_event_common: MagicMock
    ):
        mock_create_auth_adjustment_event_common.return_value = SimulationEvent(
            time=sentinel.time, event={"posting_instruction_batch": sentinel.batch}
        )
        result = simulation_helper.create_auth_adjustment_instruction(
            event_datetime=sentinel.time, client_transaction_id=sentinel.tx_id
        )
        self.assertEqual(
            result,
            SimulationEvent(
                time=sentinel.time, event={"create_posting_instruction_batch": sentinel.batch}
            ),
        )
        mock_create_auth_adjustment_event_common.assert_called_once_with(
            value_datetime=sentinel.time,
            amount=None,
            replacement_amount=None,
            client_transaction_id=sentinel.tx_id,
            instruction_details=None,
            batch_details=None,
            client_batch_id="",
            pib_timestamp=None,
            booking_datetime=None,
        )

    @patch.object(simulation_helper, "create_custom_instruction_event_common", autospec=True)
    def test_create_custom_instruction(
        self, mock_create_custom_instruction_event_common: MagicMock
    ):
        mock_create_custom_instruction_event_common.return_value = SimulationEvent(
            time=sentinel.time, event={"posting_instruction_batch": sentinel.batch}
        )
        result = simulation_helper.create_custom_instruction(
            amount=sentinel.amount,
            debtor_target_account_id=sentinel.acc1,
            creditor_target_account_id=sentinel.acc2,
            debtor_target_account_address=sentinel.addr1,
            creditor_target_account_address=sentinel.addr2,
            event_datetime=sentinel.time,
        )
        self.assertEqual(
            result,
            SimulationEvent(
                time=sentinel.time, event={"create_posting_instruction_batch": sentinel.batch}
            ),
        )
        mock_create_custom_instruction_event_common.assert_called_once_with(
            amount=sentinel.amount,
            debtor_target_account_id=sentinel.acc1,
            creditor_target_account_id=sentinel.acc2,
            debtor_target_account_address=sentinel.addr1,
            creditor_target_account_address=sentinel.addr2,
            value_datetime=sentinel.time,
            client_transaction_id="",
            denomination=None,
            instruction_details=None,
            batch_details=None,
            client_batch_id="",
            pib_timestamp=None,
            booking_datetime=None,
            debtor_target_sub_account_id=None,
            creditor_target_sub_account_id=None,
        )

    @patch.object(simulation_helper, "create_inbound_authorisation_event_common", autospec=True)
    def test_create_inbound_authorisation_instruction(
        self, mock_create_inbound_authorisation_event_common: MagicMock
    ):
        mock_create_inbound_authorisation_event_common.return_value = SimulationEvent(
            time=sentinel.time, event={"posting_instruction_batch": sentinel.batch}
        )
        result = simulation_helper.create_inbound_authorisation_instruction(
            amount=sentinel.amount, event_datetime=sentinel.time
        )
        self.assertEqual(
            result,
            SimulationEvent(
                time=sentinel.time, event={"create_posting_instruction_batch": sentinel.batch}
            ),
        )
        mock_create_inbound_authorisation_event_common.assert_called_once_with(
            amount=sentinel.amount,
            value_datetime=sentinel.time,
            denomination=None,
            client_transaction_id="",
            instruction_details=None,
            batch_details=None,
            client_batch_id="",
            target_account_id=None,
            internal_account_id=None,
            pib_timestamp=None,
            booking_datetime=None,
            target_account_address=None,
            asset=None,
            target_sub_account_id=None,
        )

    @patch.object(simulation_helper, "create_inbound_authorisation_event_common", autospec=True)
    def test_create_inbound_authorisation_instruction_with_sub_account(
        self, mock_create_inbound_authorisation_event_common: MagicMock
    ):
        mock_create_inbound_authorisation_event_common.return_value = SimulationEvent(
            time=sentinel.time, event={"posting_instruction_batch": sentinel.batch}
        )
        result = simulation_helper.create_inbound_authorisation_instruction(
            amount=sentinel.amount,
            event_datetime=sentinel.time,
            target_sub_account_id=sentinel.sub_account_id,
        )
        self.assertEqual(
            result,
            SimulationEvent(
                time=sentinel.time, event={"create_posting_instruction_batch": sentinel.batch}
            ),
        )
        mock_create_inbound_authorisation_event_common.assert_called_once_with(
            amount=sentinel.amount,
            value_datetime=sentinel.time,
            denomination=None,
            client_transaction_id="",
            instruction_details=None,
            batch_details=None,
            client_batch_id="",
            target_account_id=None,
            internal_account_id=None,
            pib_timestamp=None,
            booking_datetime=None,
            target_account_address=None,
            asset=None,
            target_sub_account_id=sentinel.sub_account_id,
        )

    @patch.object(simulation_helper, "create_inbound_hard_settlement_event_common", autospec=True)
    def test_create_inbound_hard_settlement_instruction(
        self, mock_create_inbound_hard_settlement_event_common: MagicMock
    ):
        mock_create_inbound_hard_settlement_event_common.return_value = SimulationEvent(
            time=sentinel.time, event={"posting_instruction_batch": sentinel.batch}
        )
        result = simulation_helper.create_inbound_hard_settlement_instruction(
            amount=sentinel.amount, event_datetime=sentinel.time
        )
        self.assertEqual(
            result,
            SimulationEvent(
                time=sentinel.time, event={"create_posting_instruction_batch": sentinel.batch}
            ),
        )
        mock_create_inbound_hard_settlement_event_common.assert_called_once_with(
            amount=sentinel.amount,
            value_datetime=sentinel.time,
            denomination=None,
            client_transaction_id="",
            instruction_details=None,
            batch_details=None,
            client_batch_id="",
            target_account_id=None,
            internal_account_id=None,
            pib_timestamp=None,
            booking_datetime=None,
            target_account_address=None,
            asset=None,
            target_sub_account_id=None,
        )

    @patch.object(simulation_helper, "create_outbound_authorisation_event_common", autospec=True)
    def test_create_outbound_authorisation_instruction(
        self, mock_create_outbound_authorisation_event_common: MagicMock
    ):
        mock_create_outbound_authorisation_event_common.return_value = SimulationEvent(
            time=sentinel.time, event={"posting_instruction_batch": sentinel.batch}
        )
        result = simulation_helper.create_outbound_authorisation_instruction(
            amount=sentinel.amount, event_datetime=sentinel.time
        )
        self.assertEqual(
            result,
            SimulationEvent(
                time=sentinel.time, event={"create_posting_instruction_batch": sentinel.batch}
            ),
        )
        mock_create_outbound_authorisation_event_common.assert_called_once_with(
            amount=sentinel.amount,
            value_datetime=sentinel.time,
            denomination=None,
            client_transaction_id="",
            instruction_details=None,
            batch_details=None,
            client_batch_id="",
            target_account_id=None,
            internal_account_id=None,
            pib_timestamp=None,
            booking_datetime=None,
            target_account_address=None,
            asset=None,
            target_sub_account_id=None,
        )

    @patch.object(simulation_helper, "create_outbound_hard_settlement_event_common", autospec=True)
    def test_create_outbound_hard_settlement_instruction(
        self, mock_create_outbound_hard_settlement_event_common: MagicMock
    ):
        mock_create_outbound_hard_settlement_event_common.return_value = SimulationEvent(
            time=sentinel.time, event={"posting_instruction_batch": sentinel.batch}
        )
        result = simulation_helper.create_outbound_hard_settlement_instruction(
            amount=sentinel.amount, event_datetime=sentinel.time
        )
        self.assertEqual(
            result,
            SimulationEvent(
                time=sentinel.time, event={"create_posting_instruction_batch": sentinel.batch}
            ),
        )
        mock_create_outbound_hard_settlement_event_common.assert_called_once_with(
            amount=sentinel.amount,
            value_datetime=sentinel.time,
            denomination=None,
            client_transaction_id="",
            instruction_details=None,
            batch_details=None,
            client_batch_id="",
            target_account_id=None,
            internal_account_id=None,
            pib_timestamp=None,
            advice=None,
            target_account_address=None,
            asset=None,
            booking_datetime=None,
            target_sub_account_id=None,
        )

    @patch.object(simulation_helper, "create_release_event_common", autospec=True)
    def test_create_release_event(self, mock_create_release_event_common: MagicMock):
        mock_create_release_event_common.return_value = SimulationEvent(
            time=sentinel.time, event={"posting_instruction_batch": sentinel.batch}
        )
        result = simulation_helper.create_release_event(
            client_transaction_id=sentinel.tx_id, event_datetime=sentinel.time
        )
        self.assertEqual(
            result,
            SimulationEvent(
                time=sentinel.time, event={"create_posting_instruction_batch": sentinel.batch}
            ),
        )
        mock_create_release_event_common.assert_called_once_with(
            client_transaction_id=sentinel.tx_id,
            value_datetime=sentinel.time,
            instruction_details=None,
            batch_details=None,
            client_batch_id="",
            pib_timestamp=None,
            require_pre_posting_hook_execution=False,
            booking_datetime=None,
        )

    @patch.object(simulation_helper, "create_settlement_event_common", autospec=True)
    def test_create_settlement_event(self, mock_create_settlement_event_common: MagicMock):
        mock_create_settlement_event_common.return_value = SimulationEvent(
            time=sentinel.time, event={"posting_instruction_batch": sentinel.batch}
        )
        result = simulation_helper.create_settlement_event(
            amount=sentinel.amount,
            client_transaction_id=sentinel.tx_id,
            event_datetime=sentinel.time,
        )
        self.assertEqual(
            result,
            SimulationEvent(
                time=sentinel.time, event={"create_posting_instruction_batch": sentinel.batch}
            ),
        )
        mock_create_settlement_event_common.assert_called_once_with(
            amount=sentinel.amount,
            client_transaction_id=sentinel.tx_id,
            value_datetime=sentinel.time,
            instruction_details=None,
            batch_details=None,
            client_batch_id="",
            final=False,
            pib_timestamp=None,
            require_pre_posting_hook_execution=False,
            booking_datetime=None,
        )

    @patch.object(simulation_helper, "create_transfer_event_common", autospec=True)
    def test_create_transfer_instruction(self, mock_create_transfer_event_common: MagicMock):
        mock_create_transfer_event_common.return_value = SimulationEvent(
            time=sentinel.time, event={"posting_instruction_batch": sentinel.batch}
        )
        result = simulation_helper.create_transfer_instruction(
            amount=sentinel.amount,
            event_datetime=sentinel.time,
            creditor_target_account_id=sentinel.acc1,
            debtor_target_account_id=sentinel.acc2,
        )
        self.assertEqual(
            result,
            SimulationEvent(
                time=sentinel.time, event={"create_posting_instruction_batch": sentinel.batch}
            ),
        )
        mock_create_transfer_event_common.assert_called_once_with(
            amount=sentinel.amount,
            value_datetime=sentinel.time,
            creditor_target_account_id=sentinel.acc1,
            debtor_target_account_id=sentinel.acc2,
            denomination="",
            client_transaction_id="",
            instruction_details=None,
            batch_details=None,
            client_batch_id="",
            pib_timestamp=None,
            booking_datetime=None,
            debtor_target_sub_account_id=None,
            creditor_target_sub_account_id=None,
            debtor_target_account_address=None,
            creditor_target_account_address=None,
        )

    @patch.object(simulation_helper, "create_posting_instruction_batch_event_common", autospec=True)
    def test_create_posting_instruction_batch(
        self, mock_create_posting_instruction_batch_event_common: MagicMock
    ):
        mock_create_posting_instruction_batch_event_common.return_value = SimulationEvent(
            time=sentinel.time, event={"posting_instruction_batch": sentinel.batch}
        )
        result = simulation_helper.create_posting_instruction_batch(
            instructions=[sentinel.instr], event_datetime=sentinel.time
        )
        self.assertEqual(
            result,
            SimulationEvent(
                time=sentinel.time, event={"create_posting_instruction_batch": sentinel.batch}
            ),
        )
        mock_create_posting_instruction_batch_event_common.assert_called_once_with(
            instructions=[sentinel.instr],
            value_datetime=sentinel.time,
            client_transaction_id="",
            instruction_details=None,
            batch_details=None,
            client_batch_id="",
            pib_timestamp=None,
        )

    @patch.object(simulation_helper, "create_pib_posting_instruction_event_common", autospec=True)
    def test_create_pib_from_posting_instructions(
        self, mock_create_pib_posting_instruction_event_common: MagicMock
    ):
        mock_create_pib_posting_instruction_event_common.return_value = SimulationEvent(
            time=sentinel.time, event={"posting_instruction_batch": sentinel.batch}
        )
        result = simulation_helper.create_pib_from_posting_instructions(
            instructions=[sentinel.pi], event_datetime=sentinel.time
        )
        self.assertEqual(
            result,
            SimulationEvent(
                time=sentinel.time, event={"create_posting_instruction_batch": sentinel.batch}
            ),
        )
        mock_create_pib_posting_instruction_event_common.assert_called_once_with(
            instructions=[sentinel.pi],
            event_datetime=sentinel.time,
            batch_details=None,
            client_batch_id="",
        )

    @patch.object(simulation_helper, "create_auth_adjustment_pi_event_common", autospec=True)
    def test_create_auth_adjustment_posting_instruction_event(
        self, mock_create_auth_adjustment_pi_event_common: MagicMock
    ):
        mock_create_auth_adjustment_pi_event_common.return_value = SimulationEvent(
            time=sentinel.time, event={"posting_instruction_batch": sentinel.batch}
        )
        result = simulation_helper.create_auth_adjustment_posting_instruction_event(
            event_datetime=sentinel.time,
            client_transaction_id=sentinel.tx_id,
        )
        self.assertEqual(
            result,
            SimulationEvent(
                time=sentinel.time, event={"create_posting_instruction_batch": sentinel.batch}
            ),
        )
        mock_create_auth_adjustment_pi_event_common.assert_called_once_with(
            event_datetime=sentinel.time,
            client_transaction_id=sentinel.tx_id,
            amount=None,
            replacement_amount=None,
            advice=False,
            instruction_details=None,
            override=False,
            value_timestamp=None,
            booking_timestamp=None,
            client_id="",
            client_batch_id="",
            batch_details=None,
        )

    @patch.object(simulation_helper, "create_custom_instruction_pi_event_common", autospec=True)
    def test_create_custom_instruction_posting_instruction_event(
        self, mock_create_custom_instruction_pi_event_common: MagicMock
    ):
        mock_create_custom_instruction_pi_event_common.return_value = SimulationEvent(
            time=sentinel.time, event={"posting_instruction_batch": sentinel.batch}
        )
        result = simulation_helper.create_custom_instruction_posting_instruction_event(
            event_datetime=sentinel.time,
            amount=sentinel.amount,
            denomination=sentinel.denomination,
            debtor_target_account_id=sentinel.debtor,
            creditor_target_account_id=sentinel.creditor,
        )
        self.assertEqual(
            result,
            SimulationEvent(
                time=sentinel.time, event={"create_posting_instruction_batch": sentinel.batch}
            ),
        )
        mock_create_custom_instruction_pi_event_common.assert_called_once_with(
            event_datetime=sentinel.time,
            amount=sentinel.amount,
            denomination=sentinel.denomination,
            debtor_target_account_id=sentinel.debtor,
            creditor_target_account_id=sentinel.creditor,
            debtor_target_account_address=None,
            creditor_target_account_address=None,
            asset=None,
            phase=None,
            client_transaction_id="",
            instruction_details=None,
            override=False,
            value_timestamp=None,
            booking_timestamp=None,
            client_id="",
            client_batch_id="",
            batch_details=None,
            debtor_target_sub_account_id=None,
            creditor_target_sub_account_id=None,
        )

    @patch.object(simulation_helper, "create_inbound_authorisation_pi_event_common", autospec=True)
    def test_create_inbound_authorisation_posting_instruction_event(
        self, mock_create_inbound_authorisation_pi_event_common: MagicMock
    ):
        mock_create_inbound_authorisation_pi_event_common.return_value = SimulationEvent(
            time=sentinel.time, event={"posting_instruction_batch": sentinel.batch}
        )
        result = simulation_helper.create_inbound_authorisation_posting_instruction_event(
            event_datetime=sentinel.time,
            client_transaction_id=sentinel.tx_id,
            amount=sentinel.amount,
            denomination=sentinel.denomination,
        )
        self.assertEqual(
            result,
            SimulationEvent(
                time=sentinel.time, event={"create_posting_instruction_batch": sentinel.batch}
            ),
        )
        mock_create_inbound_authorisation_pi_event_common.assert_called_once_with(
            event_datetime=sentinel.time,
            client_transaction_id=sentinel.tx_id,
            amount=sentinel.amount,
            denomination=sentinel.denomination,
            target_account_id=None,
            internal_account_id=None,
            advice=None,
            target_account_address=None,
            asset=None,
            instruction_details=None,
            override=False,
            value_timestamp=None,
            booking_timestamp=None,
            client_id="",
            client_batch_id="",
            batch_details=None,
            target_sub_account_id=None,
        )

    @patch.object(
        simulation_helper, "create_inbound_hard_settlement_pi_event_common", autospec=True
    )
    def test_create_inbound_hard_settlement_posting_instruction_event(
        self, mock_create_inbound_hard_settlement_pi_event_common: MagicMock
    ):
        mock_create_inbound_hard_settlement_pi_event_common.return_value = SimulationEvent(
            time=sentinel.time, event={"posting_instruction_batch": sentinel.batch}
        )
        result = simulation_helper.create_inbound_hard_settlement_posting_instruction_event(
            event_datetime=sentinel.time,
            amount=sentinel.amount,
            denomination=sentinel.denomination,
        )
        self.assertEqual(
            result,
            SimulationEvent(
                time=sentinel.time, event={"create_posting_instruction_batch": sentinel.batch}
            ),
        )
        mock_create_inbound_hard_settlement_pi_event_common.assert_called_once_with(
            event_datetime=sentinel.time,
            amount=sentinel.amount,
            denomination=sentinel.denomination,
            target_account_id=None,
            internal_account_id=None,
            advice=None,
            target_account_address=None,
            asset=None,
            client_transaction_id="",
            instruction_details=None,
            override=False,
            value_timestamp=None,
            booking_timestamp=None,
            client_id="",
            client_batch_id="",
            batch_details=None,
            target_sub_account_id=None,
        )

    @patch.object(simulation_helper, "create_outbound_authorisation_pi_event_common", autospec=True)
    def test_create_outbound_authorisation_posting_instruction_event(
        self, mock_create_outbound_authorisation_pi_event_common: MagicMock
    ):
        mock_create_outbound_authorisation_pi_event_common.return_value = SimulationEvent(
            time=sentinel.time, event={"posting_instruction_batch": sentinel.batch}
        )
        result = simulation_helper.create_outbound_authorisation_posting_instruction_event(
            event_datetime=sentinel.time,
            client_transaction_id=sentinel.tx_id,
            amount=sentinel.amount,
            denomination=sentinel.denomination,
        )
        self.assertEqual(
            result,
            SimulationEvent(
                time=sentinel.time, event={"create_posting_instruction_batch": sentinel.batch}
            ),
        )
        mock_create_outbound_authorisation_pi_event_common.assert_called_once_with(
            event_datetime=sentinel.time,
            client_transaction_id=sentinel.tx_id,
            amount=sentinel.amount,
            denomination=sentinel.denomination,
            target_account_id=None,
            internal_account_id=None,
            advice=None,
            target_account_address=None,
            asset=None,
            instruction_details=None,
            override=False,
            value_timestamp=None,
            booking_timestamp=None,
            client_id="",
            client_batch_id="",
            batch_details=None,
            target_sub_account_id=None,
        )

    @patch.object(
        simulation_helper, "create_outbound_hard_settlement_pi_event_common", autospec=True
    )
    def test_create_outbound_hard_settlement_posting_instruction_event(
        self, mock_create_outbound_hard_settlement_pi_event_common: MagicMock
    ):
        mock_create_outbound_hard_settlement_pi_event_common.return_value = SimulationEvent(
            time=sentinel.time, event={"posting_instruction_batch": sentinel.batch}
        )
        result = simulation_helper.create_outbound_hard_settlement_posting_instruction_event(
            event_datetime=sentinel.time,
            amount=sentinel.amount,
            denomination=sentinel.denomination,
        )
        self.assertEqual(
            result,
            SimulationEvent(
                time=sentinel.time, event={"create_posting_instruction_batch": sentinel.batch}
            ),
        )
        mock_create_outbound_hard_settlement_pi_event_common.assert_called_once_with(
            event_datetime=sentinel.time,
            amount=sentinel.amount,
            denomination=sentinel.denomination,
            target_account_id=None,
            internal_account_id=None,
            advice=None,
            target_account_address=None,
            asset=None,
            client_transaction_id="",
            instruction_details=None,
            override=False,
            value_timestamp=None,
            booking_timestamp=None,
            client_id="",
            client_batch_id="",
            batch_details=None,
            target_sub_account_id=None,
        )

    @patch.object(simulation_helper, "create_release_pi_event_common", autospec=True)
    def test_create_release_posting_instruction_event(
        self, mock_create_release_pi_event_common: MagicMock
    ):
        mock_create_release_pi_event_common.return_value = SimulationEvent(
            time=sentinel.time, event={"posting_instruction_batch": sentinel.batch}
        )
        result = simulation_helper.create_release_posting_instruction_event(
            event_datetime=sentinel.time,
            client_transaction_id=sentinel.tx_id,
        )
        self.assertEqual(
            result,
            SimulationEvent(
                time=sentinel.time, event={"create_posting_instruction_batch": sentinel.batch}
            ),
        )
        mock_create_release_pi_event_common.assert_called_once_with(
            event_datetime=sentinel.time,
            client_transaction_id=sentinel.tx_id,
            require_pre_posting_hook_execution=False,
            instruction_details=None,
            override=False,
            value_timestamp=None,
            booking_timestamp=None,
            client_id="",
            client_batch_id="",
            batch_details=None,
        )

    @patch.object(simulation_helper, "create_settlement_pi_event_common", autospec=True)
    def test_create_settlement_posting_instruction_event(
        self, mock_create_settlement_pi_event_common: MagicMock
    ):
        mock_create_settlement_pi_event_common.return_value = SimulationEvent(
            time=sentinel.time, event={"posting_instruction_batch": sentinel.batch}
        )
        result = simulation_helper.create_settlement_posting_instruction_event(
            event_datetime=sentinel.time,
            client_transaction_id=sentinel.tx_id,
            amount=sentinel.amount,
        )
        self.assertEqual(
            result,
            SimulationEvent(
                time=sentinel.time, event={"create_posting_instruction_batch": sentinel.batch}
            ),
        )
        mock_create_settlement_pi_event_common.assert_called_once_with(
            event_datetime=sentinel.time,
            client_transaction_id=sentinel.tx_id,
            amount=sentinel.amount,
            final=False,
            require_pre_posting_hook_execution=False,
            instruction_details=None,
            override=False,
            value_timestamp=None,
            booking_timestamp=None,
            client_id="",
            client_batch_id="",
            batch_details=None,
        )

    @patch.object(simulation_helper, "create_transfer_pi_event_common", autospec=True)
    def test_create_transfer_posting_instruction_event(
        self, mock_create_transfer_pi_event_common: MagicMock
    ):
        mock_create_transfer_pi_event_common.return_value = SimulationEvent(
            time=sentinel.time, event={"posting_instruction_batch": sentinel.batch}
        )
        result = simulation_helper.create_transfer_posting_instruction_event(
            event_datetime=sentinel.time,
            amount=sentinel.amount,
            denomination=sentinel.denomination,
            debtor_target_account_id=sentinel.debtor,
            creditor_target_account_id=sentinel.creditor,
        )
        self.assertEqual(
            result,
            SimulationEvent(
                time=sentinel.time, event={"create_posting_instruction_batch": sentinel.batch}
            ),
        )
        mock_create_transfer_pi_event_common.assert_called_once_with(
            event_datetime=sentinel.time,
            amount=sentinel.amount,
            denomination=sentinel.denomination,
            debtor_target_account_id=sentinel.debtor,
            creditor_target_account_id=sentinel.creditor,
            client_transaction_id="",
            instruction_details=None,
            override=False,
            value_timestamp=None,
            booking_timestamp=None,
            client_id="",
            client_batch_id="",
            batch_details=None,
            debtor_target_sub_account_id=None,
            creditor_target_sub_account_id=None,
            debtor_target_account_address=None,
            creditor_target_account_address=None,
        )

    def test_create_parameter(self):
        timestamp = datetime(2026, 1, 1, tzinfo=UTC)
        parameter = core_api.ParameterResource(
            id="&{clu_param_id}",
            constraint=core_api.StringConstraint(
                string_constraint=core_api.StringConstraintValue()
            ),
        )
        result = simulation_helper.create_parameter(timestamp, parameter)

        self.assertEqual(
            result,
            SimulationEvent(
                time=timestamp,
                event=dict(
                    create_parameter=dict(
                        id="clu_param_id",
                        constraint=dict(
                            string_constraint=dict(
                                min_length=0,
                                max_length=0,
                            )
                        ),
                        metadata=None,
                    )
                ),
            ),
        )

    def test_create_parameter_value(self):
        timestamp = datetime(2026, 1, 1, tzinfo=UTC)
        cancel_timestamp = datetime(2026, 1, 2, tzinfo=UTC)
        parameter_value = contract_sim.CreateParameterValue(
            id="some_param_val_id",
            parameter_id="&{clu_param_id}",
            value=core_api.StringParameterValue(string_value="some_value"),
            effective_from_timestamp=timestamp,
            cancel_timestamp=cancel_timestamp,
            is_backdated=True,
            account_id="some_account_id",
        )
        result = simulation_helper.create_parameter_value(timestamp, parameter_value)
        expected_result = SimulationEvent(
            time=timestamp,
            event=dict(
                create_parameter_value={
                    "parameter_id": "clu_param_id",
                    "value": dict(
                        string_value="some_value",
                    ),
                    "effective_from_timestamp": "2026-01-01T00:00:00+00:00",
                    "cancel_timestamp": "2026-01-02T00:00:00+00:00",
                    "is_backdated": True,
                    "account_id": "some_account_id",
                    # "global" is a Python keyword so this dict is a literal.
                    "global": None,
                    "parameter_value_hierarchy_node_id": None,
                    "id": "some_param_val_id",
                }
            ),
        )
        self.assertEqual(result, expected_result)

    def test_create_parameter_value_with_hierarchy_node(self):
        timestamp = datetime(2026, 1, 1, tzinfo=UTC)
        parameter_value = contract_sim.CreateParameterValue(
            parameter_id="&{clu_param_id}",
            value=core_api.StringParameterValue(string_value="some_value"),
            effective_from_timestamp=timestamp,
            parameter_value_hierarchy_node_id="some_node_id",
        )
        result = simulation_helper.create_parameter_value(timestamp, parameter_value)
        expected_result = SimulationEvent(
            time=timestamp,
            event=dict(
                create_parameter_value={
                    "parameter_id": "clu_param_id",
                    "value": dict(
                        string_value="some_value",
                    ),
                    "effective_from_timestamp": "2026-01-01T00:00:00+00:00",
                    "cancel_timestamp": None,
                    "is_backdated": False,
                    "account_id": None,
                    # "global" is a Python keyword so this dict is a literal.
                    "global": None,
                    "parameter_value_hierarchy_node_id": "some_node_id",
                    "id": None,
                }
            ),
        )
        self.assertEqual(result, expected_result)

    def test_update_parameter_value(self):
        timestamp = datetime(2026, 1, 1, tzinfo=UTC)
        update_param_val = contract_sim.UpdateParameterValue(
            parameter_value=core_api.UpdateParameterValueV1ParameterValue(
                id="param_val_id",
                is_cancelled=True,
            ),
            update_mask=core_api.UpdateMask(paths=["is_cancelled"]),
        )
        result = simulation_helper.update_parameter_value(timestamp, update_param_val)
        self.assertEqual(
            result,
            SimulationEvent(
                time=timestamp,
                event=dict(
                    update_parameter_value=dict(
                        parameter_value=dict(
                            id="param_val_id",
                            effective_to_timestamp=None,
                            is_cancelled=True,
                        ),
                        update_mask=dict(paths=["is_cancelled"]),
                    )
                ),
            ),
        )

    def test_batch_create_parameter_values(self):
        timestamp = datetime(2026, 1, 1, tzinfo=UTC)
        cancel_timestamp = datetime(2026, 1, 2, tzinfo=UTC)
        param_val_1 = contract_sim.CreateParameterValue(
            id="param_val_1",
            parameter_id="p1",
            value=core_api.StringParameterValue(string_value="v1"),
            effective_from_timestamp=timestamp,
            cancel_timestamp=cancel_timestamp,
            is_backdated=True,
            global_=True,
        )
        param_val_2 = contract_sim.CreateParameterValue(
            id="param_val_2",
            parameter_id="p2",
            value=core_api.StringParameterValue(string_value="v2"),
            effective_from_timestamp=timestamp,
            account_id="some_account",
        )
        param_val_3 = contract_sim.CreateParameterValue(
            id="param_val_3",
            parameter_id="p3",
            value=core_api.StringParameterValue(string_value="v3"),
            effective_from_timestamp=timestamp,
            parameter_value_hierarchy_node_id="some_node",
        )
        batch_param_val = contract_sim.BatchCreateParameterValues(
            parameter_values=[param_val_1, param_val_2, param_val_3]
        )
        result = simulation_helper.batch_create_parameter_values(timestamp, batch_param_val)

        self.assertEqual(
            result,
            SimulationEvent(
                time=timestamp,
                event=dict(
                    batch_create_parameter_values=dict(
                        parameter_values=[
                            {
                                "parameter_id": "p1",
                                "value": dict(string_value="v1"),
                                "effective_from_timestamp": "2026-01-01T00:00:00+00:00",
                                "cancel_timestamp": "2026-01-02T00:00:00+00:00",
                                "is_backdated": True,
                                "account_id": None,
                                # "global" is a Python keyword so this dict is a literal.
                                "global": True,
                                "parameter_value_hierarchy_node_id": None,
                            },
                            {
                                "parameter_id": "p2",
                                "value": dict(string_value="v2"),
                                "effective_from_timestamp": "2026-01-01T00:00:00+00:00",
                                "cancel_timestamp": None,
                                "is_backdated": False,
                                "account_id": "some_account",
                                # "global" is a Python keyword so this dict is a literal.
                                "global": None,
                                "parameter_value_hierarchy_node_id": None,
                            },
                            {
                                "parameter_id": "p3",
                                "value": dict(string_value="v3"),
                                "effective_from_timestamp": "2026-01-01T00:00:00+00:00",
                                "cancel_timestamp": None,
                                "is_backdated": False,
                                "account_id": None,
                                # "global" is a Python keyword so this dict is a literal.
                                "global": None,
                                "parameter_value_hierarchy_node_id": "some_node",
                            },
                        ]
                    )
                ),
            ),
        )

    def test_create_parameter_value_hierarchy_node(self):
        timestamp = datetime(2026, 1, 1, tzinfo=UTC)
        node = contract_sim.CreateParameterValueHierarchyNode(
            parameter_value_hierarchy_node=core_api.CreateParameterValueHierarchyNode(
                id="node_id",
                name="node_name",
                parent_id="parent_node_id",
                metadata={"key": "value"},
            )
        )
        result = simulation_helper.create_parameter_value_hierarchy_node(timestamp, node)
        self.assertEqual(
            result,
            SimulationEvent(
                time=timestamp,
                event=dict(
                    create_parameter_value_hierarchy_node=dict(
                        parameter_value_hierarchy_node=dict(
                            id="node_id",
                            name="node_name",
                            parent_id="parent_node_id",
                            metadata={"key": "value"},
                        )
                    )
                ),
            ),
        )

    @patch.object(simulation_helper.uuid, "uuid4")
    def test_create_parameter_resource_mapping(self, mock_uuid4):
        mock_uuid4.return_value = sentinel.uuid4
        mapping = simulation_helper.create_parameter_resource_mapping({"p1": sentinel.val1})
        self.assertEqual(
            mapping,
            {
                "p1": (sentinel.val1, str(mock_uuid4.return_value)),
            },
        )

    @patch.object(simulation_helper, "load_file_contents")
    @patch.object(simulation_helper, "randrange")
    @patch.object(simulation_helper, "create_account_instruction")
    def test_account_to_simulate_with_create_account(
        self,
        mock_create_account_instruction: MagicMock,
        mock_randrange: MagicMock,
        mock_load_file_contents: MagicMock,
    ):
        timestamp = sentinel.timestamp
        account_id = sentinel.account_id
        mock_load_file_contents.return_value = sentinel.contract_contents
        mock_randrange.return_value = 12345
        mock_create_account_instruction.return_value = sentinel.create_account_event

        # Test with create_account=True
        result = simulation_helper.account_to_simulate(
            timestamp=timestamp,
            account_id=account_id,
            instance_params=sentinel.instance_params,
        )

        self.assertEqual(
            result,
            {
                "timestamp": timestamp,
                "contract_file_contents": sentinel.contract_contents,
                "account_id": str(sentinel.account_id),
                "smart_contract_version_id": "12345",
                "instance_parameters": sentinel.instance_params,
                "template_parameters": {},
                "create_account": True,
                "event": sentinel.create_account_event,
            },
        )
        mock_create_account_instruction.assert_called_once_with(
            timestamp=timestamp,
            account_id=str(sentinel.account_id),
            product_id="12345",
            instance_param_vals=sentinel.instance_params,
        )

    @patch.object(simulation_helper, "load_file_contents")
    @patch.object(simulation_helper, "create_account_instruction")
    def test_account_to_simulate_without_create_account(
        self,
        mock_create_account_instruction: MagicMock,
        mock_load_file_contents: MagicMock,
    ):
        timestamp = sentinel.timestamp
        account_id = sentinel.account_id
        mock_load_file_contents.return_value = sentinel.contract_contents

        # Test with create_account=False and explicit contract_version_id
        result = simulation_helper.account_to_simulate(
            timestamp=timestamp,
            account_id=account_id,
            contract_version_id=sentinel.manual_id,
            create_account=False,
        )
        self.assertEqual(
            result,
            {
                "timestamp": timestamp,
                "contract_file_contents": sentinel.contract_contents,
                "account_id": str(sentinel.account_id),
                "smart_contract_version_id": sentinel.manual_id,
                "instance_parameters": {},
                "template_parameters": {},
                "create_account": False,
                "event": {},
            },
        )
        mock_create_account_instruction.assert_not_called()

    def test_create_account_instruction(self):
        timestamp = sentinel.timestamp
        result = simulation_helper.create_account_instruction(
            timestamp=timestamp,
            account_id=sentinel.acc_id,
            product_id=sentinel.prod_id,
            permitted_denominations=sentinel.permitted_denominations,
            status=core_api.AccountStatus.ACCOUNT_STATUS_OPEN,
            stakeholder_ids=sentinel.stakeholder_ids,
            instance_param_vals=sentinel.instance_param_vals,
            derived_instance_param_vals=sentinel.derived_instance_param_vals,
            details=sentinel.details,
        )
        self.assertEqual(
            result,
            SimulationEvent(
                time=timestamp,
                event={
                    "create_account": {
                        "id": sentinel.acc_id,
                        "product_version_id": sentinel.prod_id,
                        "permitted_denominations": sentinel.permitted_denominations,
                        "status": "ACCOUNT_STATUS_OPEN",
                        "stakeholder_ids": sentinel.stakeholder_ids,
                        "instance_param_vals": sentinel.instance_param_vals,
                        "derived_instance_param_vals": sentinel.derived_instance_param_vals,
                        "details": sentinel.details,
                    }
                },
            ),
        )

    def test_create_account_product_version_update_instruction(self):
        timestamp = sentinel.timestamp
        result = simulation_helper.create_account_product_version_update_instruction(
            timestamp, sentinel.acc_id, sentinel.new_prod_id
        )
        self.assertEqual(
            result,
            SimulationEvent(
                time=timestamp,
                event={
                    "create_account_update": {
                        "account_id": sentinel.acc_id,
                        "product_version_update": {"product_version_id": sentinel.new_prod_id},
                    }
                },
            ),
        )

    def test_update_account_status_pending_closure(self):
        timestamp = sentinel.timestamp
        result = simulation_helper.update_account_status_pending_closure(timestamp, sentinel.acc_id)
        self.assertEqual(
            result,
            SimulationEvent(
                time=timestamp,
                event={
                    "update_account": {
                        "id": sentinel.acc_id,
                        "status": "ACCOUNT_STATUS_PENDING_CLOSURE",
                    }
                },
            ),
        )

    def test_v2_create_account_instruction(self):
        timestamp = datetime(2021, 1, 1, tzinfo=UTC)
        account = contract_sim.CustomerAccountRequestBody(
            id="acc_id",
            smart_contract_version_id="scv_id",
            status=core_api.AccountV2Status.ACCOUNT_STATUS_OPEN,
        )
        create_options = contract_sim.CreateOptions(
            parameter_values={"&{p1}": core_api.StringParameterValue(string_value="v1")},
            sub_accounts=[
                contract_sim.CreateSubAccount(
                    sub_account=core_api.SubAccountCreateSubAccount(
                        id="sub-account-id",
                        type="sub-account-type",
                        account_id="account-id",
                        status=core_api.SubAccountStatus.SUB_ACCOUNT_STATUS_OPEN,
                    ),
                )
            ],
        )
        v2_create = contract_sim.V2CreateAccount(
            account=account,
            create_options=create_options,
        )
        result = simulation_helper.v2_create_account_instruction(timestamp, v2_create)
        self.assertEqual(
            result,
            SimulationEvent(
                time=timestamp,
                event={
                    "v2_create_account": {
                        "account": account.model_dump(),
                        "create_options": {
                            "parameter_values": {"p1": {"string_value": "v1"}},
                            "sub_accounts": [
                                {
                                    "request_id": None,
                                    "sub_account": {
                                        "id": "sub-account-id",
                                        "type": "sub-account-type",
                                        "account_id": "account-id",
                                        "status": "SUB_ACCOUNT_STATUS_OPEN",
                                        "details": None,
                                        "name": None,
                                    },
                                }
                            ],
                        },
                    }
                },
            ),
        )

    def test_v2_create_account_instruction_no_options(self):
        timestamp = datetime(2021, 1, 1, tzinfo=UTC)
        account = contract_sim.CustomerAccountRequestBody(
            id="acc_id",
            smart_contract_version_id="scv_id",
            status=core_api.AccountV2Status.ACCOUNT_STATUS_OPEN,
        )
        v2_create = contract_sim.V2CreateAccount(
            account=account,
            create_options=None,
        )
        result = simulation_helper.v2_create_account_instruction(timestamp, v2_create)
        self.assertEqual(
            result,
            SimulationEvent(
                time=timestamp,
                event={
                    "v2_create_account": {
                        "account": account.model_dump(),
                        "create_options": None,
                    }
                },
            ),
        )

    def test_create_sub_account_instruction(self):
        timestamp = datetime(2026, 1, 1, tzinfo=UTC)
        result = simulation_helper.create_sub_account_instruction(
            timestamp,
            sub_account_id="sub_acc_1",
            sub_account_type="SAVE",
            account_id="acc_1",
            status=core_api.SubAccountStatus.SUB_ACCOUNT_STATUS_OPEN,
            name="Sub-Account Name",
            details={"key": "val"},
        )
        self.assertEqual(
            result,
            SimulationEvent(
                time=timestamp,
                event={
                    "create_sub_account": {
                        "request_id": None,
                        "sub_account": {
                            "id": "sub_acc_1",
                            "type": "SAVE",
                            "account_id": "acc_1",
                            "status": "SUB_ACCOUNT_STATUS_OPEN",
                            "name": "Sub-Account Name",
                            "details": {"key": "val"},
                        },
                    }
                },
            ),
        )

    def test_v2_update_account_status(self):
        timestamp = datetime(2021, 1, 1, tzinfo=UTC)
        result = simulation_helper.v2_update_account_status(
            timestamp, "acc_id", core_api.AccountV2Status.ACCOUNT_STATUS_OPEN
        )
        self.assertEqual(
            result,
            SimulationEvent(
                time=timestamp,
                event={
                    "v2_update_account": {
                        "account": {
                            "id": "acc_id",
                            "smart_contract_version_id": None,
                            "parameter_value_hierarchy_node_id": None,
                            "status": "ACCOUNT_STATUS_OPEN",
                            "processing_label": None,
                        },
                        "update_mask": {"paths": ["status"]},
                    }
                },
            ),
        )

    def test_v2_update_account_smart_contract_version_id(self):
        timestamp = datetime(2021, 1, 1, tzinfo=UTC)
        result = simulation_helper.v2_update_account_smart_contract_version_id(
            timestamp, "acc_id", "new_scv_id"
        )
        self.assertEqual(
            result,
            SimulationEvent(
                time=timestamp,
                event={
                    "v2_update_account": {
                        "account": {
                            "id": "acc_id",
                            "smart_contract_version_id": "new_scv_id",
                            "parameter_value_hierarchy_node_id": None,
                            "status": None,
                            "processing_label": None,
                        },
                        "update_mask": {"paths": ["smart_contract_version_id"]},
                    }
                },
            ),
        )

    def test_v2_update_account_parameter_value_hierarchy_node_id(self):
        timestamp = datetime(2021, 1, 1, tzinfo=UTC)
        result = simulation_helper.v2_update_account_parameter_value_hierarchy_node_id(
            timestamp, "acc_id", "node_id"
        )
        self.assertEqual(
            result,
            SimulationEvent(
                time=timestamp,
                event={
                    "v2_update_account": {
                        "account": {
                            "id": "acc_id",
                            "smart_contract_version_id": None,
                            "parameter_value_hierarchy_node_id": "node_id",
                            "status": None,
                            "processing_label": None,
                        },
                        "update_mask": {"paths": ["parameter_value_hierarchy_node_id"]},
                    }
                },
            ),
        )

    def test_create_plan_instruction(self):
        timestamp = sentinel.timestamp
        result = simulation_helper.create_plan_instruction(
            timestamp, sentinel.plan_id, sentinel.sv_id
        )
        self.assertEqual(
            result,
            SimulationEvent(
                time=timestamp,
                event={
                    "create_plan": {
                        "id": sentinel.plan_id,
                        "supervisor_contract_version_id": sentinel.sv_id,
                    }
                },
            ),
        )

    def test_create_account_plan_assoc_instruction(self):
        timestamp = sentinel.timestamp
        result = simulation_helper.create_account_plan_assoc_instruction(
            timestamp, sentinel.assoc_id, sentinel.acc_id, sentinel.plan_id
        )
        self.assertEqual(
            result,
            SimulationEvent(
                time=timestamp,
                event={
                    "create_account_plan_assoc": {
                        "id": sentinel.assoc_id,
                        "account_id": sentinel.acc_id,
                        "plan_id": sentinel.plan_id,
                        "status": "ACCOUNT_PLAN_ASSOC_STATUS_ACTIVE",
                    }
                },
            ),
        )

    def test_create_flag_definition_event(self):
        timestamp = sentinel.timestamp
        result = simulation_helper.create_flag_definition_event(timestamp, sentinel.flag_def_id)
        self.assertEqual(
            result,
            SimulationEvent(
                time=timestamp,
                event={"create_flag_definition": {"id": sentinel.flag_def_id}},
            ),
        )

    def test_create_flag_event(self):
        timestamp = datetime(2021, 1, 1, tzinfo=UTC)
        result = simulation_helper.create_flag_event(
            timestamp, sentinel.flag_def_id, sentinel.acc_id
        )
        self.assertEqual(
            result,
            SimulationEvent(
                time=timestamp,
                event={
                    "create_flag": {
                        "flag_definition_id": sentinel.flag_def_id,
                        "account_id": sentinel.acc_id,
                        "effective_timestamp": "2021-01-01T00:00:00+00:00",
                        "expiry_timestamp": "",
                        "is_backdated": False,
                        "value": core_api.FlagV1FlagValue.FLAG_VALUE_ON,
                    }
                },
            ),
        )

    def test_create_calendar(self):
        timestamp = sentinel.timestamp
        result = simulation_helper.create_calendar(timestamp, sentinel.cal_id)
        self.assertEqual(
            result,
            SimulationEvent(
                time=timestamp,
                event={"create_calendar": {"id": sentinel.cal_id}},
            ),
        )

    def test_create_calendar_event(self):
        timestamp = datetime(2021, 1, 1, tzinfo=UTC)
        start = datetime(2021, 1, 1, tzinfo=UTC)
        end = datetime(2021, 1, 2, tzinfo=UTC)
        result = simulation_helper.create_calendar_event(
            timestamp, sentinel.cal_evt_id, sentinel.cal_id, start, end
        )
        self.assertEqual(
            result,
            SimulationEvent(
                time=timestamp,
                event={
                    "create_calendar_event": {
                        "id": sentinel.cal_evt_id,
                        "calendar_id": sentinel.cal_id,
                        "start_timestamp": "2021-01-01T00:00:00+00:00",
                        "end_timestamp": "2021-01-02T00:00:00+00:00",
                    }
                },
            ),
        )

    def test_create_smart_contract_module_versions_link(self):
        timestamp = sentinel.timestamp
        result = simulation_helper.create_smart_contract_module_versions_link(
            timestamp, sentinel.link_id, sentinel.scv_id, sentinel.alias_map
        )
        self.assertEqual(
            result,
            SimulationEvent(
                time=timestamp,
                event={
                    "create_smart_contract_module_versions_link": {
                        "id": sentinel.link_id,
                        "smart_contract_version_id": sentinel.scv_id,
                        "alias_to_contract_module_version_id": sentinel.alias_map,
                    }
                },
            ),
        )

    def test_create_template_parameter_change_event(self):
        test_cases = [
            {
                "description": "given smart contract version id",
                "input": {
                    "timestamp": "2021-10-11T00:00:00Z",
                    "some_template_param": "some_value",
                    "smart_contract_version_id": "12",
                },
                "expected_event": {
                    "update_smart_contract_param": {
                        "smart_contract_version_id": "12",
                        "parameter_name": "some_template_param",
                        "new_parameter_value": "some_value",
                    }
                },
            },
            {
                "description": "default smart contract version id",
                "input": {
                    "timestamp": "2021-10-11T00:00:00Z",
                    "some_template_param": "some_value",
                },
                "expected_event": {
                    "update_smart_contract_param": {
                        "smart_contract_version_id": "0",
                        "parameter_name": "some_template_param",
                        "new_parameter_value": "some_value",
                    }
                },
            },
            {
                "description": "does not allow multiple param updates in one event",
                "input": {
                    "timestamp": "2021-10-11T00:00:00Z",
                    "some_template_param": "some_value",
                    "another_template_param": "some other value",
                },
                "expected_error": "template param update can only take in one parameter per event",
            },
        ]

        for test_case in test_cases:

            if "expected_error" in test_case:
                with self.assertRaises(ValueError) as ex:

                    simulation_helper.create_template_parameter_change_event(**test_case["input"])

                    self.assertIn(
                        test_case["expected_error"],
                        str(ex.exception),
                    )
            else:
                result = simulation_helper.create_template_parameter_change_event(
                    **test_case["input"]
                )

                self.assertEqual(
                    result.time,
                    test_case["input"]["timestamp"],
                    test_case["description"],
                )
                self.assertDictEqual(
                    result.event, test_case["expected_event"], test_case["description"]
                )

    def test_update_pgtz_instruction(self):
        event_datetime = datetime(2023, 1, 1, tzinfo=ZoneInfo("UTC"))
        timezone = ZoneInfo("Europe/London")
        processing_group = "some_pg"

        result = simulation_helper.update_pgtz_instruction(
            event_datetime=event_datetime, timezone=timezone, processing_group=processing_group
        )

        expected_event = {
            "update_processing_group": {
                "processing_group": {
                    "id": "some_pg",
                    "status": None,
                    "timezone": "Europe/London",
                },
                "update_mask": {"paths": ["timezone"]},
                # TODO (TM-127875): re-enable this when it is made available in the class.
                # "minimum_observation_timestamp_update_options": None,
            }
        }
        self.assertEqual(result.time, event_datetime)
        self.assertDictEqual(result.event, expected_event)


@patch.object(simulation_helper, "create_account_instruction")
@patch.object(simulation_helper, "v2_create_account_instruction")
class GetContractSetupEventTest(TestCase):
    def test_get_contract_setup_events_v1_instance_params(
        self,
        mock_v2_create_account_instruction: MagicMock,
        mock_create_account_instruction: MagicMock,
    ):
        mock_create_account_instruction.return_value = sentinel.create_account_instruction

        account_config = AccountConfig(instance_params={"test_param": "test_value"})
        contract_config = ContractConfig(
            template_params={}, account_configs=[account_config], contract_content=""
        )
        test_scenario = SimulationTestScenario(
            sub_tests=[],
            start=Mock(),
            end=Mock(),
            contract_config=contract_config,
            use_v1_accounts=True,
        )

        # No ValueError should be raised
        res = simulation_helper.get_contract_setup_events(test_scenario=test_scenario)

        self.assertEqual(res, [sentinel.create_account_instruction])
        mock_create_account_instruction.assert_called_once()
        mock_v2_create_account_instruction.assert_not_called()

    def test_get_contract_setup_events_v1_parameter_values(
        self,
        mock_v2_create_account_instruction: MagicMock,
        mock_create_account_instruction: MagicMock,
    ):
        account_config = AccountConfig(
            parameter_values={"test_param": StringParameterValue(string_value="test_value")}
        )
        contract_config = ContractConfig(
            template_params={}, account_configs=[account_config], contract_content=""
        )
        test_scenario = SimulationTestScenario(
            sub_tests=[],
            start=Mock(),
            end=Mock(),
            contract_config=contract_config,
            use_v1_accounts=True,
        )

        with self.assertRaises(ValueError) as e:
            simulation_helper.get_contract_setup_events(test_scenario=test_scenario)

        self.assertEqual(
            str(e.exception),
            "Cannot use parameter_values with V1 accounts, use instance_params instead",
        )

    def test_get_contract_setup_events_v2_instance_params(
        self,
        mock_v2_create_account_instruction: MagicMock,
        mock_create_account_instruction: MagicMock,
    ):
        account_config = AccountConfig(
            instance_params={"test_param": "test_value"},
        )
        contract_config = ContractConfig(
            template_params={}, account_configs=[account_config], contract_content=""
        )
        test_scenario = SimulationTestScenario(
            sub_tests=[],
            start=Mock(),
            end=Mock(),
            contract_config=contract_config,
            use_v1_accounts=False,
        )

        with self.assertRaises(ValueError) as e:
            simulation_helper.get_contract_setup_events(test_scenario=test_scenario)

        self.assertEqual(
            str(e.exception),
            "Cannot use instance_params with V2 accounts, use parameter_values instead",
        )

    def test_get_contract_setup_events_v2_parameter_values(
        self,
        mock_v2_create_account_instruction: MagicMock,
        mock_create_account_instruction: MagicMock,
    ):
        mock_v2_create_account_instruction.return_value = sentinel.v2_create_account_instruction

        account_config = AccountConfig(
            parameter_values={"test_param": StringParameterValue(string_value="test_value")}
        )
        contract_config = ContractConfig(
            template_params={}, account_configs=[account_config], contract_content=""
        )
        test_scenario = SimulationTestScenario(
            sub_tests=[],
            start=Mock(),
            end=Mock(),
            contract_config=contract_config,
            use_v1_accounts=False,
        )

        # No ValueError should be raised
        res = simulation_helper.get_contract_setup_events(test_scenario=test_scenario)

        self.assertEqual(res, [sentinel.v2_create_account_instruction])

        mock_v2_create_account_instruction.assert_called_once()
        mock_create_account_instruction.assert_not_called()
