# Copyright @ 2026 Thought Machine Group Limited. All rights reserved.
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import pytest
from dateutil.relativedelta import relativedelta

# feature library
import feature_library.lending.addresses as lending_addresses
import feature_library.lending.due_amount_calculation.due_amount_calculation as due_calc

from inception_sdk.test_framework.contracts.simulation.data_objects.data_objects import (
    AccountConfig,
    ContractConfig,
    ExpectedSchedule,
    SimulationTestScenario,
    SubTest,
)
from inception_sdk.test_framework.contracts.simulation.helper import (
    create_outbound_hard_settlement_posting_instruction_event,
)
from inception_sdk.test_framework.contracts.simulation.utils import SimulationTestCase

# inception sdk
from inception_sdk.vault.core_api import (
    DatetimeParameterValue,
    DecimalParameterValue,
    EnumerationParameterValue,
    StringParameterValue,
)

import tests.lending.due_amount_calculation.simulation.accounts as accounts
import tests.lending.due_amount_calculation.simulation.dimensions as dimensions
import tests.lending.due_amount_calculation.simulation.parameters as parameters
from tests.common.test_denomination import DEFAULT_DENOMINATION
from tests.sim_utils import NYC_TZ, create_update_pgtz_instruction

SMART_CONTRACT = "tests/lending/due_amount_calculation/simulation/smart_contract.py"

UTC = ZoneInfo("UTC")


