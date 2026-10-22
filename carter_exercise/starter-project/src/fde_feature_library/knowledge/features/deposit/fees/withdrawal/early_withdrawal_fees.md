---
type: Vault Feature
okf_version: "0.2"
profile: https://thoughtmachine.example/fde/schemas/feature-knowledge-bundle/1.0.json
profile_version: 1.0.0
title: Early Withdrawal Fees
description: Smart Contract feature deposit.fees.withdrawal.early_withdrawal_fees.
status: draft
tags:
  - deposit
identity:
  id: feature_library.deposit.fees.withdrawal.early_withdrawal_fees
  module: feature_library.deposit.fees.withdrawal.early_withdrawal_fees
  source_path: feature_library/src/feature_library/deposit/fees/withdrawal/early_withdrawal_fees.py
  kind: primary
  domain: deposit
version:
  library_version: 1.0.0
  content_hash: sha256:d8babf46be9fe4fa314dc2f916acd34c0d50dd832319b1344ab85a2845fa4dbf
generated:
  by: process:fl/0.1.0
hooks:
  - pre_posting_hook
entry_points:
  - name: notification_type
    returns: str
    reads_parameters: []
  - name: get_notification_types
    returns: list[str]
    reads_parameters: []
  - name: get_parameters
    returns: dict[str, datetime | Decimal | str | None]
    reads_parameters: []
  - name: validate
    returns: Rejection | None
    reads_parameters: []
  - name: handle_withdrawals
    returns: HandleWithdrawalsResult
    reads_parameters: []
  - name: get_current_withdrawal_amount_default_balance_adjustment
    returns: deposit_interfaces.DefaultBalanceAdjustment
    reads_parameters: []
  - name: maximum_withdrawal_limit_attribute_handler
    returns: AttributeHookResult
    reads_parameters: []
  - name: fee_free_withdrawal_limit_attribute_handler
    returns: AttributeHookResult
    reads_parameters: []
  - name: reset_withdrawals_tracker
    returns: list[CustomInstruction]
    reads_parameters: []
  - name: generate_withdrawal_fee_notification
    returns: AccountNotificationDirective
    reads_parameters: []
  - name: calculate_withdrawal_fee_amounts
    returns: WithdrawalFeeAmounts
    reads_parameters: []
  - name: get_customer_deposit_amount
    returns: Decimal
    reads_parameters: []
parameters:
  - id: "&{early_withdrawal_flat_fee}"
    clu_id: early_withdrawal_flat_fee
    constant: EARLY_WITHDRAWAL_FLAT_FEE_PARAM
    ownership: owned
    owner_feature: deposit.fees.withdrawal.early_withdrawal_fees
    level: TEMPLATE
    constraint: decimal_constraint
    clu_resource: feature_library/src/feature_library/deposit/fees/withdrawal/parameter_resource_defs/early_withdrawal_flat_fee.resource.yaml
    optional: false
    triggers_pre_parameter_change_hook: false
    triggers_post_parameter_change_hook: false
    description: ""
    drives: ""
  - id: "&{early_withdrawal_percentage_fee}"
    clu_id: early_withdrawal_percentage_fee
    constant: EARLY_WITHDRAWAL_PERCENTAGE_FEE_PARAM
    ownership: owned
    owner_feature: deposit.fees.withdrawal.early_withdrawal_fees
    level: TEMPLATE
    constraint: decimal_constraint
    clu_resource: feature_library/src/feature_library/deposit/fees/withdrawal/parameter_resource_defs/early_withdrawal_percentage_fee.resource.yaml
    optional: false
    triggers_pre_parameter_change_hook: false
    triggers_post_parameter_change_hook: false
    description: ""
    drives: ""
  - id: "&{maximum_withdrawal_percentage_limit}"
    clu_id: maximum_withdrawal_percentage_limit
    constant: MAXIMUM_WITHDRAWAL_PERCENTAGE_LIMIT_PARAM
    ownership: owned
    owner_feature: deposit.fees.withdrawal.early_withdrawal_fees
    level: TEMPLATE
    constraint: decimal_constraint
    clu_resource: feature_library/src/feature_library/deposit/fees/withdrawal/parameter_resource_defs/maximum_withdrawal_percentage_limit.resource.yaml
    optional: false
    triggers_pre_parameter_change_hook: false
    triggers_post_parameter_change_hook: false
    description: ""
    drives: ""
  - id: "&{fee_free_withdrawal_percentage_limit}"
    clu_id: fee_free_withdrawal_percentage_limit
    constant: FEE_FREE_WITHDRAWAL_PERCENTAGE_LIMIT_PARAM
    ownership: owned
    owner_feature: deposit.fees.withdrawal.early_withdrawal_fees
    level: TEMPLATE
    constraint: decimal_constraint
    clu_resource: feature_library/src/feature_library/deposit/fees/withdrawal/parameter_resource_defs/fee_free_withdrawal_percentage_limit.resource.yaml
    optional: false
    triggers_pre_parameter_change_hook: false
    triggers_post_parameter_change_hook: false
    description: ""
    drives: ""
  - id: "&{denomination}"
    clu_id: denomination
    constant: DENOMINATION_PARAM
    ownership: consumed
    owner_feature: common.denomination
    level: TEMPLATE
    constraint: string_constraint
    clu_resource: feature_library/src/feature_library/common/parameter_resource_defs/denomination.resource.yaml
    optional: false
    triggers_pre_parameter_change_hook: false
    triggers_post_parameter_change_hook: false
    description: ""
    drives: ""
