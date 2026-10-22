import json
import logging
from collections import defaultdict
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
from dateutil.relativedelta import relativedelta

from inception_sdk.test_framework.common.utils import strip_clu_notation
from inception_sdk.test_framework.contracts.simulation.data_objects.data_objects import (
    AccountConfig,
    ContractConfig,
    ExpectedRejection,
    SimulationTestScenario,
    SubTest,
)
from inception_sdk.test_framework.contracts.simulation.helper import (
    create_inbound_hard_settlement_instruction,
    create_outbound_hard_settlement_instruction,
    create_parameter_value,
)
from inception_sdk.test_framework.contracts.simulation.utils import (
    SimulationTestCase,
    get_logs_with_timestamp,
)
from inception_sdk.vault.core_api import (
    StringParameterValue,
)
from inception_sdk.vault.sim_api.contract_sim import CreateParameterValue

import tests.deposit.transaction_limits.withdrawal_limits.maximum_daily_withdrawal_by_transaction_type.simulation.accounts as accounts  # noqa: E501
import tests.deposit.transaction_limits.withdrawal_limits.maximum_daily_withdrawal_by_transaction_type.simulation.dimensions as dimensions  # noqa: E501
import tests.deposit.transaction_limits.withdrawal_limits.maximum_daily_withdrawal_by_transaction_type.simulation.parameters as parameters  # noqa: E501
import tests.deposit.transaction_limits.withdrawal_limits.maximum_daily_withdrawal_by_transaction_type.simulation.smart_contract as smart_contract  # noqa: E501
from tests.sim_utils import ctx_id_generator

log = logging.getLogger(
    "inception_sdk.test_framework.contracts.simulation.vault_caller.sim_test_request_logger"
)
handler = logging.FileHandler("/tmp/req.json", mode="w")  # whatever path the user wants to put
log.propagate = False  # comment this out if you do not want printing to stdout
log.addHandler(handler)
log.setLevel(logging.DEBUG)
handler.setLevel(logging.DEBUG)

SMART_CONTRACT = Path(
    "tests/deposit/transaction_limits/withdrawal_limits/maximum_daily_withdrawal_by_transaction_type/simulation/smart_contract.py"  # noqa: E501
)


class MaximumDailyWithdrawalByTransactionTypeBaseTest(SimulationTestCase):
    parameter_resource_dirs = [
        str(Path("src/feature_library/common/parameter_resource_defs")),
        str(
            Path(
                "src/feature_library/deposit/transaction_limits/withdrawal_limits/parameter_resource_defs"  # noqa: E501
            )
        ),
    ]
    contract_filepaths = [str(SMART_CONTRACT)]
    internal_accounts = accounts.default_internal_accounts
    parameter_values = parameters.default_parameter_values
    default_simulation_start_datetime = datetime(year=2026, month=1, day=1, tzinfo=ZoneInfo("UTC"))

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
                    permitted_denominations=[parameters.DEFAULT_DENOMINATION],
                )
            ],
        )
        return SimulationTestScenario(
            start=start,
            end=end,
            sub_tests=sub_tests,
            contract_config=contract_config,
            internal_accounts=self.internal_accounts or internal_accounts,
            debug=debug,
            use_v1_accounts=False,
        )


