# standard libs
from datetime import datetime
from decimal import Decimal
from unittest.mock import MagicMock, patch, sentinel
from zoneinfo import ZoneInfo

import pytest
from dateutil.relativedelta import relativedelta

import feature_library.common.denomination as denomination_module

# features
import feature_library.common.fetchers as fetchers
import feature_library.deposit.fees.overdraft_limit as overdraft_limit
import feature_library.deposit.fees.unarranged_overdraft_fee as unarranged_overdraft_fee

# contracts api
from contracts_api import (
    DEFAULT_ADDRESS,
    DEFAULT_ASSET,
    Balance,
    BalanceCoordinate,
    BalanceDefaultDict,
    BalancesObservation,
    ParametersObservation,
    Phase,
    ScheduledEvent,
    ScheduleExpression,
)

# inception sdk
from inception_sdk.test_framework.contracts.unit.common import (
    ACCOUNT_ID,
    FeatureTest,
)

from tests.common.test_denomination import DEFAULT_DENOMINATION

# feature_library
from tests.utils import initialise_mock_state

UTC = ZoneInfo("UTC")
DEFAULT_DATETIME = datetime(2026, 1, 1, tzinfo=UTC)
UNARRANGED_OVERDRAFT_FEE_INCOME_ACCOUNT = "UNARRANGED_OVERDRAFT_FEE_INCOME_ACCOUNT"
UNARRANGED_OVERDRAFT_FEE_RECEIVABLE_ACCOUNT = "UNARRANGED_OVERDRAFT_FEE_RECEIVABLE_ACCOUNT"
ACCOUNT_TYPE = "account_type"


