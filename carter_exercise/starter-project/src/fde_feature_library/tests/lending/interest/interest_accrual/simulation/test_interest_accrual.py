# standard libs
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

# third party
import pytest
from dateutil.relativedelta import relativedelta
from parameterized import parameterized

import feature_library.lending.addresses as lending_addresses

# inception sdk
from inception_sdk.test_framework.contracts.simulation.data_objects.data_objects import (
    AccountConfig,
    ContractConfig,
    ExpectedSchedule,
    SimulationTestScenario,
    SubTest,
)
from inception_sdk.test_framework.contracts.simulation.helper import (
    create_outbound_hard_settlement_posting_instruction_event,
    create_parameter_value,
)
from inception_sdk.test_framework.contracts.simulation.utils import SimulationTestCase
from inception_sdk.vault.core_api import DecimalParameterValue
from inception_sdk.vault.sim_api.contract_sim import CreateParameterValue

import tests.lending.interest.interest_accrual.fixed_rate_smart_contract as fixed_rate_sc
import tests.lending.interest.interest_accrual.simulation.accounts as accounts
import tests.lending.interest.interest_accrual.simulation.dimensions as dimensions
import tests.lending.interest.interest_accrual.simulation.parameters as parameters
import tests.lending.interest.interest_accrual.variable_rate_smart_contract as variable_rate_sc
from tests.common.test_denomination import DEFAULT_DENOMINATION

# features
from tests.sim_utils import create_update_pgtz_instruction, timezones

FIXED_RATE_CONTRACT = "tests/lending/interest/interest_accrual/fixed_rate_smart_contract.py"
VARIABLE_RATE_CONTRACT = "tests/lending/interest/interest_accrual/variable_rate_smart_contract.py"

UTC = ZoneInfo("UTC")


class InterestAccrualBaseTest(SimulationTestCase):
    parameter_resource_dirs = [
        str(Path("src/feature_library/lending/interest/parameter_resource_defs")),
        str(Path("src/feature_library/lending/interest/secondary/parameter_resource_defs")),
        str(Path("src/feature_library/common/parameter_resource_defs")),
    ]
    internal_accounts = accounts.default_internal_accounts
    # Start at Jan 1st 00:00:00
    default_simulation_start_datetime = datetime(
        year=2026, month=1, day=1, hour=0, minute=0, second=0, tzinfo=UTC
    )

    def get_simulation_test_scenario(
        self,
        start,
        end,
        sub_tests,
        contract_filepath,
        parameter_values,
        debug=True,
        default_tz: ZoneInfo | None = None,
    ):
        localised_sub_tests: list[SubTest] = [
            SubTest(
                description="Set the Default Processing Group Timezone",
                events=[create_update_pgtz_instruction(start, timezone=default_tz or UTC)],
            )
        ] + sub_tests

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
            sub_tests=localised_sub_tests,
            contract_config=contract_config,
            internal_accounts=self.internal_accounts,
            debug=debug,
            use_v1_accounts=False,
        )


