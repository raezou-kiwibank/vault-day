# standard libs
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
from dateutil.relativedelta import relativedelta
from parameterized import parameterized

from inception_sdk.test_framework.contracts.simulation.data_objects.data_objects import (
    AccountConfig,
    ContractConfig,
    ExpectedRejection,
    SimulationTestScenario,
    SubTest,
)
from inception_sdk.test_framework.contracts.simulation.helper import (
    create_flag_definition_event,
    create_flag_event,
    create_inbound_hard_settlement_posting_instruction_event,
)
from inception_sdk.test_framework.contracts.simulation.utils import SimulationTestCase

import tests.deposit.dormancy.dormancy.simulation.accounts as accounts
import tests.deposit.dormancy.dormancy.simulation.dimensions as dimensions
import tests.deposit.dormancy.dormancy.simulation.parameters as parameters
from tests.common.test_denomination import DEFAULT_DENOMINATION
from tests.sim_utils import (
    create_update_pgtz_instruction,
    timezones,
)

UTC = ZoneInfo("UTC")

SMART_CONTRACT = Path("tests/deposit/dormancy/dormancy/smart_contract.py")


class DormancySimulationTest(SimulationTestCase):
    contract_filepaths = [str(SMART_CONTRACT)]
    parameter_resource_dirs = [
        str(Path("src/feature_library/common/parameter_resource_defs")),
        str(Path("src/feature_library/deposit/dormancy/parameter_resource_defs")),
    ]
    internal_accounts = accounts.default_internal_accounts
    parameter_values = parameters.parameter_values
    default_simulation_start_datetime = datetime(year=2026, month=1, day=1, tzinfo=UTC)

    def get_simulation_test_scenario(
        self,
        start,
        end,
        sub_tests,
        parameter_values=None,
        default_tz=UTC,
    ):
        localised_sub_tests = [
            SubTest(
                description="Set the Default Processing Group Timezone",
                events=[create_update_pgtz_instruction(start, timezone=default_tz)],
            )
        ] + sub_tests

        contract_config = ContractConfig(
            contract_content=self.smart_contract_path_to_content[str(SMART_CONTRACT)],
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
            sub_tests=localised_sub_tests,
            contract_config=contract_config,
            internal_accounts=self.internal_accounts,
            use_v1_accounts=False,
        )

    @parameterized.expand(timezones)
    @pytest.mark.sim
    def test_postings_rejected_when_account_dormant(self, default_tz: ZoneInfo):
        start = self.default_simulation_start_datetime.astimezone(default_tz)
        end = start + relativedelta(days=1)

        sub_tests = [
            SubTest(
                description="Setup flag definition",
                events=[
                    create_flag_definition_event(
                        timestamp=start + relativedelta(minutes=1),
                        flag_definition_id="ACCOUNT_DORMANT",
                    ),
                ],
            ),
            SubTest(
                description="Postings accepted when account is NOT dormant",
                events=[
                    create_inbound_hard_settlement_posting_instruction_event(
                        amount="100.00",
                        event_datetime=start + relativedelta(hours=1),
                        target_account_id=accounts.CUSTOMER_ACCOUNT,
                        internal_account_id=accounts.INTERNAL_DORMANCY_ACCOUNT,
                        denomination=DEFAULT_DENOMINATION,
                    ),
                ],
                expected_balances_at_ts={
                    start + relativedelta(hours=1, minutes=1): {
                        accounts.CUSTOMER_ACCOUNT: [(dimensions.DEFAULT, Decimal("100"))]
                    }
                },
            ),
            SubTest(
                description="Set dormant flag",
                events=[
                    create_flag_event(
                        timestamp=start + relativedelta(hours=2),
                        flag_definition_id="ACCOUNT_DORMANT",
                        account_id=accounts.CUSTOMER_ACCOUNT,
                        expiry_timestamp=start + relativedelta(years=1),
                    ),
                ],
            ),
            SubTest(
                description="Postings rejected when account IS dormant",
                events=[
                    create_inbound_hard_settlement_posting_instruction_event(
                        amount="50.00",
                        event_datetime=start + relativedelta(hours=3),
                        target_account_id=accounts.CUSTOMER_ACCOUNT,
                        internal_account_id=accounts.INTERNAL_DORMANCY_ACCOUNT,
                        denomination=DEFAULT_DENOMINATION,
                    ),
                ],
                expected_posting_rejections=[
                    ExpectedRejection(
                        timestamp=start + relativedelta(hours=3),
                        rejection_reason=(
                            "Account flagged 'Dormant' does not accept external transactions."
                        ),
                        rejection_type="AgainstTermsAndConditions",
                        account_id=accounts.CUSTOMER_ACCOUNT,
                    )
                ],
                expected_balances_at_ts={
                    start + relativedelta(hours=3, minutes=1): {
                        accounts.CUSTOMER_ACCOUNT: [(dimensions.DEFAULT, Decimal("100"))]
                    }
                },
            ),
        ]

        scenario = self.get_simulation_test_scenario(
            start=start,
            end=end,
            sub_tests=sub_tests,
            default_tz=default_tz,
        )
        self.run_test_scenario(scenario)
