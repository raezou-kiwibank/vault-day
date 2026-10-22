__smart_contract_feature__ = True

# standard libs
from datetime import datetime
from decimal import Decimal
from typing import Mapping, NamedTuple

from dateutil.relativedelta import relativedelta

# feature library
import feature_library.common.accrual_utils as accruals
import feature_library.common.application_precision as application_precision
import feature_library.common.balance_utils as balance_utils
import feature_library.common.denomination as denomination_module
import feature_library.common.fetchers as fetchers
import feature_library.common.parameter_utils as parameter_utils
import feature_library.common.posting_utils as posting_utils
import feature_library.common.state_utils as state_utils
import feature_library.common.tuples as common_tuples
import feature_library.common.utils as common_utils
import feature_library.deposit.interest.interest_accrual as interest_accrual
import feature_library.deposit.interfaces as deposit_interfaces

# contracts api
from contracts_api import (
    DEFAULT_ADDRESS,
    DEFAULT_ASSET,
    Balance,
    BalanceCoordinate,
    BalanceDiscreteTimeseries,
    CustomInstruction,
    DefinedDateTime,
    ExpectedParameter,
    ParametersFilter,
    ParametersObservationFetcher,
    Phase,
)

# inception sdk
from inception_sdk.vault.contracts.extensions.contracts_api_extensions import SmartContractVault

# Addresses
OVERDRAFT_ACCRUED_INTEREST = "OVERDRAFT_ACCRUED_INTEREST"

# Events
OVERDRAFT_ACCRUAL_EVENT = "ACCRUE_OVERDRAFT_DAILY_FEE"
OVERDRAFT_APPLICATION_EVENT = "APPLY_OVERDRAFT_DAILY_FEE"

# Parameters
OVERDRAFT_INTEREST_RATE_PARAM_ID = "&{overdraft_interest_rate}"
OVERDRAFT_INTEREST_RATE_PARAM = ExpectedParameter(
    id=OVERDRAFT_INTEREST_RATE_PARAM_ID,
    triggers_pre_parameter_change_hook=False,
    triggers_post_parameter_change_hook=False,
)

OVERDRAFT_INTEREST_RECEIVABLE_ACCOUNT_PARAM_ID = "&{overdraft_interest_receivable_account}"
OVERDRAFT_INTEREST_RECEIVABLE_ACCOUNT_PARAM = ExpectedParameter(
    id=OVERDRAFT_INTEREST_RECEIVABLE_ACCOUNT_PARAM_ID,
    triggers_pre_parameter_change_hook=False,
    triggers_post_parameter_change_hook=False,
)

OVERDRAFT_INTEREST_RECEIVED_ACCOUNT_PARAM_ID = "&{overdraft_interest_received_account}"
OVERDRAFT_INTEREST_RECEIVED_ACCOUNT_PARAM = ExpectedParameter(
    id=OVERDRAFT_INTEREST_RECEIVED_ACCOUNT_PARAM_ID,
    triggers_pre_parameter_change_hook=False,
    triggers_post_parameter_change_hook=False,
)

INTEREST_FREE_BUFFER_DAYS_PARAM_ID = "&{interest_free_buffer_days}"
INTEREST_FREE_BUFFER_DAYS_PARAM = ExpectedParameter(
    id=INTEREST_FREE_BUFFER_DAYS_PARAM_ID,
    triggers_pre_parameter_change_hook=False,
    triggers_post_parameter_change_hook=False,
)

INTEREST_FREE_BUFFER_AMOUNT_PARAM_ID = "&{interest_free_buffer_amount}"
INTEREST_FREE_BUFFER_AMOUNT_PARAM = ExpectedParameter(
    id=INTEREST_FREE_BUFFER_AMOUNT_PARAM_ID,
    triggers_pre_parameter_change_hook=False,
    triggers_post_parameter_change_hook=False,
)

