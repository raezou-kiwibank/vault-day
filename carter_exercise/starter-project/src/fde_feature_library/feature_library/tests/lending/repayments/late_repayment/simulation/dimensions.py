# feature library
import feature_library.lending.addresses as lending_addresses

# inception sdk
from inception_sdk.test_framework.common.balance_helpers import BalanceDimensions

from tests.common.test_denomination import DEFAULT_DENOMINATION

DEFAULT = BalanceDimensions(
    denomination=DEFAULT_DENOMINATION,
)
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
LATE_REPAYMENT_FEE_INCOME = BalanceDimensions(
    denomination=DEFAULT_DENOMINATION,
)