@pytest.mark.sim
class InterestAccrualFixedRateTest(InterestAccrualBaseTest):
    contract_filepaths = [FIXED_RATE_CONTRACT]

    @classmethod
    def setUpClass(cls):
        cls.contract_filepath = FIXED_RATE_CONTRACT
        super().setUpClass()

    @parameterized.expand(timezones)
    @pytest.mark.sim
    def test_fixed_rate_accrual(self, default_tz: ZoneInfo):
        start = datetime(year=2026, month=1, day=1, hour=0, minute=0, second=0, tzinfo=default_tz)
        posting = start + relativedelta(seconds=5)
        accrual_event = start.replace(hour=23, minute=59, second=59)
        end_time = accrual_event + relativedelta(seconds=1)

        sub_tests = [
            SubTest(
                description="Manual disbursal",
                events=[
                    create_outbound_hard_settlement_posting_instruction_event(
                        amount="1000",
                        event_datetime=posting,
                        target_account_id=accounts.CUSTOMER_ACCOUNT,
                        internal_account_id=accounts.DEPOSIT_ACCOUNT,
                        target_account_address=lending_addresses.PRINCIPAL,
                        denomination=DEFAULT_DENOMINATION,
                    )
                ],
                expected_balances_at_ts={
                    posting: {
                        accounts.CUSTOMER_ACCOUNT: [
                            (dimensions.PRINCIPAL, Decimal("1000")),
                        ],
                    }
                },
            ),
            SubTest(
                description="Check schedule creation",
                events=[],
                expected_schedules=[
                    ExpectedSchedule(
                        run_times=[accrual_event.astimezone(UTC)],
                        event_id=fixed_rate_sc.interest_accrual.ACCRUAL_EVENT,
                        account_id=accounts.CUSTOMER_ACCOUNT,
                    )
                ],
            ),
            SubTest(
                description="Interest accrual",
                # 1000 * (0.12 / 365) = 0.328767... -> rounded to 5dp = 0.32877
                expected_balances_at_ts={
                    end_time: {
                        accounts.CUSTOMER_ACCOUNT: [
                            (dimensions.ACCRUED_INTEREST_RECEIVABLE, Decimal("0.32877")),
                        ],
                    }
                },
            ),
        ]

        test_scenario = self.get_simulation_test_scenario(
            start=start,
            end=end_time,
            sub_tests=sub_tests,
            contract_filepath=self.contract_filepath,
            parameter_values=parameters.fixed_rate_parameter_values,
            default_tz=default_tz,
        )
        self.run_test_scenario(test_scenario)

    @parameterized.expand(timezones)
    @pytest.mark.sim
    def test_fixed_rate_accrual_zero_principal(self, default_tz: ZoneInfo):
        start = datetime(year=2026, month=1, day=1, hour=0, minute=0, second=0, tzinfo=default_tz)
        accrual_event = start.replace(hour=23, minute=59, second=59)
        end_time = accrual_event + relativedelta(seconds=1)

        sub_tests = [
            SubTest(
                description="Check schedule creation",
                events=[],
                expected_schedules=[
                    ExpectedSchedule(
                        run_times=[accrual_event.astimezone(UTC)],
                        event_id=fixed_rate_sc.interest_accrual.ACCRUAL_EVENT,
                        account_id=accounts.CUSTOMER_ACCOUNT,
                    )
                ],
            ),
            SubTest(
                description="No interest accrual for zero principal",
                expected_balances_at_ts={
                    end_time: {
                        accounts.CUSTOMER_ACCOUNT: [
                            (dimensions.ACCRUED_INTEREST_RECEIVABLE, Decimal("0")),
                        ],
                    }
                },
            ),
        ]

        test_scenario = self.get_simulation_test_scenario(
            start=start,
            end=end_time,
            sub_tests=sub_tests,
            contract_filepath=self.contract_filepath,
            parameter_values=parameters.fixed_rate_parameter_values,
            default_tz=default_tz,
        )
        self.run_test_scenario(test_scenario)