expected_parameters = [
    OVERDRAFT_INTEREST_RATE_PARAM,
    OVERDRAFT_INTEREST_RECEIVABLE_ACCOUNT_PARAM,
    OVERDRAFT_INTEREST_RECEIVED_ACCOUNT_PARAM,
    INTEREST_FREE_BUFFER_DAYS_PARAM,
    INTEREST_FREE_BUFFER_AMOUNT_PARAM,
]

OVERDRAFT_INTEREST_POF_ID = "overdraft_interest_pof"
OVERDRAFT_INTEREST_POF = ParametersObservationFetcher(
    fetcher_id=OVERDRAFT_INTEREST_POF_ID,
    at=DefinedDateTime.EFFECTIVE_DATETIME,
    filter=ParametersFilter(parameter_ids=[p.id for p in expected_parameters]),
)

data_fetchers = [
    fetchers.ALL_BALANCES_ET_BOF,
    OVERDRAFT_INTEREST_POF,
    fetchers.ONE_MONTH_EFFECTIVE_DATE_BDIF,
]


OverdraftInterestFetchersConfig = NamedTuple(
    "OverdraftInterestFetchersConfig",
    [
        ("param_fetcher_id", str),
        ("denomination_param_id", str),
        ("month_balances_fetcher_id", str),
        ("days_in_year_param_id", str),
        ("accrual_precision_param_id", str),
        ("application_precision_param_id", str),
        ("overdraft_interest_rate_param_id", str),
        ("overdraft_interest_receivable_account_param_id", str),
        ("overdraft_interest_received_account_param_id", str),
        ("interest_free_buffer_amount_param_id", str),
        ("interest_free_buffer_days_param_id", str),
    ],
)

DEFAULT_OVERDRAFT_INTEREST_FETCHERS_CONFIG = OverdraftInterestFetchersConfig(
    param_fetcher_id=OVERDRAFT_INTEREST_POF_ID,
    denomination_param_id=denomination_module.DENOMINATION_PARAM_ID,
    month_balances_fetcher_id=fetchers.ONE_MONTH_EFFECTIVE_DATE_BDIF_ID,
    days_in_year_param_id=interest_accrual.DAYS_IN_YEAR_PARAM_ID,
    accrual_precision_param_id=interest_accrual.ACCRUAL_PRECISION_PARAM_ID,
    application_precision_param_id=application_precision.APPLICATION_PRECISION_PARAM_ID,
    overdraft_interest_rate_param_id=OVERDRAFT_INTEREST_RATE_PARAM.id,
    overdraft_interest_receivable_account_param_id=OVERDRAFT_INTEREST_RECEIVABLE_ACCOUNT_PARAM.id,
    overdraft_interest_received_account_param_id=OVERDRAFT_INTEREST_RECEIVED_ACCOUNT_PARAM.id,
    interest_free_buffer_amount_param_id=INTEREST_FREE_BUFFER_AMOUNT_PARAM.id,
    interest_free_buffer_days_param_id=INTEREST_FREE_BUFFER_DAYS_PARAM.id,
)


def get_parameters(
    vault: SmartContractVault, param_fetcher_id: str = OVERDRAFT_INTEREST_POF_ID
) -> dict[str, datetime | Decimal | str | None]:
    """Retrieves configuration parameters for the overdraft interest feature.

    Args:
        vault: The vault object to retrieve parameters from.
        param_fetcher_id: The ID of the fetcher used to retrieve parameters.

    Returns:
        A dictionary mapping parameter IDs to their values.
    """
    return vault.get_parameters_observation(fetcher_id=param_fetcher_id).parameters


