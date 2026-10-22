# Copyright @ 2023 - 2026 Thought Machine Group Limited. All rights reserved.
__smart_contract_feature__ = True

# standard libs
from datetime import datetime
from decimal import Decimal
from typing import NamedTuple

from dateutil.relativedelta import relativedelta

# features
import feature_library.common.denomination as denomination_module
import feature_library.common.fetchers as fetchers
import feature_library.common.posting_utils as posting_utils
import feature_library.common.state_utils as state_utils

# contracts api
from contracts_api import (
    DEFAULT_ASSET,
    Balance,
    BalanceCoordinate,
    CustomInstruction,
    DefinedDateTime,
    ExpectedParameter,
    ParametersFilter,
    ParametersObservationFetcher,
    Phase,
    Posting,
    Rejection,
)

# inception sdk
from inception_sdk.vault.contracts.extensions.contracts_api_extensions import SmartContractVault

# Balance addresses
EARLY_CLOSURE_FEE_ADDRESS = "EARLY_CLOSURE_FEE"


# Parameters
EARLY_CLOSURE_FEE_PARAM_ID = "&{early_closure_fee}"
EARLY_CLOSURE_FEE_PARAM = ExpectedParameter(
    id=EARLY_CLOSURE_FEE_PARAM_ID,
    triggers_pre_parameter_change_hook=False,
    triggers_post_parameter_change_hook=False,
)

EARLY_CLOSURE_DAYS_PARAM_ID = "&{early_closure_days}"
EARLY_CLOSURE_DAYS_PARAM = ExpectedParameter(
    id=EARLY_CLOSURE_DAYS_PARAM_ID,
    triggers_pre_parameter_change_hook=False,
    triggers_post_parameter_change_hook=False,
)

EARLY_CLOSURE_FEE_INCOME_ACCOUNT_PARAM_ID = "&{early_closure_fee_income_account}"
EARLY_CLOSURE_FEE_INCOME_ACCOUNT_PARAM = ExpectedParameter(
    id=EARLY_CLOSURE_FEE_INCOME_ACCOUNT_PARAM_ID,
    triggers_pre_parameter_change_hook=False,
    triggers_post_parameter_change_hook=False,
)

expected_parameters = [
    EARLY_CLOSURE_FEE_PARAM,
    EARLY_CLOSURE_DAYS_PARAM,
    EARLY_CLOSURE_FEE_INCOME_ACCOUNT_PARAM,
    denomination_module.DENOMINATION_PARAM,
]

# Fetchers
EARLY_CLOSURE_FEES_POF_ID = "early_closure_fees_pof"
EARLY_CLOSURE_FEES_POF = ParametersObservationFetcher(
    fetcher_id=EARLY_CLOSURE_FEES_POF_ID,
    at=DefinedDateTime.EFFECTIVE_DATETIME,
    filter=ParametersFilter(parameter_ids=[p.id for p in expected_parameters]),
)

data_fetchers = [
    fetchers.ALL_BALANCES_ET_BOF,
    EARLY_CLOSURE_FEES_POF,
]

EarlyClosureFeesFetchersConfig = NamedTuple(
    "EarlyClosureFeesFetchersConfig",
    [
        ("balance_fetcher_id", str),
        ("param_fetcher_id", str),
        ("denomination_param_id", str),
    ],
)
DEFAULT_EARLY_CLOSURE_FEES_FETCHERS_CONFIG = EarlyClosureFeesFetchersConfig(
    balance_fetcher_id=fetchers.ALL_BALANCES_ET_BOF.fetcher_id,
    param_fetcher_id=EARLY_CLOSURE_FEES_POF.fetcher_id,
    denomination_param_id=denomination_module.DENOMINATION_PARAM.id,
)

ApplyFeesResult = NamedTuple(
    "ApplyFeesResult",
    [
        ("custom_instructions", list[CustomInstruction]),
        ("rejection", Rejection | None),
    ],
)


def get_parameters(
    vault: SmartContractVault, param_fetcher_id: str = EARLY_CLOSURE_FEES_POF_ID
) -> dict[str, datetime | Decimal | str | None]:
    """Retrieves configuration parameters for the early closure fee feature.

    Args:
        vault: The SmartContractVault instance to query.
        param_fetcher_id: The unique identifier for the parameter fetcher.
            Defaults to `EARLY_CLOSURE_FEES_POF_ID`.

    Returns:
        Parameters for the early closure fee feature.
        (datetime, Decimal, string, or None).
    """
    return vault.get_parameters_observation(fetcher_id=param_fetcher_id).parameters


def _append_to_state(
    state: state_utils.SmartContractState,
    balance_fetcher_id: str = fetchers.ALL_BALANCES_ET_BOF.fetcher_id,
    param_fetcher_id: str = EARLY_CLOSURE_FEES_POF.fetcher_id,
) -> state_utils.SmartContractState:
    """Extends the Smart Contract state with vault parameters and balance observations.

    This helper function fetches parameter data and balances from the vault
    associated with the current state and merges them into a new state object.

    Args:
        state (SmartContractState): The current state object containing the vault reference.
        balance_fetcher_id (str): The ID of the fetcher used to observe balances.
            Defaults to ALL_BALANCES_ET_BOF.
        param_fetcher_id (str): The ID of the fetcher used to observe parameters.
            Defaults to EARLY_CLOSURE_FEES_POF_ID.

    Returns:
        SmartContractState: A new state object updated with the fetched parameters
            and balances.
    """
    return state_utils.append_to_state(
        state=state,
        parameters=get_parameters(state.vault, param_fetcher_id),
        balances=state.vault.get_balances_observation(fetcher_id=balance_fetcher_id).balances,
    )


