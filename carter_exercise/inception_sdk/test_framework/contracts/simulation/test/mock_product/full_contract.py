# Copyright @ 2020 - 2026 Thought Machine Group Limited. All rights reserved.
"""
This is a contract for testing vault caller, sourced from tutorial:
/tutorials/smart-contracts#full_contract

Some changes have been made to introduce new features not present in the contract, such as posting
enrichment.
"""
# standard libs
from decimal import ROUND_HALF_UP, Decimal
from typing import Union

# contracts api
from contracts_api import (
    DEFAULT_ADDRESS,
    DEFAULT_ASSET,
    AccountNotificationDirective,
    ActivationHookArguments,
    ActivationHookResult,
    BalanceCoordinate,
    BalancesObservationFetcher,
    CustomInstruction,
    DeactivationHookResult,
    DefinedDateTime,
    DenominationShape,
    DerivedParameterHookResult,
    NumberShape,
    OptionalShape,
    Override,
    Parameter,
    ParameterLevel,
    ParameterUpdatePermission,
    Phase,
    Posting,
    PostingInstructionEnrichment,
    PostingInstructionsDirective,
    PostPostingHookArguments,
    PostPostingHookResult,
    PrePostingHookArguments,
    PrePostingHookResult,
    Rejection,
    RejectionReason,
    RelativeDateTime,
    ScheduledEvent,
    ScheduledEventHookArguments,
    ScheduledEventHookResult,
    ScheduleExpression,
    SmartContractEventType,
    StringShape,
    fetch_account_data,
    requires,
)

api = "4.0.0"
version = "0.0.6"

parameters = [
    Parameter(
        name="denomination",
        shape=DenominationShape(),
        level=ParameterLevel.TEMPLATE,
        default_value="GBP",
    ),
    Parameter(
        name="overdraft_limit",
        shape=NumberShape(),
        level=ParameterLevel.TEMPLATE,
        description="Overdraft limit",
        display_name="Maximum overdraft permitted for this account",
        default_value=Decimal(100),
    ),
    Parameter(
        name="overdraft_fee",
        shape=NumberShape(),
        level=ParameterLevel.TEMPLATE,
        description="Overdraft fee",
        display_name="Fee charged on balances over overdraft limit",
        default_value=Decimal(20),
    ),
    Parameter(
        name="gross_interest_rate",
        shape=NumberShape(min_value=0, max_value=1, step=Decimal("0.01")),
        level=ParameterLevel.TEMPLATE,
        description="Gross interest rate",
        display_name="Rate paid on positive balances",
    ),
    Parameter(
        name="interest_payment_day",
        shape=OptionalShape(
            shape=NumberShape(min_value=1, max_value=28, step=1),
        ),
        level=ParameterLevel.INSTANCE,
        description="User-selected day of month to receive interest",
        display_name="Day of month to receive interest",
        update_permission=ParameterUpdatePermission.USER_EDITABLE,
    ),
    # Derived parameters
    Parameter(
        name="days_past_due",
        shape=NumberShape(step=Decimal(1)),
        level=ParameterLevel.INSTANCE,
        derived=True,
        description="The source of truth on how many days since the DUE balance was >0",
        display_name="Days Past Due",
    ),
    Parameter(
        name="expected_end_date",
        shape=StringShape(),
        level=ParameterLevel.INSTANCE,
        derived=True,
        description="Expected end date in the format Month/Day/Year",
        display_name="Expected end date",
    ),
]

data_fetchers = [
    BalancesObservationFetcher(
        fetcher_id="latest_balances",
        at=DefinedDateTime.EFFECTIVE_DATETIME,
    ),
    BalancesObservationFetcher(
        fetcher_id="live_balances",
        at=DefinedDateTime.LIVE,
    ),
    BalancesObservationFetcher(
        fetcher_id="end_of_day_balances",
        at=RelativeDateTime(
            origin=DefinedDateTime.EFFECTIVE_DATETIME,
            find=Override(hour=0, minute=0, second=0),
        ),
    ),
]

event_types = [
    SmartContractEventType(name="ACCRUE_INTEREST"),
    SmartContractEventType(name="APPLY_INTEREST"),
]

notification_types = ["overdraft_limit"]


