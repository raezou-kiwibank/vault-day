# inception sdk
from inception_sdk.test_framework.common.constants import ASSET, LIABILITY

CUSTOMER_ACCOUNT = "LOAN_ACCOUNT"

DEPOSIT_ACCOUNT = "DEPOSIT_ACCOUNT"
ACCRUAL_RECEIVABLE = "ACCRUAL_RECEIVABLE"


default_internal_accounts = {
    DEPOSIT_ACCOUNT: LIABILITY,
    ACCRUAL_RECEIVABLE: ASSET,
}