class UnarrangedOverdraftFeeTest(FeatureTest):
    def setup_mock_data(
        self,
        account_creation_datetime: datetime = DEFAULT_DATETIME,
        effective_datetime: datetime = DEFAULT_DATETIME,
        unarranged_overdraft_fee_param: Decimal | None = Decimal("5.00"),
        unarranged_overdraft_fee_cap: Decimal | None = Decimal("30.00"),
        arranged_overdraft_amount: Decimal | None = Decimal("100.00"),
        unarranged_overdraft_amount: Decimal | None = Decimal("300.00"),
        default_bal: Decimal | None = None,
        overdraft_fee_bal: Decimal | None = None,
        denomination: str | None = DEFAULT_DENOMINATION,
    ):
        self.effective_datetime = effective_datetime

        denom_params = {}
        if denomination is not None:
            denom_params[denomination_module.DENOMINATION_PARAM.id] = denomination

        fee_params: dict[str, str | Decimal | datetime | None] = {
            unarranged_overdraft_fee.UNARRANGED_OVERDRAFT_FEE_ACCRUAL_TIME_PARAM.id: "00:00:00",
            unarranged_overdraft_fee.UNARRANGED_OVERDRAFT_FEE_APPLICATION_DAY_PARAM.id: "1",
            unarranged_overdraft_fee.UNARRANGED_OVERDRAFT_FEE_APPLICATION_TIME_PARAM.id: "00:00:00",
        }

        if unarranged_overdraft_fee_param is not None:
            fee_params[unarranged_overdraft_fee.UNARRANGED_OVERDRAFT_FEE_PARAM.id] = (
                unarranged_overdraft_fee_param
            )
        if unarranged_overdraft_fee_cap is not None:
            fee_params[unarranged_overdraft_fee.UNARRANGED_OVERDRAFT_FEE_CAP_PARAM.id] = (
                unarranged_overdraft_fee_cap
            )
        if arranged_overdraft_amount is not None:
            fee_params[overdraft_limit.ARRANGED_OVERDRAFT_AMOUNT_PARAM.id] = (
                arranged_overdraft_amount
            )
        if unarranged_overdraft_amount is not None:
            fee_params[overdraft_limit.UNARRANGED_OVERDRAFT_AMOUNT_PARAM.id] = (
                unarranged_overdraft_amount
            )

        fee_params[unarranged_overdraft_fee.UNARRANGED_OVERDRAFT_FEE_INCOME_ACCOUNT_PARAM.id] = (
            UNARRANGED_OVERDRAFT_FEE_INCOME_ACCOUNT
        )
        fee_params[
            unarranged_overdraft_fee.UNARRANGED_OVERDRAFT_FEE_RECEIVABLE_ACCOUNT_PARAM.id
        ] = UNARRANGED_OVERDRAFT_FEE_RECEIVABLE_ACCOUNT
        params_obs: dict[str, ParametersObservation] = {
            denomination_module.DENOMINATION_ET_POF.fetcher_id: ParametersObservation(
                parameters=denom_params, value_datetime=effective_datetime
            ),
            unarranged_overdraft_fee.UNARRANGED_OVERDRAFT_FEE_POF.fetcher_id: ParametersObservation(
                parameters=fee_params,
                value_datetime=effective_datetime,
            ),
        }

        default_bal_val = default_bal if default_bal is not None else Decimal(0)
        overdraft_fee_bal_val = overdraft_fee_bal if overdraft_fee_bal is not None else Decimal(0)

        default_bals = BalanceDefaultDict(
            lambda: Balance(),
            {
                BalanceCoordinate(
                    DEFAULT_ADDRESS, DEFAULT_ASSET, DEFAULT_DENOMINATION, Phase.COMMITTED
                ): Balance(default_bal_val, Decimal(0), default_bal_val),
                BalanceCoordinate(
                    unarranged_overdraft_fee.OVERDRAFT_FEE_ADDRESS,
                    DEFAULT_ASSET,
                    DEFAULT_DENOMINATION,
                    Phase.COMMITTED,
                ): Balance(overdraft_fee_bal_val, Decimal(0), overdraft_fee_bal_val),
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
        )
        self.mock_vault.events_timezone = UTC
        self.state = MagicMock(
            vault=self.mock_vault,
            effective_datetime=effective_datetime,
            parameters=fee_params | denom_params,
            balances=default_bals,
        )

    @pytest.mark.unit
    def test_accrue_fees_raises_assertion_error_if_parameter_missing(self):
        params_to_test = [
            ("unarranged_overdraft_fee", {"unarranged_overdraft_fee_param": None}),
            ("arranged_overdraft_amount", {"arranged_overdraft_amount": None}),
            ("unarranged_overdraft_amount", {"unarranged_overdraft_amount": None}),
        ]

        for param_name, setup_kwargs in params_to_test:
            with self.subTest(missing_param=param_name):
                self.setup_mock_data(**setup_kwargs)  # type: ignore

                param_id = (
                    unarranged_overdraft_fee.UNARRANGED_OVERDRAFT_FEE_PARAM.id
                    if param_name == "unarranged_overdraft_fee"
                    else overdraft_limit.ARRANGED_OVERDRAFT_AMOUNT_PARAM.id
                    if param_name == "arranged_overdraft_amount"
                    else overdraft_limit.UNARRANGED_OVERDRAFT_AMOUNT_PARAM.id
                )
                if param_id in self.state.parameters:
                    del self.state.parameters[param_id]

                with patch.object(
                    unarranged_overdraft_fee.state_utils,
                    "check_parameters_exist",
                    return_value="Missing Param Rejection",
                ):
                    with self.assertRaises(AssertionError) as ex:
                        unarranged_overdraft_fee.accrue_fees(state=self.state)
                    self.assertEqual(ex.exception.args[0], "Missing Param Rejection")

    @patch.object(
        unarranged_overdraft_fee.accrual_utils, "create_receivable_accrual_custom_instruction"
    )
    @pytest.mark.unit
    def test_overdraft_fee_accrued(self, mock_create_payable_accrual_custom_instruction: MagicMock):
        self.setup_mock_data(
            unarranged_overdraft_fee_param=Decimal("5.00"),
            arranged_overdraft_amount=Decimal("100.00"),
            default_bal=Decimal("-150.00"),
            overdraft_fee_bal=Decimal("-10.00"),
        )

        mock_create_payable_accrual_custom_instruction.return_value = [sentinel.custom_instruction]

        result = unarranged_overdraft_fee.accrue_fees(state=self.state)

        self.assertEqual(result, [sentinel.custom_instruction])
        mock_create_payable_accrual_custom_instruction.assert_called_once_with(
            customer_account=ACCOUNT_ID,
            customer_address=unarranged_overdraft_fee.OVERDRAFT_FEE_ADDRESS,
            denomination=DEFAULT_DENOMINATION,
            amount=Decimal("5.00"),
            internal_account=UNARRANGED_OVERDRAFT_FEE_RECEIVABLE_ACCOUNT,
            instruction_details={
                "description": "Daily unarranged overdraft fee of 5.00 GBP",
                "event": unarranged_overdraft_fee.ACCRUAL_EVENT,
            },
        )

    @pytest.mark.unit
    def test_overdraft_fee_not_accrued_positive_balance(self):
        self.setup_mock_data(
            default_bal=Decimal("0.01"),
        )

        result = unarranged_overdraft_fee.accrue_fees(state=self.state)
        self.assertEqual(result, [])

    @pytest.mark.unit
    def test_overdraft_fee_not_accrued_balance_above_overdraft_limit(self):
        self.setup_mock_data(
            arranged_overdraft_amount=Decimal(100),
            default_bal=Decimal("-99.99"),
        )

        result = unarranged_overdraft_fee.accrue_fees(state=self.state)
        self.assertEqual(result, [])

    @pytest.mark.unit
    def test_overdraft_fee_not_accrued_balance_at_overdraft_limit(self):
        self.setup_mock_data(
            arranged_overdraft_amount=Decimal(100),
            default_bal=Decimal(-100),
        )

        result = unarranged_overdraft_fee.accrue_fees(state=self.state)
        self.assertEqual(result, [])

    @pytest.mark.unit
    def test_overdraft_fee_not_accrued_cap_exceeded(self):
        self.setup_mock_data(
            unarranged_overdraft_fee_cap=Decimal(30),
            default_bal=Decimal("-30.01"),
            overdraft_fee_bal=Decimal(-30),
        )

        result = unarranged_overdraft_fee.accrue_fees(state=self.state)
        self.assertEqual(result, [])

    @patch.object(
        unarranged_overdraft_fee.accrual_utils, "create_receivable_accrual_custom_instruction"
    )
    @pytest.mark.unit
    def test_overdraft_fee_partially_accrued_cap_exceeded(
        self, mock_create_payable_accrual_custom_instruction: MagicMock
    ):
        unarranged_overdraft_fee_cap = Decimal(30)
        overdraft_fee_bal_net_debit = Decimal(26)
        self.setup_mock_data(
            unarranged_overdraft_fee_param=Decimal(5),
            unarranged_overdraft_fee_cap=unarranged_overdraft_fee_cap,
            default_bal=Decimal(-150),
            overdraft_fee_bal=-overdraft_fee_bal_net_debit,
        )

        mock_create_payable_accrual_custom_instruction.return_value = [sentinel.custom_instruction]

        result = unarranged_overdraft_fee.accrue_fees(state=self.state)

        self.assertEqual(result, [sentinel.custom_instruction])
        chargeable_balance: Decimal = unarranged_overdraft_fee_cap - overdraft_fee_bal_net_debit
        self.assertEqual(chargeable_balance, Decimal(4))
        mock_create_payable_accrual_custom_instruction.assert_called_once_with(
            customer_account=ACCOUNT_ID,
            customer_address=unarranged_overdraft_fee.OVERDRAFT_FEE_ADDRESS,
            denomination=DEFAULT_DENOMINATION,
            amount=chargeable_balance,
            internal_account=UNARRANGED_OVERDRAFT_FEE_RECEIVABLE_ACCOUNT,
            instruction_details={
                "description": f"Daily unarranged overdraft fee of {chargeable_balance} GBP",
                "event": unarranged_overdraft_fee.ACCRUAL_EVENT,
            },
        )

    @patch.object(
        unarranged_overdraft_fee.accrual_utils,
        "create_receivable_accrual_application_custom_instruction",
    )
    @pytest.mark.unit
    def test_apply_fees(self, mock_accrual_application: MagicMock):
        overdraft_fee_bal_net_debit = Decimal("25.232")
        self.setup_mock_data(
            overdraft_fee_bal=-overdraft_fee_bal_net_debit,
        )

        mock_accrual_application.return_value = [sentinel.custom_instruction]

        result = unarranged_overdraft_fee.apply_fees(state=self.state, account_type=ACCOUNT_TYPE)

        self.assertEqual(result, [sentinel.custom_instruction])
        mock_accrual_application.assert_called_once_with(
            customer_account=ACCOUNT_ID,
            denomination=DEFAULT_DENOMINATION,
            application_amount=overdraft_fee_bal_net_debit,
            accrual_amount=overdraft_fee_bal_net_debit,
            accrual_customer_address=unarranged_overdraft_fee.OVERDRAFT_FEE_ADDRESS,
            accrual_internal_account=UNARRANGED_OVERDRAFT_FEE_RECEIVABLE_ACCOUNT,
            application_customer_address=DEFAULT_ADDRESS,
            application_internal_account=UNARRANGED_OVERDRAFT_FEE_INCOME_ACCOUNT,
            instruction_details={
                "description": (
                    f"Unarranged overdraft fee of {overdraft_fee_bal_net_debit} GBP applied."
                ),
                "event": unarranged_overdraft_fee.APPLICATION_EVENT,
                "gl_impacted": "True",
                "account_type": ACCOUNT_TYPE,
            },
        )

    @pytest.mark.unit
    def test_apply_fees_not_applied_when_no_accrual(self):
        self.setup_mock_data(overdraft_fee_bal=Decimal(0))

        result = unarranged_overdraft_fee.apply_fees(state=self.state)
        self.assertEqual(result, [])


class UnarrangedOverdraftFeeHelpersTest(FeatureTest):
    @pytest.mark.unit
    def test_get_parameters(self):
        mock_vault = self.create_mock(
            parameters_observation_fetchers_mapping={
                unarranged_overdraft_fee.UNARRANGED_OVERDRAFT_FEE_POF_ID: ParametersObservation(
                    parameters={"parameter_name": "parameter_value"},
                    value_datetime=DEFAULT_DATETIME,
                )
            }
        )

        result = unarranged_overdraft_fee.get_parameters(
            vault=mock_vault,
            param_fetcher_id=unarranged_overdraft_fee.UNARRANGED_OVERDRAFT_FEE_POF_ID,
        )

        self.assertEqual(result, {"parameter_name": "parameter_value"})

    @patch.object(unarranged_overdraft_fee, "get_parameters")
    @patch.object(unarranged_overdraft_fee.state_utils, "append_to_state")
    @pytest.mark.unit
    def test_append_to_state(
        self,
        mock_append_to_state: MagicMock,
        mock_get_parameters: MagicMock,
    ):
        mock_vault = self.create_mock(
            balances_observation_fetchers_mapping={
                fetchers.ALL_BALANCES_ET_BOF.fetcher_id: BalancesObservation(
                    balances=BalanceDefaultDict(lambda: Balance(), {}),
                    value_datetime=DEFAULT_DATETIME,
                )
            }
        )
        initial_parameters: dict[str, str | Decimal | datetime | None] = {
            "INITIAL_PARAM": "INITIAL_VALUE"
        }
        new_parameters: dict[str, str | Decimal | datetime | None] = {"NEW_PARAM": "NEW_VALUE"}

        mock_state = initialise_mock_state(
            vault=mock_vault,
            parameters=initial_parameters,
        )
        mock_get_parameters.return_value = new_parameters

        mock_append_to_state.return_value = initialise_mock_state(
            vault=mock_vault,
            parameters=initial_parameters | new_parameters,
            effective_datetime=mock_state.effective_datetime,
        )

        result = unarranged_overdraft_fee._append_to_state(
            state=mock_state,
            fetchers_config=unarranged_overdraft_fee.DEFAULT_UNARRANGED_OVERDRAFT_FEE_FETCHERS_CONFIG,
        )

        mock_get_parameters.assert_called_once_with(
            mock_vault, unarranged_overdraft_fee.UNARRANGED_OVERDRAFT_FEE_POF_ID
        )
        mock_append_to_state.assert_called_once_with(
            state=mock_state,
            parameters=new_parameters,
            balances=mock_vault.get_balances_observation(
                fetcher_id=fetchers.ALL_BALANCES_ET_BOF_ID
            ).balances,
        )

        self.assertEqual(result.vault, mock_vault)

    @patch.object(unarranged_overdraft_fee.state_utils, "append_to_state")
    @pytest.mark.unit
    def test_get_scheduled_events(self, mock_state_utils_append_to_state: MagicMock):
        accrual_time = "12:34:56"
        application_time = "23:59:59"
        day = "1"
        mock_vault = self.create_mock(
            parameters_observation_fetchers_mapping={
                unarranged_overdraft_fee.UNARRANGED_OVERDRAFT_FEE_POF_ID: ParametersObservation(
                    parameters={},
                    value_datetime=DEFAULT_DATETIME,
                )
            }
        )
        mock_vault.events_timezone = UTC
        mock_state = initialise_mock_state(
            vault=mock_vault,
            effective_datetime=DEFAULT_DATETIME,
            parameters={
                unarranged_overdraft_fee.UNARRANGED_OVERDRAFT_FEE_ACCRUAL_TIME_PARAM.id: (
                    accrual_time
                ),
                unarranged_overdraft_fee.UNARRANGED_OVERDRAFT_FEE_APPLICATION_TIME_PARAM.id: (
                    application_time
                ),
                unarranged_overdraft_fee.UNARRANGED_OVERDRAFT_FEE_APPLICATION_DAY_PARAM.id: day,
            },
        )
        mock_state_utils_append_to_state.return_value = mock_state

        result = unarranged_overdraft_fee.get_scheduled_events(state=mock_state)
        start = DEFAULT_DATETIME + relativedelta(days=1)
        expected_events = {
            unarranged_overdraft_fee.ACCRUAL_EVENT: ScheduledEvent(
                start_datetime=start,
                expression=ScheduleExpression(
                    hour=12,
                    minute=34,
                    second=56,
                ),
            ),
            unarranged_overdraft_fee.APPLICATION_EVENT: ScheduledEvent(
                start_datetime=start,
                expression=ScheduleExpression(
                    day=1,
                    hour=23,
                    minute=59,
                    second=59,
                ),
            ),
        }
        self.assertEqual(result, expected_events)

    @patch.object(unarranged_overdraft_fee.state_utils, "check_parameters_exist")
    @patch.object(unarranged_overdraft_fee.state_utils, "append_to_state")
    @pytest.mark.unit
    def test_get_scheduled_events_returns_rejection_if_parameter_missing(
        self, mock_state_utils_append_to_state: MagicMock, mock_check_parameters_exist: MagicMock
    ):
        mock_state = initialise_mock_state()
        mock_state_utils_append_to_state.return_value = mock_state
        mock_check_parameters_exist.return_value = sentinel.rejection

        with self.assertRaises(AssertionError) as ex:
            unarranged_overdraft_fee.get_scheduled_events(state=mock_state)

        self.assertEqual(ex.exception.args[0], sentinel.rejection)
