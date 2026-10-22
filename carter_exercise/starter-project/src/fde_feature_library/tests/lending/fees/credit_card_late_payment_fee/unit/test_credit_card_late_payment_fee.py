# standard libs
from datetime import datetime
from decimal import Decimal
from unittest.mock import MagicMock, patch, sentinel
from zoneinfo import ZoneInfo

import pytest

import feature_library.common.denomination as denomination_module

# features
import feature_library.common.fetchers as fetchers
import feature_library.lending.addresses as lending_addresses
import feature_library.lending.fees.credit_card_late_payment_fee as late_payment_fee_module

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

# feature_library
from tests.utils import initialise_mock_state

UTC_ZONE = ZoneInfo("UTC")
DEFAULT_DATETIME = datetime(2026, 1, 1, tzinfo=UTC_ZONE)

DENOMINATION = DEFAULT_DENOMINATION
LATE_PAYMENT_FEE_INCOME_ACCOUNT = "LATE_PAYMENT_FEE_INCOME"
ACCOUNT_TYPE = "credit_card"


class LatePaymentFeeTest(FeatureTest):
    def _create_balances(
        self,
        min_payment_tracker: Decimal = Decimal(0),
        total_repayments_tracker: Decimal = Decimal(0),
        fees: Decimal = Decimal(0),
    ) -> BalanceDefaultDict:
        mapping = {}
        for address, amount in [
            (lending_addresses.MINIMUM_PAYMENT_DUE_TRACKER, min_payment_tracker),
            (lending_addresses.TOTAL_REPAYMENTS_TRACKER, total_repayments_tracker),
            (lending_addresses.FEES, fees),
        ]:
            if amount != 0:
                mapping[
                    BalanceCoordinate(address, DEFAULT_ASSET, DENOMINATION, Phase.COMMITTED)
                ] = Balance(amount, Decimal(0), amount)
        return BalanceDefaultDict(lambda: Balance(), mapping)

    def _setup_state(
        self,
        fee_amount: Decimal = Decimal("12"),
        fee_enabled: str = "True",
        min_payment_tracker: Decimal = Decimal(0),
        total_repayments_tracker: Decimal = Decimal(0),
    ) -> MagicMock:
        balances = self._create_balances(
            min_payment_tracker=min_payment_tracker,
            total_repayments_tracker=total_repayments_tracker,
        )
        params = {
            denomination_module.DENOMINATION_PARAM.id: DENOMINATION,
            late_payment_fee_module.LATE_PAYMENT_FEE_AMOUNT_PARAM.id: fee_amount,
            late_payment_fee_module.LATE_PAYMENT_FEE_INCOME_ACCOUNT_PARAM.id: LATE_PAYMENT_FEE_INCOME_ACCOUNT,  # noqa: E501
            late_payment_fee_module.LATE_PAYMENT_FEE_ENABLED_PARAM.id: fee_enabled,
            late_payment_fee_module.LATE_PAYMENT_CHECK_DAY_PARAM.id: "26",
            late_payment_fee_module.LATE_PAYMENT_CHECK_TIME_PARAM.id: "00:00:02",
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
                late_payment_fee_module.LATE_PAYMENT_FEE_POF.fetcher_id: ParametersObservation(
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
    def test_late_payment_fee_applied_when_underpaid(self):
        state = self._setup_state(
            fee_amount=Decimal("12"),
            min_payment_tracker=Decimal("100"),
            total_repayments_tracker=Decimal("50"),
        )
        result = late_payment_fee_module.check_and_apply_late_payment_fee(
            state=state, account_type=ACCOUNT_TYPE
        )
        self.assertEqual(len(result), 1)
        self.assertIn("Late payment fee", result[0].instruction_details["description"])

    @pytest.mark.unit
    def test_no_fee_when_fully_paid(self):
        state = self._setup_state(
            fee_amount=Decimal("12"),
            min_payment_tracker=Decimal("100"),
            total_repayments_tracker=Decimal("100"),
        )
        result = late_payment_fee_module.check_and_apply_late_payment_fee(
            state=state, account_type=ACCOUNT_TYPE
        )
        self.assertEqual(len(result), 0)

    @pytest.mark.unit
    def test_no_fee_when_overpaid(self):
        state = self._setup_state(
            fee_amount=Decimal("12"),
            min_payment_tracker=Decimal("100"),
            total_repayments_tracker=Decimal("200"),
        )
        result = late_payment_fee_module.check_and_apply_late_payment_fee(
            state=state, account_type=ACCOUNT_TYPE
        )
        self.assertEqual(len(result), 0)

    @pytest.mark.unit
    def test_no_fee_when_no_minimum_payment_due(self):
        state = self._setup_state(
            fee_amount=Decimal("12"),
            min_payment_tracker=Decimal("0"),
            total_repayments_tracker=Decimal("0"),
        )
        result = late_payment_fee_module.check_and_apply_late_payment_fee(
            state=state, account_type=ACCOUNT_TYPE
        )
        self.assertEqual(len(result), 0)

    @pytest.mark.unit
    def test_no_fee_when_fee_amount_is_zero(self):
        state = self._setup_state(
            fee_amount=Decimal("0"),
            min_payment_tracker=Decimal("100"),
            total_repayments_tracker=Decimal("50"),
        )
        result = late_payment_fee_module.check_and_apply_late_payment_fee(
            state=state, account_type=ACCOUNT_TYPE
        )
        self.assertEqual(len(result), 0)

    @pytest.mark.unit
    def test_fee_posted_to_fees_address(self):
        state = self._setup_state(
            fee_amount=Decimal("12"),
            min_payment_tracker=Decimal("100"),
            total_repayments_tracker=Decimal("50"),
        )
        result = late_payment_fee_module.check_and_apply_late_payment_fee(
            state=state, account_type=ACCOUNT_TYPE
        )
        self.assertEqual(len(result), 1)
        # Verify the posting debits FEES address
        postings = result[0].postings
        debit_posting = [p for p in postings if not p.credit][0]
        self.assertEqual(debit_posting.account_address, lending_addresses.FEES)

    @pytest.mark.unit
    def test_no_fee_when_disabled(self):
        state = self._setup_state(
            fee_amount=Decimal("12"),
            fee_enabled="False",
            min_payment_tracker=Decimal("100"),
            total_repayments_tracker=Decimal("50"),
        )
        result = late_payment_fee_module.check_and_apply_late_payment_fee(
            state=state, account_type=ACCOUNT_TYPE
        )
        self.assertEqual(len(result), 0)

    @pytest.mark.unit
    def test_no_fee_when_repayments_exactly_match_minimum(self):
        """Boundary: exact minimum payment should not trigger late fee."""
        state = self._setup_state(
            fee_amount=Decimal("12"),
            min_payment_tracker=Decimal("100"),
            total_repayments_tracker=Decimal("100"),
        )
        result = late_payment_fee_module.check_and_apply_late_payment_fee(
            state=state, account_type=ACCOUNT_TYPE
        )
        self.assertEqual(len(result), 0)


class LatePaymentFeeScheduleTest(FeatureTest):
    @patch.object(late_payment_fee_module.state_utils, "append_to_state")
    @pytest.mark.unit
    def test_get_scheduled_events(self, mock_append_to_state: MagicMock):
        check_time = "00:00:02"
        day = "26"
        mock_state = initialise_mock_state(
            effective_datetime=DEFAULT_DATETIME,
            parameters={
                late_payment_fee_module.LATE_PAYMENT_CHECK_DAY_PARAM.id: day,
                late_payment_fee_module.LATE_PAYMENT_CHECK_TIME_PARAM.id: check_time,
            },
        )
        mock_append_to_state.return_value = mock_state
        mock_state.vault.events_timezone = UTC_ZONE

        result = late_payment_fee_module.get_scheduled_events(state=mock_state)

        expected = {
            late_payment_fee_module.CHECK_LATE_PAYMENT_EVENT: ScheduledEvent(
                start_datetime=DEFAULT_DATETIME,
                expression=ScheduleExpression(
                    day=26,
                    hour=0,
                    minute=0,
                    second=2,
                ),
            )
        }
        self.assertEqual(result, expected)

    @patch.object(late_payment_fee_module.state_utils, "check_parameters_exist")
    @patch.object(late_payment_fee_module.state_utils, "append_to_state")
    @pytest.mark.unit
    def test_get_scheduled_events_raises_on_missing_params(
        self, mock_append_to_state: MagicMock, mock_check_params: MagicMock
    ):
        mock_state = initialise_mock_state()
        mock_append_to_state.return_value = mock_state
        mock_check_params.return_value = sentinel.rejection

        with self.assertRaises(AssertionError) as ex:
            late_payment_fee_module.get_scheduled_events(state=mock_state)

        self.assertEqual(ex.exception.args[0], sentinel.rejection)
