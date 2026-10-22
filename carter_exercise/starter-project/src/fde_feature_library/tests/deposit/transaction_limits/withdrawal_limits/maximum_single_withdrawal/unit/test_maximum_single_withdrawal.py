# standard libs
from datetime import datetime
from decimal import Decimal
from unittest.mock import MagicMock
from zoneinfo import ZoneInfo

import pytest

import feature_library.common.denomination as denomination_module

# features
import feature_library.common.state_utils as state_utils
from feature_library.deposit.transaction_limits.withdrawal_limits import (
    maximum_single_withdrawal,
)

# contracts api
from contracts_api import (
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


class TestMaximumSingleWithdrawal(CommonTransactionLimitTest):
    def _simple_mock(
        self,
        creation_date: datetime = DEFAULT_DATETIME,
        max_withdrawal: Decimal | None = None,
    ) -> MagicMock:
        return super().create_mock(
            creation_date=creation_date,
            parameters_observation_fetchers_mapping={
                maximum_single_withdrawal.MAX_WITHDRAWAL_POF.fetcher_id: ParametersObservation(
                    parameters={maximum_single_withdrawal.MAX_WITHDRAWAL_PARAM.id: max_withdrawal},
                    value_datetime=creation_date,
                )
            },
        )

    def _positive_test_case(
        self,
        state: state_utils.SmartContractState,
        postings: list,
    ):
        self.assertIsNone(
            maximum_single_withdrawal.validate(
                state=state,
                postings=postings,
            )
        )
        alternate_state = state_utils.initialise_state(
            vault=state.vault,
            effective_datetime=state.effective_datetime,
            parameters={
                **{
                    k: v
                    for k, v in state.parameters.items()
                    if k != maximum_single_withdrawal.MAX_WITHDRAWAL_PARAM.id
                },
                "alternate_param_id": Decimal("100"),
            },
        )
        self.assertIsNone(
            maximum_single_withdrawal.validate(
                state=alternate_state,
                postings=postings,
                fetchers_config=maximum_single_withdrawal.MaximumSingleWithdrawalFetchersConfig(
                    param_fetcher_id=maximum_single_withdrawal.MAX_WITHDRAWAL_POF_ID,
                    denomination_param_id=denomination_module.DENOMINATION_PARAM_ID,
                    maximum_withdrawal_param_id="alternate_param_id",
                ),
            )
        )

    def _negative_test_case(
        self,
        expected_rejection: Rejection,
        state: state_utils.SmartContractState,
        postings: list,
    ):
        result = maximum_single_withdrawal.validate(
            state=state,
            postings=postings,
        )
        self.assertEqual(result, expected_rejection)

    @pytest.mark.unit
    def test_maximum_single_withdrawal_ignore_deposit(self):
        effective_datetime = datetime(2026, 1, 1, 12, tzinfo=UTC)
        posting_instructions = [self.inbound_hard_settlement(amount=Decimal("1000"))]

        mock_vault = self._simple_mock(
            creation_date=effective_datetime,
            max_withdrawal=Decimal("100"),
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
            postings=posting_instructions,
        )

    @pytest.mark.unit
    def test_maximum_single_withdrawal_exceeded(self):
        effective_datetime = datetime(2026, 1, 1, 12, tzinfo=UTC)
        posting_instructions = [self.outbound_hard_settlement(amount=Decimal("101"))]

        mock_vault = self._simple_mock(
            creation_date=effective_datetime,
            max_withdrawal=Decimal("100"),
        )
        state = state_utils.initialise_state(
            vault=mock_vault,
            effective_datetime=effective_datetime,
            parameters={
                denomination_module.DENOMINATION_PARAM.id: DEFAULT_DENOMINATION,
            },
        )
        expected_rejection = Rejection(
            message="Transaction amount 101 GBP is greater than the maximum withdrawal "
            "amount 100 GBP.",
            reason_code=RejectionReason.AGAINST_TNC,
        )
        self._negative_test_case(
            expected_rejection=expected_rejection,
            state=state,
            postings=posting_instructions,
        )

    @pytest.mark.unit
    def test_maximum_single_withdrawal_not_exceeded(self):
        effective_datetime = datetime(2026, 1, 1, 12, tzinfo=UTC)
        posting_instructions = [self.outbound_hard_settlement(amount=Decimal("99"))]

        mock_vault = self._simple_mock(
            creation_date=effective_datetime,
            max_withdrawal=Decimal("100"),
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
            postings=posting_instructions,
        )

    @pytest.mark.unit
    def test_maximum_single_withdrawal_met(self):
        effective_datetime = datetime(2026, 1, 1, 12, tzinfo=UTC)
        posting_instructions = [self.outbound_hard_settlement(amount=Decimal("100"))]

        mock_vault = self._simple_mock(
            creation_date=effective_datetime,
            max_withdrawal=Decimal("100"),
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
            postings=posting_instructions,
        )

    @pytest.mark.unit
    def test_maximum_single_withdrawal_several_postings_do_not_exceed_limit(self):
        effective_datetime = datetime(2026, 1, 1, 12, tzinfo=UTC)
        posting_instructions = [
            self.inbound_hard_settlement(amount=Decimal("200")),
            self.outbound_hard_settlement(amount=Decimal("100")),
            self.outbound_hard_settlement(amount=Decimal("55")),
            self.outbound_hard_settlement(amount=Decimal("45.01")),
        ]

        mock_vault = self._simple_mock(
            creation_date=effective_datetime,
            max_withdrawal=Decimal("100"),
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
            postings=posting_instructions,
        )

    @pytest.mark.unit
    def test_maximum_single_withdrawal_several_postings_and_one_exceeds_limit(self):
        effective_datetime = datetime(2026, 1, 1, 12, tzinfo=UTC)
        posting_instructions = [
            self.inbound_hard_settlement(amount=Decimal("200")),
            self.outbound_hard_settlement(amount=Decimal("100")),
            self.outbound_hard_settlement(amount=Decimal("45.01")),
            self.outbound_hard_settlement(amount=Decimal("100.01")),
        ]

        mock_vault = self._simple_mock(
            creation_date=effective_datetime,
            max_withdrawal=Decimal("100"),
        )
        state = state_utils.initialise_state(
            vault=mock_vault,
            effective_datetime=effective_datetime,
            parameters={
                denomination_module.DENOMINATION_PARAM.id: DEFAULT_DENOMINATION,
            },
        )
        expected_rejection = Rejection(
            message="Transaction amount 100.01 GBP is greater than the maximum withdrawal "
            "amount 100 GBP.",
            reason_code=RejectionReason.AGAINST_TNC,
        )
        self._negative_test_case(
            expected_rejection=expected_rejection,
            state=state,
            postings=posting_instructions,
        )
