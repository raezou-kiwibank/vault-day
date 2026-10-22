# standard libs
from datetime import datetime
from unittest import TestCase
from zoneinfo import ZoneInfo

# inception sdk
from inception_sdk.test_framework.common.date_helper import isoformat, isoparse

UTC = ZoneInfo("UTC")


class TestIsoformat(TestCase):

    def test_isoformat_datetime(self):
        self.assertEquals("2024-01-01T00:00:00+00:00", isoformat(datetime(2024, 1, 1, tzinfo=UTC)))

    def test_isoformat_str(self):
        self.assertEquals("2024-01-01T00:00:00+00:00", isoformat("2024-01-01T00:00:00+00:00"))

    def test_isoformat_none(self):
        self.assertEquals(None, isoformat(None))


class TestIsoparse(TestCase):

    def test_isoparse_str(self):
        self.assertEquals(datetime(2024, 1, 1, tzinfo=UTC), isoparse("2024-01-01T00:00:00+00:00"))

    def test_isoparse_none(self):
        self.assertEquals(None, isoparse(None))
