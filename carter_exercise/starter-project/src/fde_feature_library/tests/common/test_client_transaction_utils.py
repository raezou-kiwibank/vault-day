# standard libs
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import MagicMock, call, patch, sentinel
from zoneinfo import ZoneInfo

import pytest
from dateutil.relativedelta import relativedelta

# features
import feature_library.common.client_transaction_utils as client_transaction_utils

# contracts api
from contracts_api import Balance, ClientTransaction

# inception sdk
from inception_sdk.test_framework.contracts.unit.common import FeatureTest
from inception_sdk.test_framework.contracts.unit.contracts_api_sentinels import DEFAULT_POSTINGS

from tests.common.test_denomination import DEFAULT_DENOMINATION

CUT_OFF_DATE = datetime(2019, 1, 1, tzinfo=ZoneInfo("UTC"))
CTX_ID_1 = "client_transaction_id_1"
CTX_ID_2 = "client_transaction_id_2"
CTX_ID_3 = "client_transaction_id_3"
DEFAULT_ACCOUNT = "default_account"
CTX_ID_DUMMY = "client_transaction_id_dummy"


class TestSumClientTransactions(FeatureTest):
    @pytest.mark.unit
    def test_sum_client_transactions_handles_hard_settlement_deposits(self):
        value_datetime = CUT_OFF_DATE + timedelta(hours=1)

        ctx = ClientTransaction(
            client_transaction_id=CTX_ID_1,
            account_id=DEFAULT_ACCOUNT,
            posting_instructions=[
                self.inbound_hard_settlement(
                    amount=Decimal("501"),
                    value_datetime=value_datetime,
                )
            ],
            tside=self.tside,
        )

        result = client_transaction_utils.sum_client_transactions(
            cutoff_datetime=CUT_OFF_DATE,
            client_transactions={CTX_ID_1: ctx},
            denomination=DEFAULT_DENOMINATION,
        )
        self.assertEqual(result, Balance(credit=Decimal(501), debit=Decimal(0), net=Decimal(501)))

    @pytest.mark.unit
    def test_sum_client_transactions_handles_hard_settlement_withdrawals(self):
        value_datetime = CUT_OFF_DATE + timedelta(hours=+1)

        ctx = ClientTransaction(
            client_transaction_id=CTX_ID_1,
            account_id=DEFAULT_ACCOUNT,
            posting_instructions=[
                self.outbound_hard_settlement(
                    amount=Decimal("502"),
                    value_datetime=value_datetime,
                )
            ],
            tside=self.tside,
        )

        result = client_transaction_utils.sum_client_transactions(
            cutoff_datetime=CUT_OFF_DATE,
            client_transactions={CTX_ID_1: ctx},
            denomination=DEFAULT_DENOMINATION,
        )
        self.assertEqual(result, Balance(credit=Decimal(0), debit=Decimal(502), net=Decimal(-502)))

    @pytest.mark.unit
    def test_sum_client_transactions_handles_mix_of_txns(self):
        """
        Sum should include PIBs of mixed transaction types (e.g. Deposits and Withdrawals)
        """
        value_datetime = CUT_OFF_DATE + timedelta(hours=1)
        postings_inbound = [
            self.inbound_hard_settlement(
                amount=Decimal("501"),
                value_datetime=value_datetime,
            )
        ]
        postings_outbound = [
            self.outbound_hard_settlement(
                amount=Decimal("501"),
                value_datetime=value_datetime,
            )
        ]

        ctx_inbound = ClientTransaction(
            client_transaction_id=CTX_ID_1,
            account_id=DEFAULT_ACCOUNT,
            posting_instructions=postings_inbound,
        )

        ctx_outbound = ClientTransaction(
            client_transaction_id=CTX_ID_1,
            account_id=DEFAULT_ACCOUNT,
            posting_instructions=postings_outbound,
        )

        result = client_transaction_utils.sum_client_transactions(
            cutoff_datetime=CUT_OFF_DATE,
            client_transactions={CTX_ID_1: ctx_inbound, CTX_ID_2: ctx_outbound},
            denomination=DEFAULT_DENOMINATION,
        )
        self.assertEqual(result, Balance(credit=Decimal(501), debit=Decimal(501), net=Decimal(0)))

    @pytest.mark.unit
    def test_sum_client_transactions_settlement_value_not_counted_twice(self):
        """
        When summing client transactions including proposed, the
        function should consider chainable transactions
        and not double count an auth and a settlement
        """
        value_datetime = CUT_OFF_DATE + timedelta(hours=1)

        ctx = ClientTransaction(
            client_transaction_id=CTX_ID_1,
            account_id=DEFAULT_ACCOUNT,
            posting_instructions=[
                self.outbound_auth(
                    amount=Decimal("105"),
                    value_datetime=value_datetime - timedelta(minutes=1),
                ),
                self.settle_outbound_auth(
                    unsettled_amount=Decimal("105"),
                    amount=Decimal("105"),
                    value_datetime=value_datetime,
                ),
            ],
            tside=self.tside,
        )

        result = client_transaction_utils.sum_client_transactions(
            client_transactions={CTX_ID_1: ctx},
            cutoff_datetime=CUT_OFF_DATE,
            denomination=DEFAULT_DENOMINATION,
        )
        self.assertEqual(result, Balance(credit=Decimal(0), debit=Decimal(105), net=Decimal(-105)))

    @pytest.mark.unit
    def test_sum_client_transactions_handles_partial_settlements(self):
        """
        A partial settlement should not affect the sum of the client
        transactions as the settlement wasn't final so any value up to the
        original auth of 105 could still be settled
        """
        value_datetime = CUT_OFF_DATE + timedelta(hours=1)

        ctx = ClientTransaction(
            client_transaction_id=CTX_ID_1,
            account_id=DEFAULT_ACCOUNT,
            posting_instructions=[
                self.outbound_auth(
                    amount=Decimal("105"),
                    value_datetime=value_datetime - timedelta(minutes=1),
                ),
                self.settle_outbound_auth(
                    unsettled_amount=Decimal("105"),
                    amount=Decimal("40"),
                    value_datetime=value_datetime,
                ),
            ],
            tside=self.tside,
        )

        result = client_transaction_utils.sum_client_transactions(
            client_transactions={CTX_ID_1: ctx},
            cutoff_datetime=CUT_OFF_DATE,
            denomination=DEFAULT_DENOMINATION,
        )

        self.assertEqual(result, Balance(credit=Decimal(0), debit=Decimal(105), net=Decimal(-105)))

    @pytest.mark.unit
    def test_sum_client_transaction_handles_cancelled_transactions(self):
        """
        Sum should not include cancelled client transactions ids as the original
        funds that were authed have now be zero'd out
        """
        value_datetime = CUT_OFF_DATE + timedelta(hours=1)

        ctx = ClientTransaction(
            client_transaction_id=CTX_ID_1,
            account_id=DEFAULT_ACCOUNT,
            posting_instructions=[
                self.outbound_auth(
                    amount=Decimal("10"),
                    value_datetime=value_datetime - timedelta(minutes=1),
                ),
                self.release_outbound_auth(
                    unsettled_amount=Decimal("10"),
                    value_datetime=value_datetime,
                ),
            ],
            tside=self.tside,
        )

        result = client_transaction_utils.sum_client_transactions(
            client_transactions={CTX_ID_1: ctx},
            cutoff_datetime=CUT_OFF_DATE,
            denomination=DEFAULT_DENOMINATION,
        )

        self.assertEqual(result, Balance(credit=Decimal(0), debit=Decimal(0), net=Decimal(0)))

    @pytest.mark.unit
    def test_sum_client_transactions_includes_transaction_on_cut_off(self):
        """
        Sum should include pib that takes place on the cut-off time
        """
        value_datetime = CUT_OFF_DATE

        ctx = ClientTransaction(
            client_transaction_id=CTX_ID_1,
            account_id=DEFAULT_ACCOUNT,
            posting_instructions=[
                self.outbound_hard_settlement(
                    amount=Decimal("501"),
                    denomination="USD",
                    value_datetime=value_datetime,
                )
            ],
            tside=self.tside,
        )

        result = client_transaction_utils.sum_client_transactions(
            client_transactions={CTX_ID_1: ctx}, cutoff_datetime=CUT_OFF_DATE, denomination="USD"
        )

        self.assertEqual(result, Balance(credit=Decimal(0), debit=Decimal(501), net=Decimal(-501)))

    @pytest.mark.unit
    def test_sum_client_transactions_includes_transaction_after_cut_off(self):
        """
        Sum should include pib that takes place after the cut-off time
        """
        value_datetime = CUT_OFF_DATE + timedelta(hours=1)

        ctx = ClientTransaction(
            client_transaction_id=CTX_ID_1,
            account_id=DEFAULT_ACCOUNT,
            posting_instructions=[
                self.outbound_hard_settlement(
                    amount=Decimal("501"),
                    denomination="USD",
                    value_datetime=value_datetime,
                )
            ],
            tside=self.tside,
        )

        result = client_transaction_utils.sum_client_transactions(
            client_transactions={CTX_ID_1: ctx}, cutoff_datetime=CUT_OFF_DATE, denomination="USD"
        )

        self.assertEqual(result, Balance(credit=Decimal(0), debit=Decimal(501), net=Decimal(-501)))

    @pytest.mark.unit
    def test_sum_client_transactions_excludes_transaction_before_cut_off(self):
        """
        Sum should not include a posting with value_datetime before the cut-off time as it is not
        considered as part of that day's total
        """
        value_datetime = CUT_OFF_DATE - timedelta(hours=1)

        ctx = ClientTransaction(
            client_transaction_id=CTX_ID_1,
            account_id=DEFAULT_ACCOUNT,
            posting_instructions=[
                self.outbound_hard_settlement(
                    amount=Decimal("501"),
                    denomination="USD",
                    value_datetime=value_datetime,
                )
            ],
            tside=self.tside,
        )

        result = client_transaction_utils.sum_client_transactions(
            client_transactions={CTX_ID_1: ctx}, cutoff_datetime=CUT_OFF_DATE, denomination="USD"
        )

        self.assertEqual(result, Balance(credit=Decimal(0), debit=Decimal(0), net=Decimal(0)))

    @pytest.mark.unit
    def test_sum_client_transactions_excludes_transactions_of_different_denomination(self):
        """
        Sum should not include a posting with denomination different than the one indicated
        """
        value_datetime = CUT_OFF_DATE + timedelta(hours=1)

        ctx = ClientTransaction(
            client_transaction_id=CTX_ID_1,
            account_id=DEFAULT_ACCOUNT,
            posting_instructions=[
                self.outbound_hard_settlement(
                    amount=Decimal("501"),
                    denomination="USD",
                    value_datetime=value_datetime,
                )
            ],
            tside=self.tside,
        )

        ctx2 = ClientTransaction(
            client_transaction_id=CTX_ID_2,
            account_id=DEFAULT_ACCOUNT,
            posting_instructions=[
                self.outbound_hard_settlement(
                    amount=Decimal("100"),
                    denomination="EUR",
                    value_datetime=value_datetime,
                )
            ],
            tside=self.tside,
        )

        result = client_transaction_utils.sum_client_transactions(
            client_transactions={CTX_ID_1: ctx, CTX_ID_2: ctx2},
            cutoff_datetime=CUT_OFF_DATE,
            denomination="EUR",
        )

        self.assertEqual(result, Balance(credit=Decimal(0), debit=Decimal(100), net=Decimal(-100)))

    @pytest.mark.unit
    def test_chainable_transactions_auth_adjust_cut_off_respected(self):
        """
        If an auth takes place before the cutoff time, only the
        proposed auth adjustment should contribute to the
        withdrawals.
        """
        previous_day_value_datetime = CUT_OFF_DATE - timedelta(hours=23)
        value_datetime = CUT_OFF_DATE + timedelta(hours=1)

        ctx = ClientTransaction(
            client_transaction_id=CTX_ID_1,
            account_id=DEFAULT_ACCOUNT,
            posting_instructions=[
                self.outbound_auth(
                    amount=Decimal("90"),
                    value_datetime=previous_day_value_datetime,
                ),
                self.outbound_auth_adjust(
                    amount=Decimal("40"),
                    value_datetime=value_datetime,
                ),
            ],
        )

        result = client_transaction_utils.sum_client_transactions(
            client_transactions={CTX_ID_1: ctx},
            cutoff_datetime=CUT_OFF_DATE,
            denomination=DEFAULT_DENOMINATION,
        )

        self.assertEqual(result, Balance(credit=Decimal(0), debit=Decimal(40), net=Decimal(-40)))

    @pytest.mark.unit
    def test_chainable_transactions_auth_adjust_decrease(self):
        """
        A negative auth adjustment to an outbound auth is considered as deposit
        """
        previous_day_value_datetime = CUT_OFF_DATE - timedelta(hours=23)
        value_datetime = CUT_OFF_DATE + timedelta(hours=1)

        ctx = ClientTransaction(
            client_transaction_id=CTX_ID_1,
            account_id=DEFAULT_ACCOUNT,
            posting_instructions=[
                self.outbound_auth(
                    amount=Decimal("90"),
                    value_datetime=previous_day_value_datetime,
                ),
                self.outbound_auth_adjust(
                    amount=Decimal("-40"),
                    value_datetime=value_datetime,
                ),
            ],
        )

        result = client_transaction_utils.sum_client_transactions(
            client_transactions={CTX_ID_1: ctx},
            cutoff_datetime=CUT_OFF_DATE,
            denomination=DEFAULT_DENOMINATION,
        )

        self.assertEqual(result, Balance(credit=Decimal(40), debit=Decimal(0), net=Decimal(40)))

    @pytest.mark.unit
    def test_chainable_settlements_cut_off_respected(self):
        """
        If an auth takes place before the cutoff time, the proposed
        settlement should still not impact the the sum as it
        was already accounted for at the time of the auth.
        """
        previous_day_value_datetime = CUT_OFF_DATE - timedelta(hours=23)
        value_datetime = CUT_OFF_DATE + timedelta(hours=1)

        ctx = ClientTransaction(
            client_transaction_id=CTX_ID_1,
            account_id=DEFAULT_ACCOUNT,
            posting_instructions=[
                self.outbound_auth(
                    amount=Decimal("90"),
                    value_datetime=previous_day_value_datetime,
                ),
                self.settle_outbound_auth(
                    unsettled_amount=Decimal("90"),
                    amount=Decimal("90"),
                    value_datetime=value_datetime,
                ),
            ],
            tside=self.tside,
        )
        result = client_transaction_utils.sum_client_transactions(
            client_transactions={CTX_ID_1: ctx},
            cutoff_datetime=CUT_OFF_DATE,
            denomination=DEFAULT_DENOMINATION,
        )
        self.assertEqual(result, Balance(credit=Decimal(0), debit=Decimal(0), net=Decimal(0)))

    @pytest.mark.unit
    def test_custom_instruction_client_transaction_has_zero_sum(self):
        ctx = ClientTransaction(
            client_transaction_id=CTX_ID_1,
            account_id=sentinel.account_id,
            posting_instructions=[
                self.custom_instruction(
                    postings=DEFAULT_POSTINGS,
                    value_datetime=CUT_OFF_DATE,
                ),
            ],
            tside=self.tside,
        )
        result = client_transaction_utils.sum_client_transactions(
            client_transactions={CTX_ID_1: ctx},
            cutoff_datetime=CUT_OFF_DATE,
            denomination=DEFAULT_DENOMINATION,
        )
        self.assertEqual(result, Balance(credit=Decimal(0), debit=Decimal(0), net=Decimal(0)))


