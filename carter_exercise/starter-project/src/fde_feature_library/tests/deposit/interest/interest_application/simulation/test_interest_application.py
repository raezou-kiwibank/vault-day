# standard libs
import logging
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
from dateutil.relativedelta import relativedelta
from parameterized import parameterized

# library
import feature_library.deposit.addresses as deposit_addresses
import feature_library.deposit.interest.interest_accrual as interest_accrual
import feature_library.deposit.interest.interest_application as interest_application

# contracts api
from contracts_api import DEFAULT_ADDRESS, DEFAULT_ASSET

# inception sdk
from inception_sdk.test_framework.contracts.simulation.data_objects.data_objects import (
    AccountConfig,
    ContractConfig,
    ExpectedSchedule,
    SimulationTestScenario,
    SubTest,
)
from inception_sdk.test_framework.contracts.simulation.helper import (
    create_inbound_hard_settlement_instruction,
    create_inbound_hard_settlement_posting_instruction_event,
)
from inception_sdk.test_framework.contracts.simulation.utils import SimulationTestCase
from inception_sdk.vault.core_api import EnumerationParameterValue

import tests.deposit.interest.interest_application.simulation.accounts as accounts
import tests.deposit.interest.interest_application.simulation.dimensions as dimensions
import tests.deposit.interest.interest_application.simulation.parameters as parameters
from tests.sim_utils import UTC, create_update_pgtz_instruction, timezones

SMART_CONTRACT = str(Path("tests/deposit/interest/interest_application/smart_contract.py"))
OVERDRAFT_INTEREST_APP_SC = str(
    Path("tests/deposit/interest/interest_application/overdraft_interest_app_sc.py")
)

log = logging.getLogger(
    "inception_sdk.test_framework.contracts.simulation.vault_caller.sim_test_request_logger"
)
handler = logging.FileHandler("/tmp/req.json", mode="w")
log.propagate = False
log.addHandler(handler)
log.setLevel(logging.DEBUG)
handler.setLevel(logging.DEBUG)


class InterestApplicationBaseTest(SimulationTestCase):
    parameter_resource_dirs = [
        "src/feature_library/deposit/interest/parameter_resource_defs",
        "src/feature_library/common/parameter_resource_defs",
    ]
    contract_filepaths = [str(SMART_CONTRACT), str(OVERDRAFT_INTEREST_APP_SC)]
    internal_accounts = accounts.default_internal_accounts
    parameter_values = parameters.default_parameter_values
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
        default_tz: ZoneInfo | None = None,
        contract_filepath: str | None = None,
    ):
        localised_sub_tests: list[SubTest] = [
            SubTest(
                description="Set the Default Processing Group Timezone",
                events=[create_update_pgtz_instruction(start, timezone=default_tz or UTC)],
            )
        ] + sub_tests

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
            sub_tests=localised_sub_tests,
            contract_config=contract_config,
            internal_accounts=self.internal_accounts or internal_accounts,
            debug=debug,
            use_v1_accounts=False,
        )


