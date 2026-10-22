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
import feature_library.deposit.fees.withdrawal.excess_fee as excess_fee_module

# inception sdk
from inception_sdk.test_framework.contracts.simulation.data_objects.data_objects import (
    AccountConfig,
    ContractConfig,
    SimulationTestScenario,
    SubTest,
)
from inception_sdk.test_framework.contracts.simulation.helper import (
    create_inbound_hard_settlement_instruction,
    create_outbound_hard_settlement_instruction,
)
from inception_sdk.test_framework.contracts.simulation.utils import SimulationTestCase
from inception_sdk.vault.core_api import EnumerationParameterValue

import tests.deposit.fees.withdrawal.excess_fee.simulation.accounts as accounts
import tests.deposit.fees.withdrawal.excess_fee.simulation.dimensions as dimensions
import tests.deposit.fees.withdrawal.excess_fee.simulation.parameters as parameters
from tests.sim_utils import UTC, create_update_pgtz_instruction, ctx_id_generator, timezones

SMART_CONTRACT = str(Path("tests/deposit/fees/withdrawal/excess_fee/simulation/smart_contract.py"))

log = logging.getLogger(
    "inception_sdk.test_framework.contracts.simulation.vault_caller.sim_test_request_logger"
)
handler = logging.FileHandler("/tmp/req.json", mode="w")
log.propagate = False
log.addHandler(handler)
log.setLevel(logging.DEBUG)
handler.setLevel(logging.DEBUG)


class ExcessFeeBaseTest(SimulationTestCase):
    parameter_resource_dirs = [
        "src/feature_library/common/parameter_resource_defs",
        "src/feature_library/deposit/fees/withdrawal/parameter_resource_defs",
    ]
    contract_filepaths = [str(SMART_CONTRACT)]
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
    ):
        localised_sub_tests: list[SubTest] = [
            SubTest(
                description="Set the Default Processing Group Timezone",
                events=[create_update_pgtz_instruction(start, timezone=default_tz or UTC)],
            )
        ] + sub_tests

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
            sub_tests=localised_sub_tests,
            contract_config=contract_config,
            internal_accounts=self.internal_accounts or internal_accounts,
            debug=debug,
            use_v1_accounts=False,
        )


