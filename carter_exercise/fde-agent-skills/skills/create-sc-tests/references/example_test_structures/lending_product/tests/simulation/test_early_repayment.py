# standard libs
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

import feature_library.lending.addresses as lending_addresses

# third party
import pytest

# simulation
import tests.lending.repayments.early_repayment.simulation.accounts as accounts
import tests.lending.repayments.early_repayment.simulation.dimensions as dimensions
import tests.lending.repayments.early_repayment.simulation.parameters as parameters
from inception_sdk.test_framework.common.balance_helpers import BalanceDimensions

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
from tests.common.test_denomination import DEFAULT_DENOMINATION

VERTICAL_CONTRACT = str(
    Path("lending_product/contracts/template/vertical_hierarchy_smart_contract.py")
)
HORIZONTAL_CONTRACT = str(
    Path("lending_product/contracts/template/horizontal_hierarchy_smart_contract.py")
)

UTC = ZoneInfo("UTC")


class EarlyRepaymentSimulationTest(SimulationTestCase):
    parameter_resource_dirs = [
        str(Path("lending_product/parameters")),
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
class VerticalHierarchyEarlyRepaymentTest(EarlyRepaymentSimulationTest):
    contract_filepaths = [VERTICAL_CONTRACT]

    @pytest.mark.sim
    def test_vertical_hierarchy_early_repayment(self):
        start = self.default_simulation_start_datetime
        disbursal_ts = start
        repayment_ts = start.replace(day=2)
        end = repayment_ts.replace(hour=1)

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
                        amount="100",
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
                        amount="50",
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
                            (dimensions.INTEREST_OVERDUE, Decimal("100")),
                            (dimensions.INTEREST_DUE, Decimal("50")),
                            (dimensions.PRINCIPAL_DUE, Decimal("50")),
                        ],
                    }
                },
            ),
            SubTest(
                description="Full early repayment with flat fee",
                events=[
                    create_inbound_hard_settlement_posting_instruction_event(
                        amount="1310",
                        event_datetime=repayment_ts,
                        target_account_id=accounts.CUSTOMER_ACCOUNT,
                        internal_account_id=accounts.INTERNAL_ACCOUNT,
                        denomination=DEFAULT_DENOMINATION,
                    )
                ],
                expected_balances_at_ts={
                    repayment_ts: {
                        accounts.CUSTOMER_ACCOUNT: [
                            # Principal remains as we don't have distribution logic in test SC
                            (dimensions.PRINCIPAL, Decimal("1000")),
                            # Net balance on DEFAULT should be -1000
                            # (-1310 repayment + 10 fee charge)
                            (dimensions.DEFAULT, Decimal("-1300")),
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
            parameter_values=parameters.vertical_hierarchy_parameter_values,
        )
        self.run_test_scenario(test_scenario)


@pytest.mark.sim
class HorizontalHierarchyEarlyRepaymentTest(EarlyRepaymentSimulationTest):
    contract_filepaths = [HORIZONTAL_CONTRACT]

    @pytest.mark.sim
    def test_horizontal_hierarchy_early_repayment(self):
        start = self.default_simulation_start_datetime
        disbursal_ts = start
        repayment_ts = start.replace(day=2)
        end = repayment_ts.replace(hour=1)

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
                    create_outbound_hard_settlement_posting_instruction_event(
                        amount="100",
                        event_datetime=disbursal_ts,
                        target_account_id=accounts.CUSTOMER_ACCOUNT,
                        internal_account_id=accounts.INTERNAL_ACCOUNT,
                        target_account_address="PRINCIPAL_OVERDUE_20260128",
                        denomination=DEFAULT_DENOMINATION,
                    ),
                    create_outbound_hard_settlement_posting_instruction_event(
                        amount="100",
                        event_datetime=disbursal_ts,
                        target_account_id=accounts.CUSTOMER_ACCOUNT,
                        internal_account_id=accounts.INTERNAL_ACCOUNT,
                        target_account_address="INTEREST_OVERDUE_20260128",
                        denomination=DEFAULT_DENOMINATION,
                    ),
                    create_outbound_hard_settlement_posting_instruction_event(
                        amount="100",
                        event_datetime=disbursal_ts,
                        target_account_id=accounts.CUSTOMER_ACCOUNT,
                        internal_account_id=accounts.INTERNAL_ACCOUNT,
                        target_account_address="PRINCIPAL_OVERDUE_20260228",
                        denomination=DEFAULT_DENOMINATION,
                    ),
                    create_outbound_hard_settlement_posting_instruction_event(
                        amount="100",
                        event_datetime=disbursal_ts,
                        target_account_id=accounts.CUSTOMER_ACCOUNT,
                        internal_account_id=accounts.INTERNAL_ACCOUNT,
                        target_account_address="INTEREST_OVERDUE_20260228",
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
                        amount="50",
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
                            (
                                BalanceDimensions(
                                    address="PRINCIPAL_OVERDUE_20260128",
                                    denomination=DEFAULT_DENOMINATION,
                                ),
                                Decimal("100"),
                            ),
                            (
                                BalanceDimensions(
                                    address="INTEREST_OVERDUE_20260128",
                                    denomination=DEFAULT_DENOMINATION,
                                ),
                                Decimal("100"),
                            ),
                            (
                                BalanceDimensions(
                                    address="PRINCIPAL_OVERDUE_20260228",
                                    denomination=DEFAULT_DENOMINATION,
                                ),
                                Decimal("100"),
                            ),
                            (
                                BalanceDimensions(
                                    address="INTEREST_OVERDUE_20260228",
                                    denomination=DEFAULT_DENOMINATION,
                                ),
                                Decimal("100"),
                            ),
                            (dimensions.INTEREST_DUE, Decimal("50")),
                            (dimensions.PRINCIPAL_DUE, Decimal("50")),
                        ],
                    }
                },
            ),
            SubTest(
                description="Full early repayment with percentage fee",
                # Fee is 5% of 1000 = 50. Total repayment = 1000 + 50 = 1050
                events=[
                    create_inbound_hard_settlement_posting_instruction_event(
                        amount="1550",
                        event_datetime=repayment_ts,
                        target_account_id=accounts.CUSTOMER_ACCOUNT,
                        internal_account_id=accounts.INTERNAL_ACCOUNT,
                        denomination=DEFAULT_DENOMINATION,
                    )
                ],
                expected_balances_at_ts={
                    repayment_ts: {
                        accounts.CUSTOMER_ACCOUNT: [
                            # Principal remains as we don't have distribution logic in test SC
                            (dimensions.PRINCIPAL, Decimal("1000")),
                            # Net balance on DEFAULT should be -1000
                            # (-1550 repayment + 50 fee charge)
                            (dimensions.DEFAULT, Decimal("-1500")),
                        ],
                        accounts.EARLY_REPAYMENT_FEE_INCOME_ACCOUNT: [
                            (dimensions.EARLY_REPAYMENT_FEE_INCOME, Decimal("50")),
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
            parameter_values=parameters.horizontal_hierarchy_parameter_values,
        )
        self.run_test_scenario(test_scenario)
