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
from feature_library.common.posting_utils import PostingInstructionListAlias
from feature_library.deposit.transaction_limits.deposit_limits import maximum_balance_limit

# contracts api
from contracts_api import (
    BalanceDefaultDict,
    BalancesObservation,
    ParametersObservation,
    Rejection,
    RejectionReason,
)

# inception sdk
from inception_sdk.test_framework.contracts.unit.common import (
    DEFAULT_DATETIME,
    DEFAULT_DENOMINATION,
)

from tests.deposit.transaction_limits.deposit_limits.test_common_transaction_limit import (  # noqa: E501
    CommonTransactionLimitTest,
)

UTC = ZoneInfo("UTC")


class TestMaximumBalanceLimit(CommonTransactionLimitTest):
    def _simple_mock(
        self,
        balances_observation_fetchers_mapping: dict[str, BalancesObservation] | None = None,
        creation_date: datetime = DEFAULT_DATETIME,
        max_bal_limit: Decimal | None = None,
    ) -> MagicMock:
        return super().create_mock(
            balances_observation_fetchers_mapping=balances_observation_fetchers_mapping,
            creation_date=creation_date,
            parameters_observation_fetchers_mapping={
                maximum_balance_limit.MAX_BAL_LIMIT_POF.fetcher_id: ParametersObservation(
                    parameters={maximum_balance_limit.MAXIMUM_BALANCE_PARAM.id: max_bal_limit},
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
            maximum_balance_limit.validate(
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
                    if k != maximum_balance_limit.MAXIMUM_BALANCE_PARAM.id
                },
                "alternate_param_id": Decimal(100),
            },
        )
        self.assertIsNone(
            maximum_balance_limit.validate(
                state=alternate_state,
                postings=posting_instructions,
                fetchers_config=maximum_balance_limit.DEFAULT_MAXIMUM_BALANCE_LIMIT_FETCHERS_CONFIG._replace(
                    maximum_balance_param_id="alternate_param_id"
                ),
            )
        )
        self.assertIsNone(
            maximum_balance_limit.validate(
                state=state,
                postings=posting_instructions,
                fetchers_config=maximum_balance_limit.DEFAULT_MAXIMUM_BALANCE_LIMIT_FETCHERS_CONFIG,
            )
        )

    def _negative_test_case(
        self,
        expected_rejection: Rejection,
        state: state_utils.SmartContractState,
        posting_instructions: PostingInstructionListAlias,
    ):
        result = maximum_balance_limit.validate(
            state=state,
            postings=posting_instructions,
        )
        self.assertEqual(result, expected_rejection)

        alternate_state = state_utils.initialise_state(
            vault=state.vault,
            effective_datetime=state.effective_datetime,
            parameters={
                **{
                    k: v
                    for k, v in state.parameters.items()
                    if k != maximum_balance_limit.MAXIMUM_BALANCE_PARAM.id
                },
                "alternate_param_id": Decimal(100),
            },
        )
        result_2 = maximum_balance_limit.validate(
            state=alternate_state,
            postings=posting_instructions,
            fetchers_config=maximum_balance_limit.DEFAULT_MAXIMUM_BALANCE_LIMIT_FETCHERS_CONFIG._replace(
                maximum_balance_param_id="alternate_param_id"
            ),
        )
        self.assertEqual(result_2, expected_rejection)

        result_3 = maximum_balance_limit.validate(
            state=state,
            postings=posting_instructions,
            fetchers_config=maximum_balance_limit.DEFAULT_MAXIMUM_BALANCE_LIMIT_FETCHERS_CONFIG,
        )
        self.assertEqual(result_3, expected_rejection)

    @pytest.mark.unit
    def test_maximum_balance_limit_ignore_withdrawal(
        self,
    ):
        posting_instructions = [
            self.outbound_hard_settlement(denomination=DEFAULT_DENOMINATION, amount=Decimal(1000))
        ]
        account_bals: BalanceDefaultDict = self.balances()
        effective_datetime = datetime(2026, 1, 1, tzinfo=UTC)
        mock_vault = self._simple_mock(
            balances_observation_fetchers_mapping={
                fetchers.ALL_BALANCES_LIVE_BOF.fetcher_id: BalancesObservation(
                    balances=account_bals,
                    value_datetime=effective_datetime,
                    at_datetime=effective_datetime,
                )
            },
            creation_date=effective_datetime,
            max_bal_limit=Decimal(100),
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
            posting_instructions=posting_instructions,
        )

    @pytest.mark.unit
    def test_maximum_balance_limit_postings_total_is_under_the_limit(
        self,
    ):
        account_bals: BalanceDefaultDict = self.balances()
        effective_datetime = datetime(2026, 1, 1, tzinfo=UTC)
        mock_vault = self._simple_mock(
            balances_observation_fetchers_mapping={
                fetchers.ALL_BALANCES_LIVE_BOF.fetcher_id: BalancesObservation(
                    balances=account_bals,
                    value_datetime=effective_datetime,
                    at_datetime=effective_datetime,
                )
            },
            creation_date=effective_datetime,
            max_bal_limit=Decimal(100),
        )
        posting_instructions = [
            self.outbound_hard_settlement(denomination=DEFAULT_DENOMINATION, amount=Decimal(1000)),
            self.inbound_hard_settlement(denomination=DEFAULT_DENOMINATION, amount=Decimal(500)),
            self.inbound_hard_settlement(denomination=DEFAULT_DENOMINATION, amount=Decimal(500)),
            self.inbound_hard_settlement(
                denomination=DEFAULT_DENOMINATION, amount=Decimal("99.99")
            ),
        ]
        state = state_utils.initialise_state(
            vault=mock_vault,
            effective_datetime=effective_datetime,
            parameters={
                denomination_module.DENOMINATION_PARAM.id: DEFAULT_DENOMINATION,
            },
        )
        self._positive_test_case(
            state=state,
            posting_instructions=posting_instructions,
        )

    @pytest.mark.unit
    def test_maximum_balance_limit_postings_total_is_over_the_limit(
        self,
    ):
        posting_instructions = [
            self.outbound_hard_settlement(denomination=DEFAULT_DENOMINATION, amount=Decimal(1000)),
            self.inbound_hard_settlement(denomination=DEFAULT_DENOMINATION, amount=Decimal(500)),
            self.inbound_hard_settlement(denomination=DEFAULT_DENOMINATION, amount=Decimal(500)),
            self.inbound_hard_settlement(denomination=DEFAULT_DENOMINATION, amount=Decimal(101)),
        ]
        account_bals: BalanceDefaultDict = self.balances()
        effective_datetime = datetime(2026, 1, 1, tzinfo=UTC)
        mock_vault = self._simple_mock(
            balances_observation_fetchers_mapping={
                fetchers.ALL_BALANCES_LIVE_BOF.fetcher_id: BalancesObservation(
                    balances=account_bals,
                    value_datetime=effective_datetime,
                    at_datetime=effective_datetime,
                )
            },
            creation_date=effective_datetime,
            max_bal_limit=Decimal(100),
        )
        state = state_utils.initialise_state(
            vault=mock_vault,
            effective_datetime=effective_datetime,
            parameters={
                denomination_module.DENOMINATION_PARAM.id: DEFAULT_DENOMINATION,
            },
        )
        expected_rejection = Rejection(
            message=f"Posting would exceed maximum permitted balance 100 {DEFAULT_DENOMINATION}.",
            reason_code=RejectionReason.AGAINST_TNC,
        )
        self._negative_test_case(
            expected_rejection=expected_rejection,
            state=state,
            posting_instructions=posting_instructions,
        )

    @pytest.mark.unit
    def test_maximum_balance_limit_exceeded(
        self,
    ):
        posting_instructions = [
            self.inbound_hard_settlement(denomination=DEFAULT_DENOMINATION, amount=Decimal(101))
        ]
        account_bals: BalanceDefaultDict = self.balances()
        effective_datetime = datetime(2026, 1, 1, tzinfo=UTC)
        mock_vault = self._simple_mock(
            balances_observation_fetchers_mapping={
                fetchers.ALL_BALANCES_LIVE_BOF.fetcher_id: BalancesObservation(
                    balances=account_bals,
                    value_datetime=effective_datetime,
                    at_datetime=effective_datetime,
                )
            },
            creation_date=effective_datetime,
            max_bal_limit=Decimal(100),
        )
        state = state_utils.initialise_state(
            vault=mock_vault,
            effective_datetime=effective_datetime,
            parameters={
                denomination_module.DENOMINATION_PARAM.id: DEFAULT_DENOMINATION,
            },
        )
        expected_rejection = Rejection(
            message=f"Posting would exceed maximum permitted balance 100 {DEFAULT_DENOMINATION}.",
            reason_code=RejectionReason.AGAINST_TNC,
        )
        self._negative_test_case(
            expected_rejection=expected_rejection,
            state=state,
            posting_instructions=posting_instructions,
        )

    @pytest.mark.unit
    def test_maximum_balance_limit_not_exceeded(
        self,
    ):
        posting_instructions = [
            self.inbound_hard_settlement(denomination=DEFAULT_DENOMINATION, amount=Decimal(99))
        ]
        account_bals: BalanceDefaultDict = self.balances()
        effective_datetime = datetime(2026, 1, 1, tzinfo=UTC)
        mock_vault = self._simple_mock(
            balances_observation_fetchers_mapping={
                fetchers.ALL_BALANCES_LIVE_BOF.fetcher_id: BalancesObservation(
                    balances=account_bals,
                    value_datetime=effective_datetime,
                    at_datetime=effective_datetime,
                )
            },
            creation_date=effective_datetime,
            max_bal_limit=Decimal(100),
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
            posting_instructions=posting_instructions,
        )

    @pytest.mark.unit
    def test_maximum_balance_limit_exceeded_already_over(
        self,
    ):
        posting_instructions = [
            self.inbound_hard_settlement(denomination=DEFAULT_DENOMINATION, amount=Decimal(1))
        ]
        account_bals: BalanceDefaultDict = self.balances(default_committed=Decimal(100))
        effective_datetime = datetime(2026, 1, 1, tzinfo=UTC)
        mock_vault = self._simple_mock(
            balances_observation_fetchers_mapping={
                fetchers.ALL_BALANCES_LIVE_BOF.fetcher_id: BalancesObservation(
                    balances=account_bals,
                    value_datetime=effective_datetime,
                    at_datetime=effective_datetime,
                )
            },
            creation_date=effective_datetime,
            max_bal_limit=Decimal(100),
        )
        state = state_utils.initialise_state(
            vault=mock_vault,
            effective_datetime=effective_datetime,
            parameters={
                denomination_module.DENOMINATION_PARAM.id: DEFAULT_DENOMINATION,
            },
        )
        result = maximum_balance_limit.validate(
            state=state,
            postings=posting_instructions,
        )
        expected_rejection = Rejection(
            message=f"Posting would exceed maximum permitted balance 100 {DEFAULT_DENOMINATION}.",
            reason_code=RejectionReason.AGAINST_TNC,
        )
        self.assertEqual(result, expected_rejection)

        result_2 = maximum_balance_limit.validate(
            state=state,
            postings=posting_instructions,
            fetchers_config=maximum_balance_limit.DEFAULT_MAXIMUM_BALANCE_LIMIT_FETCHERS_CONFIG,
        )
        self.assertEqual(result_2, expected_rejection)
