# contracts api
# features
from feature_library.deposit.fees.unarranged_overdraft_fee import OVERDRAFT_FEE_ADDRESS

from contracts_api import DEFAULT_ADDRESS

from inception_sdk.test_framework.common.balance_helpers import BalanceDimensions

# local imports
from tests.deposit.fees.unarranged_overdraft_fee.simulation.parameters import DEFAULT_DENOMINATION

DEFAULT = BalanceDimensions(
    address=DEFAULT_ADDRESS,
    denomination=DEFAULT_DENOMINATION,
)

OVERDRAFT_FEE = BalanceDimensions(
    address=OVERDRAFT_FEE_ADDRESS,
    denomination=DEFAULT_DENOMINATION,
)
