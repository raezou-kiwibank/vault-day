import feature_library.deposit.fees.inactivity_fee as inactivity_fee

# inception sdk
from inception_sdk.test_framework.common.balance_helpers import BalanceDimensions

from tests.deposit.fees.inactivity.simulation.parameters import DEFAULT_DENOMINATION

DEFAULT = BalanceDimensions(denomination=DEFAULT_DENOMINATION)
OUTSTANDING_INACTIVITY_FEE_TRACKER = BalanceDimensions(
    address=inactivity_fee.OUTSTANDING_INACTIVITY_FEE_TRACKER,
    denomination=DEFAULT_DENOMINATION,
)
