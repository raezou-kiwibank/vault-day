# standard libs
from datetime import datetime
from decimal import Decimal
from unittest.mock import sentinel
from zoneinfo import ZoneInfo

import pytest

# features
import feature_library.lending.interest.secondary.variable_rate as variable_rate

# contracts api
from contracts_api import (
    ParametersObservation,
)

# inception sdk
from inception_sdk.test_framework.contracts.unit.common import FeatureTest

from tests.utils import initialise_mock_state

UTC = ZoneInfo("UTC")


class VariableRateTest(FeatureTest):
    def setup_mock_data(self, parameters=None, effective_datetime=None):
        params = {
            variable_rate.VARIABLE_INTEREST_RATE_PARAM_ID: Decimal("0.02"),
            variable_rate.VARIABLE_RATE_ADJUSTMENT_PARAM_ID: Decimal("0.01"),
            variable_rate.BASE_RATE_PARAM_ID: Decimal("0.03"),
            variable_rate.ANNUAL_INTEREST_RATE_CAP_PARAM_ID: Decimal("0.10"),
            variable_rate.ANNUAL_INTEREST_RATE_FLOOR_PARAM_ID: Decimal("0.01"),
        }
        if parameters:
            params.update(parameters)

        effective_dt = effective_datetime or datetime(2020, 1, 1, tzinfo=UTC)

        self.mock_vault = self.create_mock(
            account_id=sentinel.account_id,
            parameters_observation_fetchers_mapping={
                variable_rate.VARIABLE_RATE_ET_POF_ID: ParametersObservation(
                    parameters=params, value_datetime=effective_dt
                )
            },
        )

        return initialise_mock_state(
            vault=self.mock_vault, effective_datetime=effective_dt, parameters=params
        )

    @pytest.mark.unit
    def test_get_parameters(self):
        params = {
            variable_rate.VARIABLE_INTEREST_RATE_PARAM_ID: Decimal("0.02"),
            variable_rate.VARIABLE_RATE_ADJUSTMENT_PARAM_ID: Decimal("0.01"),
            variable_rate.BASE_RATE_PARAM_ID: Decimal("0.03"),
            variable_rate.ANNUAL_INTEREST_RATE_CAP_PARAM_ID: Decimal("0.10"),
            variable_rate.ANNUAL_INTEREST_RATE_FLOOR_PARAM_ID: Decimal("0.01"),
        }
        self.setup_mock_data(parameters=params)
        returned_params = variable_rate.get_parameters(self.mock_vault)
        self.assertEqual(returned_params, params)

    @pytest.mark.unit
    def test_append_to_state(self):
        params = {
            variable_rate.VARIABLE_INTEREST_RATE_PARAM_ID: Decimal("0.02"),
            variable_rate.VARIABLE_RATE_ADJUSTMENT_PARAM_ID: Decimal("0.01"),
            variable_rate.BASE_RATE_PARAM_ID: Decimal("0.03"),
            variable_rate.ANNUAL_INTEREST_RATE_CAP_PARAM_ID: Decimal("0.10"),
            variable_rate.ANNUAL_INTEREST_RATE_FLOOR_PARAM_ID: Decimal("0.01"),
        }
        state = self.setup_mock_data(parameters=params)
        # Clear parameters from state to ensure they are appended
        state = state._replace(parameters={})

        updated_state = variable_rate._append_to_state(state)
        self.assertEqual(updated_state.parameters, params)

    @pytest.mark.unit
    def test_get_annual_interest_rate(self):
        state = self.setup_mock_data()
        # 0.02 + 0.01 + 0.03 = 0.06
        rate = variable_rate.get_annual_interest_rate(state)
        self.assertEqual(rate, Decimal("0.06"))

    @pytest.mark.unit
    def test_get_annual_interest_rate_capped(self):
        state = self.setup_mock_data(
            parameters={
                variable_rate.VARIABLE_INTEREST_RATE_PARAM_ID: Decimal("0.08"),
                variable_rate.VARIABLE_RATE_ADJUSTMENT_PARAM_ID: Decimal("0.04"),
                # 0.08 + 0.04 + 0.03 = 0.15, but cap is 0.10
            }
        )
        rate = variable_rate.get_annual_interest_rate(state)
        self.assertEqual(rate, Decimal("0.10"))

    @pytest.mark.unit
    def test_get_annual_interest_rate_floored(self):
        state = self.setup_mock_data(
            parameters={
                variable_rate.VARIABLE_INTEREST_RATE_PARAM_ID: Decimal("-0.05"),
                # -0.05 + 0.01 + 0.03 = -0.01, but floor is 0.01
            }
        )
        rate = variable_rate.get_annual_interest_rate(state)
        self.assertEqual(rate, Decimal("0.01"))

    @pytest.mark.unit
    def test_get_annual_interest_rate_no_cap_or_floor(self):
        # Remove cap and floor from parameters
        params = {
            variable_rate.VARIABLE_INTEREST_RATE_PARAM_ID: Decimal("0.02"),
            variable_rate.VARIABLE_RATE_ADJUSTMENT_PARAM_ID: Decimal("0.01"),
            variable_rate.BASE_RATE_PARAM_ID: Decimal("0.03"),
        }
        state = self.setup_mock_data(parameters=params)
        # We need to manually remove them from state as setup_mock_data has defaults
        state.parameters.pop(variable_rate.ANNUAL_INTEREST_RATE_CAP_PARAM_ID)
        state.parameters.pop(variable_rate.ANNUAL_INTEREST_RATE_FLOOR_PARAM_ID)

        # 0.02 + 0.01 + 0.03 = 0.06
        rate = variable_rate.get_annual_interest_rate(state)
        self.assertEqual(rate, Decimal("0.06"))
