# standard libs
from datetime import datetime
from decimal import Decimal
from unittest.mock import MagicMock
from zoneinfo import ZoneInfo

import pytest

# features
import feature_library.common.denomination as denomination_module
import feature_library.common.state_utils as state_utils
from feature_library.common.posting_utils import PostingInstructionListAlias
from feature_library.deposit.transaction_limits.deposit_limits import minimum_single_deposit

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


class TestMinimumSingleDepositLimit(CommonTransactionLimitTest):
    def _simple_mock(
        self,
        creation_date: datetime = DEFAULT_DATETIME,
        minimum_deposit: Decimal | None = None,
    ) -> MagicMock:
        return super().create_mock(
            creation_date=creation_date,
            parameters_observation_fetchers_mapping={
                minimum_single_deposit.MIN_SINGLE_DEPOSIT_POF.fetcher_id: ParametersObservation(
                    parameters={
                        minimum_single_deposit.MINIMUM_SINGLE_DEPOSIT_PARAM.id: minimum_deposit
                    },
                    value_datetime=creation_date,
                )
            },
        )

    def _positive_test_case(
        self,
        state: state_utils.SmartContractState,
        posting_instructions: PostingInstructionListAlias,
    ):
        self.assertIsNone(
            minimum_single_deposit.validate(
                state=state,
                postings=posting_instructions,
            )
        )
        alternate_state = state_utils.initialise_state(
            vault=state.vault,
            effective_datetime=state.effective_datetime,
            parameters={
                **{
                    k: v
                    for k, v in state.parameters.items()
                    if k != minimum_single_deposit.MINIMUM_SINGLE_DEPOSIT_PARAM.id
                },
                "alternate_param_id": Decimal(1),
            },
        )
        self.assertIsNone(
            minimum_single_deposit.validate(
                state=alternate_state,
                postings=posting_instructions,
                fetchers_config=minimum_single_deposit.DEFAULT_MINIMUM_SINGLE_DEPOSIT_FETCHERS_CONFIG._replace(  # noqa: E501
                    param_fetcher_id=minimum_single_deposit.MIN_SINGLE_DEPOSIT_POF.fetcher_id,
                ),
            )
        )

    def _negative_test_case(
        self,
        expected_rejection: Rejection,
        state: state_utils.SmartContractState,
        posting_instructions: PostingInstructionListAlias,
    ):
        result = minimum_single_deposit.validate(
            state=state,
            postings=posting_instructions,
        )
        self.assertEqual(result, expected_rejection)

    @pytest.mark.unit
    def test_minimum_single_deposit_limit_ignore_withdrawal(self):
        postings = [
            self.outbound_hard_settlement(denomination=DEFAULT_DENOMINATION, amount=Decimal(1))
        ]
        effective_datetime = datetime(2026, 1, 1, tzinfo=UTC)
        mock_vault = self._simple_mock(
            creation_date=effective_datetime,
            minimum_deposit=Decimal(10),
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
            posting_instructions=postings,
        )

    @pytest.mark.unit
    def test_minimum_single_deposit_limit_postings_under_the_limit(self):
        postings = [
            self.inbound_hard_settlement(denomination=DEFAULT_DENOMINATION, amount=Decimal("9.99"))
        ]
        effective_datetime = datetime(2026, 1, 1, tzinfo=UTC)
        mock_vault = self._simple_mock(
            creation_date=effective_datetime,
            minimum_deposit=Decimal(10),
        )
        state = state_utils.initialise_state(
            vault=mock_vault,
            effective_datetime=effective_datetime,
            parameters={
                denomination_module.DENOMINATION_PARAM.id: DEFAULT_DENOMINATION,
            },
        )
        expected_rejection = Rejection(
            message=f"Transaction amount 9.99 {DEFAULT_DENOMINATION} is less than the minimum deposit "  # noqa: E501
            f"amount 10 {DEFAULT_DENOMINATION}.",
            reason_code=RejectionReason.AGAINST_TNC,
        )
        self._negative_test_case(
            expected_rejection=expected_rejection,
            state=state,
            posting_instructions=postings,
        )

    @pytest.mark.unit
    def test_minimum_single_deposit_limit_postings_at_the_limit(self):
        postings = [
            self.inbound_hard_settlement(denomination=DEFAULT_DENOMINATION, amount=Decimal(10))
        ]
        effective_datetime = datetime(2026, 1, 1, tzinfo=UTC)
        mock_vault = self._simple_mock(
            creation_date=effective_datetime,
            minimum_deposit=Decimal(10),
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
            posting_instructions=postings,
        )
