# inception sdk
# library
import feature_library.deposit.addresses as deposit_addresses

from inception_sdk.test_framework.common.balance_helpers import BalanceDimensions

from tests.deposit.interest.interest_application.simulation.parameters import (
    DEFAULT_DENOMINATION,
)

DEFAULT = BalanceDimensions(denomination=DEFAULT_DENOMINATION)

ACCRUED_INTEREST_PAYABLE = BalanceDimensions(
    address=deposit_addresses.ACCRUED_INTEREST_PAYABLE,
    denomination=DEFAULT_DENOMINATION,
)
ACCRUED_INTEREST_RECEIVABLE = BalanceDimensions(
    address=deposit_addresses.ACCRUED_INTEREST_RECEIVABLE,
    denomination=DEFAULT_DENOMINATION,
)

OVERDRAFT_ACCRUED_INTEREST = BalanceDimensions(
    address="OVERDRAFT_ACCRUED_INTEREST",
    denomination=DEFAULT_DENOMINATION,
)
