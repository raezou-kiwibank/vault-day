# standard libs
from datetime import datetime
from decimal import Decimal
from unittest.mock import MagicMock
from zoneinfo import ZoneInfo

import pytest

# features
import feature_library.common.fetchers as fetchers
import feature_library.lending.addresses as apex_addresses
import feature_library.lending.limits.credit_limit as credit_limit_module

# contracts api
from contracts_api import (
    DEFAULT_ASSET,
    Balance,
    BalanceCoordinate,
    BalanceDefaultDict,
    BalancesObservation,
    ParametersObservation,
    Phase,
    Rejection,
    RejectionReason,
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


class CreditLimitTest(FeatureTest):
    def _create_balances(
        self,
        purchase: Decimal = Decimal(0),
        cash_advance: Decimal = Decimal(0),
        interest_charged: Decimal = Decimal(0),
        fees: Decimal = Decimal(0),
    ) -> BalanceDefaultDict:
        mapping = {}
        for address, amount in [
            (apex_addresses.PURCHASE, purchase),
            (apex_addresses.CASH_ADVANCE, cash_advance),
            (apex_addresses.INTEREST_CHARGED, interest_charged),
            (apex_addresses.FEES, fees),
        ]:
            if amount != 0:
                mapping[
                    BalanceCoordinate(address, DEFAULT_ASSET, DENOMINATION, Phase.COMMITTED)
                ] = Balance(amount, Decimal(0), amount)
        return BalanceDefaultDict(lambda: Balance(), mapping)

    def _setup_state(
        self,
        credit_limit: Decimal = Decimal("5000"),
        purchase: Decimal = Decimal(0),
        cash_advance: Decimal = Decimal(0),
        interest_charged: Decimal = Decimal(0),
        fees: Decimal = Decimal(0),
    ) -> MagicMock:
        balances = self._create_balances(purchase, cash_advance, interest_charged, fees)
        params = {
            credit_limit_module.CREDIT_LIMIT_PARAM.id: credit_limit,
        }
        mock_vault = self.create_mock(
            account_id=ACCOUNT_ID,
            balances_observation_fetchers_mapping={
                fetchers.ALL_BALANCES_ET_BOF.fetcher_id: BalancesObservation(
                    balances=balances,
                    value_datetime=DEFAULT_DATETIME,
                    at_datetime=DEFAULT_DATETIME,
                ),
            },
            parameters_observation_fetchers_mapping={
                credit_limit_module.CREDIT_LIMIT_POF.fetcher_id: ParametersObservation(
                    parameters=params,
                    value_datetime=DEFAULT_DATETIME,
                ),
            },
        )
        state = MagicMock(
            vault=mock_vault,
            effective_datetime=DEFAULT_DATETIME,
            parameters=params,
            balances=balances,
        )
        return state

    @pytest.mark.unit
    def test_get_total_outstanding_zero_balance(self):
        balances = self._create_balances()
        result = credit_limit_module.get_total_outstanding(balances, DENOMINATION)
        self.assertEqual(result, Decimal(0))

    @pytest.mark.unit
    def test_get_total_outstanding_with_balances(self):
        balances = self._create_balances(
            purchase=Decimal("1000"),
            cash_advance=Decimal("500"),
            interest_charged=Decimal("50"),
            fees=Decimal("100"),
        )
        result = credit_limit_module.get_total_outstanding(balances, DENOMINATION)
        self.assertEqual(result, Decimal("1650"))

    @pytest.mark.unit
    def test_validate_credit_limit_accepts_posting_within_limit(self):
        state = self._setup_state(
            credit_limit=Decimal("5000"),
            purchase=Decimal("1000"),
        )
        result = credit_limit_module.validate_credit_limit(
            state=state,
            denomination=DENOMINATION,
            posting_amount=Decimal("500"),
        )
        self.assertIsNone(result)

    @pytest.mark.unit
    def test_validate_credit_limit_accepts_posting_at_limit(self):
        state = self._setup_state(
            credit_limit=Decimal("5000"),
            purchase=Decimal("4000"),
        )
        result = credit_limit_module.validate_credit_limit(
            state=state,
            denomination=DENOMINATION,
            posting_amount=Decimal("1000"),
        )
        self.assertIsNone(result)

    @pytest.mark.unit
    def test_validate_credit_limit_rejects_posting_over_limit(self):
        state = self._setup_state(
            credit_limit=Decimal("5000"),
            purchase=Decimal("4500"),
        )
        result = credit_limit_module.validate_credit_limit(
            state=state,
            denomination=DENOMINATION,
            posting_amount=Decimal("600"),
        )
        self.assertIsNotNone(result)
        self.assertIsInstance(result, Rejection)
        self.assertEqual(result.reason_code, RejectionReason.INSUFFICIENT_FUNDS)  # ty: ignore[possibly-missing-attribute]  # noqa: E501
        self.assertIn("credit limit", result.message)  # ty: ignore[possibly-missing-attribute]

    @pytest.mark.unit
    def test_validate_credit_limit_considers_all_balance_types(self):
        state = self._setup_state(
            credit_limit=Decimal("5000"),
            purchase=Decimal("2000"),
            cash_advance=Decimal("1000"),
            interest_charged=Decimal("500"),
            fees=Decimal("1000"),
        )
        # Total outstanding = 4500, posting 600 would be 5100 > 5000
        result = credit_limit_module.validate_credit_limit(
            state=state,
            denomination=DENOMINATION,
            posting_amount=Decimal("600"),
        )
        self.assertIsNotNone(result)
        self.assertIsInstance(result, Rejection)

    @pytest.mark.unit
    def test_validate_credit_limit_rejects_zero_limit(self):
        state = self._setup_state(credit_limit=Decimal("0"))
        result = credit_limit_module.validate_credit_limit(
            state=state,
            denomination=DENOMINATION,
            posting_amount=Decimal("100"),
        )
        self.assertIsNotNone(result)
        self.assertIsInstance(result, Rejection)
        self.assertEqual(result.reason_code, RejectionReason.AGAINST_TNC)
        self.assertIn("misconfigured", result.message)

    @pytest.mark.unit
    def test_validate_credit_limit_rejects_negative_limit(self):
        state = self._setup_state(credit_limit=Decimal("-500"))
        result = credit_limit_module.validate_credit_limit(
            state=state,
            denomination=DENOMINATION,
            posting_amount=Decimal("100"),
        )
        self.assertIsNotNone(result)
        self.assertIsInstance(result, Rejection)
        self.assertEqual(result.reason_code, RejectionReason.AGAINST_TNC)

    @pytest.mark.unit
    def test_get_available_credit(self):
        state = self._setup_state(
            credit_limit=Decimal("5000"),
            purchase=Decimal("2000"),
            cash_advance=Decimal("500"),
        )
        result = credit_limit_module.get_available_credit(
            state=state,
            denomination=DENOMINATION,
        )
        self.assertEqual(result, Decimal("2500"))
