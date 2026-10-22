# Accounts
# inception sdk
from inception_sdk.test_framework.common.constants import LIABILITY

CUSTOMER_ACCOUNT = "CUSTOMER_ACCOUNT"

# Dummy account
DUMMY_INTERNAL_ACCOUNT = "DUMMY_ACCOUNT"

# Internal accounts for simulation
default_internal_accounts = {
    "1": LIABILITY,
    DUMMY_INTERNAL_ACCOUNT: LIABILITY,
}