class DueAmountCalculationScheduleBaseTest(SimulationTestCase):
    parameter_resource_dirs = [
        str(Path("src/feature_library/common/parameter_resource_defs")),
        str(Path("src/feature_library/lending/due_amount_calculation/parameter_resource_defs")),
    ]
    contract_filepaths = [str(SMART_CONTRACT)]
    internal_accounts = accounts.default_internal_accounts
    parameter_values = parameters.default_parameter_values
    parameters: list[Any] = []
    default_simulation_start_datetime = datetime(year=2026, month=1, day=5, tzinfo=UTC)

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
class DueAmountCalculationScheduleTest(DueAmountCalculationScheduleBaseTest):
    @pytest.mark.sim
    def test_fortnightly_schedule(self):
        start = self.default_simulation_start_datetime  # 2026-01-05 (Monday)
        # We run the simulation until after the 4th scheduled event
        # 2026-01-21 (Wed): Event 1 - executes
        # 2026-01-28 (Wed): Event 2 - skipped
        # 2026-02-04 (Wed): Event 3 - executes
        # 2026-02-11 (Wed): Event 4 - skipped
        end = start + relativedelta(weeks=5, days=3)  # 2026-02-12

        sub_tests = [
            SubTest(
                description="Seed initial PRINCIPAL balance on Day 1",
                events=[
                    create_outbound_hard_settlement_posting_instruction_event(
                        amount="1000",
                        event_datetime=start + relativedelta(minutes=1),
                        target_account_id=accounts.CUSTOMER_ACCOUNT,
                        target_account_address=lending_addresses.PRINCIPAL,
                        internal_account_id=accounts.INTERNAL_ACCOUNT,
                        denomination=DEFAULT_DENOMINATION,
                    )
                ],
                expected_balances_at_ts={
                    start + relativedelta(minutes=5): {
                        accounts.CUSTOMER_ACCOUNT: [
                            (dimensions.principal, Decimal("1000")),
                            (dimensions.principal_due, Decimal("0")),
                        ]
                    }
                },
            ),
            SubTest(
                description="Check weekly schedule with fortnightly postings",
                events=[],
                expected_schedules=[
                    ExpectedSchedule(
                        run_times=[
                            datetime(year=2026, month=1, day=21, tzinfo=UTC),
                            datetime(year=2026, month=1, day=28, tzinfo=UTC),
                            datetime(year=2026, month=2, day=4, tzinfo=UTC),
                            datetime(year=2026, month=2, day=11, tzinfo=UTC),
                        ],
                        event_id="DUE_AMOUNT_CALCULATION",
                        account_id=accounts.CUSTOMER_ACCOUNT,
                    )
                ],
                expected_balances_at_ts={
                    # Wed 2026-01-21 (Event 1: 16 days elapsed, week 2, executes)
                    datetime(year=2026, month=1, day=21, hour=0, minute=0, second=1, tzinfo=UTC): {
                        accounts.CUSTOMER_ACCOUNT: [
                            (dimensions.principal, Decimal("900")),
                            (dimensions.principal_due, Decimal("100")),
                        ]
                    },
                    # Wed 2026-01-28 (Event 2: 23 days elapsed, week 3, skipped)
                    datetime(year=2026, month=1, day=28, hour=0, minute=0, second=1, tzinfo=UTC): {
                        accounts.CUSTOMER_ACCOUNT: [
                            (dimensions.principal, Decimal("900")),
                            (dimensions.principal_due, Decimal("100")),
                        ]
                    },
                    # Wed 2026-02-04 (Event 3: 30 days elapsed, week 4, executes)
                    datetime(year=2026, month=2, day=4, hour=0, minute=0, second=1, tzinfo=UTC): {
                        accounts.CUSTOMER_ACCOUNT: [
                            (dimensions.principal, Decimal("800")),
                            (dimensions.principal_due, Decimal("200")),
                        ]
                    },
                    # Wed 2026-02-11 (Event 4: 37 days elapsed, week 5, skipped)
                    datetime(year=2026, month=2, day=11, hour=0, minute=0, second=1, tzinfo=UTC): {
                        accounts.CUSTOMER_ACCOUNT: [
                            (dimensions.principal, Decimal("800")),
                            (dimensions.principal_due, Decimal("200")),
                        ]
                    },
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
    def test_weekly_schedule(self):
        start = self.default_simulation_start_datetime  # 2026-01-05 (Monday)
        # We run the simulation for 3 weeks
        # 2026-01-12 (Mon): Event 1 - executes
        # 2026-01-19 (Mon): Event 2 - executes
        # 2026-01-26 (Mon): Event 3 - executes
        end = start + relativedelta(weeks=3, days=3)  # 2026-01-29

        weekly_parameters = {
            **self.parameter_values,
            due_calc.BILLING_FREQUENCY_PARAM_ID: EnumerationParameterValue(
                enumeration_value="weekly"
            ),
            due_calc.FIRST_DUE_DATE_PARAM_ID: DatetimeParameterValue(
                date_time_value=datetime(2026, 1, 12, tzinfo=UTC),
            ),
        }

        sub_tests = [
            SubTest(
                description="Seed initial PRINCIPAL balance on Day 1",
                events=[
                    create_outbound_hard_settlement_posting_instruction_event(
                        amount="1000",
                        event_datetime=start + relativedelta(minutes=1),
                        target_account_id=accounts.CUSTOMER_ACCOUNT,
                        target_account_address=lending_addresses.PRINCIPAL,
                        internal_account_id=accounts.INTERNAL_ACCOUNT,
                        denomination=DEFAULT_DENOMINATION,
                    )
                ],
                expected_balances_at_ts={
                    start + relativedelta(minutes=5): {
                        accounts.CUSTOMER_ACCOUNT: [
                            (dimensions.principal, Decimal("1000")),
                            (dimensions.principal_due, Decimal("0")),
                        ]
                    }
                },
            ),
            SubTest(
                description="Check weekly schedule with weekly postings",
                events=[],
                expected_schedules=[
                    ExpectedSchedule(
                        run_times=[
                            datetime(year=2026, month=1, day=12, tzinfo=UTC),
                            datetime(year=2026, month=1, day=19, tzinfo=UTC),
                            datetime(year=2026, month=1, day=26, tzinfo=UTC),
                        ],
                        event_id="DUE_AMOUNT_CALCULATION",
                        account_id=accounts.CUSTOMER_ACCOUNT,
                    )
                ],
                expected_balances_at_ts={
                    # Mon 2026-01-12 (Event 1: 7 days elapsed, week 1, executes)
                    datetime(year=2026, month=1, day=12, hour=0, minute=0, second=1, tzinfo=UTC): {
                        accounts.CUSTOMER_ACCOUNT: [
                            (dimensions.principal, Decimal("900")),
                            (dimensions.principal_due, Decimal("100")),
                        ]
                    },
                    # Mon 2026-01-19 (Event 2: 14 days elapsed, week 2, executes)
                    datetime(year=2026, month=1, day=19, hour=0, minute=0, second=1, tzinfo=UTC): {
                        accounts.CUSTOMER_ACCOUNT: [
                            (dimensions.principal, Decimal("800")),
                            (dimensions.principal_due, Decimal("200")),
                        ]
                    },
                    # Mon 2026-01-26 (Event 3: 21 days elapsed, week 3, executes)
                    datetime(year=2026, month=1, day=26, hour=0, minute=0, second=1, tzinfo=UTC): {
                        accounts.CUSTOMER_ACCOUNT: [
                            (dimensions.principal, Decimal("700")),
                            (dimensions.principal_due, Decimal("300")),
                        ]
                    },
                },
            ),
        ]

        test_scenario = self.get_simulation_test_scenario(
            start=start,
            end=end,
            sub_tests=sub_tests,
            parameter_values=weekly_parameters,
        )
        self.run_test_scenario(test_scenario)

    @pytest.mark.sim
    def test_monthly_schedule(self):
        start = self.default_simulation_start_datetime  # 2026-01-05 (Monday)
        # We run the simulation for 2 months
        # 2026-02-05 (Thu): Event 1 - executes
        # 2026-03-05 (Thu): Event 2 - executes
        end = start + relativedelta(months=2, days=3)  # 2026-03-08

        monthly_parameters = {
            **self.parameter_values,
            due_calc.BILLING_FREQUENCY_PARAM_ID: EnumerationParameterValue(
                enumeration_value="monthly"
            ),
            due_calc.FIRST_DUE_DATE_PARAM_ID: DatetimeParameterValue(
                date_time_value=datetime(2026, 2, 5, tzinfo=UTC),
            ),
        }

        sub_tests = [
            SubTest(
                description="Seed initial PRINCIPAL balance on Day 1",
                events=[
                    create_outbound_hard_settlement_posting_instruction_event(
                        amount="1000",
                        event_datetime=start + relativedelta(minutes=1),
                        target_account_id=accounts.CUSTOMER_ACCOUNT,
                        target_account_address=lending_addresses.PRINCIPAL,
                        internal_account_id=accounts.INTERNAL_ACCOUNT,
                        denomination=DEFAULT_DENOMINATION,
                    )
                ],
                expected_balances_at_ts={
                    start + relativedelta(minutes=5): {
                        accounts.CUSTOMER_ACCOUNT: [
                            (dimensions.principal, Decimal("1000")),
                            (dimensions.principal_due, Decimal("0")),
                        ]
                    }
                },
            ),
            SubTest(
                description="Check monthly schedule with monthly postings",
                events=[],
                expected_schedules=[
                    ExpectedSchedule(
                        run_times=[
                            datetime(year=2026, month=2, day=5, tzinfo=UTC),
                            datetime(year=2026, month=3, day=5, tzinfo=UTC),
                        ],
                        event_id="DUE_AMOUNT_CALCULATION",
                        account_id=accounts.CUSTOMER_ACCOUNT,
                    )
                ],
                expected_balances_at_ts={
                    # Thu 2026-02-05 (Event 1: 1 month elapsed, executes)
                    datetime(year=2026, month=2, day=5, hour=0, minute=0, second=1, tzinfo=UTC): {
                        accounts.CUSTOMER_ACCOUNT: [
                            (dimensions.principal, Decimal("900")),
                            (dimensions.principal_due, Decimal("100")),
                        ]
                    },
                    # Thu 2026-03-05 (Event 2: 2 months elapsed, executes)
                    datetime(year=2026, month=3, day=5, hour=0, minute=0, second=1, tzinfo=UTC): {
                        accounts.CUSTOMER_ACCOUNT: [
                            (dimensions.principal, Decimal("800")),
                            (dimensions.principal_due, Decimal("200")),
                        ]
                    },
                },
            ),
        ]

        test_scenario = self.get_simulation_test_scenario(
            start=start,
            end=end,
            sub_tests=sub_tests,
            parameter_values=monthly_parameters,
        )
        self.run_test_scenario(test_scenario)

    @pytest.mark.sim
    def test_monthly_schedule_no_first_due_date(self):
        start = self.default_simulation_start_datetime  # 2026-01-05 (Monday)
        # We run the simulation for 2 months
        # 2026-02-05 (Thu): Event 1 - executes
        # 2026-03-05 (Thu): Event 2 - executes
        end = start + relativedelta(months=2, days=3)  # 2026-03-08

        monthly_parameters = {
            **self.parameter_values,
            due_calc.BILLING_FREQUENCY_PARAM_ID: EnumerationParameterValue(
                enumeration_value="monthly"
            ),
            due_calc.DUE_AMOUNT_CALCULATION_DAY_PARAM_ID: DecimalParameterValue(
                decimal_value=Decimal("5")
            ),
        }
        monthly_parameters.pop(due_calc.FIRST_DUE_DATE_PARAM_ID, None)

        sub_tests = [
            SubTest(
                description="Seed initial PRINCIPAL balance on Day 1",
                events=[
                    create_outbound_hard_settlement_posting_instruction_event(
                        amount="1000",
                        event_datetime=start + relativedelta(minutes=1),
                        target_account_id=accounts.CUSTOMER_ACCOUNT,
                        target_account_address=lending_addresses.PRINCIPAL,
                        internal_account_id=accounts.INTERNAL_ACCOUNT,
                        denomination=DEFAULT_DENOMINATION,
                    )
                ],
                expected_balances_at_ts={
                    start + relativedelta(minutes=5): {
                        accounts.CUSTOMER_ACCOUNT: [
                            (dimensions.principal, Decimal("1000")),
                            (dimensions.principal_due, Decimal("0")),
                        ]
                    }
                },
            ),
            SubTest(
                description="Check monthly schedule with monthly postings and auto first due date",
                events=[],
                expected_schedules=[
                    ExpectedSchedule(
                        run_times=[
                            datetime(year=2026, month=2, day=5, tzinfo=UTC),
                            datetime(year=2026, month=3, day=5, tzinfo=UTC),
                        ],
                        event_id="DUE_AMOUNT_CALCULATION",
                        account_id=accounts.CUSTOMER_ACCOUNT,
                    )
                ],
                expected_balances_at_ts={
                    # Thu 2026-02-05 (Event 1: 1 month elapsed, executes)
                    datetime(year=2026, month=2, day=5, hour=0, minute=0, second=1, tzinfo=UTC): {
                        accounts.CUSTOMER_ACCOUNT: [
                            (dimensions.principal, Decimal("900")),
                            (dimensions.principal_due, Decimal("100")),
                        ]
                    },
                    # Thu 2026-03-05 (Event 2: 2 months elapsed, executes)
                    datetime(year=2026, month=3, day=5, hour=0, minute=0, second=1, tzinfo=UTC): {
                        accounts.CUSTOMER_ACCOUNT: [
                            (dimensions.principal, Decimal("800")),
                            (dimensions.principal_due, Decimal("200")),
                        ]
                    },
                },
            ),
        ]

        test_scenario = self.get_simulation_test_scenario(
            start=start,
            end=end,
            sub_tests=sub_tests,
            parameter_values=monthly_parameters,
        )
        self.run_test_scenario(test_scenario)

    @pytest.mark.sim
    def test_fortnightly_schedule_timezone_awareness(self):
        # NY Time is UTC-5 in winter.
        # Start (Activation): 2026-01-05 02:00:00 UTC (local NY: 2026-01-04 21:00:00 EST)
        # Event 1:            2026-01-18 06:00:00 UTC (local NY: 2026-01-18 01:00:00 EST)
        # UTC elapsed days: (18 - 5) = 13 (week 1 - odd - would skip in UTC)
        # NY elapsed days:  (18 - 4) = 14 (week 2 - even - should NOT skip in NY)
        start = datetime(year=2026, month=1, day=5, hour=2, tzinfo=UTC)
        end = start + relativedelta(weeks=2, days=1)  # 2026-01-20

        ny_parameters = {
            **self.parameter_values,
            due_calc.BILLING_FREQUENCY_PARAM_ID: EnumerationParameterValue(
                enumeration_value="fortnightly"
            ),
            due_calc.FIRST_DUE_DATE_PARAM_ID: DatetimeParameterValue(
                date_time_value=datetime(2026, 1, 18, 1, tzinfo=NYC_TZ),
            ),
            due_calc.DUE_AMOUNT_CALCULATION_TIME_PARAM_ID: StringParameterValue(
                string_value="01:00:00"
            ),
        }

        sub_tests = [
            SubTest(
                description="Set the Processing Group Timezone to America/New_York and seed "
                + "Principal on Day 1",
                events=[
                    create_update_pgtz_instruction(start, timezone=NYC_TZ),
                    create_outbound_hard_settlement_posting_instruction_event(
                        amount="1000",
                        event_datetime=start + relativedelta(minutes=1),
                        target_account_id=accounts.CUSTOMER_ACCOUNT,
                        target_account_address=lending_addresses.PRINCIPAL,
                        internal_account_id=accounts.INTERNAL_ACCOUNT,
                        denomination=DEFAULT_DENOMINATION,
                    ),
                ],
                expected_balances_at_ts={
                    start + relativedelta(minutes=5): {
                        accounts.CUSTOMER_ACCOUNT: [
                            (dimensions.principal, Decimal("1000")),
                            (dimensions.principal_due, Decimal("0")),
                        ]
                    }
                },
            ),
            SubTest(
                description="Check schedule executes on even week in NY timezone despite odd week"
                + " in UTC",
                events=[],
                expected_schedules=[
                    ExpectedSchedule(
                        run_times=[
                            datetime(year=2026, month=1, day=18, hour=6, tzinfo=UTC),
                        ],
                        event_id="DUE_AMOUNT_CALCULATION",
                        account_id=accounts.CUSTOMER_ACCOUNT,
                    )
                ],
                expected_balances_at_ts={
                    # Sun 2026-01-18 06:00:00 UTC (Local 2026-01-18 01:00:00 EST)
                    # It executes, generating dues!
                    datetime(year=2026, month=1, day=18, hour=6, minute=0, second=1, tzinfo=UTC): {
                        accounts.CUSTOMER_ACCOUNT: [
                            (dimensions.principal, Decimal("900")),
                            (dimensions.principal_due, Decimal("100")),
                        ]
                    },
                },
            ),
        ]

        test_scenario = self.get_simulation_test_scenario(
            start=start,
            end=end,
            sub_tests=sub_tests,
            parameter_values=ny_parameters,
        )
        self.run_test_scenario(test_scenario)

    @pytest.mark.sim
    def test_monthly_schedule_short_month_clamping_persistence(self):
        # Jan 30, 2026 is a Friday
        start = datetime(year=2026, month=1, day=30, tzinfo=UTC)
        # We run the simulation for 2 months
        # 2026-02-28 (Sat): Event 1 - executes (clamped to end of February)
        # 2026-03-31 (Tue): Event 2 - executes (recovers to 31st!)
        end = start + relativedelta(months=2, days=5)  # 2026-04-04

        monthly_parameters = {
            **self.parameter_values,
            due_calc.BILLING_FREQUENCY_PARAM_ID: EnumerationParameterValue(
                enumeration_value="monthly"
            ),
            due_calc.DUE_AMOUNT_CALCULATION_DAY_PARAM_ID: DecimalParameterValue(
                decimal_value=Decimal("31")
            ),
        }
        monthly_parameters.pop(due_calc.FIRST_DUE_DATE_PARAM_ID, None)

        sub_tests = [
            SubTest(
                description="Seed initial PRINCIPAL balance on Day 1",
                events=[
                    create_outbound_hard_settlement_posting_instruction_event(
                        amount="1000",
                        event_datetime=start + relativedelta(minutes=1),
                        target_account_id=accounts.CUSTOMER_ACCOUNT,
                        target_account_address=lending_addresses.PRINCIPAL,
                        internal_account_id=accounts.INTERNAL_ACCOUNT,
                        denomination=DEFAULT_DENOMINATION,
                    )
                ],
                expected_balances_at_ts={
                    start + relativedelta(minutes=5): {
                        accounts.CUSTOMER_ACCOUNT: [
                            (dimensions.principal, Decimal("1000")),
                            (dimensions.principal_due, Decimal("0")),
                        ]
                    }
                },
            ),
            SubTest(
                description="Check monthly schedule snaps to Feb 28 and recovers to Mar 31",
                events=[],
                expected_schedules=[
                    ExpectedSchedule(
                        run_times=[
                            datetime(year=2026, month=2, day=28, tzinfo=UTC),
                            datetime(year=2026, month=3, day=31, tzinfo=UTC),
                        ],
                        event_id="DUE_AMOUNT_CALCULATION",
                        account_id=accounts.CUSTOMER_ACCOUNT,
                    )
                ],
                expected_balances_at_ts={
                    # Sat 2026-02-28 (Event 1: clamped to Feb 28)
                    datetime(year=2026, month=2, day=28, hour=0, minute=0, second=1, tzinfo=UTC): {
                        accounts.CUSTOMER_ACCOUNT: [
                            (dimensions.principal, Decimal("900")),
                            (dimensions.principal_due, Decimal("100")),
                        ]
                    },
                    # Tue 2026-03-31 (Event 2: recovers to Mar 31)
                    datetime(year=2026, month=3, day=31, hour=0, minute=0, second=1, tzinfo=UTC): {
                        accounts.CUSTOMER_ACCOUNT: [
                            (dimensions.principal, Decimal("800")),
                            (dimensions.principal_due, Decimal("200")),
                        ]
                    },
                },
            ),
        ]

        test_scenario = self.get_simulation_test_scenario(
            start=start,
            end=end,
            sub_tests=sub_tests,
            parameter_values=monthly_parameters,
        )
        self.run_test_scenario(test_scenario)

    @pytest.mark.sim
    def test_monthly_schedule_short_month_clamping_persistence_non_utc(self):
        # Activation at 2026-01-30 02:00:00 UTC (Local NY: 2026-01-29 21:00:00 EST)
        # Calc Day: 31st
        # Run 1 (Feb): 2026-02-28 01:00:00 EST -> 2026-02-28 06:00:00 UTC (clamped to end of Feb)
        # Run 2 (Mar): 2026-03-31 01:00:00 EDT -> 2026-03-31 05:00:00 UTC (recovers to 31st)
        # Run 3 (Apr): 2026-04-30 01:00:00 EDT -> 2026-04-30 05:00:00 UTC (clamped to 30th)
        # Run 4 (May): 2026-05-31 01:00:00 EDT -> 2026-05-31 05:00:00 UTC (recovers to 31st)
        # Run 5 (Jun): 2026-06-30 01:00:00 EDT -> 2026-06-30 05:00:00 UTC (clamped to 30th)
        # Run 6 (Jul): 2026-07-31 01:00:00 EDT -> 2026-07-31 05:00:00 UTC (recovers to 31st)
        start = datetime(year=2026, month=1, day=30, hour=2, tzinfo=UTC)
        end = start + relativedelta(months=6, days=5)  # 2026-08-04

        ny_parameters = {
            **self.parameter_values,
            due_calc.BILLING_FREQUENCY_PARAM_ID: EnumerationParameterValue(
                enumeration_value="monthly"
            ),
            due_calc.DUE_AMOUNT_CALCULATION_DAY_PARAM_ID: DecimalParameterValue(
                decimal_value=Decimal("31")
            ),
            due_calc.DUE_AMOUNT_CALCULATION_TIME_PARAM_ID: StringParameterValue(
                string_value="01:00:00"
            ),
        }
        ny_parameters.pop(due_calc.FIRST_DUE_DATE_PARAM_ID, None)

        sub_tests = [
            SubTest(
                description="Set the Processing Group Timezone to America/New_York and seed "
                + "Principal on Day 1",
                events=[
                    create_update_pgtz_instruction(start, timezone=NYC_TZ),
                    create_outbound_hard_settlement_posting_instruction_event(
                        amount="1000",
                        event_datetime=start + relativedelta(minutes=1),
                        target_account_id=accounts.CUSTOMER_ACCOUNT,
                        target_account_address=lending_addresses.PRINCIPAL,
                        internal_account_id=accounts.INTERNAL_ACCOUNT,
                        denomination=DEFAULT_DENOMINATION,
                    ),
                ],
                expected_balances_at_ts={
                    start + relativedelta(minutes=5): {
                        accounts.CUSTOMER_ACCOUNT: [
                            (dimensions.principal, Decimal("1000")),
                            (dimensions.principal_due, Decimal("0")),
                        ]
                    }
                },
            ),
            SubTest(
                description="Check monthly schedule clamps in NY timezone",
                events=[],
                expected_schedules=[
                    ExpectedSchedule(
                        run_times=[
                            datetime(year=2026, month=2, day=28, hour=6, tzinfo=UTC),
                            datetime(year=2026, month=3, day=31, hour=5, tzinfo=UTC),
                            datetime(year=2026, month=4, day=30, hour=5, tzinfo=UTC),
                            datetime(year=2026, month=5, day=31, hour=5, tzinfo=UTC),
                            datetime(year=2026, month=6, day=30, hour=5, tzinfo=UTC),
                            datetime(year=2026, month=7, day=31, hour=5, tzinfo=UTC),
                        ],
                        event_id="DUE_AMOUNT_CALCULATION",
                        account_id=accounts.CUSTOMER_ACCOUNT,
                    )
                ],
                expected_balances_at_ts={
                    # Run 1: Local NY: 2026-02-28 01:00:00 EST -> 2026-02-28 06:00:00 UTC
                    datetime(year=2026, month=2, day=28, hour=6, minute=0, second=1, tzinfo=UTC): {
                        accounts.CUSTOMER_ACCOUNT: [
                            (dimensions.principal, Decimal("900")),
                            (dimensions.principal_due, Decimal("100")),
                        ]
                    },
                    # Run 2: Local NY: 2026-03-31 01:00:00 EDT -> 2026-03-31 05:00:00 UTC
                    datetime(year=2026, month=3, day=31, hour=5, minute=0, second=1, tzinfo=UTC): {
                        accounts.CUSTOMER_ACCOUNT: [
                            (dimensions.principal, Decimal("800")),
                            (dimensions.principal_due, Decimal("200")),
                        ]
                    },
                    # Run 3: Local NY: 2026-04-30 01:00:00 EDT -> 2026-04-30 05:00:00 UTC
                    datetime(year=2026, month=4, day=30, hour=5, minute=0, second=1, tzinfo=UTC): {
                        accounts.CUSTOMER_ACCOUNT: [
                            (dimensions.principal, Decimal("700")),
                            (dimensions.principal_due, Decimal("300")),
                        ]
                    },
                    # Run 4: Local NY: 2026-05-31 01:00:00 EDT -> 2026-05-31 05:00:00 UTC
                    datetime(year=2026, month=5, day=31, hour=5, minute=0, second=1, tzinfo=UTC): {
                        accounts.CUSTOMER_ACCOUNT: [
                            (dimensions.principal, Decimal("600")),
                            (dimensions.principal_due, Decimal("400")),
                        ]
                    },
                    # Run 5: Local NY: 2026-06-30 01:00:00 EDT -> 2026-06-30 05:00:00 UTC
                    datetime(year=2026, month=6, day=30, hour=5, minute=0, second=1, tzinfo=UTC): {
                        accounts.CUSTOMER_ACCOUNT: [
                            (dimensions.principal, Decimal("500")),
                            (dimensions.principal_due, Decimal("500")),
                        ]
                    },
                    # Run 6: Local NY: 2026-07-31 01:00:00 EDT -> 2026-07-31 05:00:00 UTC
                    datetime(year=2026, month=7, day=31, hour=5, minute=0, second=1, tzinfo=UTC): {
                        accounts.CUSTOMER_ACCOUNT: [
                            (dimensions.principal, Decimal("400")),
                            (dimensions.principal_due, Decimal("600")),
                        ]
                    },
                },
            ),
        ]

        test_scenario = self.get_simulation_test_scenario(
            start=start,
            end=end,
            sub_tests=sub_tests,
            parameter_values=ny_parameters,
        )
        self.run_test_scenario(test_scenario)

    @pytest.mark.sim
    def test_weekly_schedule_modulo_day(self):
        start = self.default_simulation_start_datetime  # 2026-01-05 (Monday)
        # We run the simulation for 4 weeks (weekly schedule auto-calculation
        # starts at least 1 week after activation)
        # 2026-01-18 (Sun): Event 1 - executes (modulo weekday 6)
        # 2026-01-25 (Sun): Event 2 - executes (modulo weekday 6)
        # 2026-02-01 (Sun): Event 3 - executes (modulo weekday 6)
        end = start + relativedelta(weeks=4, days=3)  # 2026-02-05

        weekly_parameters = {
            **self.parameter_values,
            due_calc.BILLING_FREQUENCY_PARAM_ID: EnumerationParameterValue(
                enumeration_value="weekly"
            ),
            due_calc.DUE_AMOUNT_CALCULATION_DAY_PARAM_ID: DecimalParameterValue(
                decimal_value=Decimal("28")
            ),
        }
        weekly_parameters.pop(due_calc.FIRST_DUE_DATE_PARAM_ID, None)

        sub_tests = [
            SubTest(
                description="Seed initial PRINCIPAL balance on Day 1",
                events=[
                    create_outbound_hard_settlement_posting_instruction_event(
                        amount="1000",
                        event_datetime=start + relativedelta(minutes=1),
                        target_account_id=accounts.CUSTOMER_ACCOUNT,
                        target_account_address=lending_addresses.PRINCIPAL,
                        internal_account_id=accounts.INTERNAL_ACCOUNT,
                        denomination=DEFAULT_DENOMINATION,
                    )
                ],
                expected_balances_at_ts={
                    start + relativedelta(minutes=5): {
                        accounts.CUSTOMER_ACCOUNT: [
                            (dimensions.principal, Decimal("1000")),
                            (dimensions.principal_due, Decimal("0")),
                        ]
                    }
                },
            ),
            SubTest(
                description="Check weekly schedule on Sunday using modulo of calc day 28",
                events=[],
                expected_schedules=[
                    ExpectedSchedule(
                        run_times=[
                            datetime(year=2026, month=1, day=18, tzinfo=UTC),
                            datetime(year=2026, month=1, day=25, tzinfo=UTC),
                            datetime(year=2026, month=2, day=1, tzinfo=UTC),
                        ],
                        event_id="DUE_AMOUNT_CALCULATION",
                        account_id=accounts.CUSTOMER_ACCOUNT,
                    )
                ],
                expected_balances_at_ts={
                    # Sun 2026-01-18 (Event 1)
                    datetime(year=2026, month=1, day=18, hour=0, minute=0, second=1, tzinfo=UTC): {
                        accounts.CUSTOMER_ACCOUNT: [
                            (dimensions.principal, Decimal("900")),
                            (dimensions.principal_due, Decimal("100")),
                        ]
                    },
                    # Sun 2026-01-25 (Event 2)
                    datetime(year=2026, month=1, day=25, hour=0, minute=0, second=1, tzinfo=UTC): {
                        accounts.CUSTOMER_ACCOUNT: [
                            (dimensions.principal, Decimal("800")),
                            (dimensions.principal_due, Decimal("200")),
                        ]
                    },
                    # Sun 2026-02-01 (Event 3)
                    datetime(year=2026, month=2, day=1, hour=0, minute=0, second=1, tzinfo=UTC): {
                        accounts.CUSTOMER_ACCOUNT: [
                            (dimensions.principal, Decimal("700")),
                            (dimensions.principal_due, Decimal("300")),
                        ]
                    },
                },
            ),
        ]

        test_scenario = self.get_simulation_test_scenario(
            start=start,
            end=end,
            sub_tests=sub_tests,
            parameter_values=weekly_parameters,
        )
        self.run_test_scenario(test_scenario)
