# standard libs
from datetime import datetime
from decimal import Decimal
from unittest.mock import MagicMock
from zoneinfo import ZoneInfo

import pytest

# third party
from parameterized import parameterized

# features
from feature_library.common import balance_utils

# contracts api
from contracts_api import (
    DEFAULT_ADDRESS,
    DEFAULT_ASSET,
    Balance,
    BalanceCoordinate,
    BalanceDefaultDict,
    BalancesObservation,
    Phase,
    Rejection,
    RejectionReason,
)

# inception sdk
from inception_sdk.test_framework.contracts.unit.common import DEFAULT_DENOMINATION, FeatureTest

FETCHER_ID = "fetcher_id"
DEFAULT_DATETIME = datetime(2025, 1, 1, tzinfo=ZoneInfo("UTC"))

DEFAULT_COORDINATE = BalanceCoordinate(
    account_address=DEFAULT_ADDRESS,
    asset=DEFAULT_ASSET,
    denomination=DEFAULT_DENOMINATION,
    phase=Phase.COMMITTED,
)
PENDING_OUT_DEFAULT_COORD = BalanceCoordinate(
    DEFAULT_ADDRESS, DEFAULT_ASSET, DEFAULT_DENOMINATION, Phase.PENDING_OUT
)
PENDING_IN_DEFAULT_COORD = BalanceCoordinate(
    DEFAULT_ADDRESS, DEFAULT_ASSET, DEFAULT_DENOMINATION, Phase.PENDING_IN
)


