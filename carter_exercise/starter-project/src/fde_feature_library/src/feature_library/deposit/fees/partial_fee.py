__smart_contract_feature__ = True

# standard libs
from decimal import Decimal
from typing import NamedTuple

# feature library
import feature_library.common.addresses as addresses
import feature_library.common.balance_utils as balance_utils
import feature_library.common.denomination as denomination_module
import feature_library.common.fetchers as fetchers
import feature_library.common.posting_utils as posting_utils
import feature_library.common.state_utils as state_utils
import feature_library.deposit.interfaces as deposit_interfaces

# contracts api
from contracts_api import (
    DEFAULT_ADDRESS,
    DEFAULT_ASSET,
    BalanceCoordinate,
    BalanceDefaultDict,
    CustomInstruction,
    Phase,
)

# inception sdk

PartialFeeFetchersConfig = NamedTuple(
    "PartialFeeFetchersConfig",
    [
        ("balances_fetcher_id", str),
        ("denomination_param_id", str),
    ],
)
DEFAULT_PARTIAL_FEE_FETCHERS_CONFIG = PartialFeeFetchersConfig(
    balances_fetcher_id=fetchers.ALL_BALANCES_ET_BOF_ID,
    denomination_param_id=denomination_module.DENOMINATION_PARAM.id,
)


def charge_partial_fee(
    state: state_utils.SmartContractState,
    fee_custom_instruction: CustomInstruction,
    fee_details: deposit_interfaces.PartialFeeCollection,
    available_balance_feature: deposit_interfaces.AvailableBalance | None = None,
    fetchers_config: PartialFeeFetchersConfig = DEFAULT_PARTIAL_FEE_FETCHERS_CONFIG,
) -> list[CustomInstruction]:
    """Charge a Partial fee, intended to wrap an existing fee custom instruction.

    Fees are generally charged from a scheduled event.

    Args:
        state: the SmartContractState object.
        fee_custom_instruction: The custom fee instruction to wrap.
        fee_details: The associated fee details, implemented in a common feature definition.
        available_balance_feature: Interface to calculate the available balance for the account
            using a custom definition.
        fetchers_config: the configuration for the fetchers used to retrieve balances
            and denomination.

    Returns:
        An augmented list of CustomInstructions containing the partial fee instructions
        if required.
    """
    state = state_utils.append_to_state(
        state=state,
        balances=state.vault.get_balances_observation(
            fetcher_id=fetchers_config.balances_fetcher_id,
        ).balances,
    )
    rejection = state_utils.check_parameters_exist(
        state, param_ids={fetchers_config.denomination_param_id}
    )
    assert rejection is None, rejection

    denomination: str = state.parameters[fetchers_config.denomination_param_id]  # type: ignore
    incoming_fee_balances: BalanceDefaultDict = fee_custom_instruction.balances(
        account_id=state.vault.account_id, tside=state.vault.tside
    )
    fee_amount: Decimal = balance_utils.net_debit(
        incoming_fee_balances[
            BalanceCoordinate(
                account_address=DEFAULT_ADDRESS,
                asset=DEFAULT_ASSET,
                denomination=denomination,
                phase=Phase.COMMITTED,
            )
        ]
    )

    available_amount = (
        available_balance_feature.calculate(state=state)
        if available_balance_feature
        else balance_utils.get_available_balance(
            balances=state.balances, denomination=denomination
        ).net
    )

    if available_amount >= fee_amount:
        return [fee_custom_instruction]
    chargeable_fee = min(fee_amount, available_amount)
    outstanding_fee = fee_amount - chargeable_fee
    partial_fee_address = fee_details.outstanding_fee_address
    fee_internal_account = state.parameters[fee_details.internal_account_parameter_id]

    custom_instructions: list[CustomInstruction] = []

    # modify instruction details
    incoming_fee_details = fee_custom_instruction.instruction_details
    if "description" in incoming_fee_details:
        incoming_fee_details["description"] += (
            f" Partially charged, remaining {outstanding_fee}"
            " to be charged when the account has sufficient balance"
        )
    else:
        incoming_fee_details["description"] = fee_details.fee_type
    if chargeable_fee > 0:
        custom_instructions.append(
            CustomInstruction(
                postings=posting_utils.create_postings(
                    amount=chargeable_fee,
                    debit_account=state.vault.account_id,
                    credit_account=fee_internal_account,
                    denomination=denomination,
                ),
                instruction_details=incoming_fee_details,
                override_all_restrictions=True,
            )
        )

    if outstanding_fee > 0:
        custom_instructions.extend(
            modify_tracking_balance_utils(
                account_id=state.vault.account_id,
                denomination=denomination,
                tracking_address=partial_fee_address,
                value=outstanding_fee,
                instruction_details={
                    "description": f"Charge outstanding partial fee: {fee_details.fee_type}",
                    "event": f"Charge {fee_details.fee_type}",
                },
            )
        )

    return custom_instructions


OUTSTANDING_FEES_DEFAULT_FETCHERS_CONFIG = PartialFeeFetchersConfig(
    balances_fetcher_id=fetchers.ALL_BALANCES_LIVE_BOF.fetcher_id,
    denomination_param_id=denomination_module.DENOMINATION_PARAM.id,
)