class MaximumDailyWithdrawalByTransactionTypeTest(MaximumDailyWithdrawalByTransactionTypeBaseTest):
    @pytest.mark.sim
    def test_withdrawal_within_limit(self):
        start = self.default_simulation_start_datetime
        end = start + relativedelta(minutes=2)
        ctx_id = ctx_id_generator("TX_")

        sub_tests = [
            SubTest(
                description="Fund account",
                events=[
                    create_inbound_hard_settlement_instruction(
                        amount="2000",
                        event_datetime=start,
                        target_account_id=accounts.CUSTOMER_ACCOUNT,
                        internal_account_id=accounts.DUMMY_INTERNAL_ACCOUNT,
                        denomination=dimensions.DEFAULT_DENOMINATION,
                    )
                ],
                expected_balances_at_ts={
                    start: {
                        accounts.CUSTOMER_ACCOUNT: [
                            (dimensions.DEFAULT, Decimal("2000")),
                        ]
                    }
                },
            ),
            SubTest(
                description="Withdraw exactly max limit for ATM under UPPER_TIER (500)",
                events=[
                    create_outbound_hard_settlement_instruction(
                        amount="500",
                        event_datetime=start + relativedelta(minutes=1),
                        target_account_id=accounts.CUSTOMER_ACCOUNT,
                        internal_account_id=accounts.DUMMY_INTERNAL_ACCOUNT,
                        denomination=dimensions.DEFAULT_DENOMINATION,
                        instruction_details={"TRANSACTION_TYPE": "ATM"},
                        client_transaction_id=next(ctx_id),
                    )
                ],
                expected_balances_at_ts={
                    start + relativedelta(minutes=1): {
                        accounts.CUSTOMER_ACCOUNT: [
                            (dimensions.DEFAULT, Decimal("1500")),
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

    @pytest.mark.sim
    def test_withdrawal_exceeds_limit(self):
        start = self.default_simulation_start_datetime
        end = start + relativedelta(minutes=2)
        ctx_id = ctx_id_generator("TX_")
        denomination: str = parameters.DEFAULT_DENOMINATION

        sub_tests = [
            SubTest(
                description="Fund account",
                events=[
                    create_inbound_hard_settlement_instruction(
                        amount="2000",
                        event_datetime=start,
                        target_account_id=accounts.CUSTOMER_ACCOUNT,
                        internal_account_id=accounts.DUMMY_INTERNAL_ACCOUNT,
                        denomination=dimensions.DEFAULT_DENOMINATION,
                    )
                ],
                expected_balances_at_ts={
                    start: {
                        accounts.CUSTOMER_ACCOUNT: [
                            (dimensions.DEFAULT, Decimal("2000")),
                        ]
                    }
                },
            ),
            SubTest(
                description="Withdraw 500.01 for ATM, exceeding limit of 500",
                events=[
                    create_outbound_hard_settlement_instruction(
                        amount="500.01",
                        event_datetime=start + relativedelta(minutes=1),
                        target_account_id=accounts.CUSTOMER_ACCOUNT,
                        internal_account_id=accounts.DUMMY_INTERNAL_ACCOUNT,
                        denomination=dimensions.DEFAULT_DENOMINATION,
                        instruction_details={"TRANSACTION_TYPE": "ATM"},
                        client_transaction_id=next(ctx_id),
                    )
                ],
                expected_balances_at_ts={
                    start + relativedelta(minutes=1): {
                        accounts.CUSTOMER_ACCOUNT: [
                            (dimensions.DEFAULT, Decimal("2000")),
                        ]
                    }
                },
                expected_posting_rejections=[
                    ExpectedRejection(
                        timestamp=start + relativedelta(minutes=1),
                        rejection_type="AgainstTermsAndConditions",
                        rejection_reason=(
                            f"Transactions would cause the maximum daily ATM "
                            f"withdrawal limit of 500 {denomination} to be exceeded."
                        ),
                        account_id=accounts.CUSTOMER_ACCOUNT,
                    )
                ],
            ),
        ]

        test_scenario = self.get_simulation_test_scenario(
            start=start,
            end=end,
            sub_tests=sub_tests,
        )
        self.run_test_scenario(test_scenario)

    @pytest.mark.sim
    def test_parameter_change(self):
        start = self.default_simulation_start_datetime
        end = start + relativedelta(minutes=2)

        sub_tests = [
            SubTest(
                description="Fund account",
                events=[
                    create_inbound_hard_settlement_instruction(
                        amount="2000",
                        event_datetime=start,
                        target_account_id=accounts.CUSTOMER_ACCOUNT,
                        internal_account_id=accounts.DUMMY_INTERNAL_ACCOUNT,
                        denomination=dimensions.DEFAULT_DENOMINATION,
                    ),
                ],
                expected_balances_at_ts={
                    start: {
                        accounts.CUSTOMER_ACCOUNT: [
                            (dimensions.DEFAULT, Decimal("2000")),
                        ]
                    }
                },
            ),
            SubTest(
                description="Update to the ATM withdrawal limit accepted",
                events=[
                    create_parameter_value(
                        start + relativedelta(seconds=1),
                        parameter_value=CreateParameterValue(
                            parameter_id=smart_contract.maximum_daily_withdrawal_by_transaction_type.DAILY_WITHDRAWAL_LIMIT_BY_TRANSACTION_TYPE_PARAM.id,  # noqa: E501
                            value=StringParameterValue(
                                string_value=json.dumps(
                                    {
                                        "ATM": "500",
                                    }
                                ),
                            ),
                            account_id=accounts.CUSTOMER_ACCOUNT,
                        ),
                    ),
                ],
                expected_parameter_change_rejections=[],
            ),
            SubTest(
                description="Attempted update to the ATM withdrawal limit rejected",
                events=[
                    create_parameter_value(
                        start + relativedelta(seconds=2),
                        parameter_value=CreateParameterValue(
                            parameter_id=smart_contract.maximum_daily_withdrawal_by_transaction_type.DAILY_WITHDRAWAL_LIMIT_BY_TRANSACTION_TYPE_PARAM.id,  # noqa: E501
                            value=StringParameterValue(
                                string_value=json.dumps(
                                    {
                                        "ATM": "500.01",
                                    }
                                ),
                            ),
                            account_id=accounts.CUSTOMER_ACCOUNT,
                        ),
                    ),
                ],
                expected_parameter_change_rejections=[
                    ExpectedRejection(
                        timestamp=start + relativedelta(seconds=2),
                        rejection_type="AGAINST TNC",
                        rejection_reason="Cannot update ATM transaction type limit for Maximum "
                        "Daily Withdrawal Amount because 500.01 GBP exceeds tiered limit of 500 "
                        "GBP for active UPPER_TIER.",
                        account_id=accounts.CUSTOMER_ACCOUNT,
                    )
                ],
            ),
        ]

        test_scenario = self.get_simulation_test_scenario(
            start=start,
            end=end,
            sub_tests=sub_tests,
        )
        results: list = self.run_test_scenario(test_scenario)
        # Check that the first parameter update was accepted.
        logs_with_timestamp: defaultdict[datetime, list[str]] = get_logs_with_timestamp(results)
        update_confirmation: str = next(iter(logs_with_timestamp[start + relativedelta(seconds=1)]))
        self.assertEqual(
            update_confirmation,
            'created value \'string_value:"{\\"ATM\\": \\"500\\"}"\' owned by account '
            f'"{accounts.CUSTOMER_ACCOUNT}" for parameter "{strip_clu_notation(smart_contract.maximum_daily_withdrawal_by_transaction_type.DAILY_WITHDRAWAL_LIMIT_BY_TRANSACTION_TYPE_PARAM.id)}"',  # noqa: E501
        )

    def test_non_overlapping_limits_are_not_disabled(self):
        start = self.default_simulation_start_datetime
        end = start + relativedelta(minutes=2)
        ctx_id = ctx_id_generator("TX_")

        # Set daily limit only for a non-overlapping transaction type 'XXX',
        # tiered limits still define 'ATM' as 500.
        parameter_values = {
            **self.parameter_values,
            smart_contract.maximum_daily_withdrawal_by_transaction_type.DAILY_WITHDRAWAL_LIMIT_BY_TRANSACTION_TYPE_PARAM.id: StringParameterValue(
                string_value=json.dumps({"XXX": "0"})
            ),
        }

        sub_tests = [
            SubTest(
                description="Fund account",
                events=[
                    create_inbound_hard_settlement_instruction(
                        amount="2000",
                        event_datetime=start,
                        target_account_id=accounts.CUSTOMER_ACCOUNT,
                        internal_account_id=accounts.DUMMY_INTERNAL_ACCOUNT,
                        denomination=dimensions.DEFAULT_DENOMINATION,
                    )
                ],
                expected_balances_at_ts={
                    start: {
                        accounts.CUSTOMER_ACCOUNT: [
                            (dimensions.DEFAULT, Decimal("2000")),
                        ]
                    }
                },
            ),
            SubTest(
                description="Withdraw 500 for ATM is accepted (within tiered limit of 500)",
                events=[
                    create_outbound_hard_settlement_instruction(
                        amount="500",
                        event_datetime=start + relativedelta(minutes=1),
                        target_account_id=accounts.CUSTOMER_ACCOUNT,
                        internal_account_id=accounts.DUMMY_INTERNAL_ACCOUNT,
                        denomination=dimensions.DEFAULT_DENOMINATION,
                        instruction_details={"TRANSACTION_TYPE": "ATM"},
                        client_transaction_id=next(ctx_id),
                    )
                ],
                expected_balances_at_ts={
                    start + relativedelta(minutes=1): {
                        accounts.CUSTOMER_ACCOUNT: [
                            (dimensions.DEFAULT, Decimal("1500")),
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
        )
        self.run_test_scenario(test_scenario)
