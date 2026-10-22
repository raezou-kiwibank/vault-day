# standard libs
from datetime import datetime
from decimal import Decimal
from json import dumps
from unittest.mock import MagicMock, patch
from zoneinfo import ZoneInfo

import pytest

import feature_library.common.denomination as denomination_module
from feature_library.deposit.fees.withdrawal import payment_type_monthly_limit_fee

from contracts_api import (
    CustomInstruction,
    ParametersObservation,
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


class PaymentTypeMonthlyLimitFeeTest(FeatureTest):
    def setup_mock_data(
        self,
        account_creation_datetime: datetime = DEFAULT_DATETIME,
        effective_datetime: datetime = DEFAULT_DATETIME,
        monthly_limit_param: str | None = dumps({"ATM": {"fee": "0.15", "limit": "2"}}),
        income_account_param: str | None = INCOME_ACCOUNT,
        denomination: str | None = DENOMINATION,
        client_transactions_mapping: dict | None = None,
    ):
        self.effective_datetime = effective_datetime

        denom_params = {}
        if denomination is not None:
            denom_params[denomination_module.DENOMINATION_PARAM.id] = denomination

        fee_params = {}
        if monthly_limit_param is not None:
            fee_params[
                payment_type_monthly_limit_fee.MAXIMUM_MONTHLY_PAYMENT_TYPE_WITHDRAWAL_LIMIT_PARAM.id
            ] = monthly_limit_param
        if income_account_param is not None:
            fee_params[payment_type_monthly_limit_fee.PAYMENT_TYPE_FEE_INCOME_ACCOUNT_PARAM.id] = (
                income_account_param
            )

        params_obs: dict[str, ParametersObservation] = {
            denomination_module.DENOMINATION_ET_POF.fetcher_id: ParametersObservation(
                parameters=denom_params, value_datetime=effective_datetime
            ),
            payment_type_monthly_limit_fee.MONTHLY_LIMIT_FEES_POF_ID: ParametersObservation(
                parameters=fee_params,
                value_datetime=effective_datetime,
            ),
        }

        self.mock_vault = self.create_mock(
            account_id=ACCOUNT_ID,
            activation_datetime=account_creation_datetime,
            creation_date=account_creation_datetime,
            parameters_observation_fetchers_mapping=params_obs,
            client_transactions_mapping=client_transactions_mapping or {},
        )
        self.state = MagicMock(
            vault=self.mock_vault,
            effective_datetime=effective_datetime,
            parameters=fee_params | denom_params,
        )

    @pytest.mark.unit
    def test_apply_fees_raises_assertion_error_if_parameter_missing(self):
        params_to_test = [
            ("monthly_limit_param", {"monthly_limit_param": None}),
            ("income_account_param", {"income_account_param": None}),
            ("denomination", {"denomination": None}),
        ]

        for param_name, setup_kwargs in params_to_test:
            with self.subTest(missing_param=param_name):
                self.setup_mock_data(**setup_kwargs)  # type: ignore
                with self.assertRaises(AssertionError) as cm:
                    payment_type_monthly_limit_fee.apply_fees(
                        state=self.state,
                        updated_client_transactions={},
                        account_type=ACCOUNT_TYPE,
                        historic_client_transactions={},
                    )
                self.assertIn("parameters are missing: ", str(cm.exception))

    @patch.object(
        payment_type_monthly_limit_fee.client_transaction_utils,
        "extract_interval_and_proposed_debits",
    )
    @pytest.mark.unit
    def test_apply_fees_under_limit(self, mock_extract):
        self.setup_mock_data()

        # 1 historic, 1 proposed -> 2 total, limit 2 -> 0 fee
        mock_extract.return_value = (
            {"ATM": {"hist1": MagicMock()}},
            {"ATM": {"prop1": MagicMock()}},
        )

        result = payment_type_monthly_limit_fee.apply_fees(
            state=self.state,
            updated_client_transactions={"prop1": MagicMock()},
            account_type=ACCOUNT_TYPE,
            historic_client_transactions={"hist1": MagicMock()},
        )

        self.assertEqual(len(result), 0)

    @patch.object(
        payment_type_monthly_limit_fee.client_transaction_utils,
        "extract_interval_and_proposed_debits",
    )
    @pytest.mark.unit
    def test_apply_fees_at_limit(self, mock_extract):
        self.setup_mock_data()

        # 0 historic, 2 proposed -> 2 total, limit 2 -> 0 fee
        mock_extract.return_value = ({}, {"ATM": {"prop1": MagicMock(), "prop2": MagicMock()}})

        result = payment_type_monthly_limit_fee.apply_fees(
            state=self.state,
            updated_client_transactions={"prop1": MagicMock(), "prop2": MagicMock()},
            account_type=ACCOUNT_TYPE,
            historic_client_transactions={},
        )

        self.assertEqual(len(result), 0)

    @patch.object(
        payment_type_monthly_limit_fee.client_transaction_utils,
        "extract_interval_and_proposed_debits",
    )
    @pytest.mark.unit
    def test_apply_fees_over_limit_charges_fee(self, mock_extract):
        self.setup_mock_data(monthly_limit_param=dumps({"ATM": {"fee": "0.15", "limit": "2"}}))

        # 1 historic, 2 proposed -> 3 total, limit 2 -> 1 fee of 0.15
        mock_extract.return_value = (
            {"ATM": {"hist1": MagicMock()}},
            {"ATM": {"prop1": MagicMock(), "prop2": MagicMock()}},
        )

        result = payment_type_monthly_limit_fee.apply_fees(
            state=self.state,
            updated_client_transactions={"prop1": MagicMock(), "prop2": MagicMock()},
            account_type=ACCOUNT_TYPE,
            historic_client_transactions={"hist1": MagicMock()},
        )

        self.assertEqual(len(result), 1)
        instruction = result[0]
        self.assertIsInstance(instruction, CustomInstruction)

        postings = instruction.postings
        self.assertEqual(len(postings), 2)

        debit = next(p for p in postings if not p.credit)
        self.assertEqual(debit.amount, Decimal("0.15"))
        self.assertEqual(debit.account_id, ACCOUNT_ID)
        self.assertEqual(debit.denomination, DENOMINATION)

        credit = next(p for p in postings if p.credit)
        self.assertEqual(credit.amount, Decimal("0.15"))
        self.assertEqual(credit.account_id, INCOME_ACCOUNT)
        self.assertEqual(credit.denomination, DENOMINATION)

        self.assertEqual(
            instruction.instruction_details["event"], "APPLY_PAYMENT_TYPE_WITHDRAWAL_LIMIT_FEES"
        )
        self.assertIn("ATM 0.15 GBP", instruction.instruction_details["description"])

    @patch.object(
        payment_type_monthly_limit_fee.client_transaction_utils,
        "extract_interval_and_proposed_debits",
    )
    @pytest.mark.unit
    def test_apply_fees_multiple_types(self, mock_extract):
        self.setup_mock_data(
            monthly_limit_param=dumps(
                {
                    "ATM": {"fee": "0.15", "limit": "2"},
                    "POS": {"fee": "0.50", "limit": "5"},
                }
            )
        )

        # ATM: 2 historic, 2 proposed -> limit 2 -> 2 fees * 0.15 = 0.30
        # POS: 4 historic, 2 proposed -> limit 5 -> 1 fee * 0.50 = 0.50
        # Total fee: 0.80
        mock_extract.return_value = (
            {
                "ATM": {"h1": MagicMock(), "h2": MagicMock()},
                "POS": {"h1": MagicMock(), "h2": MagicMock(), "h3": MagicMock(), "h4": MagicMock()},
            },
            {
                "ATM": {"p1": MagicMock(), "p2": MagicMock()},
                "POS": {"p1": MagicMock(), "p2": MagicMock()},
            },
        )

        result = payment_type_monthly_limit_fee.apply_fees(
            state=self.state,
            updated_client_transactions={"p1": MagicMock(), "p2": MagicMock()},
            account_type=ACCOUNT_TYPE,
            historic_client_transactions={},
        )

        self.assertEqual(len(result), 1)
        instruction = result[0]
        postings = instruction.postings

        debit = next(p for p in postings if not p.credit)
        self.assertEqual(debit.amount, Decimal("0.80"))

        credit = next(p for p in postings if p.credit)
        self.assertEqual(credit.amount, Decimal("0.80"))

        desc = instruction.instruction_details["description"]
        self.assertIn("ATM 0.30 GBP", desc)
        self.assertIn("POS 0.50 GBP", desc)

    @patch.object(
        payment_type_monthly_limit_fee.client_transaction_utils,
        "extract_interval_and_proposed_debits",
    )
    @pytest.mark.unit
    def test_apply_fees_historic_transactions_none_fetches_from_vault(self, mock_extract):
        mock_historic_tx = {"hist1": MagicMock()}
        self.setup_mock_data(
            monthly_limit_param=dumps({"ATM": {"fee": "0.15", "limit": "2"}}),
            client_transactions_mapping={
                payment_type_monthly_limit_fee.MONTH_TO_EFFECTIVE_POSTIF_ID: mock_historic_tx
            },
        )

        mock_extract.return_value = ({}, {"ATM": {"prop1": MagicMock()}})

        payment_type_monthly_limit_fee.apply_fees(
            state=self.state,
            updated_client_transactions={"prop1": MagicMock()},
            account_type=ACCOUNT_TYPE,
            historic_client_transactions=None,  # Historic is None!
        )

        # verify extract_interval_and_proposed_debits was called with fetched transactions
        mock_extract.assert_called_once()
        _, kwargs = mock_extract.call_args
        self.assertEqual(kwargs["interval_transactions"], mock_historic_tx)
