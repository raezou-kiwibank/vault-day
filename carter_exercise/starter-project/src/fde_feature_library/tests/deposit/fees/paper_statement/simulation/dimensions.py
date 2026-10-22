# library
import feature_library.deposit.fees.paper_statement_fee as paper_statement_fee

# inception sdk
from inception_sdk.test_framework.common.balance_helpers import BalanceDimensions

from tests.deposit.fees.paper_statement.simulation.parameters import DEFAULT_DENOMINATION

DEFAULT = BalanceDimensions(denomination=DEFAULT_DENOMINATION)
OUTSTANDING_PAPER_STATEMENT_FEE_TRACKER = BalanceDimensions(
    address=paper_statement_fee.OUTSTANDING_PAPER_STATEMENT_FEE_TRACKER,
    denomination=DEFAULT_DENOMINATION,
)