class TestFilterClientTransactions(FeatureTest):
    def setUp(self) -> None:
        self.eligible_client_transaction = {
            CTX_ID_1: ClientTransaction(
                client_transaction_id=CTX_ID_1,
                account_id=DEFAULT_ACCOUNT,
                posting_instructions=[
                    self.outbound_hard_settlement(
                        amount=Decimal("1"),
                        value_datetime=CUT_OFF_DATE,
                        instruction_details={"type": "atm"},
                    )
                ],
                tside=self.tside,
            )
        }
        return super().setUp()

    @pytest.mark.unit
    def test_filter_with_matching_key_value(
        self,
    ):
        self.assertDictEqual(
            client_transaction_utils.filter_client_transactions(
                denomination=self.default_denomination,
                client_transactions=self.eligible_client_transaction,
                key="type",
                value="atm",
            ),
            self.eligible_client_transaction,
        )

    @pytest.mark.unit
    def test_filter_with_matching_key_value_and_multiple_txns(self):
        client_transactions = {
            CTX_ID_1: ClientTransaction(
                client_transaction_id=CTX_ID_1,
                account_id=DEFAULT_ACCOUNT,
                posting_instructions=[
                    self.outbound_hard_settlement(
                        amount=Decimal("1"),
                        value_datetime=CUT_OFF_DATE,
                        instruction_details={"type": "atm"},
                    )
                ],
                tside=self.tside,
            ),
            CTX_ID_2: ClientTransaction(
                client_transaction_id=CTX_ID_2,
                account_id=DEFAULT_ACCOUNT,
                posting_instructions=[
                    self.outbound_hard_settlement(
                        amount=Decimal("1"),
                        value_datetime=CUT_OFF_DATE,
                        instruction_details={"type": "atm"},
                    )
                ],
                tside=self.tside,
            ),
        }

        self.assertEqual(
            client_transaction_utils.filter_client_transactions(
                denomination=self.default_denomination,
                client_transactions=client_transactions,
                key="type",
                value="atm",
            ),
            client_transactions,
        )

    @pytest.mark.unit
    def test_filter_excludes_transaction_without_key(self):
        self.assertDictEqual(
            client_transaction_utils.filter_client_transactions(
                denomination=self.default_denomination,
                client_transactions=self.eligible_client_transaction,
                client_transaction_ids_to_ignore=set(),
                key="other_type",
                value="atm",
            ),
            {},
        )

    @pytest.mark.unit
    def test_filter_excludes_transaction_with_wrong_value(
        self,
    ):
        self.assertDictEqual(
            client_transaction_utils.filter_client_transactions(
                denomination=self.default_denomination,
                client_transactions=self.eligible_client_transaction,
                client_transaction_ids_to_ignore={""},
                key="type",
                value="not_atm",
            ),
            {},
        )

    @pytest.mark.unit
    def test_filter_excludes_transaction_with_id_to_ignore(
        self,
    ):
        self.assertDictEqual(
            client_transaction_utils.filter_client_transactions(
                denomination=self.default_denomination,
                client_transactions=self.eligible_client_transaction,
                client_transaction_ids_to_ignore={CTX_ID_1},
                key="type",
                value="atm",
            ),
            {},
        )

    @pytest.mark.unit
    def test_filter_excludes_released_transaction(self):
        client_transactions = {
            CTX_ID_1: ClientTransaction(
                client_transaction_id=CTX_ID_1,
                account_id=DEFAULT_ACCOUNT,
                posting_instructions=[
                    self.outbound_auth(
                        amount=Decimal("1"),
                        value_datetime=CUT_OFF_DATE,
                        instruction_details={"type": "atm"},
                    ),
                    self.release_outbound_auth(
                        unsettled_amount=Decimal("1"),
                    ),
                ],
                tside=self.tside,
            )
        }
        self.assertTrue(client_transactions[CTX_ID_1].released())

        self.assertDictEqual(
            client_transaction_utils.filter_client_transactions(
                denomination=self.default_denomination,
                client_transactions=client_transactions,
                client_transaction_ids_to_ignore=set(),
                key="type",
                value="atm",
            ),
            {},
        )

    @pytest.mark.unit
    def test_filter_excludes_custom_instructions(self):
        client_transactions = {
            CTX_ID_1: ClientTransaction(
                client_transaction_id=CTX_ID_1,
                account_id=sentinel.account_id,
                posting_instructions=[
                    self.custom_instruction(
                        amount=Decimal("1"),
                        postings=DEFAULT_POSTINGS,
                        value_datetime=CUT_OFF_DATE,
                        instruction_details={"type": "atm"},
                    ),
                ],
                tside=self.tside,
            )
        }

        self.assertEqual(
            client_transaction_utils.filter_client_transactions(
                denomination=self.default_denomination,
                client_transactions=client_transactions,
                client_transaction_ids_to_ignore={""},
                key="type",
                value="atm",
            ),
            {},
        )

    @pytest.mark.unit
    def test_filter_excludes_different_denomination(
        self,
    ):
        self.assertEqual(
            client_transaction_utils.filter_client_transactions(
                denomination="BLA",
                client_transactions=self.eligible_client_transaction,
                client_transaction_ids_to_ignore={""},
                key="type",
                value="atm",
            ),
            {},
        )