class InterestApplicationTest(InterestApplicationBaseTest):
    @parameterized.expand(timezones)
    @pytest.mark.sim
    def test_schedule_creation(self, default_tz: ZoneInfo):
        start = datetime(year=2026, month=1, day=1, tzinfo=default_tz)
        # Application at 00:00:01 on the 1st of each month.
        # Start is Jan 1st 00:00:00, so first application is Feb 1st 00:00:01.
        end = start + relativedelta(months=1, seconds=2)

        sub_tests = [
            SubTest(
                description="Check schedule creation",
                events=[],
                expected_schedules=[
                    ExpectedSchedule(
                        run_times=[(start + relativedelta(months=1, seconds=1)).astimezone(UTC)],
                        event_id="APPLY_INTEREST",
                        account_id=accounts.CUSTOMER_ACCOUNT,
                    )
                ],
            )
        ]
        test_scenario = self.get_simulation_test_scenario(
            start=start, end=end, sub_tests=sub_tests, default_tz=default_tz
        )
        self.run_test_scenario(test_scenario)

    @parameterized.expand(timezones)
    @pytest.mark.sim
    def test_quarterly_schedule_creation(self, default_tz: ZoneInfo):
        start = datetime(year=2026, month=1, day=1, tzinfo=default_tz)
        # Application at 00:00:01 on the 1st of each month.
        # Start is Jan 1st, frequency is quarterly, so first application is April 1st.
        end = start + relativedelta(months=3, seconds=2)

        parameter_values = {
            **self.parameter_values,
            interest_application.INTEREST_APPLICATION_FREQUENCY_PARAM_ID: EnumerationParameterValue(
                enumeration_value="quarterly"
            ),
        }

        sub_tests = [
            SubTest(
                description="Check quarterly schedule creation",
                events=[],
                expected_schedules=[
                    ExpectedSchedule(
                        run_times=[(start + relativedelta(months=3, seconds=1)).astimezone(UTC)],
                        event_id="APPLY_INTEREST",
                        account_id=accounts.CUSTOMER_ACCOUNT,
                    )
                ],
            )
        ]
        test_scenario = self.get_simulation_test_scenario(
            start=start,
            end=end,
            sub_tests=sub_tests,
            parameter_values=parameter_values,
            default_tz=default_tz,
        )
        self.run_test_scenario(test_scenario)

    @parameterized.expand(timezones)
    @pytest.mark.sim
    def test_annual_schedule_creation(self, default_tz: ZoneInfo):
        start = datetime(year=2026, month=1, day=1, tzinfo=default_tz)
        # Application at 00:00:01 on the 1st of each month.
        # Start is Jan 1st, frequency is annually, so first application is Jan 1st of next year.
        end = start + relativedelta(years=1, seconds=2)

        parameter_values = {
            **self.parameter_values,
            interest_application.INTEREST_APPLICATION_FREQUENCY_PARAM_ID: EnumerationParameterValue(
                enumeration_value="annually"
            ),
        }

        sub_tests = [
            SubTest(
                description="Check annual schedule creation",
                events=[],
                expected_schedules=[
                    ExpectedSchedule(
                        run_times=[(start + relativedelta(years=1, seconds=1)).astimezone(UTC)],
                        event_id="APPLY_INTEREST",
                        account_id=accounts.CUSTOMER_ACCOUNT,
                    )
                ],
            )
        ]
        test_scenario = self.get_simulation_test_scenario(
            start=start,
            end=end,
            sub_tests=sub_tests,
            parameter_values=parameter_values,
            default_tz=default_tz,
        )
        self.run_test_scenario(test_scenario)

    @parameterized.expand(timezones)
    @pytest.mark.sim
    def test_interest_application_happens_after_frequency(self, default_tz: ZoneInfo):
        start = datetime(year=2026, month=1, day=1, tzinfo=default_tz)
        # First application is Feb 1st 00:00:01
        end = start + relativedelta(months=1, seconds=2)

        sub_tests = [
            SubTest(
                description="Initial deposit on Jan 1st",
                events=[
                    create_inbound_hard_settlement_instruction(
                        amount="100",
                        event_datetime=start + relativedelta(seconds=1),
                        target_account_id=accounts.CUSTOMER_ACCOUNT,
                        internal_account_id=accounts.DUMMY_INTERNAL_ACCOUNT,
                        denomination=parameters.DEFAULT_DENOMINATION,
                    )
                ],
                expected_balances_at_ts={
                    start + relativedelta(seconds=2): {
                        accounts.CUSTOMER_ACCOUNT: [(dimensions.DEFAULT, Decimal("100"))]
                    }
                },
            ),
            SubTest(
                description="No application before Feb 1st, mock accrual",
                events=[
                    create_inbound_hard_settlement_posting_instruction_event(
                        amount="5.12345",
                        event_datetime=start + relativedelta(days=15),
                        target_account_id=accounts.CUSTOMER_ACCOUNT,
                        target_account_address=deposit_addresses.ACCRUED_INTEREST_PAYABLE,
                        internal_account_id=accounts.DUMMY_INTERNAL_ACCOUNT,
                        denomination=parameters.DEFAULT_DENOMINATION,
                    )
                ],
                expected_balances_at_ts={
                    start + relativedelta(days=15): {
                        accounts.CUSTOMER_ACCOUNT: [
                            (dimensions.DEFAULT, Decimal("100")),
                            (dimensions.ACCRUED_INTEREST_PAYABLE, Decimal("5.12345")),
                        ]
                    }
                },
            ),
            SubTest(
                description="Interest applied on Feb 1st",
                events=[],
                expected_balances_at_ts={
                    end: {
                        accounts.CUSTOMER_ACCOUNT: [
                            (dimensions.DEFAULT, Decimal("105.12")),
                            (dimensions.ACCRUED_INTEREST_PAYABLE, Decimal("0")),
                        ]
                    }
                },
                expected_schedules=[
                    ExpectedSchedule(
                        run_times=[(start + relativedelta(months=1, seconds=1)).astimezone(UTC)],
                        event_id="APPLY_INTEREST",
                        account_id=accounts.CUSTOMER_ACCOUNT,
                    )
                ],
            ),
        ]
        test_scenario = self.get_simulation_test_scenario(
            start=start,
            end=end,
            sub_tests=sub_tests,
            default_tz=default_tz,
        )
        self.run_test_scenario(test_scenario)

    @pytest.mark.sim
    def test_interest_application_handles_overdraft_interest(self):
        import feature_library.deposit.interest.secondary.overdraft_interest as overdraft_interest

        from inception_sdk.test_framework.contracts.simulation.helper import (
            create_custom_instruction_posting_instruction_event,
        )
        from inception_sdk.vault.core_api import (
            AccountIdParameterValue,
            DecimalParameterValue,
            StringParameterValue,
        )

        start = datetime(year=2026, month=1, day=1, tzinfo=ZoneInfo("UTC"))
        # monthly application on the 1st of the month
        # so next application is Feb 1st
        end = datetime(year=2026, month=2, day=1, hour=1, tzinfo=ZoneInfo("UTC"))

        parameter_values = {
            **parameters.default_parameter_values,
            interest_application.INTEREST_APPLICATION_FREQUENCY_PARAM_ID: EnumerationParameterValue(
                enumeration_value="monthly"
            ),
            interest_application.INTEREST_APPLICATION_DAY_PARAM_ID: DecimalParameterValue(
                decimal_value=Decimal("1")
            ),
            # Required accrual params for the new SC
            interest_accrual.ACCRUAL_PRECISION_PARAM_ID: DecimalParameterValue(
                decimal_value=Decimal("5")
            ),
            interest_accrual.DAYS_IN_YEAR_PARAM_ID: EnumerationParameterValue(
                enumeration_value="actual"
            ),
            interest_accrual.INTEREST_ACCRUAL_TIME_PARAM_ID: StringParameterValue(
                string_value="00:00:00"
            ),
            # Overdraft params
            overdraft_interest.INTEREST_FREE_BUFFER_AMOUNT_PARAM_ID: DecimalParameterValue(
                decimal_value=Decimal("0")
            ),
            overdraft_interest.INTEREST_FREE_BUFFER_DAYS_PARAM_ID: DecimalParameterValue(
                decimal_value=Decimal("0")
            ),
            overdraft_interest.OVERDRAFT_INTEREST_RATE_PARAM_ID: DecimalParameterValue(
                decimal_value=Decimal("0.1")
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
                description="Apply overdraft interest",
                events=[
                    # Manually accrue some overdraft interest to the address
                    create_custom_instruction_posting_instruction_event(
                        event_datetime=start + relativedelta(days=15),
                        amount="10.50",
                        denomination=parameters.DEFAULT_DENOMINATION,
                        debtor_target_account_id=accounts.CUSTOMER_ACCOUNT,
                        creditor_target_account_id=accounts.DUMMY_INTERNAL_ACCOUNT,
                        debtor_target_account_address=overdraft_interest.OVERDRAFT_ACCRUED_INTEREST,
                        creditor_target_account_address=DEFAULT_ADDRESS,
                        asset=DEFAULT_ASSET,
                    )
                ],
                expected_balances_at_ts={
                    # Verify it applied to DEFAULT on Feb 1st
                    end: {
                        accounts.CUSTOMER_ACCOUNT: [
                            (dimensions.DEFAULT, Decimal("-10.50")),
                            (dimensions.OVERDRAFT_ACCRUED_INTEREST, Decimal("0")),
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
            contract_filepath=OVERDRAFT_INTEREST_APP_SC,
        )
        self.run_test_scenario(test_scenario)
