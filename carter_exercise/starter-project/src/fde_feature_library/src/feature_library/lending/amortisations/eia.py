# Copyright @ 2026 Thought Machine Group Limited. All rights reserved.
"""Eia feature."""

__smart_contract_feature__ = True

# standard libs
from decimal import Decimal
from typing import NamedTuple

import feature_library.common.addresses as common_addresses

# feature library
import feature_library.common.application_precision as application_precision_module
import feature_library.common.balance_utils as balance_utils
import feature_library.common.denomination as denomination_module
import feature_library.common.posting_utils as posting_utils
import feature_library.common.state_utils as state_utils
import feature_library.common.utils as utils
import feature_library.lending.addresses as lending_addresses

# contracts api
from contracts_api import (
    ExpectedParameter,
    Posting,
)

# Parameters
EQUATED_INSTALMENT_AMOUNT_PARAM_ID = "&{equated_instalment_amount}"
EQUATED_INSTALMENT_AMOUNT_PARAM = ExpectedParameter(
    id=EQUATED_INSTALMENT_AMOUNT_PARAM_ID,
    optional=True,
    triggers_pre_parameter_change_hook=False,
    triggers_post_parameter_change_hook=False,
)

expected_parameters = [
    EQUATED_INSTALMENT_AMOUNT_PARAM,
]

AmortiseFetchersConfig = NamedTuple(
    "AmortiseFetchersConfig",
    [
        ("denomination_param_id", str),
    ],
)
DEFAULT_AMORTISE_FETCHERS_CONFIG = AmortiseFetchersConfig(
    denomination_param_id=denomination_module.DENOMINATION_PARAM_ID,
)


ExpectedEiaFetchersConfig = NamedTuple(
    "ExpectedEiaFetchersConfig",
    [
        ("denomination_param_id", str),
        ("application_precision_param_id", str),
    ],
)
DEFAULT_EXPECTED_EIA_FETCHERS_CONFIG = ExpectedEiaFetchersConfig(
    denomination_param_id=denomination_module.DENOMINATION_PARAM.id,
    application_precision_param_id=application_precision_module.APPLICATION_PRECISION_PARAM.id,
)


def update_eia(
    account_id: str,
    denomination: str,
    current_eia: Decimal,
    updated_eia: Decimal,
    eia_address: str = lending_addresses.EIA,
    contra_address: str = common_addresses.INTERNAL_CONTRA,
) -> list[Posting]:
    """Create postings to update the EIA balance.

    Args:
        account_id: The account ID.
        denomination: The denomination of the EIA.
        current_eia: The current EIA balance.
        updated_eia: The new calculated EIA.
        eia_address: The address of the EIA balance.
        contra_address: The contra address for double-entry bookkeeping.

    Returns:
        A list of postings, empty if no change in EIA.
    """
    return posting_utils.create_postings(
        amount=current_eia - updated_eia,
        debit_account=account_id,
        debit_address=contra_address,
        credit_account=account_id,
        credit_address=eia_address,
        denomination=denomination,
    )


def get_expected_eia(
    state: state_utils.SmartContractState,
    eia_address: str = lending_addresses.EIA,
    fetchers_config: ExpectedEiaFetchersConfig = DEFAULT_EXPECTED_EIA_FETCHERS_CONFIG,
) -> Decimal:
    """Retrieve the expected EIA from the account balances.

    Args:
        state: The smart contract state.
        eia_address: The address of the EIA balance.
        fetchers_config: The fetchers configuration for retrieving EIA details.

    Returns:
        The expected EIA balance.
    """
    rejection = state_utils.check_parameters_exist(
        state=state,
        param_ids={
            fetchers_config.denomination_param_id,
            fetchers_config.application_precision_param_id,
        },
    )
    assert rejection is None, rejection

    denomination: str = state.parameters[fetchers_config.denomination_param_id]
    eia_balance = balance_utils.balance_at_coordinates(
        balances=state.balances,
        address=eia_address,
        denomination=denomination,
    )
    decimal_places: int = int(state.parameters[fetchers_config.application_precision_param_id])
    return utils.round_decimal(amount=eia_balance, decimal_places=decimal_places)
