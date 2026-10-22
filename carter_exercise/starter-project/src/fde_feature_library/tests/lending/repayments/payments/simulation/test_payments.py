# standard libs
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

# third party
import pytest

import feature_library.lending.addresses as lending_addresses

# inception sdk
from inception_sdk.test_framework.contracts.simulation.data_objects.data_objects import (
    AccountConfig,
    ContractConfig,
    SimulationTestScenario,
    SubTest,
)
from inception_sdk.test_framework.contracts.simulation.helper import (
    create_inbound_hard_settlement_posting_instruction_event,
    create_outbound_hard_settlement_posting_instruction_event,
)
from inception_sdk.test_framework.contracts.simulation.utils import SimulationTestCase

# simulation
import tests.lending.repayments.payments.simulation.accounts as accounts
import tests.lending.repayments.payments.simulation.dimensions as dimensions
import tests.lending.repayments.payments.simulation.parameters as parameters
from tests.common.test_denomination import DEFAULT_DENOMINATION

VERTICAL_CONTRACT = str(
    Path("tests/lending/repayments/payments/simulation/vertical_hierarchy_smart_contract.py")
)
HORIZONTAL_CONTRACT = str(
    Path("tests/lending/repayments/payments/simulation/horizontal_hierarchy_smart_contract.py")
)
CUSTOM_CALLABLE_CONTRACT = str(
    Path("tests/lending/repayments/payments/simulation/custom_callable_smart_contract.py")
)

UTC = ZoneInfo("UTC")