@pytest.mark.sim
class InterestAccrualVariableRateTest(InterestAccrualBaseTest):
    contract_filepaths = [VARIABLE_RATE_CONTRACT]

    @classmethod
    def setUpClass(cls):
        cls.contract_filepath = VARIABLE_RATE_CONTRACT
        super().setUpClass()

    @parameterized.expand(timezones)
    @pytest.mark.sim
    def test_variable_rate_accrual(self, default_tz: ZoneInfo):
        start = datetime(year=2026, month=1, day=1, hour=0, minute=0, second=0, tzinfo=default_tz)
        posting = start + relativedelta(seconds=5)
        first_accrual_event = start.replace(hour=23, minute=59, second=59)
        rate_change = first_accrual_event + relativedelta(hours=1)
        second_accrual_event = first_accrual_event + relativedelta(days=1)
        second_rate_change = second_accrual_event + relativedelta(hours=1)
        third_accrual_event = second_accrual_event + relativedelta(days=1)
        end_time = third_accrual_event + relativedelta(seconds=1)

        sub_tests = [
            SubTest(
                description="Manual disbursal",
                events=[
                    create_outbound_hard_settlement_posting_instruction_event(
                        amount="1200",
                        event_datetime=posting,
                        target_account_id=accounts.CUSTOMER_ACCOUNT,
                        internal_account_id=accounts.DEPOSIT_ACCOUNT,
                        target_account_address=lending_addresses.PRINCIPAL,
                        denomination=DEFAULT_DENOMINATION,
                    )
                ],
                expected_balances_at_ts={
                    posting: {
                        accounts.CUSTOMER_ACCOUNT: [
                            (dimensions.PRINCIPAL, Decimal("1200")),
                        ],
                    }
                },
            ),
            SubTest(
                description="First Accrual",
                # 1200 * ((0.4 + 0.5 + 0.1) / 360) = 1200 * 0.00027777... = 0.333333... -> 0.33333
                expected_balances_at_ts={
                    first_accrual_event: {
                        accounts.CUSTOMER_ACCOUNT: [
                            (dimensions.ACCRUED_INTEREST_RECEIVABLE, Decimal("0.33333")),
                        ],
                    }
                },
            ),
            SubTest(
                description="Change rates",
                events=[
                    create_parameter_value(
                        timestamp=rate_change,
                        parameter_value=CreateParameterValue(
                            parameter_id=variable_rate_sc.variable_rate.BASE_RATE_PARAM_ID,
                            value=DecimalParameterValue(decimal_value=Decimal("-0.2")),
                            account_id=accounts.CUSTOMER_ACCOUNT,
                        ),
                    ),
                    create_parameter_value(
                        timestamp=rate_change,
                        parameter_value=CreateParameterValue(
                            parameter_id=variable_rate_sc.variable_rate.VARIABLE_RATE_ADJUSTMENT_PARAM_ID,  # noqa: E501
                            value=DecimalParameterValue(decimal_value=Decimal("0.1")),
                            account_id=accounts.CUSTOMER_ACCOUNT,
                        ),
                    ),
                ],
            ),
            SubTest(
                description="Second Accrual",
                # The rate change results in a total rate of 0.05 + 0.1 - 0.2 = -0.05
                # The floor of 0.01 is applied.
                # 1200 * (0.01 / 360) = 1200 * 0.000027777... = 0.033333... -> 0.03333
                # Total accrued: 0.33333 + 0.03333 = 0.36666
                expected_balances_at_ts={
                    second_accrual_event: {
                        accounts.CUSTOMER_ACCOUNT: [
                            (dimensions.ACCRUED_INTEREST_RECEIVABLE, Decimal("0.36666")),
                        ],
                    }
                },
            ),
            SubTest(
                description="Change rates (to higher than cap)",
                events=[
                    create_parameter_value(
                        timestamp=second_rate_change,
                        parameter_value=CreateParameterValue(
                            parameter_id=variable_rate_sc.variable_rate.BASE_RATE_PARAM_ID,
                            value=DecimalParameterValue(decimal_value=Decimal("0.6")),
                            account_id=accounts.CUSTOMER_ACCOUNT,
                        ),
                    ),
                ],
            ),
            SubTest(
                description="Third Accrual",
                # The rate change results in a total rate of 0.05 + 0.1 + 0.6 = 0.75
                # The cap of 0.6 is applied.
                # 1200 * (0.6 / 360) = 2.0
                # Total accrued: 0.36666 + 2.0 = 2.36666
                expected_balances_at_ts={
                    third_accrual_event: {
                        accounts.CUSTOMER_ACCOUNT: [
                            (dimensions.ACCRUED_INTEREST_RECEIVABLE, Decimal("2.36666")),
                        ],
                    }
                },
            ),
            SubTest(
                description="Check schedule creation",
                events=[],
                expected_schedules=[
                    ExpectedSchedule(
                        run_times=[
                            first_accrual_event.astimezone(UTC),
                            second_accrual_event.astimezone(UTC),
                            third_accrual_event.astimezone(UTC),
                        ],
                        event_id=variable_rate_sc.interest_accrual.ACCRUAL_EVENT,
                        account_id=accounts.CUSTOMER_ACCOUNT,
                    )
                ],
            ),
        ]

        test_scenario = self.get_simulation_test_scenario(
            start=start,
            end=end_time,
            sub_tests=sub_tests,
            contract_filepath=self.contract_filepath,
            parameter_values=parameters.variable_rate_parameter_values,
            default_tz=default_tz,
        )
        self.run_test_scenario(test_scenario)

    @parameterized.expand(timezones)
    @pytest.mark.sim
    def test_variable_rate_accrual_zero_principal(self, default_tz: ZoneInfo):
        start = datetime(year=2026, month=1, day=1, hour=0, minute=0, second=0, tzinfo=default_tz)
        accrual_event = start.replace(hour=23, minute=59, second=59)
        end_time = accrual_event + relativedelta(seconds=1)

        sub_tests = [
            SubTest(
                description="Check schedule creation",
                events=[],
                expected_schedules=[
                    ExpectedSchedule(
                        run_times=[accrual_event.astimezone(UTC)],
                        event_id=variable_rate_sc.interest_accrual.ACCRUAL_EVENT,
                        account_id=accounts.CUSTOMER_ACCOUNT,
                    )
                ],
            ),
            SubTest(
                description="No interest accrual for zero principal",
                expected_balances_at_ts={
                    end_time: {
                        accounts.CUSTOMER_ACCOUNT: [
                            (dimensions.ACCRUED_INTEREST_RECEIVABLE, Decimal("0")),
                        ],
                    }
                },
            ),
        ]

        test_scenario = self.get_simulation_test_scenario(
            start=start,
            end=end_time,
            sub_tests=sub_tests,
            contract_filepath=self.contract_filepath,
            parameter_values=parameters.variable_rate_parameter_values,
            default_tz=default_tz,
        )
        self.run_test_scenario(test_scenario)
