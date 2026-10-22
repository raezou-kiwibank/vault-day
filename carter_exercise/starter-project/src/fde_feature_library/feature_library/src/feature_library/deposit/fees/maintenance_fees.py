__smart_contract_feature__ = True

# standard libs
from datetime import datetime
from decimal import Decimal
from json import loads
from typing import NamedTuple
from zoneinfo import ZoneInfo

from dateutil.relativedelta import relativedelta

# feature library
import feature_library.common.date_and_time as date_and_time
import feature_library.common.denomination as denomination_module
import feature_library.common.fetchers as fetchers
import feature_library.common.posting_utils as posting_utils
import feature_library.common.state_utils as state_utils
import feature_library.common.utils as common_utils
import feature_library.deposit.common as common
import feature_library.deposit.fees.partial_fee as partial_fee
import feature_library.deposit.interfaces as deposit_interfaces

# contracts api
from contracts_api import (
    CustomInstruction,
    DefinedDateTime,
    ExpectedParameter,
    ParametersFilter,
    ParametersObservationFetcher,
    ScheduledEvent,
    ScheduleExpression,
    SmartContractEventType,
    UpdateAccountEventTypeDirective,
)

# inception sdk
from inception_sdk.vault.contracts.extensions.contracts_api_extensions import SmartContractVault

UTC = ZoneInfo("UTC")

# Events
APPLY_MONTHLY_FEE_EVENT = "APPLY_MONTHLY_FEE"
APPLY_ANNUAL_FEE_EVENT = "APPLY_ANNUAL_FEE"

# Frequencies
MONTHLY = "monthly"
ANNUALLY = "annually"

# Addresses
OUTSTANDING_MONTHLY_MAINTENANCE_FEE_TRACKER = "outstanding_monthly_maintenance_fee_tracker"

# Parameter IDs
MAINTENANCE_FEE_APPLICATION_DAY_PARAM_ID = "&{maintenance_fee_application_day}"
MAINTENANCE_FEE_APPLICATION_TIME_PARAM_ID = "&{maintenance_fee_application_time}"
MONTHLY_MAINTENANCE_FEE_BY_TIER_PARAM_ID = "&{monthly_maintenance_fee_by_tier}"
MONTHLY_MAINTENANCE_FEE_INCOME_ACCOUNT_PARAM_ID = "&{monthly_maintenance_fee_income_account}"
MONTHLY_MAINTENANCE_FEE_PARTIAL_FEE_ENABLED_PARAM_ID = "&{partial_maintenance_fee_enabled}"
ANNUAL_MAINTENANCE_FEE_BY_TIER_PARAM_ID = "&{annual_maintenance_fee_by_tier}"
ANNUAL_MAINTENANCE_FEE_INCOME_ACCOUNT_PARAM_ID = "&{annual_maintenance_fee_income_account}"
ACCOUNT_TIER_PARAM_ID = "&{account_tier}"

# Expected Parameters
MAINTENANCE_FEE_APPLICATION_DAY_PARAM = ExpectedParameter(
    id=MAINTENANCE_FEE_APPLICATION_DAY_PARAM_ID,
    triggers_pre_parameter_change_hook=False,
    triggers_post_parameter_change_hook=False,
)

MAINTENANCE_FEE_APPLICATION_TIME_PARAM = ExpectedParameter(
    id=MAINTENANCE_FEE_APPLICATION_TIME_PARAM_ID,
    triggers_pre_parameter_change_hook=False,
    triggers_post_parameter_change_hook=False,
)

MONTHLY_MAINTENANCE_FEE_BY_TIER_PARAM = ExpectedParameter(
    id=MONTHLY_MAINTENANCE_FEE_BY_TIER_PARAM_ID,
    triggers_pre_parameter_change_hook=False,
    triggers_post_parameter_change_hook=False,
)

MONTHLY_MAINTENANCE_FEE_INCOME_ACCOUNT_PARAM = ExpectedParameter(
    id=MONTHLY_MAINTENANCE_FEE_INCOME_ACCOUNT_PARAM_ID,
    triggers_pre_parameter_change_hook=False,
    triggers_post_parameter_change_hook=False,
)

MONTHLY_MAINTENANCE_FEE_PARTIAL_FEE_ENABLED_PARAM = ExpectedParameter(
    id=MONTHLY_MAINTENANCE_FEE_PARTIAL_FEE_ENABLED_PARAM_ID,
    optional=True,
    triggers_pre_parameter_change_hook=False,
    triggers_post_parameter_change_hook=False,
)

