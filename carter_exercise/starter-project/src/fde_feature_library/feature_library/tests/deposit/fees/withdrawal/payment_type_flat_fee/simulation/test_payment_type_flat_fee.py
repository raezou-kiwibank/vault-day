import logging
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

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
    create_outbound_hard_settlement_instruction,
)
from inception_sdk.test_framework.contracts.simulation.utils import SimulationTestCase

from tests.deposit.fees.withdrawal.payment_type_flat_fee.simulation import (
    accounts,
    dimensions,
    parameters,
)

log = logging.getLogger(
    "inception_sdk.test_framework.contracts.simulation.vault_caller.sim_test_request_logger"
)
handler = logging.FileHandler("/tmp/req.json", mode="w")
log.propagate = False
log.addHandler(handler)
log.setLevel(logging.DEBUG)
handler.setLevel(logging.DEBUG)

SMART_CONTRACT = Path(
    "tests/deposit/fees/withdrawal/payment_type_flat_fee/simulation/smart_contract.py"
)
UTC = ZoneInfo("UTC")


class PaymentTypeFlatFeeBaseTest(SimulationTestCase):
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
    ):
        contract_config = ContractConfig(
            contract_content=self.smart_contract_path_to_content[self.contract_filepath],
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
            internal_accounts=self.internal_accounts or internal_accounts,
            debug=True,
            use_v1_accounts=False,
        )


class PaymentTypeFlatFeeTest(PaymentTypeFlatFeeBaseTest):
    @pytest.mark.sim
    def test_fee_applied(self):
        start = self.default_simulation_start_datetime
        end = start + relativedelta(minutes=5)

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
                        instruction_details={
                            "event": "DEPOSIT",
                            "description": "Deposit 10,000.",
                        },
                    )
                ],
                expected_balances_at_ts={
                    start + relativedelta(minutes=1): {
                        accounts.CUSTOMER_ACCOUNT: [
                            (dimensions.DEFAULT, Decimal(10000)),
                        ]
                    }
                },
            ),
            SubTest(
                description="Withdrawal 5000 with ATM (charge 1)",
                events=[
                    create_outbound_hard_settlement_instruction(
                        amount="5000",
                        event_datetime=start + relativedelta(minutes=2),
                        target_account_id=accounts.CUSTOMER_ACCOUNT,
                        internal_account_id=accounts.DUMMY_INTERNAL_ACCOUNT,
                        denomination=dimensions.DEFAULT_DENOMINATION,
                        instruction_details={
                            "PAYMENT_TYPE": "ATM",
                        },
                    )
                ],
                expected_balances_at_ts={
                    start + relativedelta(minutes=2): {
                        accounts.CUSTOMER_ACCOUNT: [
                            # 10000 - 5000 (withdrawal) - 1 (fee)
                            (dimensions.DEFAULT, Decimal("4999")),
                        ]
                    }
                },
            ),
            SubTest(
                description="Withdrawal 2000 with POS (charge 0.5)",
                events=[
                    create_outbound_hard_settlement_instruction(
                        amount="2000",
                        event_datetime=start + relativedelta(minutes=3),
                        target_account_id=accounts.CUSTOMER_ACCOUNT,
                        internal_account_id=accounts.DUMMY_INTERNAL_ACCOUNT,
                        denomination=dimensions.DEFAULT_DENOMINATION,
                        instruction_details={
                            "PAYMENT_TYPE": "POS",
                        },
                    )
                ],
                expected_balances_at_ts={
                    start + relativedelta(minutes=3): {
                        accounts.CUSTOMER_ACCOUNT: [
                            # 4999 - 2000 (withdrawal) - 0.5 (fee)
                            (dimensions.DEFAULT, Decimal("2998.5")),
                        ]
                    }
                },
            ),
            SubTest(
                description="Withdrawal 1000 with unmatched payment type (no fee)",
                events=[
                    create_outbound_hard_settlement_instruction(
                        amount="1000",
                        event_datetime=start + relativedelta(minutes=4),
                        target_account_id=accounts.CUSTOMER_ACCOUNT,
                        internal_account_id=accounts.DUMMY_INTERNAL_ACCOUNT,
                        denomination=dimensions.DEFAULT_DENOMINATION,
                        instruction_details={
                            "PAYMENT_TYPE": "CHEQUE",
                        },
                    )
                ],
                expected_balances_at_ts={
                    start + relativedelta(minutes=4): {
                        accounts.CUSTOMER_ACCOUNT: [
                            # 2998.5 - 1000 (withdrawal)
                            (dimensions.DEFAULT, Decimal("1998.5")),
                        ]
                    }
                },
            ),
        ]

        test_scenario = self.get_simulation_test_scenario(
            start=start,
            end=end,
            sub_tests=sub_tests,
        )
        self.run_test_scenario(test_scenario)
