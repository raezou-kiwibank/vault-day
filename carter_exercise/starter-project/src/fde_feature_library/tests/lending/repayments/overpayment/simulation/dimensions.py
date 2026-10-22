# feature library
import feature_library.common.addresses as common_addresses
import feature_library.lending.addresses as lending_addresses
import feature_library.lending.repayments.overpayment as overpayment

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
OVERPAYMENT = BalanceDimensions(
    address=overpayment.OVERPAYMENT_ADDRESS,
    denomination=DEFAULT_DENOMINATION,
)
INTERNAL_CONTRA = BalanceDimensions(
    address=common_addresses.INTERNAL_CONTRA,
    denomination=DEFAULT_DENOMINATION,
)
PENALTIES = BalanceDimensions(
    address=lending_addresses.PENALTIES,
    denomination=DEFAULT_DENOMINATION,
)
OVERPAYMENT_FEE_INCOME = BalanceDimensions(
    denomination=DEFAULT_DENOMINATION,
)
