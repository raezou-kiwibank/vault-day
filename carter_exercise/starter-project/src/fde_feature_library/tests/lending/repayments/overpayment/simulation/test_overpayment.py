# Copyright @ 2026 Thought Machine Group Limited. All rights reserved.
# standard libs
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

# third party
import pytest

import feature_library.lending.addresses as lending_addresses

import inception_sdk.vault.sim_api.contract_sim as contract_sim

# inception sdk
from inception_sdk.test_framework.contracts.simulation.data_objects.data_objects import (
    AccountConfig,
    ContractConfig,
    ExpectedRejection,
    SimulationTestScenario,
    SubTest,
)
from inception_sdk.test_framework.contracts.simulation.helper import (
    create_inbound_hard_settlement_posting_instruction_event,
    create_outbound_hard_settlement_posting_instruction_event,
    create_parameter_value,
    v2_update_account_status,
)
from inception_sdk.test_framework.contracts.simulation.utils import SimulationTestCase
from inception_sdk.vault.core_api import AccountV2Status, DecimalParameterValue

# simulation
import tests.lending.repayments.overpayment.simulation.accounts as accounts
import tests.lending.repayments.overpayment.simulation.dimensions as dimensions
import tests.lending.repayments.overpayment.simulation.parameters as parameters
from tests.common.test_denomination import DEFAULT_DENOMINATION

CONTRACT = str(
    Path("tests/lending/repayments/overpayment/simulation/overpayment_smart_contract.py")
)
UTC = ZoneInfo("UTC")


class OverpaymentSimulationTest(SimulationTestCase):
    parameter_resource_dirs = [
        str(Path("src/feature_library/common/parameter_resource_defs")),
        str(Path("src/feature_library/lending/repayments/parameter_resource_defs")),
    ]
    internal_accounts = accounts.default_internal_accounts
    default_simulation_start_datetime = datetime(2026, 1, 1, tzinfo=UTC)

    def get_simulation_test_scenario(
        self,
        start,
        end,
        sub_tests,
        contract_filepath,
        parameter_values,
    ):
        contract_config = ContractConfig(
            contract_content=self.smart_contract_path_to_content[contract_filepath],
            template_params={},
            account_configs=[
                AccountConfig(
                    account_id_base=accounts.CUSTOMER_ACCOUNT,
                    parameter_values=parameter_values,
                    permitted_denominations=[DEFAULT_DENOMINATION],
                )
            ],
        )
        return SimulationTestScenario(
            start=start,
            end=end,
            sub_tests=sub_tests,
            contract_config=contract_config,
            internal_accounts=self.internal_accounts,
            use_v1_accounts=False,
        )