class BalanceUtilsTest(FeatureTest):
    @parameterized.expand(
        [
            (
                BalanceDefaultDict(mapping={DEFAULT_COORDINATE: Balance(net=Decimal(5))}),
                DEFAULT_ADDRESS,
                DEFAULT_DENOMINATION,
                DEFAULT_ASSET,
                Phase.COMMITTED,
                Decimal(5),
            ),
            (
                BalanceDefaultDict(mapping={DEFAULT_COORDINATE: Balance(net=Decimal(5))}),
                "OTHER_ADDRESS",
                DEFAULT_DENOMINATION,
                DEFAULT_ASSET,
                Phase.COMMITTED,
                Decimal("0"),
            ),
            (
                BalanceDefaultDict(mapping={DEFAULT_COORDINATE: Balance(net=Decimal(5))}),
                DEFAULT_ADDRESS,
                "EUR",
                DEFAULT_ASSET,
                Phase.COMMITTED,
                Decimal("0"),
            ),
            (
                BalanceDefaultDict(mapping={DEFAULT_COORDINATE: Balance(net=Decimal(5))}),
                DEFAULT_ADDRESS,
                DEFAULT_DENOMINATION,
                "OTHER_ASSET",
                Phase.COMMITTED,
                Decimal("0"),
            ),
            (
                BalanceDefaultDict(mapping={DEFAULT_COORDINATE: Balance(net=Decimal(5))}),
                DEFAULT_ADDRESS,
                DEFAULT_DENOMINATION,
                DEFAULT_ASSET,
                Phase.PENDING_IN,
                Decimal("0"),
            ),
        ]
    )
    @pytest.mark.unit
    def test_balance_at_coordinates_no_rounding(
        self,
        balances: BalanceDefaultDict,
        address: str,
        denomination: str,
        asset: str,
        phase: Phase,
        expected_value: Decimal,
    ):
        result = balance_utils.balance_at_coordinates(
            balances=balances,
            address=address,
            denomination=denomination,
            asset=asset,
            phase=phase,
        )

        self.assertEqual(result, expected_value)

    @parameterized.expand(
        [
            (Decimal("5.1234"), 2, Decimal("5.12")),
            (Decimal("5.1266"), 2, Decimal("5.13")),
        ]
    )
    @pytest.mark.unit
    def test_balance_at_coordinates_with_rounding(
        self, net_balance: Decimal, decimal_places: int, expected_value: Decimal
    ):
        balances = BalanceDefaultDict(mapping={DEFAULT_COORDINATE: Balance(net=net_balance)})

        result = balance_utils.balance_at_coordinates(
            balances=balances,
            address=DEFAULT_ADDRESS,
            denomination=DEFAULT_DENOMINATION,
            decimal_places=decimal_places,
        )

        self.assertEqual(result, expected_value)

    @pytest.mark.unit
    def test_get_balance_from_observation(self):
        expected_balance = Decimal("100")
        mock_vault = self.create_mock(
            balances_observation_fetchers_mapping={
                FETCHER_ID: BalancesObservation(
                    balances=BalanceDefaultDict(
                        mapping={DEFAULT_COORDINATE: Balance(net=expected_balance)}
                    ),
                    value_datetime=DEFAULT_DATETIME,
                )
            }
        )

        result = balance_utils.get_balance_from_observation(
            vault=mock_vault,
            balance_coordinate=DEFAULT_COORDINATE,
            fetcher_id=FETCHER_ID,
        )

        self.assertEqual(result, expected_balance)

    @pytest.mark.unit
    def test_get_balance_from_interval_uses_at_datetime(self):
        # We need to simulate the BalanceTimeseries object responding to .at()
        mock_timeseries = MagicMock()
        mock_timeseries.at.return_value = Balance(net=Decimal("50"))

        mock_vault = self.create_mock(
            balances_interval_fetchers_mapping={FETCHER_ID: {DEFAULT_COORDINATE: mock_timeseries}}  # ty: ignore[invalid-argument-type]  # noqa: E501
        )

        effective_dt = datetime(2025, 1, 2, tzinfo=ZoneInfo("UTC"))
        result = balance_utils.get_balance_from_interval(
            vault=mock_vault,
            balance_coordinate=DEFAULT_COORDINATE,
            fetcher_id=FETCHER_ID,
            effective_datetime=effective_dt,
        )

        self.assertEqual(result, Decimal("50"))
        mock_timeseries.at.assert_called_once_with(at_datetime=effective_dt)

    @pytest.mark.unit
    def test_get_balances_from_interval_uses_at_datetime(self):
        mock_timeseries = MagicMock()
        mock_timeseries.at.return_value = Balance(net=Decimal("75"))

        mock_vault = self.create_mock(
            balances_interval_fetchers_mapping={FETCHER_ID: {DEFAULT_COORDINATE: mock_timeseries}}  # ty: ignore[invalid-argument-type]  # noqa: E501
        )

        effective_dt = datetime(2025, 1, 2, tzinfo=ZoneInfo("UTC"))
        result_dict = balance_utils.get_balances_from_interval(
            vault=mock_vault,
            fetcher_id=FETCHER_ID,
            effective_datetime=effective_dt,
        )

        self.assertEqual(result_dict[DEFAULT_COORDINATE].net, Decimal("75"))
        mock_timeseries.at.assert_called_once_with(at_datetime=effective_dt)

    @pytest.mark.unit
    def test_get_balances_from_interval_uses_latest_when_no_datetime(self):
        # Setup the mock timeseries to return a value when .latest() is called
        mock_timeseries = MagicMock()
        mock_timeseries.latest.return_value = Balance(net=Decimal("123"))

        mock_vault = self.create_mock(
            balances_interval_fetchers_mapping={FETCHER_ID: {DEFAULT_COORDINATE: mock_timeseries}}  # ty: ignore[invalid-argument-type]  # noqa: E501
        )

        # Run the function with effective_datetime=None.
        # This triggers the logic in `get_balance_default_dict_from_mapping` to use .latest()
        result_dict = balance_utils.get_balances_from_interval(
            vault=mock_vault,
            fetcher_id=FETCHER_ID,
            effective_datetime=None,  # type: ignore
        )

        # Verify the result matches the value from .latest()
        self.assertEqual(result_dict[DEFAULT_COORDINATE].net, Decimal("123"))

        # Verify .latest() was actually called, and .at() was not
        mock_timeseries.latest.assert_called_once()
        mock_timeseries.at.assert_not_called()

    @pytest.mark.unit
    def test_get_balance_default_dict_from_mapping_uses_latest_if_datetime_none(self):
        # Direct test for the helper function to cover the "else ts.latest()" branch
        mock_timeseries = MagicMock()
        mock_timeseries.latest.return_value = Balance(net=Decimal(99))

        mapping = {DEFAULT_COORDINATE: mock_timeseries}

        # Calling the helper directly
        result = balance_utils.get_balance_default_dict_from_mapping(
            mapping=mapping, effective_datetime=None
        )

        self.assertEqual(result[DEFAULT_COORDINATE].net, Decimal(99))
        mock_timeseries.latest.assert_called_once()

    @pytest.mark.unit
    def test_get_available_balance_default_phases(self):
        balances = BalanceDefaultDict(
            mapping={
                DEFAULT_COORDINATE: Balance(net=Decimal(10)),
                PENDING_OUT_DEFAULT_COORD: Balance(net=Decimal(-2)),
                PENDING_IN_DEFAULT_COORD: Balance(net=Decimal(5)),
            }
        )
        result = balance_utils.get_available_balance(
            balances=balances, denomination=DEFAULT_DENOMINATION
        )
        self.assertEqual(result.net, Decimal(8))

    @pytest.mark.unit
    def test_get_available_balance_custom_phase(self):
        balances = BalanceDefaultDict(
            mapping={
                DEFAULT_COORDINATE: Balance(net=Decimal(10)),
                PENDING_OUT_DEFAULT_COORD: Balance(net=Decimal(-2)),
                PENDING_IN_DEFAULT_COORD: Balance(net=Decimal(5)),
            }
        )
        result = balance_utils.get_available_balance(
            balances=balances, denomination=DEFAULT_DENOMINATION, phase=Phase.PENDING_IN
        )
        self.assertEqual(result.net, Decimal(5))

    @pytest.mark.unit
    def test_get_current_net_balance_default_phases(self):
        balances = BalanceDefaultDict(
            mapping={
                DEFAULT_COORDINATE: Balance(net=Decimal(10)),
                PENDING_OUT_DEFAULT_COORD: Balance(net=Decimal(-2)),
                PENDING_IN_DEFAULT_COORD: Balance(net=Decimal(5)),
            }
        )
        result = balance_utils.get_current_net_balance(
            balances=balances, denomination=DEFAULT_DENOMINATION
        )
        self.assertEqual(result.net, Decimal(15))

    @pytest.mark.unit
    def test_get_current_net_balance_custom_phase(self):
        balances = BalanceDefaultDict(
            mapping={
                DEFAULT_COORDINATE: Balance(net=Decimal(10)),
                PENDING_OUT_DEFAULT_COORD: Balance(net=Decimal(-2)),
                PENDING_IN_DEFAULT_COORD: Balance(net=Decimal(5)),
            }
        )
        result = balance_utils.get_current_net_balance(
            balances=balances, denomination=DEFAULT_DENOMINATION, phase=Phase.PENDING_OUT
        )
        self.assertEqual(result.net, Decimal(-2))