def apply_fees(
    state: state_utils.SmartContractState,
    account_type: str,
    early_closure_fee_address: str = EARLY_CLOSURE_FEE_ADDRESS,
    fetchers_config: EarlyClosureFeesFetchersConfig = DEFAULT_EARLY_CLOSURE_FEES_FETCHERS_CONFIG,
) -> ApplyFeesResult:
    """Applies the early closure fee if account is closed within 'early_closure_days' number of days
    (midnight inclusive) and if the fee hasn't been applied already.

    :param state: The SmartContractState containing the vault, parameters, and balances.
    :param account_type: The account type to be noted in the custom instruction detail.
    :param early_closure_fee_address: The address used to track if fee was applied.
    :param fetchers_config: The balances and parameters fetchers configuration.
    :return: Returns the Custom Instruction for charging the fee and tracking the fee.
    """

    state = _append_to_state(state)
    if rejection := state_utils.check_parameters_exist(
        state, {fetchers_config.denomination_param_id}
    ):
        return ApplyFeesResult(custom_instructions=[], rejection=rejection)

    denomination: str = state.parameters[fetchers_config.denomination_param_id]  # type: ignore
    creation_datetime: datetime = state.vault.get_account_activation_datetime()
    early_closure_fee = Decimal(state.parameters[EARLY_CLOSURE_FEE_PARAM_ID])  # type: ignore
    early_closure_days = int(state.parameters[EARLY_CLOSURE_DAYS_PARAM_ID])  # type: ignore
    early_closure_fee_income_account: str = str(
        state.parameters[EARLY_CLOSURE_FEE_INCOME_ACCOUNT_PARAM_ID]
    )

    if early_closure_fee <= 0:
        return ApplyFeesResult(
            custom_instructions=[],
            rejection=None,
        )

    early_closure_cut_off_datetime = creation_datetime + relativedelta(days=early_closure_days)

    # Check if early closure fee was not charged before.
    # Since this fee's tracker postings zero out the tracker address (i.e. net zero) so the
    # close code hook does not leave any non-zero custom balance definitions, we cannot
    # check for net != 0. Instead, we check the debit.
    early_closure_fee_coord = BalanceCoordinate(
        account_address=early_closure_fee_address,
        asset=DEFAULT_ASSET,
        denomination=denomination,
        phase=Phase.COMMITTED,
    )
    early_closure_fees_charge_tracker: Balance = state.balances[early_closure_fee_coord]

    if (
        # If an early fee has already been charged or it is after the early closure cutoff,
        # then do not charge a fee.
        early_closure_fees_charge_tracker.debit > 0
        or state.effective_datetime > early_closure_cut_off_datetime
    ):
        return ApplyFeesResult(
            custom_instructions=[],
            rejection=None,
        )

    fee_postings = posting_utils.create_postings(
        amount=early_closure_fee,
        debit_account=state.vault.account_id,
        credit_account=early_closure_fee_income_account,
        denomination=denomination,
    )

    tracker_postings = _update_closure_fee_tracker(
        denomination=denomination,
        account_id=state.vault.account_id,
        account_tracker_address=early_closure_fee_address,
    )

    postings = fee_postings + tracker_postings
    if postings:
        instructions = [
            CustomInstruction(
                postings=postings,
                value_datetime=state.effective_datetime,
                instruction_details=posting_utils.standard_instruction_details(
                    description="EARLY CLOSURE FEE",
                    event_type="CLOSE_ACCOUNT",
                    gl_impacted=True,
                    account_type=account_type,
                ),
                override_all_restrictions=True,
            )
        ]

        return ApplyFeesResult(custom_instructions=instructions, rejection=None)

    return ApplyFeesResult(
        custom_instructions=[],
        rejection=None,
    )


def _update_closure_fee_tracker(
    denomination: str,
    account_id: str,
    account_tracker_address: str,
) -> list[Posting]:
    """Create postings to track early closure fee applied. Whereas other trackers
    normally make non-zero net postings, here the postings net zero so as to
    not leave custom balance definitions with non-zero balances since it is
    intended for use in the close code hook. Since the sole purpose is to track
    if a fee was applied, the amount can be hardcoded to 1.

    :param denomination: The denomination of this instruction.
    :param account_id: Account id.
    :param account_tracker_address: Address for tracking purposes.
    :return: Returns debit and credit entries for early closure fee tracking.
    """

    postings = posting_utils.create_postings(
        amount=Decimal(1),
        debit_account=account_id,
        debit_address=account_tracker_address,
        credit_account=account_id,
        credit_address=account_tracker_address,
        denomination=denomination,
    )

    return postings
