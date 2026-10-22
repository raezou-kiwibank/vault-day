# standard libs

# features

from inception_sdk.test_framework.common.constants import ASSET, LIABILITY

import tests.deposit.fees.unarranged_overdraft_fee.simulation.parameters as parameters

CUSTOMER_ACCOUNT = "CUSTOMER_ACCOUNT"
DUMMY_INTERNAL_ACCOUNT = "DUMMY_INTERNAL_ACCOUNT"

default_internal_accounts = {
    DUMMY_INTERNAL_ACCOUNT: ASSET,
    parameters.INCOME_ACCOUNT: ASSET,
    parameters.RECEIVABLE_ACCOUNT: LIABILITY,
}
