# feature library
import feature_library.lending.addresses as lending_addresses

# inception sdk
from inception_sdk.test_framework.common.balance_helpers import BalanceDimensions

from tests.common.test_denomination import DEFAULT_DENOMINATION

PRINCIPAL = BalanceDimensions(
    address=lending_addresses.PRINCIPAL,
    denomination=DEFAULT_DENOMINATION,
)
ACCRUED_INTEREST_RECEIVABLE = BalanceDimensions(
    address=lending_addresses.ACCRUED_INTEREST_RECEIVABLE,
    denomination=DEFAULT_DENOMINATION,
)
