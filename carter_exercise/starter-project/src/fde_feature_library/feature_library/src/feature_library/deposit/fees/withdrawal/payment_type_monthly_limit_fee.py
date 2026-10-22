# Copyright @ 2026 Thought Machine Group Limited. All rights reserved.
__smart_contract_feature__ = True

# standard libs
from datetime import datetime
from decimal import Decimal
from json import loads
from typing import List, Mapping, NamedTuple
from zoneinfo import ZoneInfo

# feature library
import feature_library.common.client_transaction_utils as client_transaction_utils
import feature_library.common.denomination as denomination_module
import feature_library.common.posting_utils as posting_utils
import feature_library.common.state_utils as state_utils

# contracts api
from contracts_api import (
    ClientTransaction,
    CustomInstruction,
    DefinedDateTime,
    ExpectedParameter,
    ParametersFilter,
    ParametersObservationFetcher,
    PostingsIntervalFetcher,
    RelativeDateTime,
    Shift,
)

# inception sdk
from inception_sdk.vault.contracts.extensions.contracts_api_extensions import SmartContractVault

PAYMENT_TYPE = "PAYMENT_TYPE"
APPLICATION_EVENT = "APPLY_PAYMENT_TYPE_WITHDRAWAL_LIMIT_FEES"
UTC = ZoneInfo("UTC")

# Parameters
MAXIMUM_MONTHLY_PAYMENT_TYPE_WITHDRAWAL_LIMIT_PARAM_ID = (
    "&{maximum_monthly_payment_type_withdrawal_limit}"
)
"""
The parameter value should look like this:
{
    "ATM": {"fee": "0.50", "limit": "8"},
}
"""
MAXIMUM_MONTHLY_PAYMENT_TYPE_WITHDRAWAL_LIMIT_PARAM = ExpectedParameter(
    id=MAXIMUM_MONTHLY_PAYMENT_TYPE_WITHDRAWAL_LIMIT_PARAM_ID,
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
    MAXIMUM_MONTHLY_PAYMENT_TYPE_WITHDRAWAL_LIMIT_PARAM,
    PAYMENT_TYPE_FEE_INCOME_ACCOUNT_PARAM,
    denomination_module.DENOMINATION_PARAM,
]

# Fetchers
MONTHLY_LIMIT_FEES_POF_ID = "monthly_limit_fees_pof"
MONTHLY_LIMIT_FEES_POF = ParametersObservationFetcher(
    fetcher_id=MONTHLY_LIMIT_FEES_POF_ID,
    at=DefinedDateTime.EFFECTIVE_DATETIME,
    filter=ParametersFilter(parameter_ids=[p.id for p in expected_parameters]),
)

# Retrieves all the postings that happened from the previous month to the effective date.
MONTH_TO_EFFECTIVE_POSTIF_ID = "MONTH_TO_EFFECTIVE_POSTIF"
MONTH_TO_EFFECTIVE_POSTIF = PostingsIntervalFetcher(
    fetcher_id=MONTH_TO_EFFECTIVE_POSTIF_ID,
    start=RelativeDateTime(origin=DefinedDateTime.EFFECTIVE_DATETIME, shift=Shift(days=-31)),
    end=DefinedDateTime.EFFECTIVE_DATETIME,
)

data_fetchers = [
    MONTHLY_LIMIT_FEES_POF,
    MONTH_TO_EFFECTIVE_POSTIF,
]

PaymentTypeMonthlyLimitFeeFetchersConfig = NamedTuple(
    "PaymentTypeMonthlyLimitFeeFetchersConfig",
    [
        ("param_fetcher_id", str),
        ("client_transaction_fetcher_id", str),
        ("denomination_param_id", str),
    ],
)

DEFAULT_PAYMENT_TYPE_MONTHLY_LIMIT_FEE_FETCHERS_CONFIG = PaymentTypeMonthlyLimitFeeFetchersConfig(
    param_fetcher_id=MONTHLY_LIMIT_FEES_POF_ID,
    client_transaction_fetcher_id=MONTH_TO_EFFECTIVE_POSTIF_ID,
    denomination_param_id=denomination_module.DENOMINATION_PARAM.id,
)


def get_parameters(
    vault: SmartContractVault, param_fetcher_id: str = MONTHLY_LIMIT_FEES_POF_ID
) -> dict[str, datetime | Decimal | str | None]:
    """Retrieves configuration parameters for the payment type monthly limit fee feature."""
    return vault.get_parameters_observation(fetcher_id=param_fetcher_id).parameters


def _append_to_state(
    state: state_utils.SmartContractState,
    param_fetcher_id: str = MONTHLY_LIMIT_FEES_POF_ID,
) -> state_utils.SmartContractState:
    """Updates the contract state with specific parameter observations."""
    return state_utils.append_to_state(
        state=state,
        parameters=get_parameters(state.vault, param_fetcher_id),
    )


