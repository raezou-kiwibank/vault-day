# Copyright @ 2026 Thought Machine Group Limited. All rights reserved.
# standard libs
from datetime import datetime
from decimal import Decimal
from unittest.mock import MagicMock
from zoneinfo import ZoneInfo

import pytest

import feature_library.common.denomination as denomination_module

# features
import feature_library.common.state_utils as state_utils
from feature_library.deposit.transaction_limits.withdrawal_limits import (
    maximum_withdrawal_by_payment_type,
)

# contracts api
from contracts_api import (
    DEFAULT_ADDRESS,
    DEFAULT_ASSET,
    Balance,
    BalanceCoordinate,
    BalanceDefaultDict,
    ParametersObservation,
    Phase,
    Rejection,
    RejectionReason,
)

# inception sdk
from inception_sdk.test_framework.contracts.unit.common import (
    DEFAULT_DATETIME,
    DEFAULT_DENOMINATION,
)

from tests.deposit.transaction_limits.deposit_limits.test_common_transaction_limit import (
    CommonTransactionLimitTest,
)

UTC = ZoneInfo("UTC")


class TestMaximumWithdrawalByPaymentTypeLimit(CommonTransactionLimitTest):
    def _simple_mock(
        self,
        creation_date: datetime = DEFAULT_DATETIME,
        max_withdrawal_by_payment_type: str | None = None,
    ) -> MagicMock:
        return super().create_mock(
            creation_date=creation_date,
            parameters_observation_fetchers_mapping={
                maximum_withdrawal_by_payment_type.MAX_WITHDRAWAL_BY_PAYMENT_TYPE_POF.fetcher_id: ParametersObservation(  # noqa: E501
                    parameters={
                        maximum_withdrawal_by_payment_type.MAX_WITHDRAWAL_BY_PAYMENT_TYPE_PARAM.id: max_withdrawal_by_payment_type  # noqa: E501
                    },
                    value_datetime=creation_date,
                )
            },
        )

    def mock_posting(
        self,
        withdrawal_amount: Decimal,
        payment_type: str | None = None,
        denomination: str = DEFAULT_DENOMINATION,
    ):
        mock_instruction = MagicMock()
        mock_instruction.instruction_details = {}
        if payment_type:
            mock_instruction.instruction_details[
                maximum_withdrawal_by_payment_type.PAYMENT_TYPE
            ] = payment_type

        def mock_balances():
            return BalanceDefaultDict(
                lambda: Balance(),
                {
                    BalanceCoordinate(
                        DEFAULT_ADDRESS, DEFAULT_ASSET, denomination, Phase.COMMITTED
                    ): Balance(debit=withdrawal_amount, credit=Decimal(0))
                },
            )

        mock_instruction.balances.side_effect = mock_balances
        return mock_instruction

    @pytest.mark.unit
    def test_limit_exceeded(self):
        effective_datetime = datetime(2026, 1, 1, 12, tzinfo=UTC)
        withdrawal_amount = Decimal("100.01")
        payment_type = "ATM"
        postings = [self.mock_posting(withdrawal_amount, payment_type=payment_type)]

        mock_vault = self._simple_mock(
            creation_date=effective_datetime,
            max_withdrawal_by_payment_type='{"ATM": "100"}',
        )
        state = state_utils.initialise_state(
            vault=mock_vault,
            effective_datetime=effective_datetime,
            parameters={
                denomination_module.DENOMINATION_PARAM.id: DEFAULT_DENOMINATION,
            },
        )
        expected_rejection = Rejection(
            message=f"Transaction amount {withdrawal_amount:0.2f} {DEFAULT_DENOMINATION} is "
            f"more than the maximum withdrawal amount 100 "
            f"{DEFAULT_DENOMINATION} allowed for the the payment type {payment_type}.",
            reason_code=RejectionReason.AGAINST_TNC,
        )
        result = maximum_withdrawal_by_payment_type.validate(
            state=state,
            postings=postings,
        )
        self.assertEqual(result, expected_rejection)

    @pytest.mark.unit
    def test_limit_met(self):
        effective_datetime = datetime(2026, 1, 1, 12, tzinfo=UTC)
        withdrawal_amount = Decimal("100")
        payment_type = "ATM"
        postings = [self.mock_posting(withdrawal_amount, payment_type=payment_type)]

        mock_vault = self._simple_mock(
            creation_date=effective_datetime,
            max_withdrawal_by_payment_type='{"ATM": "100"}',
        )
        state = state_utils.initialise_state(
            vault=mock_vault,
            effective_datetime=effective_datetime,
            parameters={
                denomination_module.DENOMINATION_PARAM.id: DEFAULT_DENOMINATION,
            },
        )
        result = maximum_withdrawal_by_payment_type.validate(
            state=state,
            postings=postings,
        )
        self.assertIsNone(result)

    @pytest.mark.unit
    def test_limit_not_exceeded(self):
        effective_datetime = datetime(2026, 1, 1, 12, tzinfo=UTC)
        withdrawal_amount = Decimal("99.99")
        payment_type = "ATM"
        postings = [self.mock_posting(withdrawal_amount, payment_type=payment_type)]

        mock_vault = self._simple_mock(
            creation_date=effective_datetime,
            max_withdrawal_by_payment_type='{"ATM": "100"}',
        )
        state = state_utils.initialise_state(
            vault=mock_vault,
            effective_datetime=effective_datetime,
            parameters={
                denomination_module.DENOMINATION_PARAM.id: DEFAULT_DENOMINATION,
            },
        )
        result = maximum_withdrawal_by_payment_type.validate(
            state=state,
            postings=postings,
        )
        self.assertIsNone(result)

    @pytest.mark.unit
    def test_no_withdrawal_proposed(self):
        effective_datetime = datetime(2026, 1, 1, 12, tzinfo=UTC)
        # Deposit (negative net_debit)
        postings = [self.mock_posting(Decimal("-501"), payment_type="ATM")]

        mock_vault = self._simple_mock(
            creation_date=effective_datetime,
            max_withdrawal_by_payment_type='{"ATM": "100"}',
        )
        state = state_utils.initialise_state(
            vault=mock_vault,
            effective_datetime=effective_datetime,
            parameters={
                denomination_module.DENOMINATION_PARAM.id: DEFAULT_DENOMINATION,
            },
        )
        result = maximum_withdrawal_by_payment_type.validate(
            state=state,
            postings=postings,
        )
        self.assertIsNone(result)

    @pytest.mark.unit
    def test_transaction_type_not_in_limits(self):
        effective_datetime = datetime(2026, 1, 1, 12, tzinfo=UTC)
        withdrawal_amount = Decimal("501")
        payment_type = "UNKNOWN"
        postings = [self.mock_posting(withdrawal_amount, payment_type=payment_type)]

        mock_vault = self._simple_mock(
            creation_date=effective_datetime,
            max_withdrawal_by_payment_type='{"ATM": "100"}',
        )
        state = state_utils.initialise_state(
            vault=mock_vault,
            effective_datetime=effective_datetime,
            parameters={
                denomination_module.DENOMINATION_PARAM.id: DEFAULT_DENOMINATION,
            },
        )
        result = maximum_withdrawal_by_payment_type.validate(
            state=state,
            postings=postings,
        )
        self.assertIsNone(result)

    @pytest.mark.unit
    def test_no_limit_set(self):
        effective_datetime = datetime(2026, 1, 1, 12, tzinfo=UTC)
        withdrawal_amount = Decimal("501")
        payment_type = "ATM"
        postings = [self.mock_posting(withdrawal_amount, payment_type=payment_type)]

        mock_vault = self._simple_mock(
            creation_date=effective_datetime,
            max_withdrawal_by_payment_type="{}",
        )
        state = state_utils.initialise_state(
            vault=mock_vault,
            effective_datetime=effective_datetime,
            parameters={
                denomination_module.DENOMINATION_PARAM.id: DEFAULT_DENOMINATION,
            },
        )
        result = maximum_withdrawal_by_payment_type.validate(
            state=state,
            postings=postings,
        )
        self.assertIsNone(result)
