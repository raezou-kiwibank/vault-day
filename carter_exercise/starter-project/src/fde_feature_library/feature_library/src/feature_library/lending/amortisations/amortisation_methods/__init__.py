# Copyright @ 2026 Thought Machine Group Limited. All rights reserved.

# standard libs
from typing import NamedTuple

# feature library
import feature_library.common.application_precision as application_precision_module
import feature_library.common.denomination as denomination_module
import feature_library.lending.addresses as lending_addresses
import feature_library.lending.interest.interest_application as interest_application
import feature_library.lending.interest.secondary.fixed_rate as fixed_rate
import feature_library.lending.principal.principal as principal_module
import feature_library.lending.term.term as term_helpers

TermDetails = NamedTuple(
    "TermDetails",
    [
        ("elapsed", int),
        ("remaining", int),
    ],
)

TermDetailsFetchersConfig = NamedTuple(
    "DecliningPrincipalFetchersConfig",
    [
        ("denomination_param_id", str),
        ("term_param_id", str),
        ("principal_address", str),
        ("eia_address", str),
    ],
)

DEFAULT_TERM_DETAILS_FETCHERS_CONFIG = TermDetailsFetchersConfig(
    denomination_param_id=denomination_module.DENOMINATION_PARAM.id,
    term_param_id=term_helpers.TERM_PARAM_ID,
    principal_address=lending_addresses.PRINCIPAL,
    eia_address=lending_addresses.EIA,
)

CalculateEiaFetchersConfig = NamedTuple(
    "CalculateEiaFetchersConfig",
    [
        ("principal_param_id", str),
        ("term_param_id", str),
        ("application_precision_param_id", str),
    ],
)
DEFAULT_CALCULATE_EIA_FETCHERS_CONFIG = CalculateEiaFetchersConfig(
    principal_param_id=principal_module.PRINCIPAL_PARAM_ID,
    term_param_id=term_helpers.TERM_PARAM_ID,
    application_precision_param_id=application_precision_module.APPLICATION_PRECISION_PARAM_ID,
)

GetInterestFetchersConfig = NamedTuple(
    "GetInterestFetchersConfig",
    [
        ("denomination_param_id", str),
        ("principal_param_id", str),
        ("term_param_id", str),
        ("fixed_interest_rate_param_id", str),
        ("application_precision_param_id", str),
    ],
)
DEFAULT_GET_INTEREST_FETCHERS_CONFIG = GetInterestFetchersConfig(
    denomination_param_id=denomination_module.DENOMINATION_PARAM_ID,
    principal_param_id=principal_module.PRINCIPAL_PARAM_ID,
    term_param_id=term_helpers.TERM_PARAM_ID,
    fixed_interest_rate_param_id=fixed_rate.FIXED_INTEREST_RATE_PARAM_ID,
    application_precision_param_id=application_precision_module.APPLICATION_PRECISION_PARAM_ID,
)

ApplyInterestFetchersConfig = NamedTuple(
    "ApplyInterestFetchersConfig",
    [
        ("denomination_param_id", str),
        ("interest_received_account_param_id", str),
        ("interest_due_address", str),
    ],
)
DEFAULT_APPLY_INTEREST_FETCHERS_CONFIG = ApplyInterestFetchersConfig(
    denomination_param_id=denomination_module.DENOMINATION_PARAM_ID,
    interest_received_account_param_id=interest_application.INTEREST_RECEIVED_ACCOUNT_PARAM_ID,
    interest_due_address=lending_addresses.INTEREST_DUE,
)