class TestSumDebitsByInstructionDetails(FeatureTest):
    @patch.object(client_transaction_utils, "sum_client_transactions")
    @patch.object(client_transaction_utils, "filter_client_transactions")
    @pytest.mark.unit
    def test_sum_debits_by_instruction_details(
        self, mock_filter_transactions: MagicMock, mock_sum_client_transaction: MagicMock
    ):
        mock_filter_transactions.return_value = sentinel.filtered_transactions
        mock_sum_client_transaction.return_value = Balance(
            credit=sentinel.net_credit, debit=sentinel.net_debit, net=sentinel.net
        )

        self.assertEqual(
            client_transaction_utils.sum_debits_by_instruction_details_key(
                denomination=sentinel.denomination,
                client_transactions=sentinel.client_transactions,
                client_transaction_ids_to_ignore=sentinel.client_transaction_ids_to_ignore,
                cutoff_datetime=sentinel.cutoff_datetime,
                key=sentinel.key,
                value=sentinel.value,
            ),
            sentinel.net_debit,
        )
        mock_filter_transactions.assert_called_once_with(
            denomination=sentinel.denomination,
            client_transactions=sentinel.client_transactions,
            client_transaction_ids_to_ignore=sentinel.client_transaction_ids_to_ignore,
            key=sentinel.key,
            value=sentinel.value,
        )
        mock_sum_client_transaction.assert_called_once_with(
            cutoff_datetime=sentinel.cutoff_datetime,
            client_transactions=sentinel.filtered_transactions,
            denomination=sentinel.denomination,
        )


