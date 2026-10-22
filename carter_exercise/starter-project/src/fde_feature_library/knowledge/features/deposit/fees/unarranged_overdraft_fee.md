---
type: Vault Feature
okf_version: "0.2"
profile: https://thoughtmachine.example/fde/schemas/feature-knowledge-bundle/1.0.json
profile_version: 1.0.0
title: Unarranged Overdraft Fee
description: Smart Contract feature deposit.fees.unarranged_overdraft_fee.
status: draft
tags:
  - deposit
identity:
  id: feature_library.deposit.fees.unarranged_overdraft_fee
  module: feature_library.deposit.fees.unarranged_overdraft_fee
  source_path: feature_library/src/feature_library/deposit/fees/unarranged_overdraft_fee.py
  kind: primary
  domain: deposit
version:
  library_version: 1.0.0
  content_hash: sha256:621ce8597d57d2f4bad12e0d92b6dbf77342d1ef13812996d3af5701101dd27d
generated:
  by: process:fl/0.1.0
hooks:
  - activation_hook
  - scheduled_event_hook
entry_points:
  - name: get_parameters
    returns: dict[str, datetime | Decimal | str | None]
    reads_parameters: []
  - name: get_scheduled_events
    returns: dict[str, ScheduledEvent]
    reads_parameters: []
  - name: accrue_fees
    returns: list[CustomInstruction]
    reads_parameters: []
  - name: apply_fees
    returns: list[CustomInstruction]
    reads_parameters: []
parameters:
  - id: "&{unarranged_overdraft_fee}"
    clu_id: unarranged_overdraft_fee
    constant: UNARRANGED_OVERDRAFT_FEE_PARAM
    ownership: owned
    owner_feature: deposit.fees.unarranged_overdraft_fee
    level: TEMPLATE
    constraint: decimal_constraint
    clu_resource: feature_library/src/feature_library/deposit/fees/parameter_resource_defs/unarranged_overdraft_fee.resource.yaml
    optional: true
    triggers_pre_parameter_change_hook: false
    triggers_post_parameter_change_hook: false
    description: ""
    drives: ""
  - id: "&{unarranged_overdraft_fee_cap}"
    clu_id: unarranged_overdraft_fee_cap
    constant: UNARRANGED_OVERDRAFT_FEE_CAP_PARAM
    ownership: owned
    owner_feature: deposit.fees.unarranged_overdraft_fee
    level: TEMPLATE
    constraint: decimal_constraint
    clu_resource: feature_library/src/feature_library/deposit/fees/parameter_resource_defs/unarranged_overdraft_fee_cap.resource.yaml
    optional: true
    triggers_pre_parameter_change_hook: false
    triggers_post_parameter_change_hook: false
    description: ""
    drives: ""
  - id: "&{unarranged_overdraft_fee_income_account}"
    clu_id: unarranged_overdraft_fee_income_account
    constant: UNARRANGED_OVERDRAFT_FEE_INCOME_ACCOUNT_PARAM
    ownership: owned
    owner_feature: deposit.fees.unarranged_overdraft_fee
    level: TEMPLATE
    constraint: account_constraint
    clu_resource: feature_library/src/feature_library/deposit/fees/parameter_resource_defs/unarranged_overdraft_fee_income_account.resource.yaml
    optional: true
    triggers_pre_parameter_change_hook: false
    triggers_post_parameter_change_hook: false
    description: ""
    drives: ""
  - id: "&{unarranged_overdraft_fee_receivable_account}"
    clu_id: unarranged_overdraft_fee_receivable_account
    constant: UNARRANGED_OVERDRAFT_FEE_RECEIVABLE_ACCOUNT_PARAM
    ownership: owned
    owner_feature: deposit.fees.unarranged_overdraft_fee
    level: TEMPLATE
    constraint: account_constraint
    clu_resource: feature_library/src/feature_library/deposit/fees/parameter_resource_defs/unarranged_overdraft_fee_receivable_account.resource.yaml
    optional: true
    triggers_pre_parameter_change_hook: false
    triggers_post_parameter_change_hook: false
    description: ""
    drives: ""
  - id: "&{arranged_overdraft_amount}"
    clu_id: arranged_overdraft_amount
    constant: ARRANGED_OVERDRAFT_AMOUNT_PARAM
    ownership: consumed
    owner_feature: deposit.fees.overdraft_limit
    level: TEMPLATE
    constraint: decimal_constraint
    clu_resource: feature_library/src/feature_library/deposit/fees/parameter_resource_defs/arranged_overdraft_amount.resource.yaml
    optional: true
    triggers_pre_parameter_change_hook: false
    triggers_post_parameter_change_hook: false
    description: ""
    drives: ""
  - id: "&{unarranged_overdraft_amount}"
    clu_id: unarranged_overdraft_amount
    constant: UNARRANGED_OVERDRAFT_AMOUNT_PARAM
    ownership: consumed
    owner_feature: deposit.fees.overdraft_limit
    level: TEMPLATE
    constraint: decimal_constraint
    clu_resource: feature_library/src/feature_library/deposit/fees/parameter_resource_defs/unarranged_overdraft_amount.resource.yaml
    optional: true
    triggers_pre_parameter_change_hook: false
    triggers_post_parameter_change_hook: false
    description: ""
    drives: ""
  - id: "&{unarranged_overdraft_fee_accrual_time}"
    clu_id: unarranged_overdraft_fee_accrual_time
    constant: UNARRANGED_OVERDRAFT_FEE_ACCRUAL_TIME_PARAM
    ownership: owned
    owner_feature: deposit.fees.unarranged_overdraft_fee
    level: TEMPLATE
    constraint: string_constraint
    clu_resource: feature_library/src/feature_library/deposit/fees/parameter_resource_defs/unarranged_overdraft_fee_accrual_time.resource.yaml
    optional: false
    triggers_pre_parameter_change_hook: false
    triggers_post_parameter_change_hook: false
    description: ""
    drives: ""
  - id: "&{unarranged_overdraft_fee_application_day}"
    clu_id: unarranged_overdraft_fee_application_day
    constant: UNARRANGED_OVERDRAFT_FEE_APPLICATION_DAY_PARAM
    ownership: owned
    owner_feature: deposit.fees.unarranged_overdraft_fee
    level: TEMPLATE
    constraint: decimal_constraint
    clu_resource: feature_library/src/feature_library/deposit/fees/parameter_resource_defs/unarranged_overdraft_fee_application_day.resource.yaml
    optional: false
    triggers_pre_parameter_change_hook: false
    triggers_post_parameter_change_hook: false
    description: ""
    drives: ""
  - id: "&{unarranged_overdraft_fee_application_time}"
    clu_id: unarranged_overdraft_fee_application_time
    constant: UNARRANGED_OVERDRAFT_FEE_APPLICATION_TIME_PARAM
    ownership: owned
    owner_feature: deposit.fees.unarranged_overdraft_fee
    level: TEMPLATE
    constraint: string_constraint
    clu_resource: feature_library/src/feature_library/deposit/fees/parameter_resource_defs/unarranged_overdraft_fee_application_time.resource.yaml
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
  - fetcher_id: all_balances_et_bof
    kind: BalancesObservationFetcher
    declared_in: common.fetchers
  - fetcher_id: unarranged_overdraft_fee_pof
    kind: ParametersObservationFetcher
    declared_in: deposit.fees.unarranged_overdraft_fee
