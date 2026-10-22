# standard libs
from datetime import datetime
from decimal import Decimal
from unittest.mock import sentinel
from zoneinfo import ZoneInfo

import pytest

# features
import feature_library.lending.interest.secondary.fixed_rate as fixed_rate

# contracts api
from contracts_api import (
    ParametersObservation,
)

# inception sdk
from inception_sdk.test_framework.contracts.unit.common import FeatureTest

from tests.utils import initialise_mock_state

UTC = ZoneInfo("UTC")


class FixedRateTest(FeatureTest):
    def setup_mock_data(self, parameters=None, effective_datetime=None):
        params = {
            fixed_rate.FIXED_INTEREST_RATE_PARAM_ID: Decimal("0.05"),
        }
        if parameters:
            params.update(parameters)

        effective_dt = effective_datetime or datetime(2020, 1, 1, tzinfo=UTC)

        self.mock_vault = self.create_mock(
            account_id=sentinel.account_id,
            parameters_observation_fetchers_mapping={
                fixed_rate.FIXED_INTEREST_RATE_ET_POF_ID: ParametersObservation(
                    parameters=params, value_datetime=effective_dt
                )
            },
        )

        return initialise_mock_state(
            vault=self.mock_vault, effective_datetime=effective_dt, parameters=params
        )

    @pytest.mark.unit
    def test_get_parameters(self):
        params = {fixed_rate.FIXED_INTEREST_RATE_PARAM_ID: Decimal("0.05")}
        self.setup_mock_data(parameters=params)
        returned_params = fixed_rate.get_parameters(self.mock_vault)
        self.assertEqual(returned_params, params)

    @pytest.mark.unit
    def test_append_to_state(self):
        params = {fixed_rate.FIXED_INTEREST_RATE_PARAM_ID: Decimal("0.05")}
        state = self.setup_mock_data(parameters=params)
        # Clear parameters from state to ensure they are appended
        state = state._replace(parameters={})

        updated_state = fixed_rate._append_to_state(state)
        self.assertEqual(updated_state.parameters, params)

    @pytest.mark.unit
    def test_get_annual_interest_rate(self):
        state = self.setup_mock_data()
        rate = fixed_rate.get_annual_interest_rate(state)
        self.assertEqual(rate, Decimal("0.05"))
