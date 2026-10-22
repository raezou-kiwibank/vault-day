# standard libs
from datetime import datetime
from decimal import Decimal
from unittest.mock import MagicMock
from zoneinfo import ZoneInfo

import pytest
from dateutil.relativedelta import relativedelta

import feature_library.common.denomination as denomination_module

# features
import feature_library.common.fetchers as fetchers
import feature_library.common.state_utils as state_utils
from feature_library.deposit.transaction_limits.deposit_limits import maximum_daily_deposit

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
    CTX_ID_1,
    CTX_ID_2,
    CommonTransactionLimitTest,
)

UTC = ZoneInfo("UTC")


class TestMaximumDailyDepositLimit(CommonTransactionLimitTest):
    def _simple_mock(
        self,
        client_transactions_mapping: dict[str, dict[str, ClientTransaction]] | None = None,
        creation_date: datetime = DEFAULT_DATETIME,
        maximum_daily_deposit_limit: Decimal | None = None,
    ) -> MagicMock:
        return super().create_mock(
            client_transactions_mapping=client_transactions_mapping,
            creation_date=creation_date,
            parameters_observation_fetchers_mapping={
                maximum_daily_deposit.MAX_DAILY_DEPOSIT_POF.fetcher_id: ParametersObservation(
                    parameters={
                        maximum_daily_deposit.MAXIMUM_DAILY_DEPOSIT_PARAM.id: maximum_daily_deposit_limit  # noqa: E501
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
            maximum_daily_deposit.validate(
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
                    if k != maximum_daily_deposit.MAXIMUM_DAILY_DEPOSIT_PARAM.id
                },
                "alternate_param_id": Decimal(100),
            },
        )
        self.assertIsNone(
            maximum_daily_deposit.validate(
                state=alternate_state,
                client_transactions=client_transactions,
                fetchers_config=maximum_daily_deposit.DEFAULT_MAXIMUM_DAILY_DEPOSIT_FETCHERS_CONFIG._replace(  # noqa: E501
                    param_fetcher_id=maximum_daily_deposit.MAX_DAILY_DEPOSIT_POF.fetcher_id,
                ),
            )
        )

    def _negative_test_case(
        self,
        expected_rejection: Rejection,
        state: state_utils.SmartContractState,
        client_transactions: dict[str, ClientTransaction],
    ):
        result = maximum_daily_deposit.validate(
            state=state,
            client_transactions=client_transactions,
        )
        self.assertEqual(result, expected_rejection)

    def mock_client_transaction(
        self,
        ctx_id: str,
        start_datetime: datetime,
        deposit_amount=Decimal(0),
        withdrawal_amount=Decimal(0),
    ):
        mock_transaction = MagicMock(spec=ClientTransaction)
        mock_transaction.client_transaction_id = ctx_id
        mock_transaction.denomination = DEFAULT_DENOMINATION
        mock_transaction.start_datetime = start_datetime

        def mock_effects(effective_datetime=None):
            effect_mock = MagicMock()
            if effective_datetime is not None and effective_datetime < start_datetime:
                effect_mock.settled = Decimal(0)
                effect_mock.unsettled = Decimal(0)
            else:
                effect_mock.settled = deposit_amount - withdrawal_amount
                effect_mock.unsettled = Decimal(0)
            return effect_mock

        mock_transaction.effects.side_effect = mock_effects
        return mock_transaction

    @pytest.mark.unit
    def test_maximum_daily_deposit_limit_ignore_withdrawal(
        self,
    ):
        effective_datetime = datetime(2026, 1, 1, tzinfo=UTC)
        ctx = self.mock_client_transaction(
            ctx_id=CTX_ID_1, start_datetime=effective_datetime, withdrawal_amount=Decimal(100)
        )
        client_transactions = {CTX_ID_1: ctx}
        mock_vault = self._simple_mock(
            client_transactions_mapping={fetchers.EFFECTIVE_DATE_POSTIF_ID: {}},
            creation_date=effective_datetime,
            maximum_daily_deposit_limit=Decimal(100),
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
    def test_maximum_daily_deposit_limit_postings_total_is_under_the_limit(
        self,
    ):
        effective_datetime = datetime(2026, 1, 1, tzinfo=UTC)
        historic_ctx = {
            "historic_1": self.mock_client_transaction(
                ctx_id="historic_1",
                start_datetime=effective_datetime - relativedelta(days=1),
                deposit_amount=Decimal(50),
            )
        }
        mock_vault = self._simple_mock(
            client_transactions_mapping={fetchers.EFFECTIVE_DATE_POSTIF_ID: historic_ctx},
            creation_date=effective_datetime,
            maximum_daily_deposit_limit=Decimal(100),
        )
        client_transactions = {
            CTX_ID_1: self.mock_client_transaction(
                ctx_id=CTX_ID_1,
                start_datetime=effective_datetime,
                withdrawal_amount=Decimal(1000),
            ),
            CTX_ID_2: self.mock_client_transaction(
                ctx_id=CTX_ID_2,
                start_datetime=effective_datetime,
                deposit_amount=Decimal("49.99"),
            ),
        }
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
    def test_maximum_daily_deposit_limit_postings_total_is_over_the_limit(
        self,
    ):
        start_datetime = datetime(2026, 1, 1, tzinfo=UTC)
        effective_datetime = start_datetime + relativedelta(days=1, microseconds=-1)
        historic_ctx = {
            "historic_1": self.mock_client_transaction(
                ctx_id="historic_1",
                start_datetime=start_datetime,
                deposit_amount=Decimal(50),
            )
        }
        mock_vault = self._simple_mock(
            client_transactions_mapping={fetchers.EFFECTIVE_DATE_POSTIF_ID: historic_ctx},
            creation_date=start_datetime,
            maximum_daily_deposit_limit=Decimal(100),
        )
        client_transactions = {
            CTX_ID_1: self.mock_client_transaction(
                ctx_id=CTX_ID_1,
                start_datetime=effective_datetime,
                withdrawal_amount=Decimal(1000),
            ),
            CTX_ID_2: self.mock_client_transaction(
                ctx_id=CTX_ID_2,
                start_datetime=effective_datetime,
                deposit_amount=Decimal("50.01"),
            ),
        }
        state = state_utils.initialise_state(
            vault=mock_vault,
            effective_datetime=effective_datetime,
            parameters={
                denomination_module.DENOMINATION_PARAM.id: DEFAULT_DENOMINATION,
            },
        )
        expected_rejection = Rejection(
            message=f"Transactions would cause the maximum daily deposit limit of "
            f"100 {DEFAULT_DENOMINATION} to be exceeded.",
            reason_code=RejectionReason.AGAINST_TNC,
        )
        self._negative_test_case(
            expected_rejection=expected_rejection,
            state=state,
            client_transactions=client_transactions,
        )

    @pytest.mark.unit
    def test_maximum_daily_deposit_limit_exactly_at_limit(
        self,
    ):
        effective_datetime = datetime(2026, 1, 1, tzinfo=UTC)
        historic_ctx = {
            "historic_1": self.mock_client_transaction(
                ctx_id="historic_1",
                start_datetime=effective_datetime,
                deposit_amount=Decimal(50),
            )
        }
        mock_vault = self._simple_mock(
            client_transactions_mapping={fetchers.EFFECTIVE_DATE_POSTIF_ID: historic_ctx},
            creation_date=effective_datetime,
            maximum_daily_deposit_limit=Decimal(100),
        )
        client_transactions = {
            CTX_ID_1: self.mock_client_transaction(
                ctx_id=CTX_ID_1,
                start_datetime=effective_datetime,
                withdrawal_amount=Decimal(1000),
            ),
            CTX_ID_2: self.mock_client_transaction(
                ctx_id=CTX_ID_2,
                start_datetime=effective_datetime + relativedelta(days=1, microseconds=-1),
                deposit_amount=Decimal(50),
            ),
        }
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