# We should ideally test get_total_transaction_impact separately and mock here. At the moment
# it's tested within sum_client_transactions, so we're repeating some tests
@patch.object(client_transaction_utils, "filter_client_transactions")
class TestExtractDebitsByInstructionDetails(FeatureTest):
    def setUp(self) -> None:
        self.eligible_client_transaction = {
            CTX_ID_1: ClientTransaction(
                client_transaction_id=CTX_ID_1,
                account_id=DEFAULT_ACCOUNT,
                posting_instructions=[
                    self.outbound_hard_settlement(
                        amount=Decimal("1"),
                        value_datetime=CUT_OFF_DATE,
                        instruction_details={"type": "atm"},
                    )
                ],
                tside=self.tside,
            )
        }
        return super().setUp()

    @pytest.mark.unit
    def test_extract_debits_filters_client_transactions(
        self, mock_filter_client_transactions: MagicMock
    ):
        mock_filter_client_transactions.return_value = {}
        self.assertListEqual(
            client_transaction_utils.extract_debits_by_instruction_details_key(
                denomination=sentinel.denomination,
                client_transactions=sentinel.client_transactions,
                client_transaction_ids_to_ignore={CTX_ID_DUMMY},
                cutoff_datetime=sentinel.cutoff_datetime,
                key=sentinel.key,
                value=sentinel.value,
            ),
            [],
        )
        mock_filter_client_transactions.assert_called_once_with(
            denomination=sentinel.denomination,
            client_transactions=sentinel.client_transactions,
            client_transaction_ids_to_ignore={CTX_ID_DUMMY},
            key=sentinel.key,
            value=sentinel.value,
        )

    @pytest.mark.unit
    def test_extract_debits_outbound_auth_settle_across_cut_off(
        self, mock_filter_client_transactions: MagicMock
    ):
        # settle has no net debit impact to a previous auth
        auth_posting = self.outbound_auth(
            amount=Decimal("1"),
            value_datetime=CUT_OFF_DATE - timedelta(minutes=1),
            instruction_details={"type": "atm"},
        )
        settle_posting = self.settle_outbound_auth(
            amount=Decimal("1"),
            unsettled_amount=Decimal("1"),
            value_datetime=CUT_OFF_DATE + timedelta(minutes=1),
            instruction_details={"type": "atm"},
        )
        mock_filter_client_transactions.return_value = {
            CTX_ID_1: ClientTransaction(
                client_transaction_id=CTX_ID_1,
                account_id=DEFAULT_ACCOUNT,
                posting_instructions=[
                    auth_posting,
                    settle_posting,
                ],
                tside=self.tside,
            )
        }
        self.assertListEqual(
            client_transaction_utils.extract_debits_by_instruction_details_key(
                denomination=sentinel.denomination,
                client_transactions=sentinel.client_transactions,
                client_transaction_ids_to_ignore={CTX_ID_DUMMY},
                cutoff_datetime=CUT_OFF_DATE,
                key=sentinel.key,
                value=sentinel.value,
            ),
            [],
        )

    @pytest.mark.unit
    def test_extract_debits_outbound_auth_oversettle_across_cut_off(
        self, mock_filter_client_transactions: MagicMock
    ):
        # oversettle has net debit impact == over settlement amount
        auth_posting = self.outbound_auth(
            amount=Decimal("1"),
            value_datetime=CUT_OFF_DATE - timedelta(minutes=1),
            instruction_details={"type": "atm"},
        )
        settle_posting = self.settle_outbound_auth(
            amount=Decimal("2"),
            unsettled_amount=Decimal("1"),
            value_datetime=CUT_OFF_DATE + timedelta(minutes=1),
            instruction_details={"type": "atm"},
        )
        mock_filter_client_transactions.return_value = {
            CTX_ID_1: ClientTransaction(
                client_transaction_id=CTX_ID_1,
                account_id=DEFAULT_ACCOUNT,
                posting_instructions=[
                    auth_posting,
                    settle_posting,
                ],
                tside=self.tside,
            )
        }
        self.assertListEqual(
            client_transaction_utils.extract_debits_by_instruction_details_key(
                denomination=sentinel.denomination,
                client_transactions=sentinel.client_transactions,
                client_transaction_ids_to_ignore={CTX_ID_DUMMY},
                cutoff_datetime=CUT_OFF_DATE,
                key=sentinel.key,
                value=sentinel.value,
            ),
            [settle_posting],
        )

    @pytest.mark.unit
    def test_extract_debits_outbound_auth_settle_after_cut_off(
        self, mock_filter_client_transactions: MagicMock
    ):
        # auth/settle after cut-off has net debit impact == auth amount
        auth_posting = self.outbound_auth(
            amount=Decimal("1"),
            value_datetime=CUT_OFF_DATE,
            instruction_details={"type": "atm"},
        )
        settle_posting = self.settle_outbound_auth(
            amount=Decimal("1"),
            unsettled_amount=Decimal("1"),
            value_datetime=CUT_OFF_DATE + timedelta(minutes=1),
            instruction_details={"type": "atm"},
        )
        mock_filter_client_transactions.return_value = {
            CTX_ID_1: ClientTransaction(
                client_transaction_id=CTX_ID_1,
                account_id=DEFAULT_ACCOUNT,
                posting_instructions=[
                    auth_posting,
                    settle_posting,
                ],
                tside=self.tside,
            )
        }
        self.assertListEqual(
            client_transaction_utils.extract_debits_by_instruction_details_key(
                denomination=sentinel.denomination,
                client_transactions=sentinel.client_transactions,
                client_transaction_ids_to_ignore={CTX_ID_DUMMY},
                cutoff_datetime=CUT_OFF_DATE,
                key=sentinel.key,
                value=sentinel.value,
            ),
            [auth_posting],
        )

    @pytest.mark.unit
    def test_extract_debits_outbound_auth_over_settle_after_cut_off(
        self, mock_filter_client_transactions: MagicMock
    ):
        # auth over settle after cut-off has net debit impact == auth + over settlement amount
        auth_posting = self.outbound_auth(
            amount=Decimal("1"),
            value_datetime=CUT_OFF_DATE,
            instruction_details={"type": "atm"},
        )
        settle_posting = self.settle_outbound_auth(
            amount=Decimal("2"),
            unsettled_amount=Decimal("1"),
            value_datetime=CUT_OFF_DATE + timedelta(minutes=1),
            instruction_details={"type": "atm"},
        )
        mock_filter_client_transactions.return_value = {
            CTX_ID_1: ClientTransaction(
                client_transaction_id=CTX_ID_1,
                account_id=DEFAULT_ACCOUNT,
                posting_instructions=[
                    auth_posting,
                    settle_posting,
                ],
                tside=self.tside,
            )
        }
        self.assertListEqual(
            client_transaction_utils.extract_debits_by_instruction_details_key(
                denomination=sentinel.denomination,
                client_transactions=sentinel.client_transactions,
                client_transaction_ids_to_ignore={CTX_ID_DUMMY},
                cutoff_datetime=CUT_OFF_DATE,
                key=sentinel.key,
                value=sentinel.value,
            ),
            [auth_posting, settle_posting],
        )

    @pytest.mark.unit
    def test_extract_debits_outbound_auth_and_decrease_auth_adjustment_after_cut_off(
        self, mock_filter_client_transactions: MagicMock
    ):
        # decreasing auth is a net credit, so only the original auth is a net debit
        auth_posting = self.outbound_auth(
            amount=Decimal("1"),
            value_datetime=CUT_OFF_DATE,
            instruction_details={"type": "atm"},
        )
        adjust_posting = self.outbound_auth_adjust(
            amount=Decimal("-2"),
            value_datetime=CUT_OFF_DATE + timedelta(minutes=1),
            instruction_details={"type": "atm"},
        )
        mock_filter_client_transactions.return_value = {
            CTX_ID_1: ClientTransaction(
                client_transaction_id=CTX_ID_1,
                account_id=DEFAULT_ACCOUNT,
                posting_instructions=[
                    auth_posting,
                    adjust_posting,
                ],
                tside=self.tside,
            )
        }
        self.assertListEqual(
            client_transaction_utils.extract_debits_by_instruction_details_key(
                denomination=sentinel.denomination,
                client_transactions=sentinel.client_transactions,
                client_transaction_ids_to_ignore={CTX_ID_DUMMY},
                cutoff_datetime=CUT_OFF_DATE,
                key=sentinel.key,
                value=sentinel.value,
            ),
            [auth_posting],
        )

    @pytest.mark.unit
    def test_extract_debits_outbound_auth_and_increase_auth_adjustment_after_cut_off(
        self, mock_filter_client_transactions: MagicMock
    ):
        # increasing auth is a net debit, so both auth and adjustment are returned
        auth_posting = self.outbound_auth(
            amount=Decimal("1"),
            value_datetime=CUT_OFF_DATE,
            instruction_details={"type": "atm"},
        )
        adjust_posting = self.outbound_auth_adjust(
            amount=Decimal("2"),
            value_datetime=CUT_OFF_DATE + timedelta(minutes=1),
            instruction_details={"type": "atm"},
        )
        mock_filter_client_transactions.return_value = {
            CTX_ID_1: ClientTransaction(
                client_transaction_id=CTX_ID_1,
                account_id=DEFAULT_ACCOUNT,
                posting_instructions=[
                    auth_posting,
                    adjust_posting,
                ],
                tside=self.tside,
            )
        }
        self.assertListEqual(
            client_transaction_utils.extract_debits_by_instruction_details_key(
                denomination=sentinel.denomination,
                client_transactions=sentinel.client_transactions,
                client_transaction_ids_to_ignore={CTX_ID_DUMMY},
                cutoff_datetime=CUT_OFF_DATE,
                key=sentinel.key,
                value=sentinel.value,
            ),
            [auth_posting, adjust_posting],
        )

    @pytest.mark.unit
    def test_extract_debits_outbound_hard_settle_before_cut_off(
        self, mock_filter_client_transactions: MagicMock
    ):
        # outbound hard settlement before cut-off is net 0 after the cut-off
        outbound_hard_settle_posting = self.outbound_hard_settlement(
            amount=Decimal("1"),
            value_datetime=CUT_OFF_DATE - timedelta(minutes=1),
            instruction_details={"type": "atm"},
        )

        mock_filter_client_transactions.return_value = {
            CTX_ID_1: ClientTransaction(
                client_transaction_id=CTX_ID_1,
                account_id=DEFAULT_ACCOUNT,
                posting_instructions=[
                    outbound_hard_settle_posting,
                ],
                tside=self.tside,
            )
        }
        self.assertListEqual(
            client_transaction_utils.extract_debits_by_instruction_details_key(
                denomination=sentinel.denomination,
                client_transactions=sentinel.client_transactions,
                client_transaction_ids_to_ignore={CTX_ID_DUMMY},
                cutoff_datetime=CUT_OFF_DATE,
                key=sentinel.key,
                value=sentinel.value,
            ),
            [],
        )

    @pytest.mark.unit
    def test_extract_debits_outbound_hard_settle_after_cut_off(
        self, mock_filter_client_transactions: MagicMock
    ):
        # outbound hard settlement after cut-off is net debit after the cut-off for hard settlement
        # amount
        outbound_hard_settle_posting = self.outbound_hard_settlement(
            amount=Decimal("1"),
            value_datetime=CUT_OFF_DATE + timedelta(minutes=1),
            instruction_details={"type": "atm"},
        )

        mock_filter_client_transactions.return_value = {
            CTX_ID_1: ClientTransaction(
                client_transaction_id=CTX_ID_1,
                account_id=DEFAULT_ACCOUNT,
                posting_instructions=[
                    outbound_hard_settle_posting,
                ],
                tside=self.tside,
            )
        }
        self.assertListEqual(
            client_transaction_utils.extract_debits_by_instruction_details_key(
                denomination=sentinel.denomination,
                client_transactions=sentinel.client_transactions,
                client_transaction_ids_to_ignore={CTX_ID_DUMMY},
                cutoff_datetime=CUT_OFF_DATE,
                key=sentinel.key,
                value=sentinel.value,
            ),
            [outbound_hard_settle_posting],
        )

    @pytest.mark.unit
    def test_extract_debits_inbound_auth_settle_across_cut_off(
        self, mock_filter_client_transactions: MagicMock
    ):
        # inbound postings are credits and are never included
        auth_posting = self.inbound_auth(
            amount=Decimal("1"),
            value_datetime=CUT_OFF_DATE - timedelta(minutes=1),
            instruction_details={"type": "atm"},
        )
        settle_posting = self.settle_inbound_auth(
            amount=Decimal("1"),
            unsettled_amount=Decimal("1"),
            value_datetime=CUT_OFF_DATE + timedelta(minutes=1),
            instruction_details={"type": "atm"},
        )
        mock_filter_client_transactions.return_value = {
            CTX_ID_1: ClientTransaction(
                client_transaction_id=CTX_ID_1,
                account_id=DEFAULT_ACCOUNT,
                posting_instructions=[
                    auth_posting,
                    settle_posting,
                ],
                tside=self.tside,
            )
        }
        self.assertListEqual(
            client_transaction_utils.extract_debits_by_instruction_details_key(
                denomination=sentinel.denomination,
                client_transactions=sentinel.client_transactions,
                client_transaction_ids_to_ignore={CTX_ID_DUMMY},
                cutoff_datetime=CUT_OFF_DATE,
                key=sentinel.key,
                value=sentinel.value,
            ),
            [],
        )

    @pytest.mark.unit
    def test_extract_debits_inbound_auth_settle_after_cut_off(
        self, mock_filter_client_transactions: MagicMock
    ):
        # inbound postings are credits and are never included

        auth_posting = self.inbound_auth(
            amount=Decimal("1"),
            value_datetime=CUT_OFF_DATE,
            instruction_details={"type": "atm"},
        )
        settle_posting = self.settle_inbound_auth(
            amount=Decimal("1"),
            unsettled_amount=Decimal("1"),
            value_datetime=CUT_OFF_DATE + timedelta(minutes=1),
            instruction_details={"type": "atm"},
        )
        mock_filter_client_transactions.return_value = {
            CTX_ID_1: ClientTransaction(
                client_transaction_id=CTX_ID_1,
                account_id=DEFAULT_ACCOUNT,
                posting_instructions=[
                    auth_posting,
                    settle_posting,
                ],
                tside=self.tside,
            )
        }
        self.assertListEqual(
            client_transaction_utils.extract_debits_by_instruction_details_key(
                denomination=sentinel.denomination,
                client_transactions=sentinel.client_transactions,
                client_transaction_ids_to_ignore={CTX_ID_DUMMY},
                cutoff_datetime=CUT_OFF_DATE,
                key=sentinel.key,
                value=sentinel.value,
            ),
            [],
        )

    @pytest.mark.unit
    def test_extract_debits_inbound_hard_settle_before_cut_off(
        self, mock_filter_client_transactions: MagicMock
    ):
        # inbound postings are credits and are never included
        inbound_hard_settle_posting = self.inbound_hard_settlement(
            amount=Decimal("1"),
            value_datetime=CUT_OFF_DATE - timedelta(minutes=1),
            instruction_details={"type": "atm"},
        )

        mock_filter_client_transactions.return_value = {
            CTX_ID_1: ClientTransaction(
                client_transaction_id=CTX_ID_1,
                account_id=DEFAULT_ACCOUNT,
                posting_instructions=[
                    inbound_hard_settle_posting,
                ],
                tside=self.tside,
            )
        }
        self.assertListEqual(
            client_transaction_utils.extract_debits_by_instruction_details_key(
                denomination=sentinel.denomination,
                client_transactions=sentinel.client_transactions,
                client_transaction_ids_to_ignore={CTX_ID_DUMMY},
                cutoff_datetime=CUT_OFF_DATE,
                key=sentinel.key,
                value=sentinel.value,
            ),
            [],
        )

    @pytest.mark.unit
    def test_extract_debits_inbound_hard_settle_after_cut_off(
        self, mock_filter_client_transactions: MagicMock
    ):
        # inbound postings are credits and are never included
        inbound_hard_settle_posting = self.inbound_hard_settlement(
            amount=Decimal("1"),
            value_datetime=CUT_OFF_DATE + timedelta(minutes=1),
            instruction_details={"type": "atm"},
        )

        mock_filter_client_transactions.return_value = {
            CTX_ID_1: ClientTransaction(
                client_transaction_id=CTX_ID_1,
                account_id=DEFAULT_ACCOUNT,
                posting_instructions=[
                    inbound_hard_settle_posting,
                ],
                tside=self.tside,
            )
        }
        self.assertListEqual(
            client_transaction_utils.extract_debits_by_instruction_details_key(
                denomination=sentinel.denomination,
                client_transactions=sentinel.client_transactions,
                client_transaction_ids_to_ignore={CTX_ID_DUMMY},
                cutoff_datetime=CUT_OFF_DATE,
                key=sentinel.key,
                value=sentinel.value,
            ),
            [],
        )

    @pytest.mark.unit
    def test_extract_debits_custom_instruction(self, mock_filter_client_transactions: MagicMock):
        # custom instructions have none effects so we do not try to derive intent and classify them
        # as a debit
        mock_filter_client_transactions.return_value = {
            CTX_ID_1: ClientTransaction(
                client_transaction_id=CTX_ID_1,
                account_id=sentinel.account_id,
                posting_instructions=[
                    self.custom_instruction(
                        amount=Decimal("1"),
                        postings=DEFAULT_POSTINGS,
                        value_datetime=CUT_OFF_DATE,
                        instruction_details={"type": "atm"},
                    ),
                ],
                tside=self.tside,
            )
        }
        self.assertListEqual(
            client_transaction_utils.extract_debits_by_instruction_details_key(
                denomination=sentinel.denomination,
                client_transactions=sentinel.client_transactions,
                client_transaction_ids_to_ignore={CTX_ID_DUMMY},
                cutoff_datetime=CUT_OFF_DATE,
                key=sentinel.key,
                value=sentinel.value,
            ),
            [],
        )


