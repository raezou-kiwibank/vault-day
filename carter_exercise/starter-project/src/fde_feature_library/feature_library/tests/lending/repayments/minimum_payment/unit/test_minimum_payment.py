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
import feature_library.lending.repayments.minimum_payment as minimum_payment_module

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


class MinimumPaymentCalculationTest(FeatureTest):
    @pytest.mark.unit
    def test_percentage_is_highest(self):
        # 2% of 5000 = 100, fixed = 25, interest+fees = 30
        result = minimum_payment_module.calculate_minimum_payment(
            total_balance=Decimal("5000"),
            accrued_interest=Decimal("20"),
            fees=Decimal("10"),
            percentage=Decimal("0.02"),
            fixed_amount=Decimal("25"),
        )
        self.assertEqual(result, Decimal("100.00"))

    @pytest.mark.unit
    def test_fixed_amount_is_highest(self):
        # 2% of 1000 = 20, fixed = 25, interest+fees = 10
        result = minimum_payment_module.calculate_minimum_payment(
            total_balance=Decimal("1000"),
            accrued_interest=Decimal("5"),
            fees=Decimal("5"),
            percentage=Decimal("0.02"),
            fixed_amount=Decimal("25"),
        )
        self.assertEqual(result, Decimal("25"))

    @pytest.mark.unit
    def test_interest_plus_fees_is_highest(self):
        # 2% of 500 = 10, fixed = 25, interest+fees = 50
        result = minimum_payment_module.calculate_minimum_payment(
            total_balance=Decimal("500"),
            accrued_interest=Decimal("30"),
            fees=Decimal("20"),
            percentage=Decimal("0.02"),
            fixed_amount=Decimal("25"),
        )
        self.assertEqual(result, Decimal("50"))

    @pytest.mark.unit
    def test_capped_at_total_balance(self):
        # Min payment would be 25 but total balance is only 10
        result = minimum_payment_module.calculate_minimum_payment(
            total_balance=Decimal("10"),
            accrued_interest=Decimal("0"),
            fees=Decimal("0"),
            percentage=Decimal("0.02"),
            fixed_amount=Decimal("25"),
        )
        self.assertEqual(result, Decimal("10"))

    @pytest.mark.unit
    def test_zero_balance(self):
        result = minimum_payment_module.calculate_minimum_payment(
            total_balance=Decimal("0"),
            accrued_interest=Decimal("0"),
            fees=Decimal("0"),
            percentage=Decimal("0.02"),
            fixed_amount=Decimal("25"),
        )
        self.assertEqual(result, Decimal("0"))

    @pytest.mark.unit
    def test_negative_balance(self):
        # Customer has a credit balance (overpaid)
        result = minimum_payment_module.calculate_minimum_payment(
            total_balance=Decimal("-50"),
            accrued_interest=Decimal("0"),
            fees=Decimal("0"),
            percentage=Decimal("0.02"),
            fixed_amount=Decimal("25"),
        )
        self.assertEqual(result, Decimal("0"))


class StatementCutScheduleTest(FeatureTest):
    @pytest.mark.unit
    def test_get_scheduled_events(self):
        statement_time = "00:00:01"
        day = "15"
        mock_state = initialise_mock_state(
            effective_datetime=DEFAULT_DATETIME,
            parameters={
                minimum_payment_module.STATEMENT_TIME_PARAM.id: statement_time,
                minimum_payment_module.STATEMENT_DAY_PARAM.id: day,
            },
        )

        mock_state.vault.events_timezone = UTC_ZONE

        with patch.object(
            minimum_payment_module.state_utils, "append_to_state", return_value=mock_state
        ):
            result = minimum_payment_module.get_scheduled_events(state=mock_state)

        expected_event = {
            minimum_payment_module.STATEMENT_CUT_EVENT: ScheduledEvent(
                start_datetime=DEFAULT_DATETIME,
                expression=ScheduleExpression(
                    day=15,
                    hour=0,
                    minute=0,
                    second=1,
                ),
            )
        }
        self.assertEqual(result, expected_event)


