# third party
import pytest
from parameterized import parameterized

# features
from feature_library.common import date_and_time

from contracts_api import Rejection, RejectionReason

# inception sdk
from inception_sdk.test_framework.contracts.unit.common import FeatureTest


class DateAndTimeTest(FeatureTest):
    @parameterized.expand(
        input=[
            # Valid times
            ("12:34:56", None),
            ("00:00:00", None),
            ("23:59:59", None),
            # Invalid length
            (
                "12:34:5",
                Rejection(
                    message="Invalid time format: '12:34:5'. Expected 8 characters (HH:MM:SS).",
                    reason_code=RejectionReason.AGAINST_TNC,
                ),
            ),
            (
                "12:34:567",
                Rejection(
                    message="Invalid time format: '12:34:567'. Expected 8 characters (HH:MM:SS).",
                    reason_code=RejectionReason.AGAINST_TNC,
                ),
            ),
            # Invalid colon positions
            (
                "12-34:56",
                Rejection(
                    message="Invalid time format: '12-34:56'. Expected colons at positions 2 and "
                    "5.",
                    reason_code=RejectionReason.AGAINST_TNC,
                ),
            ),
            (
                "12:34-56",
                Rejection(
                    message="Invalid time format: '12:34-56'. Expected colons at positions 2 and "
                    "5.",
                    reason_code=RejectionReason.AGAINST_TNC,
                ),
            ),
            # Non-numeric segments
            (
                "A2:34:56",
                Rejection(
                    message="Invalid time format: 'A2:34:56'. Time segments must be numeric.",
                    reason_code=RejectionReason.AGAINST_TNC,
                ),
            ),
            (
                "1A:34:56",
                Rejection(
                    message="Invalid time format: '1A:34:56'. Time segments must be numeric.",
                    reason_code=RejectionReason.AGAINST_TNC,
                ),
            ),
            (
                "12:A4:56",
                Rejection(
                    message="Invalid time format: '12:A4:56'. Time segments must be numeric.",
                    reason_code=RejectionReason.AGAINST_TNC,
                ),
            ),
            (
                "12:3A:56",
                Rejection(
                    message="Invalid time format: '12:3A:56'. Time segments must be numeric.",
                    reason_code=RejectionReason.AGAINST_TNC,
                ),
            ),
            (
                "12:34:A6",
                Rejection(
                    message="Invalid time format: '12:34:A6'. Time segments must be numeric.",
                    reason_code=RejectionReason.AGAINST_TNC,
                ),
            ),
            (
                "12:34:5A",
                Rejection(
                    message="Invalid time format: '12:34:5A'. Time segments must be numeric.",
                    reason_code=RejectionReason.AGAINST_TNC,
                ),
            ),
            (
                "AB:CD:EF",
                Rejection(
                    message="Invalid time format: 'AB:CD:EF'. Time segments must be numeric.",
                    reason_code=RejectionReason.AGAINST_TNC,
                ),
            ),
        ]
    )
    @pytest.mark.unit
    def test_validate_time_format(self, time_str: str, expected_rejection: Rejection | None):
        result = date_and_time.validate_time_format(time_str)

        self.assertEqual(result, expected_rejection)

    @parameterized.expand(
        input=[
            ("12:34:56", date_and_time.Time(hour=12, minute=34, second=56)),
            ("00:00:00", date_and_time.Time(hour=0, minute=0, second=0)),
            ("23:59:59", date_and_time.Time(hour=23, minute=59, second=59)),
        ]
    )
    @pytest.mark.unit
    def test_parse_time_str(self, time_str: str, expected_time: date_and_time.Time):
        result = date_and_time.parse_time_str(time_str)
        self.assertEqual(result, expected_time)

    @parameterized.expand(
        input=[
            ("12:34:5",),
            ("12-34:56",),
            ("A2:34:56",),
        ]
    )
    @pytest.mark.unit
    def test_parse_time_str_invalid(self, time_str: str):
        with self.assertRaises(AssertionError):
            date_and_time.parse_time_str(time_str)
