import feature_library.lending.addresses as lending_addresses

from contracts_api import DEFAULT_ADDRESS

from inception_sdk.test_framework.common.balance_helpers import BalanceDimensions

from tests.common.test_denomination import DEFAULT_DENOMINATION

default = BalanceDimensions(
    address=DEFAULT_ADDRESS,
    denomination=DEFAULT_DENOMINATION,
)
principal = BalanceDimensions(
    address=lending_addresses.PRINCIPAL,
    denomination=DEFAULT_DENOMINATION,
)
accrued_interest_receivable = BalanceDimensions(
    address=lending_addresses.ACCRUED_INTEREST_RECEIVABLE,
    denomination=DEFAULT_DENOMINATION,
)
interest_due = BalanceDimensions(
    address=lending_addresses.INTEREST_DUE,
    denomination=DEFAULT_DENOMINATION,
)