class PaymentsSimulationTestBase(SimulationTestCase):
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
class VerticalHierarchyPaymentsTest(PaymentsSimulationTestBase):
    contract_filepaths = [VERTICAL_CONTRACT]

    @pytest.mark.sim
    def test_vertical_hierarchy_payments(self):
        start = self.default_simulation_start_datetime
        disbursal_ts = start
        repayment_ts = start.replace(day=2)
        end = repayment_ts.replace(hour=4)

        sub_tests = [
            SubTest(
                description="Populate balances",
                events=[
                    create_outbound_hard_settlement_posting_instruction_event(
                        amount="1000",
                        event_datetime=disbursal_ts,
                        target_account_id=accounts.CUSTOMER_ACCOUNT,
                        internal_account_id=accounts.INTERNAL_ACCOUNT,
                        target_account_address=lending_addresses.PRINCIPAL,
                        denomination=DEFAULT_DENOMINATION,
                    ),
                    create_outbound_hard_settlement_posting_instruction_event(
                        amount="100",
                        event_datetime=disbursal_ts,
                        target_account_id=accounts.CUSTOMER_ACCOUNT,
                        internal_account_id=accounts.INTERNAL_ACCOUNT,
                        target_account_address=lending_addresses.PRINCIPAL_OVERDUE,
                        denomination=DEFAULT_DENOMINATION,
                    ),
                    create_outbound_hard_settlement_posting_instruction_event(
                        amount="50",
                        event_datetime=disbursal_ts,
                        target_account_id=accounts.CUSTOMER_ACCOUNT,
                        internal_account_id=accounts.INTERNAL_ACCOUNT,
                        target_account_address=lending_addresses.INTEREST_OVERDUE,
                        denomination=DEFAULT_DENOMINATION,
                    ),
                    create_outbound_hard_settlement_posting_instruction_event(
                        amount="50",
                        event_datetime=disbursal_ts,
                        target_account_id=accounts.CUSTOMER_ACCOUNT,
                        internal_account_id=accounts.INTERNAL_ACCOUNT,
                        target_account_address=lending_addresses.INTEREST_DUE,
                        denomination=DEFAULT_DENOMINATION,
                    ),
                    create_outbound_hard_settlement_posting_instruction_event(
                        amount="200",
                        event_datetime=disbursal_ts,
                        target_account_id=accounts.CUSTOMER_ACCOUNT,
                        internal_account_id=accounts.INTERNAL_ACCOUNT,
                        target_account_address=lending_addresses.PRINCIPAL_DUE,
                        denomination=DEFAULT_DENOMINATION,
                    ),
                ],
                expected_balances_at_ts={
                    disbursal_ts: {
                        accounts.CUSTOMER_ACCOUNT: [
                            (dimensions.PRINCIPAL, Decimal("1000")),
                            (dimensions.PRINCIPAL_OVERDUE, Decimal("100")),
                            (dimensions.INTEREST_OVERDUE, Decimal("50")),
                            (dimensions.INTEREST_DUE, Decimal("50")),
                            (dimensions.PRINCIPAL_DUE, Decimal("200")),
                        ],
                    }
                },
            ),
            SubTest(
                description="Underpayment (Partial Repayment)",
                events=[
                    create_inbound_hard_settlement_posting_instruction_event(
                        amount="100",  # Clears PRINCIPAL_OVERDUE (100) first
                        event_datetime=repayment_ts,
                        denomination=DEFAULT_DENOMINATION,
                        target_account_id=accounts.CUSTOMER_ACCOUNT,
                        internal_account_id=accounts.INTERNAL_ACCOUNT,
                    ),
                ],
                expected_balances_at_ts={
                    repayment_ts: {
                        accounts.CUSTOMER_ACCOUNT: [
                            (dimensions.PRINCIPAL, Decimal("1000")),
                            (dimensions.PRINCIPAL_OVERDUE, Decimal("0")),
                            (dimensions.INTEREST_OVERDUE, Decimal("50")),
                            (dimensions.PRINCIPAL_DUE, Decimal("200")),
                            (dimensions.INTEREST_DUE, Decimal("50")),
                        ],
                    }
                },
            ),
            SubTest(
                description="Exact Repayment of Remaining Due/Overdue",
                events=[
                    create_inbound_hard_settlement_posting_instruction_event(
                        amount="300",  # Clears PRINCIPAL_OVERDUE (50), INTEREST_DUE (50), PRINCIPAL_DUE (200)
                        event_datetime=repayment_ts.replace(hour=1),
                        denomination=DEFAULT_DENOMINATION,
                        target_account_id=accounts.CUSTOMER_ACCOUNT,
                        internal_account_id=accounts.INTERNAL_ACCOUNT,
                    ),
                ],
                expected_balances_at_ts={
                    repayment_ts.replace(hour=1): {
                        accounts.CUSTOMER_ACCOUNT: [
                            (dimensions.PRINCIPAL, Decimal("1000")),
                            (dimensions.INTEREST_OVERDUE, Decimal("0")),
                            (dimensions.PRINCIPAL_OVERDUE, Decimal("0")),
                            (dimensions.INTEREST_DUE, Decimal("0")),
                            (dimensions.PRINCIPAL_DUE, Decimal("0")),
                            (dimensions.OVERPAYMENT, Decimal("0")),
                        ],
                    }
                },
            ),
            SubTest(
                description="Overpayment",
                events=[
                    create_inbound_hard_settlement_posting_instruction_event(
                        amount="100",  # No due/overdue balances, goes to overpayment which clears principal
                        event_datetime=repayment_ts.replace(hour=2),
                        denomination=DEFAULT_DENOMINATION,
                        target_account_id=accounts.CUSTOMER_ACCOUNT,
                        internal_account_id=accounts.INTERNAL_ACCOUNT,
                    ),
                ],
                expected_balances_at_ts={
                    repayment_ts.replace(hour=2): {
                        accounts.CUSTOMER_ACCOUNT: [
                            (dimensions.PRINCIPAL, Decimal("900")),
                            (
                                dimensions.OVERPAYMENT,
                                Decimal("100"),
                            ),  # Tracker balance from overpayment logic
                        ],
                    }
                },
            ),
            SubTest(
                description="Early Repayment (Full Repayment)",
                events=[
                    create_inbound_hard_settlement_posting_instruction_event(
                        amount="910",  # Clears remaining principal (900) + early repayment fee (10)
                        event_datetime=repayment_ts.replace(hour=3),
                        denomination=DEFAULT_DENOMINATION,
                        target_account_id=accounts.CUSTOMER_ACCOUNT,
                        internal_account_id=accounts.INTERNAL_ACCOUNT,
                    ),
                ],
                expected_balances_at_ts={
                    repayment_ts.replace(hour=3): {
                        accounts.CUSTOMER_ACCOUNT: [
                            (dimensions.PRINCIPAL, Decimal("0")),
                            (
                                dimensions.OVERPAYMENT,
                                Decimal("1000"),
                            ),  # total overpayment (100 + 900)
                        ],
                        accounts.EARLY_REPAYMENT_FEE_INCOME_ACCOUNT: [
                            (dimensions.EARLY_REPAYMENT_FEE_INCOME, Decimal("10")),
                        ],
                    }
                },
            ),
        ]

        test_scenario = self.get_simulation_test_scenario(
            start=start,
            end=end,
            sub_tests=sub_tests,
            contract_filepath=VERTICAL_CONTRACT,
            parameter_values=parameters.parameter_values,
        )
        self.run_test_scenario(test_scenario)