data_fetchers:
  - fetcher_id: withdrawal_fees_pof
    kind: ParametersObservationFetcher
    declared_in: deposit.fees.withdrawal.early_withdrawal_fees
events: []
event_style: static
notifications: []
balance_addresses:
  - INTERNAL_CONTRA
interfaces:
  provides: []
  consumes:
    - DefaultBalanceAdjustment
dependencies:
  features:
    - common.addresses
    - common.balance_utils
    - common.calendar_utils
    - common.denomination
    - common.fetchers
    - common.posting_utils
    - common.state_utils
    - common.utils
    - deposit.interfaces
  used_by: []
tests:
  unit: 1
  simulation: 1
  e2e: 1
traceability:
  business_requirements: []
  used_by_products: []
complete: false
---

# Early Withdrawal Fees

> Generated by `python3 -m fl docs`. Curated prose comes from `feature_library/src/feature_library/deposit/fees/withdrawal/early_withdrawal_fees.okf.yaml`; everything else is derived from the module source. Do not edit by hand.

| Property | Value |
|---|---|
| Module | `feature_library.deposit.fees.withdrawal.early_withdrawal_fees` |
| Domain | deposit |
| Status | undeclared |
| Version | — |
| Hooks | `pre_posting_hook` |
| Source | `feature_library/src/feature_library/deposit/fees/withdrawal/early_withdrawal_fees.py` |

## What it does

_Not yet described._

## Traceability: configuration to outcome

Every input below is a value a bank configures. The diagram shows which function consumes it and which hook turns it into an outcome.

