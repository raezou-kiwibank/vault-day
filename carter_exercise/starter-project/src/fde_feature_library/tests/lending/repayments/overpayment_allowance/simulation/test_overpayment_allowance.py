# Copyright @ 2026 Thought Machine Group Limited. All rights reserved.
# standard libs
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

# third party
import pytest
from dateutil.relativedelta import relativedelta

import feature_library.lending.repayments.overpayment as overpayment
import feature_library.lending.repayments.overpayment_allowance as overpayment_allowance

# inception sdk
from inception_sdk.test_framework.contracts.simulation.data_objects.data_objects import (
    AccountConfig,
    ContractConfig,
    ExpectedSchedule,
    SimulationEvent,
    SimulationTestScenario,
    SubTest,
)
from inception_sdk.test_framework.contracts.simulation.helper import (
    create_inbound_hard_settlement_posting_instruction_event,
    v2_update_account_status,
)
from inception_sdk.test_framework.contracts.simulation.utils import SimulationTestCase
from inception_sdk.vault.core_api import AccountV2Status, DecimalParameterValue

# simulation
import tests.lending.repayments.overpayment_allowance.simulation.accounts as accounts
import tests.lending.repayments.overpayment_allowance.simulation.dimensions as dimensions
import tests.lending.repayments.overpayment_allowance.simulation.parameters as parameters
from tests.common.test_denomination import DEFAULT_DENOMINATION

CONTRACT = str(
    Path(
        "tests/lending/repayments/overpayment_allowance/simulation/overpayment_allowance_smart_contract.py"
    )
)
UTC = ZoneInfo("UTC")


