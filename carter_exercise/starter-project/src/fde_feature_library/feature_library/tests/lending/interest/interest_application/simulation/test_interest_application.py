# standard libs
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
from dateutil.relativedelta import relativedelta

# feature library
import feature_library.lending.addresses as lending_addresses
import feature_library.lending.interest.interest_application as interest_application

# contracts api
from contracts_api import DEFAULT_ASSET

# inception sdk
from inception_sdk.test_framework.contracts.simulation.data_objects.data_objects import (
    AccountConfig,
    ContractConfig,
    ExpectedSchedule,
    SimulationTestScenario,
    SubTest,
)
from inception_sdk.test_framework.contracts.simulation.helper import (
    create_inbound_hard_settlement_posting_instruction_event,
    create_outbound_hard_settlement_posting_instruction_event,
)
from inception_sdk.test_framework.contracts.simulation.utils import SimulationTestCase

import tests.lending.interest.interest_application.simulation.accounts as accounts
import tests.lending.interest.interest_application.simulation.dimensions as dimensions
import tests.lending.interest.interest_application.simulation.parameters as parameters
import tests.lending.interest.interest_application.smart_contract as smart_contract
from tests.common.test_denomination import DEFAULT_DENOMINATION

SMART_CONTRACT = "tests/lending/interest/interest_application/smart_contract.py"

UTC = ZoneInfo("UTC")


class InterestApplicationBaseTest(SimulationTestCase):
    parameter_resource_dirs = [
        str(Path("src/feature_library/lending/interest/parameter_resource_defs")),
        str(Path("src/feature_library/common/parameter_resource_defs")),
    ]
    contract_filepaths = [str(SMART_CONTRACT)]
    internal_accounts = accounts.default_internal_accounts
    parameter_values = parameters.default_parameter_values
    parameters = []
    default_simulation_start_datetime = datetime(year=2026, month=1, day=1, tzinfo=UTC)

    @classmethod
    def setUpClass(cls):
        cls.contract_filepath = str(SMART_CONTRACT)
        super().setUpClass()

    def get_simulation_test_scenario(
        self,
        start,
        end,
        sub_tests,
        parameter_values=None,
        internal_accounts=None,
        debug=False,
    ):
        contract_config = ContractConfig(
            contract_content=self.smart_contract_path_to_content[self.contract_filepath],
            template_params={},
            account_configs=[
                AccountConfig(
                    account_id_base=accounts.CUSTOMER_ACCOUNT,
                    parameter_values=parameter_values or self.parameter_values,
                    permitted_denominations=[DEFAULT_DENOMINATION],
                )
            ],
        )
        return SimulationTestScenario(
            start=start,
            end=end,
            sub_tests=sub_tests,
            contract_config=contract_config,
            internal_accounts=self.internal_accounts or internal_accounts,
            parameters=self.parameters,
            debug=debug,
            use_v1_accounts=False,
        )