def _append_to_state(
    state: state_utils.SmartContractState,
    fetchers_config: OverdraftInterestFetchersConfig = DEFAULT_OVERDRAFT_INTEREST_FETCHERS_CONFIG,
    balance_fetcher_id: str = fetchers.ALL_BALANCES_ET_BOF_ID,
) -> state_utils.SmartContractState:
    """Updates the contract state with overdraft interest parameters and balances.

    Args:
        state: The current state of the smart contract.
        fetchers_config: Configuration for the fetchers used.
        balance_fetcher_id: The ID of the fetcher used to retrieve balances.

    Returns:
        The updated state object.
    """
    return state_utils.append_to_state(
        state=state,
        parameters=get_parameters(state.vault, fetchers_config.param_fetcher_id),
        balances=state.vault.get_balances_observation(fetcher_id=balance_fetcher_id).balances,
    )


def get_interest_rate(
    state: state_utils.SmartContractState,
    fetchers_config: OverdraftInterestFetchersConfig | None = None,
) -> common_tuples.InterestRateTuple:
    """Retrieves the overdraft interest rate from the contract state.

    Args:
        state: The current state of the smart contract.
        fetchers_config: Feature fetchers config.

    Returns:
        The interest rate tuple containing the rate and interest type.
    """
    fetchers_config = fetchers_config or DEFAULT_OVERDRAFT_INTEREST_FETCHERS_CONFIG
    state = _append_to_state(state=state, fetchers_config=fetchers_config)
    overdraft_interest_rate: Decimal = state.parameters.get(
        fetchers_config.overdraft_interest_rate_param_id
    )  # type: ignore

    return common_tuples.InterestRateTuple(
        interest_rate_param_value=overdraft_interest_rate,
        interest_type=common_tuples.INTEREST_TYPE_OVERDRAFT,
    )


def accrue_interest(
    state: state_utils.SmartContractState,
    account_type: str = "",
    fetchers_config: OverdraftInterestFetchersConfig = DEFAULT_OVERDRAFT_INTEREST_FETCHERS_CONFIG,
) -> list[CustomInstruction]:
    """Creates the posting instructions to accrue overdraft interest on the specified balances.

    This requires 6 days of balances for the interest_free_buffer_days comparison.

    Args:
        state: The current state of the smart contract.
        account_type: The account type for GL purposes.
        fetchers_config: Configuration for the fetchers used.

    Returns:
        The overdraft accrual posting instructions.
    """
    state = _append_to_state(state=state, fetchers_config=fetchers_config)

    rejection = state_utils.check_parameters_exist(
        state=state,
        param_ids={
            fetchers_config.accrual_precision_param_id,
            fetchers_config.days_in_year_param_id,
            fetchers_config.denomination_param_id,
            fetchers_config.overdraft_interest_rate_param_id,
            fetchers_config.overdraft_interest_receivable_account_param_id,
            fetchers_config.interest_free_buffer_amount_param_id,
            fetchers_config.interest_free_buffer_days_param_id,
        },
    )
    assert rejection is None, rejection

    yearly_interest_rate_param: Decimal = state.parameters[
        fetchers_config.overdraft_interest_rate_param_id
    ]  # type: ignore
    yearly_interest_rate = (
        Decimal(yearly_interest_rate_param)
        if yearly_interest_rate_param is not None
        else Decimal(0)
    )
    overdraft_interest_receivable_account: str = state.parameters[
        fetchers_config.overdraft_interest_receivable_account_param_id
    ]  # type: ignore

    if not (yearly_interest_rate > 0 and overdraft_interest_receivable_account):
        return []

    accrual_balance: Balance = calculate_accrual_balance(
        state=state,
        fetchers_config=fetchers_config,
    )

    if balance_utils.net_credit(accrual_balance) >= 0:
        return []

    days_in_year: str = state.parameters[fetchers_config.days_in_year_param_id]  # type: ignore
    rounding_precision = int(state.parameters[fetchers_config.accrual_precision_param_id])  # type: ignore
    denomination: str = state.parameters[fetchers_config.denomination_param_id]  # type: ignore

    day_rate: Decimal = parameter_utils.yearly_to_daily_rate(
        effective_date=state.effective_datetime,
        yearly_rate=yearly_interest_rate,
        days_in_year=days_in_year,
    )
    accrual_amount_rounded = common_utils.round_decimal(
        balance_utils.net_debit(accrual_balance) * day_rate, decimal_places=rounding_precision
    )

    return accruals.create_receivable_accrual_custom_instruction(
        customer_account=state.vault.account_id,
        customer_address=OVERDRAFT_ACCRUED_INTEREST,
        denomination=denomination,
        amount=accrual_amount_rounded,
        internal_account=overdraft_interest_receivable_account,
        instruction_details=posting_utils.standard_instruction_details(
            description=f"Accrual on overdraft balance of "
            f"{balance_utils.net_debit(accrual_balance):.2f} {denomination} at "
            f"{yearly_interest_rate * 100:.2f}%",
            event_type=OVERDRAFT_ACCRUAL_EVENT,
            gl_impacted=True,
            account_type=account_type,
        ),
    )


