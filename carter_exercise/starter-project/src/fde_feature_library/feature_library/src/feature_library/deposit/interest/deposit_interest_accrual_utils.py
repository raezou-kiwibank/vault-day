__smart_contract_feature__ = True

# standard libs
from decimal import Decimal

import feature_library.common.accrual_utils as accruals
import feature_library.common.balance_utils as balance_utils
import feature_library.common.denomination as denomination
import feature_library.common.fetchers as fetchers
import feature_library.common.posting_utils as posting_utils
import feature_library.common.state_utils as state_utils
import feature_library.deposit.addresses as deposit_addresses

# contracts api
from contracts_api import DEFAULT_ADDRESS, Balance, BalanceDefaultDict, CustomInstruction

# inception sdk


def get_accrual_capital(
    *,
    state: state_utils.SmartContractState,
    denomination_param_id: str = denomination.DENOMINATION_PARAM_ID,
    balances: BalanceDefaultDict | None = None,
    capital_addresses: list[str] | None = None,
) -> Balance:
    """Get the capital balance to accrue interest on."""

    rejection = state_utils.check_parameters_exist(state=state, param_ids={denomination_param_id})
    assert rejection is None, rejection

    denomination: str = state.parameters.get(denomination_param_id)  # type: ignore

    # Default to DEFAULT address if none provided
    capital_addresses = capital_addresses or [DEFAULT_ADDRESS]

    # Check if we have the balances for these addresses in state
    coordinates = balance_utils.get_coordinates(
        addresses=capital_addresses, denomination=denomination
    )

    if not state_utils.is_coordinates_in_state(state=state, coordinates=coordinates):
        # We must update the state with the required balances
        state = state_utils.append_to_state(
            state=state,
            balances=state.vault.get_balances_observation(
                fetcher_id=fetchers.ALL_BALANCES_ET_BOF_ID
            ).balances,
        )

    return balance_utils.sum_balances(
        balances=balances or state.balances,
        addresses=capital_addresses,
        denomination=denomination,
    )


def get_interest_reversal_postings(
    *,
    state: state_utils.SmartContractState,
    event_name: str,
    account_type: str = "",
    balances: BalanceDefaultDict | None = None,
    denomination_param_id: str = denomination.DENOMINATION_PARAM_ID,
    accrued_payable_account_param_id: str = "",
    accrued_receivable_account_param_id: str = "",
    accrued_payable_address: str = deposit_addresses.ACCRUED_INTEREST_PAYABLE,
    accrued_receivable_address: str = deposit_addresses.ACCRUED_INTEREST_RECEIVABLE,
) -> list[CustomInstruction]:
    """Reverse any accrued interest and apply back to the internal account."""
    custom_instructions: list[CustomInstruction] = []

    rejection = state_utils.check_parameters_exist(
        state=state,
        param_ids={
            denomination_param_id,
            accrued_payable_account_param_id,
            accrued_receivable_account_param_id,
        },
    )
    assert rejection is None, rejection

    denomination: str = state.parameters.get(denomination_param_id)  # type: ignore
    accrued_payable_account: str = state.parameters.get(accrued_payable_account_param_id)  # type: ignore
    accrued_receivable_account: str = state.parameters.get(accrued_receivable_account_param_id)  # type: ignore

    if not balances:
        state = state_utils.append_to_state(
            state=state,
            balances=state.vault.get_balances_observation(
                fetcher_id=fetchers.ALL_BALANCES_ET_BOF_ID
            ).balances,
        )

    balances = balances or state.balances

    if accrued_interest_receivable := balance_utils.sum_balances(
        balances=balances,
        addresses=[accrued_receivable_address],
        denomination=denomination,
    ).net:
        custom_instructions.extend(
            accruals.create_payable_accrual_custom_instruction(
                customer_account=state.vault.account_id,
                customer_address=accrued_receivable_address,
                denomination=denomination,
                amount=accrued_interest_receivable,
                internal_account=accrued_receivable_account,
                instruction_details=posting_utils.standard_instruction_details(
                    description=f"Reversing {accrued_interest_receivable} {denomination} "
                    "of accrued interest",
                    event_type=event_name,
                    gl_impacted=True,
                    account_type=account_type,
                ),
                reversal=True,
            )
        )

    if accrued_interest_payable := balance_utils.sum_balances(
        balances=balances,
        addresses=[accrued_payable_address],
        denomination=denomination,
    ).net:
        custom_instructions.extend(
            accruals.create_payable_accrual_custom_instruction(
                customer_account=state.vault.account_id,
                customer_address=accrued_payable_address,
                denomination=denomination,
                amount=accrued_interest_payable,
                internal_account=accrued_payable_account,
                instruction_details=posting_utils.standard_instruction_details(
                    description=f"Reversing {accrued_interest_payable} {denomination} "
                    "of accrued interest",
                    event_type=event_name,
                    gl_impacted=True,
                    account_type=account_type,
                ),
                reversal=True,
            )
        )

    return custom_instructions


def get_target_customer_address_and_internal_account(
    *,
    accrual_amount: Decimal,
    accrued_interest_payable_account: str = "",
    accrued_interest_receivable_account: str = "",
) -> tuple[str, str]:
    """Return the payable or receivable customer address and internal account based on the
    sign of the accrual amount
    """
    return (
        (deposit_addresses.ACCRUED_INTEREST_PAYABLE, accrued_interest_payable_account)
        if accrual_amount >= 0
        else (
            deposit_addresses.ACCRUED_INTEREST_RECEIVABLE,
            accrued_interest_receivable_account,
        )
    )