class StatementCutLogicTest(FeatureTest):
    def _create_balances(
        self,
        purchase: Decimal = Decimal(0),
        cash_advance: Decimal = Decimal(0),
        interest_charged: Decimal = Decimal(0),
        fees: Decimal = Decimal(0),
        accrued_purchase: Decimal = Decimal(0),
        accrued_cash_advance: Decimal = Decimal(0),
        min_payment_tracker: Decimal = Decimal(0),
        statement_balance_tracker: Decimal = Decimal(0),
        total_repayments_tracker: Decimal = Decimal(0),
    ) -> BalanceDefaultDict:
        mapping = {}
        for address, amount in [
            (apex_addresses.PURCHASE, purchase),
            (apex_addresses.CASH_ADVANCE, cash_advance),
            (apex_addresses.INTEREST_CHARGED, interest_charged),
            (apex_addresses.FEES, fees),
            (apex_addresses.INTEREST_ACCRUED_PURCHASE, accrued_purchase),
            (apex_addresses.INTEREST_ACCRUED_CASH_ADVANCE, accrued_cash_advance),
            (apex_addresses.MINIMUM_PAYMENT_DUE_TRACKER, min_payment_tracker),
            (apex_addresses.STATEMENT_BALANCE_TRACKER, statement_balance_tracker),
            (apex_addresses.TOTAL_REPAYMENTS_TRACKER, total_repayments_tracker),
        ]:
            if amount != 0:
                mapping[
                    BalanceCoordinate(address, DEFAULT_ASSET, DENOMINATION, Phase.COMMITTED)
                ] = Balance(amount, Decimal(0), amount)
        return BalanceDefaultDict(lambda: Balance(), mapping)

    def _setup_state(
        self,
        balances: BalanceDefaultDict | None = None,
        percentage: Decimal = Decimal("0.02"),
        fixed_amount: Decimal = Decimal("25"),
    ) -> MagicMock:
        if balances is None:
            balances = self._create_balances()

        params = {
            denomination_module.DENOMINATION_PARAM.id: DENOMINATION,
            minimum_payment_module.MINIMUM_PAYMENT_PERCENTAGE_PARAM.id: percentage,
            minimum_payment_module.MINIMUM_PAYMENT_FIXED_AMOUNT_PARAM.id: fixed_amount,
            minimum_payment_module.STATEMENT_DAY_PARAM.id: "15",
            minimum_payment_module.PAYMENT_DUE_DAYS_PARAM.id: "25",
            minimum_payment_module.STATEMENT_TIME_PARAM.id: "00:00:01",
            minimum_payment_module.INTEREST_RECEIVABLE_ACCOUNT_PARAM.id: INTEREST_RECEIVABLE_ACCOUNT,  # noqa: E501
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
                minimum_payment_module.STATEMENT_CUT_POF.fetcher_id: ParametersObservation(
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
    def test_statement_cut_with_purchase_balance_and_accrued_interest(self):
        balances = self._create_balances(
            purchase=Decimal("1000"),
            accrued_purchase=Decimal("20.12345"),
        )
        state = self._setup_state(balances=balances)
        result = minimum_payment_module.statement_cut_logic(state=state, account_type=ACCOUNT_TYPE)
        # Should have instructions for:
        # 1. Interest application (accrued -> charged)
        # 2. Minimum payment tracker
        # 3. Statement balance tracker
        self.assertTrue(len(result) > 0)

    @pytest.mark.unit
    def test_statement_cut_zero_balance(self):
        balances = self._create_balances()
        state = self._setup_state(balances=balances)
        result = minimum_payment_module.statement_cut_logic(state=state, account_type=ACCOUNT_TYPE)
        # With zero balance, no tracker postings needed
        self.assertEqual(len(result), 0)