events:
  - ACCRUE_UNARRANGED_OVERDRAFT_FEE
  - APPLY_UNARRANGED_OVERDRAFT_FEE
event_style: static
notifications: []
balance_addresses: []
interfaces:
  provides: []
  consumes: []
dependencies:
  features:
    - common.accrual_utils
    - common.balance_utils
    - common.date_and_time
    - common.denomination
    - common.fetchers
    - common.posting_utils
    - common.state_utils
    - deposit.fees.overdraft_limit
  used_by: []
tests:
  unit: 1
  simulation: 1
  e2e: 1
traceability:
  business_requirements: []
  used_by_products:
    - corporate_current_account
    - personal_current_account
complete: true
---

# Unarranged Overdraft Fee

> Generated by `python3 -m fl docs`. Curated prose comes from `feature_library/src/feature_library/deposit/fees/unarranged_overdraft_fee.okf.yaml`; everything else is derived from the module source. Do not edit by hand.

| Property | Value |
|---|---|
| Module | `feature_library.deposit.fees.unarranged_overdraft_fee` |
| Domain | deposit |
| Status | undeclared |
| Version | — |
| Hooks | `activation_hook`, `scheduled_event_hook` |
| Source | `feature_library/src/feature_library/deposit/fees/unarranged_overdraft_fee.py` |

## What it does

_Not yet described._

## Traceability: configuration to outcome

Every input below is a value a bank configures. The diagram shows which function consumes it and which hook turns it into an outcome.

