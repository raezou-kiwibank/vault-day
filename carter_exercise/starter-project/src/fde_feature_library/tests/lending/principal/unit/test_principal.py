# Copyright @ 2026 Thought Machine Group Limited. All rights reserved.
# standard libs
from datetime import datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

import pytest

# features
import feature_library.lending.principal.principal as principal

# contracts api
from contracts_api import ParametersObservation

# inception sdk
from inception_sdk.test_framework.contracts.unit.common import FeatureTest

UTC_ZONE = ZoneInfo("UTC")
DEFAULT_DATETIME = datetime(2026, 1, 1, tzinfo=UTC_ZONE)


@pytest.mark.unit
class PrincipalTest(FeatureTest):
    @pytest.mark.unit
    def test_get_parameters(self):
        principal_value = Decimal("1000")
        params_obs = {
            principal.PRINCIPAL_POF_ID: ParametersObservation(
                parameters={principal.PRINCIPAL_PARAM_ID: principal_value},
                value_datetime=DEFAULT_DATETIME,
            )
        }
        mock_vault = self.create_mock(parameters_observation_fetchers_mapping=params_obs)

        result = principal.get_parameters(vault=mock_vault)

        self.assertEqual(result, {principal.PRINCIPAL_PARAM_ID: principal_value})
