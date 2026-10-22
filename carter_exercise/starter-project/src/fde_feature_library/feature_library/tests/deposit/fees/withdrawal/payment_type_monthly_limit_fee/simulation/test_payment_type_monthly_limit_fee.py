import logging
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
    SimulationTestScenario,
    SubTest,
)
from inception_sdk.test_framework.contracts.simulation.helper import (
    create_inbound_hard_settlement_instruction,
    create_outbound_hard_settlement_instruction,
)
from inception_sdk.test_framework.contracts.simulation.utils import SimulationTestCase

import tests.deposit.fees.withdrawal.payment_type_monthly_limit_fee.simulation.accounts as accounts
from tests.deposit.fees.withdrawal.payment_type_monthly_limit_fee.simulation import (
    dimensions,
    parameters,
)
from tests.sim_utils import UTC, create_update_pgtz_instruction, timezones

log = logging.getLogger(
    "inception_sdk.test_framework.contracts.simulation.vault_caller.sim_test_request_logger"
)
handler = logging.FileHandler("/tmp/req.json", mode="w")
log.propagate = False
log.addHandler(handler)
log.setLevel(logging.DEBUG)
handler.setLevel(logging.DEBUG)

SMART_CONTRACT = Path(
    "tests/deposit/fees/withdrawal/payment_type_monthly_limit_fee/simulation/smart_contract.py"
)


