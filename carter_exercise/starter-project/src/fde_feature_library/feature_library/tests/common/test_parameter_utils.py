# standard libs
from datetime import datetime
from decimal import Decimal
from typing import Any
from zoneinfo import ZoneInfo

import pytest

# third party
from parameterized import parameterized

# features
from feature_library.common import parameter_utils

# contracts api
from contracts_api import (
    DEFAULT_ADDRESS,
    DEFAULT_ASSET,
    BalanceCoordinate,
    ExpectedParameter,
    ParametersObservation,
    Phase,
)

# inception sdk
from inception_sdk.test_framework.contracts.unit.common import FeatureTest

from tests.common.test_denomination import DEFAULT_DENOMINATION

PARAMETER_NAME = "parameter_name"
FETCHER_ID = "fetcher_id"
DEFAULT_DATETIME = datetime(2025, 1, 1, tzinfo=ZoneInfo("UTC"))

DEFAULT_COORDINATE = BalanceCoordinate(
    account_address=DEFAULT_ADDRESS,
    asset=DEFAULT_ASSET,
    denomination=DEFAULT_DENOMINATION,
    phase=Phase.COMMITTED,
)


class ParameterUtilsTest(FeatureTest):
    def test_distinct_expected_parameters(self):
        param1 = ExpectedParameter(id="param_1")
        param2 = ExpectedParameter(id="param_2")
        param1_duplicate = ExpectedParameter(id="param_1", optional=True)

        input_params = [param1, param2, param1_duplicate]
        expected_output = [param1, param2]

        result = parameter_utils.distinct_expected_parameters(input_params)

        self.assertListEqual(result, expected_output)

    @parameterized.expand(
        input=[
            ("string", "value", False, False, False, None, "value"),
            ("decimal", Decimal("1"), False, False, False, None, Decimal("1")),
            (
                "date",
                DEFAULT_DATETIME,
                False,
                False,
                False,
                None,
                DEFAULT_DATETIME,
            ),
            (
                "json",
                '{"k": "v"}',
                True,
                False,
                False,
                None,
                {"k": "v"},
            ),
            ("bool_true", "true", False, True, False, None, True),
            ("bool_true_caps", "TRUE", False, True, False, None, True),
            ("bool_false", "false", False, True, False, None, False),
            ("bool_false_caps", "FALSE", False, True, False, None, False),
            ("optional_no_default", None, False, False, True, None, None),
            ("optional_default", None, False, False, True, "default", "default"),
            ("not_optional_default", "value", False, False, False, "default", "value"),
        ]
    )
    @pytest.mark.unit
    def test_get_parameter_from_observation_parameter_types(
        self,
        name: str,
        parameter_value: Any,
        is_json: bool,
        is_boolean: bool,
        is_optional: bool,
        default_value: Any | None,
        expected_value: None,
    ):
        mock_vault = self.create_mock(
            parameters_observation_fetchers_mapping={
                FETCHER_ID: ParametersObservation(
                    parameters={PARAMETER_NAME: parameter_value},
                    value_datetime=DEFAULT_DATETIME,
                )
            }
        )

        result = parameter_utils.get_parameter_from_observation(
            vault=mock_vault,
            name=PARAMETER_NAME,
            fetcher_id=FETCHER_ID,
            is_json=is_json,
            is_boolean=is_boolean,
            is_optional=is_optional,
            default_value=default_value,
        )

        self.assertEqual(result, expected_value)

    @parameterized.expand(
        input=[
            (
                datetime(2025, 1, 1, tzinfo=ZoneInfo("UTC")),
                Decimal("0.1"),
                Decimal("0.0002739726"),
            ),
            (
                datetime(2024, 1, 1, tzinfo=ZoneInfo("UTC")),
                Decimal("0.1"),
                Decimal("0.0002732240"),
            ),
            (datetime(2024, 1, 1, tzinfo=ZoneInfo("UTC")), Decimal("0"), Decimal("0")),
            (
                datetime(2025, 1, 1, tzinfo=ZoneInfo("UTC")),
                Decimal("-0.1"),
                Decimal("-0.0002739726"),
            ),
        ]
    )
    @pytest.mark.unit
    def test_yearly_to_daily_rate_actual_days_in_year(
        self,
        effective_date: datetime,
        yearly_rate: Decimal,
        expected_value: Decimal,
    ):
        result = parameter_utils.yearly_to_daily_rate(effective_date, yearly_rate)

        self.assertEqual(result, expected_value)

    @parameterized.expand(
        input=[
            (
                datetime(2025, 1, 1, tzinfo=ZoneInfo("UTC")),
                Decimal("0.1"),
                Decimal("0.0002777778"),
            ),
            (
                datetime(2024, 1, 1, tzinfo=ZoneInfo("UTC")),
                Decimal("0.1"),
                Decimal("0.0002777778"),
            ),
            (datetime(2024, 1, 1, tzinfo=ZoneInfo("UTC")), Decimal("0"), Decimal("0")),
            (
                datetime(2025, 1, 1, tzinfo=ZoneInfo("UTC")),
                Decimal("-0.1"),
                Decimal("-0.0002777778"),
            ),
        ]
    )
    @pytest.mark.unit
    def test_yearly_to_daily_rate_360_days_in_year(
        self,
        effective_date: datetime,
        yearly_rate: Decimal,
        expected_value: Decimal,
    ):
        result = parameter_utils.yearly_to_daily_rate(
            effective_date, yearly_rate, days_in_year="360"
        )

        self.assertEqual(result, expected_value)

    @parameterized.expand(
        input=[
            (Decimal("0.12"), Decimal("0.01")),
            (Decimal("0"), Decimal("0")),
            (Decimal("-0.12"), Decimal("-0.01")),
            (Decimal("0.1"), Decimal("0.0083333333")),
            (Decimal("-0.1"), Decimal("-0.0083333333")),
        ]
    )
    @pytest.mark.unit
    def test_yearly_to_monthly_rate(self, yearly_rate: Decimal, expected_value: Decimal):
        result = parameter_utils.yearly_to_monthly_rate(yearly_rate)

        self.assertEqual(result, expected_value)
