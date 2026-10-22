# Copyright @ 2026 Thought Machine Group Limited. All rights reserved.
import feature_library.common.denomination as denomination_module
import feature_library.common.fetchers as common_fetchers
import feature_library.common.parameter_utils as parameter_utils
import feature_library.common.state_utils as state_utils
import feature_library.lending.closure.close_loan as close_loan
import feature_library.lending.interfaces as lending_interfaces
import feature_library.lending.repayments.secondary.vertical_repayment_hierarchy as vertical_hierarchy  # noqa

from contracts_api import (
    DeactivationHookArguments,
    DeactivationHookResult,
    PostPostingHookArguments,
    PostPostingHookResult,
    Tside,
    fetch_account_data,
)

from inception_sdk.vault.contracts.extensions.contracts_api_extensions import SmartContractVault

api = "4.0.0"
version = "1.0.0"
tside = Tside.ASSET

PRODUCT_NAME = "CLOSE_LOAN_VERTICAL"

notification_types = [
    close_loan.notification_type(product_name=PRODUCT_NAME),
]

# Required for simulation
expected_parameters = parameter_utils.distinct_expected_parameters(
    [
        *denomination_module.expected_parameters,
    ]
)

data_fetchers = common_fetchers.distinct_fetchers(
    [
        *denomination_module.data_fetchers,
        common_fetchers.ALL_BALANCES_ET_BOF,
    ]
)


@fetch_account_data(
    parameters=[
        denomination_module.DENOMINATION_ET_POF_ID,
    ],
    balances=[
        common_fetchers.ALL_BALANCES_ET_BOF_ID,
    ],
)
def post_posting_hook(
    vault: SmartContractVault, arguments: PostPostingHookArguments
) -> PostPostingHookResult | None:
    state = state_utils.initialise_state(
        vault=vault,
        effective_datetime=arguments.effective_datetime,
        parameters=denomination_module.get_parameters(vault),
        balances=vault.get_balances_observation(
            fetcher_id=common_fetchers.ALL_BALANCES_ET_BOF_ID
        ).balances,
    )

    repayment_hierarchy_config = lending_interfaces.RepaymentHierarchyConfig(
        repayment_hierarchy=vertical_hierarchy.VerticalRepaymentHierarchy,
        fetchers_config=vertical_hierarchy.DEFAULT_VERTICAL_FETCHERS_CONFIG,
    )

    account_notification_directives = []

    if close_loan.does_repayment_fully_repay_loan(
        state=state,
        repayment_posting_instructions=arguments.posting_instructions,
        repayment_hierarchy_config=repayment_hierarchy_config,
    ):
        account_notification_directives.append(
            close_loan.send_loan_paid_off_notification(
                state=state,
                product_name=PRODUCT_NAME,
            )
        )

    return PostPostingHookResult(account_notification_directives=account_notification_directives)


@fetch_account_data(
    parameters=[
        denomination_module.DENOMINATION_ET_POF_ID,
    ],
    balances=[
        common_fetchers.ALL_BALANCES_ET_BOF_ID,
    ],
)
def deactivation_hook(
    vault: SmartContractVault, arguments: DeactivationHookArguments
) -> DeactivationHookResult | None:
    state = state_utils.initialise_state(
        vault=vault,
        effective_datetime=arguments.effective_datetime,
        parameters=denomination_module.get_parameters(vault),
        balances=vault.get_balances_observation(
            fetcher_id=common_fetchers.ALL_BALANCES_ET_BOF_ID
        ).balances,
    )

    repayment_hierarchy_config = lending_interfaces.RepaymentHierarchyConfig(
        repayment_hierarchy=vertical_hierarchy.VerticalRepaymentHierarchy,
        fetchers_config=vertical_hierarchy.DEFAULT_VERTICAL_FETCHERS_CONFIG,
    )

    if rejection := close_loan.reject_closure_when_outstanding_debt(
        state=state,
        repayment_hierarchy_config=repayment_hierarchy_config,
    ):
        return DeactivationHookResult(rejection=rejection)

    return None
