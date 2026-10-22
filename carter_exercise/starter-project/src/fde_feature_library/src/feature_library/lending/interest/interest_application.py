__smart_contract_feature__ = True

# standard-library
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal
from typing import NamedTuple

from dateutil.relativedelta import relativedelta

# feature-library
import feature_library.common.accrual_utils as accrual_utils
import feature_library.common.application_precision as application_precision_module
import feature_library.common.balance_utils as balance_utils
import feature_library.common.denomination as denomination_module
import feature_library.common.state_utils as state_utils
import feature_library.common.utils as utils
import feature_library.lending.addresses as lending_addresses
import feature_library.lending.interest.interest_accrual as interest_accrual
import feature_library.lending.interfaces as lending_interfaces

# Contracts-API
from contracts_api import (
    DEFAULT_ADDRESS,
    DEFAULT_ASSET,
    BalanceCoordinate,
    BalanceDefaultDict,
    BalancesFilter,
    BalancesObservationFetcher,
    DefinedDateTime,
    ExpectedParameter,
    ParametersFilter,
    ParametersObservationFetcher,
    Phase,
    Posting,
    RelativeDateTime,
    Shift,
)

# Parameters
INTEREST_RECEIVED_ACCOUNT_PARAM_ID = "&{interest_received_account}"
INTEREST_RECEIVED_ACCOUNT_PARAM = ExpectedParameter(
    id=INTEREST_RECEIVED_ACCOUNT_PARAM_ID,
    triggers_pre_parameter_change_hook=False,
    triggers_post_parameter_change_hook=False,
)

expected_parameters = [
    INTEREST_RECEIVED_ACCOUNT_PARAM,
    application_precision_module.APPLICATION_PRECISION_PARAM,
    denomination_module.DENOMINATION_PARAM,
]

# Parameter Fetchers
INTEREST_APPLICATION_PARAMS_ET_POF_ID = "interest_application_params_et_pof"
INTEREST_APPLICATION_PARAMS_ET_POF = ParametersObservationFetcher(
    fetcher_id=INTEREST_APPLICATION_PARAMS_ET_POF_ID,
    at=DefinedDateTime.EFFECTIVE_DATETIME,
    filter=ParametersFilter(parameter_ids=[p.id for p in expected_parameters]),
)

# Balance Fetchers
ACCRUED_INTEREST_ET_BOF_ID = "accrued_interest_effective_datetime_bof"
ACCRUED_INTEREST_ET_BOF = BalancesObservationFetcher(
    fetcher_id=ACCRUED_INTEREST_ET_BOF_ID,
    at=DefinedDateTime.EFFECTIVE_DATETIME,
    filter=BalancesFilter(addresses=[lending_addresses.ACCRUED_INTEREST_RECEIVABLE]),
)

# TODO how can non-eia interest calculation be improved to support timezone changes
ACCRUED_INTEREST_ONE_MONTH_AGO_BOF_ID = "accrued_interest_one_month_ago_bof"
ACCRUED_INTEREST_ONE_MONTH_AGO_BOF = BalancesObservationFetcher(
    fetcher_id=ACCRUED_INTEREST_ONE_MONTH_AGO_BOF_ID,
    at=RelativeDateTime(origin=DefinedDateTime.EFFECTIVE_DATETIME, shift=Shift(months=-1)),
    filter=BalancesFilter(addresses=[lending_addresses.ACCRUED_INTEREST_RECEIVABLE]),
)

data_fetchers = [
    INTEREST_APPLICATION_PARAMS_ET_POF,
    ACCRUED_INTEREST_ET_BOF,
    ACCRUED_INTEREST_ONE_MONTH_AGO_BOF,
]

# Config
InterestApplicationFetchersConfig = NamedTuple(
    "InterestApplicationFetchersConfig",
    [
        ("accrued_bal_fetcher_id", str),
        ("accrued_one_month_ago_bal_fetcher_id", str),
        ("param_fetcher_id", str),
        ("denomination_param_id", str),
        ("application_precision_param_id", str),
        ("interest_received_account_param_id", str),
        ("accrued_receivable_account_param_id", str),
        ("accrual_address", str),
        ("application_address", str),
    ],
)

