# standard libs
import json
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
from dateutil.relativedelta import relativedelta

# library
import feature_library.deposit.interest.secondary.flat_interest as flat_interest

# inception sdk
from inception_sdk.test_framework.contracts.simulation.data_objects.data_objects import (
    AccountConfig,
    ContractConfig,
    SimulationTestScenario,
    SubTest,
)
from inception_sdk.test_framework.contracts.simulation.helper import (
    create_inbound_hard_settlement_instruction,
)
from inception_sdk.test_framework.contracts.simulation.utils import SimulationTestCase
from inception_sdk.vault.core_api import DecimalParameterValue, StringParameterValue

import tests.deposit.interest.interest_accrual.simulation.accounts as accounts
import tests.deposit.interest.interest_accrual.simulation.dimensions as dimensions
import tests.deposit.interest.interest_accrual.simulation.parameters as parameters
import tests.deposit.interest.interest_accrual.tiered_interest_sc as tiered_interest_sc

SMART_CONTRACT = str(Path("tests/deposit/interest/interest_accrual/tiered_interest_sc.py"))
FLAT_INTEREST_SC = str(Path("tests/deposit/interest/interest_accrual/flat_interest_sc.py"))
MULTI_INTEREST_SC = str(Path("tests/deposit/interest/interest_accrual/multi_interest_type_sc.py"))
OVERDRAFT_INTEREST_SC = str(
    Path("tests/deposit/interest/interest_accrual/overdraft_interest_sc.py")
)