ANNUAL_MAINTENANCE_FEE_BY_TIER_PARAM = ExpectedParameter(
    id=ANNUAL_MAINTENANCE_FEE_BY_TIER_PARAM_ID,
    triggers_pre_parameter_change_hook=False,
    triggers_post_parameter_change_hook=False,
)

ANNUAL_MAINTENANCE_FEE_INCOME_ACCOUNT_PARAM = ExpectedParameter(
    id=ANNUAL_MAINTENANCE_FEE_INCOME_ACCOUNT_PARAM_ID,
    triggers_pre_parameter_change_hook=False,
    triggers_post_parameter_change_hook=False,
)

expected_parameters = [
    MAINTENANCE_FEE_APPLICATION_DAY_PARAM,
    MAINTENANCE_FEE_APPLICATION_TIME_PARAM,
    MONTHLY_MAINTENANCE_FEE_BY_TIER_PARAM,
    MONTHLY_MAINTENANCE_FEE_INCOME_ACCOUNT_PARAM,
    MONTHLY_MAINTENANCE_FEE_PARTIAL_FEE_ENABLED_PARAM,
    ANNUAL_MAINTENANCE_FEE_BY_TIER_PARAM,
    ANNUAL_MAINTENANCE_FEE_INCOME_ACCOUNT_PARAM,
    common.ACCOUNT_TIER_PARAM,
    denomination_module.DENOMINATION_PARAM,
]

# Fetchers
MAINTENANCE_FEES_POF_ID = "maintenance_fees_pof"
MAINTENANCE_FEES_POF = ParametersObservationFetcher(
    fetcher_id=MAINTENANCE_FEES_POF_ID,
    at=DefinedDateTime.EFFECTIVE_DATETIME,
    filter=ParametersFilter(parameter_ids=[p.id for p in expected_parameters]),
)

data_fetchers = [
    fetchers.ALL_BALANCES_ET_BOF,
    MAINTENANCE_FEES_POF,
]


def event_types(*, product_name: str, frequency: str) -> list[SmartContractEventType]:
    """Creates monthly or annual event to apply maintenance fees.

    Args:
        product_name: the name of the product to create the event.
        frequency: the frequency to create the monthly or annual event.

    Returns:
        Smart contract event type to scheduled event.
    """
    if frequency == MONTHLY:
        event_name = APPLY_MONTHLY_FEE_EVENT
    elif frequency == ANNUALLY:
        event_name = APPLY_ANNUAL_FEE_EVENT
    else:
        return []
    return [
        SmartContractEventType(
            name=event_name,
            scheduler_tag_ids=[f"{product_name.upper()}_{event_name}_AST"],
        )
    ]


MaintenanceFeesFetchersConfig = NamedTuple(
    "MaintenanceFeesFetchersConfig",
    [
        ("param_fetcher_id", str),
        ("denomination_param_id", str),
    ],
)

DEFAULT_MAINTENANCE_FEES_FETCHERS_CONFIG = MaintenanceFeesFetchersConfig(
    param_fetcher_id=MAINTENANCE_FEES_POF_ID,
    denomination_param_id=denomination_module.DENOMINATION_PARAM.id,
)


def get_parameters(
    vault: SmartContractVault, param_fetcher_id: str = MAINTENANCE_FEES_POF_ID
) -> dict[str, datetime | Decimal | str | None]:
    """Retrieves configuration parameters for the maintenance fees feature."""
    return vault.get_parameters_observation(fetcher_id=param_fetcher_id).parameters


def _append_to_state(
    state: state_utils.SmartContractState,
    fetchers_config: MaintenanceFeesFetchersConfig = DEFAULT_MAINTENANCE_FEES_FETCHERS_CONFIG,
    balance_fetcher_id: str = fetchers.ALL_BALANCES_ET_BOF_ID,
) -> state_utils.SmartContractState:
    """Updates the contract state with maintenance fee parameters and balances."""
    return state_utils.append_to_state(
        state=state,
        parameters=get_parameters(state.vault, fetchers_config.param_fetcher_id),
        balances=state.vault.get_balances_observation(fetcher_id=balance_fetcher_id).balances,
    )