class ExcessFeeTest(ExcessFeeBaseTest):
    @parameterized.expand(timezones)
    @pytest.mark.sim
    def test_fee_applied_over_limit(self, default_tz: ZoneInfo):
        start = datetime(year=2026, month=1, day=1, tzinfo=default_tz)
        end = start + relativedelta(minutes=5)
        ctx_id = ctx_id_generator("TX_")

        sub_tests = [
            SubTest(
                description="Deposit 1000",
                events=[
                    create_inbound_hard_settlement_instruction(
                        amount="1000",
                        event_datetime=start + relativedelta(minutes=1),
                        target_account_id=accounts.CUSTOMER_ACCOUNT,
                        internal_account_id=accounts.DUMMY_INTERNAL_ACCOUNT,
                        denomination=parameters.DEFAULT_DENOMINATION,
                    )
                ],
                expected_balances_at_ts={
                    start + relativedelta(minutes=1, seconds=1): {
                        accounts.CUSTOMER_ACCOUNT: [
                            (dimensions.DEFAULT, Decimal(1000)),
                        ]
                    }
                },
            ),
            SubTest(
                description="First Withdrawal (limit is 2, no fee)",
                events=[
                    create_outbound_hard_settlement_instruction(
                        amount="100",
                        event_datetime=start + relativedelta(minutes=2),
                        target_account_id=accounts.CUSTOMER_ACCOUNT,
                        internal_account_id=accounts.DUMMY_INTERNAL_ACCOUNT,
                        denomination=parameters.DEFAULT_DENOMINATION,
                        instruction_details={"TRANSACTION_TYPE": "ATM"},
                        client_transaction_id=next(ctx_id),
                    )
                ],
                expected_balances_at_ts={
                    start + relativedelta(minutes=2, seconds=1): {
                        accounts.CUSTOMER_ACCOUNT: [
                            (dimensions.DEFAULT, Decimal(900)),
                        ]
                    }
                },
            ),
            SubTest(
                description="Second Withdrawal (limit is 2, no fee)",
                events=[
                    create_outbound_hard_settlement_instruction(
                        amount="100",
                        event_datetime=start + relativedelta(minutes=3),
                        target_account_id=accounts.CUSTOMER_ACCOUNT,
                        internal_account_id=accounts.DUMMY_INTERNAL_ACCOUNT,
                        denomination=parameters.DEFAULT_DENOMINATION,
                        instruction_details={"TRANSACTION_TYPE": "ATM"},
                        client_transaction_id=next(ctx_id),
                    )
                ],
                expected_balances_at_ts={
                    start + relativedelta(minutes=3, seconds=1): {
                        accounts.CUSTOMER_ACCOUNT: [
                            (dimensions.DEFAULT, Decimal(800)),
                        ]
                    }
                },
            ),
            SubTest(
                description="Third Withdrawal (limit is 2, fee of 2.50)",
                events=[
                    create_outbound_hard_settlement_instruction(
                        amount="100",
                        event_datetime=start + relativedelta(minutes=4),
                        target_account_id=accounts.CUSTOMER_ACCOUNT,
                        internal_account_id=accounts.DUMMY_INTERNAL_ACCOUNT,
                        denomination=parameters.DEFAULT_DENOMINATION,
                        instruction_details={"TRANSACTION_TYPE": "ATM"},
                        client_transaction_id=next(ctx_id),
                    )
                ],
                expected_balances_at_ts={
                    start + relativedelta(minutes=4, seconds=1): {
                        accounts.CUSTOMER_ACCOUNT: [
                            (dimensions.DEFAULT, Decimal("697.50")),
                        ]
                    }
                },
            ),
        ]

        test_scenario = self.get_simulation_test_scenario(
            start=start, end=end, sub_tests=sub_tests, default_tz=default_tz
        )
        self.run_test_scenario(test_scenario)

    @parameterized.expand(timezones)
    @pytest.mark.sim
    def test_fee_rejected_over_limit_when_block_withdrawals_is_true(self, default_tz: ZoneInfo):
        start = datetime(year=2026, month=1, day=1, tzinfo=default_tz)
        end = start + relativedelta(minutes=5)
        ctx_id = ctx_id_generator("TX_")

        parameter_values = {
            **self.parameter_values,
            excess_fee_module.BLOCK_EXCESS_WITHDRAWALS_PARAM_ID: EnumerationParameterValue(
                enumeration_value="True"
            ),
        }

        sub_tests = [
            SubTest(
                description="Deposit 1000",
                events=[
                    create_inbound_hard_settlement_instruction(
                        amount="1000",
                        event_datetime=start + relativedelta(minutes=1),
                        target_account_id=accounts.CUSTOMER_ACCOUNT,
                        internal_account_id=accounts.DUMMY_INTERNAL_ACCOUNT,
                        denomination=parameters.DEFAULT_DENOMINATION,
                    )
                ],
                expected_balances_at_ts={
                    start + relativedelta(minutes=1, seconds=1): {
                        accounts.CUSTOMER_ACCOUNT: [
                            (dimensions.DEFAULT, Decimal(1000)),
                        ]
                    }
                },
            ),
            SubTest(
                description="First Withdrawal (limit is 2, no fee)",
                events=[
                    create_outbound_hard_settlement_instruction(
                        amount="100",
                        event_datetime=start + relativedelta(minutes=2),
                        target_account_id=accounts.CUSTOMER_ACCOUNT,
                        internal_account_id=accounts.DUMMY_INTERNAL_ACCOUNT,
                        denomination=parameters.DEFAULT_DENOMINATION,
                        instruction_details={"TRANSACTION_TYPE": "ATM"},
                        client_transaction_id=next(ctx_id),
                    )
                ],
                expected_balances_at_ts={
                    start + relativedelta(minutes=2, seconds=1): {
                        accounts.CUSTOMER_ACCOUNT: [
                            (dimensions.DEFAULT, Decimal(900)),
                        ]
                    }
                },
            ),
            SubTest(
                description="Second Withdrawal (limit is 2, no fee)",
                events=[
                    create_outbound_hard_settlement_instruction(
                        amount="100",
                        event_datetime=start + relativedelta(minutes=3),
                        target_account_id=accounts.CUSTOMER_ACCOUNT,
                        internal_account_id=accounts.DUMMY_INTERNAL_ACCOUNT,
                        denomination=parameters.DEFAULT_DENOMINATION,
                        instruction_details={"TRANSACTION_TYPE": "ATM"},
                        client_transaction_id=next(ctx_id),
                    )
                ],
                expected_balances_at_ts={
                    start + relativedelta(minutes=3, seconds=1): {
                        accounts.CUSTOMER_ACCOUNT: [
                            (dimensions.DEFAULT, Decimal(800)),
                        ]
                    }
                },
            ),
            SubTest(
                description="Third Withdrawal is rejected because over limit",
                events=[
                    create_outbound_hard_settlement_instruction(
                        amount="100",
                        event_datetime=start + relativedelta(minutes=4),
                        target_account_id=accounts.CUSTOMER_ACCOUNT,
                        internal_account_id=accounts.DUMMY_INTERNAL_ACCOUNT,
                        denomination=parameters.DEFAULT_DENOMINATION,
                        instruction_details={"TRANSACTION_TYPE": "ATM"},
                        client_transaction_id=next(ctx_id),
                    )
                ],
                expected_balances_at_ts={
                    start + relativedelta(minutes=4, seconds=1): {
                        accounts.CUSTOMER_ACCOUNT: [
                            (
                                dimensions.DEFAULT,
                                Decimal(800),
                            ),  # Balance unchanged because rejected
                        ]
                    }
                },
            ),
        ]

        test_scenario = self.get_simulation_test_scenario(
            start=start,
            end=end,
            sub_tests=sub_tests,
            default_tz=default_tz,
            parameter_values=parameter_values,
        )
        self.run_test_scenario(test_scenario)
