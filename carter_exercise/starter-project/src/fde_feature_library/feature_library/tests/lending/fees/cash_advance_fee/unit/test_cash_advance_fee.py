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
import feature_library.lending.fees.cash_advance_fee as cash_advance_fee_module

# contracts api
from contracts_api import (
    Balance,
    BalanceDefaultDict,
    BalancesObservation,
    ParametersObservation,
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
CASH_ADVANCE_FEE_INCOME_ACCOUNT = "CASH_ADVANCE_FEE_INCOME"
ACCOUNT_TYPE = "credit_card"


class CashAdvanceFeeCalculationTest(FeatureTest):
    @pytest.mark.unit
    def test_percentage_fee_greater_than_flat(self):
        # 3% of 500 = 15, flat = 3 -> 15
        result = cash_advance_fee_module.calculate_cash_advance_fee(
            amount=Decimal("500"),
            percentage=Decimal("0.03"),
            flat_amount=Decimal("3"),
        )
        self.assertEqual(result, Decimal("15.00"))

    @pytest.mark.unit
    def test_flat_fee_greater_than_percentage(self):
        # 3% of 50 = 1.50, flat = 3 -> 3
        result = cash_advance_fee_module.calculate_cash_advance_fee(
            amount=Decimal("50"),
            percentage=Decimal("0.03"),
            flat_amount=Decimal("3"),
        )
        self.assertEqual(result, Decimal("3"))

    @pytest.mark.unit
    def test_percentage_fee_rounds_half_up(self):
        # 3% of 16.67 = 0.5001 -> rounds to 0.50
        result = cash_advance_fee_module.calculate_cash_advance_fee(
            amount=Decimal("16.67"),
            percentage=Decimal("0.03"),
            flat_amount=Decimal("0"),
        )
        self.assertEqual(result, Decimal("0.50"))


class CashAdvanceFeeChargeTest(FeatureTest):
    def _setup_state(
        self,
        transaction_amount: Decimal = Decimal("200"),
        percentage: Decimal = Decimal("0.03"),
        flat_amount: Decimal = Decimal("3"),
    ) -> MagicMock:
        balances = BalanceDefaultDict(lambda: Balance(), {})
        params = {
            denomination_module.DENOMINATION_PARAM.id: DENOMINATION,
            cash_advance_fee_module.CASH_ADVANCE_FEE_PERCENTAGE_PARAM.id: percentage,
            cash_advance_fee_module.CASH_ADVANCE_FEE_FLAT_AMOUNT_PARAM.id: flat_amount,
            cash_advance_fee_module.CASH_ADVANCE_FEE_INCOME_ACCOUNT_PARAM.id: CASH_ADVANCE_FEE_INCOME_ACCOUNT,  # noqa: E501
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
                cash_advance_fee_module.CASH_ADVANCE_FEE_POF.fetcher_id: ParametersObservation(
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
    def test_fee_charged_on_cash_advance(self):
        state = self._setup_state(transaction_amount=Decimal("200"))
        result = cash_advance_fee_module.charge_cash_advance_fee(
            state=state,
            transaction_amount=Decimal("200"),
            account_type=ACCOUNT_TYPE,
        )
        self.assertEqual(len(result), 1)
        # 3% of 200 = 6, which is > flat 3
        postings = result[0].postings
        debit_posting = [p for p in postings if not p.credit][0]
        self.assertEqual(debit_posting.amount, Decimal("6.00"))
        self.assertEqual(debit_posting.account_address, apex_addresses.FEES)

    @pytest.mark.unit
    def test_fee_uses_flat_minimum(self):
        state = self._setup_state(
            transaction_amount=Decimal("50"),
            percentage=Decimal("0.03"),
            flat_amount=Decimal("3"),
        )
        result = cash_advance_fee_module.charge_cash_advance_fee(
            state=state,
            transaction_amount=Decimal("50"),
            account_type=ACCOUNT_TYPE,
        )
        self.assertEqual(len(result), 1)
        # 3% of 50 = 1.50 < flat 3 -> fee = 3
        postings = result[0].postings
        debit_posting = [p for p in postings if not p.credit][0]
        self.assertEqual(debit_posting.amount, Decimal("3"))

    @pytest.mark.unit
    def test_fee_credits_income_account(self):
        state = self._setup_state()
        result = cash_advance_fee_module.charge_cash_advance_fee(
            state=state,
            transaction_amount=Decimal("200"),
            account_type=ACCOUNT_TYPE,
        )
        postings = result[0].postings
        credit_posting = [p for p in postings if p.credit][0]
        self.assertEqual(credit_posting.account_id, CASH_ADVANCE_FEE_INCOME_ACCOUNT)

    @pytest.mark.unit
    def test_no_fee_when_both_zero(self):
        state = self._setup_state(
            percentage=Decimal("0"),
            flat_amount=Decimal("0"),
        )
        result = cash_advance_fee_module.charge_cash_advance_fee(
            state=state,
            transaction_amount=Decimal("200"),
            account_type=ACCOUNT_TYPE,
        )
        self.assertEqual(len(result), 0)

    @pytest.mark.unit
    def test_assertion_error_on_missing_param(self):
        state = self._setup_state()
        # Remove a required parameter
        del state.parameters[cash_advance_fee_module.CASH_ADVANCE_FEE_PERCENTAGE_PARAM.id]
        with self.assertRaises(AssertionError):
            cash_advance_fee_module.charge_cash_advance_fee(
                state=state,
                transaction_amount=Decimal("200"),
                account_type=ACCOUNT_TYPE,
            )
