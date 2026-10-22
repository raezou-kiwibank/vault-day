# Copyright @ 2026 Thought Machine Group Limited. All rights reserved.
__smart_contract_feature__ = True

# standard libs
from decimal import Decimal
from typing import Callable, NamedTuple

# feature library
import feature_library.common.balance_utils as balance_utils
import feature_library.common.denomination as denomination_module
import feature_library.common.posting_utils as posting_utils
import feature_library.common.state_utils as state_utils
import feature_library.common.utils as utils
import feature_library.lending.interfaces as lending_interfaces

# contracts api
from contracts_api import (
    DEFAULT_ADDRESS,
    DEFAULT_ASSET,
    BalanceCoordinate,
    BalanceDefaultDict,
    CustomInstruction,
    Phase,
    Posting,
    PostPostingHookArguments,
)

RepaymentAmounts = NamedTuple(
    "RepaymentAmounts",
    [
        ("unrounded_amount", Decimal),
        ("rounded_amount", Decimal),
    ],
)

RepaymentDistribution = NamedTuple(
    "RepaymentDistribution",
    [
        ("repayment_per_address", dict[str, RepaymentAmounts]),
        ("remaining_repayment_amount", Decimal),
    ],
)


def redistribute_postings(
    debit_account: str,
    denomination: str,
    amount: Decimal,
    credit_account: str,
    credit_address: str,
    debit_address: str = DEFAULT_ADDRESS,
) -> list[Posting]:
    """Redistribute a lump sum of payment into another account / address.

    Args:
        debit_account: The account id that receives initial sum and initiates the redistribution.
        denomination: The denomination of the application.
        amount: The amount to pay. If <= 0 an empty list is returned.
        credit_account: The account id that receives the redistributed amount.
        credit_address: The address to receive the redistributed amount in the credit_account.
        debit_address: The address from which to move the amount.

    Returns:
        The payment postings, in credit-debit pair.
    """
    if amount <= Decimal(0):
        return []
    return posting_utils.create_postings(
        amount=amount,
        debit_account=debit_account,
        credit_account=credit_account,
        denomination=denomination,
        debit_address=debit_address,
        credit_address=credit_address,
    )


def distribute_repayment_for_single_target(
    balances: BalanceDefaultDict,
    repayment_amount: Decimal,
    denomination: str,
    repayment_hierarchy: list[str],
    phase: Phase = Phase.COMMITTED,
) -> RepaymentDistribution:
    """Determine how a repayment amount is distributed across balances.

    Based on the repayment hierarchy and the outstanding balances. Each repayment
    hierarchy address' balance is rounded to 2 decimal points for repayment purposes.
    Both rounded and unrounded amounts are returned so that the consumer can decide how
    to handle remainders. For example, a repayment of 0.01 distributed to a balance of
    0.0052 or to a balance of 0.0012.

    Args:
        balances: The balances to distribute the repayment amount across.
        repayment_amount: The 2 decimal point repayment amount to distribute.
        denomination: The denomination of the repayment.
        repayment_hierarchy: Contains the order in which a repayment amount is to be
            distributed across addresses.
        phase: The balance phase of the balances fetched to get amounts from.

    Returns:
        A dictionary of addresses to repayment amounts to be repaid and the remaining
            repayment amount.
    """

    remaining_repayment_amount: Decimal = repayment_amount

    repayment_per_address: dict[str, RepaymentAmounts] = {}

    for repayment_address in repayment_hierarchy:
        bal_coord = BalanceCoordinate(repayment_address, DEFAULT_ASSET, denomination, phase)

        unrounded_address_amount: Decimal = balance_utils.net_debit(balances[bal_coord])
        rounded_address_amount: Decimal = utils.round_decimal(unrounded_address_amount, 2)

        rounded_address_repayment_amount: Decimal = min(
            rounded_address_amount, remaining_repayment_amount
        )
        # can't repay a balance that is < 2 decimal points - this should be dealt with in
        # close_code for early repayments
        if rounded_address_repayment_amount == Decimal(0):
            continue

        # ensure that the unrounded repayment amount is <= unrounded address amount
        # rounded repayment amount can be >, =, or < unrounded address amount
        unrounded_address_repayment_amount = (
            unrounded_address_amount
            if rounded_address_amount <= remaining_repayment_amount
            else remaining_repayment_amount
        )
        repayment_per_address[repayment_address] = RepaymentAmounts(
            unrounded_amount=unrounded_address_repayment_amount,
            rounded_amount=rounded_address_repayment_amount,
        )

        remaining_repayment_amount -= rounded_address_repayment_amount

    return RepaymentDistribution(
        repayment_per_address=repayment_per_address,
        remaining_repayment_amount=remaining_repayment_amount,
    )