def get_scheduled_events(
    state: state_utils.SmartContractState,
    frequency: str,
    fetchers_config: MaintenanceFeesFetchersConfig = DEFAULT_MAINTENANCE_FEES_FETCHERS_CONFIG,
) -> dict[str, ScheduledEvent]:
    """Create monthly or annual scheduled event to apply maintenance fees."""
    state = state_utils.append_to_state(
        state=state,
        parameters=get_parameters(state.vault, fetchers_config.param_fetcher_id),
    )

    schedule_param_ids: set[str] = {
        MAINTENANCE_FEE_APPLICATION_DAY_PARAM.id,
        MAINTENANCE_FEE_APPLICATION_TIME_PARAM.id,
    }

    rejection = state_utils.check_parameters_exist(state=state, param_ids=schedule_param_ids)
    assert rejection is None, rejection

    application_time_str = str(state.parameters[MAINTENANCE_FEE_APPLICATION_TIME_PARAM.id])
    application_time: date_and_time.Time = date_and_time.parse_time_str(application_time_str)
    day = int(state.parameters[MAINTENANCE_FEE_APPLICATION_DAY_PARAM.id])  # type: ignore

    start_datetime = state.effective_datetime.astimezone(state.vault.events_timezone).replace(
        hour=0, minute=0, second=0, microsecond=0
    )

    if frequency == MONTHLY:
        schedule_expression = ScheduleExpression(
            day=day,
            hour=application_time.hour,
            minute=application_time.minute,
            second=application_time.second,
        )
        return {
            APPLY_MONTHLY_FEE_EVENT: ScheduledEvent(
                start_datetime=start_datetime + relativedelta(months=1),
                expression=schedule_expression,
            )
        }
    elif frequency == ANNUALLY:
        # Adjust day if February 29th and next year is not a leap year.
        # Standard behaviour handles it.
        schedule_expression = ScheduleExpression(
            day=day,
            hour=application_time.hour,
            minute=application_time.minute,
            second=application_time.second,
        )

        return {
            APPLY_ANNUAL_FEE_EVENT: ScheduledEvent(
                start_datetime=start_datetime + relativedelta(years=1),
                expression=schedule_expression,
            )
        }

    return {}


def update_next_annual_schedule_execution(
    state: state_utils.SmartContractState,
    fetchers_config: MaintenanceFeesFetchersConfig = DEFAULT_MAINTENANCE_FEES_FETCHERS_CONFIG,
) -> UpdateAccountEventTypeDirective | None:
    """Update next annual scheduled execution with intended month not february.

    Returns None if no update is needed.
    """
    state = state_utils.append_to_state(
        state=state,
        parameters=get_parameters(state.vault, fetchers_config.param_fetcher_id),
    )

    rejection = state_utils.check_parameters_exist(
        state=state, param_ids={MAINTENANCE_FEE_APPLICATION_DAY_PARAM.id}
    )
    assert rejection is None, rejection

    schedule_day = int(state.parameters[MAINTENANCE_FEE_APPLICATION_DAY_PARAM.id])  # type: ignore

    effective_datetime = state.effective_datetime

    # no need to reschedule if application month not february or schedule day < 29
    if int(effective_datetime.month) != 2 or (
        int(effective_datetime.month) == 2 and schedule_day < 29
    ):
        return None

    new_schedule = get_scheduled_events(
        state=state, frequency=ANNUALLY, fetchers_config=fetchers_config
    )

    return UpdateAccountEventTypeDirective(
        event_type=APPLY_ANNUAL_FEE_EVENT,
        expression=new_schedule[APPLY_ANNUAL_FEE_EVENT].expression,
    )


PARTIAL_FEE_DETAILS = deposit_interfaces.PartialFeeCollection(
    outstanding_fee_address=OUTSTANDING_MONTHLY_MAINTENANCE_FEE_TRACKER,
    fee_type="Partial Monthly Maintenance Fee",
    internal_account_parameter_id=MONTHLY_MAINTENANCE_FEE_INCOME_ACCOUNT_PARAM.id,
)


def _are_monthly_partial_payments_enabled(
    state: state_utils.SmartContractState,
) -> bool:
    return common_utils.str_to_bool(
        str(state.parameters.get(MONTHLY_MAINTENANCE_FEE_PARTIAL_FEE_ENABLED_PARAM.id, "False"))
    )


