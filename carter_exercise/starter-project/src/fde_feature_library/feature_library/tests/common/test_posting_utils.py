# standard libs
from decimal import Decimal

import pytest

# third party
from parameterized import parameterized

# features
from feature_library.common import posting_utils

# contracts api
from contracts_api import (
    DEFAULT_ADDRESS,
    DEFAULT_ASSET,
    BalanceCoordinate,
    Phase,
)

# inception sdk
from inception_sdk.test_framework.contracts.unit.common import FeatureTest

from tests.common.test_denomination import DEFAULT_DENOMINATION

DEFAULT_COORDINATE = BalanceCoordinate(
    account_address=DEFAULT_ADDRESS,
    asset=DEFAULT_ASSET,
    denomination=DEFAULT_DENOMINATION,
    phase=Phase.COMMITTED,
)


class PostingUtilsTest(FeatureTest):
    @parameterized.expand(
        input=[
            (Decimal(100), 2),
            (Decimal(0), 0),
            (Decimal(-10), 2),
        ]
    )
    @pytest.mark.unit
    def test_create_postings(self, amount, expected_len):
        result = posting_utils.create_postings(
            amount=amount,
            debit_account="DEBIT_ACC",
            credit_account="CREDIT_ACC",
            denomination=DEFAULT_DENOMINATION,
        )

        self.assertEqual(len(result), expected_len)

        if expected_len > 0:
            debit_posting = result[0]
            credit_posting = result[1]
            is_positive_amt = amount >= 0
            if not is_positive_amt:
                debit_posting, credit_posting = credit_posting, debit_posting

            self.assertEqual(credit_posting.amount, abs(amount))
            self.assertEqual(credit_posting.credit, True)
            self.assertEqual(
                credit_posting.account_id, "CREDIT_ACC" if is_positive_amt else "DEBIT_ACC"
            )

            self.assertEqual(debit_posting.amount, abs(amount))
            self.assertEqual(debit_posting.credit, False)
            self.assertEqual(
                debit_posting.account_id, "DEBIT_ACC" if is_positive_amt else "CREDIT_ACC"
            )
