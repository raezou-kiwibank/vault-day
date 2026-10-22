# library
import feature_library.deposit.fees.withdrawal.early_withdrawal_fees as early_withdrawal_fees

# inception sdk
from inception_sdk.test_framework.common.balance_helpers import BalanceDimensions

from tests.deposit.fees.withdrawal.early_withdrawal_fee.simulation.parameters import (  # noqa: E501
    DEFAULT_DENOMINATION,
)

DEFAULT = BalanceDimensions(denomination=DEFAULT_DENOMINATION)
EARLY_WITHDRAWALS_TRACKER_DIMENSION = BalanceDimensions(
    address=early_withdrawal_fees.EARLY_WITHDRAWALS_TRACKER_ADDRESS,
    denomination=DEFAULT_DENOMINATION,
)