def _retrieve_eod_observations(
    state: state_utils.SmartContractState,
    fetchers_config: OverdraftInterestFetchersConfig,
) -> list[Balance]:
    """Retrieves the last 6 End-Of-Day net credit balances for the default address.

    Positions:[0] - current EOD, [1] - Previous Day, [2] - 2 Days Ago, ... , [5] - 5 Days Ago

    Args:
        state: The current state of the smart contract.
        fetchers_config: Configuration for the fetchers used.
        denomination: The denomination of the balances.

    Returns:
        List of net credit balances ordered in reverse chronological order.
    """
    rejection = state_utils.check_parameters_exist(
        state=state,
        param_ids={
            fetchers_config.denomination_param_id,
        },
    )
    assert rejection is None, rejection
    one_month_bals_ts_map: Mapping[BalanceCoordinate, BalanceDiscreteTimeseries] = (
        state.vault.get_balances_discrete_timeseries(
            fetcher_id=fetchers_config.month_balances_fetcher_id,
        )
    )
    denomination: str = state.parameters[fetchers_config.denomination_param_id]  # type: ignore
    coord = BalanceCoordinate(
        account_address=DEFAULT_ADDRESS,
        asset=DEFAULT_ASSET,
        denomination=denomination,
        phase=Phase.COMMITTED,
    )

    if coord not in one_month_bals_ts_map:
        return [Balance()] * 6

    one_month_bals_ts: BalanceDiscreteTimeseries = one_month_bals_ts_map[coord]

    # Get the last 6 days of balances
    balances_list = []
    for i in range(6):
        ts_item = one_month_bals_ts.get(
            at_datetime=state.effective_datetime - relativedelta(days=i)
        )
        balances_list.append(ts_item.value if ts_item else Balance())

    return balances_list


