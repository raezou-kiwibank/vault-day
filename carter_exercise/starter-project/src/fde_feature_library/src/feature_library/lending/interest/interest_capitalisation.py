# Copyright @ 2026 Thought Machine Group Limited. All rights reserved.
__smart_contract_feature__ = True
# standard libs
from typing import NamedTuple

# feature library
import feature_library.common.accrual_utils as accruals
import feature_library.common.addresses as common_addresses
import feature_library.common.application_precision as application_precision_module
import feature_library.common.balance_utils as balance_utils
import feature_library.common.denomination as denomination_module
import feature_library.common.posting_utils as posting_utils
import feature_library.common.state_utils as state_utils
import feature_library.common.utils as utils
import feature_library.lending.addresses as lending_addresses

# contracts api
from contracts_api import (
    DEFAULT_ADDRESS,
    CustomInstruction,
    ExpectedParameter,
)

# Parameters
CAPITALISED_INTEREST_RECEIVABLE_ACCOUNT_PARAM_ID = "&{capitalised_interest_receivable_account}"
CAPITALISED_INTEREST_RECEIVABLE_ACCOUNT_PARAM = ExpectedParameter(
    id=CAPITALISED_INTEREST_RECEIVABLE_ACCOUNT_PARAM_ID,
    triggers_pre_parameter_change_hook=False,
    triggers_post_parameter_change_hook=False,
)

CAPITALISED_INTEREST_RECEIVED_ACCOUNT_PARAM_ID = "&{capitalised_interest_received_account}"
CAPITALISED_INTEREST_RECEIVED_ACCOUNT_PARAM = ExpectedParameter(
    id=CAPITALISED_INTEREST_RECEIVED_ACCOUNT_PARAM_ID,
    triggers_pre_parameter_change_hook=False,
    triggers_post_parameter_change_hook=False,
)

CAPITALISED_PENALTIES_RECEIVED_ACCOUNT_PARAM_ID = "&{capitalised_penalties_received_account}"
CAPITALISED_PENALTIES_RECEIVED_ACCOUNT_PARAM = ExpectedParameter(
    id=CAPITALISED_PENALTIES_RECEIVED_ACCOUNT_PARAM_ID,
    triggers_pre_parameter_change_hook=False,
    triggers_post_parameter_change_hook=False,
)

CAPITALISE_PENALTY_INTEREST_PARAM_ID = "&{capitalise_penalty_interest}"
CAPITALISE_PENALTY_INTEREST_PARAM = ExpectedParameter(
    id=CAPITALISE_PENALTY_INTEREST_PARAM_ID,
    triggers_pre_parameter_change_hook=False,
    triggers_post_parameter_change_hook=False,
)

expected_parameters = [
    CAPITALISED_INTEREST_RECEIVABLE_ACCOUNT_PARAM,
    CAPITALISED_INTEREST_RECEIVED_ACCOUNT_PARAM,
    CAPITALISED_PENALTIES_RECEIVED_ACCOUNT_PARAM,
    CAPITALISE_PENALTY_INTEREST_PARAM,
]


InterestCapitalisationFetchersConfig = NamedTuple(
    "InterestCapitalisationFetchersConfig",
    [
        ("application_precision_param_id", str),
        ("capitalised_interest_received_account_param_id", str),
        ("capitalised_interest_receivable_account_param_id", str),
        ("denomination_param_id", str),
    ],
)
DEFAULT_INTEREST_CAP_FETCHERS_CONFIG = InterestCapitalisationFetchersConfig(
    application_precision_param_id=application_precision_module.APPLICATION_PRECISION_PARAM.id,
    capitalised_interest_received_account_param_id=CAPITALISED_INTEREST_RECEIVED_ACCOUNT_PARAM_ID,
    capitalised_interest_receivable_account_param_id=CAPITALISED_INTEREST_RECEIVABLE_ACCOUNT_PARAM_ID,
    denomination_param_id=denomination_module.DENOMINATION_PARAM_ID,
)


def is_capitalise_penalty_interest(state: state_utils.SmartContractState) -> bool:
    """Return whether penalty interest is configured to be capitalised.

    Args:
        state: The smart contract state.

    Returns:
        True if penalty interest should be capitalised.
    """
    param: str = state.parameters[CAPITALISE_PENALTY_INTEREST_PARAM_ID]  # type: ignore
    return utils.str_to_bool(param)


def handle_overpayments_to_penalties_pending_capitalisation(
    state: state_utils.SmartContractState,
    account_type: str = "",
    accrual_address: str = lending_addresses.ACCRUED_OVERDUE_INTEREST_PENDING_CAPITALISATION,
    target_address: str = DEFAULT_ADDRESS,
) -> list[CustomInstruction]:
    """Handle overpayments applied to accrued overdue interest pending capitalisation.

    Args:
        state: The smart contract state.
        account_type: The type of account, e.g. LOAN or MORTGAGE.
        accrual_address: The address that the interest to capitalise is held at.
        target_address: The address to capitalise the interest to.

    Returns:
        Custom instructions to capitalise the penalty interest if necessary.
    """
    return handle_interest_capitalisation(
        state=state,
        account_type=account_type,
        accrual_address=accrual_address,
        target_address=target_address,
    )


