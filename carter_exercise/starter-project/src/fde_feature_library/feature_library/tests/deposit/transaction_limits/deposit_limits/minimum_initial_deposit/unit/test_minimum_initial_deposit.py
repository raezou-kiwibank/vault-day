# standard libs
from datetime import datetime
from decimal import Decimal
from unittest.mock import MagicMock
from zoneinfo import ZoneInfo

import pytest

# features
import feature_library.common.denomination as denomination_module
import feature_library.common.fetchers as fetchers
import feature_library.common.state_utils as state_utils
from feature_library.common.posting_utils import PostingInstructionListAlias
from feature_library.deposit.transaction_limits.deposit_limits import minimum_initial_deposit

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

from tests.deposit.transaction_limits.deposit_limits.test_common_transaction_limit import (
    CommonTransactionLimitTest,
)

UTC = ZoneInfo("UTC")


class TestMinimumInitialDeposit(CommonTransactionLimitTest):
    def _simple_mock(
        self,
        balances_observation_fetchers_mapping: dict[str, BalancesObservation] | None = None,
        creation_date: datetime = DEFAULT_DATETIME,
        min_initial_deposit: Decimal | None = None,
    ) -> MagicMock:
        return super().create_mock(
            balances_observation_fetchers_mapping=balances_observation_fetchers_mapping,
            creation_date=creation_date,
            parameters_observation_fetchers_mapping={
                minimum_initial_deposit.MIN_INITIAL_DEPOSIT_POF.fetcher_id: ParametersObservation(
                    parameters={
                        minimum_initial_deposit.MIN_INITIAL_DEPOSIT_PARAM.id: min_initial_deposit
                    },
                    value_datetime=creation_date,
                )
            },
        )

    def _positive_test_case(
        self,
        state: state_utils.SmartContractState,
        posting_instructions: PostingInstructionListAlias,
        min_initial_deposit: Decimal,
    ):
        self.assertIsNone(
            minimum_initial_deposit.validate(
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
                    if k != minimum_initial_deposit.MIN_INITIAL_DEPOSIT_PARAM.id
                },
                "alternate_param_id": min_initial_deposit,
            },
        )
        self.assertIsNone(
            minimum_initial_deposit.validate(
                state=alternate_state,
                postings=posting_instructions,
                minimum_initial_deposit_param_id="alternate_param_id",
            )
        )
        self.assertIsNone(
            minimum_initial_deposit.validate(
                state=state,
                postings=posting_instructions,
                balance_fetcher_id=fetchers.ALL_BALANCES_LIVE_BOF.fetcher_id,
                param_fetcher_id=minimum_initial_deposit.MIN_INITIAL_DEPOSIT_POF.fetcher_id,
            )
        )

    def _negative_test_case(
        self,
        expected_rejection: Rejection,
        state: state_utils.SmartContractState,
        posting_instructions: PostingInstructionListAlias,
        min_initial_deposit: Decimal,
    ):
        result = minimum_initial_deposit.validate(
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
                    if k != minimum_initial_deposit.MIN_INITIAL_DEPOSIT_PARAM.id
                },
                "alternate_param_id": min_initial_deposit,
            },
        )
        result_2 = minimum_initial_deposit.validate(
            state=alternate_state,
            postings=posting_instructions,
            minimum_initial_deposit_param_id="alternate_param_id",
        )
        self.assertEqual(result_2, expected_rejection)

        result_3 = minimum_initial_deposit.validate(
            state=state,
            postings=posting_instructions,
            balance_fetcher_id=fetchers.ALL_BALANCES_LIVE_BOF.fetcher_id,
            param_fetcher_id=minimum_initial_deposit.MIN_INITIAL_DEPOSIT_POF.fetcher_id,
        )
        self.assertEqual(result_3, expected_rejection)

    @pytest.mark.unit
    def test_minimum_initial_deposit_ignore_withdrawal(self):
        postings = [
            self.outbound_hard_settlement(denomination=DEFAULT_DENOMINATION, amount=Decimal(1000))
        ]
        account_bals: BalanceDefaultDict = self.balances(default_committed=Decimal(1))
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
            min_initial_deposit=Decimal(20),
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
            min_initial_deposit=Decimal(20),
        )

    @pytest.mark.unit
    def test_minimum_initial_deposit_with_single_posting_not_met(self):
        postings = [
            self.inbound_hard_settlement(denomination=DEFAULT_DENOMINATION, amount=Decimal(19))
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
            min_initial_deposit=Decimal(20),
        )
        state = state_utils.initialise_state(
            vault=mock_vault,
            effective_datetime=effective_datetime,
            parameters={
                denomination_module.DENOMINATION_PARAM.id: DEFAULT_DENOMINATION,
            },
        )
        expected_rejection = Rejection(
            message=f"Transaction amount 19.00 {DEFAULT_DENOMINATION} is less than the minimum "
            f"initial deposit amount 20.00 {DEFAULT_DENOMINATION}.",
            reason_code=RejectionReason.AGAINST_TNC,
        )
        self._negative_test_case(
            expected_rejection=expected_rejection,
            state=state,
            posting_instructions=postings,
            min_initial_deposit=Decimal(20),
        )

    @pytest.mark.unit
    def test_minimum_initial_deposit_with_single_posting_met(self):
        postings = [
            self.inbound_hard_settlement(denomination=DEFAULT_DENOMINATION, amount=Decimal(20))
        ]
        account_bals: BalanceDefaultDict = self.balances(default_committed=Decimal(1))
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
            min_initial_deposit=Decimal(20),
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
            min_initial_deposit=Decimal(20),
        )

    @pytest.mark.unit
    def test_minimum_initial_deposit_not_met_but_balance_exists(self):
        postings = [
            self.inbound_hard_settlement(denomination=DEFAULT_DENOMINATION, amount=Decimal(1))
        ]
        account_bals: BalanceDefaultDict = self.balances(default_committed=Decimal(19))
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
            min_initial_deposit=Decimal(20),
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
            min_initial_deposit=Decimal(20),
        )

    @pytest.mark.unit
    def test_no_rejection_when_net_affect_of_multiple_postings_is_equal_to_the_min_initial_deposit(
        self,
    ):
        postings = [
            self.inbound_hard_settlement(denomination=DEFAULT_DENOMINATION, amount=Decimal("10")),
            self.inbound_hard_settlement(denomination=DEFAULT_DENOMINATION, amount=Decimal("5")),
            self.inbound_hard_settlement(denomination=DEFAULT_DENOMINATION, amount=Decimal("5")),
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
            min_initial_deposit=Decimal(20),
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
            min_initial_deposit=Decimal(20),
        )

    @pytest.mark.unit
    def test_no_rejection_when_net_affect_of_multiple_postings_is_above_the_min_initial_deposit(
        self,
    ):
        postings = [
            self.inbound_hard_settlement(denomination=DEFAULT_DENOMINATION, amount=Decimal("11")),
            self.inbound_hard_settlement(denomination=DEFAULT_DENOMINATION, amount=Decimal("5")),
            self.inbound_hard_settlement(denomination=DEFAULT_DENOMINATION, amount=Decimal("5")),
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
            min_initial_deposit=Decimal(20),
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
            min_initial_deposit=Decimal(20),
        )

    @pytest.mark.unit
    def test_rejection_raised_when_net_affect_of_multiple_postings_is_below_the_min_initial_deposit(
        self,
    ):
        postings = [
            self.inbound_hard_settlement(denomination=DEFAULT_DENOMINATION, amount=Decimal("20")),
            self.outbound_hard_settlement(denomination=DEFAULT_DENOMINATION, amount=Decimal("20")),
            self.inbound_hard_settlement(denomination=DEFAULT_DENOMINATION, amount=Decimal("5")),
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
            min_initial_deposit=Decimal(20),
        )
        state = state_utils.initialise_state(
            vault=mock_vault,
            effective_datetime=effective_datetime,
            parameters={
                denomination_module.DENOMINATION_PARAM.id: DEFAULT_DENOMINATION,
            },
        )
        expected_rejection = Rejection(
            message="Transaction amount 5.00 GBP is less than the "
            "minimum initial deposit amount 20.00 GBP.",
            reason_code=RejectionReason.AGAINST_TNC,
        )
        self._negative_test_case(
            expected_rejection=expected_rejection,
            state=state,
            posting_instructions=postings,
            min_initial_deposit=Decimal(20),
        )
