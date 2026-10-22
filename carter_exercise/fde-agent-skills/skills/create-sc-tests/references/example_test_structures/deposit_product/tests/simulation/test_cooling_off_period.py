# Copyright @ 2026 Thought Machine Group Limited. All rights reserved.
# standard libs
import logging
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

# features
import feature_library.deposit.temporal_features.cooling_off_period as cooling_off_period

# third party
import pytest
import tests.deposit.temporal_features.cooling_off_period.simulation.accounts as accounts
import tests.deposit.temporal_features.cooling_off_period.simulation.parameters as parameters
import tests.deposit.temporal_features.cooling_off_period.smart_contract as smart_contract
from dateutil.relativedelta import relativedelta
from inception_sdk.test_framework.common.balance_helpers import BalanceDimensions

# inception sdk
from inception_sdk.test_framework.contracts.simulation.data_objects.data_objects import (
    AccountConfig,
    ContractConfig,
    ContractNotificationResourceType,
    ExpectedContractNotification,
    SimulationEvent,
    SimulationTestScenario,
    SubTest,
)
from inception_sdk.test_framework.contracts.simulation.helper import (
    create_inbound_hard_settlement_posting_instruction_event,
    create_outbound_hard_settlement_posting_instruction_event,
)
from inception_sdk.test_framework.contracts.simulation.utils import (
    SimulationTestCase,
)
from parameterized import parameterized
from tests.common.test_denomination import DEFAULT_DENOMINATION
from tests.sim_utils import create_update_pgtz_instruction, timezones

log = logging.getLogger(
    "inception_sdk.test_framework.contracts.simulation.vault_caller.sim_test_request_logger"
)

SMART_CONTRACT = str(Path("deposit_product/contracts/template/smart_contract.py"))
UTC = ZoneInfo("UTC")


