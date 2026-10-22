# standard libs
from datetime import datetime
from decimal import Decimal
from unittest.mock import MagicMock
from zoneinfo import ZoneInfo

import pytest

import feature_library.common.denomination as denomination_module

# features
import feature_library.common.fetchers as fetchers
import feature_library.lending.addresses as apex_addresses
import feature_library.lending.rewards.points_accrual as points_accrual_module

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
DEFAULT_DATETIME = datetime(2026, 1, 1, tzinfo=UTC_ZONE)

DENOMINATION = DEFAULT_DENOMINATION
ACCOUNT_TYPE = "credit_card"


class PointsRateTest(FeatureTest):
    @pytest.mark.unit
    def test_travel_portal_rate(self):
        result = points_accrual_module._get_points_rate_for_category(
            merchant_category=points_accrual_module.CATEGORY_TRAVEL_PORTAL,
            travel_portal_rate=Decimal("5"),
            travel_dining_rate=Decimal("3"),
            other_rate=Decimal("2"),
        )
        self.assertEqual(result, Decimal("5"))

    @pytest.mark.unit
    def test_travel_dining_rate(self):
        result = points_accrual_module._get_points_rate_for_category(
            merchant_category=points_accrual_module.CATEGORY_TRAVEL_DINING,
            travel_portal_rate=Decimal("5"),
            travel_dining_rate=Decimal("3"),
            other_rate=Decimal("2"),
        )
        self.assertEqual(result, Decimal("3"))

    @pytest.mark.unit
    def test_other_rate(self):
        result = points_accrual_module._get_points_rate_for_category(
            merchant_category=points_accrual_module.CATEGORY_OTHER,
            travel_portal_rate=Decimal("5"),
            travel_dining_rate=Decimal("3"),
            other_rate=Decimal("2"),
        )
        self.assertEqual(result, Decimal("2"))

    @pytest.mark.unit
    def test_unknown_category_uses_other_rate(self):
        result = points_accrual_module._get_points_rate_for_category(
            merchant_category="unknown_category",
            travel_portal_rate=Decimal("5"),
            travel_dining_rate=Decimal("3"),
            other_rate=Decimal("2"),
        )
        self.assertEqual(result, Decimal("2"))