class TestFilterClientTransactionsByType(FeatureTest):
    def setUp(self) -> None:
        self.eligible_client_transaction = {
            CTX_ID_1: ClientTransaction(
                client_transaction_id=CTX_ID_1,
                account_id=DEFAULT_ACCOUNT,
                posting_instructions=[
                    self.outbound_hard_settlement(
                        amount=Decimal("1"),
                        value_datetime=CUT_OFF_DATE,
                        instruction_details={"type": "atm"},
                    )
                ],
                tside=self.tside,
            )
        }
        return super().setUp()

    @pytest.mark.unit
    def test_filter_with_matching_key_value(
        self,
    ):
        self.assertDictEqual(
            client_transaction_utils.filter_client_transactions_by_type(
                denomination=self.default_denomination,
                client_transactions=self.eligible_client_transaction,
                key="type",
                values=["atm"],
            ),
            {"atm": self.eligible_client_transaction},
        )

    @pytest.mark.unit
    def test_filter_with_matching_key_value_and_multiple_txns(self):
        client_transactions = {
            CTX_ID_1: ClientTransaction(
                client_transaction_id=CTX_ID_1,
                account_id=DEFAULT_ACCOUNT,
                posting_instructions=[
                    self.outbound_hard_settlement(
                        amount=Decimal("1"),
                        value_datetime=CUT_OFF_DATE,
                        instruction_details={"type": "atm"},
                    )
                ],
                tside=self.tside,
            ),
            CTX_ID_2: ClientTransaction(
                client_transaction_id=CTX_ID_2,
                account_id=DEFAULT_ACCOUNT,
                posting_instructions=[
                    self.outbound_hard_settlement(
                        amount=Decimal("1"),
                        value_datetime=CUT_OFF_DATE,
                        instruction_details={"type": "atm"},
                    )
                ],
                tside=self.tside,
            ),
        }

        self.assertEqual(
            client_transaction_utils.filter_client_transactions_by_type(
                denomination=self.default_denomination,
                client_transactions=client_transactions,
                key="type",
                values=["atm"],
            ),
            {"atm": client_transactions},
        )

    @pytest.mark.unit
    def test_filter_excludes_transaction_without_key(self):
        self.assertDictEqual(
            client_transaction_utils.filter_client_transactions_by_type(
                denomination=self.default_denomination,
                client_transactions=self.eligible_client_transaction,
                client_transaction_ids_to_ignore=set(),
                key="other_type",
                values=["atm"],
            ),
            {"atm": {}},
        )

    @pytest.mark.unit
    def test_filter_excludes_transaction_with_wrong_value(
        self,
    ):
        self.assertDictEqual(
            client_transaction_utils.filter_client_transactions_by_type(
                denomination=self.default_denomination,
                client_transactions=self.eligible_client_transaction,
                client_transaction_ids_to_ignore={""},
                key="type",
                values=["not_atm"],
            ),
            {"not_atm": {}},
        )

    @pytest.mark.unit
    def test_filter_excludes_transaction_with_id_to_ignore(
        self,
    ):
        self.assertDictEqual(
            client_transaction_utils.filter_client_transactions_by_type(
                denomination=self.default_denomination,
                client_transactions=self.eligible_client_transaction,
                client_transaction_ids_to_ignore={CTX_ID_1},
                key="type",
                values=["atm"],
            ),
            {"atm": {}},
        )

    @pytest.mark.unit
    def test_filter_excludes_released_transaction(self):
        client_transactions = {
            CTX_ID_1: ClientTransaction(
                client_transaction_id=CTX_ID_1,
                account_id=DEFAULT_ACCOUNT,
                posting_instructions=[
                    self.outbound_auth(
                        amount=Decimal("1"),
                        value_datetime=CUT_OFF_DATE,
                        instruction_details={"type": "atm"},
                    ),
                    self.release_outbound_auth(
                        unsettled_amount=Decimal("1"),
                    ),
                ],
                tside=self.tside,
            )
        }
        self.assertTrue(client_transactions[CTX_ID_1].released())

        self.assertDictEqual(
            client_transaction_utils.filter_client_transactions_by_type(
                denomination=self.default_denomination,
                client_transactions=client_transactions,
                client_transaction_ids_to_ignore=set(),
                key="type",
                values=["atm"],
            ),
            {"atm": {}},
        )

    @pytest.mark.unit
    def test_filter_excludes_custom_instructions(self):
        client_transactions = {
            CTX_ID_1: ClientTransaction(
                client_transaction_id=CTX_ID_1,
                account_id=sentinel.account_id,
                posting_instructions=[
                    self.custom_instruction(
                        amount=Decimal("1"),
                        postings=DEFAULT_POSTINGS,
                        value_datetime=CUT_OFF_DATE,
                        instruction_details={"type": "atm"},
                    ),
                ],
                tside=self.tside,
            )
        }

        self.assertEqual(
            client_transaction_utils.filter_client_transactions_by_type(
                denomination=self.default_denomination,
                client_transactions=client_transactions,
                client_transaction_ids_to_ignore={""},
                key="type",
                values=["atm"],
            ),
            {"atm": {}},
        )

    @pytest.mark.unit
    def test_filter_excludes_different_denomination(
        self,
    ):
        self.assertEqual(
            client_transaction_utils.filter_client_transactions_by_type(
                denomination="BLA",
                client_transactions=self.eligible_client_transaction,
                client_transaction_ids_to_ignore={""},
                key="type",
                values=["atm"],
            ),
            {"atm": {}},
        )

    @pytest.mark.unit
    def test_filter_with_multiple_eligible_types(self):
        atm_client_transactions = {
            CTX_ID_1: ClientTransaction(
                client_transaction_id=CTX_ID_1,
                account_id=DEFAULT_ACCOUNT,
                posting_instructions=[
                    self.outbound_hard_settlement(
                        amount=Decimal("1"),
                        value_datetime=CUT_OFF_DATE,
                        instruction_details={"type": "atm"},
                    )
                ],
                tside=self.tside,
            ),
            CTX_ID_2: ClientTransaction(
                client_transaction_id=CTX_ID_2,
                account_id=DEFAULT_ACCOUNT,
                posting_instructions=[
                    self.outbound_hard_settlement(
                        amount=Decimal("1"),
                        value_datetime=CUT_OFF_DATE,
                        instruction_details={"type": "atm"},
                    )
                ],
                tside=self.tside,
            ),
        }
        pos_client_transactions = {
            CTX_ID_3: ClientTransaction(
                client_transaction_id=CTX_ID_3,
                account_id=DEFAULT_ACCOUNT,
                posting_instructions=[
                    self.outbound_hard_settlement(
                        amount=Decimal("1"),
                        value_datetime=CUT_OFF_DATE,
                        instruction_details={"type": "pos"},
                    )
                ],
                tside=self.tside,
            ),
        }
        client_transactions = atm_client_transactions | pos_client_transactions
        self.assertEqual(
            client_transaction_utils.filter_client_transactions_by_type(
                denomination=self.default_denomination,
                client_transactions=client_transactions,
                key="type",
                values=["atm", "pos", "other"],
            ),
            {"atm": atm_client_transactions, "pos": pos_client_transactions, "other": {}},
        )