@pytest.mark.sim
class HorizontalHierarchyPaymentsTest(PaymentsSimulationTestBase):
    contract_filepaths = [HORIZONTAL_CONTRACT]

    @pytest.mark.sim
    def test_horizontal_hierarchy_payments(self):
        start = self.default_simulation_start_datetime
        disbursal_ts = start
        repayment_ts = start.replace(day=2)
        end = repayment_ts.replace(hour=4)

        sub_tests = [
            SubTest(
                description="Populate balances",
                events=[
                    create_outbound_hard_settlement_posting_instruction_event(
                        amount="1000",
                        event_datetime=disbursal_ts,
                        target_account_id=accounts.CUSTOMER_ACCOUNT,
                        internal_account_id=accounts.INTERNAL_ACCOUNT,
                        target_account_address=lending_addresses.PRINCIPAL,
                        denomination=DEFAULT_DENOMINATION,
                    ),
                    create_outbound_hard_settlement_posting_instruction_event(
                        amount="60",
                        event_datetime=disbursal_ts,
                        target_account_id=accounts.CUSTOMER_ACCOUNT,
                        internal_account_id=accounts.INTERNAL_ACCOUNT,
                        target_account_address=f"{lending_addresses.PRINCIPAL_OVERDUE}_20251201",
                        denomination=DEFAULT_DENOMINATION,
                    ),
                    create_outbound_hard_settlement_posting_instruction_event(
                        amount="20",
                        event_datetime=disbursal_ts,
                        target_account_id=accounts.CUSTOMER_ACCOUNT,
                        internal_account_id=accounts.INTERNAL_ACCOUNT,
                        target_account_address=f"{lending_addresses.INTEREST_OVERDUE}_20251201",
                        denomination=DEFAULT_DENOMINATION,
                    ),
                    create_outbound_hard_settlement_posting_instruction_event(
                        amount="40",
                        event_datetime=disbursal_ts,
                        target_account_id=accounts.CUSTOMER_ACCOUNT,
                        internal_account_id=accounts.INTERNAL_ACCOUNT,
                        target_account_address=f"{lending_addresses.PRINCIPAL_OVERDUE}_20260101",
                        denomination=DEFAULT_DENOMINATION,
                    ),
                    create_outbound_hard_settlement_posting_instruction_event(
                        amount="30",
                        event_datetime=disbursal_ts,
                        target_account_id=accounts.CUSTOMER_ACCOUNT,
                        internal_account_id=accounts.INTERNAL_ACCOUNT,
                        target_account_address=f"{lending_addresses.INTEREST_OVERDUE}_20260101",
                        denomination=DEFAULT_DENOMINATION,
                    ),
                    create_outbound_hard_settlement_posting_instruction_event(
                        amount="50",
                        event_datetime=disbursal_ts,
                        target_account_id=accounts.CUSTOMER_ACCOUNT,
                        internal_account_id=accounts.INTERNAL_ACCOUNT,
                        target_account_address=lending_addresses.INTEREST_DUE,
                        denomination=DEFAULT_DENOMINATION,
                    ),
                    create_outbound_hard_settlement_posting_instruction_event(
                        amount="200",
                        event_datetime=disbursal_ts,
                        target_account_id=accounts.CUSTOMER_ACCOUNT,
                        internal_account_id=accounts.INTERNAL_ACCOUNT,
                        target_account_address=lending_addresses.PRINCIPAL_DUE,
                        denomination=DEFAULT_DENOMINATION,
                    ),
                ],
                expected_balances_at_ts={
                    disbursal_ts: {
                        accounts.CUSTOMER_ACCOUNT: [
                            (dimensions.PRINCIPAL, Decimal("1000")),
                            (dimensions.PRINCIPAL_OVERDUE_20251201, Decimal("60")),
                            (dimensions.INTEREST_OVERDUE_20251201, Decimal("20")),
                            (dimensions.PRINCIPAL_OVERDUE_20260101, Decimal("40")),
                            (dimensions.INTEREST_OVERDUE_20260101, Decimal("30")),
                            (dimensions.INTEREST_DUE, Decimal("50")),
                            (dimensions.PRINCIPAL_DUE, Decimal("200")),
                        ],
                    }
                },
            ),
            SubTest(
                description="Underpayment (Partial Repayment)",
                events=[
                    create_inbound_hard_settlement_posting_instruction_event(
                        amount="100",  # Clears PRINCIPAL_OVERDUE_20251201(60) -> INTEREST_OVERDUE_20251201(20) -> PRINCIPAL_OVERDUE_20260101(20)
                        event_datetime=repayment_ts,
                        denomination=DEFAULT_DENOMINATION,
                        target_account_id=accounts.CUSTOMER_ACCOUNT,
                        internal_account_id=accounts.INTERNAL_ACCOUNT,
                    ),
                ],
                expected_balances_at_ts={
                    repayment_ts: {
                        accounts.CUSTOMER_ACCOUNT: [
                            (dimensions.PRINCIPAL, Decimal("1000")),
                            (dimensions.PRINCIPAL_OVERDUE_20251201, Decimal("0")),
                            (dimensions.INTEREST_OVERDUE_20251201, Decimal("0")),
                            (dimensions.PRINCIPAL_OVERDUE_20260101, Decimal("20")),
                            (dimensions.INTEREST_OVERDUE_20260101, Decimal("30")),
                            (dimensions.PRINCIPAL_DUE, Decimal("200")),
                            (dimensions.INTEREST_DUE, Decimal("50")),
                        ],
                    }
                },
            ),
            SubTest(
                description="Exact Repayment of Remaining Due/Overdue",
                events=[
                    create_inbound_hard_settlement_posting_instruction_event(
                        amount="300",  # Clears PRINCIPAL_OVERDUE_20260101(20), INTEREST_OVERDUE_20260101(30), PRINCIPAL_DUE(200), INTEREST_DUE(50)
                        event_datetime=repayment_ts.replace(hour=1),
                        denomination=DEFAULT_DENOMINATION,
                        target_account_id=accounts.CUSTOMER_ACCOUNT,
                        internal_account_id=accounts.INTERNAL_ACCOUNT,
                    ),
                ],
                expected_balances_at_ts={
                    repayment_ts.replace(hour=1): {
                        accounts.CUSTOMER_ACCOUNT: [
                            (dimensions.PRINCIPAL, Decimal("1000")),
                            (dimensions.PRINCIPAL_OVERDUE_20260101, Decimal("0")),
                            (dimensions.INTEREST_OVERDUE_20260101, Decimal("0")),
                            (dimensions.INTEREST_DUE, Decimal("0")),
                            (dimensions.PRINCIPAL_DUE, Decimal("0")),
                            (dimensions.OVERPAYMENT, Decimal("0")),
                        ],
                    }
                },
            ),
            SubTest(
                description="Overpayment",
                events=[
                    create_inbound_hard_settlement_posting_instruction_event(
                        amount="100",  # No due/overdue balances, goes to overpayment which clears principal
                        event_datetime=repayment_ts.replace(hour=2),
                        denomination=DEFAULT_DENOMINATION,
                        target_account_id=accounts.CUSTOMER_ACCOUNT,
                        internal_account_id=accounts.INTERNAL_ACCOUNT,
                    ),
                ],
                expected_balances_at_ts={
                    repayment_ts.replace(hour=2): {
                        accounts.CUSTOMER_ACCOUNT: [
                            (dimensions.PRINCIPAL, Decimal("900")),
                            (
                                dimensions.OVERPAYMENT,
                                Decimal("100"),
                            ),  # Tracker balance from overpayment logic
                        ],
                    }
                },
            ),
            SubTest(
                description="Early Repayment (Full Repayment)",
                events=[
                    create_inbound_hard_settlement_posting_instruction_event(
                        amount="910",  # Clears remaining principal (900) + early repayment fee (10)
                        event_datetime=repayment_ts.replace(hour=3),
                        denomination=DEFAULT_DENOMINATION,
                        target_account_id=accounts.CUSTOMER_ACCOUNT,
                        internal_account_id=accounts.INTERNAL_ACCOUNT,
                    ),
                ],
                expected_balances_at_ts={
                    repayment_ts.replace(hour=3): {
                        accounts.CUSTOMER_ACCOUNT: [
                            (dimensions.PRINCIPAL, Decimal("0")),
                            (
                                dimensions.OVERPAYMENT,
                                Decimal("1000"),
                            ),  # total overpayment (100 + 900)
                        ],
                        accounts.EARLY_REPAYMENT_FEE_INCOME_ACCOUNT: [
                            (dimensions.EARLY_REPAYMENT_FEE_INCOME, Decimal("10")),
                        ],
                    }
                },
            ),
        ]

        test_scenario = self.get_simulation_test_scenario(
            start=start,
            end=end,
            sub_tests=sub_tests,
            contract_filepath=HORIZONTAL_CONTRACT,
            parameter_values=parameters.parameter_values,
        )
        self.run_test_scenario(test_scenario)