@requires(parameters=True)
def activation_hook(
    vault, hook_arguments: ActivationHookArguments
) -> Union[ActivationHookResult, None]:

    # Accrue interest daily, at midnight
    interest_accrual_event = ScheduledEvent(
        expression=ScheduleExpression(hour=0, minute=0, second=0),
        start_datetime=hook_arguments.effective_datetime.astimezone(vault.events_timezone),
    )

    # Apply interest monthly, on the user-selected date, one-minute past midnight
    # If not set, default to the first of the month
    payment_day = vault.get_parameter_timeseries(name="interest_payment_day").latest()
    if not payment_day:
        payment_day = 1

    interest_application_event = ScheduledEvent(
        expression=ScheduleExpression(day=str(payment_day.value), hour=0, minute=1, second=0),
        start_datetime=hook_arguments.effective_datetime.astimezone(vault.events_timezone),
    )

    return ActivationHookResult(
        scheduled_events_return_value={
            "ACCRUE_INTEREST": interest_accrual_event,
            "APPLY_INTEREST": interest_application_event,
        }
    )


@requires(parameters=True)
@fetch_account_data(balances=["live_balances"])
def deactivation_hook(vault, hook_arguments):
    balances = vault.get_balances_observation(fetcher_id="live_balances").balances
    denomination = vault.get_parameter_timeseries(name="denomination").latest()

    if balances[(DEFAULT_ADDRESS, DEFAULT_ASSET, denomination, Phase.COMMITTED)].net != 0:
        return DeactivationHookResult(
            rejection=Rejection(
                message="Cannot close account until account balance nets to 0",
                reason_code=RejectionReason.AGAINST_TNC,
            )
        )


@requires(event_type="ACCRUE_INTEREST", parameters=True)
@fetch_account_data(event_type="ACCRUE_INTEREST", balances=["end_of_day_balances"])
@requires(event_type="APPLY_INTEREST", parameters=True)
@fetch_account_data(event_type="APPLY_INTEREST", balances=["latest_balances"])
def scheduled_event_hook(
    vault, hook_arguments: ScheduledEventHookArguments
) -> Union[ScheduledEventHookResult, None]:

    if hook_arguments.event_type == "ACCRUE_INTEREST":
        interest_accrual_postings = _get_interest_accrual_postings(
            vault, hook_arguments.effective_datetime
        )

        if interest_accrual_postings:
            return ScheduledEventHookResult(
                posting_instructions_directives=[
                    PostingInstructionsDirective(
                        posting_instructions=interest_accrual_postings,
                    )
                ],
            )

    if hook_arguments.event_type == "APPLY_INTEREST":
        interest_application_postings = _get_interest_application_postings(
            vault, hook_arguments.effective_datetime
        )

        if interest_application_postings:
            return ScheduledEventHookResult(
                posting_instructions_directives=[
                    PostingInstructionsDirective(
                        posting_instructions=interest_application_postings,
                    )
                ],
            )


@requires(parameters=True)
def pre_posting_hook(
    vault, hook_arguments: PrePostingHookArguments
) -> Union[PrePostingHookResult, None]:
    allowed_denomination = vault.get_parameter_timeseries(name="denomination").latest()

    if any(
        posting.denomination != allowed_denomination
        for posting in hook_arguments.posting_instructions
    ):
        return PrePostingHookResult(
            rejection=Rejection(
                message="Transactions must be in GBP only.",
                reason_code=RejectionReason.WRONG_DENOMINATION,
            )
        )

    enrichment_details = {}
    proposed = hook_arguments.posting_instructions[0]
    for proposed in hook_arguments.posting_instructions:
        enrichment_details[proposed.id] = PostingInstructionEnrichment(details={"key": "value"})
    return PrePostingHookResult(enrichment_details=enrichment_details)


@requires(parameters=True)
@fetch_account_data(balances=["latest_balances"])
def post_posting_hook(
    vault, hook_arguments: PostPostingHookArguments
) -> Union[PostPostingHookResult, None]:
    # Get the latest parameter values
    denomination = vault.get_parameter_timeseries(name="denomination").latest()
    overdraft_limit = vault.get_parameter_timeseries(name="overdraft_limit").latest()
    overdraft_fee = vault.get_parameter_timeseries(name="overdraft_fee").latest()

    # Fetch balances
    balances = vault.get_balances_observation(fetcher_id="latest_balances").balances

    committed_balances = balances[
        BalanceCoordinate(DEFAULT_ADDRESS, DEFAULT_ASSET, denomination, Phase.COMMITTED)
    ]
    net_committed_balance = committed_balances.net

    # Check if the committed balance is greater than the allowed overdraft
    if -net_committed_balance > overdraft_limit:
        # Charge the fee
        overdraft_fee_postings = _get_overdraft_fee_postings(overdraft_fee, denomination)
        if overdraft_fee_postings:
            return PostPostingHookResult(
                account_notification_directives=[
                    AccountNotificationDirective(
                        notification_type="overdraft_limit",
                        notification_details={"exceeded": "false"},
                    )
                ],
                posting_instructions_directives=[
                    PostingInstructionsDirective(
                        posting_instructions=overdraft_fee_postings,
                    )
                ],
            )
    return PostPostingHookResult(
        account_notification_directives=[
            AccountNotificationDirective(
                notification_type="overdraft_limit",
                notification_details={"exceeded": "false"},
            )
        ]
    )