```mermaid
graph LR
  subgraph CONFIG[Configuration inputs]
    direction TB
    p_early_withdrawal_flat_fee["&{early_withdrawal_flat_fee}"]
    p_early_withdrawal_percentage_fee["&{early_withdrawal_percentage_fee}"]
    p_maximum_withdrawal_percentage_limit["&{maximum_withdrawal_percentage_limit}"]
    p_fee_free_withdrawal_percentage_limit["&{fee_free_withdrawal_percentage_limit}"]
    p_denomination["&{denomination}"]
  end
  subgraph DATA[Data fetched at execution]
    direction TB
    d_withdrawal_fees_pof[/"withdrawal_fees_pof\n(ParametersObservationFetcher)"/]
  end
  subgraph FEAT["early_withdrawal_fees"]
    direction TB
    f_notification_type("notification_type()")
    f_get_notification_types("get_notification_types()")
    f_validate("validate()")
    f_handle_withdrawals("handle_withdrawals()")
    f_get_current_withdrawal_amount_default_balance_adjustment("get_current_withdrawal_amount_default_balance_adjustment()")
    f_maximum_withdrawal_limit_attribute_handler("maximum_withdrawal_limit_attribute_handler()")
    f_fee_free_withdrawal_limit_attribute_handler("fee_free_withdrawal_limit_attribute_handler()")
    f_reset_withdrawals_tracker("reset_withdrawals_tracker()")
    f_generate_withdrawal_fee_notification("generate_withdrawal_fee_notification()")
    f_calculate_withdrawal_fee_amounts("calculate_withdrawal_fee_amounts()")
  end
  subgraph HOOKS[Contract hooks]
    direction TB
    h_pre_posting_hook[["pre_posting_hook"]]
  end
  subgraph OUT[Outcomes]
    direction TB
    o_0["Rejection | None"]
    o_1["addresses: INTERNAL_CONTRA"]
  end
  p_early_withdrawal_flat_fee --> f_notification_type
  p_early_withdrawal_percentage_fee --> f_notification_type
  p_maximum_withdrawal_percentage_limit --> f_notification_type
  p_fee_free_withdrawal_percentage_limit --> f_notification_type
  p_denomination --> f_notification_type
  d_withdrawal_fees_pof --> f_notification_type
  f_notification_type --> h_pre_posting_hook
  f_get_notification_types --> h_pre_posting_hook
  f_validate --> h_pre_posting_hook
  f_handle_withdrawals --> h_pre_posting_hook
  f_get_current_withdrawal_amount_default_balance_adjustment --> h_pre_posting_hook
  f_maximum_withdrawal_limit_attribute_handler --> h_pre_posting_hook
  f_fee_free_withdrawal_limit_attribute_handler --> h_pre_posting_hook
  f_reset_withdrawals_tracker --> h_pre_posting_hook
  f_generate_withdrawal_fee_notification --> h_pre_posting_hook
  f_calculate_withdrawal_fee_amounts --> h_pre_posting_hook
  h_pre_posting_hook --> o_0
  h_pre_posting_hook --> o_1
```

## Inputs — parameters

| Reference | Meaning | Hierarchy level | Constraint | Required | CLU resource |
|---|---|---|---|---|---|
| `&{early_withdrawal_flat_fee}` | Triggers pre-parameter change hook? No.  Optional? No. | — | decimal_constraint | required | `feature_library/src/feature_library/deposit/fees/withdrawal/parameter_resource_defs/early_withdrawal_flat_fee.resource.yaml` |
| `&{early_withdrawal_percentage_fee}` | Triggers pre-parameter change hook? No.  Optional? No. | — | decimal_constraint | required | `feature_library/src/feature_library/deposit/fees/withdrawal/parameter_resource_defs/early_withdrawal_percentage_fee.resource.yaml` |
| `&{maximum_withdrawal_percentage_limit}` | Triggers pre-parameter change hook? No.  Optional? No. | — | decimal_constraint | required | `feature_library/src/feature_library/deposit/fees/withdrawal/parameter_resource_defs/maximum_withdrawal_percentage_limit.resource.yaml` |
| `&{fee_free_withdrawal_percentage_limit}` | Triggers pre-parameter change hook? No.  Optional? No. | — | decimal_constraint | required | `feature_library/src/feature_library/deposit/fees/withdrawal/parameter_resource_defs/fee_free_withdrawal_percentage_limit.resource.yaml` |
| `&{denomination}` | _undocumented_ | — | string_constraint | required | `feature_library/src/feature_library/common/parameter_resource_defs/denomination.resource.yaml` |

## Inputs — data fetched at execution

| Fetcher id | Type | Anchor | Filter |
|---|---|---|---|
| `withdrawal_fees_pof` | ParametersObservationFetcher | DefinedDateTime.EFFECTIVE_DATETIME | ParametersFilter(parameter_ids=[p.id for p in expected_parameters]) |