def calculate_accrual_balance(
    state: state_utils.SmartContractState,
    fetchers_config: OverdraftInterestFetchersConfig,
) -> Balance:
    """Factor in optional interest free buffer days and amount to determine the balance.

    Returns a zero Balance if calculated amount is in net credit.

    Args:
        state: The current state of the smart contract.
        fetchers_config: Configuration for the fetchers used.

    Returns:
        The balance to use in overdraft interest accruals, should always be less or equal zero.
    """
    rejection = state_utils.check_parameters_exist(
        state=state,
        param_ids={
            fetchers_config.denomination_param_id,
            fetchers_config.interest_free_buffer_amount_param_id,
            fetchers_config.interest_free_buffer_days_param_id,
        },
    )
    assert rejection is None, rejection
    observations: list[Balance] = _retrieve_eod_observations(
        state=state, fetchers_config=fetchers_config
    )
    end_of_day_balance: Balance = observations[0]

    # If EOD balance is in net credit no need to continue since the account is not in overdraft
    if balance_utils.net_credit(end_of_day_balance) >= 0:
        return Balance()

    interest_free_amount_param = state.parameters[
        fetchers_config.interest_free_buffer_amount_param_id
    ]
    interest_free_amount = (
        Decimal(str(interest_free_amount_param))
        if interest_free_amount_param is not None
        else Decimal(0)
    )
    buffered_end_of_day_balance = end_of_day_balance + Balance(
        credit=interest_free_amount, net=interest_free_amount
    )

    # If the buffer period is set to 0 the buffer amount is always applied
    interest_free_days_param = state.parameters[fetchers_config.interest_free_buffer_days_param_id]
    interest_free_days = (
        int(str(interest_free_days_param)) if interest_free_days_param is not None else 0
    )
    if interest_free_days == 0:
        if balance_utils.net_credit(buffered_end_of_day_balance) >= 0:
            return Balance()
        else:
            return buffered_end_of_day_balance

    highest_amount: Balance = next(
        iter(
            sorted(
                observations[1 : interest_free_days + 1],
                key=lambda b: balance_utils.net_credit(b),
                reverse=True,
            )
        ),
        Balance(),
    )

    # If there is a positive day in the interest free period the free buffer amount is still
    # applied (if the interest free amount is set to zero the full overdraft amount will covered)
    # otherwise it means the free period limit has been reached and the buffer amount no longer
    # applies
    if balance_utils.net_credit(highest_amount) >= 0:
        return (
            Balance()
            if balance_utils.net_credit(buffered_end_of_day_balance) >= 0
            or interest_free_amount == 0
            else buffered_end_of_day_balance
        )

    return end_of_day_balance


def overdraft_interest_capitalisation_custom_instruction(
    customer_account: str,
    denomination: str,
    application_amount: Decimal,
    accrual_amount: Decimal,
    instruction_details: dict[str, str],
    accrual_customer_address: str,
    accrual_internal_account: str,
    application_customer_address: str,
    application_internal_account: str,
) -> list[CustomInstruction]:
    """Create a Custom Instruction for applying (capitalising) accrued overdraft interest.

    Debits the customer account and credits the internal income account for application.
    Debits the internal receivable account and credits the customer accrual address to zero out the accrual.
    """
    if application_amount == 0:
        return []

    # 1. Application postings (Move money from customer to internal income account)
    postings = posting_utils.create_postings(
        amount=application_amount,
        debit_account=customer_account,
        credit_account=application_internal_account,
        denomination=denomination,
        debit_address=application_customer_address,
        credit_address=DEFAULT_ADDRESS,
    )

    # 2. Reversal of the accrual (Move money from internal receivable back to customer accrual address)
    if accrual_amount != 0:
        postings.extend(
            posting_utils.create_postings(
                amount=accrual_amount,
                debit_account=accrual_internal_account,
                credit_account=customer_account,
                denomination=denomination,
                debit_address=DEFAULT_ADDRESS,
                credit_address=accrual_customer_address,
            )
        )

    return (
        [
            CustomInstruction(
                postings=postings,
                instruction_details=instruction_details,
                override_all_restrictions=True,
            )
        ]
        if postings
        else []
    )


