# library
import feature_library.lending.addresses as apex_addresses

# inception sdk
from inception_sdk.test_framework.common.balance_helpers import BalanceDimensions

from tests.common.test_denomination import DEFAULT_DENOMINATION

DEFAULT = BalanceDimensions(denomination=DEFAULT_DENOMINATION)
PURCHASE = BalanceDimensions(
    address=apex_addresses.PURCHASE,
    denomination=DEFAULT_DENOMINATION,
)