def apply_monthly_fee(
    state: state_utils.SmartContractState,
    account_type: str,
    fetchers_config: MaintenanceFeesFetchersConfig = DEFAULT_MAINTENANCE_FEES_FETCHERS_CONFIG,
    monthly_fee_waive_conditions: list[deposit_interfaces.WaiveFeeCondition] | None = None,
    available_balance_feature: deposit_interfaces.AvailableBalance | None = None,
) -> list[CustomInstruction]:
    """Gets monthly maintenance fees and the account where it will be credited."""
    if any(
        f.waive_fees(vault=state.vault, effective_datetime=state.effective_datetime)
        for f in monthly_fee_waive_conditions or []
    ):
        return []

    state = _append_to_state(state=state, fetchers_config=fetchers_config)

    rejection = state_utils.check_parameters_exist(
        state,
        {
            fetchers_config.denomination_param_id,
            common.ACCOUNT_TIER_PARAM.id,
            MONTHLY_MAINTENANCE_FEE_BY_TIER_PARAM.id,
            MONTHLY_MAINTENANCE_FEE_INCOME_ACCOUNT_PARAM.id,
        },
    )
    assert rejection is None, rejection

    maintenance_fee_income_account = str(
        state.parameters[MONTHLY_MAINTENANCE_FEE_INCOME_ACCOUNT_PARAM.id]
    )

    monthly_maintenance_fee_tiers = loads(
        str(state.parameters[MONTHLY_MAINTENANCE_FEE_BY_TIER_PARAM.id])
    )
    tier = str(state.parameters[common.ACCOUNT_TIER_PARAM.id])
    maintenance_fee_monthly = Decimal(monthly_maintenance_fee_tiers.get(tier, "0"))

    if maintenance_fee_monthly <= 0:
        return []

    denomination = str(state.parameters[fetchers_config.denomination_param_id])

    fee_instructions = [
        CustomInstruction(
            postings=posting_utils.create_postings(
                amount=maintenance_fee_monthly,
                debit_account=state.vault.account_id,
                credit_account=maintenance_fee_income_account,
                denomination=denomination,
            ),
            value_datetime=state.effective_datetime,
            instruction_details=posting_utils.standard_instruction_details(
                description="Monthly maintenance fee",
                event_type=APPLY_MONTHLY_FEE_EVENT,
                gl_impacted=True,
                account_type=account_type,
            ),
            override_all_restrictions=True,
        )
    ]

    if _are_monthly_partial_payments_enabled(state):
        return partial_fee.charge_partial_fee(
            state=state,
            fee_custom_instruction=fee_instructions[0],
            fee_details=PARTIAL_FEE_DETAILS,
            available_balance_feature=available_balance_feature,
        )

    return fee_instructions


def apply_annual_fee(
    state: state_utils.SmartContractState,
    account_type: str,
    fetchers_config: MaintenanceFeesFetchersConfig = DEFAULT_MAINTENANCE_FEES_FETCHERS_CONFIG,
) -> list[CustomInstruction]:
    """Gets annual maintenance fees and the account where it will be credited."""
    state = _append_to_state(state=state, fetchers_config=fetchers_config)

    rejection = state_utils.check_parameters_exist(
        state,
        {
            fetchers_config.denomination_param_id,
            common.ACCOUNT_TIER_PARAM.id,
            ANNUAL_MAINTENANCE_FEE_BY_TIER_PARAM.id,
            ANNUAL_MAINTENANCE_FEE_INCOME_ACCOUNT_PARAM.id,
        },
    )
    assert rejection is None, rejection

    maintenance_fee_income_account = str(
        state.parameters[ANNUAL_MAINTENANCE_FEE_INCOME_ACCOUNT_PARAM.id]
    )

    annual_maintenance_fee_tiers = loads(
        str(state.parameters[ANNUAL_MAINTENANCE_FEE_BY_TIER_PARAM.id])
    )
    tier = str(state.parameters[common.ACCOUNT_TIER_PARAM.id])
    maintenance_fee_annual = Decimal(annual_maintenance_fee_tiers.get(tier, "0"))

    if maintenance_fee_annual <= 0:
        return []

    denomination = str(state.parameters[fetchers_config.denomination_param_id])

    fee_instructions = [
        CustomInstruction(
            postings=posting_utils.create_postings(
                amount=maintenance_fee_annual,
                debit_account=state.vault.account_id,
                credit_account=maintenance_fee_income_account,
                denomination=denomination,
            ),
            value_datetime=state.effective_datetime,
            instruction_details=posting_utils.standard_instruction_details(
                description="Annual maintenance fee",
                event_type=APPLY_ANNUAL_FEE_EVENT,
                gl_impacted=True,
                account_type=account_type,
            ),
            override_all_restrictions=True,
        )
    ]

    return fee_instructions
