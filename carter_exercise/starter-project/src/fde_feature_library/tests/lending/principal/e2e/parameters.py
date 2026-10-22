# standard libs
from decimal import Decimal

# feature library
import feature_library.common.denomination as denomination
import feature_library.lending.principal.maximum_loan_principal as maximum_loan_principal
import feature_library.lending.principal.minimum_loan_principal as minimum_loan_principal

# inception sdk
from inception_sdk.vault.core_api import (
    DecimalParameterValue,
    ParameterValue,
    StringParameterValue,
)

from tests.common.test_denomination import DEFAULT_DENOMINATION

# Shared base parameters
base_parameters: dict[str, ParameterValue] = {
    denomination.DENOMINATION_PARAM_ID: StringParameterValue(
        string_value=DEFAULT_DENOMINATION,
    ),
}

# Maximum Loan Principal specific parameters
maximum_loan_principal_parameters: dict[str, ParameterValue] = {
    **base_parameters,
    maximum_loan_principal.MAXIMUM_LOAN_PRINCIPAL_PARAM_ID: DecimalParameterValue(
        decimal_value=Decimal("1000")
    ),
}

# Minimum Loan Principal specific parameters
minimum_loan_principal_parameters: dict[str, ParameterValue] = {
    **base_parameters,
    minimum_loan_principal.MINIMUM_LOAN_PRINCIPAL_PARAM_ID: DecimalParameterValue(
        decimal_value=Decimal("50")
    ),
}

# Default for backward compatibility
default_parameter_values = maximum_loan_principal_parameters