@requires(parameters=True)
def derived_parameter_hook(vault, hook_arguments):
    # The logic is simplified just for testing return of derived parameter
    return DerivedParameterHookResult(
        parameters_return_value={"days_past_due": Decimal("10"), "expected_end_date": "2020-12-22"}
    )


def _get_overdraft_fee_postings(overdraft_fee, denomination):
    posting_instructions = _make_custom_transfer_instructions(
        amount=overdraft_fee,
        denomination=denomination,
        from_account_id="Main account",
        to_account_id="1",
    )
    return posting_instructions


def _make_custom_transfer_instructions(
    amount: Decimal,
    denomination: str,
    from_account_id: str,
    to_account_id: str,
    from_account_address: str = DEFAULT_ADDRESS,
    to_account_address: str = DEFAULT_ADDRESS,
    asset: str = DEFAULT_ASSET,
) -> list[CustomInstruction]:
    postings = [
        Posting(
            credit=True,
            amount=amount,
            denomination=denomination,
            account_id=to_account_id,
            account_address=to_account_address,
            asset=asset,
            phase=Phase.COMMITTED,
        ),
        Posting(
            credit=False,
            amount=amount,
            denomination=denomination,
            account_id=from_account_id,
            account_address=from_account_address,
            asset=asset,
            phase=Phase.COMMITTED,
        ),
    ]
    custom_instruction = CustomInstruction(
        postings=postings,
    )

    return [custom_instruction]


def _get_interest_application_postings(vault, effective_datetime):
    denomination = vault.get_parameter_timeseries(name="denomination").latest()
    balances = vault.get_balances_observation(fetcher_id="latest_balances").balances

    total_accrued_interest = balances[
        BalanceCoordinate("ACCRUED_INCOMING", DEFAULT_ASSET, denomination, Phase.COMMITTED)
    ].net

    amount_to_be_paid = _precision_fulfillment(total_accrued_interest)

    if amount_to_be_paid > 0:
        customer_transfer_instructions = _make_custom_transfer_instructions(
            amount=amount_to_be_paid,
            denomination=denomination,
            from_account_id=vault.account_id,
            from_account_address="ACCRUED_INCOMING",
            to_account_id=vault.account_id,
            to_account_address=DEFAULT_ADDRESS,
        )

        internal_account_transfer_instructions = _make_custom_transfer_instructions(
            amount=amount_to_be_paid,
            denomination=denomination,
            from_account_id="internal_account",
            from_account_address=DEFAULT_ADDRESS,
            to_account_id="internal_account",
            to_account_address="ACCRUED_OUTGOING",
        )

        posting_instructions = (
            customer_transfer_instructions + internal_account_transfer_instructions
        )

        return posting_instructions


def _get_interest_accrual_postings(vault, effective_datetime):
    accrued_interest = _calculate_accrued_interest(vault, effective_datetime)
    denomination = vault.get_parameter_timeseries(name="denomination").latest()

    if accrued_interest > 0:
        posting_instructions = _make_custom_transfer_instructions(
            amount=accrued_interest,
            denomination=denomination,
            from_account_id="internal_account",
            from_account_address="ACCRUED_OUTGOING",
            to_account_id=vault.account_id,
            to_account_address="ACCRUED_INCOMING",
        )
        return posting_instructions


def _calculate_accrued_interest(vault, effective_datetime):
    denomination = vault.get_parameter_timeseries(name="denomination").latest()

    # Fetch effective balance
    balances = vault.get_balances_observation(fetcher_id="end_of_day_balances").balances
    effective_balance = balances[
        BalanceCoordinate(DEFAULT_ADDRESS, DEFAULT_ASSET, denomination, Phase.COMMITTED)
    ].net

    # Fetch gross interest rate and calculate the daily rate
    gross_interest_rate = vault.get_parameter_timeseries(name="gross_interest_rate").at(
        at_datetime=effective_datetime
    )
    daily_rate = gross_interest_rate / 365

    accrued_interest = _precision_accrual(effective_balance * daily_rate)

    return accrued_interest


def _precision_accrual(amount):
    return amount.quantize(Decimal(".00001"), rounding=ROUND_HALF_UP)


def _precision_fulfillment(amount):
    return amount.quantize(Decimal(".01"), rounding=ROUND_HALF_UP)


# flake8: noqa
# mypy: ignore-errors