class TestSumDebitsByType(FeatureTest):
    @patch.object(client_transaction_utils, "sum_client_transactions")
    @patch.object(client_transaction_utils, "filter_client_transactions_by_type")
    @pytest.mark.unit
    def test_sum_debits_by_instruction_details(
        self, mock_filter_transactions: MagicMock, mock_sum_client_transaction: MagicMock
    ):
        mock_filter_transactions.return_value = {
            sentinel.value_1: sentinel.filtered_transactions_1,
            sentinel.value_2: sentinel.filtered_transactions_2,
        }
        mock_sum_client_transaction.side_effect = [
            Balance(credit=sentinel.net_credit_1, debit=sentinel.net_debit_1),
            Balance(credit=sentinel.net_credit_2, debit=sentinel.net_debit_2),
        ]

        self.assertDictEqual(
            client_transaction_utils.sum_debits_by_type(
                denomination=sentinel.denomination,
                client_transactions=sentinel.client_transactions,
                client_transaction_ids_to_ignore=sentinel.client_transaction_ids_to_ignore,
                cutoff_datetime=sentinel.cutoff_datetime,
                key=sentinel.key,
                values=[sentinel.value_1, sentinel.value_2],
            ),
            {sentinel.value_1: sentinel.net_debit_1, sentinel.value_2: sentinel.net_debit_2},
        )
        mock_filter_transactions.assert_called_once_with(
            denomination=sentinel.denomination,
            client_transactions=sentinel.client_transactions,
            client_transaction_ids_to_ignore=sentinel.client_transaction_ids_to_ignore,
            key=sentinel.key,
            values=[sentinel.value_1, sentinel.value_2],
        )
        mock_sum_client_transaction.assert_has_calls(
            calls=[
                call(
                    cutoff_datetime=sentinel.cutoff_datetime,
                    client_transactions=sentinel.filtered_transactions_1,
                    denomination=sentinel.denomination,
                ),
                call(
                    cutoff_datetime=sentinel.cutoff_datetime,
                    client_transactions=sentinel.filtered_transactions_2,
                    denomination=sentinel.denomination,
                ),
            ]
        )