def handle_penalty_interest_capitalisation(
    state: state_utils.SmartContractState,
    account_type: str,
    accrual_address: str = lending_addresses.ACCRUED_OVERDUE_INTEREST_PENDING_CAPITALISATION,
    target_address: str = lending_addresses.PRINCIPAL,
    fetchers_config: InterestCapitalisationFetchersConfig = DEFAULT_INTEREST_CAP_FETCHERS_CONFIG,
) -> list[CustomInstruction]:
    """Handle capitalisation of penalty interest if configured to do so.

    Args:
        state: The smart contract state.
        account_type: The type of account, e.g. LOAN or MORTGAGE.
        accrual_address: The address that the interest to capitalise is held at.
        target_address: The address to capitalise the interest to.
        fetchers_config: Fetcher configuration to use.

    Returns:
        Custom instructions to capitalise the penalty interest if necessary.
    """
    if is_capitalise_penalty_interest(state=state):
        return handle_interest_capitalisation(
            state=state,
            account_type=account_type,
            accrual_address=accrual_address,
            target_address=target_address,
        )

    return []


def handle_interest_capitalisation(
    state: state_utils.SmartContractState,
    account_type: str = "",
    accrual_address: str = lending_addresses.ACCRUED_INTEREST_PENDING_CAPITALISATION,
    target_address: str = lending_addresses.PRINCIPAL,
    fetchers_config: InterestCapitalisationFetchersConfig = DEFAULT_INTEREST_CAP_FETCHERS_CONFIG,
) -> list[CustomInstruction]:
    """Capitalise any accrued interest pending capitalisation after a repayment holiday ends.

    This may result in debit to PRINCIPAL and to the tracker balance for Capitalised Interest.
    This function needs running as frequently as the end of the repayment holiday needs detecting
    (e.g. run daily if you need to know by EOD) as we can't explicitly trigger any logic when a
    repayment holiday ends.

    Args:
        state: The smart contract state.
        account_type: The type of account, e.g. LOAN or MORTGAGE.
        accrual_address: The address that the interest to capitalise is held at.
        target_address: The address to capitalise the interest to.
        fetchers_config: Fetcher configuration to use.

    Returns:
        Posting instructions to capitalise the interest.
    """
    rejection = state_utils.check_parameters_exist(
        state=state,
        param_ids={
            fetchers_config.capitalised_interest_received_account_param_id,
            fetchers_config.capitalised_interest_receivable_account_param_id,
            fetchers_config.application_precision_param_id,
            fetchers_config.denomination_param_id,
        },
    )
    assert rejection is None, rejection

    capitalised_interest_received_account: str = state.parameters[
        fetchers_config.capitalised_interest_received_account_param_id
    ]  # type: ignore
    capitalised_interest_receivable_account: str = state.parameters[
        fetchers_config.capitalised_interest_receivable_account_param_id
    ]  # type: ignore
    application_precision: int = int(
        state.parameters[fetchers_config.application_precision_param_id]
    )

    event_type = "END_OF_REPAYMENT_HOLIDAY"
    denomination: str = state.parameters[fetchers_config.denomination_param_id]  # type: ignore

    accrued_capitalised_interest = balance_utils.balance_at_coordinates(
        balances=state.balances,
        address=accrual_address,
        denomination=denomination,
    )
    interest_to_apply = utils.round_decimal(
        amount=accrued_capitalised_interest, decimal_places=application_precision
    )

    if interest_to_apply <= 0:
        return []

    postings = accruals.create_receivable_accrual_application_postings(
        customer_account=state.vault.account_id,
        denomination=denomination,
        accrual_amount=accrued_capitalised_interest,
        application_amount=interest_to_apply,
        accrual_customer_address=accrual_address,
        accrual_internal_account=capitalised_interest_receivable_account,
        # TODO override to DEFAULT for early repayment
        application_customer_address=target_address,
        application_internal_account=capitalised_interest_received_account,
    ) + posting_utils.create_postings(
        amount=interest_to_apply,
        debit_account=state.vault.account_id,
        credit_account=state.vault.account_id,
        debit_address=lending_addresses.CAPITALISED_INTEREST_TRACKER,
        credit_address=common_addresses.INTERNAL_CONTRA,
        denomination=denomination,
    )

    return [
        CustomInstruction(
            postings=postings,
            instruction_details={
                "description": "Capitalise interest accrued to principal",
                "event": event_type,
                "gl_impacted": "True",
                "account_type": account_type,
            },
        )
    ]
