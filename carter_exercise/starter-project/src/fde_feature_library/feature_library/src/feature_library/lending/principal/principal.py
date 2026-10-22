# Copyright @ 2026 Thought Machine Group Limited. All rights reserved.
__smart_contract_feature__ = True

# standard libs
from datetime import datetime
from decimal import Decimal
from typing import NamedTuple

# feature library
# contracts api
from contracts_api import (
    DefinedDateTime,
    ExpectedParameter,
    ParametersFilter,
    ParametersObservationFetcher,
)

# inception sdk
from inception_sdk.vault.contracts.extensions.contracts_api_extensions import SmartContractVault

# Parameters
PRINCIPAL_PARAM_ID = "&{principal}"
PRINCIPAL_PARAM = ExpectedParameter(
    id=PRINCIPAL_PARAM_ID,
    triggers_pre_parameter_change_hook=False,
    triggers_post_parameter_change_hook=False,
)

expected_parameters = [
    PRINCIPAL_PARAM,
]

# Fetchers
PRINCIPAL_POF_ID = "principal_pof"
PRINCIPAL_POF = ParametersObservationFetcher(
    fetcher_id=PRINCIPAL_POF_ID,
    at=DefinedDateTime.EFFECTIVE_DATETIME,
    filter=ParametersFilter(parameter_ids=[p.id for p in expected_parameters]),
)

data_fetchers = [
    PRINCIPAL_POF,
]

PrincipalFetchersConfig = NamedTuple(
    "PrincipalFetchersConfig",
    [
        ("param_fetcher_id", str),
        ("principal_param_id", str),
    ],
)

DEFAULT_FETCHERS_CONFIG = PrincipalFetchersConfig(
    param_fetcher_id=PRINCIPAL_POF_ID,
    principal_param_id=PRINCIPAL_PARAM_ID,
)


def get_parameters(
    vault: SmartContractVault, param_fetcher_id: str = PRINCIPAL_POF_ID
) -> dict[str, datetime | Decimal | str | None]:
    """Retrieves configuration parameters for the principal feature.

    Args:
        vault: The SmartContractVault instance to query.
        param_fetcher_id: The unique identifier for the parameter fetcher.
            Defaults to `PRINCIPAL_POF_ID`.

    Returns:
        Parameters for the principal feature.
    """
    return vault.get_parameters_observation(fetcher_id=param_fetcher_id).parameters
