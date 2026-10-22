# ruff: noqa: E501
# standard libs
import json
from datetime import datetime
from decimal import Decimal
from unittest.mock import MagicMock
from zoneinfo import ZoneInfo

import pytest

import feature_library.common.denomination as denomination_module

# features
import feature_library.common.fetchers as fetchers
import feature_library.common.state_utils as state_utils
import feature_library.deposit.common as withdrawal_limits_common
from feature_library.deposit.transaction_limits.withdrawal_limits import (
    minimum_balance_by_tier,
)

# contracts api
from contracts_api import (
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


class TestMinimumBalanceByTier(CommonTransactionLimitTest):
    def _simple_mock(
        self,
        creation_date: datetime = DEFAULT_DATETIME,
        tiered_minimum_balance_threshold: str | None = None,
        account_tier: str | None = "STANDARD",
        balances: BalancesObservation | None = None,
    ) -> MagicMock:
        return super().create_mock(
            creation_date=creation_date,
            parameters_observation_fetchers_mapping={
                minimum_balance_by_tier.MIN_BALANCE_BY_TIER_POF.fetcher_id: ParametersObservation(
                    parameters={
                        minimum_balance_by_tier.TIERED_MIN_BALANCE_THRESHOLD_PARAM.id: tiered_minimum_balance_threshold,  # noqa: E501
                        withdrawal_limits_common.ACCOUNT_TIER_PARAM.id: account_tier,
                    },
                    value_datetime=creation_date,
                )
            },
            balances_observation_fetchers_mapping={fetchers.ALL_BALANCES_LIVE_BOF_ID: balances},  # type: ignore
        )

    def _positive_test_case(
        self,
        state: state_utils.SmartContractState,
        postings: list,
    ):
        self.assertIsNone(
            minimum_balance_by_tier.validate(
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
                    if k != minimum_balance_by_tier.TIERED_MIN_BALANCE_THRESHOLD_PARAM.id
                },
                "alternate_param_id": json.dumps({"STANDARD": "0", "SAVINGS": "100"}),
                withdrawal_limits_common.ACCOUNT_TIER_PARAM.id: state.parameters.get(
                    withdrawal_limits_common.ACCOUNT_TIER_PARAM.id
                ),
            },
        )
        self.assertIsNone(
            minimum_balance_by_tier.validate(
                state=alternate_state,
                postings=postings,
                fetchers_config=minimum_balance_by_tier.MinimumBalanceByTierFetchersConfig(
                    param_fetcher_id=minimum_balance_by_tier.MIN_BALANCE_BY_TIER_POF_ID,
                    balances_fetcher_id=fetchers.ALL_BALANCES_LIVE_BOF_ID,
                    denomination_param_id=denomination_module.DENOMINATION_PARAM_ID,
                    account_tier_param_id=withdrawal_limits_common.ACCOUNT_TIER_PARAM.id,
                    tiered_minimum_balance_threshold_param_id="alternate_param_id",
                ),
            )
        )

    def _negative_test_case(
        self,
        expected_rejection: Rejection,
        state: state_utils.SmartContractState,
        postings: list,
    ):
        result = minimum_balance_by_tier.validate(
            state=state,
            postings=postings,
        )
        self.assertEqual(result, expected_rejection)

        alternate_state = state_utils.initialise_state(
            vault=state.vault,
            effective_datetime=state.effective_datetime,
            parameters={
                **{
                    k: v
                    for k, v in state.parameters.items()
                    if k != minimum_balance_by_tier.TIERED_MIN_BALANCE_THRESHOLD_PARAM.id
                },
                "alternate_param_id": json.dumps({"STANDARD": "0", "SAVINGS": "100"}),
                withdrawal_limits_common.ACCOUNT_TIER_PARAM.id: state.parameters.get(
                    withdrawal_limits_common.ACCOUNT_TIER_PARAM.id
                ),
            },
        )
        result_2 = minimum_balance_by_tier.validate(
            state=alternate_state,
            postings=postings,
            fetchers_config=minimum_balance_by_tier.MinimumBalanceByTierFetchersConfig(
                param_fetcher_id=minimum_balance_by_tier.MIN_BALANCE_BY_TIER_POF_ID,
                balances_fetcher_id=fetchers.ALL_BALANCES_LIVE_BOF_ID,
                denomination_param_id=denomination_module.DENOMINATION_PARAM_ID,
                account_tier_param_id=withdrawal_limits_common.ACCOUNT_TIER_PARAM.id,
                tiered_minimum_balance_threshold_param_id="alternate_param_id",
            ),
        )
        self.assertEqual(result_2, expected_rejection)

    @pytest.mark.unit
    def test_account_tier_minimum_balance_exceeded(self):
        effective_datetime = datetime(2026, 1, 1, 12, tzinfo=UTC)
        posting_instructions = [self.outbound_hard_settlement(amount=Decimal("1"))]

        mock_vault = self._simple_mock(
            creation_date=effective_datetime,
            tiered_minimum_balance_threshold=json.dumps({"STANDARD": "0", "SAVINGS": "100"}),
            account_tier="SAVINGS",
            balances=BalancesObservation(
                balances=self.balances(default_committed=Decimal("100")),
                value_datetime=effective_datetime,
            ),
        )
        state = state_utils.initialise_state(
            vault=mock_vault,
            effective_datetime=effective_datetime,
            parameters={
                denomination_module.DENOMINATION_PARAM.id: DEFAULT_DENOMINATION,
                withdrawal_limits_common.ACCOUNT_TIER_PARAM.id: "SAVINGS",
            },
        )
        expected_rejection = Rejection(
            message="Transaction amount -1 GBP will result in the account balance falling "
            "below the minimum permitted of 100 GBP.",
            reason_code=RejectionReason.AGAINST_TNC,
        )

        self._negative_test_case(
            expected_rejection=expected_rejection,
            state=state,
            postings=posting_instructions,
        )

    @pytest.mark.unit
    def test_account_tier_minimum_balance_not_exceeded(self):
        effective_datetime = datetime(2026, 1, 1, 12, tzinfo=UTC)
        posting_instructions = [self.outbound_hard_settlement(amount=Decimal("99"))]

        mock_vault = self._simple_mock(
            creation_date=effective_datetime,
            tiered_minimum_balance_threshold=json.dumps({"STANDARD": "0", "SAVINGS": "100"}),
            account_tier="STANDARD",
            balances=BalancesObservation(
                balances=self.balances(default_committed=Decimal("100")),
                value_datetime=effective_datetime,
            ),
        )
        state = state_utils.initialise_state(
            vault=mock_vault,
            effective_datetime=effective_datetime,
            parameters={
                denomination_module.DENOMINATION_PARAM.id: DEFAULT_DENOMINATION,
                withdrawal_limits_common.ACCOUNT_TIER_PARAM.id: "STANDARD",
            },
        )
        self._positive_test_case(
            state=state,
            postings=posting_instructions,
        )

    @pytest.mark.unit
    def test_account_tier_minimum_balance_exceeded_below_zero(self):
        effective_datetime = datetime(2026, 1, 1, 12, tzinfo=UTC)
        posting_instructions = [self.outbound_hard_settlement(amount=Decimal("101"))]

        mock_vault = self._simple_mock(
            creation_date=effective_datetime,
            tiered_minimum_balance_threshold=json.dumps({"STANDARD": "0", "SAVINGS": "100"}),
            account_tier="STANDARD",
            balances=BalancesObservation(
                balances=self.balances(default_committed=Decimal("100")),
                value_datetime=effective_datetime,
            ),
        )
        state = state_utils.initialise_state(
            vault=mock_vault,
            effective_datetime=effective_datetime,
            parameters={
                denomination_module.DENOMINATION_PARAM.id: DEFAULT_DENOMINATION,
                withdrawal_limits_common.ACCOUNT_TIER_PARAM.id: "STANDARD",
            },
        )
        expected_rejection = Rejection(
            message="Transaction amount -101 GBP will result in the account balance "
            "falling below the minimum permitted of 0 GBP.",
            reason_code=RejectionReason.AGAINST_TNC,
        )

        self._negative_test_case(
            expected_rejection=expected_rejection,
            state=state,
            postings=posting_instructions,
        )

    @pytest.mark.unit
    def test_account_tier_minimum_balance_multi_postings_limit_not_exceeded(self):
        effective_datetime = datetime(2026, 1, 1, 12, tzinfo=UTC)
        posting_instructions = [
            self.inbound_hard_settlement(amount=Decimal("50")),
            self.outbound_hard_settlement(amount=Decimal("50")),
            self.outbound_hard_settlement(amount=Decimal("50")),
            self.outbound_hard_settlement(amount=Decimal("50")),
        ]

        mock_vault = self._simple_mock(
            creation_date=effective_datetime,
            tiered_minimum_balance_threshold=json.dumps({"STANDARD": "0", "SAVINGS": "100"}),
            account_tier="STANDARD",
            balances=BalancesObservation(
                balances=self.balances(default_committed=Decimal("100")),
                value_datetime=effective_datetime,
            ),
        )
        state = state_utils.initialise_state(
            vault=mock_vault,
            effective_datetime=effective_datetime,
            parameters={
                denomination_module.DENOMINATION_PARAM.id: DEFAULT_DENOMINATION,
                withdrawal_limits_common.ACCOUNT_TIER_PARAM.id: "STANDARD",
            },
        )
        self._positive_test_case(
            state=state,
            postings=posting_instructions,
        )

    @pytest.mark.unit
    def test_account_tier_minimum_balance_multi_postings_limit_exceeded(self):
        effective_datetime = datetime(2026, 1, 1, 12, tzinfo=UTC)
        posting_instructions = [
            self.inbound_hard_settlement(amount=Decimal("50")),
            self.outbound_hard_settlement(amount=Decimal("50")),
            self.outbound_hard_settlement(amount=Decimal("50")),
            self.outbound_hard_settlement(amount=Decimal("50.01")),
        ]

        mock_vault = self._simple_mock(
            creation_date=effective_datetime,
            tiered_minimum_balance_threshold=json.dumps({"STANDARD": "0", "SAVINGS": "100"}),
            account_tier="STANDARD",
            balances=BalancesObservation(
                balances=self.balances(default_committed=Decimal("100")),
                value_datetime=effective_datetime,
            ),
        )
        state = state_utils.initialise_state(
            vault=mock_vault,
            effective_datetime=effective_datetime,
            parameters={
                denomination_module.DENOMINATION_PARAM.id: DEFAULT_DENOMINATION,
                withdrawal_limits_common.ACCOUNT_TIER_PARAM.id: "STANDARD",
            },
        )
        expected_rejection = Rejection(
            message="Transaction amount -100.01 GBP will result in the account balance "
            "falling below the minimum permitted of 0 GBP.",
            reason_code=RejectionReason.AGAINST_TNC,
        )

        self._negative_test_case(
            expected_rejection=expected_rejection,
            state=state,
            postings=posting_instructions,
        )
