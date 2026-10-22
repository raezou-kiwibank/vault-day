# standard libs
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import MagicMock
from zoneinfo import ZoneInfo

import pytest

import feature_library.common.denomination as denomination_module

# features
import feature_library.common.fetchers as fetchers
import feature_library.lending.addresses as apex_addresses
import feature_library.lending.rewards.welcome_bonus as welcome_bonus_module

# contracts api
from contracts_api import (
    DEFAULT_ASSET,
    Balance,
    BalanceCoordinate,
    BalanceDefaultDict,
    BalancesObservation,
    ParametersObservation,
    Phase,
)

# inception sdk
from inception_sdk.test_framework.contracts.unit.common import (
    ACCOUNT_ID,
    FeatureTest,
)

from tests.common.test_denomination import DEFAULT_DENOMINATION

UTC_ZONE = ZoneInfo("UTC")
ACCOUNT_CREATION_DATETIME = datetime(2026, 1, 1, tzinfo=UTC_ZONE)

DENOMINATION = DEFAULT_DENOMINATION
ACCOUNT_TYPE = "credit_card"


class WelcomeBonusTest(FeatureTest):
    def _create_balances(
        self,
        spend_tracker: Decimal = Decimal(0),
        rewards_points: Decimal = Decimal(0),
    ) -> BalanceDefaultDict:
        mapping = {}
        for address, amount in [
            (apex_addresses.WELCOME_BONUS_SPEND_TRACKER, spend_tracker),
            (apex_addresses.REWARDS_POINTS, rewards_points),
        ]:
            if amount != 0:
                mapping[
                    BalanceCoordinate(address, DEFAULT_ASSET, DENOMINATION, Phase.COMMITTED)
                ] = Balance(amount, Decimal(0), amount)
        return BalanceDefaultDict(lambda: Balance(), mapping)

    def _setup_state(
        self,
        days_since_opening: int = 0,
        spend_tracker: Decimal = Decimal(0),
        threshold: Decimal = Decimal("6000"),
        bonus_points: Decimal = Decimal("100000"),
        period_days: int = 90,
    ) -> MagicMock:
        effective_datetime = ACCOUNT_CREATION_DATETIME + timedelta(days=days_since_opening)
        balances = self._create_balances(spend_tracker=spend_tracker)
        params = {
            denomination_module.DENOMINATION_PARAM.id: DENOMINATION,
            welcome_bonus_module.WELCOME_BONUS_THRESHOLD_PARAM.id: threshold,
            welcome_bonus_module.WELCOME_BONUS_POINTS_PARAM.id: bonus_points,
            welcome_bonus_module.WELCOME_BONUS_PERIOD_DAYS_PARAM.id: Decimal(str(period_days)),
        }
        mock_vault = self.create_mock(
            account_id=ACCOUNT_ID,
            activation_datetime=ACCOUNT_CREATION_DATETIME,
            creation_date=ACCOUNT_CREATION_DATETIME,
            balances_observation_fetchers_mapping={
                fetchers.EFFECTIVE_DATE_BOF.fetcher_id: BalancesObservation(
                    balances=balances,
                    value_datetime=effective_datetime,
                    at_datetime=effective_datetime,
                ),
                fetchers.ALL_BALANCES_ET_BOF.fetcher_id: BalancesObservation(
                    balances=balances,
                    value_datetime=effective_datetime,
                    at_datetime=effective_datetime,
                ),
            },
            parameters_observation_fetchers_mapping={
                welcome_bonus_module.WELCOME_BONUS_POF.fetcher_id: ParametersObservation(
                    parameters=params, value_datetime=effective_datetime
                ),
            },
        )
        return MagicMock(
            vault=mock_vault,
            effective_datetime=effective_datetime,
            parameters=params,
            balances=balances,
        )

    @pytest.mark.unit
    def test_spend_tracked_on_purchase(self):
        state = self._setup_state(days_since_opening=10, spend_tracker=Decimal("0"))
        result = welcome_bonus_module.track_and_award_welcome_bonus(
            state=state,
            transaction_amount=Decimal("1000"),
            transaction_type="PURCHASE",
            account_type=ACCOUNT_TYPE,
        )
        # Should track spend (1 instruction) but not award bonus yet
        self.assertEqual(len(result), 1)
        debit = [p for p in result[0].postings if not p.credit][0]
        self.assertEqual(debit.account_address, apex_addresses.WELCOME_BONUS_SPEND_TRACKER)
        self.assertEqual(debit.amount, Decimal("1000"))

    @pytest.mark.unit
    def test_bonus_awarded_when_threshold_met(self):
        state = self._setup_state(
            days_since_opening=30,
            spend_tracker=Decimal("5500"),
        )
        result = welcome_bonus_module.track_and_award_welcome_bonus(
            state=state,
            transaction_amount=Decimal("600"),
            transaction_type="PURCHASE",
            account_type=ACCOUNT_TYPE,
        )
        # Should have 2 instructions: spend tracking + bonus award
        self.assertEqual(len(result), 2)
        # Second instruction should be bonus points
        bonus_debit = [p for p in result[1].postings if not p.credit][0]
        self.assertEqual(bonus_debit.account_address, apex_addresses.REWARDS_POINTS)
        self.assertEqual(bonus_debit.amount, Decimal("100000"))

    @pytest.mark.unit
    def test_no_tracking_for_cash_advance(self):
        state = self._setup_state(days_since_opening=10)
        result = welcome_bonus_module.track_and_award_welcome_bonus(
            state=state,
            transaction_amount=Decimal("1000"),
            transaction_type="CASH_ADVANCE",
            account_type=ACCOUNT_TYPE,
        )
        self.assertEqual(len(result), 0)

    @pytest.mark.unit
    def test_no_tracking_after_period_expires(self):
        state = self._setup_state(
            days_since_opening=91,
            spend_tracker=Decimal("0"),
            period_days=90,
        )
        result = welcome_bonus_module.track_and_award_welcome_bonus(
            state=state,
            transaction_amount=Decimal("1000"),
            transaction_type="PURCHASE",
            account_type=ACCOUNT_TYPE,
        )
        self.assertEqual(len(result), 0)

    @pytest.mark.unit
    def test_no_tracking_when_threshold_already_met(self):
        state = self._setup_state(
            days_since_opening=30,
            spend_tracker=Decimal("6000"),
        )
        result = welcome_bonus_module.track_and_award_welcome_bonus(
            state=state,
            transaction_amount=Decimal("100"),
            transaction_type="PURCHASE",
            account_type=ACCOUNT_TYPE,
        )
        self.assertEqual(len(result), 0)

    @pytest.mark.unit
    def test_no_tracking_for_zero_amount(self):
        state = self._setup_state(days_since_opening=10)
        result = welcome_bonus_module.track_and_award_welcome_bonus(
            state=state,
            transaction_amount=Decimal("0"),
            transaction_type="PURCHASE",
            account_type=ACCOUNT_TYPE,
        )
        self.assertEqual(len(result), 0)

    @pytest.mark.unit
    def test_tracking_on_last_day_of_period(self):
        state = self._setup_state(
            days_since_opening=90,
            spend_tracker=Decimal("0"),
            period_days=90,
        )
        result = welcome_bonus_module.track_and_award_welcome_bonus(
            state=state,
            transaction_amount=Decimal("1000"),
            transaction_type="PURCHASE",
            account_type=ACCOUNT_TYPE,
        )
        # Day 90 is within 90-day period
        self.assertEqual(len(result), 1)

    @pytest.mark.unit
    def test_no_tracking_for_fee_transaction(self):
        state = self._setup_state(days_since_opening=10)
        result = welcome_bonus_module.track_and_award_welcome_bonus(
            state=state,
            transaction_amount=Decimal("100"),
            transaction_type="FEE",
            account_type=ACCOUNT_TYPE,
        )
        self.assertEqual(len(result), 0)

    @pytest.mark.unit
    def test_refund_decrements_spend_tracker(self):
        state = self._setup_state(
            days_since_opening=30,
            spend_tracker=Decimal("3000"),
        )
        result = welcome_bonus_module.track_and_award_welcome_bonus(
            state=state,
            transaction_amount=Decimal("-500"),
            transaction_type="PURCHASE",
            account_type=ACCOUNT_TYPE,
        )
        self.assertEqual(len(result), 1)
        # Reversal credits the spend tracker
        credit = [p for p in result[0].postings if p.credit][0]
        self.assertEqual(credit.account_address, apex_addresses.WELCOME_BONUS_SPEND_TRACKER)
        self.assertEqual(credit.amount, Decimal("500"))

    @pytest.mark.unit
    def test_refund_capped_at_current_spend(self):
        # Refund of 500 but only 200 tracked spend
        state = self._setup_state(
            days_since_opening=30,
            spend_tracker=Decimal("200"),
        )
        result = welcome_bonus_module.track_and_award_welcome_bonus(
            state=state,
            transaction_amount=Decimal("-500"),
            transaction_type="PURCHASE",
            account_type=ACCOUNT_TYPE,
        )
        self.assertEqual(len(result), 1)
        credit = [p for p in result[0].postings if p.credit][0]
        self.assertEqual(credit.amount, Decimal("200"))

    @pytest.mark.unit
    def test_refund_no_reversal_when_no_spend_tracked(self):
        state = self._setup_state(
            days_since_opening=30,
            spend_tracker=Decimal("0"),
        )
        result = welcome_bonus_module.track_and_award_welcome_bonus(
            state=state,
            transaction_amount=Decimal("-500"),
            transaction_type="PURCHASE",
            account_type=ACCOUNT_TYPE,
        )
        self.assertEqual(len(result), 0)

    @pytest.mark.unit
    def test_refund_still_tracked_after_period_expires(self):
        # Refunds should still be processed even after the bonus period
        state = self._setup_state(
            days_since_opening=91,
            spend_tracker=Decimal("3000"),
            period_days=90,
        )
        result = welcome_bonus_module.track_and_award_welcome_bonus(
            state=state,
            transaction_amount=Decimal("-500"),
            transaction_type="PURCHASE",
            account_type=ACCOUNT_TYPE,
        )
        # Period expired, but refund reversal should NOT happen (period check applies)
        self.assertEqual(len(result), 0)
