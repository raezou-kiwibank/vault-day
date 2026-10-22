# Copyright @ 2023 Thought Machine Group Limited. All rights reserved.

# standard libs
from datetime import datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

# contracts api
from contracts_api import (
    Attribute,
    AttributeDateTimeType,
    AttributeDecimalType,
    AttributeHookArguments,
    AttributeHookResult,
    AttributeStringType,
)

# inception sdk
from inception_sdk.vault.contracts.extensions.contracts_api_extensions.vault_types import (
    SmartContractVault,
)

api = "4.0.0"
version = "1.0.0"

STRING_ATTRIBUTE_NAME = "string_attribute"
DECIMAL_ATTRIBUTE_NAME = "decimal_attribute"
DATE_TIME_ATTRIBUTE_NAME = "date_time_attribute"

attributes = [
    Attribute(
        name=STRING_ATTRIBUTE_NAME,
        data_type=AttributeStringType(),
    ),
    Attribute(
        name=DECIMAL_ATTRIBUTE_NAME,
        data_type=AttributeDecimalType(),
    ),
    Attribute(
        name=DATE_TIME_ATTRIBUTE_NAME,
        data_type=AttributeDateTimeType(),
    ),
]


def attribute_hook(
    vault: SmartContractVault, hook_arguments: AttributeHookArguments
) -> AttributeHookResult:
    attribute_name = hook_arguments.attribute_name
    attribute_value_map = {
        STRING_ATTRIBUTE_NAME: "string_attribute_value",
        DECIMAL_ATTRIBUTE_NAME: Decimal("1234"),
        DATE_TIME_ATTRIBUTE_NAME: datetime(2025, 2, 2, tzinfo=ZoneInfo("UTC")),
    }
    return AttributeHookResult(attribute_value=attribute_value_map[attribute_name])
