# Copyright @ 2026 Thought Machine Group Limited. All rights reserved.
__smart_contract_feature__ = True

# standard libs
from datetime import datetime
from decimal import Decimal

# feature library
import feature_library.common.balance_utils as balance_utils
import feature_library.lending.addresses as lending_addresses

# contracts api
from contracts_api import (
    BalanceDefaultDict,
    DefinedDateTime,
    ExpectedParameter,
    ParametersFilter,
    ParametersObservationFetcher,
)

# inception sdk
from inception_sdk.vault.contracts.extensions.contracts_api_extensions import SmartContractVault

# Parameters
TERM_PARAM_ID = "&{term}"
TERM_PARAM = ExpectedParameter(
    id=TERM_PARAM_ID,
    triggers_pre_parameter_change_hook=False,
    triggers_post_parameter_change_hook=False,
)

expected_parameters = [
    TERM_PARAM,
]

TERM_POF_ID = "term_pof"
TERM_POF = ParametersObservationFetcher(
    fetcher_id=TERM_POF_ID,
    at=DefinedDateTime.EFFECTIVE_DATETIME,
    filter=ParametersFilter(parameter_ids=[p.id for p in expected_parameters]),
)

data_fetchers = [
    TERM_POF,
]


def get_parameters(
    vault: SmartContractVault, param_fetcher_id: str = TERM_POF_ID
) -> dict[str, datetime | Decimal | str | None]:
    """Retrieves configuration parameters for the lending term feature.

    Args:
        vault: The SmartContractVault instance to query.
        param_fetcher_id: The unique identifier for the parameter fetcher.
            Defaults to `TERM_POF_ID`.

    Returns:
        Parameters for the lending term feature.
    """
    return vault.get_parameters_observation(fetcher_id=param_fetcher_id).parameters


def get_elapsed_term(
    balances: BalanceDefaultDict,
    denomination: str,
    repayment_count_address: str = lending_addresses.TERM_COUNTER,
) -> int:
    """Gets the elapsed term from the term counter address.

    Args:
        balances: The account balances.
        denomination: The account denomination.
        repayment_count_address: The address tracking the elapsed term.

    Returns:
        int: The elapsed term.
    """
    return int(
        balance_utils.balance_at_coordinates(
            balances=balances,
            address=repayment_count_address,
            denomination=denomination,
        )
    )
