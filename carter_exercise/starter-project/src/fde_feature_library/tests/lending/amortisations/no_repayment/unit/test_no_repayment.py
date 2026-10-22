# standard libs
from datetime import datetime
from decimal import Decimal
from unittest.mock import MagicMock, patch, sentinel
from zoneinfo import ZoneInfo

import pytest
from dateutil.relativedelta import relativedelta

import feature_library.common.denomination as denomination_module
import feature_library.lending.addresses as lending_addresses

# feature library
import feature_library.lending.amortisations.amortisation_methods.no_repayment as no_repayment
import feature_library.lending.term.term as term_helpers

# contracts api
from contracts_api import Posting, Tside

# inception sdk
from inception_sdk.test_framework.contracts.unit.common import DEFAULT_DATETIME, FeatureTest

from tests.common.test_denomination import DEFAULT_DENOMINATION
from tests.utils import initialise_mock_state


class NoRepaymentCommon(FeatureTest):
    default_denomination = DEFAULT_DENOMINATION
    tside = Tside.ASSET


class TermDetailsTest(NoRepaymentCommon):
    @pytest.mark.unit
    def test_term_details(self):
        mock_vault = self.create_mock()
        state = initialise_mock_state(
            vault=mock_vault,
            effective_datetime=DEFAULT_DATETIME + relativedelta(months=4),
            parameters={
                term_helpers.TERM_PARAM_ID: "10",
            },
        )
        result = no_repayment.term_details(
            state=state,
        )

        self.assertEqual(result, (4, 6))

    @pytest.mark.unit
    def test_historical_effective_datetime(self):
        mock_vault = self.create_mock()
        state = initialise_mock_state(
            vault=mock_vault,
            effective_datetime=DEFAULT_DATETIME - relativedelta(months=4),
            parameters={
                term_helpers.TERM_PARAM_ID: "10",
            },
        )
        result = no_repayment.term_details(
            state=state,
        )

        self.assertEqual(result, (0, 10))

    @pytest.mark.unit
    def test_effective_datetime_after_set_term(self):
        mock_vault = self.create_mock()
        state = initialise_mock_state(
            vault=mock_vault,
            effective_datetime=DEFAULT_DATETIME + relativedelta(years=1),
            parameters={
                term_helpers.TERM_PARAM_ID: "10",
            },
        )
        result = no_repayment.term_details(
            state=state,
        )

        self.assertEqual(result, (10, 0))


class CalculateEmi(FeatureTest):
    @pytest.mark.unit
    def test_calculate_eia(self):
        result = no_repayment.calculate_eia()

        self.assertEqual(result, Decimal("0"))


class IsNoRepaymentLoanTest(FeatureTest):
    @pytest.mark.unit
    def test_is_no_repayment_loan_true(self):
        self.assertEqual(no_repayment.is_no_repayment_loan("NO_REPAYMENT"), True)

    @pytest.mark.unit
    def test_is_no_repayment_lower_case_true(self):
        self.assertEqual(no_repayment.is_no_repayment_loan("no_repayment"), True)

    @pytest.mark.unit
    def test_is_no_repayment_loan_false(self):
        self.assertEqual(no_repayment.is_no_repayment_loan("other"), False)


class GetBalloonPaymentDatetimeTest(FeatureTest):
    test_date = datetime(2019, 1, 1, tzinfo=ZoneInfo("UTC"))

    @pytest.mark.unit
    def test_zero_offset_days(self):
        mock_vault = self.create_mock(creation_date=self.test_date)
        state = initialise_mock_state(
            vault=mock_vault,
            parameters={
                term_helpers.TERM_PARAM_ID: "12",
                "balloon_payment_days_delta": "0",
            },
        )
        expected_result = datetime(2020, 1, 1, tzinfo=ZoneInfo("UTC"))

        result = no_repayment.get_balloon_payment_datetime(state=state)

        self.assertEqual(result, expected_result)

    @pytest.mark.unit
    def test_non_zero_offset_days(self):
        mock_vault = self.create_mock(creation_date=self.test_date)
        state = initialise_mock_state(
            vault=mock_vault,
            parameters={
                term_helpers.TERM_PARAM_ID: "12",
                "balloon_payment_days_delta": "10",
            },
        )
        expected_result = datetime(2020, 1, 11, tzinfo=ZoneInfo("UTC"))

        result = no_repayment.get_balloon_payment_datetime(state=state)

        self.assertEqual(result, expected_result)


@patch.object(no_repayment.balance_utils, "balance_at_coordinates")
@patch.object(no_repayment.eia_module, "update_eia")
@patch.object(no_repayment, "calculate_eia")
class AmortiseTest(NoRepaymentCommon):
    @pytest.mark.unit
    def test_amortise_returns_instructions_when_eia_updated(
        self,
        mock_calculate_eia: MagicMock,
        mock_update_eia: MagicMock,
        mock_balance_at_coordinates: MagicMock,
    ):
        mock_calculate_eia.return_value = Decimal("100")
        mock_posting = MagicMock(spec=Posting)
        mock_update_eia.return_value = [mock_posting]
        mock_balance_at_coordinates.return_value = Decimal("50")

        mock_vault = self.create_mock(account_id=sentinel.account_id)
        state = initialise_mock_state(
            vault=mock_vault,
            parameters={denomination_module.DENOMINATION_PARAM_ID: DEFAULT_DENOMINATION},
            balances=sentinel.balances,
        )

        result = no_repayment.amortise(
            state=state,
        )

        mock_calculate_eia.assert_called_once_with()
        mock_balance_at_coordinates.assert_called_once_with(
            balances=sentinel.balances,
            address=lending_addresses.EIA,
            denomination=DEFAULT_DENOMINATION,
        )
        mock_update_eia.assert_called_once_with(
            account_id=sentinel.account_id,
            denomination=DEFAULT_DENOMINATION,
            current_eia=Decimal("50"),
            updated_eia=Decimal("100"),
        )
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].postings, [mock_posting])
        self.assertEqual(result[0].instruction_details["event"], "ACCOUNT_ACTIVATION")

    @pytest.mark.unit
    def test_amortise_returns_empty_list_when_no_eia_update(
        self,
        mock_calculate_eia: MagicMock,
        mock_update_eia: MagicMock,
        mock_balance_at_coordinates: MagicMock,
    ):
        mock_calculate_eia.return_value = Decimal("50")
        mock_update_eia.return_value = []
        mock_balance_at_coordinates.return_value = Decimal("50")

        mock_vault = self.create_mock(account_id=sentinel.account_id)
        state = initialise_mock_state(
            vault=mock_vault,
            parameters={denomination_module.DENOMINATION_PARAM_ID: DEFAULT_DENOMINATION},
            balances=sentinel.balances,
        )

        result = no_repayment.amortise(
            state=state,
        )

        self.assertEqual(result, [])
