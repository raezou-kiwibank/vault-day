# standard libs
from datetime import datetime
from decimal import Decimal
from unittest.mock import MagicMock, patch, sentinel
from zoneinfo import ZoneInfo

import pytest

# features
import feature_library.lending.addresses as lending_addresses
import feature_library.lending.interest.interest_accrual as interest_accrual

# contracts api
from contracts_api import (
    DEFAULT_ASSET,
    Balance,
    BalanceCoordinate,
    BalanceDefaultDict,
    BalancesObservation,
    ParametersObservation,
    Phase,
    ScheduleExpression,
)

# inception sdk
from inception_sdk.test_framework.contracts.unit.common import FeatureTest

from tests.common.test_denomination import DEFAULT_DENOMINATION
from tests.utils import initialise_mock_state

UTC = ZoneInfo("UTC")


class InterestAccrualTest(FeatureTest):
    def setUp(self):
        self.mock_get_annual_interest_rate = MagicMock(return_value=Decimal("0.10"))
        self.addCleanup(patch.stopall)

    def setup_mock_data(self, parameters=None, balances=None, effective_datetime=None):
        params = {
            interest_accrual.ACCRUED_INTEREST_RECEIVABLE_ACCOUNT_PARAM_ID: (
                sentinel.receivable_account
            ),
            interest_accrual.DAYS_IN_YEAR_PARAM_ID: "actual",
            interest_accrual.ACCRUAL_PRECISION_PARAM_ID: 5,
            interest_accrual.ACCRUAL_TIME_PARAM_ID: "00:00:01",
            interest_accrual.DEFAULT_FETCHERS_CONFIG.denomination_param_id: DEFAULT_DENOMINATION,
        }
        if parameters:
            params.update(parameters)

        effective_dt = effective_datetime or datetime(2020, 1, 1, tzinfo=UTC)

        balances = balances or BalanceDefaultDict()

        self.mock_vault = self.create_mock(
            account_id=sentinel.account_id,
            parameters_observation_fetchers_mapping={
                interest_accrual.PARAM_ET_POF_ID: ParametersObservation(
                    parameters=params, value_datetime=effective_dt
                )
            },
            balances_observation_fetchers_mapping={
                interest_accrual.DEFAULT_FETCHERS_CONFIG.balance_fetcher_id: BalancesObservation(
                    balances=balances, value_datetime=effective_dt
                )
            },
        )

        return initialise_mock_state(
            vault=self.mock_vault,
            effective_datetime=effective_dt,
            parameters=params,
            balances=balances,
        )

    @pytest.mark.unit
    def test_get_scheduled_events(self):
        state = self.setup_mock_data()
        events = interest_accrual.get_scheduled_events(state)

        self.assertIn(interest_accrual.ACCRUAL_EVENT, events)
        event = events[interest_accrual.ACCRUAL_EVENT]
        self.assertEqual(event.expression, ScheduleExpression(hour=0, minute=0, second=1))
        # 2020-01-01 00:00:00 UTC
        self.assertEqual(event.start_datetime, datetime(2020, 1, 1, tzinfo=UTC))

    @pytest.mark.unit
    def test_get_scheduled_events_with_custom_fetchers_config(self):
        state = self.setup_mock_data()

        custom_fetchers_config = interest_accrual.GetScheduledEventsFetchersConfig(
            param_fetcher_id=interest_accrual.PARAM_ET_POF_ID,
            interest_accrual_time_param_id=interest_accrual.ACCRUAL_TIME_PARAM_ID,
        )

        events = interest_accrual.get_scheduled_events(
            state=state, fetchers_config=custom_fetchers_config
        )

        self.assertIn(interest_accrual.ACCRUAL_EVENT, events)
        event = events[interest_accrual.ACCRUAL_EVENT]
        self.assertEqual(event.expression, ScheduleExpression(hour=0, minute=0, second=1))
        self.assertEqual(event.start_datetime, datetime(2020, 1, 1, tzinfo=UTC))

    @patch.object(interest_accrual.accrual_utils, "create_receivable_accrual_custom_instruction")
    @pytest.mark.unit
    def test_schedule_logic_accrues_interest(self, mock_accrual_ci: MagicMock):
        mock_accrual_ci.return_value = [sentinel.custom_instruction]

        balances = BalanceDefaultDict(
            mapping={
                BalanceCoordinate(
                    lending_addresses.PRINCIPAL,
                    DEFAULT_ASSET,
                    DEFAULT_DENOMINATION,
                    Phase.COMMITTED,
                ): Balance(debit=Decimal("1000"))
            }
        )

        state = self.setup_mock_data(balances=balances)

        result = interest_accrual.schedule_logic(
            state=state,
            get_annual_interest_rate=self.mock_get_annual_interest_rate,
            account_type=sentinel.account_type,
        )

        self.assertEqual(result, [sentinel.custom_instruction])

        # 1000 * 0.00027322 = 0.27322
        expected_amount = Decimal("0.27322")

        mock_accrual_ci.assert_called_once()
        kwargs = mock_accrual_ci.call_args.kwargs
        self.assertEqual(kwargs["amount"], expected_amount)
        self.assertEqual(kwargs["customer_account"], sentinel.account_id)
        self.assertEqual(kwargs["internal_account"], sentinel.receivable_account)
        self.assertEqual(kwargs["customer_address"], lending_addresses.ACCRUED_INTEREST_RECEIVABLE)

    @patch.object(interest_accrual.accrual_utils, "create_receivable_accrual_custom_instruction")
    @pytest.mark.unit
    def test_schedule_logic_no_accrual_when_amount_is_zero(self, mock_accrual_ci: MagicMock):
        mock_accrual_ci.return_value = []
        balances = BalanceDefaultDict(
            mapping={
                BalanceCoordinate(
                    lending_addresses.PRINCIPAL,
                    DEFAULT_ASSET,
                    DEFAULT_DENOMINATION,
                    Phase.COMMITTED,
                ): Balance(debit=Decimal("0"))
            }
        )

        state = self.setup_mock_data(balances=balances)

        result = interest_accrual.schedule_logic(
            state=state,
            get_annual_interest_rate=self.mock_get_annual_interest_rate,
            account_type=sentinel.account_type,
        )

        self.assertEqual(result, [])
        mock_accrual_ci.assert_called_once()
        self.assertEqual(mock_accrual_ci.call_args[1]["amount"], Decimal("0"))

    @patch.object(interest_accrual.accrual_utils, "create_receivable_accrual_custom_instruction")
    @pytest.mark.unit
    def test_schedule_logic_accrues_interest_with_multiple_principal_addresses(
        self, mock_accrual_ci: MagicMock
    ):
        mock_accrual_ci.return_value = [sentinel.custom_instruction]

        balances = BalanceDefaultDict(
            mapping={
                BalanceCoordinate(
                    lending_addresses.PRINCIPAL,
                    DEFAULT_ASSET,
                    DEFAULT_DENOMINATION,
                    Phase.COMMITTED,
                ): Balance(debit=Decimal("1000")),
                BalanceCoordinate(
                    "OTHER_PRINCIPAL", DEFAULT_ASSET, DEFAULT_DENOMINATION, Phase.COMMITTED
                ): Balance(debit=Decimal("500")),
            }
        )

        state = self.setup_mock_data(balances=balances)

        result = interest_accrual.schedule_logic(
            state=state,
            get_annual_interest_rate=self.mock_get_annual_interest_rate,
            account_type=sentinel.account_type,
            principal_addresses=[lending_addresses.PRINCIPAL, "OTHER_PRINCIPAL"],
        )

        # (1000 + 500) * 0.00027322 = 0.40983
        expected_amount = Decimal("0.40984")

        self.assertEqual(result, [sentinel.custom_instruction])
        kwargs = mock_accrual_ci.call_args.kwargs
        self.assertEqual(kwargs["amount"], expected_amount)

    @patch.object(interest_accrual.accrual_utils, "create_receivable_accrual_custom_instruction")
    @pytest.mark.unit
    def test_schedule_logic_uses_custom_accrual_address(self, mock_accrual_ci: MagicMock):
        mock_accrual_ci.return_value = [sentinel.custom_instruction]

        balances = BalanceDefaultDict(
            mapping={
                BalanceCoordinate(
                    lending_addresses.PRINCIPAL,
                    DEFAULT_ASSET,
                    DEFAULT_DENOMINATION,
                    Phase.COMMITTED,
                ): Balance(debit=Decimal("1000"))
            }
        )

        state = self.setup_mock_data(balances=balances)

        result = interest_accrual.schedule_logic(
            state=state,
            get_annual_interest_rate=self.mock_get_annual_interest_rate,
            account_type=sentinel.account_type,
            customer_accrual_address="CUSTOM_ACCRUAL_ADDRESS",
        )

        self.assertEqual(result, [sentinel.custom_instruction])
        kwargs = mock_accrual_ci.call_args.kwargs
        self.assertEqual(kwargs["customer_address"], "CUSTOM_ACCRUAL_ADDRESS")