@pytest.mark.sim
class TestOverpayment(OverpaymentSimulationTest):
    contract_filepaths = [CONTRACT]

    @pytest.mark.sim
    def test_overpayment_handled_correctly_no_fee(self):
        """Scenario A & C: Standard overpayment with no fee (fee_rate = 0.0 or 1.0)"""
        start = self.default_simulation_start_datetime
        disbursal_ts = start
        repayment_1_ts = start.replace(day=2)
        param_change_ts = start.replace(day=3)
        repayment_2_ts = start.replace(day=4)
        end = start.replace(day=5)

        # Start with fee set to 0.0
        param_values = parameters.parameter_values.copy()
        param_values.update(
            {
                parameters.overpayment.OVERPAYMENT_FEE_RATE_PARAM_ID: DecimalParameterValue(
                    decimal_value=Decimal("0.0")
                )
            }
        )

        sub_tests = [
            SubTest(
                description="Disburse loan",
                events=[
                    create_outbound_hard_settlement_posting_instruction_event(
                        amount="1000",
                        event_datetime=disbursal_ts,
                        target_account_id=accounts.CUSTOMER_ACCOUNT,
                        internal_account_id=accounts.INTERNAL_ACCOUNT,
                        target_account_address=lending_addresses.PRINCIPAL,
                        denomination=DEFAULT_DENOMINATION,
                    ),
                ],
                expected_balances_at_ts={
                    disbursal_ts: {
                        accounts.CUSTOMER_ACCOUNT: [
                            (dimensions.PRINCIPAL, Decimal("1000")),
                        ],
                    }
                },
            ),
            SubTest(
                description="Process overpayment with 0.0 fee rate",
                events=[
                    create_inbound_hard_settlement_posting_instruction_event(
                        amount="100",
                        event_datetime=repayment_1_ts,
                        target_account_id=accounts.CUSTOMER_ACCOUNT,
                        internal_account_id=accounts.INTERNAL_ACCOUNT,
                        denomination=DEFAULT_DENOMINATION,
                    )
                ],
                expected_balances_at_ts={
                    repayment_1_ts: {
                        accounts.CUSTOMER_ACCOUNT: [
                            (dimensions.PRINCIPAL, Decimal("900")),
                            (dimensions.OVERPAYMENT, Decimal("100")),
                            (dimensions.INTERNAL_CONTRA, Decimal("-100")),
                            (dimensions.DEFAULT, Decimal("0")),
                        ],
                    }
                },
            ),
            SubTest(
                description="Update fee rate to 1.0",
                events=[
                    create_parameter_value(
                        timestamp=param_change_ts,
                        parameter_value=contract_sim.CreateParameterValue(
                            parameter_id=parameters.overpayment.OVERPAYMENT_FEE_RATE_PARAM_ID,
                            value=DecimalParameterValue(decimal_value=Decimal("1.0")),
                            account_id=accounts.CUSTOMER_ACCOUNT,
                        ),
                    )
                ],
            ),
            SubTest(
                description="Process overpayment with 1.0 fee rate (no fee should be charged)",
                events=[
                    create_inbound_hard_settlement_posting_instruction_event(
                        amount="100",
                        event_datetime=repayment_2_ts,
                        target_account_id=accounts.CUSTOMER_ACCOUNT,
                        internal_account_id=accounts.INTERNAL_ACCOUNT,
                        denomination=DEFAULT_DENOMINATION,
                    )
                ],
                expected_balances_at_ts={
                    repayment_2_ts: {
                        accounts.CUSTOMER_ACCOUNT: [
                            (dimensions.PRINCIPAL, Decimal("800")),
                            (dimensions.OVERPAYMENT, Decimal("200")),
                            (dimensions.INTERNAL_CONTRA, Decimal("-200")),
                            (dimensions.DEFAULT, Decimal("0")),
                            # Verify no penalty postings were made
                            (dimensions.PENALTIES, Decimal("0")),
                        ],
                    }
                },
            ),
        ]

        test_scenario = self.get_simulation_test_scenario(
            start=start,
            end=end,
            sub_tests=sub_tests,
            contract_filepath=CONTRACT,
            parameter_values=param_values,
        )
        self.run_test_scenario(test_scenario)

    @pytest.mark.sim
    def test_overpayment_handled_correctly_with_fee(self):
        """Scenario B: Overpayment with fee charged (fee_rate = 0.05)"""
        start = self.default_simulation_start_datetime
        disbursal_ts = start
        repayment_ts = start.replace(day=2)
        end = repayment_ts.replace(hour=1)

        param_values = parameters.parameter_values.copy()
        # Ensure rate is 5%
        param_values.update(
            {
                parameters.overpayment.OVERPAYMENT_FEE_RATE_PARAM_ID: parameters.DecimalParameterValue(
                    decimal_value=Decimal("0.05")
                )
            }
        )

        sub_tests = [
            SubTest(
                description="Disburse loan",
                events=[
                    create_outbound_hard_settlement_posting_instruction_event(
                        amount="1000",
                        event_datetime=disbursal_ts,
                        target_account_id=accounts.CUSTOMER_ACCOUNT,
                        internal_account_id=accounts.INTERNAL_ACCOUNT,
                        target_account_address=lending_addresses.PRINCIPAL,
                        denomination=DEFAULT_DENOMINATION,
                    ),
                ],
            ),
            SubTest(
                description="Process overpayment with fee",
                events=[
                    create_inbound_hard_settlement_posting_instruction_event(
                        amount="100",
                        event_datetime=repayment_ts,
                        target_account_id=accounts.CUSTOMER_ACCOUNT,
                        internal_account_id=accounts.INTERNAL_ACCOUNT,
                        denomination=DEFAULT_DENOMINATION,
                    )
                ],
                expected_balances_at_ts={
                    repayment_ts: {
                        accounts.CUSTOMER_ACCOUNT: [
                            (dimensions.PRINCIPAL, Decimal("900")),
                            (dimensions.OVERPAYMENT, Decimal("100")),
                            (dimensions.INTERNAL_CONTRA, Decimal("-100")),
                            # Fee = 100 * 0.05 = 5.00
                            # Posted to PENALTIES (debit)
                            (dimensions.PENALTIES, Decimal("5")),
                        ],
                        accounts.OVERPAYMENT_FEE_INCOME_ACCOUNT: [
                            (dimensions.OVERPAYMENT_FEE_INCOME, Decimal("5")),
                        ],
                    }
                },
            ),
        ]

        test_scenario = self.get_simulation_test_scenario(
            start=start,
            end=end,
            sub_tests=sub_tests,
            contract_filepath=CONTRACT,
            parameter_values=param_values,
        )
        self.run_test_scenario(test_scenario)

    @pytest.mark.sim
    def test_overpayment_rejected_when_greater_than_max(self):
        """Scenario D: Overpayment rejected when amount > max allowed"""
        start = self.default_simulation_start_datetime
        disbursal_ts = start
        repayment_ts = start.replace(day=2)
        end = repayment_ts.replace(hour=1)

        param_values = parameters.parameter_values.copy()

        sub_tests = [
            SubTest(
                description="Disburse loan",
                events=[
                    create_outbound_hard_settlement_posting_instruction_event(
                        amount="100",
                        event_datetime=disbursal_ts,
                        target_account_id=accounts.CUSTOMER_ACCOUNT,
                        internal_account_id=accounts.INTERNAL_ACCOUNT,
                        target_account_address=lending_addresses.PRINCIPAL,
                        denomination=DEFAULT_DENOMINATION,
                    ),
                ],
            ),
            SubTest(
                description="Attempt excessive overpayment (rejected)",
                events=[
                    create_inbound_hard_settlement_posting_instruction_event(
                        amount="200",
                        event_datetime=repayment_ts,
                        target_account_id=accounts.CUSTOMER_ACCOUNT,
                        internal_account_id=accounts.INTERNAL_ACCOUNT,
                        denomination=DEFAULT_DENOMINATION,
                    )
                ],
                # Rejection expectation
                expected_posting_rejections=[
                    ExpectedRejection(
                        timestamp=repayment_ts,
                        account_id=accounts.CUSTOMER_ACCOUNT,
                        rejection_type="AgainstTermsAndConditions",
                        rejection_reason="Cannot pay more than is owed.",
                    )
                ],
            ),
        ]

        test_scenario = self.get_simulation_test_scenario(
            start=start,
            end=end,
            sub_tests=sub_tests,
            contract_filepath=CONTRACT,
            parameter_values=param_values,
        )
        self.run_test_scenario(test_scenario)

    @pytest.mark.sim
    def test_overpayment_deactivation_cleanup(self):
        """Scenario E: Overpayment deactivation cleanup"""
        start = self.default_simulation_start_datetime
        disbursal_ts = start
        repayment_ts = start.replace(day=2)
        deactivation_ts = start.replace(day=3)
        end = deactivation_ts.replace(hour=1)

        param_values = parameters.parameter_values.copy()
        # Set fee to 0 to avoid penalties preventing account closure
        param_values.update(
            {
                parameters.overpayment.OVERPAYMENT_FEE_RATE_PARAM_ID: DecimalParameterValue(
                    decimal_value=Decimal("0.00")
                )
            }
        )

        sub_tests = [
            SubTest(
                description="Disburse loan",
                events=[
                    create_outbound_hard_settlement_posting_instruction_event(
                        amount="1000",
                        event_datetime=disbursal_ts,
                        target_account_id=accounts.CUSTOMER_ACCOUNT,
                        internal_account_id=accounts.INTERNAL_ACCOUNT,
                        target_account_address=lending_addresses.PRINCIPAL,
                        denomination=DEFAULT_DENOMINATION,
                    ),
                ],
                expected_balances_at_ts={
                    disbursal_ts: {
                        accounts.CUSTOMER_ACCOUNT: [
                            (dimensions.PRINCIPAL, Decimal("1000")),
                        ],
                    }
                },
            ),
            SubTest(
                description="Repay fully (all overpayment)",
                events=[
                    create_inbound_hard_settlement_posting_instruction_event(
                        amount="1000",
                        event_datetime=repayment_ts,
                        target_account_id=accounts.CUSTOMER_ACCOUNT,
                        internal_account_id=accounts.INTERNAL_ACCOUNT,
                        denomination=DEFAULT_DENOMINATION,
                    )
                ],
                expected_balances_at_ts={
                    repayment_ts: {
                        accounts.CUSTOMER_ACCOUNT: [
                            (dimensions.PRINCIPAL, Decimal("0")),
                            (dimensions.OVERPAYMENT, Decimal("1000")),
                            (dimensions.INTERNAL_CONTRA, Decimal("-1000")),
                        ],
                    }
                },
            ),
            SubTest(
                description="Deactivate account and cleanup",
                events=[
                    v2_update_account_status(
                        timestamp=deactivation_ts,
                        account_id=accounts.CUSTOMER_ACCOUNT,
                        status=AccountV2Status.ACCOUNT_STATUS_CLOSED,
                    )
                ],
                expected_balances_at_ts={
                    deactivation_ts: {
                        accounts.CUSTOMER_ACCOUNT: [
                            (dimensions.PRINCIPAL, Decimal("0")),
                            (dimensions.OVERPAYMENT, Decimal("0")),
                            (dimensions.INTERNAL_CONTRA, Decimal("0")),
                        ],
                    }
                },
            ),
        ]

        test_scenario = self.get_simulation_test_scenario(
            start=start,
            end=end,
            sub_tests=sub_tests,
            contract_filepath=CONTRACT,
            parameter_values=param_values,
        )
        self.run_test_scenario(test_scenario)
