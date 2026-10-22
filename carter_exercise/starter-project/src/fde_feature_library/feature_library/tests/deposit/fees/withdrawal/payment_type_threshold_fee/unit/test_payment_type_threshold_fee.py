# standard libs
from datetime import datetime
from decimal import Decimal
from json import dumps
from unittest.mock import MagicMock
from zoneinfo import ZoneInfo

import pytest

import feature_library.common.denomination as denomination_module
from feature_library.deposit.fees.withdrawal import payment_type_threshold_fee

from contracts_api import (
    ParametersObservation,
    Tside,
)

from inception_sdk.test_framework.contracts.unit.common import (
    ACCOUNT_ID,
    FeatureTest,
)

from tests.common.test_denomination import DEFAULT_DENOMINATION

UTC_ZONE = ZoneInfo("UTC")
DEFAULT_DATETIME = datetime(2026, 1, 1, tzinfo=UTC_ZONE)

DENOMINATION = DEFAULT_DENOMINATION
INCOME_ACCOUNT = "INCOME_ACCOUNT"
ACCOUNT_TYPE = "account_type"


class PaymentTypeThresholdFeeTest(FeatureTest):
    def setup_mock_data(
        self,
        account_creation_datetime: datetime = DEFAULT_DATETIME,
        effective_datetime: datetime = DEFAULT_DATETIME,
        threshold_fee_param: str | None = dumps({"ATM": {"fee": "0.15", "threshold": "5000"}}),
        income_account_param: str | None = INCOME_ACCOUNT,
        denomination: str | None = DEFAULT_DENOMINATION,
    ):
        self.effective_datetime = effective_datetime
        self.tside = Tside.LIABILITY

        denom_params = {}
        if denomination is not None:
            denom_params[denomination_module.DENOMINATION_PARAM.id] = denomination

        fee_params = {}
        if threshold_fee_param is not None:
            fee_params[payment_type_threshold_fee.PAYMENT_TYPE_THRESHOLD_FEE_PARAM.id] = (
                threshold_fee_param
            )
        if income_account_param is not None:
            fee_params[payment_type_threshold_fee.PAYMENT_TYPE_FEE_INCOME_ACCOUNT_PARAM.id] = (
                income_account_param
            )

        params_obs: dict[str, ParametersObservation] = {
            denomination_module.DENOMINATION_ET_POF.fetcher_id: ParametersObservation(
                parameters=denom_params, value_datetime=effective_datetime
            ),
            payment_type_threshold_fee.PAYMENT_TYPE_THRESHOLD_FEE_POF_ID: ParametersObservation(
                parameters=fee_params,
                value_datetime=effective_datetime,
            ),
        }

        self.mock_vault = self.create_mock(
            account_id=ACCOUNT_ID,
            activation_datetime=account_creation_datetime,
            creation_date=account_creation_datetime,
            parameters_observation_fetchers_mapping=params_obs,
        )
        self.state = MagicMock(
            vault=self.mock_vault,
            effective_datetime=effective_datetime,
            parameters=fee_params | denom_params,
        )

    @pytest.mark.unit
    def test_apply_fees_over_threshold(self):
        self.setup_mock_data()
        posting = self.outbound_hard_settlement(
            amount=Decimal("5000.01"),
            denomination=DENOMINATION,
            instruction_details={"PAYMENT_TYPE": "ATM"},
            tside=Tside.LIABILITY,
        )
        result = payment_type_threshold_fee.apply_fees(
            state=self.state,
            posting_instructions=[posting],
            account_type=ACCOUNT_TYPE,
        )

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].postings[0].amount, Decimal("0.15"))
        self.assertEqual(result[0].instruction_details["payment_type"], "ATM")

    @pytest.mark.unit
    def test_apply_fees_under_threshold(self):
        self.setup_mock_data()
        posting = self.outbound_hard_settlement(
            amount=Decimal("4999.99"),
            denomination=DENOMINATION,
            instruction_details={"PAYMENT_TYPE": "ATM"},
            tside=Tside.LIABILITY,
        )
        result = payment_type_threshold_fee.apply_fees(
            state=self.state,
            posting_instructions=[posting],
            account_type=ACCOUNT_TYPE,
        )

        self.assertEqual(len(result), 0)

    @pytest.mark.unit
    def test_apply_fees_unmatched_payment_type(self):
        self.setup_mock_data()
        posting = self.outbound_hard_settlement(
            amount=Decimal(6000),
            denomination=DENOMINATION,
            instruction_details={"PAYMENT_TYPE": "POS"},
            tside=Tside.LIABILITY,
        )
        result = payment_type_threshold_fee.apply_fees(
            state=self.state,
            posting_instructions=[posting],
            account_type=ACCOUNT_TYPE,
        )

        self.assertEqual(len(result), 0)
