# Copyright @ 2026 Thought Machine Group Limited. All rights reserved.
# standard libs
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

# features
import feature_library.lending.term.term as term_module

# contracts api
from contracts_api import ParametersObservation

# inception sdk
from inception_sdk.test_framework.contracts.unit.common import FeatureTest

UTC_ZONE = ZoneInfo("UTC")
DEFAULT_DATETIME = datetime(2026, 1, 1, tzinfo=UTC_ZONE)


@pytest.mark.unit
class TermTest(FeatureTest):
    @pytest.mark.unit
    def test_get_parameters(self):
        term_value = "12"
        params_obs = {
            term_module.TERM_POF_ID: ParametersObservation(
                parameters={term_module.TERM_PARAM_ID: term_value},
                value_datetime=DEFAULT_DATETIME,
            )
        }
        mock_vault = self.create_mock(parameters_observation_fetchers_mapping=params_obs)

        result = term_module.get_parameters(vault=mock_vault)

        self.assertEqual(result, {term_module.TERM_PARAM_ID: term_value})
