# Copyright @ 2026 Thought Machine Group Limited. All rights reserved.
import feature_library.lending.addresses as lending_addresses

from inception_sdk.test_framework.common.balance_helpers import BalanceDimensions

from tests.common.test_denomination import DEFAULT_DENOMINATION

principal = BalanceDimensions(
    address=lending_addresses.PRINCIPAL,
    denomination=DEFAULT_DENOMINATION,
)
principal_due = BalanceDimensions(
    address=lending_addresses.PRINCIPAL_DUE,
    denomination=DEFAULT_DENOMINATION,
)
