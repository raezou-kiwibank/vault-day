__smart_contract_feature__ = True

# standard libs
from datetime import datetime
from decimal import Decimal
from typing import NamedTuple

from dateutil.relativedelta import relativedelta

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
    Rejection,
    RejectionReason,
    RelativeDateTime,
    Shift,
)

# inception sdk
from inception_sdk.vault.contracts.extensions.contracts_api_extensions import SmartContractVault

# instruction detail key
INSTRUCTION_DETAIL_KEY = "TRANSACTION_TYPE"

# Parameters
EXCESS_FEE_PARAM_ID = "&{excess_fee}"
EXCESS_FEE_PARAM = ExpectedParameter(
    id=EXCESS_FEE_PARAM_ID,
    optional=True,
    triggers_pre_parameter_change_hook=False,
    triggers_post_parameter_change_hook=False,
)

PERMITTED_WITHDRAWALS_PARAM_ID = "&{permitted_withdrawals}"
PERMITTED_WITHDRAWALS_PARAM = ExpectedParameter(
    id=PERMITTED_WITHDRAWALS_PARAM_ID,
    optional=True,
    triggers_pre_parameter_change_hook=False,
    triggers_post_parameter_change_hook=False,
)

EXCESS_FEE_MONITORED_TRANSACTION_TYPE_PARAM_ID = "&{excess_fee_monitored_transaction_type}"
EXCESS_FEE_MONITORED_TRANSACTION_TYPE_PARAM = ExpectedParameter(
    id=EXCESS_FEE_MONITORED_TRANSACTION_TYPE_PARAM_ID,
    optional=True,
    triggers_pre_parameter_change_hook=False,
    triggers_post_parameter_change_hook=False,
)

EXCESS_FEE_INCOME_ACCOUNT_PARAM_ID = "&{excess_fee_income_account}"
EXCESS_FEE_INCOME_ACCOUNT_PARAM = ExpectedParameter(
    id=EXCESS_FEE_INCOME_ACCOUNT_PARAM_ID,
    triggers_pre_parameter_change_hook=False,
    triggers_post_parameter_change_hook=False,
)

BLOCK_EXCESS_WITHDRAWALS_PARAM_ID = "&{block_excess_withdrawals}"
BLOCK_EXCESS_WITHDRAWALS_PARAM = ExpectedParameter(
    id=BLOCK_EXCESS_WITHDRAWALS_PARAM_ID,
    optional=True,
    triggers_pre_parameter_change_hook=False,
    triggers_post_parameter_change_hook=False,
)

expected_parameters = [
    EXCESS_FEE_PARAM,
    PERMITTED_WITHDRAWALS_PARAM,
    EXCESS_FEE_MONITORED_TRANSACTION_TYPE_PARAM,
    EXCESS_FEE_INCOME_ACCOUNT_PARAM,
    BLOCK_EXCESS_WITHDRAWALS_PARAM,
    denomination_module.DENOMINATION_PARAM,
]

# Fetchers
EXCESS_FEE_PARAMS_ET_POF_ID = "excess_fee_params_et_pof"
EXCESS_FEE_PARAMS_ET_POF = ParametersObservationFetcher(
    fetcher_id=EXCESS_FEE_PARAMS_ET_POF_ID,
    at=DefinedDateTime.EFFECTIVE_DATETIME,
    filter=ParametersFilter(parameter_ids=[p.id for p in expected_parameters]),
)

# Month to effective postings fetcher
EXCESS_FEE_POSTIF_ID = "excess_fee_postif"
EXCESS_FEE_POSTIF = PostingsIntervalFetcher(
    fetcher_id=EXCESS_FEE_POSTIF_ID,
    start=RelativeDateTime(origin=DefinedDateTime.EFFECTIVE_DATETIME, shift=Shift(months=-1)),
    end=DefinedDateTime.EFFECTIVE_DATETIME,
)

data_fetchers = [EXCESS_FEE_PARAMS_ET_POF, EXCESS_FEE_POSTIF]

ExcessFeeFetchersConfig = NamedTuple(
    "ExcessFeeFetchersConfig",
    [
        ("param_fetcher_id", str),
        ("postif_id", str),
        ("denomination_param_id", str),
    ],
)

