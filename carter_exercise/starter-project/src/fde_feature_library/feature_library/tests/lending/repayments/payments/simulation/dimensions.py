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
PRINCIPAL_DUE = BalanceDimensions(
    address=lending_addresses.PRINCIPAL_DUE,
    denomination=DEFAULT_DENOMINATION,
)
INTEREST_DUE = BalanceDimensions(
    address=lending_addresses.INTEREST_DUE,
    denomination=DEFAULT_DENOMINATION,
)
ACCRUED_INTEREST_RECEIVABLE = BalanceDimensions(
    address=lending_addresses.ACCRUED_INTEREST_RECEIVABLE,
    denomination=DEFAULT_DENOMINATION,
)
EARLY_REPAYMENT_FEE_INCOME = BalanceDimensions(
    denomination=DEFAULT_DENOMINATION,
)
PRINCIPAL_OVERDUE = BalanceDimensions(
    address=lending_addresses.PRINCIPAL_OVERDUE,
    denomination=DEFAULT_DENOMINATION,
)
PRINCIPAL_OVERDUE_20251201 = BalanceDimensions(
    address=f"{lending_addresses.PRINCIPAL_OVERDUE}_20251201",
    denomination=DEFAULT_DENOMINATION,
)
PRINCIPAL_OVERDUE_20260101 = BalanceDimensions(
    address=f"{lending_addresses.PRINCIPAL_OVERDUE}_20260101",
    denomination=DEFAULT_DENOMINATION,
)
INTEREST_OVERDUE = BalanceDimensions(
    address=lending_addresses.INTEREST_OVERDUE,
    denomination=DEFAULT_DENOMINATION,
)
INTEREST_OVERDUE_20251201 = BalanceDimensions(
    address=f"{lending_addresses.INTEREST_OVERDUE}_20251201",
    denomination=DEFAULT_DENOMINATION,
)
INTEREST_OVERDUE_20260101 = BalanceDimensions(
    address=f"{lending_addresses.INTEREST_OVERDUE}_20260101",
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
