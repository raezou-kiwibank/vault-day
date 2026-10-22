# Copyright @ 2023 - 2026 Thought Machine Group Limited. All rights reserved.

# standard libs
from datetime import datetime
from decimal import Decimal
from unittest.mock import MagicMock
from zoneinfo import ZoneInfo

import pytest
from dateutil.relativedelta import relativedelta

import feature_library.common.denomination as denomination_module

# features
import feature_library.deposit.fees.early_closure_fee as early_closure_fee_module

# contracts api
from contracts_api import (
    DEFAULT_ADDRESS,
    DEFAULT_ASSET,
    Balance,
    BalanceCoordinate,
    BalanceDefaultDict,
    BalancesObservation,
    CustomInstruction,
    ParametersObservation,
    Phase,
    Posting,
)

# inception sdk
from inception_sdk.test_framework.contracts.unit.common import (
    ACCOUNT_ID,
    FeatureTest,
)

from tests.common.test_denomination import DEFAULT_DENOMINATION

UTC_ZONE = ZoneInfo("UTC")
DEFAULT_DATETIME = datetime(2026, 1, 1, tzinfo=UTC_ZONE)

DENOMINATION = DEFAULT_DENOMINATION
EARLY_CLOSURE_FEE_INCOME_ACCOUNT = "EARLY_CLOSURE_FEE_INCOME"
ACCOUNT_TYPE = "account_type"


def none_to_zero(d: Decimal | None = None) -> Decimal:
    return d if d is not None else Decimal(0)


