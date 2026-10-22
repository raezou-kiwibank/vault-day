# Copyright @ 2026 Thought Machine Group Limited. All rights reserved.
from datetime import datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from feature_library.common import denomination

# feature library
from feature_library.lending.due_amount_calculation import due_amount_calculation

# inception sdk
from inception_sdk.vault.core_api import (
    DatetimeParameterValue,
    DecimalParameterValue,
    EnumerationParameterValue,
    StringParameterValue,
)

from tests.common.test_denomination import DEFAULT_DENOMINATION

UTC = ZoneInfo("UTC")

default_parameter_values = {
    denomination.DENOMINATION_PARAM_ID: StringParameterValue(
        string_value=DEFAULT_DENOMINATION,
    ),
    due_amount_calculation.BILLING_FREQUENCY_PARAM_ID: EnumerationParameterValue(
        enumeration_value="fortnightly",
    ),
    due_amount_calculation.DUE_AMOUNT_CALCULATION_TIME_PARAM_ID: StringParameterValue(
        string_value="00:00:00",
    ),
    due_amount_calculation.DUE_AMOUNT_CALCULATION_DAY_PARAM_ID: DecimalParameterValue(
        decimal_value=Decimal("3"),  # 3 = Wednesday
    ),
    due_amount_calculation.FIRST_DUE_DATE_PARAM_ID: DatetimeParameterValue(
        date_time_value=datetime(2026, 1, 21, tzinfo=UTC),
    ),
}