class InterestAccrualBaseTest(SimulationTestCase):
    parameter_resource_dirs = [
        "src/feature_library/deposit/interest/parameter_resource_defs",
        "src/feature_library/common/parameter_resource_defs",
    ]
    contract_filepaths = [
        str(SMART_CONTRACT),
        str(FLAT_INTEREST_SC),
        str(MULTI_INTEREST_SC),
        str(OVERDRAFT_INTEREST_SC),
    ]
    internal_accounts = accounts.default_internal_accounts
    parameter_values = parameters.default_parameter_values
    parameters = []
    default_simulation_start_datetime = datetime(year=2026, month=1, day=1, tzinfo=ZoneInfo("UTC"))

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
        contract_filepath=None,
    ):
        contract_filepath = contract_filepath or self.contract_filepath

        contract_config = ContractConfig(
            contract_content=self.smart_contract_path_to_content[contract_filepath],
            template_params={},
            account_configs=[
                AccountConfig(
                    account_id_base=accounts.CUSTOMER_ACCOUNT,
                    parameter_values=parameter_values or self.parameter_values,
                    permitted_denominations=[parameters.DEFAULT_DENOMINATION],
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


class TieredInterestTest(InterestAccrualBaseTest):
    @pytest.mark.sim
    def test_tiered_interest_accrual(self):
        parameter_values = {
            **parameters.default_parameter_values,
            tiered_interest_sc.tiered_interest.TIERED_INTEREST_RATES_PARAM_ID: StringParameterValue(
                string_value=json.dumps(
                    {
                        "0": "0.01",
                        "500": "0.5",
                        "1000": "0.8",
                        "1500": "1",
                    }
                )
            ),
        }

        start = datetime(year=2026, month=1, day=1, tzinfo=ZoneInfo("UTC"))
        # Accrual at 00:00:00, so we check just after that on subsequent days
        end = start + relativedelta(days=2, seconds=1)

        sub_tests = [
            SubTest(
                description="No accrual on zero balance",
                events=[],
                expected_balances_at_ts={
                    start + relativedelta(days=1): {
                        accounts.CUSTOMER_ACCOUNT: [
                            (dimensions.ACCRUED_INTEREST_PAYABLE, Decimal(0))
                        ]
                    }
                },
            ),
            SubTest(
                description="Accrual on multiple tiers (2000 total balance)",
                events=[
                    create_inbound_hard_settlement_instruction(
                        amount="2000",
                        event_datetime=start + relativedelta(days=1, seconds=1),
                        target_account_id=accounts.CUSTOMER_ACCOUNT,
                        internal_account_id=accounts.DUMMY_INTERNAL_ACCOUNT,
                        denomination=parameters.DEFAULT_DENOMINATION,
                    )
                ],
                expected_balances_at_ts={
                    # 500 * 0.01 / 365 = 0.0136986...
                    # 500 * 0.50 / 365 = 0.6849315...
                    # 500 * 0.80 / 365 = 1.095890...
                    # 500 * 1.00 / 365 = 1.369863...
                    # Total: 3.16438... -> 3.16438 (precision 5)
                    start + relativedelta(days=2): {
                        accounts.CUSTOMER_ACCOUNT: [
                            (dimensions.ACCRUED_INTEREST_PAYABLE, Decimal("3.16438"))
                        ]
                    }
                },
            ),
        ]

        test_scenario = self.get_simulation_test_scenario(
            start=start,
            end=end,
            sub_tests=sub_tests,
            parameter_values=parameter_values,
        )
        self.run_test_scenario(test_scenario)

    @pytest.mark.sim
    def test_negative_tiered_interest_accrual(self):
        start = datetime(year=2026, month=1, day=1, tzinfo=ZoneInfo("UTC"))
        # Accrual at 00:00:00, so we check just after that on the next day
        end = start + relativedelta(days=1, seconds=1)

        # Custom tiers: 0-500 @ -1%, 500+ @ -2%
        # For 1000 balance:
        # 500 * -0.01 / 365 = -0.013698...
        # 500 * -0.02 / 365 = -0.027397...
        # Total: -0.041095... -> -0.04110 (precision 5)
        parameter_values = {
            **parameters.default_parameter_values,
            tiered_interest_sc.tiered_interest.TIERED_INTEREST_RATES_PARAM_ID: StringParameterValue(
                string_value=json.dumps({"0": "-0.01", "500": "-0.02"})
            ),
        }

        sub_tests = [
            SubTest(
                description="Negative accrual on tiers (1000 total: 500 at -1%, 500 at -2%)",
                events=[
                    create_inbound_hard_settlement_instruction(
                        amount="1000",
                        event_datetime=start,
                        target_account_id=accounts.CUSTOMER_ACCOUNT,
                        internal_account_id=accounts.DUMMY_INTERNAL_ACCOUNT,
                        denomination=parameters.DEFAULT_DENOMINATION,
                    )
                ],
                expected_balances_at_ts={
                    start + relativedelta(days=1): {
                        accounts.CUSTOMER_ACCOUNT: [
                            (dimensions.ACCRUED_INTEREST_PAYABLE, Decimal("0")),
                            (dimensions.ACCRUED_INTEREST_RECEIVABLE, Decimal("-0.0411")),
                        ]
                    }
                },
            ),
        ]

        test_scenario = self.get_simulation_test_scenario(
            start=start,
            end=end,
            sub_tests=sub_tests,
            parameter_values=parameter_values,
        )
        self.run_test_scenario(test_scenario)

    @pytest.mark.sim
    def test_accrual_below_lowest_tier(self):
        import json

        from inception_sdk.vault.core_api import StringParameterValue

        start = datetime(year=2026, month=1, day=1, tzinfo=ZoneInfo("UTC"))
        end = start + relativedelta(days=1, seconds=1)

        # Lowest tier starts at 1000
        parameter_values = {
            **parameters.default_parameter_values,
            tiered_interest_sc.tiered_interest.TIERED_INTEREST_RATES_PARAM_ID: StringParameterValue(
                string_value=json.dumps({"1000": "0.01"})
            ),
        }

        sub_tests = [
            SubTest(
                description="No accrual when balance (50) is below lowest tier (1000)",
                events=[
                    create_inbound_hard_settlement_instruction(
                        amount="50",
                        event_datetime=start,
                        target_account_id=accounts.CUSTOMER_ACCOUNT,
                        internal_account_id=accounts.DUMMY_INTERNAL_ACCOUNT,
                        denomination=parameters.DEFAULT_DENOMINATION,
                    )
                ],
                expected_balances_at_ts={
                    start + relativedelta(days=1): {
                        accounts.CUSTOMER_ACCOUNT: [
                            (dimensions.ACCRUED_INTEREST_PAYABLE, Decimal("0")),
                        ]
                    }
                },
            ),
        ]

        test_scenario = self.get_simulation_test_scenario(
            start=start,
            end=end,
            sub_tests=sub_tests,
            parameter_values=parameter_values,
        )
        self.run_test_scenario(test_scenario)


class FlatInterestTest(InterestAccrualBaseTest):
    @pytest.mark.sim
    def test_flat_interest_accrual(self):
        start = datetime(year=2026, month=1, day=1, tzinfo=ZoneInfo("UTC"))
        end = start + relativedelta(days=1, seconds=1)

        # 10% annual rate: 1000 * 0.10 / 365 = 0.2739726... -> 0.27397 (precision 5)
        parameter_values = {
            **parameters.default_parameter_values,
            flat_interest.FIXED_INTEREST_RATE_PARAM_ID: DecimalParameterValue(
                decimal_value=Decimal("0.1")
            ),
        }

        sub_tests = [
            SubTest(
                description="Flat interest accrual (1000 balance at 10%)",
                events=[
                    create_inbound_hard_settlement_instruction(
                        amount="1000",
                        event_datetime=start,
                        target_account_id=accounts.CUSTOMER_ACCOUNT,
                        internal_account_id=accounts.DUMMY_INTERNAL_ACCOUNT,
                        denomination=parameters.DEFAULT_DENOMINATION,
                    )
                ],
                expected_balances_at_ts={
                    start + relativedelta(days=1): {
                        accounts.CUSTOMER_ACCOUNT: [
                            (dimensions.ACCRUED_INTEREST_PAYABLE, Decimal("0.27397")),
                        ]
                    }
                },
            ),
        ]

        test_scenario = self.get_simulation_test_scenario(
            start=start,
            end=end,
            sub_tests=sub_tests,
            parameter_values=parameter_values,
            contract_filepath=FLAT_INTEREST_SC,
        )
        self.run_test_scenario(test_scenario)

    @pytest.mark.sim
    def test_flat_interest_negative_accrual(self):
        start = datetime(year=2026, month=1, day=1, tzinfo=ZoneInfo("UTC"))
        end = start + relativedelta(days=1, seconds=1)

        # -1% annual rate: 1000 * -0.01 / 365 = -0.02739726... -> 0.02740 (precision 5) on ACCRUED_INTEREST_RECEIVABLE
        parameter_values = {
            **parameters.default_parameter_values,
            flat_interest.FIXED_INTEREST_RATE_PARAM_ID: DecimalParameterValue(
                decimal_value=Decimal("-0.01")
            ),
        }

        sub_tests = [
            SubTest(
                description="Flat interest negative accrual (1000 balance at -1%)",
                events=[
                    create_inbound_hard_settlement_instruction(
                        amount="1000",
                        event_datetime=start,
                        target_account_id=accounts.CUSTOMER_ACCOUNT,
                        internal_account_id=accounts.DUMMY_INTERNAL_ACCOUNT,
                        denomination=parameters.DEFAULT_DENOMINATION,
                    )
                ],
                expected_balances_at_ts={
                    start + relativedelta(days=1): {
                        accounts.CUSTOMER_ACCOUNT: [
                            (dimensions.ACCRUED_INTEREST_PAYABLE, Decimal("0")),
                            (dimensions.ACCRUED_INTEREST_RECEIVABLE, Decimal("-0.02740")),
                        ]
                    }
                },
            ),
        ]

        test_scenario = self.get_simulation_test_scenario(
            start=start,
            end=end,
            sub_tests=sub_tests,
            parameter_values=parameter_values,
            contract_filepath=FLAT_INTEREST_SC,
        )
        self.run_test_scenario(test_scenario)


class MultiInterestTest(InterestAccrualBaseTest):
    @classmethod
    def setUpClass(cls):
        cls.contract_filepath = str(MULTI_INTEREST_SC)
        super().setUpClass()

    @pytest.mark.sim
    def test_multi_interest_accrual(self):
        start = datetime(year=2026, month=1, day=1, tzinfo=ZoneInfo("UTC"))
        end = start + relativedelta(days=1, seconds=1)

        # 1000 balance
        # Tiered:
        # 0-500 @ 1%: 500 * 0.01 / 365 = 0.013698...
        # 500-1000 @ 50%: 500 * 0.50 / 365 = 0.684931...
        # Tiered Total: 0.698629...

        # Flat:
        # 1000 @ 10%: 1000 * 0.10 / 365 = 0.273972...

        # Combined Total: 0.698629 + 0.273972 = 0.972601... -> 0.97260 (precision 5)

        parameter_values = {
            **parameters.default_parameter_values,
            tiered_interest_sc.tiered_interest.TIERED_INTEREST_RATES_PARAM_ID: StringParameterValue(
                string_value=json.dumps({"0": "0.01", "500": "0.5"})
            ),
            flat_interest.FIXED_INTEREST_RATE_PARAM_ID: DecimalParameterValue(
                decimal_value=Decimal("0.1")
            ),
        }

        sub_tests = [
            SubTest(
                description="Multi interest accrual (Tiered + Flat)",
                events=[
                    create_inbound_hard_settlement_instruction(
                        amount="1000",
                        event_datetime=start,
                        target_account_id=accounts.CUSTOMER_ACCOUNT,
                        internal_account_id=accounts.DUMMY_INTERNAL_ACCOUNT,
                        denomination=parameters.DEFAULT_DENOMINATION,
                    )
                ],
                expected_balances_at_ts={
                    start + relativedelta(days=1): {
                        accounts.CUSTOMER_ACCOUNT: [
                            (dimensions.ACCRUED_INTEREST_PAYABLE, Decimal("0.97260")),
                        ]
                    }
                },
            ),
        ]

        test_scenario = self.get_simulation_test_scenario(
            start=start,
            end=end,
            sub_tests=sub_tests,
            parameter_values=parameter_values,
            contract_filepath=MULTI_INTEREST_SC,
        )
        self.run_test_scenario(test_scenario)


class OverdraftInterestTest(InterestAccrualBaseTest):
    @pytest.mark.sim
    def test_overdraft_interest_accrual(self):
        import feature_library.deposit.interest.secondary.overdraft_interest as overdraft_interest

        from inception_sdk.test_framework.contracts.simulation.helper import (
            create_outbound_hard_settlement_instruction,
        )
        from inception_sdk.vault.core_api import (
            AccountIdParameterValue,
            DecimalParameterValue,
        )

        start = datetime(year=2026, month=1, day=1, tzinfo=ZoneInfo("UTC"))
        end = start + relativedelta(days=2, seconds=1)

        # 14.6% annual rate: 1000 * 0.146 / 365 = 0.40 daily
        parameter_values = {
            **parameters.default_parameter_values,
            overdraft_interest.OVERDRAFT_INTEREST_RATE_PARAM_ID: DecimalParameterValue(
                decimal_value=Decimal("0.146")
            ),
            overdraft_interest.INTEREST_FREE_BUFFER_AMOUNT_PARAM_ID: DecimalParameterValue(
                decimal_value=Decimal("0")
            ),
            overdraft_interest.INTEREST_FREE_BUFFER_DAYS_PARAM_ID: DecimalParameterValue(
                decimal_value=Decimal("0")
            ),
            overdraft_interest.OVERDRAFT_INTEREST_RECEIVABLE_ACCOUNT_PARAM_ID: AccountIdParameterValue(  # noqa
                account_id_value=accounts.DUMMY_INTERNAL_ACCOUNT
            ),
            overdraft_interest.OVERDRAFT_INTEREST_RECEIVED_ACCOUNT_PARAM_ID: AccountIdParameterValue(  # noqa
                account_id_value=accounts.DUMMY_INTERNAL_ACCOUNT
            ),
            overdraft_interest.application_precision.APPLICATION_PRECISION_PARAM_ID: DecimalParameterValue(  # noqa
                decimal_value=Decimal("2")
            ),
        }

        sub_tests = [
            SubTest(
                description="Overdraft interest accrual (1000 overdraft at 14.6%)",
                events=[
                    create_outbound_hard_settlement_instruction(
                        amount="1000",
                        event_datetime=start + relativedelta(seconds=1),
                        target_account_id=accounts.CUSTOMER_ACCOUNT,
                        internal_account_id=accounts.DUMMY_INTERNAL_ACCOUNT,
                        denomination=dimensions.DEFAULT_DENOMINATION,
                    )
                ],
                expected_balances_at_ts={
                    start + relativedelta(days=1, seconds=1): {
                        accounts.CUSTOMER_ACCOUNT: [
                            (dimensions.OVERDRAFT_ACCRUED_INTEREST, Decimal("-0.40"))
                        ]
                    }
                },
            ),
        ]

        test_scenario = self.get_simulation_test_scenario(
            start=start,
            end=end,
            sub_tests=sub_tests,
            parameter_values=parameter_values,
            contract_filepath=OVERDRAFT_INTEREST_SC,
        )
        self.run_test_scenario(test_scenario)