class ValidateReadyForClosureTest(FeatureTest):
    @pytest.mark.unit
    def test_validate_ready_for_closure_returns_none_when_all_balances_are_zero(self):
        balances = BalanceDefaultDict(
            mapping={
                DEFAULT_COORDINATE: Balance(net=Decimal(0)),
                PENDING_OUT_DEFAULT_COORD: Balance(net=Decimal(0)),
            }
        )
        result = balance_utils.validate_ready_for_closure(balances=balances)
        self.assertIsNone(result)

    @pytest.mark.unit
    def test_validate_ready_for_closure_returns_rejection_when_net_credit_balance_exists(self):
        balances = BalanceDefaultDict(
            mapping={
                DEFAULT_COORDINATE: Balance(net=Decimal(10)),
                PENDING_OUT_DEFAULT_COORD: Balance(net=Decimal(-10)),
            }
        )
        expected_result = Rejection(
            message="There are non-zero balances.",
            reason_code=RejectionReason.AGAINST_TNC,
        )
        result = balance_utils.validate_ready_for_closure(balances=balances)
        self.assertEqual(result, expected_result)

    @pytest.mark.unit
    def test_validate_ready_for_closure_returns_rejection_when_net_debit_balance_exists(self):
        balances = BalanceDefaultDict(
            mapping={
                DEFAULT_COORDINATE: Balance(net=Decimal(0)),
                PENDING_OUT_DEFAULT_COORD: Balance(net=Decimal(-10)),
            }
        )
        expected_result = Rejection(
            message="There are non-zero balances.",
            reason_code=RejectionReason.AGAINST_TNC,
        )
        result = balance_utils.validate_ready_for_closure(balances=balances)
        self.assertEqual(result, expected_result)

    @pytest.mark.unit
    def test_validate_ready_for_closure_returns_rejection_when_balances_cancel(self):
        balances = BalanceDefaultDict(
            mapping={
                DEFAULT_COORDINATE: Balance(net=Decimal(10)),
                PENDING_OUT_DEFAULT_COORD: Balance(net=Decimal(-10)),
            }
        )
        expected_result = Rejection(
            message="There are non-zero balances.",
            reason_code=RejectionReason.AGAINST_TNC,
        )
        result = balance_utils.validate_ready_for_closure(balances=balances)
        self.assertEqual(result, expected_result)

    @pytest.mark.unit
    def test_validate_ready_for_closure_returns_none_for_empty_balances(self):
        balances = BalanceDefaultDict()
        result = balance_utils.validate_ready_for_closure(balances=balances)
        self.assertIsNone(result)