def generate_repayment_postings(
    state: state_utils.SmartContractState,
    hook_arguments: PostPostingHookArguments,
    repayment_hierarchy_config: lending_interfaces.RepaymentHierarchyConfig,
    is_posting_early_repayment_callable: Callable[
        [
            state_utils.SmartContractState,
            Decimal,
            lending_interfaces.RepaymentHierarchyConfig,
            list[lending_interfaces.EarlyRepaymentFee],
        ],
        bool,
    ],
    handle_penalties_pending_capitalisation_callable: Callable[
        [state_utils.SmartContractState],
        list[CustomInstruction],
    ],
    overpayment_features: list[lending_interfaces.Overpayment] | None = None,
    early_repayment_fees: list[lending_interfaces.EarlyRepaymentFee] | None = None,
    repay_accrued_interest_callable: (
        Callable[[state_utils.SmartContractState, Decimal], list[Posting]] | None
    ) = None,
) -> list[CustomInstruction]:
    """Generates the necessary CustomInstructions to process a repayment.

    This includes redistributing the payment amount across the repayment hierarchy,
    handling any overpayments via specified features, and charging early repayment fees
    if applicable.

    Args:
        state: The current state of the smart contract.
        hook_arguments: Arguments from the post-posting hook.
        repayment_hierarchy_config: Configuration for the repayment hierarchy.
        is_posting_early_repayment_callable: Callable to determine if this is an
            early repayment.
        handle_penalties_pending_capitalisation_callable: Callable to handle penalties
            pending capitalisation.
        overpayment_features: Optional list of overpayment features to handle excess
            repayment.
        early_repayment_fees: Optional list of early repayment fees to charge.
        repay_accrued_interest_callable: Optional callable to repay accrued interest
            during overpayment.

    Returns:
        A list of CustomInstructions to be executed.
    """

    rejection = state_utils.check_parameters_exist(
        state=state, param_ids={denomination_module.DENOMINATION_PARAM_ID}
    )
    assert rejection is None, rejection

    denomination: str = state.parameters[denomination_module.DENOMINATION_PARAM_ID]  # type: ignore

    # here it is assumed that the repayment amount will always be in the DEFAULT balance address
    # associated with the first posting instruction, which should be enforced in the pre_posting
    # hook
    repayment_amount: Decimal = balance_utils.net_credit(
        bal=hook_arguments.posting_instructions[0].balances()[
            (DEFAULT_ADDRESS, DEFAULT_ASSET, denomination, Phase.COMMITTED)
        ]
    )

    balances = state.balances

    custom_instructions: list[CustomInstruction] = []

    repayment_hierarchy: list[str] = (
        repayment_hierarchy_config.repayment_hierarchy.get_repayment_hierarchy_order(
            state=state,
            fetchers_config=repayment_hierarchy_config.fetchers_config,
        )
    )

    repayment_postings: list[Posting] = []
    overpayment_amount = Decimal("0")

    if repayment_amount > 0:
        repayment_distribution: RepaymentDistribution = distribute_repayment_for_single_target(
            balances=balances,
            repayment_amount=repayment_amount,
            denomination=denomination,
            repayment_hierarchy=repayment_hierarchy,
        )

        overpayment_amount = repayment_distribution.remaining_repayment_amount

        for (
            repayment_address,
            repayment_address_amount,
        ) in repayment_distribution.repayment_per_address.items():
            # no postings are required when due balance is 0 or rounds to 0
            if repayment_address_amount.rounded_amount == Decimal(0):
                continue

            repayment_postings += redistribute_postings(
                debit_account=state.vault.account_id,
                amount=repayment_address_amount.rounded_amount,
                denomination=denomination,
                credit_account=state.vault.account_id,
                credit_address=repayment_address,
            )

        # Data transformation
        if repayment_postings:
            custom_instructions += [
                CustomInstruction(
                    postings=repayment_postings,
                    instruction_details={
                        "description": "Process a repayment",
                        "event": "PROCESS_REPAYMENTS",
                    },
                )
            ]

    # run overpayment feature logic
    if overpayment_amount > 0 and overpayment_features is not None:
        for overpayment_feature in overpayment_features:
            overpayment_postings = overpayment_feature.handle_overpayment(
                state=state,
                overpayment_amount=overpayment_amount,
                repay_accrued_interest_callable=repay_accrued_interest_callable,
            )

            # Data transformation
            if overpayment_postings:
                custom_instructions += [
                    CustomInstruction(
                        postings=overpayment_postings,
                        instruction_details={
                            "description": "Process repayment overpayment",
                            "event": "PROCESS_REPAYMENTS",
                        },
                    )
                ]

    if is_posting_early_repayment_callable(
        state,
        repayment_amount,
        repayment_hierarchy_config,
        early_repayment_fees if early_repayment_fees else [],
    ):
        custom_instructions.extend(handle_penalties_pending_capitalisation_callable(state))

        if early_repayment_fees:
            for early_repayment_fee in early_repayment_fees:
                amount_to_charge = early_repayment_fee.get_early_repayment_fee_amount(
                    state=state,
                )
                custom_instructions.extend(
                    early_repayment_fee.charge_early_repayment_fee(
                        state=state,
                        amount_to_charge=amount_to_charge,
                        fee_name=early_repayment_fee.fee_name,
                    )
                )

    return custom_instructions