DEFAULT_EXCESS_FEE_FETCHERS_CONFIG = ExcessFeeFetchersConfig(
    param_fetcher_id=EXCESS_FEE_PARAMS_ET_POF_ID,
    postif_id=EXCESS_FEE_POSTIF_ID,
    denomination_param_id=denomination_module.DENOMINATION_PARAM.id,
)

WithdrawalCounts = NamedTuple(
    "WithdrawalCounts",
    [
        ("current_withdrawals", int),
        ("proposed_withdrawals", int),
        ("permitted_withdrawals", int),
    ],
)


def get_parameters(
    vault: SmartContractVault, fetcher_id: str = EXCESS_FEE_PARAMS_ET_POF_ID
) -> dict[str, datetime | Decimal | str | None]:
    """Retrieves configuration parameters for the excess withdrawal fee feature.

    Args:
        vault: The vault object to retrieve parameters from.
        fetcher_id: The ID of the fetcher used to retrieve parameters.

    Returns:
        A dictionary mapping parameter IDs to their values.
    """
    return vault.get_parameters_observation(fetcher_id=fetcher_id).parameters


def _append_to_state(
    state: state_utils.SmartContractState,
    fetchers_config: ExcessFeeFetchersConfig,
) -> state_utils.SmartContractState:
    """Updates the contract state with the excess withdrawal fee parameters.

    Args:
        state: The current state of the smart contract.
        fetchers_config: Configuration for the fetchers used.

    Returns:
        The updated state object.
    """
    parameters = get_parameters(state.vault, fetchers_config.param_fetcher_id)

    state = state_utils.append_to_state(
        state=state,
        parameters=parameters,
    )

    return state


def validate(
    state: state_utils.SmartContractState,
    proposed_client_transactions: dict[str, ClientTransaction],
    fetchers_config: ExcessFeeFetchersConfig = DEFAULT_EXCESS_FEE_FETCHERS_CONFIG,
) -> Rejection | None:
    """Checks the number of relevant withdrawals in the current month and rejects if the
    limit has been exceeded and blocking is enabled.

    Args:
        state: The current state of the smart contract.
        proposed_client_transactions: New or updated client transactions to validate.
        fetchers_config: Configuration for the fetchers used.

    Returns:
        A rejection if the withdrawal limit is exceeded and blocking is enabled, else None.
    """
    state = _append_to_state(state, fetchers_config)

    rejection = state_utils.check_parameters_exist(state, {fetchers_config.denomination_param_id})
    assert rejection is None, rejection

    block_excess_withdrawals: bool = (
        str(state.parameters.get(BLOCK_EXCESS_WITHDRAWALS_PARAM_ID, "False")).upper() == "TRUE"
    )

    if not block_excess_withdrawals:
        return None

    withdrawal_counts: WithdrawalCounts | None = _fetch_withdrawal_counts(
        state=state,
        proposed_client_transactions=proposed_client_transactions,
        fetchers_config=fetchers_config,
    )
    if not withdrawal_counts:
        return None

    if (
        withdrawal_counts.current_withdrawals + withdrawal_counts.proposed_withdrawals
        > withdrawal_counts.permitted_withdrawals
    ):
        return Rejection(
            message=f"Transactions would cause the maximum monthly withdrawal limit of "
            f"{withdrawal_counts.permitted_withdrawals} to be exceeded.",
            reason_code=RejectionReason.AGAINST_TNC,
        )

    return None