def charge_outstanding_fees(
    state: state_utils.SmartContractState,
    fee_collection: list[deposit_interfaces.PartialFeeCollection],
    available_balance_feature: deposit_interfaces.AvailableBalance | None = None,
    fetchers_config: PartialFeeFetchersConfig = OUTSTANDING_FEES_DEFAULT_FETCHERS_CONFIG,
) -> list[CustomInstruction]:
    """Charge outstanding fees from the post posting hook.

    This addresses charging of outstanding partial amounts based on a pre-defined
    static repayment hierarchy. It will reduce the tracking balance by the
    amount charged.

    Args:
        state: the SmartContractState object.
        fee_collection: The list of partial fees to collect from. The order will define
            the repayment hierarchy.
        available_balance_feature: Interface to calculate the available balance for the account
            using a custom definition.
        fetchers_config: the configuration for the fetchers used to retrieve balances
            and denomination.

    Returns:
        a list of CustomInstructions to execute due to outstanding fees.
    """
    state = state_utils.append_to_state(
        state=state,
        balances=state.vault.get_balances_observation(
            fetcher_id=fetchers_config.balances_fetcher_id,
        ).balances,
    )
    rejection = state_utils.check_parameters_exist(
        state, param_ids={fetchers_config.denomination_param_id}
    )
    assert rejection is None, rejection

    denomination: str = state.parameters[fetchers_config.denomination_param_id]  # type: ignore
    custom_instructions: list[CustomInstruction] = []
    account_available_balance = (
        available_balance_feature.calculate(state=state)
        if available_balance_feature
        else balance_utils.get_available_balance(
            balances=state.balances, denomination=denomination
        ).net
    )

    for fee in fee_collection:
        if account_available_balance <= Decimal("0"):
            break
        outstanding_fee_address = fee.outstanding_fee_address
        outstanding_fee_amount = balance_utils.balance_at_coordinates(
            address=outstanding_fee_address, balances=state.balances, denomination=denomination
        )
        amount_to_charge = min(outstanding_fee_amount, account_available_balance)
        fee_internal_account = state.parameters[fee.internal_account_parameter_id]

        if amount_to_charge > Decimal(0):
            custom_instructions.append(
                CustomInstruction(
                    postings=posting_utils.create_postings(
                        amount=amount_to_charge,
                        debit_account=state.vault.account_id,
                        credit_account=fee_internal_account,
                        denomination=denomination,
                    ),
                    instruction_details={
                        "description": f"Charge outstanding partial fee: {fee.fee_type}",
                        "event": f"Charge {fee.fee_type}",
                    },
                    override_all_restrictions=True,
                )
            )
            custom_instructions.extend(
                modify_tracking_balance_utils(
                    account_id=state.vault.account_id,
                    denomination=denomination,
                    tracking_address=outstanding_fee_address,
                    value=amount_to_charge,
                    payment_deduction=True,
                    instruction_details={
                        "description": f"Charge outstanding partial fee: {fee.fee_type}",
                        "event": f"Charge {fee.fee_type}",
                    },
                ),
            )
            account_available_balance -= amount_to_charge

    return custom_instructions


def has_outstanding_fees(
    state: state_utils.SmartContractState,
    fee_collection: list[deposit_interfaces.PartialFeeCollection],
    fetchers_config: PartialFeeFetchersConfig = OUTSTANDING_FEES_DEFAULT_FETCHERS_CONFIG,
) -> bool:
    """Check for any outstanding fees.

    This can be used in the Deactivation Hook to block account closure.

    Args:
        state: the SmartContractState object.
        fee_collection: The list of partial fees to collect from.
        fetchers_config: the configuration for the fetchers used to retrieve balances
            and denomination.

    Returns:
        True if any of the fees have an outstanding balance.
    """
    state = state_utils.append_to_state(
        state=state,
        balances=state.vault.get_balances_observation(
            fetcher_id=fetchers_config.balances_fetcher_id,
        ).balances,
    )
    rejection = state_utils.check_parameters_exist(
        state, param_ids={fetchers_config.denomination_param_id}
    )
    assert rejection is None, rejection

    denomination: str = state.parameters[fetchers_config.denomination_param_id]  # type: ignore

    return any(
        balance_utils.balance_at_coordinates(
            address=fee.outstanding_fee_address,
            balances=state.balances,
            denomination=denomination,
        )
        > Decimal(0)
        for fee in fee_collection
    )


def modify_tracking_balance_utils(
    account_id: str,
    denomination: str,
    tracking_address: str,
    value: Decimal,
    payment_deduction: bool = False,
    instruction_details: dict[str, str] | None = None,
) -> list[CustomInstruction]:
    """Increase the tracking balance for a partial payment address.

    To decrease the value on the tracking, set the payment_deduction argument to True to imply the
    tracking balance has been decreased due to the amount owed being paid.

    Args:
        account_id: the account ID to modify the tracking balance for.
        denomination: the denomination of the account.
        tracking_address: the Partial Payment Tracking Address.
        value: The amount to INCREASE the tracking balance by, or DECREASE if PAYMENT_DEDUCTION
            is TRUE.
        payment_deduction: Whether or not to reverse the instruction by the amount.
        instruction_details: Optional instruction details for the custom instruction.

    Returns:
        returns the resulting custom instruction.
    """
    debit_address = addresses.INTERNAL_CONTRA
    credit_address = tracking_address

    if value <= 0:
        return []

    # flip addresses if deducting from tracking balance due to a payment
    if payment_deduction:
        credit_address = debit_address
        debit_address = tracking_address

    return [
        CustomInstruction(
            postings=posting_utils.create_postings(
                amount=value,
                debit_account=account_id,
                debit_address=debit_address,
                credit_account=account_id,
                credit_address=credit_address,
                denomination=denomination,
            ),
            instruction_details=instruction_details or {},
            override_all_restrictions=True,
        )
    ]
