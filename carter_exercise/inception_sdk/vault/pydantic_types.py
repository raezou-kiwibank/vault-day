# standard libs
from decimal import Decimal, DecimalException
from typing import Annotated, Any, Callable, Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

# third party
from pydantic import AwareDatetime, BaseModel, ConfigDict, GetCoreSchemaHandler
from pydantic.functional_serializers import PlainSerializer
from pydantic.main import IncEx
from pydantic_core import core_schema

# inception sdk
from inception_sdk.test_framework.common.date_helper import isoformat


class OneOfException(Exception):
    pass


class VaultBaseModel(BaseModel):
    # ensures we serialise to enum.value, as Vault APIs expect
    model_config = ConfigDict(use_enum_values=True)

    @classmethod
    def one_of_validator(cls, data: dict[str, Any], field_names: list[str]):
        populated_fields = [
            # `None` is considered to be an unpopulated field so we can't just check if
            # field_name is in the dict keys
            data[field_name]
            for field_name in field_names
            if data.get(field_name) is not None
        ]
        if len(populated_fields) != 1:
            raise OneOfException(
                f"{cls.__name__} can contain one of {field_names}. Got {populated_fields}"
            )
        return data

    # We are overriding the default behaviour of `by_alias` so that it now defaults to True.
    # This is since we have some attributes which clash with Pythonic keywords, e.g. global,
    # hence we alias this to global_ and must serialise by alias to build the correct requests.
    def model_dump(
        self,
        *,
        mode: Literal["json", "python"] | str = "python",
        include: IncEx | None = None,
        exclude: IncEx | None = None,
        context: Any | None = None,
        by_alias: bool | None = True,  # this default diverges from Pydantic default
        exclude_unset: bool = False,
        exclude_defaults: bool = False,
        exclude_none: bool = False,
        exclude_computed_fields: bool = False,
        round_trip: bool = False,
        warnings: bool | Literal["none", "warn", "error"] = True,
        fallback: Callable[[Any], Any] | None = None,
        serialize_as_any: bool = False,
        polymorphic_serialization: bool | None = None,
    ) -> dict[str, Any]:
        return super().model_dump(
            mode=mode,
            include=include,
            exclude=exclude,
            context=context,
            by_alias=by_alias,
            exclude_unset=exclude_unset,
            exclude_defaults=exclude_defaults,
            exclude_none=exclude_none,
            exclude_computed_fields=exclude_computed_fields,
            round_trip=round_trip,
            warnings=warnings,
            fallback=fallback,
            serialize_as_any=serialize_as_any,
            polymorphic_serialization=polymorphic_serialization,
        )

    def model_dump_json(
        self,
        *,
        indent: int | None = None,
        ensure_ascii: bool = False,
        include: IncEx | None = None,
        exclude: IncEx | None = None,
        context: Any | None = None,
        by_alias: bool | None = True,  # this default diverges from Pydantic default
        exclude_unset: bool = False,
        exclude_defaults: bool = False,
        exclude_none: bool = False,
        exclude_computed_fields: bool = False,
        round_trip: bool = False,
        warnings: bool | Literal["none", "warn", "error"] = True,
        fallback: Callable[[Any], Any] | None = None,
        serialize_as_any: bool = False,
        polymorphic_serialization: bool | None = None,
    ) -> str:
        return super().model_dump_json(
            indent=indent,
            ensure_ascii=ensure_ascii,
            include=include,
            exclude=exclude,
            context=context,
            by_alias=by_alias,
            exclude_unset=exclude_unset,
            exclude_defaults=exclude_defaults,
            exclude_none=exclude_none,
            exclude_computed_fields=exclude_computed_fields,
            round_trip=round_trip,
            warnings=warnings,
            fallback=fallback,
            serialize_as_any=serialize_as_any,
            polymorphic_serialization=polymorphic_serialization,
        )


class _OptionalZoneInfoPydanticAnnotation:
    # Due to proto behaviour the timezone in REST APIs can be an empty string or an IANA timezone
    # which should be treated in Python as None or ZoneInfo, respectively
    @classmethod
    def __get_pydantic_core_schema__(
        cls, _source_type: Any, _handler: GetCoreSchemaHandler
    ) -> core_schema.CoreSchema:
        def validate_from_str(value: str) -> ZoneInfo | None:
            try:
                # Handles empty string
                return None if value == "" else ZoneInfo(value)
            except ZoneInfoNotFoundError:
                raise ValueError("Invalid timezone")

        none_or_str_schema = core_schema.union_schema(
            [
                core_schema.none_schema(),
                core_schema.chain_schema(
                    [
                        core_schema.str_schema(),
                        core_schema.no_info_plain_validator_function(validate_from_str),
                    ],
                ),
            ]
        )
        return core_schema.json_or_python_schema(
            json_schema=none_or_str_schema,
            python_schema=core_schema.union_schema(
                [
                    core_schema.is_instance_schema(ZoneInfo),
                    none_or_str_schema,
                ]
            ),
            serialization=core_schema.plain_serializer_function_ser_schema(
                lambda instance: "" if instance is None else instance.key, when_used="always"
            ),
        )


class _OptionalDecimalPydanticAnnotation:
    # Due to proto behaviour the decimal type in REST APIs can be an empty string or a decimal
    # string which should be treated in Python as None or Decimal, respectively
    @classmethod
    def __get_pydantic_core_schema__(
        cls, _source_type: Any, _handler: GetCoreSchemaHandler
    ) -> core_schema.CoreSchema:
        def validate_from_str(value: str) -> Decimal | None:
            try:
                # Handles empty string
                return None if value == "" else Decimal(value)
            except DecimalException:
                raise ValueError("Invalid decimal value")

        none_or_str_schema = core_schema.union_schema(
            [
                core_schema.none_schema(),
                core_schema.chain_schema(
                    [
                        core_schema.str_schema(),
                        core_schema.no_info_plain_validator_function(validate_from_str),
                    ],
                ),
            ]
        )
        return core_schema.json_or_python_schema(
            json_schema=none_or_str_schema,
            python_schema=core_schema.union_schema(
                [
                    core_schema.is_instance_schema(Decimal),
                    none_or_str_schema,
                ]
            ),
            serialization=core_schema.plain_serializer_function_ser_schema(
                lambda instance: "" if instance is None else str(instance), when_used="always"
            ),
        )


OptionalZoneInfo = Annotated[ZoneInfo | None, _OptionalZoneInfoPydanticAnnotation]
Datetime = Annotated[
    AwareDatetime,
    PlainSerializer(lambda x: isoformat(x)),
]
OptionalDatetime = Datetime | None
# Ensures we can serialise to JSON ok
Decimal_ = Annotated[Decimal, PlainSerializer(lambda x: str(x))]
OptionalDecimal = Annotated[Decimal | None, _OptionalDecimalPydanticAnnotation]