DEFAULT_FETCHERS_CONFIG = InterestApplicationFetchersConfig(
    accrued_bal_fetcher_id=ACCRUED_INTEREST_ET_BOF_ID,
    accrued_one_month_ago_bal_fetcher_id=ACCRUED_INTEREST_ONE_MONTH_AGO_BOF_ID,
    param_fetcher_id=INTEREST_APPLICATION_PARAMS_ET_POF_ID,
    denomination_param_id=denomination_module.DENOMINATION_PARAM_ID,
    application_precision_param_id=application_precision_module.APPLICATION_PRECISION_PARAM_ID,
    interest_received_account_param_id=INTEREST_RECEIVED_ACCOUNT_PARAM_ID,
    accrued_receivable_account_param_id=interest_accrual.ACCRUED_INTEREST_RECEIVABLE_ACCOUNT_PARAM_ID,
    accrual_address=lending_addresses.ACCRUED_INTEREST_RECEIVABLE,
    application_address=lending_addresses.INTEREST_DUE,
)


def _append_to_state(
    state: state_utils.SmartContractState,
    fetchers_config: InterestApplicationFetchersConfig = DEFAULT_FETCHERS_CONFIG,
) -> state_utils.SmartContractState:
    """Append interest application parameters and balances to the smart contract state.

    Args:
        state (SmartContractState): The current smart contract state.
        fetchers_config (InterestApplicationFetchersConfig, optional): Configuration for the
            parameter and balance fetchers. Defaults to DEFAULT_FETCHERS_CONFIG.

    Returns:
        SmartContractState: The updated smart contract state.
    """
    # 1. Fetch feature-specific parameters if needed
    parameters = state.vault.get_parameters_observation(
        fetcher_id=fetchers_config.param_fetcher_id
    ).parameters

    # 2. Fetch balances
    balances = state.vault.get_balances_observation(
        fetcher_id=fetchers_config.accrued_bal_fetcher_id
    ).balances

    state = state_utils.append_to_state(state=state, parameters=parameters, balances=balances)

    return state


def apply_interest(
    *,
    state: state_utils.SmartContractState,
    previous_application_datetime: datetime,
    fetchers_config: InterestApplicationFetchersConfig = DEFAULT_FETCHERS_CONFIG,
) -> list[Posting]:
    """Creates postings to apply accrued interest.

    This handles the transfer of money from internal accrual accounts to the customer account
    at a specific address (e.g. lending_addresses.INTEREST_DUE).

    Args:
        state (state_utils.SmartContractState): Smart Contract State
        previous_application_datetime (datetime): The previous datetime of interest application
        fetchers_config (InterestApplicationFetchersConfig, optional): Fetchers configuration.
            Defaults to DEFAULT_FETCHERS_CONFIG.

    Returns:
        list[Posting]: List of postings for interest application
    """
    state = _append_to_state(state=state, fetchers_config=fetchers_config)

    rejection = state_utils.check_parameters_exist(
        state=state,
        param_ids={
            fetchers_config.denomination_param_id,
            fetchers_config.application_precision_param_id,
            fetchers_config.interest_received_account_param_id,
            fetchers_config.accrued_receivable_account_param_id,
        },
    )
    assert rejection is None, rejection

    params = state.parameters
    denomination: str = params[fetchers_config.denomination_param_id]  # type: ignore
    application_precision: int = int(params[fetchers_config.application_precision_param_id])  # type: ignore
    application_internal_account: str = params[fetchers_config.interest_received_account_param_id]  # type: ignore
    accrual_internal_account: str = params[fetchers_config.accrued_receivable_account_param_id]  # type: ignore

    # Fetchers for one month ago
    one_month_ago_observation = state.vault.get_balances_observation(
        fetcher_id=fetchers_config.accrued_one_month_ago_bal_fetcher_id
    )

    interest_application_amounts = _get_interest_to_apply(
        balances_at_application=state.balances,
        balances_one_repayment_period_ago=one_month_ago_observation.balances,
        denomination=denomination,
        application_precision=application_precision,
        effective_datetime=state.effective_datetime,
        previous_application_datetime=previous_application_datetime,
        accrual_address=fetchers_config.accrual_address,
    )

    return accrual_utils.create_receivable_accrual_application_postings(
        customer_account=state.vault.account_id,
        denomination=denomination,
        application_amount=interest_application_amounts.total_rounded,
        accrual_amount=interest_application_amounts.eia_accrued
        + interest_application_amounts.non_eia_accrued,
        accrual_customer_address=fetchers_config.accrual_address,
        accrual_internal_account=accrual_internal_account,
        application_customer_address=fetchers_config.application_address,
        application_internal_account=application_internal_account,
    )


