# standard libs
from decimal import Decimal
from unittest.mock import MagicMock, patch, sentinel

import pytest

# features
import feature_library.lending.amortisations.eia as eia

# contracts api
# inception sdk
from inception_sdk.test_framework.contracts.unit.common import FeatureTest


class EIATest(FeatureTest):
    maxDiff = None


@patch.object(eia.posting_utils, "create_postings")
class UpdateEIATest(EIATest):
    @pytest.mark.unit
    def test_update_eia_zero_delta(self, mock_create_postings: MagicMock):
        mock_create_postings.return_value = []
        self.assertListEqual(
            eia.update_eia(
                account_id=sentinel.account_id,
                denomination=sentinel.denomination,
                current_eia=Decimal("1"),
                updated_eia=Decimal("1"),
            ),
            [],
        )
        mock_create_postings.assert_called_once_with(
            amount=Decimal("0"),
            debit_account=sentinel.account_id,
            debit_address=eia.common_addresses.INTERNAL_CONTRA,
            credit_account=sentinel.account_id,
            credit_address=eia.lending_addresses.EIA,
            denomination=sentinel.denomination,
        )

    @pytest.mark.unit
    def test_update_eia_negative_delta(self, mock_create_postings: MagicMock):
        mock_create_postings.return_value = [sentinel.postings]
        self.assertListEqual(
            eia.update_eia(
                account_id=sentinel.account_id,
                denomination=sentinel.denomination,
                current_eia=Decimal("1"),
                updated_eia=Decimal("2"),
            ),
            [sentinel.postings],
        )
        mock_create_postings.assert_called_once_with(
            amount=Decimal("-1"),
            debit_account=sentinel.account_id,
            debit_address=eia.common_addresses.INTERNAL_CONTRA,
            credit_account=sentinel.account_id,
            credit_address=eia.lending_addresses.EIA,
            denomination=sentinel.denomination,
        )

    @pytest.mark.unit
    def test_update_eia_positive_delta(self, mock_create_postings: MagicMock):
        mock_create_postings.return_value = [sentinel.postings]
        self.assertListEqual(
            eia.update_eia(
                account_id=sentinel.account_id,
                denomination=sentinel.denomination,
                current_eia=Decimal("2"),
                updated_eia=Decimal("1"),
            ),
            [sentinel.postings],
        )
        mock_create_postings.assert_called_once_with(
            amount=Decimal("1"),
            debit_account=sentinel.account_id,
            debit_address=eia.common_addresses.INTERNAL_CONTRA,
            credit_account=sentinel.account_id,
            credit_address=eia.lending_addresses.EIA,
            denomination=sentinel.denomination,
        )


@patch.object(eia.utils, "round_decimal")
@patch.object(eia.balance_utils, "balance_at_coordinates")
class GetExpectedEIATest(EIATest):
    @pytest.mark.unit
    def test_get_expected_eia_default_decimal_places(
        self, mock_balance_at_coordinates: MagicMock, mock_round_decimal: MagicMock
    ):
        mock_balance_at_coordinates.return_value = sentinel.eia
        mock_round_decimal.return_value = sentinel.rounded_eia
        mock_state = MagicMock(
            balances=sentinel.balances,
            parameters={
                eia.DEFAULT_EXPECTED_EIA_FETCHERS_CONFIG.denomination_param_id: (
                    sentinel.denomination
                ),
                eia.DEFAULT_EXPECTED_EIA_FETCHERS_CONFIG.application_precision_param_id: 2,
            },
        )
        result = eia.get_expected_eia(state=mock_state)
        self.assertEqual(result, sentinel.rounded_eia)
        mock_balance_at_coordinates.assert_called_once_with(
            balances=sentinel.balances,
            address=eia.lending_addresses.EIA,
            denomination=sentinel.denomination,
        )
        mock_round_decimal.assert_called_once_with(
            amount=sentinel.eia,
            decimal_places=2,
        )

    @pytest.mark.unit
    def test_get_expected_eia_decimal_places_provided(
        self, mock_balance_at_coordinates: MagicMock, mock_round_decimal: MagicMock
    ):
        mock_balance_at_coordinates.return_value = sentinel.eia
        mock_round_decimal.return_value = sentinel.rounded_eia
        mock_state = MagicMock(
            balances=sentinel.balances,
            parameters={
                eia.DEFAULT_EXPECTED_EIA_FETCHERS_CONFIG.denomination_param_id: (
                    sentinel.denomination
                ),
                eia.DEFAULT_EXPECTED_EIA_FETCHERS_CONFIG.application_precision_param_id: 5,
            },
        )
        result = eia.get_expected_eia(state=mock_state)
        self.assertEqual(result, sentinel.rounded_eia)
        mock_balance_at_coordinates.assert_called_once_with(
            balances=sentinel.balances,
            address=eia.lending_addresses.EIA,
            denomination=sentinel.denomination,
        )
        mock_round_decimal.assert_called_once_with(
            amount=sentinel.eia,
            decimal_places=5,
        )

    @pytest.mark.unit
    def test_get_expected_eia_no_rounding(
        self, mock_balance_at_coordinates: MagicMock, mock_round_decimal: MagicMock
    ):
        mock_balance_at_coordinates.return_value = sentinel.eia
        mock_round_decimal.return_value = sentinel.eia
        mock_state = MagicMock(
            balances=sentinel.balances,
            parameters={
                eia.DEFAULT_EXPECTED_EIA_FETCHERS_CONFIG.denomination_param_id: sentinel.denomination,
                eia.DEFAULT_EXPECTED_EIA_FETCHERS_CONFIG.application_precision_param_id: 5,  # or whatever default is tested
            },
        )
        result = eia.get_expected_eia(state=mock_state)
        self.assertEqual(result, sentinel.eia)
        mock_balance_at_coordinates.assert_called_once_with(
            balances=sentinel.balances,
            address=eia.lending_addresses.EIA,
            denomination=sentinel.denomination,
        )
        mock_round_decimal.assert_called_once_with(amount=sentinel.eia, decimal_places=5)