```mermaid
graph LR
  subgraph CONFIG[Configuration inputs]
    direction TB
    p_unarranged_overdraft_fee["&{unarranged_overdraft_fee}"]
    p_unarranged_overdraft_fee_cap["&{unarranged_overdraft_fee_cap}"]
    p_unarranged_overdraft_fee_income_account["&{unarranged_overdraft_fee_income_account}"]
    p_unarranged_overdraft_fee_receivable_account["&{unarranged_overdraft_fee_receivable_account}"]
    p_arranged_overdraft_amount["&{arranged_overdraft_amount}"]
    p_unarranged_overdraft_amount["&{unarranged_overdraft_amount}"]
    p_unarranged_overdraft_fee_accrual_time["&{unarranged_overdraft_fee_accrual_time}"]
    p_unarranged_overdraft_fee_application_day["&{unarranged_overdraft_fee_application_day}"]
    p_unarranged_overdraft_fee_application_time["&{unarranged_overdraft_fee_application_time}"]
    p_denomination["&{denomination}"]
  end
  subgraph DATA[Data fetched at execution]
    direction TB
    d_all_balances_et_bof[/"all_balances_et_bof\n(BalancesObservationFetcher)"/]
    d_unarranged_overdraft_fee_pof[/"unarranged_overdraft_fee_pof\n(ParametersObservationFetcher)"/]
  end
  subgraph FEAT["unarranged_overdraft_fee"]
    direction TB
    f_get_scheduled_events("get_scheduled_events()")
    f_accrue_fees("accrue_fees()")
    f_apply_fees("apply_fees()")
  end
  subgraph HOOKS[Contract hooks]
    direction TB
    h_activation_hook[["activation_hook"]]
    h_scheduled_event_hook[["scheduled_event_hook"]]
  end
  subgraph OUT[Outcomes]
    direction TB
    o_0["ScheduledEvent map"]
    o_1["CustomInstruction[] / directives"]
    o_2["scheduled events: ACCRUE_UNARRANGED_OVERDRAFT_FEE, APPLY_UNARRANGED_OVERDRAFT_FEE"]
  end
  p_unarranged_overdraft_fee --> f_get_scheduled_events
  p_unarranged_overdraft_fee_cap --> f_get_scheduled_events
  p_unarranged_overdraft_fee_income_account --> f_get_scheduled_events
  p_unarranged_overdraft_fee_receivable_account --> f_get_scheduled_events
  p_arranged_overdraft_amount --> f_get_scheduled_events
  p_unarranged_overdraft_amount --> f_get_scheduled_events
  p_unarranged_overdraft_fee_accrual_time --> f_get_scheduled_events
  p_unarranged_overdraft_fee_application_day --> f_get_scheduled_events
  p_unarranged_overdraft_fee_application_time --> f_get_scheduled_events
  p_denomination --> f_get_scheduled_events
  d_all_balances_et_bof --> f_get_scheduled_events
  d_unarranged_overdraft_fee_pof --> f_get_scheduled_events
  f_get_scheduled_events --> h_activation_hook
  f_get_scheduled_events --> h_scheduled_event_hook
  f_accrue_fees --> h_activation_hook
  f_accrue_fees --> h_scheduled_event_hook
  f_apply_fees --> h_activation_hook
  f_apply_fees --> h_scheduled_event_hook
  h_activation_hook --> o_0
  h_scheduled_event_hook --> o_0
  h_activation_hook --> o_1
  h_scheduled_event_hook --> o_1
  h_activation_hook --> o_2
  h_scheduled_event_hook --> o_2
```

## Inputs — parameters

