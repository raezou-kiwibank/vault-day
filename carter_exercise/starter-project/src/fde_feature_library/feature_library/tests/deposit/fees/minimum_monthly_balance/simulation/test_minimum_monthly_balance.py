import logging
from datetime import datetime
from decimal import Decimal
from pathlib import Path

import pytest
from dateutil.relativedelta import relativedelta

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

from tests.deposit.fees.minimum_monthly_balance.simulation import (
    accounts,
    dimensions,
    parameters,
)
from tests.sim_utils import UTC

SMART_CONTRACT = Path("tests/deposit/fees/minimum_monthly_balance/simulation/smart_contract.py")

log = logging.getLogger(
    "inception_sdk.test_framework.contracts.simulation.vault_caller.sim_test_request_logger"
)
handler = logging.FileHandler("/tmp/req.json", mode="w")
log.propagate = False
log.addHandler(handler)
log.setLevel(logging.DEBUG)
handler.setLevel(logging.DEBUG)


class MinimumMonthlyBalanceTest(SimulationTestCase):
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
    def test_fee_applied_below_threshold(self):
        start = self.default_simulation_start_datetime
        end = start + relativedelta(months=1, days=1)

        sub_tests = [
            SubTest(
                description="Fee applied on Feb 1st due to 0 balance",
                expected_balances_at_ts={
                    start + relativedelta(months=1, hours=1): {
                        accounts.CUSTOMER_ACCOUNT: [
                            (
                                dimensions.DEFAULT,
                                Decimal("-5.00"),
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
        ]

        test_scenario = self.get_simulation_test_scenario(start=start, end=end, sub_tests=sub_tests)
        self.run_test_scenario(test_scenario)

    @pytest.mark.sim
    def test_fee_not_applied_above_threshold(self):
        start = self.default_simulation_start_datetime
        end = start + relativedelta(months=1, days=1)

        sub_tests = [
            SubTest(
                description="Deposit 100",
                events=[
                    create_inbound_hard_settlement_instruction(
                        amount="100",
                        event_datetime=start + relativedelta(days=1),
                        target_account_id=accounts.CUSTOMER_ACCOUNT,
                        internal_account_id=accounts.DUMMY_INTERNAL_ACCOUNT,
                        denomination=dimensions.DEFAULT_DENOMINATION,
                    ),
                ],
                expected_balances_at_ts={
                    start + relativedelta(months=1, hours=1): {
                        accounts.CUSTOMER_ACCOUNT: [
                            (
                                dimensions.DEFAULT,
                                Decimal("100.00"),
                            )
                        ],
                        accounts.INCOME_ACCOUNT: [
                            (
                                dimensions.DEFAULT,
                                Decimal("0.00"),
                            )
                        ],
                    }
                },
            ),
        ]

        test_scenario = self.get_simulation_test_scenario(start=start, end=end, sub_tests=sub_tests)
        self.run_test_scenario(test_scenario)
