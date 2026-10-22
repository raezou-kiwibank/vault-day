# standard libs
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
from dateutil.relativedelta import relativedelta

# library
# inception sdk
from inception_sdk.test_framework.contracts.simulation.data_objects.data_objects import (
    AccountConfig,
    ContractConfig,
    SimulationTestScenario,
    SubTest,
)
from inception_sdk.test_framework.contracts.simulation.utils import SimulationTestCase

import tests.lending.disbursal.disbursement.simulation.accounts as accounts
import tests.lending.disbursal.disbursement.simulation.dimensions as dimensions
import tests.lending.disbursal.disbursement.simulation.parameters as parameters

SMART_CONTRACT = "tests/lending/disbursal/disbursement/smart_contract.py"

UTC = ZoneInfo("UTC")


class DisbursementBaseTest(SimulationTestCase):
    parameter_resource_dirs = [
        str(Path("src/feature_library/lending/disbursal/parameter_resource_defs")),
        str(Path("src/feature_library/lending/principal/parameter_resource_defs")),
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
        debug=True,
    ):
        contract_config = ContractConfig(
            contract_content=self.smart_contract_path_to_content[self.contract_filepath],
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
            internal_accounts=self.internal_accounts,
            parameters=self.parameters,
            debug=debug,
            use_v1_accounts=False,
        )


class DisbursementTest(DisbursementBaseTest):
    @pytest.mark.sim
    def test_disbursement_on_activation(self):
        start = self.default_simulation_start_datetime
        # Simulation end must be after start
        end = start + relativedelta(seconds=1)

        sub_tests = [
            SubTest(
                description="Check disbursement postings at account activation",
                events=[],
                expected_balances_at_ts={
                    end: {
                        accounts.CUSTOMER_ACCOUNT: [
                            (dimensions.PRINCIPAL, Decimal("1000")),
                        ],
                        accounts.DEPOSIT_ACCOUNT: [
                            (dimensions.DEFAULT, Decimal("1000")),
                        ],
                    }
                },
            )
        ]
        test_scenario = self.get_simulation_test_scenario(
            start=start,
            end=end,
            sub_tests=sub_tests,
        )
        self.run_test_scenario(test_scenario)