@pytest.mark.sim
class InterestApplicationTest(InterestApplicationBaseTest):
    @pytest.mark.sim
    def test_interest_application(self):
        start = self.default_simulation_start_datetime
        # Fake accrual halfway through the month
        accrual_time = start + relativedelta(days=15)
        # Application after one month
        application_event = start + relativedelta(day=28)

        end = application_event + relativedelta(minutes=1)

        sub_tests = [
            SubTest(
                description="Fake accrual",
                events=[
                    create_outbound_hard_settlement_posting_instruction_event(
                        amount="10.12345",
                        denomination=DEFAULT_DENOMINATION,
                        target_account_id=accounts.CUSTOMER_ACCOUNT,
                        internal_account_id=accounts.INTERNAL_ACCOUNT,
                        advice=False,
                        target_account_address=lending_addresses.ACCRUED_INTEREST_RECEIVABLE,
                        event_datetime=accrual_time,
                        asset=DEFAULT_ASSET,
                    )
                ],
                expected_balances_at_ts={
                    accrual_time + relativedelta(seconds=1): {
                        accounts.CUSTOMER_ACCOUNT: [
                            (dimensions.accrued_interest_receivable, Decimal("10.12345")),
                        ]
                    }
                },
            ),
            SubTest(
                description="Check application after 1 month",
                # Accrued: 10.12345
                # Rounded application (precision 2): 10.12
                # After application:
                # ACCRUED_INTEREST_RECEIVABLE should be 0 (full reversal of unrounded 10.12345)
                # INTEREST_DUE should be 10.12
                expected_balances_at_ts={
                    application_event: {
                        accounts.CUSTOMER_ACCOUNT: [
                            (dimensions.accrued_interest_receivable, Decimal("0")),
                            (dimensions.interest_due, Decimal("10.12")),
                        ]
                    }
                },
                expected_schedules=[
                    ExpectedSchedule(
                        run_times=[application_event],
                        event_id=smart_contract.APPLICATION_EVENT,
                        account_id=accounts.CUSTOMER_ACCOUNT,
                        count=1,
                    )
                ],
            ),
        ]

        test_scenario = self.get_simulation_test_scenario(
            start=start,
            end=end,
            sub_tests=sub_tests,
        )
        self.run_test_scenario(test_scenario)

    @pytest.mark.sim
    def test_interest_application_zero_balance(self):
        start = self.default_simulation_start_datetime
        # Application after one month (Jan 28th)
        application_event = start + relativedelta(day=28)

        end = application_event + relativedelta(minutes=1)

        sub_tests = [
            SubTest(
                description="Check application when accrued interest is 0",
                events=[],
                expected_balances_at_ts={
                    application_event: {
                        accounts.CUSTOMER_ACCOUNT: [
                            (dimensions.accrued_interest_receivable, Decimal("0")),
                            (dimensions.interest_due, Decimal("0")),
                        ]
                    }
                },
                expected_schedules=[
                    ExpectedSchedule(
                        run_times=[application_event],
                        event_id=smart_contract.APPLICATION_EVENT,
                        account_id=accounts.CUSTOMER_ACCOUNT,
                        count=1,
                    )
                ],
            ),
        ]

        test_scenario = self.get_simulation_test_scenario(
            start=start,
            end=end,
            sub_tests=sub_tests,
        )
        self.run_test_scenario(test_scenario)

    @pytest.mark.sim
    def test_repay_accrued_interest(self):
        start = self.default_simulation_start_datetime
        # Fake accrual halfway through the month
        accrual_time = start + relativedelta(days=15)
        # "Overpayment" a day later
        repayment_time = accrual_time + relativedelta(days=1)

        end = repayment_time + relativedelta(minutes=1)

        sub_tests = [
            SubTest(
                description="Fake accrual",
                events=[
                    create_outbound_hard_settlement_posting_instruction_event(
                        amount="10.12345",
                        denomination=DEFAULT_DENOMINATION,
                        target_account_id=accounts.CUSTOMER_ACCOUNT,
                        internal_account_id=accounts.INTERNAL_ACCOUNT,
                        advice=False,
                        target_account_address=lending_addresses.ACCRUED_INTEREST_RECEIVABLE,
                        event_datetime=accrual_time,
                        asset=DEFAULT_ASSET,
                    )
                ],
                expected_balances_at_ts={
                    accrual_time + relativedelta(seconds=1): {
                        accounts.CUSTOMER_ACCOUNT: [
                            (dimensions.accrued_interest_receivable, Decimal("10.12345")),
                        ]
                    }
                },
            ),
            SubTest(
                description="Repay accrued interest due to overpayment",
                # Accrued: 10.12345, Rounded: 10.12
                # Repay 5.00
                # This should:
                # 1. Apply 5.00 interest (Move 5.00 from internal to customer INTEREST_DUE)
                # 2. Rebalance (Move 5.00 from customer DEFAULT to customer INTEREST_DUE -
                #    handled by repayment)
                # 3. Reverse 5.00 accrual (Move 5.00 from customer ACCRUED_INTEREST_RECEIVABLE
                #    to internal)
                # Results:
                # ACCRUED_INTEREST_RECEIVABLE: 10.12345 - 5.00 = 5.12345
                # INTEREST_DUE: 5.00 (from application) - 5.00 (from repayment) = 0
                events=[
                    create_inbound_hard_settlement_posting_instruction_event(
                        amount="5.00",
                        denomination=DEFAULT_DENOMINATION,
                        target_account_id=accounts.CUSTOMER_ACCOUNT,
                        internal_account_id=accounts.INTERNAL_ACCOUNT,
                        advice=False,
                        target_account_address=interest_application.DEFAULT_ADDRESS,
                        event_datetime=repayment_time,
                        asset=DEFAULT_ASSET,
                        instruction_details={"description": smart_contract.OVERPAYMENT},
                    )
                ],
                expected_balances_at_ts={
                    repayment_time + relativedelta(seconds=1): {
                        accounts.CUSTOMER_ACCOUNT: [
                            (dimensions.accrued_interest_receivable, Decimal("5.12345")),
                            (dimensions.interest_due, Decimal("0")),
                        ]
                    }
                },
            ),
        ]

        test_scenario = self.get_simulation_test_scenario(
            start=start,
            end=end,
            sub_tests=sub_tests,
        )
        self.run_test_scenario(test_scenario)

    @pytest.mark.sim
    def test_repay_accrued_interest_zero_balance(self):
        start = self.default_simulation_start_datetime
        repayment_time = start + relativedelta(days=1)

        end = repayment_time + relativedelta(minutes=1)

        sub_tests = [
            SubTest(
                description="Repay when accrued interest is 0",
                events=[
                    create_inbound_hard_settlement_posting_instruction_event(
                        amount="5.00",
                        denomination=DEFAULT_DENOMINATION,
                        target_account_id=accounts.CUSTOMER_ACCOUNT,
                        internal_account_id=accounts.INTERNAL_ACCOUNT,
                        advice=False,
                        target_account_address=interest_application.DEFAULT_ADDRESS,
                        event_datetime=repayment_time,
                        asset=DEFAULT_ASSET,
                        instruction_details={"description": smart_contract.OVERPAYMENT},
                    )
                ],
                expected_balances_at_ts={
                    repayment_time + relativedelta(seconds=1): {
                        accounts.CUSTOMER_ACCOUNT: [
                            (dimensions.accrued_interest_receivable, Decimal("0")),
                            (dimensions.interest_due, Decimal("0")),
                            (dimensions.default, Decimal("-5")),
                        ]
                    }
                },
            ),
        ]

        test_scenario = self.get_simulation_test_scenario(
            start=start,
            end=end,
            sub_tests=sub_tests,
        )
        self.run_test_scenario(test_scenario)
