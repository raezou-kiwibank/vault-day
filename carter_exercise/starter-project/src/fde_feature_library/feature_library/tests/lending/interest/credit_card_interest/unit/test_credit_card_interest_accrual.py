# standard libs
from datetime import datetime
from decimal import Decimal
from unittest.mock import MagicMock, patch
from zoneinfo import ZoneInfo

import pytest

import feature_library.common.denomination as denomination_module

# features
import feature_library.common.fetchers as fetchers
import feature_library.lending.addresses as apex_addresses
import feature_library.lending.interest.credit_card_interest_accrual as interest_accrual_module

# contracts api
from contracts_api import (
    DEFAULT_ASSET,
    Balance,
    BalanceCoordinate,
    BalanceDefaultDict,
    BalancesObservation,
    ParametersObservation,
    Phase,
    ScheduledEvent,
    ScheduleExpression,
)

# inception sdk
from inception_sdk.test_framework.contracts.unit.common import (
    ACCOUNT_ID,
    FeatureTest,
)

from tests.common.test_denomination import DEFAULT_DENOMINATION
from tests.utils import initialise_mock_state

UTC_ZONE = ZoneInfo("UTC")
DEFAULT_DATETIME = datetime(2026, 1, 1, tzinfo=UTC_ZONE)

DENOMINATION = DEFAULT_DENOMINATION
INTEREST_RECEIVABLE_ACCOUNT = "INTEREST_RECEIVABLE"
ACCOUNT_TYPE = "credit_card"


class CreditCardInterestAccrualCalculationTest(FeatureTest):
    @pytest.mark.unit
    def test_calculate_daily_accrual_standard(self):
        # 24.9% APR on £1000 balance, non-leap year (365 days)
        # Daily rate = 0.249 / 365 = 0.00068219...
        # Accrual = 1000 * 0.00068219... = 0.68219...
        # Rounded to 5dp = 0.68219
        result = interest_accrual_module._calculate_daily_accrual(
            balance=Decimal("1000"),
            annual_rate=Decimal("0.249"),
            effective_datetime=datetime(2026, 6, 15, tzinfo=UTC_ZONE),  # 2026 is not a leap year
            precision=5,
        )
        expected = Decimal("0.68219")
        self.assertEqual(result, expected)

    @pytest.mark.unit
    def test_calculate_daily_accrual_leap_year(self):
        # 24.9% APR on £1000 balance, leap year (366 days)
        # Daily rate = 0.249 / 366 = 0.00068032...
        # Accrual = 1000 * 0.00068032... = 0.68032...
        # Rounded to 5dp = 0.68033
        result = interest_accrual_module._calculate_daily_accrual(
            balance=Decimal("1000"),
            annual_rate=Decimal("0.249"),
            effective_datetime=datetime(2028, 6, 15, tzinfo=UTC_ZONE),  # 2028 is a leap year
            precision=5,
        )
        expected = Decimal("0.68033")
        self.assertEqual(result, expected)

    @pytest.mark.unit
    def test_calculate_daily_accrual_zero_balance(self):
        result = interest_accrual_module._calculate_daily_accrual(
            balance=Decimal("0"),
            annual_rate=Decimal("0.249"),
            effective_datetime=DEFAULT_DATETIME,
            precision=5,
        )
        self.assertEqual(result, Decimal(0))

    @pytest.mark.unit
    def test_calculate_daily_accrual_zero_rate(self):
        result = interest_accrual_module._calculate_daily_accrual(
            balance=Decimal("1000"),
            annual_rate=Decimal("0"),
            effective_datetime=DEFAULT_DATETIME,
            precision=5,
        )
        self.assertEqual(result, Decimal(0))

    @pytest.mark.unit
    def test_calculate_daily_accrual_negative_balance(self):
        result = interest_accrual_module._calculate_daily_accrual(
            balance=Decimal("-100"),
            annual_rate=Decimal("0.249"),
            effective_datetime=DEFAULT_DATETIME,
            precision=5,
        )
        self.assertEqual(result, Decimal(0))