class PointsAccrualTest(FeatureTest):
    def _create_balances(
        self,
        rewards_points: Decimal = Decimal(0),
    ) -> BalanceDefaultDict:
        mapping = {}
        if rewards_points != 0:
            mapping[
                BalanceCoordinate(
                    apex_addresses.REWARDS_POINTS,
                    DEFAULT_ASSET,
                    DENOMINATION,
                    Phase.COMMITTED,
                )
            ] = Balance(rewards_points, Decimal(0), rewards_points)
        return BalanceDefaultDict(lambda: Balance(), mapping)

    def _setup_state(
        self,
        travel_portal_rate: Decimal = Decimal("5"),
        travel_dining_rate: Decimal = Decimal("3"),
        other_rate: Decimal = Decimal("2"),
        rewards_points: Decimal = Decimal(0),
    ) -> MagicMock:
        balances = self._create_balances(rewards_points=rewards_points)
        params = {
            denomination_module.DENOMINATION_PARAM.id: DENOMINATION,
            points_accrual_module.POINTS_RATE_TRAVEL_PORTAL_PARAM.id: travel_portal_rate,
            points_accrual_module.POINTS_RATE_TRAVEL_DINING_PARAM.id: travel_dining_rate,
            points_accrual_module.POINTS_RATE_OTHER_PARAM.id: other_rate,
        }
        mock_vault = self.create_mock(
            account_id=ACCOUNT_ID,
            balances_observation_fetchers_mapping={
                fetchers.EFFECTIVE_DATE_BOF.fetcher_id: BalancesObservation(
                    balances=balances,
                    value_datetime=DEFAULT_DATETIME,
                    at_datetime=DEFAULT_DATETIME,
                ),
                fetchers.ALL_BALANCES_ET_BOF.fetcher_id: BalancesObservation(
                    balances=balances,
                    value_datetime=DEFAULT_DATETIME,
                    at_datetime=DEFAULT_DATETIME,
                ),
            },
            parameters_observation_fetchers_mapping={
                points_accrual_module.POINTS_ACCRUAL_POF.fetcher_id: ParametersObservation(
                    parameters=params, value_datetime=DEFAULT_DATETIME
                ),
            },
        )
        return MagicMock(
            vault=mock_vault,
            effective_datetime=DEFAULT_DATETIME,
            parameters=params,
            balances=balances,
        )

    @pytest.mark.unit
    def test_5x_points_on_travel_portal(self):
        state = self._setup_state()
        result = points_accrual_module.accrue_points(
            state=state,
            transaction_amount=Decimal("100"),
            merchant_category=points_accrual_module.CATEGORY_TRAVEL_PORTAL,
            transaction_type="PURCHASE",
            account_type=ACCOUNT_TYPE,
        )
        self.assertEqual(len(result), 1)
        debit = [p for p in result[0].postings if not p.credit][0]
        self.assertEqual(debit.amount, Decimal("500"))
        self.assertEqual(debit.account_address, apex_addresses.REWARDS_POINTS)

    @pytest.mark.unit
    def test_3x_points_on_travel_dining(self):
        state = self._setup_state()
        result = points_accrual_module.accrue_points(
            state=state,
            transaction_amount=Decimal("100"),
            merchant_category=points_accrual_module.CATEGORY_TRAVEL_DINING,
            transaction_type="PURCHASE",
            account_type=ACCOUNT_TYPE,
        )
        self.assertEqual(len(result), 1)
        debit = [p for p in result[0].postings if not p.credit][0]
        self.assertEqual(debit.amount, Decimal("300"))

    @pytest.mark.unit
    def test_2x_points_on_other(self):
        state = self._setup_state()
        result = points_accrual_module.accrue_points(
            state=state,
            transaction_amount=Decimal("100"),
            merchant_category=points_accrual_module.CATEGORY_OTHER,
            transaction_type="PURCHASE",
            account_type=ACCOUNT_TYPE,
        )
        self.assertEqual(len(result), 1)
        debit = [p for p in result[0].postings if not p.credit][0]
        self.assertEqual(debit.amount, Decimal("200"))

    @pytest.mark.unit
    def test_no_points_on_cash_advance(self):
        state = self._setup_state()
        result = points_accrual_module.accrue_points(
            state=state,
            transaction_amount=Decimal("100"),
            merchant_category=points_accrual_module.CATEGORY_OTHER,
            transaction_type="CASH_ADVANCE",
            account_type=ACCOUNT_TYPE,
        )
        self.assertEqual(len(result), 0)

    @pytest.mark.unit
    def test_no_points_on_fee(self):
        state = self._setup_state()
        result = points_accrual_module.accrue_points(
            state=state,
            transaction_amount=Decimal("100"),
            merchant_category=points_accrual_module.CATEGORY_OTHER,
            transaction_type="FEE",
            account_type=ACCOUNT_TYPE,
        )
        self.assertEqual(len(result), 0)

    @pytest.mark.unit
    def test_no_points_on_zero_amount(self):
        state = self._setup_state()
        result = points_accrual_module.accrue_points(
            state=state,
            transaction_amount=Decimal("0"),
            merchant_category=points_accrual_module.CATEGORY_OTHER,
            transaction_type="PURCHASE",
            account_type=ACCOUNT_TYPE,
        )
        self.assertEqual(len(result), 0)

    @pytest.mark.unit
    def test_points_floor_rounded(self):
        # 2x on 10.99 = 21.98 -> floor to 21
        state = self._setup_state()
        result = points_accrual_module.accrue_points(
            state=state,
            transaction_amount=Decimal("10.99"),
            merchant_category=points_accrual_module.CATEGORY_OTHER,
            transaction_type="PURCHASE",
            account_type=ACCOUNT_TYPE,
        )
        self.assertEqual(len(result), 1)
        debit = [p for p in result[0].postings if not p.credit][0]
        self.assertEqual(debit.amount, Decimal("21"))

    @pytest.mark.unit
    def test_refund_claws_back_points(self):
        # Refund of 50 at 2x rate = 100 points clawback, capped at 200 existing
        state = self._setup_state(rewards_points=Decimal("200"))
        result = points_accrual_module.accrue_points(
            state=state,
            transaction_amount=Decimal("-50"),
            merchant_category=points_accrual_module.CATEGORY_OTHER,
            transaction_type="PURCHASE",
            account_type=ACCOUNT_TYPE,
        )
        self.assertEqual(len(result), 1)
        # Clawback reverses the posting direction: credit REWARDS_POINTS
        credit = [p for p in result[0].postings if p.credit][0]
        self.assertEqual(credit.account_address, apex_addresses.REWARDS_POINTS)
        self.assertEqual(credit.amount, Decimal("100"))

    @pytest.mark.unit
    def test_refund_clawback_capped_at_current_points(self):
        # Refund of 100 at 2x = 200 clawback, but only 50 points exist
        state = self._setup_state(rewards_points=Decimal("50"))
        result = points_accrual_module.accrue_points(
            state=state,
            transaction_amount=Decimal("-100"),
            merchant_category=points_accrual_module.CATEGORY_OTHER,
            transaction_type="PURCHASE",
            account_type=ACCOUNT_TYPE,
        )
        self.assertEqual(len(result), 1)
        credit = [p for p in result[0].postings if p.credit][0]
        self.assertEqual(credit.amount, Decimal("50"))

    @pytest.mark.unit
    def test_refund_no_clawback_when_no_points(self):
        # Refund but no points to claw back
        state = self._setup_state(rewards_points=Decimal("0"))
        result = points_accrual_module.accrue_points(
            state=state,
            transaction_amount=Decimal("-50"),
            merchant_category=points_accrual_module.CATEGORY_OTHER,
            transaction_type="PURCHASE",
            account_type=ACCOUNT_TYPE,
        )
        self.assertEqual(len(result), 0)

    @pytest.mark.unit
    def test_no_clawback_on_cash_advance_refund(self):
        state = self._setup_state(rewards_points=Decimal("200"))
        result = points_accrual_module.accrue_points(
            state=state,
            transaction_amount=Decimal("-50"),
            merchant_category=points_accrual_module.CATEGORY_OTHER,
            transaction_type="CASH_ADVANCE",
            account_type=ACCOUNT_TYPE,
        )
        self.assertEqual(len(result), 0)