def _interest_amounts(
    balances: BalanceDefaultDict,
    denomination: str,
    accrual_address: str,
    precision: int = 2,
    rounding: str = ROUND_HALF_UP,
) -> tuple[Decimal, Decimal]:
    """Determine the amount of interest in balances, un-rounded and rounded.

    Args:
        balances (BalanceDefaultDict): Balances for the account that interest is being applied on.
        denomination (str): Denomination of the accrued interest to apply.
        accrual_address (str): The account address where interest is accrued.
        precision (int, optional): The number of decimal places to round to. Defaults to 2.
        rounding (str, optional): The Decimal rounding strategy to use. Defaults to ROUND_HALF_UP.

    Returns:
        tuple[Decimal, Decimal]: The un-rounded and rounded amounts.
    """

    accrued_amount = balance_utils.net_debit(
        balances[
            BalanceCoordinate(
                account_address=accrual_address,
                asset=DEFAULT_ASSET,
                denomination=denomination,
                phase=Phase.COMMITTED,
            )
        ]
    )

    return accrued_amount, utils.round_decimal(
        accrued_amount, decimal_places=precision, rounding=rounding
    )


def _get_interest_to_apply(
    *,
    balances_at_application: BalanceDefaultDict,
    balances_one_repayment_period_ago: BalanceDefaultDict,
    denomination: str,
    application_precision: int,
    effective_datetime: datetime,
    previous_application_datetime: datetime,
    accrual_address: str,
) -> lending_interfaces.InterestAmounts:
    """Calculate the interest amounts to apply, considering EIA and non-EIA components.

    Args:
        balances_at_application (BalanceDefaultDict): Balances at the time of interest application.
        balances_one_repayment_period_ago (BalanceDefaultDict): Balances one repayment period ago.
        denomination (str): The currency denomination.
        application_precision (int): The precision to use for rounding applied interest.
        effective_datetime (datetime): The current effective datetime.
        previous_application_datetime (datetime): The datetime of the previous interest application.
        accrual_address (str): The account address where interest is accrued.

    Returns:
        InterestAmounts: A NamedTuple containing the calculated interest components.
    """

    effective_unrounded, effective_rounded = _interest_amounts(
        balances=balances_at_application,
        denomination=denomination,
        precision=application_precision,
        accrual_address=accrual_address,
    )

    # Assuming monthly due amount calculation, Non-EIA interest is usually == accrued interest
    # one month ago. This doesn't hold when the previous application was less than a month ago,
    # as it would have already dealt with the accrued interest from one month ago. Instead we
    # assume the non-eia interest is zero. This scenario can occur due to a due amount calculation
    # day change:
    # - due amount calculation on 2023/02/04
    # - change of due amount calculation day from 4 to 2 on 2023/02/05
    # - next due amount calculation on 2023/03/02, which is less than one month after 2023/02/04

    # The logic cannot be extended to when the previous application was exactly a month ago, as this
    # application may have been during a repayment holiday where accrued interest was not actually
    # applied. This interest should be treated as non-EIA after the holiday ends. This is a
    # limitation of relying on last_execution_datetime to determine previous application dates, as
    # it records execution of the schedule and not its outcomes. For example:
    # - accrued interest is 1.25 on due amount calculation day falling on 2023/02/04, but interest
    # is not applied due to a repayment holiday
    # - accrued interest is still 1.25 on the next due amount calculation on 2023/03/04, which is
    # one month after the previous date
    # - the expected non-eia interest is 1.25, as it was legitimately accrued before the last time
    # interest was applied.
    # Due amount calculation day changes should be blocked during repayment holidays to avoid the
    # two scenarios from stacking.

    if effective_datetime - relativedelta(months=1) < previous_application_datetime:
        one_period_ago_unrounded, one_period_ago_rounded = Decimal(0), Decimal(0)
    else:
        one_period_ago_unrounded, one_period_ago_rounded = _interest_amounts(
            balances=balances_one_repayment_period_ago,
            denomination=denomination,
            precision=application_precision,
            accrual_address=accrual_address,
        )

    return lending_interfaces.InterestAmounts(
        eia_accrued=effective_unrounded - one_period_ago_unrounded,
        eia_rounded_accrued=effective_rounded - one_period_ago_rounded,
        non_eia_accrued=one_period_ago_unrounded,
        non_eia_rounded_accrued=one_period_ago_rounded,
        total_rounded=effective_rounded,
    )


