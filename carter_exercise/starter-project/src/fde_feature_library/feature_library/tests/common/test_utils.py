# standard libs
from decimal import Decimal

import pytest

# third party
from parameterized import parameterized

# features
from feature_library.common import utils

# inception sdk
from inception_sdk.test_framework.contracts.unit.common import FeatureTest


class UtilsTest(FeatureTest):
    @parameterized.expand(
        input=[
            ("true", True),
            ("TRUE", True),
            ("tRUE", True),
            ("_true", False),
            ("false", False),
            ("FALSE", False),
            ("truee", False),
        ]
    )
    @pytest.mark.unit
    def test_str_to_bool(self, string: str, expected_value: bool):
        result = utils.str_to_bool(string)

        self.assertEqual(result, expected_value)

    @parameterized.expand(
        input=[
            (Decimal("0.1234"), 2, Decimal("0.12")),
            (Decimal("0.1278"), 2, Decimal("0.13")),
            (Decimal("0.12"), 2, Decimal("0.12")),
            (Decimal("-0.1234"), 2, Decimal("-0.12")),
            (Decimal("-0.1278"), 2, Decimal("-0.13")),
            (Decimal("-0.12"), 2, Decimal("-0.12")),
        ]
    )
    @pytest.mark.unit
    def test_round_at_decimal_default_rounding(
        self, amount: Decimal, decimal_places: int, expected_value: Decimal
    ):
        result = utils.round_decimal(amount, decimal_places)

        self.assertEqual(result, expected_value)