## Public API

| Function | Returns | Purpose |
|---|---|---|
| `notification_type(product_name)` | `str` | Returns a notification type. |
| `get_notification_types(product_name)` | `list[str]` | Generates all the notification types for this Feature module. |
| `get_parameters(vault, param_fetcher_id)` | `dict[str, datetime \| Decimal \| str \| None]` | Retrieves configuration parameters for the withdrawal fees feature. |
| `validate(state, posting_instructions, balance_adjustments, fetchers_config)` | `Rejection \| None` | For use in the pre_posting_hook. |
| `handle_withdrawals(state, posting_instructions, product_name, balance_adjustments, fetchers_config)` | `HandleWithdrawalsResult` | For use in the post_posting_hook. |
| `get_current_withdrawal_amount_default_balance_adjustment(withdrawal_amount)` | `deposit_interfaces.DefaultBalanceAdjustment` | The customer deposited amount is the sum of the DEFAULT balance. |
| `maximum_withdrawal_limit_attribute_handler(vault, hook_arguments, fetchers_config)` | `AttributeHookResult` | Get the maximum withdrawal limit for the derived parameter value. |
| `fee_free_withdrawal_limit_attribute_handler(vault, hook_arguments, fetchers_config)` | `AttributeHookResult` | Get the fee free withdrawal limit for the derived parameter value. |
| `reset_withdrawals_tracker(state, balance_fetcher_id, param_fetcher_id, denomination_param_id)` | `list[CustomInstruction]` | Create postings to net-off the withdrawals tracker balance. |
| `generate_withdrawal_fee_notification(account_id, denomination, withdrawal_amount, flat_fee_amount, percentage_fee_amount, product_name, client_batch_id, precision)` | `AccountNotificationDirective` | Generate the notification containing the respective fee amounts for a withdrawal. |
| `calculate_withdrawal_fee_amounts(state, withdrawal_amount, balance_adjustments, precision)` | `WithdrawalFeeAmounts` | Calculate the flat fee and percentage fee amounts that are chargeable against a withdrawal. |
| `get_customer_deposit_amount(state, balance_adjustments, fetchers_config)` | `Decimal` | Calculate the amount the customer has deposited in the account. |

## Outputs

| Kind | Values | Notes |
|---|---|---|
| Balance addresses | `INTERNAL_CONTRA` | — |

## Composition points

Accepts: `DefaultBalanceAdjustment`

## Where it sits in the library

```mermaid
graph BT
  me_early_withdrawal_fees["early_withdrawal_fees"]:::self
  dep_common_addresses["common.addresses"] --> me_early_withdrawal_fees
  dep_common_balance_utils["common.balance_utils"] --> me_early_withdrawal_fees
  dep_common_calendar_utils["common.calendar_utils"] --> me_early_withdrawal_fees
  dep_common_denomination["common.denomination"] --> me_early_withdrawal_fees
  dep_common_fetchers["common.fetchers"] --> me_early_withdrawal_fees
  dep_common_posting_utils["common.posting_utils"] --> me_early_withdrawal_fees
  dep_common_state_utils["common.state_utils"] --> me_early_withdrawal_fees
  dep_common_utils["common.utils"] --> me_early_withdrawal_fees
  dep_deposit_interfaces["deposit.interfaces"] --> me_early_withdrawal_fees
  classDef self fill:#dbeafe,stroke:#1d4ed8,stroke-width:2px;
  classDef product fill:#dcfce7,stroke:#15803d,stroke-width:2px;
```

## Requirement traceability

_No business requirement is linked to this feature yet, so it cannot be traced back to a stated need._

## Products using it

_None. A feature that no product composes is not yet a proven building block._

## Testing

| Tier | Status | Test modules |
|---|---|---|
| Unit | yes | 1 |
| Simulation | yes | 1 |
| End-to-end | yes | 1 |

<!-- generated:end -->
