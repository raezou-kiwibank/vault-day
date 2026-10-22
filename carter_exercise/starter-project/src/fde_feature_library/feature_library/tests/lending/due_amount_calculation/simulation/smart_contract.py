# Copyright @ 2026 Thought Machine Group Limited. All rights reserved.
from decimal import Decimal
from typing import Any

# feature library
import feature_library.common.denomination as denomination_module
import feature_library.common.fetchers as common_fetchers
import feature_library.common.parameter_utils as parameter_utils
import feature_library.common.state_utils as state_utils
import feature_library.lending.due_amount_calculation.due_amount_calculation as due_calc
import feature_library.lending.interfaces as lending_interfaces

# contracts api
from contracts_api import (
    ActivationHookArguments,
    ActivationHookResult,
    PostingInstructionsDirective,
    ScheduledEventHookArguments,
    ScheduledEventHookResult,
    Tside,
    fetch_account_data,
)

from inception_sdk.vault.contracts.extensions.contracts_api_extensions import SmartContractVault

api = "4.0.0"
version = "1.0.0"
tside = Tside.ASSET

expected_parameters: list[Any] = parameter_utils.distinct_expected_parameters(
    [
        *due_calc.expected_parameters,
        *denomination_module.expected_parameters,
    ]
)

data_fetchers: list[Any] = common_fetchers.distinct_fetchers(
    [
        *due_calc.data_fetchers,  # type: ignore
        *denomination_module.data_fetchers,
        common_fetchers.ALL_BALANCES_ET_BOF,
    ]
)

event_types = due_calc.event_types("DUMMY")


@fetch_account_data(
    parameters=[
        due_calc.DUE_AMOUNT_CALC_POF_ID,
        denomination_module.DENOMINATION_ET_POF_ID,
    ]
)
def activation_hook(
    vault: SmartContractVault, arguments: ActivationHookArguments
) -> ActivationHookResult | None:
    state = state_utils.initialise_state(
        vault=vault,
        effective_datetime=arguments.effective_datetime,
    )
    scheduled_events = due_calc.get_scheduled_events(state=state)
    return ActivationHookResult(scheduled_events_return_value=scheduled_events)


# Dummy Functional Interfaces as per lending conventions
dummy_interest_application = lending_interfaces.InterestApplication(
    apply_interest=lambda **kwargs: [],
    get_interest_to_apply=lambda **kwargs: lending_interfaces.InterestAmounts(
        eia_rounded_accrued=Decimal("0"),
        eia_accrued=Decimal("0"),
        non_eia_rounded_accrued=Decimal("0"),
        non_eia_accrued=Decimal("0"),
        total_rounded=Decimal("0"),
    ),
)

dummy_repayment_hierarchy = lending_interfaces.RepaymentHierarchy(
    get_total_outstanding_debt=lambda **kwargs: Decimal("0"),
    get_total_overdue_amount=lambda **kwargs: Decimal("0"),
    get_total_due_amount=lambda **kwargs: Decimal("0"),
    get_repayment_hierarchy_order=lambda **kwargs: [],
)

dummy_repayment_hierarchy_config = lending_interfaces.RepaymentHierarchyConfig(
    repayment_hierarchy=dummy_repayment_hierarchy,
    fetchers_config=[],
)


@fetch_account_data(
    event_type=due_calc.DUE_AMOUNT_CALCULATION_EVENT,
    parameters=[
        due_calc.DUE_AMOUNT_CALC_POF_ID,
        denomination_module.DENOMINATION_ET_POF_ID,
    ],
    balances=[
        common_fetchers.ALL_BALANCES_ET_BOF_ID,
    ],
    last_scheduled_event_datetimes=[
        due_calc.LAST_DUE_AMOUNT_CALCULATION_SOF_ID,
    ],
)
def scheduled_event_hook(
    vault: SmartContractVault, hook_arguments: ScheduledEventHookArguments
) -> ScheduledEventHookResult | None:
    params = (
        denomination_module.get_parameters(vault=vault)
        | vault.get_parameters_observation(fetcher_id=due_calc.DUE_AMOUNT_CALC_POF_ID).parameters
    )

    state = state_utils.initialise_state(
        vault=vault,
        effective_datetime=hook_arguments.effective_datetime,
        parameters=params,
    )

    custom_instructions = []
    event_type_directives = []
    if hook_arguments.event_type == due_calc.DUE_AMOUNT_CALCULATION_EVENT:
        schedule_logic_result = due_calc.schedule_logic(
            state=state,
            get_expected_eia_callable=lambda state: Decimal("100"),
            interest_application_feature=dummy_interest_application,
            repayment_hierarchy_config=dummy_repayment_hierarchy_config,
        )
        custom_instructions = schedule_logic_result.custom_instructions
        event_type_directives = schedule_logic_result.event_type_directives

    return ScheduledEventHookResult(
        posting_instructions_directives=[
            PostingInstructionsDirective(
                posting_instructions=custom_instructions,
                value_datetime=hook_arguments.effective_datetime,
            )
        ]
        if custom_instructions
        else None,
        update_account_event_type_directives=event_type_directives or None,
    )
