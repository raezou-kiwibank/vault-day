# Copyright @ 2026 Thought Machine Group Limited. All rights reserved.
import feature_library.lending.addresses as lending_addresses

from inception_sdk.test_framework.common.balance_helpers import BalanceDimensions

from tests.common.test_denomination import DEFAULT_DENOMINATION

PRINCIPAL = BalanceDimensions(
    address=lending_addresses.PRINCIPAL,
    denomination=DEFAULT_DENOMINATION,
)
PRINCIPAL_DUE = BalanceDimensions(
    address=lending_addresses.PRINCIPAL_DUE,
    denomination=DEFAULT_DENOMINATION,
)
INTEREST_DUE = BalanceDimensions(
    address=lending_addresses.INTEREST_DUE,
    denomination=DEFAULT_DENOMINATION,
)
PRINCIPAL_OVERDUE = BalanceDimensions(
    address=lending_addresses.PRINCIPAL_OVERDUE,
    denomination=DEFAULT_DENOMINATION,
)
INTEREST_OVERDUE = BalanceDimensions(
    address=lending_addresses.INTEREST_OVERDUE,
    denomination=DEFAULT_DENOMINATION,
)
PENALTIES = BalanceDimensions(
    address=lending_addresses.PENALTIES,
    denomination=DEFAULT_DENOMINATION,
)
ACCRUED_INTEREST_RECEIVABLE = BalanceDimensions(
    address=lending_addresses.ACCRUED_INTEREST_RECEIVABLE,
    denomination=DEFAULT_DENOMINATION,
)
