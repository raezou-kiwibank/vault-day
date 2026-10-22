# standard libs
from datetime import datetime
from decimal import Decimal
from unittest.mock import MagicMock
from zoneinfo import ZoneInfo

import pytest

import feature_library.common.denomination as denomination_module

# features
import feature_library.common.fetchers as fetchers
import feature_library.common.state_utils as state_utils
from feature_library.deposit.transaction_limits.withdrawal_limits import (
    maximum_daily_withdrawal,
)

# contracts api
from contracts_api import (
    ClientTransaction,
    ParametersObservation,
    Rejection,
    RejectionReason,
)

# inception sdk
from inception_sdk.test_framework.contracts.unit.common import (
    DEFAULT_DATETIME,
    DEFAULT_DENOMINATION,
)

from tests.deposit.transaction_limits.deposit_limits.test_common_transaction_limit import (
    CommonTransactionLimitTest,
)

UTC = ZoneInfo("UTC")


class TestMaximumDailyWithdrawalLimit(CommonTransactionLimitTest):
    def _simple_mock(
        self,
        client_transactions_mapping: dict[str, dict[str, ClientTransaction]] | None = None,
        creation_date: datetime = DEFAULT_DATETIME,
        max_daily_withdrawal: Decimal | None = None,
    ) -> MagicMock:
        return super().create_mock(
            client_transactions_mapping=client_transactions_mapping,
            creation_date=creation_date,
            parameters_observation_fetchers_mapping={
                maximum_daily_withdrawal.MAX_DAILY_WITHDRAWAL_POF.fetcher_id: ParametersObservation(
                    parameters={
                        maximum_daily_withdrawal.MAX_DAILY_WITHDRAWAL_PARAM.id: max_daily_withdrawal
                    },
                    value_datetime=creation_date,
                )
            },
        )

    def _positive_test_case(
        self,
        state: state_utils.SmartContractState,
        client_transactions: dict[str, ClientTransaction],
    ):
        self.assertIsNone(
            maximum_daily_withdrawal.validate(
                state=state,
                client_transactions=client_transactions,
            )
        )
        alternate_state = state_utils.initialise_state(
            vault=state.vault,
            effective_datetime=state.effective_datetime,
            parameters={
                **{
                    k: v
                    for k, v in state.parameters.items()
                    if k != maximum_daily_withdrawal.MAX_DAILY_WITHDRAWAL_PARAM.id
                },
                "alternate_param_id": Decimal(100),
            },
        )
        self.assertIsNone(
            maximum_daily_withdrawal.validate(
                state=alternate_state,
                client_transactions=client_transactions,
                fetchers_config=maximum_daily_withdrawal.MaximumDailyWithdrawalFetchersConfig(
                    param_fetcher_id=maximum_daily_withdrawal.MAX_DAILY_WITHDRAWAL_POF_ID,
                    client_transactions_fetcher_id=fetchers.EFFECTIVE_DATE_POSTIF_ID,
                    denomination_param_id=denomination_module.DENOMINATION_PARAM_ID,
                    maximum_daily_withdrawal_param_id="alternate_param_id",
                ),
            )
        )
        self.assertIsNone(
            maximum_daily_withdrawal.validate(
                state=state,
                client_transactions=client_transactions,
                fetchers_config=maximum_daily_withdrawal.MaximumDailyWithdrawalFetchersConfig(
                    param_fetcher_id=maximum_daily_withdrawal.MAX_DAILY_WITHDRAWAL_POF.fetcher_id,
                    client_transactions_fetcher_id=fetchers.EFFECTIVE_DATE_POSTIF.fetcher_id,
                    denomination_param_id=denomination_module.DENOMINATION_PARAM_ID,
                    maximum_daily_withdrawal_param_id=maximum_daily_withdrawal.MAX_DAILY_WITHDRAWAL_PARAM_ID,  # noqa: E501
                ),
            )
        )

    def _negative_test_case(
        self,
        expected_rejection: Rejection,
        state: state_utils.SmartContractState,
        client_transactions: dict[str, ClientTransaction],
    ):
        result = maximum_daily_withdrawal.validate(
            state=state,
            client_transactions=client_transactions,
        )
        self.assertEqual(result, expected_rejection)

        alternate_state = state_utils.initialise_state(
            vault=state.vault,
            effective_datetime=state.effective_datetime,
            parameters={
                **{
                    k: v
                    for k, v in state.parameters.items()
                    if k != maximum_daily_withdrawal.MAX_DAILY_WITHDRAWAL_PARAM.id
                },
                "alternate_param_id": Decimal(100),
            },
        )
        result_2 = maximum_daily_withdrawal.validate(
            state=alternate_state,
            client_transactions=client_transactions,
            fetchers_config=maximum_daily_withdrawal.MaximumDailyWithdrawalFetchersConfig(
                param_fetcher_id=maximum_daily_withdrawal.MAX_DAILY_WITHDRAWAL_POF_ID,
                client_transactions_fetcher_id=fetchers.EFFECTIVE_DATE_POSTIF_ID,
                denomination_param_id=denomination_module.DENOMINATION_PARAM_ID,
                maximum_daily_withdrawal_param_id="alternate_param_id",
            ),
        )
        self.assertEqual(result_2, expected_rejection)

        result_3 = maximum_daily_withdrawal.validate(
            state=state,
            client_transactions=client_transactions,
            fetchers_config=maximum_daily_withdrawal.MaximumDailyWithdrawalFetchersConfig(
                param_fetcher_id=maximum_daily_withdrawal.MAX_DAILY_WITHDRAWAL_POF.fetcher_id,
                client_transactions_fetcher_id=fetchers.EFFECTIVE_DATE_POSTIF.fetcher_id,
                denomination_param_id=denomination_module.DENOMINATION_PARAM_ID,
                maximum_daily_withdrawal_param_id=maximum_daily_withdrawal.MAX_DAILY_WITHDRAWAL_PARAM_ID,  # noqa: E501
            ),
        )
        self.assertEqual(result_3, expected_rejection)

    def mock_client_transaction(self, withdrawal_amount: Decimal, start_datetime: datetime):
        mock_transaction = MagicMock(spec=ClientTransaction)
        mock_transaction.denomination = DEFAULT_DENOMINATION
        mock_transaction.start_datetime = start_datetime

        def mock_effects(effective_datetime=None):
            effect_mock = MagicMock()
            if effective_datetime is not None and effective_datetime < start_datetime:
                effect_mock.settled = Decimal(0)
                effect_mock.unsettled = Decimal(0)
            else:
                effect_mock.settled = -withdrawal_amount
                effect_mock.unsettled = Decimal(0)
            return effect_mock

        mock_transaction.effects.side_effect = mock_effects
        return mock_transaction

    def mock_deposit_transaction(self, deposit_amount: Decimal, start_datetime: datetime):
        mock_transaction = MagicMock(spec=ClientTransaction)
        mock_transaction.denomination = DEFAULT_DENOMINATION
        mock_transaction.start_datetime = start_datetime

        def mock_effects(effective_datetime=None):
            effect_mock = MagicMock()
            if effective_datetime is not None and effective_datetime < start_datetime:
                effect_mock.settled = Decimal(0)
                effect_mock.unsettled = Decimal(0)
            else:
                effect_mock.settled = deposit_amount
                effect_mock.unsettled = Decimal(0)
            return effect_mock

        mock_transaction.effects.side_effect = mock_effects
        return mock_transaction

    @pytest.mark.unit
    def test_maximum_daily_withdrawal_limit_ignore_deposit(self):
        effective_datetime = datetime(2026, 1, 1, 12, tzinfo=UTC)
        client_transactions = {
            "ctx_1": self.mock_deposit_transaction(Decimal(1000), effective_datetime)
        }
        mock_vault = self._simple_mock(
            client_transactions_mapping={fetchers.EFFECTIVE_DATE_POSTIF.fetcher_id: {}},
            creation_date=effective_datetime,
            max_daily_withdrawal=Decimal(100),
        )
        state = state_utils.initialise_state(
            vault=mock_vault,
            effective_datetime=effective_datetime,
            parameters={
                denomination_module.DENOMINATION_PARAM.id: DEFAULT_DENOMINATION,
            },
        )
        self._positive_test_case(
            state=state,
            client_transactions=client_transactions,
        )

    @pytest.mark.unit
    def test_maximum_daily_withdrawal_limit_postings_total_is_under_the_limit(self):
        effective_datetime = datetime(2026, 1, 1, 12, tzinfo=UTC)
        past_datetime = datetime(2026, 1, 1, 10, tzinfo=UTC)

        client_transactions = {
            "ctx_1": self.mock_client_transaction(Decimal(50), effective_datetime)
        }
        past_transactions = {"ctx_past": self.mock_client_transaction(Decimal(40), past_datetime)}

        mock_vault = self._simple_mock(
            client_transactions_mapping={
                fetchers.EFFECTIVE_DATE_POSTIF.fetcher_id: past_transactions
            },
            creation_date=effective_datetime,
            max_daily_withdrawal=Decimal(100),
        )
        state = state_utils.initialise_state(
            vault=mock_vault,
            effective_datetime=effective_datetime,
            parameters={
                denomination_module.DENOMINATION_PARAM.id: DEFAULT_DENOMINATION,
            },
        )
        self._positive_test_case(
            state=state,
            client_transactions=client_transactions,
        )

    @pytest.mark.unit
    def test_maximum_daily_withdrawal_limit_postings_total_is_over_the_limit(self):
        effective_datetime = datetime(2026, 1, 1, 12, tzinfo=UTC)
        past_datetime = datetime(2026, 1, 1, 10, tzinfo=UTC)

        client_transactions = {
            "ctx_1": self.mock_client_transaction(Decimal(60), effective_datetime)
        }
        past_transactions = {"ctx_past": self.mock_client_transaction(Decimal(50), past_datetime)}

        mock_vault = self._simple_mock(
            client_transactions_mapping={
                fetchers.EFFECTIVE_DATE_POSTIF.fetcher_id: past_transactions
            },
            creation_date=effective_datetime,
            max_daily_withdrawal=Decimal(100),
        )
        state = state_utils.initialise_state(
            vault=mock_vault,
            effective_datetime=effective_datetime,
            parameters={
                denomination_module.DENOMINATION_PARAM.id: DEFAULT_DENOMINATION,
            },
        )
        expected_rejection = Rejection(
            message=f"Transactions with a total of 110 {DEFAULT_DENOMINATION} would cause the "
            f"maximum daily withdrawal limit of 100 {DEFAULT_DENOMINATION} to be exceeded.",
            reason_code=RejectionReason.AGAINST_TNC,
        )
        self._negative_test_case(
            expected_rejection=expected_rejection,
            state=state,
            client_transactions=client_transactions,
        )

    @pytest.mark.unit
    def test_maximum_daily_withdrawal_limit_exceeded(self):
        effective_datetime = datetime(2026, 1, 1, 12, tzinfo=UTC)

        client_transactions = {
            "ctx_1": self.mock_client_transaction(Decimal(101), effective_datetime)
        }

        mock_vault = self._simple_mock(
            client_transactions_mapping={fetchers.EFFECTIVE_DATE_POSTIF.fetcher_id: {}},
            creation_date=effective_datetime,
            max_daily_withdrawal=Decimal(100),
        )
        state = state_utils.initialise_state(
            vault=mock_vault,
            effective_datetime=effective_datetime,
            parameters={
                denomination_module.DENOMINATION_PARAM.id: DEFAULT_DENOMINATION,
            },
        )
        expected_rejection = Rejection(
            message=f"Transactions with a total of 101 {DEFAULT_DENOMINATION} would cause the "
            f"maximum daily withdrawal limit of 100 {DEFAULT_DENOMINATION} to be exceeded.",
            reason_code=RejectionReason.AGAINST_TNC,
        )
        self._negative_test_case(
            expected_rejection=expected_rejection,
            state=state,
            client_transactions=client_transactions,
        )