def apply_interest(
    state: state_utils.SmartContractState,
    account_type: str = "",
    fetchers_config: OverdraftInterestFetchersConfig = DEFAULT_OVERDRAFT_INTEREST_FETCHERS_CONFIG,
) -> list[CustomInstruction]:
    """Creates the postings instructions to apply the accrued overdraft interest.

    Includes additional postings required to zero the accrued overdraft interest remainders.

    Args:
        state: The current state of the smart contract.
        account_type: The account type for GL purposes.
        fetchers_config: Configuration for the fetchers used.

    Returns:
        The overdraft interest application related posting instructions.
    """
    state = _append_to_state(state=state, fetchers_config=fetchers_config)
    rejection = state_utils.check_parameters_exist(
        state,
        {
            fetchers_config.denomination_param_id,
            fetchers_config.application_precision_param_id,
            fetchers_config.overdraft_interest_receivable_account_param_id,
            fetchers_config.overdraft_interest_received_account_param_id,
        },
    )
    assert rejection is None, rejection

    denomination = str(state.parameters[fetchers_config.denomination_param_id])
    accrued_overdraft_interest: Decimal = balance_utils.net_debit(
        state.balances[
            BalanceCoordinate(
                account_address=OVERDRAFT_ACCRUED_INTEREST,
                asset=DEFAULT_ASSET,
                denomination=denomination,
                phase=Phase.COMMITTED,
            )
        ]
    )
    # No accrued overdraft interest to charge to the account
    if accrued_overdraft_interest <= 0:
        return []

    application_precision = int(state.parameters[fetchers_config.application_precision_param_id])  # type: ignore
    application_amount_rounded = common_utils.round_decimal(
        amount=accrued_overdraft_interest,
        decimal_places=application_precision,
    )
    return overdraft_interest_capitalisation_custom_instruction(
        customer_account=state.vault.account_id,
        denomination=denomination,
        accrual_amount=accrued_overdraft_interest,
        accrual_customer_address=OVERDRAFT_ACCRUED_INTEREST,
        accrual_internal_account=state.parameters[
            fetchers_config.overdraft_interest_receivable_account_param_id
        ],  # type: ignore
        application_amount=application_amount_rounded,
        application_customer_address=DEFAULT_ADDRESS,
        application_internal_account=state.parameters[
            fetchers_config.overdraft_interest_received_account_param_id
        ],  # type: ignore
        instruction_details=posting_utils.standard_instruction_details(
            description=f"Apply {application_amount_rounded} {denomination} overdraft "
            f"interest of {accrued_overdraft_interest} rounded to {application_precision}"
            f" DP to {state.vault.account_id}.",
            event_type=OVERDRAFT_APPLICATION_EVENT,
            gl_impacted=True,
            account_type=account_type,
        ),
    )


def get_interest_reversal_postings(
    state: state_utils.SmartContractState,
    event_name: str,
    account_type: str = "",
    fetchers_config: OverdraftInterestFetchersConfig = DEFAULT_OVERDRAFT_INTEREST_FETCHERS_CONFIG,
) -> list[CustomInstruction]:
    """Reverse any accrued overdraft interest and apply back to the internal account.

    During account closure, any overdraft interest that has not been applied should return back to
    the bank's internal account.

    Args:
        state: The current state of the smart contract.
        event_name: The name of the event reversing any accrue interest.
        account_type: The account type for GL purposes.
        fetchers_config: Configuration for the fetchers used.

    Returns:
        The accrued interest reversal posting instructions.
    """
    state = _append_to_state(state=state, fetchers_config=fetchers_config)

    overdraft_interest_receivable_account = str(
        state.parameters.get(fetchers_config.overdraft_interest_receivable_account_param_id, "")
    )
    # Required optional parameters are not set
    if not overdraft_interest_receivable_account:
        return []

    denomination = str(state.parameters[fetchers_config.denomination_param_id])

    accrued_overdraft_interest = balance_utils.balance_at_coordinates(
        balances=state.balances,
        address=OVERDRAFT_ACCRUED_INTEREST,
        denomination=denomination,
    )

    # No accrued overdraft interest to revert
    if accrued_overdraft_interest == 0:
        return []

    return accruals.create_receivable_accrual_custom_instruction(
        customer_account=state.vault.account_id,
        customer_address=OVERDRAFT_ACCRUED_INTEREST,
        denomination=denomination,
        amount=abs(accrued_overdraft_interest),
        internal_account=overdraft_interest_receivable_account,
        instruction_details=posting_utils.standard_instruction_details(
            description=f"Reversing {accrued_overdraft_interest} {denomination} "
            "of accrued overdraft interest.",
            event_type=event_name,
            gl_impacted=True,
            account_type=account_type,
        ),
        reversal=True,
    )


