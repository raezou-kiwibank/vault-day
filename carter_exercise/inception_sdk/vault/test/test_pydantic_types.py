# standard libs
from datetime import datetime
from decimal import Decimal
from typing import Any
from unittest import TestCase
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

# third party
from pydantic import ValidationError, model_validator

# inception sdk
import inception_sdk.vault.pydantic_types as pydantic_types
from inception_sdk.vault.test.common import TestPydanticModels


class ClassWithZoneInfo(pydantic_types.VaultBaseModel):
    zoneinfo_field: pydantic_types.OptionalZoneInfo = None


class TestValidZoneInfo(TestPydanticModels.Base[ClassWithZoneInfo]):

    dictionary = dict(zoneinfo_field="Europe/London")
    resource = ClassWithZoneInfo(zoneinfo_field=ZoneInfo("Europe/London"))


class TestNoneZoneInfo(TestPydanticModels.Base[ClassWithZoneInfo]):

    dictionary = dict(zoneinfo_field="")
    resource = ClassWithZoneInfo()


class TestInvalidZoneInfo(TestCase):

    def test_invalid_timezone_parsing(self):
        with self.assertRaises(ZoneInfoNotFoundError):
            ClassWithZoneInfo(zoneinfo_field=ZoneInfo("Invalid/TZ"))

    def test_invalid_timezone_outputting(self):
        with self.assertRaises(ValueError):
            ClassWithZoneInfo.model_validate(dict(zoneinfo_field="Invalid/TZ"))


class ClassWithDecimal(pydantic_types.VaultBaseModel):
    decimal_field: pydantic_types.OptionalDecimal = None


class TestValidDecimal(TestPydanticModels.Base[ClassWithDecimal]):

    dictionary = dict(decimal_field="0.00")
    resource = ClassWithDecimal(decimal_field=Decimal("0.00"))


class TestNoneDecimal(TestPydanticModels.Base[ClassWithDecimal]):

    dictionary = dict(decimal_field="")
    resource = ClassWithDecimal(decimal_field=None)


class TestInvalidDecimal(TestCase):

    def test_invalid_decimal(self):
        with self.assertRaises(ValidationError):
            ClassWithDecimal.model_validate(dict(decimal_field="invalid_decimal"))


class ClassWithOptionalDateTime(pydantic_types.VaultBaseModel):
    datetime_field: pydantic_types.OptionalDatetime = None


class TestValidOptionalDatetime(TestPydanticModels.Base[ClassWithOptionalDateTime]):

    dictionary = dict(datetime_field="2023-01-02T03:04:05.000006+00:00")
    resource = ClassWithOptionalDateTime(
        datetime_field=datetime(2023, 1, 2, 3, 4, 5, 6, tzinfo=ZoneInfo("UTC"))
    )


class TestNoneOptionalDatetime(TestPydanticModels.Base[ClassWithOptionalDateTime]):

    dictionary = dict(datetime_field=None)
    resource = ClassWithOptionalDateTime()


class TestOptionalDatetimeValidation(TestCase):

    def test_invalid_datetime(self):
        with self.assertRaises(ValidationError):
            ClassWithOptionalDateTime.model_validate(dict(datetime_field="2023-99-99T00:00:00Z"))

    def test_missing_timezone(self):
        with self.assertRaises(ValidationError):
            ClassWithOptionalDateTime.model_validate(dict(datetime_field="2023-01-02T00:00:00"))


class ClassWithDateTime(pydantic_types.VaultBaseModel):
    datetime_field: pydantic_types.Datetime


class TestValidDatetime(TestPydanticModels.Base[ClassWithDateTime]):

    dictionary = dict(datetime_field="2023-01-02T03:04:05.000006+00:00")
    resource = ClassWithDateTime(
        datetime_field=datetime(2023, 1, 2, 3, 4, 5, 6, tzinfo=ZoneInfo("UTC"))
    )


class TestDatetimeValidation(TestCase):

    def test_invalid_datetime(self):
        with self.assertRaises(ValidationError):
            ClassWithDateTime.model_validate(dict(datetime_field="2023-99-99T00:00:00Z"))

    def test_missing_timezone(self):
        with self.assertRaises(ValidationError):
            ClassWithDateTime.model_validate(dict(datetime_field="2023-01-02T00:00:00"))

    def test_none_datetime(self):
        with self.assertRaises(ValidationError):
            ClassWithDateTime.model_validate(dict())


class TestOneOfValidator(TestCase):

    class ModelWithOneOf(pydantic_types.VaultBaseModel):
        field_1: str | None = None
        field_2: dict | None = None
        field_3: str | None = None

        @model_validator(mode="before")
        @classmethod
        def validate_model(cls, data: Any) -> Any:
            """
            Check that only one field is populated out of field_1 and field_2
            """
            if isinstance(data, dict):
                cls.one_of_validator(
                    data=data,
                    field_names=["field_1", "field_2"],
                )

            return data

    def test_one_of_raises_if_multiple(self):
        with self.assertRaises(pydantic_types.OneOfException):
            self.ModelWithOneOf(field_1="1", field_2={})

    def test_one_of_raises_if_none_specified(self):
        with self.assertRaises(pydantic_types.OneOfException):
            self.ModelWithOneOf()

    def test_one_of_raises_for_explicit_none(self):
        with self.assertRaises(pydantic_types.OneOfException):
            self.ModelWithOneOf(field_2=None)

    def test_one_of_doesnt_raise_if_one_field_populated(self):
        self.assertIsNotNone(self.ModelWithOneOf(field_1="1"))
