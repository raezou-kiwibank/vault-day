# standard libs
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
from dateutil.relativedelta import relativedelta

# inception sdk
from inception_sdk.test_framework.contracts.simulation.data_objects.data_objects import (
    AccountConfig,
    ContractConfig,
    ExpectedRejection,
    SimulationTestScenario,
    SubTest,
)
from inception_sdk.test_framework.contracts.simulation.helper import (
    create_outbound_hard_settlement_instruction,
)
from inception_sdk.test_framework.contracts.simulation.utils import (
    SimulationTestCase,
)

import tests.lending.principal.simulation.accounts as accounts
import tests.lending.principal.simulation.dimensions as dimensions
import tests.lending.principal.simulation.parameters as parameters
from tests.common.test_denomination import DEFAULT_DENOMINATION

SMART_CONTRACT = Path("tests/lending/principal/maximum_loan_principal_sc.py")

UTC = ZoneInfo("UTC")


class MaximumLoanPrincipalBaseTest(SimulationTestCase):
    parameter_resource_dirs = [
        str(Path("src/feature_library/lending/principal/parameter_resource_defs")),
        str(Path("src/feature_library/common/parameter_resource_defs")),
    ]
    contract_filepaths = [str(SMART_CONTRACT)]
    internal_accounts = accounts.default_internal_accounts
    parameter_values = parameters.maximum_loan_principal_parameters
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
            internal_accounts=self.internal_accounts,
            debug=debug,
            use_v1_accounts=False,
        )


class MaximumLoanPrincipalTest(MaximumLoanPrincipalBaseTest):
    @pytest.mark.sim
    def test_loan_amount_within_limit_accepted(self):
        start = self.default_simulation_start_datetime
        end = start + relativedelta(seconds=1)

        sub_tests = [
            SubTest(
                description="Check loan amount within limit is accepted",
                events=[
                    create_outbound_hard_settlement_instruction(
                        amount="500",
                        event_datetime=start,
                        target_account_id=accounts.CUSTOMER_ACCOUNT,
                        internal_account_id=accounts.DUMMY_INTERNAL_ACCOUNT,
                        denomination=DEFAULT_DENOMINATION,
                    ),
                ],
                expected_balances_at_ts={
                    start: {
                        accounts.CUSTOMER_ACCOUNT: [
                            (dimensions.DEFAULT, Decimal("500")),
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

    @pytest.mark.sim
    def test_loan_amount_exceeding_limit_rejected(self):
        start = self.default_simulation_start_datetime
        end = start + relativedelta(seconds=1)

        sub_tests = [
            SubTest(
                description="Check loan amount exceeding limit is rejected",
                events=[
                    create_outbound_hard_settlement_instruction(
                        amount="1500",
                        event_datetime=start,
                        target_account_id=accounts.CUSTOMER_ACCOUNT,
                        internal_account_id=accounts.DUMMY_INTERNAL_ACCOUNT,
                        denomination=DEFAULT_DENOMINATION,
                    ),
                ],
                expected_posting_rejections=[
                    ExpectedRejection(
                        timestamp=start,
                        rejection_type="AgainstTermsAndConditions",
                        rejection_reason=(
                            "Cannot create loan larger than maximum loan amount limit of: 1000."
                        ),
                        account_id=accounts.CUSTOMER_ACCOUNT,
                    )
                ],
            )
        ]
        test_scenario = self.get_simulation_test_scenario(
            start=start,
            end=end,
            sub_tests=sub_tests,
        )
        self.run_test_scenario(test_scenario)