def get_overdraft_accrual_amount(
    *,
    effective_balance: Balance,
    effective_datetime: datetime,
    interest_rates: Decimal,
    days_in_year: str,
    precision: int = 5,
    state: state_utils.SmartContractState | None = None,
    fetchers_config: OverdraftInterestFetchersConfig | None = None,
) -> common_tuples.AccrualDetail:
    """Calculates overdraft interest accrual amount using specialized buffer logic.

    Args:
        effective_balance: The current effective balance.
        effective_datetime: The effective datetime of the accrual.
        interest_rates: The yearly interest rate.
        days_in_year: The days in year convention.
        precision: The rounding precision.
        state: The smart contract state (required for historical balance fetching).
        fetchers_config: Feature fetchers config.

    Returns:
        AccrualDetail containing the calculated amount and description.
    """
    assert state is not None, "State is required for overdraft interest accrual"
    fetchers_config = fetchers_config or DEFAULT_OVERDRAFT_INTEREST_FETCHERS_CONFIG
    state = _append_to_state(
        state=state,
        fetchers_config=fetchers_config,
    )

    accrual_balance: Balance = calculate_accrual_balance(
        state=state,
        fetchers_config=fetchers_config,
    )
    effective_net_debit: Decimal = balance_utils.net_debit(accrual_balance)
    if not effective_net_debit > 0:
        return common_tuples.AccrualDetail(Decimal(0), "")

    day_rate: Decimal = parameter_utils.yearly_to_daily_rate(
        effective_date=effective_datetime,
        yearly_rate=interest_rates,
        days_in_year=days_in_year,
    )

    accrual_amount_rounded: Decimal = common_utils.round_decimal(
        effective_net_debit * day_rate, decimal_places=precision
    )

    return common_tuples.AccrualDetail(
        accrual_amount=accrual_amount_rounded,
        description=f"Accrual on overdraft balance of "
        f"{balance_utils.net_debit(accrual_balance):.2f} at "
        f"{interest_rates * 100:.2f}%",
    )


def get_accrual_payable_customer_address() -> str:
    return OVERDRAFT_ACCRUED_INTEREST


def get_accrual_receivable_customer_address() -> str:
    return OVERDRAFT_ACCRUED_INTEREST


def get_accrual_payable_internal_account(
    state: state_utils.SmartContractState,
) -> str:
    """Returns the internal account where overdraft interest is accrued.

    Args:
        state: Smart contract state.

    Returns:
        The internal account ID for overdraft interest receivable.
    """
    # Overdraft interest is always receivable (payable=False)
    state = _append_to_state(state=state)
    # There is no overdraft interest payable account id defined because we never expect to have negative overdraft interest rates, so for the sake of completeness, we provide this function and return the receivable address.
    return state.parameters.get(OVERDRAFT_INTEREST_RECEIVABLE_ACCOUNT_PARAM_ID, "")  # type: ignore


def get_accrual_receivable_internal_account(
    state: state_utils.SmartContractState,
) -> str:
    """Returns the internal account where overdraft interest is accrued.

    Args:
        state: Smart contract state.

    Returns:
        The internal account ID for overdraft interest receivable.
    """
    # Overdraft interest is always receivable (payable=False)
    state = _append_to_state(state=state)
    return state.parameters.get(OVERDRAFT_INTEREST_RECEIVABLE_ACCOUNT_PARAM_ID, "")  # type: ignore


InterestType = deposit_interfaces.InterestType(
    get_interest_rate=get_interest_rate,
    get_accrual_amount=get_overdraft_accrual_amount,
    get_accrual_payable_customer_address=get_accrual_payable_customer_address,
    get_accrual_receivable_customer_address=get_accrual_payable_customer_address,
    get_accrual_payable_internal_account=get_accrual_payable_internal_account,
    get_accrual_receivable_internal_account=get_accrual_receivable_internal_account,
)