class EarlyClosureFeeTest(FeatureTest):
    def setup_mock_data(
        self,
        account_creation_datetime: datetime = DEFAULT_DATETIME,
        effective_datetime: datetime = DEFAULT_DATETIME,
        early_closure_days: int = 0,
        early_closure_fee: Decimal = Decimal(0),
        early_closure_fee_income_account: str = "EARLY_CLOSURE_FEE_INCOME_ACCOUNT",
        default_bal: Decimal | None = None,
        early_closure_fees_tracker_bal: Decimal | None = None,
    ):
        default_bal = none_to_zero(default_bal)
        early_closure_fees_tracker_bal = none_to_zero(early_closure_fees_tracker_bal)
        self.effective_datetime = effective_datetime
        # mock vault
        denom_params = {denomination_module.DENOMINATION_PARAM.id: self.default_denomination}
        early_closure_fees_params = {
            early_closure_fee_module.EARLY_CLOSURE_DAYS_PARAM.id: early_closure_days,
            early_closure_fee_module.EARLY_CLOSURE_FEE_PARAM.id: none_to_zero(early_closure_fee),
            early_closure_fee_module.EARLY_CLOSURE_FEE_INCOME_ACCOUNT_PARAM.id: early_closure_fee_income_account,  # noqa: E501
        }
        params_obs: dict[str, ParametersObservation] = {
            denomination_module.DENOMINATION_ET_POF.fetcher_id: ParametersObservation(
                parameters=denom_params, value_datetime=effective_datetime
            ),
            early_closure_fee_module.EARLY_CLOSURE_FEES_POF.fetcher_id: ParametersObservation(
                parameters=early_closure_fees_params,  # ty: ignore[invalid-argument-type]
                value_datetime=effective_datetime,
            ),
        }
        default_bals = BalanceDefaultDict(
            lambda: Balance(),
            {
                BalanceCoordinate(
                    DEFAULT_ADDRESS, DEFAULT_ASSET, self.default_denomination, Phase.COMMITTED
                ): Balance(default_bal, Decimal(0), default_bal),
                BalanceCoordinate(
                    early_closure_fee_module.EARLY_CLOSURE_FEE_ADDRESS,
                    DEFAULT_ASSET,
                    self.default_denomination,
                    Phase.COMMITTED,
                ): Balance(
                    early_closure_fees_tracker_bal, early_closure_fees_tracker_bal, Decimal(0)
                ),
            },
        )
        self.mock_vault = self.create_mock(
            account_id=ACCOUNT_ID,
            activation_datetime=account_creation_datetime,
            balances_observation_fetchers_mapping={
                early_closure_fee_module.fetchers.ALL_BALANCES_ET_BOF.fetcher_id: BalancesObservation(  # noqa: E501
                    balances=default_bals,
                    value_datetime=effective_datetime,
                    at_datetime=effective_datetime,
                ),
            },
            creation_date=account_creation_datetime,
            parameters_observation_fetchers_mapping=params_obs,
        )
        self.state = MagicMock(
            vault=self.mock_vault,
            effective_datetime=effective_datetime,
            parameters=early_closure_fees_params | denom_params,
            balances=default_bals,
        )

    @pytest.mark.unit
    def test_early_closure_fee_not_applied_if_closed_after_closure_days(
        self,
    ):
        account_creation_datetime = DEFAULT_DATETIME
        effective_datetime = account_creation_datetime + relativedelta(days=8)
        self.setup_mock_data(
            account_creation_datetime=DEFAULT_DATETIME,
            effective_datetime=effective_datetime,
            early_closure_fee=Decimal(10),
            early_closure_days=7,
            early_closure_fee_income_account=EARLY_CLOSURE_FEE_INCOME_ACCOUNT,
        )
        result = early_closure_fee_module.apply_fees(
            state=self.state,
            account_type=ACCOUNT_TYPE,
        )
        self.assertEqual(len(result.custom_instructions), 0)
        self.assertIsNone(result.rejection)

    @pytest.mark.unit
    def test_early_closure_fee_applied_if_closed_within_closure_days(
        self,
    ):
        early_closure_fee = Decimal(10)
        effective_datetime = DEFAULT_DATETIME + relativedelta(days=6)
        self.setup_mock_data(
            account_creation_datetime=DEFAULT_DATETIME,
            effective_datetime=effective_datetime,
            early_closure_days=7,
            early_closure_fee=early_closure_fee,
            early_closure_fee_income_account=EARLY_CLOSURE_FEE_INCOME_ACCOUNT,
        )
        result = early_closure_fee_module.apply_fees(
            state=self.state,
            account_type=ACCOUNT_TYPE,
        )
        expected = [
            CustomInstruction(
                postings=[
                    Posting(
                        credit=False,
                        amount=early_closure_fee,
                        denomination=self.default_denomination,
                        account_id=ACCOUNT_ID,
                        account_address=DEFAULT_ADDRESS,
                        asset=DEFAULT_ASSET,
                        phase=Phase.COMMITTED,
                    ),
                    Posting(
                        credit=True,
                        amount=early_closure_fee,
                        denomination=self.default_denomination,
                        account_id=EARLY_CLOSURE_FEE_INCOME_ACCOUNT,
                        account_address=DEFAULT_ADDRESS,
                        asset=DEFAULT_ASSET,
                        phase=Phase.COMMITTED,
                    ),
                    Posting(
                        credit=False,
                        amount=Decimal(1),
                        denomination=self.default_denomination,
                        account_id=ACCOUNT_ID,
                        account_address=early_closure_fee_module.EARLY_CLOSURE_FEE_ADDRESS,
                        asset=DEFAULT_ASSET,
                        phase=Phase.COMMITTED,
                    ),
                    Posting(
                        credit=True,
                        amount=Decimal(1),
                        denomination=self.default_denomination,
                        account_id=ACCOUNT_ID,
                        account_address=early_closure_fee_module.EARLY_CLOSURE_FEE_ADDRESS,
                        asset=DEFAULT_ASSET,
                        phase=Phase.COMMITTED,
                    ),
                ],
                instruction_details={
                    "description": "EARLY CLOSURE FEE",
                    "event": "CLOSE_ACCOUNT",
                    "gl_impacted": str(True),
                    "account_type": ACCOUNT_TYPE,
                },
                value_datetime=effective_datetime,
                override_all_restrictions=True,
            )
        ]
        self.assertListEqual(result.custom_instructions, expected)
        self.assertIsNone(result.rejection)

    @pytest.mark.unit
    def test_early_closure_fee_not_applied_if_already_applied(
        self,
    ):
        self.setup_mock_data(
            account_creation_datetime=DEFAULT_DATETIME,
            early_closure_days=7,
            early_closure_fee=Decimal(10),
            early_closure_fee_income_account=EARLY_CLOSURE_FEE_INCOME_ACCOUNT,
            early_closure_fees_tracker_bal=Decimal(1),
        )
        result = early_closure_fee_module.apply_fees(
            state=self.state,
            account_type=ACCOUNT_TYPE,
        )

        self.assertEqual(len(result.custom_instructions), 0)
        self.assertIsNone(result.rejection)

    @pytest.mark.unit
    def test_early_closure_fee_not_applied_if_zero_fee(
        self,
    ):
        self.setup_mock_data(
            account_creation_datetime=DEFAULT_DATETIME,
            early_closure_days=7,
            early_closure_fee=Decimal(0),
            early_closure_fee_income_account=EARLY_CLOSURE_FEE_INCOME_ACCOUNT,
            early_closure_fees_tracker_bal=Decimal(1),
        )

        result = early_closure_fee_module.apply_fees(
            state=self.state,
            account_type=ACCOUNT_TYPE,
        )

        self.assertEqual(len(result.custom_instructions), 0)
        self.assertIsNone(result.rejection)


class HelpersTest(FeatureTest):
    @pytest.mark.unit
    def test_update_closure_fee_tracker(
        self,
    ):
        expected_result = [
            Posting(
                credit=False,
                amount=Decimal(1),
                denomination=DENOMINATION,
                account_id=ACCOUNT_ID,
                account_address=early_closure_fee_module.EARLY_CLOSURE_FEE_ADDRESS,
                asset=DEFAULT_ASSET,
                phase=Phase.COMMITTED,
            ),
            Posting(
                credit=True,
                amount=Decimal(1),
                denomination=DENOMINATION,
                account_id=ACCOUNT_ID,
                account_address=early_closure_fee_module.EARLY_CLOSURE_FEE_ADDRESS,
                asset=DEFAULT_ASSET,
                phase=Phase.COMMITTED,
            ),
        ]
        results = early_closure_fee_module._update_closure_fee_tracker(
            denomination=DENOMINATION,
            account_id=ACCOUNT_ID,
            account_tracker_address=early_closure_fee_module.EARLY_CLOSURE_FEE_ADDRESS,
        )

        self.assertEqual(results, expected_result)
