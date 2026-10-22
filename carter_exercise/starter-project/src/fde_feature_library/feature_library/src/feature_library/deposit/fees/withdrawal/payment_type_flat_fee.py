# Copyright @ 2026 Thought Machine Group Limited. All rights reserved.
__smart_contract_feature__ = True

# standard libs
from datetime import datetime
from decimal import Decimal
from json import loads
from typing import Any, List, NamedTuple

# feature library
import feature_library.common.balance_utils as balance_utils
import feature_library.common.denomination as denomination_module
import feature_library.common.fetchers as fetchers
import feature_library.common.posting_utils as posting_utils
import feature_library.common.state_utils as state_utils

# contracts api
from contracts_api import (
    CustomInstruction,
    DefinedDateTime,
    ExpectedParameter,
    ParametersFilter,
    ParametersObservationFetcher,
)

# inception sdk
from inception_sdk.vault.contracts.extensions.contracts_api_extensions import SmartContractVault

PAYMENT_TYPE = "PAYMENT_TYPE"
APPLICATION_EVENT = "APPLY_PAYMENT_TYPE_FLAT_FEE"

# Parameters
PAYMENT_TYPE_FLAT_FEE_PARAM_ID = "&{payment_type_flat_fee}"

"""
The parameter value should look like this:
{
    "ATM": "1.00",
}
"""
PAYMENT_TYPE_FLAT_FEE_PARAM = ExpectedParameter(
    id=PAYMENT_TYPE_FLAT_FEE_PARAM_ID,
    triggers_pre_parameter_change_hook=False,
    triggers_post_parameter_change_hook=False,
)

PAYMENT_TYPE_FEE_INCOME_ACCOUNT_PARAM_ID = "&{payment_type_fee_income_account}"
PAYMENT_TYPE_FEE_INCOME_ACCOUNT_PARAM = ExpectedParameter(
    id=PAYMENT_TYPE_FEE_INCOME_ACCOUNT_PARAM_ID,
    triggers_pre_parameter_change_hook=False,
    triggers_post_parameter_change_hook=False,
)

expected_parameters = [
    PAYMENT_TYPE_FLAT_FEE_PARAM,
    PAYMENT_TYPE_FEE_INCOME_ACCOUNT_PARAM,
    denomination_module.DENOMINATION_PARAM,
]

PAYMENT_TYPE_FLAT_FEE_POF_ID = "payment_type_flat_fee_pof"
PAYMENT_TYPE_FLAT_FEE_POF = ParametersObservationFetcher(
    fetcher_id=PAYMENT_TYPE_FLAT_FEE_POF_ID,
    at=DefinedDateTime.EFFECTIVE_DATETIME,
    filter=ParametersFilter(parameter_ids=[p.id for p in expected_parameters]),
)

data_fetchers = [
    fetchers.ALL_BALANCES_ET_BOF,
    PAYMENT_TYPE_FLAT_FEE_POF,
]

PaymentTypeFlatFeeFetchersConfig = NamedTuple(
    "PaymentTypeFlatFeeFetchersConfig",
    [
        ("param_fetcher_id", str),
        ("denomination_param_id", str),
    ],
)

DEFAULT_PAYMENT_TYPE_FLAT_FEE_FETCHERS_CONFIG = PaymentTypeFlatFeeFetchersConfig(
    param_fetcher_id=PAYMENT_TYPE_FLAT_FEE_POF_ID,
    denomination_param_id=denomination_module.DENOMINATION_PARAM.id,
)


def get_parameters(
    vault: SmartContractVault, param_fetcher_id: str = PAYMENT_TYPE_FLAT_FEE_POF_ID
) -> dict[str, datetime | Decimal | str | None]:
    """Retrieves configuration parameters for the payment type flat fee feature."""
    return vault.get_parameters_observation(fetcher_id=param_fetcher_id).parameters


def _append_to_state(
    state: state_utils.SmartContractState,
    param_fetcher_id: str = PAYMENT_TYPE_FLAT_FEE_POF_ID,
) -> state_utils.SmartContractState:
    """Updates the contract state with specific parameter observations."""
    return state_utils.append_to_state(
        state=state,
        parameters=get_parameters(state.vault, param_fetcher_id),
    )


def apply_fees(
    state: state_utils.SmartContractState,
    posting_instructions: posting_utils.PostingInstructionListAlias,
    account_type: str,
    fetchers_config: PaymentTypeFlatFeeFetchersConfig = (
        DEFAULT_PAYMENT_TYPE_FLAT_FEE_FETCHERS_CONFIG
    ),
) -> List[CustomInstruction]:
    """Checks posting instruction details for a PAYMENT_TYPE key and returns fee instructions if the
    posting type matches a configured payment type with a flat fee.

    The fee is credited to the account defined by the payment_type_fee_income_account parameter.

    Args:
        state: The current state of the smart contract.
        posting_instructions: The list of posting instructions to evaluate for fees.
        account_type: The account type to be noted in the custom instruction details.
        fetchers_config: Configuration for the fetchers used to retrieve parameters.

    Returns:
        A list of CustomInstructions for charging any applicable fees.
    """
    state = _append_to_state(state=state, param_fetcher_id=fetchers_config.param_fetcher_id)
    rejection = state_utils.check_parameters_exist(
        state,
        {
            fetchers_config.denomination_param_id,
            PAYMENT_TYPE_FLAT_FEE_PARAM.id,
            PAYMENT_TYPE_FEE_INCOME_ACCOUNT_PARAM.id,
        },
    )
    assert rejection is None, rejection

    params: dict[str, datetime | Decimal | str | None] = state.parameters
    denomination: str = str(params[fetchers_config.denomination_param_id])
    income_account: str = str(params[PAYMENT_TYPE_FEE_INCOME_ACCOUNT_PARAM.id])
    flat_fees: dict[str, str] = loads(str(params[PAYMENT_TYPE_FLAT_FEE_PARAM.id]))

    def _map_posting_to_fee(posting: Any) -> CustomInstruction | None:
        payment_type: str | None = posting.instruction_details.get(PAYMENT_TYPE)
        if not payment_type or payment_type not in flat_fees:
            return None

        fee_amount = Decimal(flat_fees[payment_type])
        if fee_amount <= 0:
            return None

        balance_delta: Decimal = balance_utils.net_debit(
            balance_utils.get_available_balance(posting.balances(), denomination)
        )
        if balance_delta <= 0:
            return None

        return CustomInstruction(
            postings=posting_utils.create_postings(
                amount=fee_amount,
                debit_account=state.vault.account_id,
                credit_account=income_account,
                denomination=denomination,
            ),
            value_datetime=state.effective_datetime,
            instruction_details={
                **posting_utils.standard_instruction_details(
                    description=f"payment fee applied for withdrawal using {payment_type}",
                    event_type=APPLICATION_EVENT,
                    gl_impacted=True,
                    account_type=account_type,
                ),
                "payment_type": payment_type,
            },
            override_all_restrictions=True,
        )

    return [
        instruction
        for posting in posting_instructions
        if (instruction := _map_posting_to_fee(posting)) is not None
    ]