class PaymentTypeMonthlyLimitFeeBaseTest(SimulationTestCase):
    parameter_resource_dirs = [
        str(Path("src/feature_library/common/parameter_resource_defs")),
        str(Path("src/feature_library/deposit/fees/withdrawal/parameter_resource_defs")),
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


class PaymentTypeMonthlyLimitFeeTest(PaymentTypeMonthlyLimitFeeBaseTest):
    @parameterized.expand(timezones)
    @pytest.mark.sim
    def test_fee_applied_over_limit(self, default_tz: ZoneInfo):
        start = self.default_simulation_start_datetime.astimezone(default_tz)
        end = start + relativedelta(minutes=5)

        # Config has limit 2, so the 3rd ATM transaction will incur the fee of 0.50

        sub_tests = [
            SubTest(
                description="Deposit 10000",
                events=[
                    create_inbound_hard_settlement_instruction(
                        amount="10000",
                        event_datetime=start + relativedelta(minutes=1),
                        target_account_id=accounts.CUSTOMER_ACCOUNT,
                        internal_account_id=accounts.DUMMY_INTERNAL_ACCOUNT,
                        denomination=dimensions.DEFAULT_DENOMINATION,
                        instruction_details={"event": "DEPOSIT"},
                    )
                ],
                expected_balances_at_ts={
                    start + relativedelta(minutes=1, seconds=1): {
                        accounts.CUSTOMER_ACCOUNT: [
                            (dimensions.DEFAULT, Decimal(10000)),
                        ]
                    }
                },
            ),
            SubTest(
                description="First ATM Withdrawal (limit is 2, no fee)",
                events=[
                    create_outbound_hard_settlement_instruction(
                        amount="100",
                        event_datetime=start + relativedelta(minutes=2),
                        target_account_id=accounts.CUSTOMER_ACCOUNT,
                        internal_account_id=accounts.DUMMY_INTERNAL_ACCOUNT,
                        denomination=dimensions.DEFAULT_DENOMINATION,
                        instruction_details={"PAYMENT_TYPE": "ATM"},
                        client_transaction_id="TX_1",
                    )
                ],
                expected_balances_at_ts={
                    start + relativedelta(minutes=2, seconds=1): {
                        accounts.CUSTOMER_ACCOUNT: [
                            (dimensions.DEFAULT, Decimal(9900)),
                        ]
                    }
                },
            ),
            SubTest(
                description="Second ATM Withdrawal (limit is 2, no fee)",
                events=[
                    create_outbound_hard_settlement_instruction(
                        amount="100",
                        event_datetime=start + relativedelta(minutes=3),
                        target_account_id=accounts.CUSTOMER_ACCOUNT,
                        internal_account_id=accounts.DUMMY_INTERNAL_ACCOUNT,
                        denomination=dimensions.DEFAULT_DENOMINATION,
                        instruction_details={"PAYMENT_TYPE": "ATM"},
                        client_transaction_id="TX_2",
                    )
                ],
                expected_balances_at_ts={
                    start + relativedelta(minutes=3, seconds=1): {
                        accounts.CUSTOMER_ACCOUNT: [
                            (dimensions.DEFAULT, Decimal(9800)),
                        ]
                    }
                },
            ),
            SubTest(
                description="Third ATM Withdrawal (limit is 2, triggers fee of 0.50)",
                events=[
                    create_outbound_hard_settlement_instruction(
                        amount="100",
                        event_datetime=start + relativedelta(minutes=4),
                        target_account_id=accounts.CUSTOMER_ACCOUNT,
                        internal_account_id=accounts.DUMMY_INTERNAL_ACCOUNT,
                        denomination=dimensions.DEFAULT_DENOMINATION,
                        instruction_details={"PAYMENT_TYPE": "ATM"},
                        client_transaction_id="TX_3",
                    )
                ],
                expected_balances_at_ts={
                    start + relativedelta(minutes=4, seconds=1): {
                        accounts.CUSTOMER_ACCOUNT: [
                            # 9800 - 100 - 0.50 = 9699.50
                            (dimensions.DEFAULT, Decimal("9699.50")),
                        ]
                    }
                },
            ),
        ]

        test_scenario = self.get_simulation_test_scenario(
            start=start, end=end, sub_tests=sub_tests, debug=True, default_tz=default_tz
        )
        self.run_test_scenario(test_scenario)

    @parameterized.expand(timezones)
    @pytest.mark.sim
    def test_fee_not_applied_under_limit(self, default_tz: ZoneInfo):
        start = self.default_simulation_start_datetime.astimezone(default_tz)
        end = start + relativedelta(minutes=4)

        sub_tests = [
            SubTest(
                description="Deposit 10000",
                events=[
                    create_inbound_hard_settlement_instruction(
                        amount="10000",
                        event_datetime=start + relativedelta(minutes=1),
                        target_account_id=accounts.CUSTOMER_ACCOUNT,
                        internal_account_id=accounts.DUMMY_INTERNAL_ACCOUNT,
                        denomination=dimensions.DEFAULT_DENOMINATION,
                        instruction_details={"event": "DEPOSIT"},
                    )
                ],
                expected_balances_at_ts={
                    start + relativedelta(minutes=1, seconds=1): {
                        accounts.CUSTOMER_ACCOUNT: [
                            (dimensions.DEFAULT, Decimal(10000)),
                        ]
                    }
                },
            ),
            SubTest(
                description="First ATM Withdrawal (limit is 2, no fee)",
                events=[
                    create_outbound_hard_settlement_instruction(
                        amount="100",
                        event_datetime=start + relativedelta(minutes=2),
                        target_account_id=accounts.CUSTOMER_ACCOUNT,
                        internal_account_id=accounts.DUMMY_INTERNAL_ACCOUNT,
                        denomination=dimensions.DEFAULT_DENOMINATION,
                        instruction_details={"PAYMENT_TYPE": "ATM"},
                        client_transaction_id="TX_1",
                    )
                ],
                expected_balances_at_ts={
                    start + relativedelta(minutes=2, seconds=1): {
                        accounts.CUSTOMER_ACCOUNT: [
                            (dimensions.DEFAULT, Decimal(9900)),
                        ]
                    }
                },
            ),
        ]

        test_scenario = self.get_simulation_test_scenario(
            start=start,
            end=end,
            sub_tests=sub_tests,
            debug=True,
            default_tz=default_tz,
        )
        self.run_test_scenario(test_scenario)

    @parameterized.expand(timezones)
    @pytest.mark.sim
    def test_fee_not_applied_unmatched_payment_type(self, default_tz: ZoneInfo):
        start = self.default_simulation_start_datetime.astimezone(default_tz)
        end = start + relativedelta(minutes=6)

        sub_tests = [
            SubTest(
                description="Deposit 10000",
                events=[
                    create_inbound_hard_settlement_instruction(
                        amount="10000",
                        event_datetime=start + relativedelta(minutes=1),
                        target_account_id=accounts.CUSTOMER_ACCOUNT,
                        internal_account_id=accounts.DUMMY_INTERNAL_ACCOUNT,
                        denomination=dimensions.DEFAULT_DENOMINATION,
                        instruction_details={"event": "DEPOSIT"},
                    )
                ],
                expected_balances_at_ts={
                    start + relativedelta(minutes=1, seconds=1): {
                        accounts.CUSTOMER_ACCOUNT: [
                            (dimensions.DEFAULT, Decimal(10000)),
                        ]
                    }
                },
            ),
            SubTest(
                description="First POS Withdrawal (not configured, no limit, no fee)",
                events=[
                    create_outbound_hard_settlement_instruction(
                        amount="100",
                        event_datetime=start + relativedelta(minutes=2),
                        target_account_id=accounts.CUSTOMER_ACCOUNT,
                        internal_account_id=accounts.DUMMY_INTERNAL_ACCOUNT,
                        denomination=dimensions.DEFAULT_DENOMINATION,
                        instruction_details={"PAYMENT_TYPE": "POS"},
                        client_transaction_id="TX_1",
                    )
                ],
                expected_balances_at_ts={
                    start + relativedelta(minutes=2, seconds=1): {
                        accounts.CUSTOMER_ACCOUNT: [
                            (dimensions.DEFAULT, Decimal(9900)),
                        ]
                    }
                },
            ),
            SubTest(
                description="Second POS Withdrawal (not configured, no limit, no fee)",
                events=[
                    create_outbound_hard_settlement_instruction(
                        amount="100",
                        event_datetime=start + relativedelta(minutes=3),
                        target_account_id=accounts.CUSTOMER_ACCOUNT,
                        internal_account_id=accounts.DUMMY_INTERNAL_ACCOUNT,
                        denomination=dimensions.DEFAULT_DENOMINATION,
                        instruction_details={"PAYMENT_TYPE": "POS"},
                        client_transaction_id="TX_2",
                    )
                ],
                expected_balances_at_ts={
                    start + relativedelta(minutes=3, seconds=1): {
                        accounts.CUSTOMER_ACCOUNT: [
                            (dimensions.DEFAULT, Decimal(9800)),
                        ]
                    }
                },
            ),
            SubTest(
                description="Third POS Withdrawal (not configured, no limit, no fee)",
                events=[
                    create_outbound_hard_settlement_instruction(
                        amount="100",
                        event_datetime=start + relativedelta(minutes=4),
                        target_account_id=accounts.CUSTOMER_ACCOUNT,
                        internal_account_id=accounts.DUMMY_INTERNAL_ACCOUNT,
                        denomination=dimensions.DEFAULT_DENOMINATION,
                        instruction_details={"PAYMENT_TYPE": "POS"},
                        client_transaction_id="TX_3",
                    )
                ],
                expected_balances_at_ts={
                    start + relativedelta(minutes=4, seconds=1): {
                        accounts.CUSTOMER_ACCOUNT: [
                            (dimensions.DEFAULT, Decimal(9700)),
                        ]
                    }
                },
            ),
        ]

        test_scenario = self.get_simulation_test_scenario(
            start=start,
            end=end,
            sub_tests=sub_tests,
            debug=True,
            default_tz=default_tz,
        )
        self.run_test_scenario(test_scenario)