class CreditCardInterestAccrualScheduleTest(FeatureTest):
    @pytest.mark.unit
    def test_schedule_logic_purchase_only(self):
        purchase_balance = Decimal("1000")
        balances = BalanceDefaultDict(
            lambda: Balance(),
            {
                BalanceCoordinate(
                    apex_addresses.PURCHASE, DEFAULT_ASSET, DENOMINATION, Phase.COMMITTED
                ): Balance(purchase_balance, Decimal(0), purchase_balance),
            },
        )
        params = {
            denomination_module.DENOMINATION_PARAM.id: DENOMINATION,
            interest_accrual_module.PURCHASE_INTEREST_RATE_PARAM.id: Decimal("0.249"),
            interest_accrual_module.CASH_ADVANCE_INTEREST_RATE_PARAM.id: Decimal("0.299"),
            interest_accrual_module.INTEREST_ACCRUAL_PRECISION_PARAM.id: Decimal("5"),
            interest_accrual_module.INTEREST_RECEIVABLE_ACCOUNT_PARAM.id: INTEREST_RECEIVABLE_ACCOUNT,  # noqa: E501
            interest_accrual_module.INTEREST_ACCRUAL_TIME_PARAM.id: "00:00:01",
        }
        mock_vault = self.create_mock(
            account_id=ACCOUNT_ID,
            balances_observation_fetchers_mapping={
                fetchers.EFFECTIVE_DATE_BOF.fetcher_id: BalancesObservation(
                    balances=balances,
                    value_datetime=DEFAULT_DATETIME,
                    at_datetime=DEFAULT_DATETIME,
                ),
            },
            parameters_observation_fetchers_mapping={
                interest_accrual_module.INTEREST_ACCRUAL_POF.fetcher_id: ParametersObservation(
                    parameters=params, value_datetime=DEFAULT_DATETIME
                ),
            },
        )
        state = MagicMock(
            vault=mock_vault,
            effective_datetime=DEFAULT_DATETIME,
            parameters=params,
            balances=balances,
        )

        result = interest_accrual_module.schedule_logic(state=state, account_type=ACCOUNT_TYPE)

        # Should have exactly 1 instruction for purchase accrual (no cash advance balance)
        self.assertEqual(len(result), 1)
        self.assertIn("purchases", result[0].instruction_details["description"])

    @pytest.mark.unit
    def test_schedule_logic_no_balance(self):
        balances = BalanceDefaultDict(lambda: Balance(), {})
        params = {
            denomination_module.DENOMINATION_PARAM.id: DENOMINATION,
            interest_accrual_module.PURCHASE_INTEREST_RATE_PARAM.id: Decimal("0.249"),
            interest_accrual_module.CASH_ADVANCE_INTEREST_RATE_PARAM.id: Decimal("0.299"),
            interest_accrual_module.INTEREST_ACCRUAL_PRECISION_PARAM.id: Decimal("5"),
            interest_accrual_module.INTEREST_RECEIVABLE_ACCOUNT_PARAM.id: INTEREST_RECEIVABLE_ACCOUNT,  # noqa: E501
            interest_accrual_module.INTEREST_ACCRUAL_TIME_PARAM.id: "00:00:01",
        }
        mock_vault = self.create_mock(
            account_id=ACCOUNT_ID,
            balances_observation_fetchers_mapping={
                fetchers.EFFECTIVE_DATE_BOF.fetcher_id: BalancesObservation(
                    balances=balances,
                    value_datetime=DEFAULT_DATETIME,
                    at_datetime=DEFAULT_DATETIME,
                ),
            },
            parameters_observation_fetchers_mapping={
                interest_accrual_module.INTEREST_ACCRUAL_POF.fetcher_id: ParametersObservation(
                    parameters=params, value_datetime=DEFAULT_DATETIME
                ),
            },
        )
        state = MagicMock(
            vault=mock_vault,
            effective_datetime=DEFAULT_DATETIME,
            parameters=params,
            balances=balances,
        )

        result = interest_accrual_module.schedule_logic(state=state, account_type=ACCOUNT_TYPE)
        self.assertEqual(len(result), 0)

    @pytest.mark.unit
    def test_schedule_logic_both_purchase_and_cash_advance(self):
        purchase_balance = Decimal("1000")
        cash_advance_balance = Decimal("500")
        balances = BalanceDefaultDict(
            lambda: Balance(),
            {
                BalanceCoordinate(
                    apex_addresses.PURCHASE, DEFAULT_ASSET, DENOMINATION, Phase.COMMITTED
                ): Balance(purchase_balance, Decimal(0), purchase_balance),
                BalanceCoordinate(
                    apex_addresses.CASH_ADVANCE, DEFAULT_ASSET, DENOMINATION, Phase.COMMITTED
                ): Balance(cash_advance_balance, Decimal(0), cash_advance_balance),
            },
        )
        params = {
            denomination_module.DENOMINATION_PARAM.id: DENOMINATION,
            interest_accrual_module.PURCHASE_INTEREST_RATE_PARAM.id: Decimal("0.249"),
            interest_accrual_module.CASH_ADVANCE_INTEREST_RATE_PARAM.id: Decimal("0.299"),
            interest_accrual_module.INTEREST_ACCRUAL_PRECISION_PARAM.id: Decimal("5"),
            interest_accrual_module.INTEREST_RECEIVABLE_ACCOUNT_PARAM.id: INTEREST_RECEIVABLE_ACCOUNT,  # noqa: E501
            interest_accrual_module.INTEREST_ACCRUAL_TIME_PARAM.id: "00:00:01",
        }
        mock_vault = self.create_mock(
            account_id=ACCOUNT_ID,
            balances_observation_fetchers_mapping={
                fetchers.EFFECTIVE_DATE_BOF.fetcher_id: BalancesObservation(
                    balances=balances,
                    value_datetime=DEFAULT_DATETIME,
                    at_datetime=DEFAULT_DATETIME,
                ),
            },
            parameters_observation_fetchers_mapping={
                interest_accrual_module.INTEREST_ACCRUAL_POF.fetcher_id: ParametersObservation(
                    parameters=params, value_datetime=DEFAULT_DATETIME
                ),
            },
        )
        state = MagicMock(
            vault=mock_vault,
            effective_datetime=DEFAULT_DATETIME,
            parameters=params,
            balances=balances,
        )

        result = interest_accrual_module.schedule_logic(state=state, account_type=ACCOUNT_TYPE)
        self.assertEqual(len(result), 2)

    @pytest.mark.unit
    def test_get_scheduled_events(self):
        accrual_time = "23:59:59"
        mock_state = initialise_mock_state(
            effective_datetime=DEFAULT_DATETIME,
            parameters={
                interest_accrual_module.INTEREST_ACCRUAL_TIME_PARAM.id: accrual_time,
            },
        )

        mock_state.vault.events_timezone = UTC_ZONE

        with patch.object(
            interest_accrual_module.state_utils, "append_to_state", return_value=mock_state
        ):
            result = interest_accrual_module.get_scheduled_events(state=mock_state)

        expected_event = {
            interest_accrual_module.ACCRUAL_EVENT: ScheduledEvent(
                start_datetime=DEFAULT_DATETIME,
                expression=ScheduleExpression(
                    hour=23,
                    minute=59,
                    second=59,
                ),
            )
        }
        self.assertEqual(result, expected_event)