def handle_withdrawals(
    state: state_utils.SmartContractState,
    proposed_client_transactions: dict[str, ClientTransaction],
    fetchers_config: ExcessFeeFetchersConfig = DEFAULT_EXCESS_FEE_FETCHERS_CONFIG,
    account_type: str = "",
) -> list[CustomInstruction]:
    """Checks the number of relevant withdrawals in the current month and returns fee instructions
    if the limit has been exceeded.

    Args:
        state: The current state of the smart contract.
        proposed_client_transactions: New or updated client transactions to process.
        fetchers_config: Configuration for the fetchers used.
        account_type: The account type to be noted in the custom instruction details.

    Returns:
        A list of CustomInstructions for charging any applicable excess fees.
    """
    state = _append_to_state(state, fetchers_config)

    rejection = state_utils.check_parameters_exist(state, {fetchers_config.denomination_param_id})
    assert rejection is None, rejection

    excess_fee_amount = Decimal(state.parameters.get(EXCESS_FEE_PARAM_ID, 0) or 0)  # type: ignore

    if excess_fee_amount <= Decimal(0):
        return []

    withdrawal_counts: WithdrawalCounts | None = _fetch_withdrawal_counts(
        state=state,
        proposed_client_transactions=proposed_client_transactions,
        fetchers_config=fetchers_config,
    )
    if not withdrawal_counts:
        return []

    if withdrawal_counts.permitted_withdrawals < 0:
        return []

    # If withdrawals already exceeded then charge fee for every new withdrawal.
    proposed_exceeding_withdrawals = (
        withdrawal_counts.proposed_withdrawals
        if withdrawal_counts.current_withdrawals > withdrawal_counts.permitted_withdrawals
        else (
            withdrawal_counts.proposed_withdrawals
            + withdrawal_counts.current_withdrawals
            - withdrawal_counts.permitted_withdrawals
        )
    )

    if proposed_exceeding_withdrawals <= 0:
        return []

    excess_fee_income_account = str(state.parameters[EXCESS_FEE_INCOME_ACCOUNT_PARAM_ID])
    denomination = str(state.parameters[fetchers_config.denomination_param_id])

    return [
        CustomInstruction(
            postings=posting_utils.create_postings(
                amount=excess_fee_amount * proposed_exceeding_withdrawals,
                debit_account=state.vault.account_id,
                credit_account=excess_fee_income_account,
                denomination=denomination,
            ),
            value_datetime=state.effective_datetime,
            instruction_details=posting_utils.standard_instruction_details(
                description="Proposed withdrawals exceeded permitted "
                f"limit by {proposed_exceeding_withdrawals}",
                event_type="APPLY_EXCESS_FEES",
                gl_impacted=True,
                account_type=account_type,
            ),
        )
    ]


def _fetch_withdrawal_counts(
    state: state_utils.SmartContractState,
    proposed_client_transactions: dict[str, ClientTransaction],
    fetchers_config: ExcessFeeFetchersConfig,
) -> WithdrawalCounts | None:
    """Fetches the number of current and proposed withdrawals of the monitored transaction type.

    Args:
        state: The current state of the smart contract.
        proposed_client_transactions: New or updated client transactions.
        fetchers_config: Configuration for the fetchers used.

    Returns:
        WithdrawalCounts containing current, proposed, and permitted withdrawal numbers,
         or None if no monitored transaction type is configured.
    """
    transaction_type: str = str(
        state.parameters.get(EXCESS_FEE_MONITORED_TRANSACTION_TYPE_PARAM_ID, "") or ""
    )
    if not transaction_type:
        return None

    monthly_client_transactions = state.vault.get_client_transactions(
        fetcher_id=fetchers_config.postif_id
    )

    denomination = str(state.parameters[fetchers_config.denomination_param_id])

    historic_postings, proposed_postings = (
        client_transaction_utils.extract_interval_and_proposed_debits(
            denomination=denomination,
            proposed_transactions=proposed_client_transactions,
            interval_transactions=monthly_client_transactions,
            transaction_type_key=INSTRUCTION_DETAIL_KEY,
            transaction_types=[transaction_type],
            interval_start=state.effective_datetime
            + relativedelta(day=1, hour=0, minute=0, second=0, microsecond=0),
            effective_datetime=state.effective_datetime,
        )
    )

    current_withdrawals = len(historic_postings.get(transaction_type, {}))
    proposed_withdrawals = len(proposed_postings.get(transaction_type, {}))

    permitted_str = state.parameters.get(PERMITTED_WITHDRAWALS_PARAM_ID, "-1")
    permitted_withdrawals = int(permitted_str if permitted_str is not None else "-1")  # ty: ignore[invalid-argument-type]

    return WithdrawalCounts(
        current_withdrawals=current_withdrawals,
        proposed_withdrawals=proposed_withdrawals,
        permitted_withdrawals=permitted_withdrawals,
    )