def get_interest_to_apply(
    *,
    state: state_utils.SmartContractState,
    previous_application_datetime: datetime,
    fetchers_config: InterestApplicationFetchersConfig = DEFAULT_FETCHERS_CONFIG,
) -> lending_interfaces.InterestAmounts:
    """Determine interest amounts for application, handling EIA/non-EIA considerations.

    See InterestAmounts documentation for more details.

    Args:
        state (SmartContractState): Smart Contract State
        previous_application_datetime (datetime): the previous datetime of interest application
        fetchers_config (InterestApplicationFetchersConfig, optional): Fetchers configuration.
            Defaults to DEFAULT_FETCHERS_CONFIG.

    Returns:
        InterestAmounts: the interest amounts
    """

    state = _append_to_state(state=state, fetchers_config=fetchers_config)

    rejection = state_utils.check_parameters_exist(
        state=state,
        param_ids={
            fetchers_config.denomination_param_id,
            fetchers_config.application_precision_param_id,
        },
    )
    assert rejection is None, rejection

    denomination: str = state.parameters[fetchers_config.denomination_param_id]  # type: ignore
    application_precision: int = int(
        state.parameters[fetchers_config.application_precision_param_id]  # type: ignore
    )

    # Fetchers for one month ago
    one_month_ago_observation = state.vault.get_balances_observation(
        fetcher_id=fetchers_config.accrued_one_month_ago_bal_fetcher_id
    )

    return _get_interest_to_apply(
        balances_at_application=state.balances,
        balances_one_repayment_period_ago=one_month_ago_observation.balances,
        denomination=denomination,
        application_precision=application_precision,
        effective_datetime=state.effective_datetime,
        previous_application_datetime=previous_application_datetime,
        accrual_address=fetchers_config.accrual_address,
    )


def repay_accrued_interest(
    *,
    state: state_utils.SmartContractState,
    repayment_amount: Decimal,
    application_customer_address: str = DEFAULT_ADDRESS,
    fetchers_config: InterestApplicationFetchersConfig = DEFAULT_FETCHERS_CONFIG,
) -> list[Posting]:
    """Creates postings to repay accrued interest.

    This is typically for overpayment scenarios. In order to recognise interest income,
    repaying accrued interest is modelled as interest application + immediate repayment.

    Args:
        state (SmartContractState): Smart Contract State
        repayment_amount (Decimal): the repayment amount that can be allocated to accrued interest
        application_customer_address (str, optional): the address to use on the customer account
            for interest application. Applying to the DEFAULT_ADDRESS will rebalance the
            repayment that credits DEFAULT_ADDRESS, which makes this equivalent to applying the
            interest and repaying the applied interest. Defaults to DEFAULT_ADDRESS.
        fetchers_config (InterestApplicationFetchersConfig, optional): Fetchers configuration.
            Defaults to DEFAULT_FETCHERS_CONFIG.

    Returns:
        list[Posting]: the custom instructions for repaying accrued interest.
            Empty list if no repayment is possible (e.g. repayment amount is insufficient,
            or no accrued interest to repay)
    """

    if repayment_amount <= 0:
        return []

    state = _append_to_state(state=state, fetchers_config=fetchers_config)

    rejection = state_utils.check_parameters_exist(
        state=state,
        param_ids={
            fetchers_config.denomination_param_id,
            fetchers_config.application_precision_param_id,
            fetchers_config.interest_received_account_param_id,
            fetchers_config.accrued_receivable_account_param_id,
        },
    )
    assert rejection is None, rejection

    params = state.parameters
    denomination: str = params[fetchers_config.denomination_param_id]  # type: ignore
    application_precision: int = int(params[fetchers_config.application_precision_param_id])  # type: ignore
    application_internal_account: str = params[fetchers_config.interest_received_account_param_id]  # type: ignore
    accrual_internal_account: str = params[fetchers_config.accrued_receivable_account_param_id]  # type: ignore

    accrued_amount, rounded_accrued_amount = _interest_amounts(
        balances=state.balances,
        denomination=denomination,
        precision=application_precision,
        accrual_address=fetchers_config.accrual_address,
    )

    if rounded_accrued_amount <= repayment_amount:
        application_amount = rounded_accrued_amount
        accrual_amount = accrued_amount
    else:
        # e.g. repaying 10.12 when accrued interest is 11.145 should apply 10.12, with
        # 1.025 accrued interest remaining
        application_amount = repayment_amount
        accrual_amount = repayment_amount

    return accrual_utils.create_receivable_accrual_application_postings(
        customer_account=state.vault.account_id,
        denomination=denomination,
        application_amount=application_amount,
        accrual_amount=accrual_amount,
        accrual_customer_address=fetchers_config.accrual_address,
        accrual_internal_account=accrual_internal_account,
        application_customer_address=application_customer_address,
        application_internal_account=application_internal_account,
    )


InterestApplication = lending_interfaces.InterestApplication(
    apply_interest=apply_interest,
    get_interest_to_apply=get_interest_to_apply,
)
