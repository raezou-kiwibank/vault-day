from inception_sdk.test_framework.common.balance_helpers import BalanceDimensions

from tests.common.test_denomination import DEFAULT_DENOMINATION

DEFAULT = BalanceDimensions(
    denomination=DEFAULT_DENOMINATION,
)

OUTSTANDING_MONTHLY_MAINTENANCE_FEE_TRACKER = BalanceDimensions(
    address="outstanding_monthly_maintenance_fee_tracker",
    denomination=DEFAULT_DENOMINATION,
)