| Reference | Meaning | Hierarchy level | Constraint | Required | CLU resource |
|---|---|---|---|---|---|
| `&{unarranged_overdraft_fee}` | Triggers pre-parameter change hook? No.  Optional? Yes. | — | decimal_constraint | optional | `feature_library/src/feature_library/deposit/fees/parameter_resource_defs/unarranged_overdraft_fee.resource.yaml` |
| `&{unarranged_overdraft_fee_cap}` | Triggers pre-parameter change hook? No.  Optional? Yes. | — | decimal_constraint | optional | `feature_library/src/feature_library/deposit/fees/parameter_resource_defs/unarranged_overdraft_fee_cap.resource.yaml` |
| `&{unarranged_overdraft_fee_income_account}` | Triggers pre-parameter change hook? No.  Optional? Yes. | — | account_constraint | optional | `feature_library/src/feature_library/deposit/fees/parameter_resource_defs/unarranged_overdraft_fee_income_account.resource.yaml` |
| `&{unarranged_overdraft_fee_receivable_account}` | Triggers pre-parameter change hook? No.  Optional? Yes. | — | account_constraint | optional | `feature_library/src/feature_library/deposit/fees/parameter_resource_defs/unarranged_overdraft_fee_receivable_account.resource.yaml` |
| `&{arranged_overdraft_amount}` | Triggers pre-parameter change hook? No.  Optional? Yes. | — | decimal_constraint | optional | `feature_library/src/feature_library/deposit/fees/parameter_resource_defs/arranged_overdraft_amount.resource.yaml` |
| `&{unarranged_overdraft_amount}` | Triggers pre-parameter change hook? No.  Optional? Yes. | — | decimal_constraint | optional | `feature_library/src/feature_library/deposit/fees/parameter_resource_defs/unarranged_overdraft_amount.resource.yaml` |
| `&{unarranged_overdraft_fee_accrual_time}` | Format "HH:mm:ss".  Triggers pre-parameter change hook? No.  Optional? No. | — | string_constraint | required | `feature_library/src/feature_library/deposit/fees/parameter_resource_defs/unarranged_overdraft_fee_accrual_time.resource.yaml` |
| `&{unarranged_overdraft_fee_application_day}` | Triggers pre-parameter change hook? No.  Optional? No. | — | decimal_constraint | required | `feature_library/src/feature_library/deposit/fees/parameter_resource_defs/unarranged_overdraft_fee_application_day.resource.yaml` |
| `&{unarranged_overdraft_fee_application_time}` | Format "HH:mm:ss".  Triggers pre-parameter change hook? No.  Optional? No. | — | string_constraint | required | `feature_library/src/feature_library/deposit/fees/parameter_resource_defs/unarranged_overdraft_fee_application_time.resource.yaml` |
| `&{denomination}` | _undocumented_ | — | string_constraint | required | `feature_library/src/feature_library/common/parameter_resource_defs/denomination.resource.yaml` |

## Inputs — data fetched at execution

| Fetcher id | Type | Anchor | Filter |
|---|---|---|---|
| `all_balances_et_bof` | BalancesObservationFetcher | DefinedDateTime.EFFECTIVE_DATETIME | — |
| `unarranged_overdraft_fee_pof` | ParametersObservationFetcher | DefinedDateTime.EFFECTIVE_DATETIME | ParametersFilter(parameter_ids=[p.id for p in expected_parameters]) |

## Public API

| Function | Returns | Purpose |
|---|---|---|
| `get_parameters(vault, param_fetcher_id)` | `dict[str, datetime \| Decimal \| str \| None]` | Retrieves configuration parameters for the unarranged overdraft fee feature. |
| `get_scheduled_events(state, fetchers_config)` | `dict[str, ScheduledEvent]` | Returns the scheduled events for accruing and applying unarranged overdraft fees. |
| `accrue_fees(state, account_type, fetchers_config)` | `list[CustomInstruction]` | Accrues the daily unarranged overdraft fee based on the previous day's end-of-day balance. |
| `apply_fees(state, account_type, fetchers_config)` | `list[CustomInstruction]` | Applies the total accrued unarranged overdraft fee to the account. |

## Outputs

| Kind | Values | Notes |
|---|---|---|
| Scheduled events | `ACCRUE_UNARRANGED_OVERDRAFT_FEE`, `APPLY_UNARRANGED_OVERDRAFT_FEE` | static |

## Where it sits in the library

```mermaid
graph BT
  me_unarranged_overdraft_fee["unarranged_overdraft_fee"]:::self
  dep_common_accrual_utils["common.accrual_utils"] --> me_unarranged_overdraft_fee
  dep_common_balance_utils["common.balance_utils"] --> me_unarranged_overdraft_fee
  dep_common_date_and_time["common.date_and_time"] --> me_unarranged_overdraft_fee
  dep_common_denomination["common.denomination"] --> me_unarranged_overdraft_fee
  dep_common_fetchers["common.fetchers"] --> me_unarranged_overdraft_fee
  dep_common_posting_utils["common.posting_utils"] --> me_unarranged_overdraft_fee
  dep_common_state_utils["common.state_utils"] --> me_unarranged_overdraft_fee
  dep_deposit_fees_overdraft_limit["deposit.fees.overdraft_limit"] --> me_unarranged_overdraft_fee
  me_unarranged_overdraft_fee ==> prod_corporate_current_account["corporate_current_account"]:::product
  me_unarranged_overdraft_fee ==> prod_personal_current_account["personal_current_account"]:::product
  classDef self fill:#dbeafe,stroke:#1d4ed8,stroke-width:2px;
  classDef product fill:#dcfce7,stroke:#15803d,stroke-width:2px;
```

## Requirement traceability

_No business requirement is linked to this feature yet, so it cannot be traced back to a stated need._

## Products using it

- `corporate_current_account`
- `personal_current_account`

## Testing

| Tier | Status | Test modules |
|---|---|---|
| Unit | yes | 1 |
| Simulation | yes | 1 |
| End-to-end | yes | 1 |

<!-- generated:end -->
