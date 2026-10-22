import logging
from datetime import datetime
from decimal import Decimal
from pathlib import Path

import pytest
from dateutil.relativedelta import relativedelta

import feature_library.deposit.fees.maintenance_fees as maintenance_fees_module

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
from inception_sdk.vault.core_api import EnumerationParameterValue

from tests.deposit.fees.maintenance_fees.simulation import (
    accounts,
    dimensions,
    parameters,
)
from tests.sim_utils import UTC

SMART_CONTRACT = Path("tests/deposit/fees/maintenance_fees/simulation/smart_contract.py")

log = logging.getLogger(
    "inception_sdk.test_framework.contracts.simulation.vault_caller.sim_test_request_logger"
)
handler = logging.FileHandler("/tmp/req.json", mode="w")
log.propagate = False
log.addHandler(handler)
log.setLevel(logging.DEBUG)
handler.setLevel(logging.DEBUG)


class MaintenanceFeesTest(SimulationTestCase):
    parameter_resource_dirs = [
        str(Path("src/feature_library/common/parameter_resource_defs")),
        str(Path("src/feature_library/deposit/fees/parameter_resource_defs")),
    ]
    contract_filepaths = [str(SMART_CONTRACT)]
    internal_accounts = accounts.default_internal_accounts
    parameter_values = parameters.default_parameter_values
    default_simulation_start_datetime = datetime(2026, 1, 1, tzinfo=UTC)

    def get_simulation_test_scenario(
        self,
        start,
        end,
        sub_tests,
        parameter_values=None,
        debug=False,
    ):
        contract_config = ContractConfig(
            contract_content=self.smart_contract_path_to_content[str(SMART_CONTRACT)],
            template_params={},
            account_configs=[
                AccountConfig(
                    account_id_base=accounts.CUSTOMER_ACCOUNT,
                    parameter_values=parameter_values or self.parameter_values,
                    permitted_denominations=[dimensions.DEFAULT_DENOMINATION],
                )
            ],
        )
        return SimulationTestScenario(
            start=start,
            end=end,
            sub_tests=sub_tests,
            contract_config=contract_config,
            internal_accounts=self.internal_accounts,
            debug=debug,
            use_v1_accounts=False,
        )

    @pytest.mark.sim
    def test_monthly_and_annual_fees_applied(self):
        start = self.default_simulation_start_datetime
        end = start + relativedelta(years=1, days=1)

        sub_tests = [
            SubTest(
                description="Deposit 500 to cover fees",
                events=[
                    create_inbound_hard_settlement_instruction(
                        amount="500",
                        event_datetime=start + relativedelta(days=1),
                        target_account_id=accounts.CUSTOMER_ACCOUNT,
                        internal_account_id=accounts.DUMMY_INTERNAL_ACCOUNT,
                        denomination=dimensions.DEFAULT_DENOMINATION,
                    ),
                ],
                expected_balances_at_ts={
                    start + relativedelta(days=1, minutes=1): {
                        accounts.CUSTOMER_ACCOUNT: [
                            (
                                dimensions.DEFAULT,
                                Decimal("500.00"),
                            )
                        ]
                    }
                },
            ),
            SubTest(
                description="Monthly fee (5) applied on Feb 1st",
                expected_balances_at_ts={
                    start + relativedelta(months=1, hours=1): {
                        accounts.CUSTOMER_ACCOUNT: [
                            (
                                dimensions.DEFAULT,
                                Decimal("495.00"),
                            )
                        ],
                        accounts.INCOME_ACCOUNT: [
                            (
                                dimensions.DEFAULT,
                                Decimal("5.00"),
                            )
                        ],
                    }
                },
            ),
            SubTest(
                description="Monthly fee (5) applied on Mar 1st",
                expected_balances_at_ts={
                    start + relativedelta(months=2, hours=1): {
                        accounts.CUSTOMER_ACCOUNT: [
                            (
                                dimensions.DEFAULT,
                                Decimal("490.00"),
                            )
                        ],
                        accounts.INCOME_ACCOUNT: [
                            (
                                dimensions.DEFAULT,
                                Decimal("10.00"),
                            )
                        ],
                    }
                },
            ),
            SubTest(
                description="Annual fee (50) and Monthly fee (5) applied on Jan 1st next year",
                expected_balances_at_ts={
                    start + relativedelta(years=1, hours=1): {
                        accounts.CUSTOMER_ACCOUNT: [
                            (
                                dimensions.DEFAULT,
                                Decimal("390.00"),
                            )
                        ],
                        accounts.INCOME_ACCOUNT: [
                            (
                                dimensions.DEFAULT,
                                Decimal("110.00"),
                            )
                        ],
                    }
                },
            ),
        ]

        test_scenario = self.get_simulation_test_scenario(start=start, end=end, sub_tests=sub_tests)
        self.run_test_scenario(test_scenario)

    @pytest.mark.sim
    def test_partial_monthly_fee_applied(self):
        start = self.default_simulation_start_datetime
        end = start + relativedelta(months=2, days=1)

        parameter_values = {
            **self.parameter_values,
            maintenance_fees_module.MONTHLY_MAINTENANCE_FEE_PARTIAL_FEE_ENABLED_PARAM.id: (
                EnumerationParameterValue(enumeration_value="True")
            ),
        }

        sub_tests = [
            SubTest(
                description="Deposit 2 to cover part of the fee",
                events=[
                    create_inbound_hard_settlement_instruction(
                        amount="2",
                        event_datetime=start + relativedelta(days=1),
                        target_account_id=accounts.CUSTOMER_ACCOUNT,
                        internal_account_id=accounts.DUMMY_INTERNAL_ACCOUNT,
                        denomination=dimensions.DEFAULT_DENOMINATION,
                    ),
                ],
            ),
            SubTest(
                description="Partial monthly fee (2) applied on Feb 1st, 3 tracked",
                expected_balances_at_ts={
                    start + relativedelta(months=1, hours=1): {
                        accounts.CUSTOMER_ACCOUNT: [
                            (
                                dimensions.DEFAULT,
                                Decimal("0.00"),
                            ),
                            (
                                dimensions.OUTSTANDING_MONTHLY_MAINTENANCE_FEE_TRACKER,
                                Decimal("3.00"),
                            ),
                        ],
                        accounts.INCOME_ACCOUNT: [
                            (
                                dimensions.DEFAULT,
                                Decimal("2.00"),
                            )
                        ],
                    }
                },
            ),
        ]

        test_scenario = self.get_simulation_test_scenario(
            start=start, end=end, sub_tests=sub_tests, parameter_values=parameter_values
        )
        self.run_test_scenario(test_scenario)