@pytest.mark.sim
class CoolingOffPeriodSimulationTest(SimulationTestCase):
    parameter_resource_dirs = [
        str(Path("deposit_product/parameters")),
    ]
    contract_filepaths = [SMART_CONTRACT]
    internal_accounts = accounts.default_internal_accounts
    parameter_values = parameters.parameter_values

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
            contract_content=self.smart_contract_path_to_content[SMART_CONTRACT],
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
    def test_cooling_off_period_validation(self, default_tz: ZoneInfo):
        start = datetime(2026, 1, 1, tzinfo=default_tz)
        # cooling off period end is 5 days from activation + midnight
        # activation is 2026-01-01 00:00:00 (effectively)
        cooling_off_period_end = datetime(2026, 1, 6, 0, 0, 0, tzinfo=default_tz)
        end = cooling_off_period_end + relativedelta(days=1)

        sub_tests = [
            SubTest(
                description="Deposit 100",
                events=[
                    create_inbound_hard_settlement_posting_instruction_event(
                        amount="100.00",
                        event_datetime=start + relativedelta(hours=1),
                        target_account_id=accounts.CUSTOMER_ACCOUNT,
                        internal_account_id=accounts.INTERNAL_ACCOUNT,
                        denomination=DEFAULT_DENOMINATION,
                    )
                ],
            ),
            SubTest(
                description="Full withdrawal within cooling off period (no fee)",
                events=[
                    create_outbound_hard_settlement_posting_instruction_event(
                        amount="100.00",
                        event_datetime=start + relativedelta(days=1),
                        target_account_id=accounts.CUSTOMER_ACCOUNT,
                        internal_account_id=accounts.INTERNAL_ACCOUNT,
                        denomination=DEFAULT_DENOMINATION,
                    )
                ],
                expected_balances_at_ts={
                    start
                    + relativedelta(days=1, hours=1): {
                        accounts.CUSTOMER_ACCOUNT: [
                            (
                                BalanceDimensions(
                                    denomination=DEFAULT_DENOMINATION,
                                ),
                                Decimal("0.00"),
                            )
                        ]
                    }
                },
                # No notification should be sent for full withdrawal
                expected_contract_notifications=[],
            ),
            SubTest(
                description="Deposit 100 again",
                events=[
                    create_inbound_hard_settlement_posting_instruction_event(
                        amount="100.00",
                        event_datetime=start + relativedelta(days=2),
                        target_account_id=accounts.CUSTOMER_ACCOUNT,
                        internal_account_id=accounts.INTERNAL_ACCOUNT,
                        denomination=DEFAULT_DENOMINATION,
                    )
                ],
            ),
            SubTest(
                description="Partial withdrawal within cooling off period (subject to fees)",
                events=[
                    create_outbound_hard_settlement_posting_instruction_event(
                        amount="50.00",
                        event_datetime=start + relativedelta(days=2, hours=1),
                        target_account_id=accounts.CUSTOMER_ACCOUNT,
                        internal_account_id=accounts.INTERNAL_ACCOUNT,
                        denomination=DEFAULT_DENOMINATION,
                    )
                ],
                expected_contract_notifications=[
                    ExpectedContractNotification(
                        timestamp=start + relativedelta(days=2, hours=1),
                        notification_type=smart_contract.WITHDRAWAL_SUBJECT_TO_FEES,
                        notification_details={"account_id": accounts.CUSTOMER_ACCOUNT},
                        resource_id=accounts.CUSTOMER_ACCOUNT,
                        resource_type=ContractNotificationResourceType.RESOURCE_ACCOUNT,
                    )
                ],
            ),
            SubTest(
                description="Full withdrawal outside cooling off period (subject to fees)",
                events=[
                    create_outbound_hard_settlement_posting_instruction_event(
                        amount="50.00",
                        event_datetime=cooling_off_period_end + relativedelta(hours=1),
                        target_account_id=accounts.CUSTOMER_ACCOUNT,
                        internal_account_id=accounts.INTERNAL_ACCOUNT,
                        denomination=DEFAULT_DENOMINATION,
                    )
                ],
                expected_contract_notifications=[
                    ExpectedContractNotification(
                        timestamp=cooling_off_period_end + relativedelta(hours=1),
                        notification_type=smart_contract.WITHDRAWAL_SUBJECT_TO_FEES,
                        notification_details={"account_id": accounts.CUSTOMER_ACCOUNT},
                        resource_id=accounts.CUSTOMER_ACCOUNT,
                        resource_type=ContractNotificationResourceType.RESOURCE_ACCOUNT,
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

    @parameterized.expand(timezones)
    def test_attributes(self, default_tz: ZoneInfo):
        start = datetime(2026, 1, 1, tzinfo=default_tz)
        cooling_off_period_end = start + relativedelta(
            days=5, hour=0, minute=0, second=0, microsecond=0
        )
        end = start + relativedelta(minutes=1)

        sub_tests = [
            SubTest(
                description="Test attributes",
                events=[
                    SimulationEvent(
                        time=start,
                        event={
                            "list_account_attribute_values": {
                                "account_ids": [accounts.CUSTOMER_ACCOUNT],
                                "attribute_names": [
                                    cooling_off_period.COOLING_OFF_PERIOD_END_DATE_ATTR_ID,
                                ],
                            }
                        },
                    ),
                ],
            ),
        ]

        test_scenario = self.get_simulation_test_scenario(
            start=start,
            end=end,
            sub_tests=sub_tests,
            default_tz=default_tz,
        )
        results = self.run_test_scenario(test_scenario)
        attribute_result = next(
            filter(lambda r: r.get("result", {}).get("account_attribute_values"), results), None
        )
        self.assertIsNotNone(attribute_result)
        attribute_values = attribute_result["result"]["account_attribute_values"][
            accounts.CUSTOMER_ACCOUNT
        ]["account_attribute_values"]
        self.assertEqual(len(attribute_values), 1)

        end_date_attribute = next(
            filter(
                lambda attr_val: (
                    attr_val["attribute_name"]
                    == cooling_off_period.COOLING_OFF_PERIOD_END_DATE_ATTR_ID
                ),
                attribute_values,
            ),
            None,
        )
        self.assertIsNotNone(end_date_attribute)

        self.assertEqual(
            end_date_attribute["value"]["date_time_value"]["value"],
            cooling_off_period_end.astimezone(UTC)
            .replace(hour=0, minute=0, second=0, microsecond=0)
            .isoformat()
            .replace("+00:00", "Z"),
        )