@pytest.mark.sim
class CustomCallablePaymentsTest(PaymentsSimulationTestBase):
    contract_filepaths = [CUSTOM_CALLABLE_CONTRACT]

    @pytest.mark.sim
    def test_custom_callable_payments(self):
        start = self.default_simulation_start_datetime
        disbursal_ts = start
        repayment_ts = start.replace(day=2)
        end = repayment_ts.replace(hour=4)

        sub_tests = [
            SubTest(
                description="Populate balances",
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
                description="Early Repayment (Full Repayment) configured via lambda",
                events=[
                    create_inbound_hard_settlement_posting_instruction_event(
                        amount="1010",  # Clears remaining principal (1000) + early repayment fee (10)
                        event_datetime=repayment_ts,
                        denomination=DEFAULT_DENOMINATION,
                        target_account_id=accounts.CUSTOMER_ACCOUNT,
                        internal_account_id=accounts.INTERNAL_ACCOUNT,
                    ),
                ],
                expected_balances_at_ts={
                    repayment_ts: {
                        accounts.CUSTOMER_ACCOUNT: [
                            (dimensions.PRINCIPAL, Decimal("0")),
                        ],
                        accounts.EARLY_REPAYMENT_FEE_INCOME_ACCOUNT: [
                            (dimensions.EARLY_REPAYMENT_FEE_INCOME, Decimal("10")),
                        ],
                    }
                },
            ),
        ]

        test_scenario = self.get_simulation_test_scenario(
            start=start,
            end=end,
            sub_tests=sub_tests,
            contract_filepath=CUSTOM_CALLABLE_CONTRACT,
            parameter_values=parameters.parameter_values,
        )
        self.run_test_scenario(test_scenario)
