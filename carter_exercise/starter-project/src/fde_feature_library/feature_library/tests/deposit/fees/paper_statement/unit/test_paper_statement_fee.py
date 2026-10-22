# standard libs
from datetime import datetime
from decimal import Decimal
from unittest.mock import MagicMock, patch, sentinel
from zoneinfo import ZoneInfo

import pytest

import feature_library.common.denomination as denomination_module

# features
import feature_library.common.fetchers as fetchers
import feature_library.deposit.fees.paper_statement_fee as paper_statement_fee_module

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

UTC_ZONE = ZoneInfo("UTC")
DEFAULT_DATETIME = datetime(2026, 1, 1, tzinfo=UTC_ZONE)

DENOMINATION = DEFAULT_DENOMINATION
PAPER_STATEMENT_FEE_INCOME_ACCOUNT = "PAPER_STATEMENT_FEE_INCOME"
ACCOUNT_TYPE = "account_type"

FETCHER_ID = "fetcher_id"
PARAMETER_NAME = "parameter_name"


def none_to_zero(d: Decimal | None = None) -> Decimal:
    return d if d is not None else Decimal(0)


class PaperStatementFeeTest(FeatureTest):
    def setup_mock_data(
        self,
        account_creation_datetime: datetime = DEFAULT_DATETIME,
        effective_datetime: datetime = DEFAULT_DATETIME,
        paper_statement_fee_rate: Decimal | None = Decimal("3.00"),
        paper_statement_fee_income_account: str | None = "PAPER_STATEMENT_FEE_INCOME_ACCOUNT",
        paper_statement_fee_enabled: str | None = "True",
        partial_paper_statement_fee_enabled: str | None = "False",
        default_bal: Decimal | None = None,
        denomination: str | None = DEFAULT_DENOMINATION,
    ):
        default_bal = none_to_zero(default_bal)
        self.effective_datetime = effective_datetime

        denom_params = {}
        if denomination is not None:
            denom_params[denomination_module.DENOMINATION_PARAM.id] = denomination

        paper_statement_fees_params = {
            paper_statement_fee_module.PAPER_STATEMENT_FEE_DAY_PARAM.id: "17",
            paper_statement_fee_module.PAPER_STATEMENT_FEE_TIME_PARAM.id: "00:00:01",
        }
        if paper_statement_fee_rate is not None:
            paper_statement_fees_params[
                paper_statement_fee_module.PAPER_STATEMENT_FEE_RATE_PARAM.id
            ] = paper_statement_fee_rate
        if paper_statement_fee_income_account is not None:
            paper_statement_fees_params[
                paper_statement_fee_module.PAPER_STATEMENT_FEE_INCOME_ACCOUNT_PARAM.id
            ] = paper_statement_fee_income_account
        if paper_statement_fee_enabled is not None:
            paper_statement_fees_params[
                paper_statement_fee_module.PAPER_STATEMENT_FEE_ENABLED_PARAM.id
            ] = paper_statement_fee_enabled
        if partial_paper_statement_fee_enabled is not None:
            paper_statement_fees_params[
                paper_statement_fee_module.PAPER_STATEMENT_FEE_PARTIAL_FEE_ENABLED_PARAM.id
            ] = partial_paper_statement_fee_enabled

        params_obs: dict[str, ParametersObservation] = {
            denomination_module.DENOMINATION_ET_POF.fetcher_id: ParametersObservation(
                parameters=denom_params, value_datetime=effective_datetime
            ),
            paper_statement_fee_module.PAPER_STATEMENT_FEE_POF.fetcher_id: ParametersObservation(
                parameters=paper_statement_fees_params,
                value_datetime=effective_datetime,
            ),
        }

        default_bals = BalanceDefaultDict(
            lambda: Balance(),
            {
                BalanceCoordinate(
                    DEFAULT_ADDRESS, DEFAULT_ASSET, DENOMINATION, Phase.COMMITTED
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
        )
        self.state = MagicMock(
            vault=self.mock_vault,
            effective_datetime=effective_datetime,
            parameters=paper_statement_fees_params | denom_params,
            balances=default_bals,
        )

    @pytest.mark.unit
    def test_apply_fees_raises_assertion_error_if_parameter_missing(self):
        params_to_test = [
            ("paper_statement_fee_rate", {"paper_statement_fee_rate": None}),
            ("paper_statement_fee_income_account", {"paper_statement_fee_income_account": None}),
            ("paper_statement_fee_enabled", {"paper_statement_fee_enabled": None}),
            ("denomination", {"denomination": None}),
        ]

        for param_name, setup_kwargs in params_to_test:
            with self.subTest(missing_param=param_name):
                self.setup_mock_data(**setup_kwargs)  # type: ignore
                with self.assertRaises(AssertionError) as cm:
                    paper_statement_fee_module.apply_fees(
                        state=self.state,
                        account_type=ACCOUNT_TYPE,
                    )
                self.assertIn("parameters are missing: ", str(cm.exception))

    @pytest.mark.unit
    def test_paper_statement_fee_applied(
        self,
    ):
        paper_statement_fee_rate = Decimal("3.00")
        self.setup_mock_data(
            paper_statement_fee_rate=paper_statement_fee_rate,
            paper_statement_fee_income_account=PAPER_STATEMENT_FEE_INCOME_ACCOUNT,
            paper_statement_fee_enabled="True",
            partial_paper_statement_fee_enabled="False",
        )
        result = paper_statement_fee_module.apply_fees(
            state=self.state,
            account_type=ACCOUNT_TYPE,
        )
        expected = [
            CustomInstruction(
                postings=[
                    Posting(
                        credit=False,
                        amount=paper_statement_fee_rate,
                        denomination=DENOMINATION,
                        account_id=ACCOUNT_ID,
                        account_address=DEFAULT_ADDRESS,
                        asset=DEFAULT_ASSET,
                        phase=Phase.COMMITTED,
                    ),
                    Posting(
                        credit=True,
                        amount=paper_statement_fee_rate,
                        denomination=DENOMINATION,
                        account_id=PAPER_STATEMENT_FEE_INCOME_ACCOUNT,
                        account_address=DEFAULT_ADDRESS,
                        asset=DEFAULT_ASSET,
                        phase=Phase.COMMITTED,
                    ),
                ],
                instruction_details={
                    "description": "Monthly Paper Statement Fee Application",
                    "event": "APPLY_PAPER_STATEMENT_FEE",
                    "gl_impacted": str(True),
                    "account_type": ACCOUNT_TYPE,
                },
                value_datetime=self.effective_datetime,
                override_all_restrictions=True,
            )
        ]
        self.assertListEqual(result, expected)

    @patch.object(paper_statement_fee_module.partial_fee, "charge_partial_fee")
    @pytest.mark.unit
    def test_paper_statement_fee_partially_applied(
        self,
        mock_charge_partial_fee: MagicMock,
    ):
        paper_statement_fee_rate = Decimal("3.00")
        self.setup_mock_data(
            paper_statement_fee_rate=paper_statement_fee_rate,
            paper_statement_fee_income_account=PAPER_STATEMENT_FEE_INCOME_ACCOUNT,
            paper_statement_fee_enabled="True",
            partial_paper_statement_fee_enabled="True",
        )
        mock_charge_partial_fee.return_value = [sentinel.partial_fee_instruction]

        result = paper_statement_fee_module.apply_fees(
            state=self.state,
            account_type=ACCOUNT_TYPE,
            available_balance_feature=sentinel.available_balance_feature,
        )

        self.assertListEqual(result, [sentinel.partial_fee_instruction])

        expected_fee_instruction = CustomInstruction(
            postings=[
                Posting(
                    credit=False,
                    amount=paper_statement_fee_rate,
                    denomination=DENOMINATION,
                    account_id=ACCOUNT_ID,
                    account_address=DEFAULT_ADDRESS,
                    asset=DEFAULT_ASSET,
                    phase=Phase.COMMITTED,
                ),
                Posting(
                    credit=True,
                    amount=paper_statement_fee_rate,
                    denomination=DENOMINATION,
                    account_id=PAPER_STATEMENT_FEE_INCOME_ACCOUNT,
                    account_address=DEFAULT_ADDRESS,
                    asset=DEFAULT_ASSET,
                    phase=Phase.COMMITTED,
                ),
            ],
            instruction_details={
                "description": "Monthly Paper Statement Fee Application",
                "event": "APPLY_PAPER_STATEMENT_FEE",
                "gl_impacted": str(True),
                "account_type": ACCOUNT_TYPE,
            },
            value_datetime=self.effective_datetime,
            override_all_restrictions=True,
        )

        from unittest.mock import ANY

        mock_charge_partial_fee.assert_called_once_with(
            state=ANY,
            fee_custom_instruction=expected_fee_instruction,
            fee_details=paper_statement_fee_module.PARTIAL_FEE_DETAILS,
            available_balance_feature=sentinel.available_balance_feature,
        )

    @pytest.mark.unit
    def test_paper_statement_fee_not_applied_when_disabled(
        self,
    ):
        self.setup_mock_data(
            paper_statement_fee_rate=Decimal("3.00"),
            paper_statement_fee_income_account=PAPER_STATEMENT_FEE_INCOME_ACCOUNT,
            paper_statement_fee_enabled="False",
        )
        result = paper_statement_fee_module.apply_fees(
            state=self.state,
            account_type=ACCOUNT_TYPE,
        )

        self.assertEqual(len(result), 0)

    @pytest.mark.unit
    def test_paper_statement_fee_not_applied_when_fee_is_zero(
        self,
    ):
        self.setup_mock_data(
            paper_statement_fee_rate=Decimal(0),
            paper_statement_fee_income_account=PAPER_STATEMENT_FEE_INCOME_ACCOUNT,
            paper_statement_fee_enabled="True",
        )

        result = paper_statement_fee_module.apply_fees(
            state=self.state,
            account_type=ACCOUNT_TYPE,
        )

        self.assertEqual(len(result), 0)


class PaperStatementFeeHelpersTest(FeatureTest):
    @pytest.mark.unit
    def test_get_parameters(
        self,
    ):
        mock_vault = self.create_mock(
            parameters_observation_fetchers_mapping={
                FETCHER_ID: ParametersObservation(
                    parameters={PARAMETER_NAME: "parameter_value"},
                    value_datetime=DEFAULT_DATETIME,
                )
            }
        )

        result = paper_statement_fee_module.get_parameters(
            vault=mock_vault,
            param_fetcher_id=FETCHER_ID,
        )

        self.assertEqual(
            result,
            {PARAMETER_NAME: "parameter_value"},
        )

    @patch.object(paper_statement_fee_module, "get_parameters")
    @patch.object(paper_statement_fee_module.state_utils, "append_to_state")
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
        initial_parameters = {"INITIAL_PARAM": "INITIAL_VALUE"}
        new_parameters = {"NEW_PARAM": "NEW_VALUE"}

        mock_state = initialise_mock_state(vault=mock_vault, parameters=initial_parameters)
        mock_get_parameters.return_value = new_parameters

        mock_append_to_state.return_value = initialise_mock_state(
            vault=mock_vault,
            parameters=initial_parameters | new_parameters,
            effective_datetime=mock_state.effective_datetime,
        )

        result = paper_statement_fee_module._append_to_state(
            state=mock_state, param_fetcher_id=sentinel.param_fetcher_id
        )

        mock_get_parameters.assert_called_once_with(mock_vault, sentinel.param_fetcher_id)
        mock_append_to_state.assert_called_once_with(
            state=mock_state,
            parameters=new_parameters,
            balances=mock_vault.get_balances_observation(
                fetcher_id=fetchers.ALL_BALANCES_ET_BOF_ID
            ).balances,
        )

        # Check that parameters were merged correctly
        for key, value in initial_parameters.items():
            self.assertEqual(result.parameters[key], value)
        for key, value in new_parameters.items():
            self.assertEqual(result.parameters[key], value)

        self.assertEqual(result.vault, mock_vault)
        self.assertEqual(result.effective_datetime, mock_state.effective_datetime)

    @patch.object(paper_statement_fee_module, "_append_to_state")
    @patch.object(paper_statement_fee_module.state_utils, "append_to_state")
    @pytest.mark.unit
    def test_get_scheduled_events(
        self, mock_state_utils_append_to_state: MagicMock, mock_append_to_state: MagicMock
    ):
        application_time = "12:34:56"
        day = "17"
        mock_state = initialise_mock_state(
            effective_datetime=DEFAULT_DATETIME,
            parameters={
                paper_statement_fee_module.PAPER_STATEMENT_FEE_TIME_PARAM.id: application_time,
                paper_statement_fee_module.PAPER_STATEMENT_FEE_DAY_PARAM.id: day,
            },
        )
        # the function uses state_utils.append_to_state directly so that balances aren't requested
        mock_state_utils_append_to_state.return_value = mock_state

        result = paper_statement_fee_module.get_scheduled_events(state=mock_state)

        expected_event = {
            paper_statement_fee_module.APPLICATION_EVENT: ScheduledEvent(
                start_datetime=DEFAULT_DATETIME,
                expression=ScheduleExpression(
                    day=17,
                    hour=12,
                    minute=34,
                    second=56,
                ),
            )
        }
        self.assertEqual(result, expected_event)

    @patch.object(paper_statement_fee_module.state_utils, "check_parameters_exist")
    @patch.object(paper_statement_fee_module.state_utils, "append_to_state")
    @pytest.mark.unit
    def test_get_scheduled_events_returns_rejection_if_parameter_missing(
        self, mock_state_utils_append_to_state: MagicMock, mock_check_parameters_exist: MagicMock
    ):
        mock_state = initialise_mock_state()
        mock_state_utils_append_to_state.return_value = mock_state
        mock_check_parameters_exist.return_value = sentinel.rejection

        with self.assertRaises(AssertionError) as ex:
            paper_statement_fee_module.get_scheduled_events(state=mock_state)

        self.assertEqual(ex.exception.args[0], sentinel.rejection)
        mock_check_parameters_exist.assert_called_once_with(
            state=mock_state,
            param_ids={
                paper_statement_fee_module.PAPER_STATEMENT_FEE_DAY_PARAM.id,
                paper_statement_fee_module.PAPER_STATEMENT_FEE_TIME_PARAM.id,
            },
        )
