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
import feature_library.lending.fees.foreign_transaction_fee as fx_fee_module

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
FX_FEE_INCOME_ACCOUNT = "FX_FEE_INCOME"
ACCOUNT_TYPE = "credit_card"


class ForeignTransactionFeeTest(FeatureTest):
    def _setup_state(
        self,
        percentage: Decimal = Decimal("0.03"),
    ) -> MagicMock:
        balances = BalanceDefaultDict(lambda: Balance(), {})
        params = {
            denomination_module.DENOMINATION_PARAM.id: DENOMINATION,
            fx_fee_module.FOREIGN_TRANSACTION_FEE_PERCENTAGE_PARAM.id: percentage,
            fx_fee_module.FOREIGN_TRANSACTION_FEE_INCOME_ACCOUNT_PARAM.id: FX_FEE_INCOME_ACCOUNT,
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
                fx_fee_module.FOREIGN_TRANSACTION_FEE_POF.fetcher_id: ParametersObservation(
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
    def test_fee_charged_on_foreign_transaction(self):
        state = self._setup_state(percentage=Decimal("0.03"))
        result = fx_fee_module.charge_foreign_transaction_fee(
            state=state,
            transaction_amount=Decimal("100"),
            account_type=ACCOUNT_TYPE,
        )
        self.assertEqual(len(result), 1)
        # 3% of 100 = 3.00
        postings = result[0].postings
        debit_posting = [p for p in postings if not p.credit][0]
        self.assertEqual(debit_posting.amount, Decimal("3.00"))
        self.assertEqual(debit_posting.account_address, apex_addresses.FEES)

    @pytest.mark.unit
    def test_no_fee_when_percentage_is_zero(self):
        state = self._setup_state(percentage=Decimal("0"))
        result = fx_fee_module.charge_foreign_transaction_fee(
            state=state,
            transaction_amount=Decimal("100"),
            account_type=ACCOUNT_TYPE,
        )
        self.assertEqual(len(result), 0)

    @pytest.mark.unit
    def test_no_fee_when_percentage_is_negative(self):
        state = self._setup_state(percentage=Decimal("-0.01"))
        result = fx_fee_module.charge_foreign_transaction_fee(
            state=state,
            transaction_amount=Decimal("100"),
            account_type=ACCOUNT_TYPE,
        )
        self.assertEqual(len(result), 0)

    @pytest.mark.unit
    def test_fee_rounds_half_up(self):
        state = self._setup_state(percentage=Decimal("0.03"))
        # 3% of 33.33 = 0.9999 -> rounds to 1.00
        result = fx_fee_module.charge_foreign_transaction_fee(
            state=state,
            transaction_amount=Decimal("33.33"),
            account_type=ACCOUNT_TYPE,
        )
        self.assertEqual(len(result), 1)
        postings = result[0].postings
        debit_posting = [p for p in postings if not p.credit][0]
        self.assertEqual(debit_posting.amount, Decimal("1.00"))

    @pytest.mark.unit
    def test_fee_credits_income_account(self):
        state = self._setup_state(percentage=Decimal("0.03"))
        result = fx_fee_module.charge_foreign_transaction_fee(
            state=state,
            transaction_amount=Decimal("100"),
            account_type=ACCOUNT_TYPE,
        )
        postings = result[0].postings
        credit_posting = [p for p in postings if p.credit][0]
        self.assertEqual(credit_posting.account_id, FX_FEE_INCOME_ACCOUNT)

    @pytest.mark.unit
    def test_assertion_error_on_missing_param(self):
        state = self._setup_state()
        del state.parameters[fx_fee_module.FOREIGN_TRANSACTION_FEE_PERCENTAGE_PARAM.id]
        with self.assertRaises(AssertionError):
            fx_fee_module.charge_foreign_transaction_fee(
                state=state,
                transaction_amount=Decimal("100"),
                account_type=ACCOUNT_TYPE,
            )