def apply_fees(
    state: state_utils.SmartContractState,
    updated_client_transactions: Mapping[str, ClientTransaction],
    account_type: str,
    historic_client_transactions: Mapping[str, ClientTransaction] | None = None,
    fetchers_config: PaymentTypeMonthlyLimitFeeFetchersConfig = (
        DEFAULT_PAYMENT_TYPE_MONTHLY_LIMIT_FEE_FETCHERS_CONFIG
    ),
) -> List[CustomInstruction]:
    """Checks client transactions for PAYMENT_TYPE key and returns fee instructions if the
    number of payments exceeds a monthly limit for that payment type.

    The fee is credited to the account defined by the payment_type_fee_income_account parameter.

    Args:
        state: The current state of the smart contract.
        updated_client_transactions: New or updated client transactions that may count towards
            the limit.
        account_type: The account type to be noted in the custom instruction details.
        historic_client_transactions: Historic client transactions from start-of-month.
            If None, fetched using the configured fetcher.
        fetchers_config: Configuration for the fetchers used.

    Returns:
        A list of CustomInstructions for charging any applicable fees.
    """
    state = _append_to_state(state=state, param_fetcher_id=fetchers_config.param_fetcher_id)

    rejection = state_utils.check_parameters_exist(
        state,
        {
            fetchers_config.denomination_param_id,
            MAXIMUM_MONTHLY_PAYMENT_TYPE_WITHDRAWAL_LIMIT_PARAM_ID,
            PAYMENT_TYPE_FEE_INCOME_ACCOUNT_PARAM_ID,
        },
    )
    assert rejection is None, rejection

    params: dict[str, datetime | Decimal | str | None] = state.parameters
    denomination: str = str(params[fetchers_config.denomination_param_id])
    income_account: str = str(params[PAYMENT_TYPE_FEE_INCOME_ACCOUNT_PARAM_ID])
    monthly_limits: dict[str, dict[str, str]] = loads(
        str(params[MAXIMUM_MONTHLY_PAYMENT_TYPE_WITHDRAWAL_LIMIT_PARAM_ID])
    )

    """
    The config object for the payment type should look like this:
    {"fee": "0.50", "limit": "8"}
    """
    valid_payment_types: list[str] = [
        payment_type
        for payment_type, config in monthly_limits.items()
        if Decimal(config.get("fee", "0")) > 0 and int(config.get("limit", "-1")) >= 0
    ]

    if not valid_payment_types:
        return []

    if historic_client_transactions is None:
        historic_client_transactions = state.vault.get_client_transactions(
            fetcher_id=fetchers_config.client_transaction_fetcher_id
        )

    start_of_month: datetime = (
        state.effective_datetime.astimezone(state.vault.events_timezone)
        .replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        .astimezone(UTC)
    )

    historic_debits_by_type, proposed_debits_by_type = (
        client_transaction_utils.extract_interval_and_proposed_debits(
            denomination=denomination,
            interval_transactions=dict(historic_client_transactions),
            proposed_transactions=dict(updated_client_transactions),
            transaction_type_key=PAYMENT_TYPE,
            transaction_types=valid_payment_types,
            interval_start=start_of_month,
            effective_datetime=state.effective_datetime,
        )
    )

    def calculate_fee(pt: str) -> Decimal:
        """Calculates the fee for a given payment type based on the proposed transactions
        and the remaining monthly limit.

        Args:
            pt: The payment type to calculate the fee for.

        Returns:
            The total fee amount for the payment type.
        """
        config = monthly_limits[pt]
        limit = int(config["limit"])
        fee_amount = Decimal(config["fee"])

        historic_count = len(historic_debits_by_type.get(pt, {}))
        proposed_count = len(proposed_debits_by_type.get(pt, {}))

        # Logic: fees apply only to the portion of proposed transactions
        # that exceed the remaining monthly limit.
        num_fees = max(0, proposed_count - max(0, limit - historic_count))
        return num_fees * fee_amount

    total_fees_by_payment_type = {
        pt: fee for pt in valid_payment_types if (fee := calculate_fee(pt)) > 0
    }
    total_fee = sum(total_fees_by_payment_type.values(), Decimal(0))

    if not total_fee > 0:
        return []

    fee_breakdown = ", ".join(
        [f"{pt} {fee} {denomination}" for pt, fee in total_fees_by_payment_type.items()]
    )
    description = f"Total fees charged for limits on payment types: {fee_breakdown}"

    return [
        CustomInstruction(
            postings=posting_utils.create_postings(
                amount=total_fee,
                debit_account=state.vault.account_id,
                credit_account=income_account,
                denomination=denomination,
            ),
            value_datetime=state.effective_datetime,
            instruction_details=posting_utils.standard_instruction_details(
                description=description,
                event_type=APPLICATION_EVENT,
                gl_impacted=True,
                account_type=account_type,
            ),
            override_all_restrictions=True,
        )
    ]
