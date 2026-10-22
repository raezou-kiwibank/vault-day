# standard libs
from datetime import datetime
from decimal import Decimal
from unittest.mock import MagicMock
from zoneinfo import ZoneInfo

import pytest

import feature_library.common.denomination as denomination_module

# features
# features
import feature_library.common.fetchers as fetchers
import feature_library.deposit.fees.inactivity_fee as inactivity_fee_module

# contracts api
from contracts_api import (
    DEFAULT_ADDRESS,
    DEFAULT_ASSET,
    Balance,
    BalanceCoordinate,
    BalanceDefaultDict,
    BalancesObservation,
    CustomInstruction,
    FlagsObservation,
    ParametersObservation,
    Phase,
    Posting,
    ScheduleExpression,
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
INACTIVITY_FEE_INCOME_ACCOUNT = "INACTIVITY_FEE_INCOME"
ACCOUNT_TYPE = "account_type"


def none_to_zero(d: Decimal | None = None) -> Decimal:
    return d if d is not None else Decimal(0)


class InactivityFeeTest(FeatureTest):
    def setup_mock_data(
        self,
        account_creation_datetime: datetime = DEFAULT_DATETIME,
        effective_datetime: datetime = DEFAULT_DATETIME,
        inactivity_fee: Decimal | None = Decimal(0),
        inactivity_fee_income_account: str | None = "INACTIVITY_FEE_INCOME_ACCOUNT",
        inactivity_flags: str | None = '["ACCOUNT_INACTIVE"]',
        active_flags: list[str] | None = None,
        default_bal: Decimal | None = None,
        denomination: str | None = DEFAULT_DENOMINATION,
    ):
        default_bal = none_to_zero(default_bal)
        self.effective_datetime = effective_datetime
        active_flags = active_flags or []

        denom_params = {}
        if denomination is not None:
            denom_params[denomination_module.DENOMINATION_PARAM.id] = denomination

        inactivity_fees_params = {
            inactivity_fee_module.INACTIVITY_FEE_APPLICATION_DAY_PARAM.id: "1",
            inactivity_fee_module.INACTIVITY_FEE_APPLICATION_TIME_PARAM.id: "00:00:01",
        }
        if inactivity_fee is not None:
            inactivity_fees_params[inactivity_fee_module.INACTIVITY_FEE_PARAM.id] = inactivity_fee
        if inactivity_fee_income_account is not None:
            inactivity_fees_params[inactivity_fee_module.INACTIVITY_FEE_INCOME_ACCOUNT_PARAM.id] = (
                inactivity_fee_income_account
            )
        if inactivity_flags is not None:
            inactivity_fees_params[inactivity_fee_module.INACTIVITY_FLAGS_PARAM.id] = (
                inactivity_flags
            )

        params_obs: dict[str, ParametersObservation] = {
            denomination_module.DENOMINATION_ET_POF.fetcher_id: ParametersObservation(
                parameters=denom_params, value_datetime=effective_datetime
            ),
            inactivity_fee_module.INACTIVITY_FEE_POF.fetcher_id: ParametersObservation(
                parameters=inactivity_fees_params,
                value_datetime=effective_datetime,
            ),
        }

        flags_obs_mapping = {
            inactivity_fee_module.INACTIVITY_FOF_ID: FlagsObservation(
                flags=dict.fromkeys(active_flags, True),
                value_datetime=effective_datetime,
            )
        }

        default_bals = BalanceDefaultDict(
            lambda: Balance(),
            {
                BalanceCoordinate(
                    DEFAULT_ADDRESS, DEFAULT_ASSET, self.default_denomination, Phase.COMMITTED
                ): Balance(default_bal, Decimal(0), default_bal),
            },
        )
        self.mock_vault = self.create_mock(
            account_id=ACCOUNT_ID,
            activation_datetime=account_creation_datetime,
            balances_observation_fetchers_mapping={
                fetchers.ALL_BALANCES_ET_BOF.fetcher_id: BalancesObservation(
                    balances=default_bals,
                    value_datetime=effective_datetime,
                    at_datetime=effective_datetime,
                ),
            },
            creation_date=account_creation_datetime,
            parameters_observation_fetchers_mapping=params_obs,
            flags_observation_fetchers_mapping=flags_obs_mapping,
        )
        self.state = MagicMock(
            vault=self.mock_vault,
            effective_datetime=effective_datetime,
            parameters=inactivity_fees_params | denom_params,
            balances=default_bals,
        )

    @pytest.mark.unit
    def test_apply_fees_raises_assertion_error_if_parameter_missing(self):
        params_to_test = [
            ("inactivity_fee", {"inactivity_fee": None}),
            ("inactivity_fee_income_account", {"inactivity_fee_income_account": None}),
            ("inactivity_flags", {"inactivity_flags": None}),
            ("denomination", {"denomination": None}),
        ]

        for param_name, setup_kwargs in params_to_test:
            with self.subTest(missing_param=param_name):
                self.setup_mock_data(**setup_kwargs)  # type: ignore
                with self.assertRaises(AssertionError) as cm:
                    inactivity_fee_module.apply_fees(
                        state=self.state,
                        account_type=ACCOUNT_TYPE,
                    )
                self.assertIn("parameters are missing: ", str(cm.exception))

    @pytest.mark.unit
    def test_inactivity_fee_applied_if_flag_active(
        self,
    ):
        inactivity_fee = Decimal(10)
        self.setup_mock_data(
            inactivity_fee=inactivity_fee,
            inactivity_fee_income_account=INACTIVITY_FEE_INCOME_ACCOUNT,
            active_flags=["ACCOUNT_INACTIVE"],
        )
        result = inactivity_fee_module.apply_fees(
            state=self.state,
            account_type=ACCOUNT_TYPE,
        )
        expected = [
            CustomInstruction(
                postings=[
                    Posting(
                        credit=False,
                        amount=inactivity_fee,
                        denomination=self.default_denomination,
                        account_id=ACCOUNT_ID,
                        account_address=DEFAULT_ADDRESS,
                        asset=DEFAULT_ASSET,
                        phase=Phase.COMMITTED,
                    ),
                    Posting(
                        credit=True,
                        amount=inactivity_fee,
                        denomination=self.default_denomination,
                        account_id=INACTIVITY_FEE_INCOME_ACCOUNT,
                        account_address=DEFAULT_ADDRESS,
                        asset=DEFAULT_ASSET,
                        phase=Phase.COMMITTED,
                    ),
                ],
                instruction_details={
                    "description": "Monthly Inactivity Fee Application",
                    "event": "APPLY_INACTIVITY_FEE",
                    "gl_impacted": str(True),
                    "account_type": ACCOUNT_TYPE,
                },
                value_datetime=self.effective_datetime,
                override_all_restrictions=True,
            )
        ]
        self.assertListEqual(result, expected)

    @pytest.mark.unit
    def test_inactivity_fee_not_applied_if_no_flag(
        self,
    ):
        self.setup_mock_data(
            inactivity_fee=Decimal(10),
            inactivity_fee_income_account=INACTIVITY_FEE_INCOME_ACCOUNT,
            active_flags=[],
        )
        result = inactivity_fee_module.apply_fees(
            state=self.state,
            account_type=ACCOUNT_TYPE,
        )

        self.assertEqual(len(result), 0)

    @pytest.mark.unit
    def test_inactivity_fee_not_applied_if_zero_fee(
        self,
    ):
        self.setup_mock_data(
            inactivity_fee=Decimal(0),
            inactivity_fee_income_account=INACTIVITY_FEE_INCOME_ACCOUNT,
            active_flags=["ACCOUNT_INACTIVE"],
        )

        result = inactivity_fee_module.apply_fees(
            state=self.state,
            account_type=ACCOUNT_TYPE,
        )

        self.assertEqual(len(result), 0)

    @pytest.mark.unit
    def test_update_next_schedule_execution(self):
        self.setup_mock_data()
        result = inactivity_fee_module.update_next_schedule_execution(state=self.state)

        self.assertIsNotNone(result)
        self.assertEqual(result.event_type, inactivity_fee_module.APPLICATION_EVENT)
        self.assertEqual(
            result.expression, ScheduleExpression(day=1, month=2, hour=0, minute=0, second=1)
        )

    @pytest.mark.unit
    def test_schedule_logic(self):
        inactivity_fee = Decimal(10)
        self.setup_mock_data(
            inactivity_fee=inactivity_fee,
            inactivity_fee_income_account=INACTIVITY_FEE_INCOME_ACCOUNT,
            active_flags=["ACCOUNT_INACTIVE"],
        )
        result = inactivity_fee_module.schedule_logic(
            state=self.state,
            account_type=ACCOUNT_TYPE,
        )

        # check custom instruction is returned (fee applied)
        self.assertEqual(len(result.custom_instructions), 1)
        self.assertEqual(
            result.custom_instructions[0].instruction_details["description"],
            "Monthly Inactivity Fee Application",
        )

        # check event directive is returned
        self.assertEqual(len(result.event_type_directives), 1)
        self.assertEqual(
            result.event_type_directives[0].event_type, inactivity_fee_module.APPLICATION_EVENT
        )
        self.assertEqual(
            result.event_type_directives[0].expression,
            ScheduleExpression(day=1, month=2, hour=0, minute=0, second=1),
        )
