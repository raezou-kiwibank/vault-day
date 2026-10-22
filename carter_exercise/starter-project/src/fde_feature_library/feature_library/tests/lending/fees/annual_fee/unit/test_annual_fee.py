# standard libs
from datetime import datetime
from decimal import Decimal
from unittest.mock import MagicMock, patch, sentinel
from zoneinfo import ZoneInfo

import pytest
from dateutil.relativedelta import relativedelta

import feature_library.common.denomination as denomination_module

# features
import feature_library.common.fetchers as fetchers
import feature_library.lending.addresses as apex_addresses
import feature_library.lending.fees.annual_fee as annual_fee_module

# contracts api
from contracts_api import (
    DEFAULT_ADDRESS,
    DEFAULT_ASSET,
    Balance,
    BalanceDefaultDict,
    BalancesObservation,
    CustomInstruction,
    ParametersObservation,
    Phase,
    Posting,
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
ANNUAL_FEE_INCOME_ACCOUNT = "ANNUAL_FEE_INCOME"
ACCOUNT_TYPE = "credit_card"

FETCHER_ID = "fetcher_id"
PARAMETER_NAME = "parameter_name"


class AnnualFeeTest(FeatureTest):
    def setup_mock_data(
        self,
        effective_datetime: datetime = DEFAULT_DATETIME,
        annual_fee_amount: Decimal | None = Decimal("1000"),
        annual_fee_income_account: str | None = "ANNUAL_FEE_INCOME",
        annual_fee_enabled: str | None = "True",
        denomination: str | None = DEFAULT_DENOMINATION,
    ):
        self.effective_datetime = effective_datetime

        denom_params = {}
        if denomination is not None:
            denom_params[denomination_module.DENOMINATION_PARAM.id] = denomination

        annual_fee_params = {
            annual_fee_module.ANNUAL_FEE_DAY_PARAM.id: "1",
            annual_fee_module.ANNUAL_FEE_MONTH_PARAM.id: "1",
            annual_fee_module.ANNUAL_FEE_TIME_PARAM.id: "00:00:01",
        }
        if annual_fee_amount is not None:
            annual_fee_params[annual_fee_module.ANNUAL_FEE_AMOUNT_PARAM.id] = annual_fee_amount
        if annual_fee_income_account is not None:
            annual_fee_params[annual_fee_module.ANNUAL_FEE_INCOME_ACCOUNT_PARAM.id] = (
                annual_fee_income_account
            )
        if annual_fee_enabled is not None:
            annual_fee_params[annual_fee_module.ANNUAL_FEE_ENABLED_PARAM.id] = annual_fee_enabled

        params_obs = {
            denomination_module.DENOMINATION_ET_POF.fetcher_id: ParametersObservation(
                parameters=denom_params, value_datetime=effective_datetime
            ),
            annual_fee_module.ANNUAL_FEE_POF.fetcher_id: ParametersObservation(
                parameters=annual_fee_params,
                value_datetime=effective_datetime,
            ),
        }

        default_bals = BalanceDefaultDict(lambda: Balance(), {})
        self.mock_vault = self.create_mock(
            account_id=ACCOUNT_ID,
            activation_datetime=effective_datetime,
            balances_observation_fetchers_mapping={
                fetchers.EFFECTIVE_DATE_BOF.fetcher_id: BalancesObservation(
                    balances=default_bals,
                    value_datetime=effective_datetime,
                    at_datetime=effective_datetime,
                ),
            },
            creation_date=effective_datetime,
            parameters_observation_fetchers_mapping=params_obs,
        )
        self.state = MagicMock(
            vault=self.mock_vault,
            effective_datetime=effective_datetime,
            parameters=annual_fee_params | denom_params,
            balances=default_bals,
        )

    @pytest.mark.unit
    def test_apply_fees_raises_assertion_error_if_parameter_missing(self):
        params_to_test = [
            ("annual_fee_amount", {"annual_fee_amount": None}),
            ("annual_fee_income_account", {"annual_fee_income_account": None}),
            ("annual_fee_enabled", {"annual_fee_enabled": None}),
            ("denomination", {"denomination": None}),
        ]

        for param_name, setup_kwargs in params_to_test:
            with self.subTest(missing_param=param_name):
                self.setup_mock_data(**setup_kwargs)  # type: ignore
                with self.assertRaises(AssertionError) as cm:
                    annual_fee_module.apply_fees(
                        state=self.state,
                        account_type=ACCOUNT_TYPE,
                    )
                self.assertIn("parameters are missing: ", str(cm.exception))

    @pytest.mark.unit
    def test_annual_fee_applied(self):
        annual_fee_amount = Decimal("1000")
        self.setup_mock_data(
            annual_fee_amount=annual_fee_amount,
            annual_fee_income_account=ANNUAL_FEE_INCOME_ACCOUNT,
            annual_fee_enabled="True",
        )
        result = annual_fee_module.apply_fees(
            state=self.state,
            account_type=ACCOUNT_TYPE,
        )
        expected = [
            CustomInstruction(
                postings=[
                    Posting(
                        credit=False,
                        amount=annual_fee_amount,
                        denomination=DENOMINATION,
                        account_id=ACCOUNT_ID,
                        account_address=apex_addresses.FEES,
                        asset=DEFAULT_ASSET,
                        phase=Phase.COMMITTED,
                    ),
                    Posting(
                        credit=True,
                        amount=annual_fee_amount,
                        denomination=DENOMINATION,
                        account_id=ANNUAL_FEE_INCOME_ACCOUNT,
                        account_address=DEFAULT_ADDRESS,
                        asset=DEFAULT_ASSET,
                        phase=Phase.COMMITTED,
                    ),
                ],
                instruction_details={
                    "description": "Annual Fee Application",
                    "event": "APPLY_ANNUAL_FEE",
                    "gl_impacted": str(True),
                    "account_type": ACCOUNT_TYPE,
                },
                value_datetime=self.effective_datetime,
                override_all_restrictions=True,
            )
        ]
        self.assertListEqual(result, expected)

    @pytest.mark.unit
    def test_annual_fee_not_applied_when_disabled(self):
        self.setup_mock_data(
            annual_fee_amount=Decimal("1000"),
            annual_fee_income_account=ANNUAL_FEE_INCOME_ACCOUNT,
            annual_fee_enabled="False",
        )
        result = annual_fee_module.apply_fees(
            state=self.state,
            account_type=ACCOUNT_TYPE,
        )
        self.assertEqual(len(result), 0)

    @pytest.mark.unit
    def test_annual_fee_not_applied_when_fee_is_zero(self):
        self.setup_mock_data(
            annual_fee_amount=Decimal(0),
            annual_fee_income_account=ANNUAL_FEE_INCOME_ACCOUNT,
            annual_fee_enabled="True",
        )
        result = annual_fee_module.apply_fees(
            state=self.state,
            account_type=ACCOUNT_TYPE,
        )
        self.assertEqual(len(result), 0)


class AnnualFeeHelpersTest(FeatureTest):
    @pytest.mark.unit
    def test_get_parameters(self):
        mock_vault = self.create_mock(
            parameters_observation_fetchers_mapping={
                FETCHER_ID: ParametersObservation(
                    parameters={PARAMETER_NAME: "parameter_value"},
                    value_datetime=DEFAULT_DATETIME,
                )
            }
        )

        result = annual_fee_module.get_parameters(
            vault=mock_vault,
            param_fetcher_id=FETCHER_ID,
        )

        self.assertEqual(
            result,
            {PARAMETER_NAME: "parameter_value"},
        )

    @patch.object(annual_fee_module, "_append_to_state")
    @patch.object(annual_fee_module.state_utils, "append_to_state")
    @pytest.mark.unit
    def test_get_scheduled_events(
        self, mock_state_utils_append_to_state: MagicMock, mock_append_to_state: MagicMock
    ):
        application_time = "12:34:56"
        day = "17"
        month = "6"
        mock_state = initialise_mock_state(
            effective_datetime=DEFAULT_DATETIME,
            parameters={
                annual_fee_module.ANNUAL_FEE_TIME_PARAM.id: application_time,
                annual_fee_module.ANNUAL_FEE_DAY_PARAM.id: day,
                annual_fee_module.ANNUAL_FEE_MONTH_PARAM.id: month,
            },
        )
        mock_state_utils_append_to_state.return_value = mock_state
        mock_state.vault.events_timezone = UTC_ZONE

        result = annual_fee_module.get_scheduled_events(state=mock_state)

        expected_event = {
            annual_fee_module.APPLICATION_EVENT: ScheduledEvent(
                start_datetime=DEFAULT_DATETIME + relativedelta(months=1),
                expression=ScheduleExpression(
                    day=int(day),
                    month=int(month),
                    hour=12,
                    minute=34,
                    second=56,
                ),
            )
        }
        self.assertEqual(result, expected_event)

    @patch.object(annual_fee_module.state_utils, "check_parameters_exist")
    @patch.object(annual_fee_module.state_utils, "append_to_state")
    @pytest.mark.unit
    def test_get_scheduled_events_returns_rejection_if_parameter_missing(
        self, mock_state_utils_append_to_state: MagicMock, mock_check_parameters_exist: MagicMock
    ):
        mock_state = initialise_mock_state()
        mock_state_utils_append_to_state.return_value = mock_state
        mock_check_parameters_exist.return_value = sentinel.rejection

        with self.assertRaises(AssertionError) as ex:
            annual_fee_module.get_scheduled_events(state=mock_state)

        self.assertEqual(ex.exception.args[0], sentinel.rejection)
        mock_check_parameters_exist.assert_called_once_with(
            state=mock_state,
            param_ids={
                annual_fee_module.ANNUAL_FEE_DAY_PARAM.id,
                annual_fee_module.ANNUAL_FEE_MONTH_PARAM.id,
                annual_fee_module.ANNUAL_FEE_TIME_PARAM.id,
            },
        )
