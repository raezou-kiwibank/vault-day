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
    minimum_single_withdrawal,
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


class TestMinimumSingleWithdrawal(CommonTransactionLimitTest):
    def _simple_mock(
        self,
        creation_date: datetime = DEFAULT_DATETIME,
        min_withdrawal: Decimal | None = None,
    ) -> MagicMock:
        return super().create_mock(
            creation_date=creation_date,
            parameters_observation_fetchers_mapping={
                minimum_single_withdrawal.MIN_WITHDRAWAL_POF.fetcher_id: ParametersObservation(
                    parameters={minimum_single_withdrawal.MIN_WITHDRAWAL_PARAM.id: min_withdrawal},
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
            minimum_single_withdrawal.validate(
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
                    if k != minimum_single_withdrawal.MIN_WITHDRAWAL_PARAM.id
                },
                "alternate_param_id": Decimal("0.01"),
            },
        )
        self.assertIsNone(
            minimum_single_withdrawal.validate(
                state=alternate_state,
                postings=postings,
                fetchers_config=minimum_single_withdrawal.MinimumSingleWithdrawalFetchersConfig(
                    param_fetcher_id=minimum_single_withdrawal.MIN_WITHDRAWAL_POF_ID,
                    denomination_param_id=denomination_module.DENOMINATION_PARAM_ID,
                    minimum_withdrawal_param_id="alternate_param_id",
                ),
            )
        )

    def _negative_test_case(
        self,
        expected_rejection: Rejection,
        state: state_utils.SmartContractState,
        postings: list,
    ):
        result = minimum_single_withdrawal.validate(
            state=state,
            postings=postings,
        )
        self.assertEqual(result, expected_rejection)

    @pytest.mark.unit
    def test_minimum_single_withdrawal_ignore_deposit(self):
        effective_datetime = datetime(2026, 1, 1, 12, tzinfo=UTC)
        posting_instructions = [self.inbound_hard_settlement(amount=Decimal("0.001"))]

        mock_vault = self._simple_mock(
            creation_date=effective_datetime,
            min_withdrawal=Decimal("0.01"),
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
    def test_minimum_single_withdrawal_not_met(self):
        effective_datetime = datetime(2026, 1, 1, 12, tzinfo=UTC)
        posting_instructions = [self.outbound_hard_settlement(amount=Decimal("0.001"))]

        mock_vault = self._simple_mock(
            creation_date=effective_datetime,
            min_withdrawal=Decimal("0.01"),
        )
        state = state_utils.initialise_state(
            vault=mock_vault,
            effective_datetime=effective_datetime,
            parameters={
                denomination_module.DENOMINATION_PARAM.id: DEFAULT_DENOMINATION,
            },
        )
        expected_rejection = Rejection(
            message="Transaction amount 0.001 GBP is less than the minimum withdrawal "
            "amount 0.01 GBP.",
            reason_code=RejectionReason.AGAINST_TNC,
        )

        self._negative_test_case(
            expected_rejection=expected_rejection,
            state=state,
            postings=posting_instructions,
        )

    @pytest.mark.unit
    def test_minimum_single_withdrawal_exceeded(self):
        effective_datetime = datetime(2026, 1, 1, 12, tzinfo=UTC)
        posting_instructions = [self.outbound_hard_settlement(amount=Decimal("0.02"))]

        mock_vault = self._simple_mock(
            creation_date=effective_datetime,
            min_withdrawal=Decimal("0.01"),
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
    def test_minimum_single_withdrawal_met(self):
        effective_datetime = datetime(2026, 1, 1, 12, tzinfo=UTC)
        posting_instructions = [self.outbound_hard_settlement(amount=Decimal("0.01"))]

        mock_vault = self._simple_mock(
            creation_date=effective_datetime,
            min_withdrawal=Decimal("0.01"),
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
    def test_minimum_single_withdrawal_several_postings_one_doesnt_meet_limit(self):
        effective_datetime = datetime(2026, 1, 1, 12, tzinfo=UTC)
        posting_instructions = [
            self.inbound_hard_settlement(amount=Decimal("0.001")),
            self.outbound_hard_settlement(amount=Decimal("100.001")),
            self.outbound_hard_settlement(amount=Decimal("0.01")),
            self.outbound_hard_settlement(amount=Decimal("0.00999")),
        ]

        mock_vault = self._simple_mock(
            creation_date=effective_datetime,
            min_withdrawal=Decimal("0.01"),
        )
        state = state_utils.initialise_state(
            vault=mock_vault,
            effective_datetime=effective_datetime,
            parameters={
                denomination_module.DENOMINATION_PARAM.id: DEFAULT_DENOMINATION,
            },
        )
        expected_rejection = Rejection(
            message="Transaction amount 0.00999 GBP is less than the minimum withdrawal "
            "amount 0.01 GBP.",
            reason_code=RejectionReason.AGAINST_TNC,
        )

        self._negative_test_case(
            expected_rejection=expected_rejection,
            state=state,
            postings=posting_instructions,
        )