class OverpaymentAllowanceSimulationTest(SimulationTestCase):
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
class TestOverpaymentAllowance(OverpaymentAllowanceSimulationTest):
    contract_filepaths = [CONTRACT]

    @pytest.mark.sim
    def test_overpayment_allowance_initialisation_and_reduction(self):
        """Scenario: Initialisation on activation and reduction on overpayment"""
        start = self.default_simulation_start_datetime
        disbursal_ts = start + relativedelta(minutes=1)
        repayment_ts = start + relativedelta(days=1)
        end = start + relativedelta(days=2)

        sub_tests = [
            SubTest(
                description="Initialisation on activation",
                expected_balances_at_ts={
                    start + relativedelta(seconds=1): {
                        accounts.CUSTOMER_ACCOUNT: [
                            # Initial principal used was 1000, percentage 0.10 => 100 allowance
                            (dimensions.REMAINING_OVERPAYMENT_ALLOWANCE_TRACKER, Decimal("100")),
                            (dimensions.PRINCIPAL, Decimal("1000")),
                        ],
                    }
                },
            ),
            SubTest(
                description="Reduce allowance on overpayment",
                events=[
                    create_inbound_hard_settlement_posting_instruction_event(
                        amount="50",
                        event_datetime=repayment_ts,
                        target_account_id=accounts.CUSTOMER_ACCOUNT,
                        internal_account_id=accounts.INTERNAL_ACCOUNT,
                        denomination=DEFAULT_DENOMINATION,
                    )
                ],
                expected_balances_at_ts={
                    repayment_ts: {
                        accounts.CUSTOMER_ACCOUNT: [
                            # Allowance reduced by 50 => 100 - 50 = 50
                            (dimensions.REMAINING_OVERPAYMENT_ALLOWANCE_TRACKER, Decimal("50")),
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
            parameter_values=parameters.parameter_values,
        )
        self.run_test_scenario(test_scenario)

    @pytest.mark.sim
    def test_overpayment_allowance_early_repayment_fee(self):
        """Scenario: Early repayment fee calculation beyond allowance"""
        start = self.default_simulation_start_datetime
        # Disburse some principal first so we have debt
        disbursal_ts = start + relativedelta(hours=1)
        repayment_ts = start + relativedelta(days=1)
        end = start + relativedelta(days=2)

        sub_tests = [
            SubTest(
                description="Process early repayment with fee",
                events=[
                    create_inbound_hard_settlement_posting_instruction_event(
                        amount="500",
                        event_datetime=repayment_ts,
                        target_account_id=accounts.CUSTOMER_ACCOUNT,
                        internal_account_id=accounts.INTERNAL_ACCOUNT,
                        denomination=DEFAULT_DENOMINATION,
                        instruction_details={"type": "EARLY_REPAYMENT"},
                    )
                ],
                expected_balances_at_ts={
                    repayment_ts: {
                        accounts.CUSTOMER_ACCOUNT: [
                            # Total Debt = 1000. Due = 0.
                            # Overpayment needed to repay = 1000.
                            # Remaining Allowance Tracker = 100.
                            # Inflight Allowance = 100 - 1000 = -900.
                            # Exceeded = 900.
                            # Fee = 900 * 0.05 = 45.
                            (dimensions.PENALTIES, Decimal("45")),
                        ],
                        accounts.OVERPAYMENT_ALLOWANCE_FEE_INCOME_ACCOUNT: [
                            (dimensions.OVERPAYMENT_ALLOWANCE_FEE_INCOME, Decimal("45")),
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
            parameter_values=parameters.parameter_values,
        )
        self.run_test_scenario(test_scenario)

    @pytest.mark.sim
    def test_overpayment_allowance_scheduled_reset_and_usage_fee(self):
        """Scenario: Annual reset and usage fee charging"""
        start = self.default_simulation_start_datetime
        # Disburse 1000 principal
        disbursal_ts = start + relativedelta(hours=1)
        # Use 150 allowance (exceeding initial 100)
        overpayment_ts = start + relativedelta(days=1, hours=1)
        # Anniversary is 2027-01-01 00:00:00 (since activation is at 2026-01-01 00:00:00 and 1y is added)
        anniversary_ts = datetime(2027, 1, 1, 0, 0, 0, tzinfo=UTC)
        end = anniversary_ts + relativedelta(hours=1)

        sub_tests = [
            SubTest(
                description="Setup account and use allowance",
                events=[
                    create_inbound_hard_settlement_posting_instruction_event(
                        amount="150",
                        event_datetime=overpayment_ts,
                        target_account_id=accounts.CUSTOMER_ACCOUNT,
                        internal_account_id=accounts.INTERNAL_ACCOUNT,
                        denomination=DEFAULT_DENOMINATION,
                    ),
                ],
                expected_balances_at_ts={
                    overpayment_ts: {
                        accounts.CUSTOMER_ACCOUNT: [
                            (dimensions.PRINCIPAL, Decimal("850")),
                            (dimensions.PENALTIES, Decimal("0")),
                            (dimensions.REMAINING_OVERPAYMENT_ALLOWANCE_TRACKER, Decimal("-50")),
                        ],
                    }
                },
            ),
            SubTest(
                description="Anniversary reset and fee",
                expected_schedules=[
                    ExpectedSchedule(
                        run_times=[anniversary_ts],
                        event_id=overpayment_allowance.CHECK_OVERPAYMENT_ALLOWANCE_EVENT,
                        account_id=accounts.CUSTOMER_ACCOUNT,
                    )
                ],
                expected_balances_at_ts={
                    anniversary_ts: {
                        accounts.CUSTOMER_ACCOUNT: [
                            # Fee: 150 used - 100 allowance = 50 excess.
                            # 50 * 0.05 = 2.50 fee.
                            (dimensions.PENALTIES, Decimal("2.5")),
                            # Reset: Outstanding Principal was 1000 - 150 = 850.
                            # New allowance = 850 * 0.10 = 85.
                            (dimensions.REMAINING_OVERPAYMENT_ALLOWANCE_TRACKER, Decimal("85")),
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
            parameter_values=parameters.parameter_values,
        )
        self.run_test_scenario(test_scenario)

    @pytest.mark.sim
    def test_overpayment_allowance_adhoc_usage_and_status(self):
        """Scenario: Adhoc usage (conversion) and derived status"""
        start = self.default_simulation_start_datetime
        disbursal_ts = start
        # Overpay 50
        overpayment_ts = start + relativedelta(days=1)
        # Convert at day 10
        check_ts = start + relativedelta(days=10)
        end = start + relativedelta(days=11)

        sub_tests = [
            SubTest(
                description="Disburse principal",
                expected_balances_at_ts={
                    start: {
                        accounts.CUSTOMER_ACCOUNT: [
                            (dimensions.PRINCIPAL, Decimal("1000")),
                            (dimensions.REMAINING_OVERPAYMENT_ALLOWANCE_TRACKER, Decimal("100")),
                            (dimensions.OVERPAYMENT, Decimal("0")),
                        ],
                    }
                },
            ),
            SubTest(
                description="Overpay",
                events=[
                    create_inbound_hard_settlement_posting_instruction_event(
                        amount="50",
                        event_datetime=overpayment_ts,
                        target_account_id=accounts.CUSTOMER_ACCOUNT,
                        internal_account_id=accounts.INTERNAL_ACCOUNT,
                        denomination=DEFAULT_DENOMINATION,
                    )
                ],
                expected_balances_at_ts={
                    overpayment_ts: {
                        accounts.CUSTOMER_ACCOUNT: [
                            (dimensions.PRINCIPAL, Decimal("950")),
                            (dimensions.REMAINING_OVERPAYMENT_ALLOWANCE_TRACKER, Decimal("50")),
                            (dimensions.OVERPAYMENT, Decimal("50")),
                        ],
                    }
                },
            ),
            SubTest(
                description="Check attributes",
                events=[
                    SimulationEvent(
                        time=check_ts,
                        event={
                            "list_account_attribute_values": {
                                "account_ids": [accounts.CUSTOMER_ACCOUNT],
                                "attribute_names": [
                                    overpayment_allowance.OVERPAYMENT_ALLOWANCE_REMAINING_ATTR_ID,
                                    overpayment_allowance.OVERPAYMENT_ALLOWANCE_USED_ATTR_ID,
                                ],
                            }
                        },
                    ),
                ],
            ),
        ]

        test_scenario = self.get_simulation_test_scenario(
            start=start,
            end=end,
            sub_tests=sub_tests,
            contract_filepath=CONTRACT,
            parameter_values=parameters.parameter_values,
        )
        results = self.run_test_scenario(test_scenario)

        # Manually verify the attributes from the simulation results
        attribute_result = next(
            filter(lambda r: r.get("result", {}).get("account_attribute_values"), results), None
        )
        self.assertIsNotNone(attribute_result)
        attribute_values = attribute_result["result"]["account_attribute_values"][
            accounts.CUSTOMER_ACCOUNT
        ]["account_attribute_values"]

        # 100 allowance - 50 used = 50 remaining
        remaining_attr = next(
            filter(
                lambda a: (
                    a["attribute_name"]
                    == overpayment_allowance.OVERPAYMENT_ALLOWANCE_REMAINING_ATTR_ID
                ),
                attribute_values,
            )
        )
        self.assertEqual(Decimal(remaining_attr["value"]["decimal_value"]["value"]), Decimal("50"))

        used_attr = next(
            filter(
                lambda a: (
                    a["attribute_name"] == overpayment_allowance.OVERPAYMENT_ALLOWANCE_USED_ATTR_ID
                ),
                attribute_values,
            )
        )
        self.assertEqual(Decimal(used_attr["value"]["decimal_value"]["value"]), Decimal("50"))

    @pytest.mark.sim
    def test_overpayment_allowance_deactivation_cleanup(self):
        """Scenario: Deactivation cleanup of tracker balances"""
        start = self.default_simulation_start_datetime
        repayment_ts = start + relativedelta(days=1)
        # Deactivate at day 5
        deactivation_ts = start + relativedelta(days=5)
        end = deactivation_ts  # start + relativedelta(days=6)

        parameter_values = parameters.parameter_values.copy()
        parameter_values[overpayment_allowance.OVERPAYMENT_ALLOWANCE_FEE_PERCENTAGE_PARAM_ID] = (
            DecimalParameterValue(decimal_value=Decimal("0.0"))
        )
        parameter_values[overpayment.OVERPAYMENT_FEE_RATE_PARAM_ID] = DecimalParameterValue(
            decimal_value=Decimal("0.0")
        )

        sub_tests = [
            SubTest(
                description="Repay full principal",
                events=[
                    create_inbound_hard_settlement_posting_instruction_event(
                        amount="1000",
                        event_datetime=repayment_ts,
                        denomination=DEFAULT_DENOMINATION,
                        target_account_id=accounts.CUSTOMER_ACCOUNT,
                        internal_account_id=accounts.INTERNAL_ACCOUNT,
                    ),
                ],
                expected_balances_at_ts={
                    repayment_ts: {
                        accounts.CUSTOMER_ACCOUNT: [
                            (dimensions.DEFAULT, Decimal("0")),
                            (dimensions.PRINCIPAL, Decimal("0")),
                            # initial allowance was 1000 * 0.10 = 100
                            # repayment was 1000, so 1000 - 100 = 900 exceeded.
                            # Tracker balance = 100 - 1000 = -900
                            (dimensions.REMAINING_OVERPAYMENT_ALLOWANCE_TRACKER, Decimal("-900")),
                        ]
                    },
                },
            ),
            SubTest(
                description="Deactivate",
                events=[
                    v2_update_account_status(
                        timestamp=deactivation_ts,
                        account_id=accounts.CUSTOMER_ACCOUNT,
                        status=AccountV2Status.ACCOUNT_STATUS_CLOSED,
                    ),
                ],
                expected_balances_at_ts={
                    deactivation_ts: {
                        accounts.CUSTOMER_ACCOUNT: [
                            (dimensions.REMAINING_OVERPAYMENT_ALLOWANCE_TRACKER, Decimal("0")),
                            (dimensions.INTERNAL_CONTRA, Decimal("0")),
                        ]
                    },
                },
            ),
        ]

        test_scenario = self.get_simulation_test_scenario(
            start=start,
            end=end,
            sub_tests=sub_tests,
            contract_filepath=CONTRACT,
            parameter_values=parameter_values,
        )
        self.run_test_scenario(test_scenario)