# We should ideally test get_total_transaction_impact separately and mock here. At the moment
# it's tested within sum_client_transactions, so we're repeating some tests
@patch.object(client_transaction_utils, "filter_client_transactions_by_type")
class TestExtractDebitsByType(FeatureTest):
    @pytest.mark.unit
    def test_extract_debits_filters_client_transactions(
        self, mock_filter_client_transactions: MagicMock
    ):
        mock_filter_client_transactions.return_value = {}
        self.assertDictEqual(
            client_transaction_utils.extract_debits_by_type(
                denomination=sentinel.denomination,
                client_transactions=sentinel.client_transactions,
                client_transaction_ids_to_ignore={CTX_ID_DUMMY},
                cutoff_datetime=sentinel.cutoff_datetime,
                key=sentinel.key,
                values=[sentinel.value],
            ),
            {},
        )
        mock_filter_client_transactions.assert_called_once_with(
            denomination=sentinel.denomination,
            client_transactions=sentinel.client_transactions,
            client_transaction_ids_to_ignore={CTX_ID_DUMMY},
            key=sentinel.key,
            values=[sentinel.value],
        )

    @pytest.mark.unit
    def test_extract_debits_outbound_auth_settle_across_cut_off(
        self, mock_filter_client_transactions: MagicMock
    ):
        # settle has no net debit impact to a previous auth
        auth_posting = self.outbound_auth(
            amount=Decimal("1"),
            value_datetime=CUT_OFF_DATE - timedelta(minutes=1),
            instruction_details={"type": "atm"},
        )
        settle_posting = self.settle_outbound_auth(
            amount=Decimal("1"),
            unsettled_amount=Decimal("1"),
            value_datetime=CUT_OFF_DATE + timedelta(minutes=1),
            instruction_details={"type": "atm"},
        )
        mock_filter_client_transactions.return_value = {
            "atm": {
                CTX_ID_1: ClientTransaction(
                    client_transaction_id=CTX_ID_1,
                    account_id=DEFAULT_ACCOUNT,
                    posting_instructions=[
                        auth_posting,
                        settle_posting,
                    ],
                    tside=self.tside,
                )
            }
        }
        self.assertDictEqual(
            client_transaction_utils.extract_debits_by_type(
                denomination=sentinel.denomination,
                client_transactions=sentinel.client_transactions,
                client_transaction_ids_to_ignore={CTX_ID_DUMMY},
                cutoff_datetime=CUT_OFF_DATE,
                key=sentinel.key,
                values=["atm"],
            ),
            {"atm": {}},
        )

    @pytest.mark.unit
    def test_extract_debits_outbound_auth_oversettle_across_cut_off(
        self, mock_filter_client_transactions: MagicMock
    ):
        # oversettle has net debit impact == over settlement amount
        auth_posting = self.outbound_auth(
            amount=Decimal("1"),
            value_datetime=CUT_OFF_DATE - timedelta(minutes=1),
            instruction_details={"type": "atm"},
        )
        settle_posting = self.settle_outbound_auth(
            amount=Decimal("2"),
            unsettled_amount=Decimal("1"),
            value_datetime=CUT_OFF_DATE + timedelta(minutes=1),
            instruction_details={"type": "atm"},
        )
        mock_filter_client_transactions.return_value = {
            "atm": {
                CTX_ID_1: ClientTransaction(
                    client_transaction_id=CTX_ID_1,
                    account_id=DEFAULT_ACCOUNT,
                    posting_instructions=[
                        auth_posting,
                        settle_posting,
                    ],
                    tside=self.tside,
                )
            }
        }
        self.assertDictEqual(
            client_transaction_utils.extract_debits_by_type(
                denomination=sentinel.denomination,
                client_transactions=sentinel.client_transactions,
                client_transaction_ids_to_ignore={CTX_ID_DUMMY},
                cutoff_datetime=CUT_OFF_DATE,
                key=sentinel.key,
                values=["atm"],
            ),
            {"atm": {"client_id_MOCK_POSTING_2019-01-01 00:01:00+00:00": settle_posting}},
        )

    @pytest.mark.unit
    def test_extract_debits_outbound_auth_settle_after_cut_off(
        self, mock_filter_client_transactions: MagicMock
    ):
        # auth/settle after cut-off has net debit impact == auth amount
        auth_posting = self.outbound_auth(
            amount=Decimal("1"),
            value_datetime=CUT_OFF_DATE,
            instruction_details={"type": "atm"},
        )
        settle_posting = self.settle_outbound_auth(
            amount=Decimal("1"),
            unsettled_amount=Decimal("1"),
            value_datetime=CUT_OFF_DATE + timedelta(minutes=1),
            instruction_details={"type": "atm"},
        )
        mock_filter_client_transactions.return_value = {
            "atm": {
                CTX_ID_1: ClientTransaction(
                    client_transaction_id=CTX_ID_1,
                    account_id=DEFAULT_ACCOUNT,
                    posting_instructions=[
                        auth_posting,
                        settle_posting,
                    ],
                    tside=self.tside,
                )
            }
        }
        self.assertDictEqual(
            client_transaction_utils.extract_debits_by_type(
                denomination=sentinel.denomination,
                client_transactions=sentinel.client_transactions,
                client_transaction_ids_to_ignore={CTX_ID_DUMMY},
                cutoff_datetime=CUT_OFF_DATE,
                key=sentinel.key,
                values=["atm"],
            ),
            {"atm": {"client_id_MOCK_POSTING_2019-01-01 00:00:00+00:00": auth_posting}},
        )

    @pytest.mark.unit
    def test_extract_debits_outbound_auth_over_settle_after_cut_off(
        self, mock_filter_client_transactions: MagicMock
    ):
        # auth over settle after cut-off has net debit impact == auth + over settlement amount
        auth_posting = self.outbound_auth(
            amount=Decimal("1"),
            value_datetime=CUT_OFF_DATE,
            instruction_details={"type": "atm"},
        )
        settle_posting = self.settle_outbound_auth(
            amount=Decimal("2"),
            unsettled_amount=Decimal("1"),
            value_datetime=CUT_OFF_DATE + timedelta(minutes=1),
            instruction_details={"type": "atm"},
        )
        mock_filter_client_transactions.return_value = {
            "atm": {
                CTX_ID_1: ClientTransaction(
                    client_transaction_id=CTX_ID_1,
                    account_id=DEFAULT_ACCOUNT,
                    posting_instructions=[
                        auth_posting,
                        settle_posting,
                    ],
                    tside=self.tside,
                )
            }
        }
        self.assertDictEqual(
            client_transaction_utils.extract_debits_by_type(
                denomination=sentinel.denomination,
                client_transactions=sentinel.client_transactions,
                client_transaction_ids_to_ignore={CTX_ID_DUMMY},
                cutoff_datetime=CUT_OFF_DATE,
                key=sentinel.key,
                values=["atm"],
            ),
            {
                "atm": {
                    "client_id_MOCK_POSTING_2019-01-01 00:00:00+00:00": auth_posting,
                    "client_id_MOCK_POSTING_2019-01-01 00:01:00+00:00": settle_posting,
                }
            },
        )

    @pytest.mark.unit
    def test_extract_debits_outbound_auth_and_decrease_auth_adjustment_after_cut_off(
        self, mock_filter_client_transactions: MagicMock
    ):
        # decreasing auth is a net credit, so only the original auth is a net debit
        auth_posting = self.outbound_auth(
            amount=Decimal("1"),
            value_datetime=CUT_OFF_DATE,
            instruction_details={"type": "atm"},
        )
        adjust_posting = self.outbound_auth_adjust(
            amount=Decimal("-2"),
            value_datetime=CUT_OFF_DATE + timedelta(minutes=1),
            instruction_details={"type": "atm"},
        )
        mock_filter_client_transactions.return_value = {
            "atm": {
                CTX_ID_1: ClientTransaction(
                    client_transaction_id=CTX_ID_1,
                    account_id=DEFAULT_ACCOUNT,
                    posting_instructions=[
                        auth_posting,
                        adjust_posting,
                    ],
                    tside=self.tside,
                )
            }
        }
        self.assertDictEqual(
            client_transaction_utils.extract_debits_by_type(
                denomination=sentinel.denomination,
                client_transactions=sentinel.client_transactions,
                client_transaction_ids_to_ignore={CTX_ID_DUMMY},
                cutoff_datetime=CUT_OFF_DATE,
                key=sentinel.key,
                values=["atm"],
            ),
            {
                "atm": {
                    "client_id_MOCK_POSTING_2019-01-01 00:00:00+00:00": auth_posting,
                }
            },
        )

    @pytest.mark.unit
    def test_extract_debits_outbound_auth_and_increase_auth_adjustment_after_cut_off(
        self, mock_filter_client_transactions: MagicMock
    ):
        # increasing auth is a net debit, so both auth and adjustment are returned
        auth_posting = self.outbound_auth(
            amount=Decimal("1"),
            value_datetime=CUT_OFF_DATE,
            instruction_details={"type": "atm"},
        )
        adjust_posting = self.outbound_auth_adjust(
            amount=Decimal("2"),
            value_datetime=CUT_OFF_DATE + timedelta(minutes=1),
            instruction_details={"type": "atm"},
        )
        mock_filter_client_transactions.return_value = {
            "atm": {
                CTX_ID_1: ClientTransaction(
                    client_transaction_id=CTX_ID_1,
                    account_id=DEFAULT_ACCOUNT,
                    posting_instructions=[
                        auth_posting,
                        adjust_posting,
                    ],
                    tside=self.tside,
                )
            }
        }
        self.assertDictEqual(
            client_transaction_utils.extract_debits_by_type(
                denomination=sentinel.denomination,
                client_transactions=sentinel.client_transactions,
                client_transaction_ids_to_ignore={CTX_ID_DUMMY},
                cutoff_datetime=CUT_OFF_DATE,
                key=sentinel.key,
                values=["atm"],
            ),
            {
                "atm": {
                    "client_id_MOCK_POSTING_2019-01-01 00:00:00+00:00": auth_posting,
                    "client_id_MOCK_POSTING_2019-01-01 00:01:00+00:00": adjust_posting,
                }
            },
        )

    @pytest.mark.unit
    def test_extract_debits_outbound_hard_settle_before_cut_off(
        self, mock_filter_client_transactions: MagicMock
    ):
        # outbound hard settlement before cut-off is net 0 after the cut-off
        outbound_hard_settle_posting = self.outbound_hard_settlement(
            amount=Decimal("1"),
            value_datetime=CUT_OFF_DATE - timedelta(minutes=1),
            instruction_details={"type": "atm"},
        )

        mock_filter_client_transactions.return_value = {
            "atm": {
                CTX_ID_1: ClientTransaction(
                    client_transaction_id=CTX_ID_1,
                    account_id=DEFAULT_ACCOUNT,
                    posting_instructions=[
                        outbound_hard_settle_posting,
                    ],
                    tside=self.tside,
                )
            }
        }
        self.assertDictEqual(
            client_transaction_utils.extract_debits_by_type(
                denomination=sentinel.denomination,
                client_transactions=sentinel.client_transactions,
                client_transaction_ids_to_ignore={CTX_ID_DUMMY},
                cutoff_datetime=CUT_OFF_DATE,
                key=sentinel.key,
                values=["atm"],
            ),
            {"atm": {}},
        )

    @pytest.mark.unit
    def test_extract_debits_outbound_hard_settle_after_cut_off(
        self, mock_filter_client_transactions: MagicMock
    ):
        # outbound hard settlement after cut-off is net debit after the cut-off for hard settlement
        # amount
        outbound_hard_settle_posting = self.outbound_hard_settlement(
            amount=Decimal("1"),
            value_datetime=CUT_OFF_DATE + timedelta(minutes=1),
            instruction_details={"type": "atm"},
        )

        mock_filter_client_transactions.return_value = {
            "atm": {
                CTX_ID_1: ClientTransaction(
                    client_transaction_id=CTX_ID_1,
                    account_id=DEFAULT_ACCOUNT,
                    posting_instructions=[
                        outbound_hard_settle_posting,
                    ],
                    tside=self.tside,
                )
            }
        }
        self.assertDictEqual(
            client_transaction_utils.extract_debits_by_type(
                denomination=sentinel.denomination,
                client_transactions=sentinel.client_transactions,
                client_transaction_ids_to_ignore={CTX_ID_DUMMY},
                cutoff_datetime=CUT_OFF_DATE,
                key=sentinel.key,
                values=["atm"],
            ),
            {
                "atm": {
                    "client_id_MOCK_POSTING_2019-01-01 00:01:00+00:00": (
                        outbound_hard_settle_posting
                    )
                }
            },
        )

    @pytest.mark.unit
    def test_extract_debits_inbound_auth_settle_across_cut_off(
        self, mock_filter_client_transactions: MagicMock
    ):
        # inbound postings are credits and are never included
        auth_posting = self.inbound_auth(
            amount=Decimal("1"),
            value_datetime=CUT_OFF_DATE - timedelta(minutes=1),
            instruction_details={"type": "atm"},
        )
        settle_posting = self.settle_inbound_auth(
            amount=Decimal("1"),
            unsettled_amount=Decimal("1"),
            value_datetime=CUT_OFF_DATE + timedelta(minutes=1),
            instruction_details={"type": "atm"},
        )
        mock_filter_client_transactions.return_value = {
            "atm": {
                CTX_ID_1: ClientTransaction(
                    client_transaction_id=CTX_ID_1,
                    account_id=DEFAULT_ACCOUNT,
                    posting_instructions=[
                        auth_posting,
                        settle_posting,
                    ],
                    tside=self.tside,
                )
            }
        }
        self.assertDictEqual(
            client_transaction_utils.extract_debits_by_type(
                denomination=sentinel.denomination,
                client_transactions=sentinel.client_transactions,
                client_transaction_ids_to_ignore={CTX_ID_DUMMY},
                cutoff_datetime=CUT_OFF_DATE,
                key=sentinel.key,
                values=["atm"],
            ),
            {"atm": {}},
        )

    @pytest.mark.unit
    def test_extract_debits_inbound_auth_settle_after_cut_off(
        self, mock_filter_client_transactions: MagicMock
    ):
        # inbound postings are credits and are never included

        auth_posting = self.inbound_auth(
            amount=Decimal("1"),
            value_datetime=CUT_OFF_DATE,
            instruction_details={"type": "atm"},
        )
        settle_posting = self.settle_inbound_auth(
            amount=Decimal("1"),
            unsettled_amount=Decimal("1"),
            value_datetime=CUT_OFF_DATE + timedelta(minutes=1),
            instruction_details={"type": "atm"},
        )
        mock_filter_client_transactions.return_value = {
            "atm": {
                CTX_ID_1: ClientTransaction(
                    client_transaction_id=CTX_ID_1,
                    account_id=DEFAULT_ACCOUNT,
                    posting_instructions=[
                        auth_posting,
                        settle_posting,
                    ],
                    tside=self.tside,
                )
            }
        }
        self.assertDictEqual(
            client_transaction_utils.extract_debits_by_type(
                denomination=sentinel.denomination,
                client_transactions=sentinel.client_transactions,
                client_transaction_ids_to_ignore={CTX_ID_DUMMY},
                cutoff_datetime=CUT_OFF_DATE,
                key=sentinel.key,
                values=["atm"],
            ),
            {"atm": {}},
        )

    @pytest.mark.unit
    def test_extract_debits_inbound_hard_settle_before_cut_off(
        self, mock_filter_client_transactions: MagicMock
    ):
        # inbound postings are credits and are never included
        inbound_hard_settle_posting = self.inbound_hard_settlement(
            amount=Decimal("1"),
            value_datetime=CUT_OFF_DATE - timedelta(minutes=1),
            instruction_details={"type": "atm"},
        )

        mock_filter_client_transactions.return_value = {
            "atm": {
                CTX_ID_1: ClientTransaction(
                    client_transaction_id=CTX_ID_1,
                    account_id=DEFAULT_ACCOUNT,
                    posting_instructions=[
                        inbound_hard_settle_posting,
                    ],
                    tside=self.tside,
                )
            }
        }
        self.assertDictEqual(
            client_transaction_utils.extract_debits_by_type(
                denomination=sentinel.denomination,
                client_transactions=sentinel.client_transactions,
                client_transaction_ids_to_ignore={CTX_ID_DUMMY},
                cutoff_datetime=CUT_OFF_DATE,
                key=sentinel.key,
                values=["atm"],
            ),
            {"atm": {}},
        )

    @pytest.mark.unit
    def test_extract_debits_inbound_hard_settle_after_cut_off(
        self, mock_filter_client_transactions: MagicMock
    ):
        # inbound postings are credits and are never included
        inbound_hard_settle_posting = self.inbound_hard_settlement(
            amount=Decimal("1"),
            value_datetime=CUT_OFF_DATE + timedelta(minutes=1),
            instruction_details={"type": "atm"},
        )

        mock_filter_client_transactions.return_value = {
            "atm": {
                CTX_ID_1: ClientTransaction(
                    client_transaction_id=CTX_ID_1,
                    account_id=DEFAULT_ACCOUNT,
                    posting_instructions=[
                        inbound_hard_settle_posting,
                    ],
                    tside=self.tside,
                )
            }
        }
        self.assertDictEqual(
            client_transaction_utils.extract_debits_by_type(
                denomination=sentinel.denomination,
                client_transactions=sentinel.client_transactions,
                client_transaction_ids_to_ignore={CTX_ID_DUMMY},
                cutoff_datetime=CUT_OFF_DATE,
                key=sentinel.key,
                values=["atm"],
            ),
            {"atm": {}},
        )

    @pytest.mark.unit
    def test_extract_debits_custom_instruction(self, mock_filter_client_transactions: MagicMock):
        # custom instructions have none effects so we do not try to derive intent and classify them
        # as a debit
        mock_filter_client_transactions.return_value = {
            "atm": {
                CTX_ID_1: ClientTransaction(
                    client_transaction_id=CTX_ID_1,
                    account_id=sentinel.account_id,
                    posting_instructions=[
                        self.custom_instruction(
                            amount=Decimal("1"),
                            postings=DEFAULT_POSTINGS,
                            value_datetime=CUT_OFF_DATE,
                            instruction_details={"type": "atm"},
                        ),
                    ],
                    tside=self.tside,
                )
            }
        }
        self.assertDictEqual(
            client_transaction_utils.extract_debits_by_type(
                denomination=sentinel.denomination,
                client_transactions=sentinel.client_transactions,
                client_transaction_ids_to_ignore={CTX_ID_DUMMY},
                cutoff_datetime=CUT_OFF_DATE,
                key=sentinel.key,
                values=["atm"],
            ),
            {"atm": {}},
        )

    @pytest.mark.unit
    def test_extract_debits_multiple_types(self, mock_filter_client_transactions: MagicMock):
        # custom instructions have none effects so we do not try to derive intent and classify them
        # as a debit
        # outbound hard settlement after cut-off is net debit after the cut-off for hard settlement
        # amount
        outbound_hard_settle_posting = self.outbound_hard_settlement(
            amount=Decimal("1"),
            value_datetime=CUT_OFF_DATE + timedelta(minutes=1),
            instruction_details={"type": "atm"},
        )
        pos_client_transactions = {
            "pos": {
                CTX_ID_1: ClientTransaction(
                    client_transaction_id=CTX_ID_1,
                    account_id=DEFAULT_ACCOUNT,
                    posting_instructions=[
                        outbound_hard_settle_posting,
                    ],
                    tside=self.tside,
                )
            }
        }
        atm_client_transactions = {
            "atm": {
                CTX_ID_2: ClientTransaction(
                    client_transaction_id=CTX_ID_2,
                    account_id=sentinel.account_id,
                    posting_instructions=[
                        self.custom_instruction(
                            amount=Decimal("1"),
                            postings=DEFAULT_POSTINGS,
                            value_datetime=CUT_OFF_DATE,
                            instruction_details={"type": "atm"},
                        ),
                    ],
                    tside=self.tside,
                )
            }
        }
        other_client_transactions: dict[str, dict[str, ClientTransaction]] = {"other": {}}

        mock_filter_client_transactions.return_value = (
            pos_client_transactions | atm_client_transactions | other_client_transactions
        )
        self.assertDictEqual(
            client_transaction_utils.extract_debits_by_type(
                denomination=sentinel.denomination,
                client_transactions=sentinel.client_transactions,
                client_transaction_ids_to_ignore={CTX_ID_DUMMY},
                cutoff_datetime=CUT_OFF_DATE,
                key=sentinel.key,
                values=["atm", "pos", "other"],
            ),
            {
                "pos": {
                    "client_id_MOCK_POSTING_2019-01-01 00:01:00+00:00": (
                        outbound_hard_settle_posting
                    )
                },
                "atm": {},
                "other": {},
            },
        )


