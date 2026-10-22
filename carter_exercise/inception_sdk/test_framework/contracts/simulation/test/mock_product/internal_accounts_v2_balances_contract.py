# Copyright @ 2023 Thought Machine Group Limited. All rights reserved.

# standard libs
from decimal import ROUND_HALF_UP, Decimal
from typing import Optional

# contracts api
from contracts_api import (
    DEFAULT_ADDRESS,
    DEFAULT_ASSET,
    AccountNotificationDirective,
    ActivationHookArguments,
    ActivationHookResult,
    BalanceCoordinate,
    BalanceDefaultDict,
    BalancesObservationFetcher,
    CustomInstruction,
    DefinedDateTime,
    Phase,
    Posting,
    PostingInstructionsDirective,
    PostPostingHookArguments,
    PostPostingHookResult,
    Tside,
    fetch_account_data,
)

api = "4.0.0"
version = "1.0.0"
display_name = "Debugging Contract"
summary = "Debugging Contract"
tside = Tside.LIABILITY

# this can be amended to whichever other currencies as needed
supported_denominations = ["GBP", "EUR"]

PRODUCT_NAME = "internal_account_balances"

EFFECTIVE_OBSERVATION_FETCHER_ID = "EFFECTIVE_FETCHER"
EFFECTIVE_OBSERVATION_FETCHER = BalancesObservationFetcher(
    fetcher_id=EFFECTIVE_OBSERVATION_FETCHER_ID, at=DefinedDateTime.EFFECTIVE_DATETIME
)
LIVE_BALANCES_BOF_ID = "live_balances_bof"
LIVE_BALANCES_BOF = BalancesObservationFetcher(
    fetcher_id=LIVE_BALANCES_BOF_ID, at=DefinedDateTime.LIVE
)
data_fetchers = [LIVE_BALANCES_BOF, EFFECTIVE_OBSERVATION_FETCHER]

DEBUG_NOTIFICATION = "DEBUG_NOTIFICATION"
notification_types: list[str] = [DEBUG_NOTIFICATION]


def activation_hook(
    vault, hook_arguments: ActivationHookArguments
) -> Optional[ActivationHookResult]:
    # Return two PIDs so that the sim response has multiple PIBs in one result
    return ActivationHookResult(
        posting_instructions_directives=[
            # Debit IA "1" with £100 on activation
            PostingInstructionsDirective(
                posting_instructions=[
                    CustomInstruction(
                        postings=utils_create_postings(
                            amount=Decimal("100"),
                            debit_account="1",
                            credit_account=vault.account_id,
                        )
                    )
                ]
            ),
            # Credit IA "2" with £50 on activation
            PostingInstructionsDirective(
                posting_instructions=[
                    CustomInstruction(
                        postings=utils_create_postings(
                            amount=Decimal("50"),
                            debit_account=vault.account_id,
                            credit_account="2",
                        )
                    )
                ]
            ),
        ]
    )


@fetch_account_data(balances=[LIVE_BALANCES_BOF_ID])
def post_posting_hook(vault, hook_arguments: PostPostingHookArguments) -> PostPostingHookResult:
    balances = vault.get_balances_observation(fetcher_id=LIVE_BALANCES_BOF_ID).balances
    default_committed = utils_balance_at_coordinates(balances=balances, denomination="GBP")

    return PostPostingHookResult(
        account_notification_directives=[
            AccountNotificationDirective(
                notification_type=DEBUG_NOTIFICATION,
                notification_details={"default_committed": str(default_committed)},
            )
        ],
    )


def utils_round_decimal(
    amount: Decimal, decimal_places: int, rounding: str = ROUND_HALF_UP
) -> Decimal:
    """
    Round an amount to specified number of decimal places
    :param amount: Decimal, amount to round
    :param decimal_places: int, number of places to round to
    :param rounding: the type of rounding strategy to use
    :return: Decimal, rounded amount
    """
    return amount.quantize(Decimal((0, (1,), -int(decimal_places))), rounding=rounding)


def utils_create_postings(
    amount: Decimal,
    debit_account: str,
    credit_account: str,
    debit_address: str = DEFAULT_ADDRESS,
    credit_address: str = DEFAULT_ADDRESS,
    denomination: str = "GBP",
    asset: str = DEFAULT_ASSET,
) -> list[Posting]:
    """
    Creates a pair of postings to debit the debit_address on debit_account
    and credit the credit_address on credit_account by the specified amount

    :param amount: The amount to pay. If the amount is <= 0, an empty list is returned
    :param debit_account: The account from which to debit the amount
    :param credit_account: The account to which to credit the amount
    :param debit_address: The address from which to move the amount
    :param credit_address: The address to which to move the amount
    :param denomination: The denomination of the postings
    :param asset: The asset of the postings
    :return: The credit-debit pair of postings
    """
    if amount <= Decimal("0"):
        return []
    return [
        Posting(
            credit=True,
            amount=amount,
            denomination=denomination,
            account_id=credit_account,
            account_address=credit_address,
            asset=asset,
            phase=Phase.COMMITTED,
        ),
        Posting(
            credit=False,
            amount=amount,
            denomination=denomination,
            account_id=debit_account,
            account_address=debit_address,
            asset=asset,
            phase=Phase.COMMITTED,
        ),
    ]


def utils_balance_at_coordinates(
    *,
    balances: BalanceDefaultDict,
    address: str = DEFAULT_ADDRESS,
    denomination: str,
    asset: str = DEFAULT_ASSET,
    phase: Phase = Phase.COMMITTED,
    decimal_places: int | None = None
) -> Decimal:
    balance_net = balances[BalanceCoordinate(address, asset, denomination, phase)].net
    return (
        balance_net
        if decimal_places is None
        else utils_round_decimal(amount=balance_net, decimal_places=decimal_places)
    )