@patch.object(client_transaction_utils, "extract_debits_by_type")
class TestExtractPeriodAndProposedDebits(FeatureTest):
    @pytest.mark.unit
    def test_no_interval_debits(self, mock_extract_debits_by_type: MagicMock):
        mock_extract_debits_by_type.side_effect = [
            {"atm": {}},
            {"atm": {"unique_id_1": sentinel.proposed_posting}},
        ]
        interval_debits, proposed_debits = (
            client_transaction_utils.extract_interval_and_proposed_debits(
                denomination=sentinel.denomination,
                proposed_transactions=sentinel.proposed_transactions,
                interval_transactions=sentinel.interval_transactions,
                transaction_type_key=sentinel.transaction_type_key,
                transaction_types=sentinel.transaction_types,
                interval_start=sentinel.interval_start,
                effective_datetime=sentinel.effective_datetime,
            )
        )
        self.assertDictEqual(interval_debits, {"atm": {}})
        self.assertDictEqual(proposed_debits, {"atm": {"unique_id_1": sentinel.proposed_posting}})

    @pytest.mark.unit
    def test_no_overlap_between_interval_proposed_debits(
        self, mock_extract_debits_by_type: MagicMock
    ):
        mock_extract_debits_by_type.side_effect = [
            {"atm": {"unique_id_1": sentinel.proposed_posting_1}},
            {"atm": {"unique_id_2": sentinel.proposed_posting_2}},
        ]
        interval_debits, proposed_debits = (
            client_transaction_utils.extract_interval_and_proposed_debits(
                denomination=sentinel.denomination,
                proposed_transactions=sentinel.proposed_transactions,
                interval_transactions=sentinel.interval_transactions,
                transaction_type_key=sentinel.transaction_type_key,
                transaction_types=sentinel.transaction_types,
                interval_start=sentinel.interval_start,
                effective_datetime=sentinel.effective_datetime,
            )
        )
        self.assertDictEqual(interval_debits, {"atm": {"unique_id_1": sentinel.proposed_posting_1}})
        self.assertDictEqual(proposed_debits, {"atm": {"unique_id_2": sentinel.proposed_posting_2}})

    @pytest.mark.unit
    def test_partial_overlap_between_interval_proposed_debits(
        self, mock_extract_debits_by_type: MagicMock
    ):
        mock_extract_debits_by_type.side_effect = [
            {
                "atm": {
                    "unique_id_1": sentinel.proposed_posting_1,
                    "unique_id_2": sentinel.proposed_posting_2,
                }
            },
            {"atm": {"unique_id_2": sentinel.proposed_posting_2}},
        ]
        interval_debits, proposed_debits = (
            client_transaction_utils.extract_interval_and_proposed_debits(
                denomination=sentinel.denomination,
                proposed_transactions=sentinel.proposed_transactions,
                interval_transactions=sentinel.interval_transactions,
                transaction_type_key=sentinel.transaction_type_key,
                transaction_types=sentinel.transaction_types,
                interval_start=sentinel.interval_start,
                effective_datetime=sentinel.effective_datetime,
            )
        )
        self.assertDictEqual(interval_debits, {"atm": {"unique_id_1": sentinel.proposed_posting_1}})
        self.assertDictEqual(proposed_debits, {"atm": {"unique_id_2": sentinel.proposed_posting_2}})

    @pytest.mark.unit
    def test_full_overlap_between_interval_proposed_debits(
        self, mock_extract_debits_by_type: MagicMock
    ):
        mock_extract_debits_by_type.side_effect = [
            {
                "atm": {
                    "unique_id_1": sentinel.proposed_posting_1,
                    "unique_id_2": sentinel.proposed_posting_2,
                }
            },
            {
                "atm": {
                    "unique_id_1": sentinel.proposed_posting_1,
                    "unique_id_2": sentinel.proposed_posting_2,
                }
            },
        ]
        interval_debits, proposed_debits = (
            client_transaction_utils.extract_interval_and_proposed_debits(
                denomination=sentinel.denomination,
                proposed_transactions=sentinel.proposed_transactions,
                interval_transactions=sentinel.interval_transactions,
                transaction_type_key=sentinel.transaction_type_key,
                transaction_types=sentinel.transaction_types,
                interval_start=sentinel.interval_start,
                effective_datetime=sentinel.effective_datetime,
            )
        )
        self.assertDictEqual(interval_debits, {"atm": {}})
        self.assertDictEqual(
            proposed_debits,
            {
                "atm": {
                    "unique_id_1": sentinel.proposed_posting_1,
                    "unique_id_2": sentinel.proposed_posting_2,
                }
            },
        )


class TestIsDebit(FeatureTest):
    @patch.object(client_transaction_utils, "get_total_transaction_impact")
    @pytest.mark.unit
    def test_is_debit_returns_true_when_impact_decreases(
        self, mock_get_total_transaction_impact: MagicMock
    ):
        # Impact decreases: -10 to -12 (debit)
        mock_get_total_transaction_impact.side_effect = [Decimal("-10.01"), Decimal(-10)]

        mock_tx = MagicMock()
        mock_posting = MagicMock(value_datetime=datetime(2023, 1, 1))

        self.assertTrue(client_transaction_utils.is_debit(mock_tx, mock_posting))

        mock_get_total_transaction_impact.assert_has_calls(
            [
                call(transaction=mock_tx, effective_datetime=mock_posting.value_datetime),
                call(
                    transaction=mock_tx,
                    effective_datetime=mock_posting.value_datetime - relativedelta(microseconds=1),
                ),
            ]
        )

    @patch.object(client_transaction_utils, "get_total_transaction_impact")
    @pytest.mark.unit
    def test_is_debit_returns_false_when_impact_increases(
        self, mock_get_total_transaction_impact: MagicMock
    ):
        # Impact increases: -10 to -8 (credit)
        mock_get_total_transaction_impact.side_effect = [Decimal("-9.99"), Decimal(-10)]

        mock_tx = MagicMock()
        mock_posting = MagicMock(value_datetime=datetime(2023, 1, 1))

        self.assertFalse(client_transaction_utils.is_debit(mock_tx, mock_posting))

    @patch.object(client_transaction_utils, "get_total_transaction_impact")
    @pytest.mark.unit
    def test_is_debit_returns_false_when_impact_is_unchanged(
        self, mock_get_total_transaction_impact: MagicMock
    ):
        # Impact unchanged: -10 to -10 (no net impact)
        mock_get_total_transaction_impact.side_effect = [Decimal(-10), Decimal(-10)]

        mock_tx = MagicMock()
        mock_posting = MagicMock(value_datetime=datetime(2023, 1, 1))

        self.assertFalse(client_transaction_utils.is_debit(mock_tx, mock_posting))
