---
type: Vault Feature
okf_version: "0.2"
profile: https://thoughtmachine.example/fde/schemas/feature-knowledge-bundle/1.0.json
profile_version: 1.0.0
title: Interest Application
description: Smart Contract feature deposit.interest.interest_application.
status: draft
tags:
  - deposit
identity:
  id: feature_library.deposit.interest.interest_application
  module: feature_library.deposit.interest.interest_application
  source_path: feature_library/src/feature_library/deposit/interest/interest_application.py
  kind: primary
  domain: deposit
version:
  library_version: 1.0.0
  content_hash: sha256:e2da75a12af5d271a066c595f1ebef6d2da3ca66c7c43238e1f5a93ade37d296
generated:
  by: process:fl/0.1.0
hooks:
  - activation_hook
  - scheduled_event_hook
entry_points:
  - name: event_types
    returns: list[SmartContractEventType]
    reads_parameters: []
  - name: get_parameters
    returns: dict[str, datetime | Decimal | str | None]
    reads_parameters: []
  - name: get_scheduled_events
    returns: dict[str, ScheduledEvent]
    reads_parameters:
      - "&{denomination}"
  - name: schedule_logic
    returns: common_tuples.ScheduleLogicResult
    reads_parameters: []
  - name: update_next_schedule_execution
    returns: UpdateAccountEventTypeDirective | None
    reads_parameters: []
parameters:
  - id: "&{interest_application_day}"
    clu_id: interest_application_day
    constant: INTEREST_APPLICATION_DAY_PARAM
    ownership: owned
    owner_feature: deposit.interest.interest_application
    level: TEMPLATE
    constraint: decimal_constraint
    clu_resource: feature_library/src/feature_library/deposit/interest/parameter_resource_defs/interest_application_day.resource.yaml
    optional: false
    triggers_pre_parameter_change_hook: false
    triggers_post_parameter_change_hook: false
    description: ""
    drives: ""
  - id: "&{interest_application_frequency}"
    clu_id: interest_application_frequency
    constant: INTEREST_APPLICATION_FREQUENCY_PARAM
    ownership: owned
    owner_feature: deposit.interest.interest_application
    level: TEMPLATE
    constraint: enumeration_constraint
    clu_resource: feature_library/src/feature_library/deposit/interest/parameter_resource_defs/interest_application_frequency.resource.yaml
    optional: false
    triggers_pre_parameter_change_hook: false
    triggers_post_parameter_change_hook: false
    description: ""
    drives: ""
  - id: "&{interest_application_time}"
    clu_id: interest_application_time
    constant: INTEREST_APPLICATION_TIME_PARAM
    ownership: owned
    owner_feature: deposit.interest.interest_application
    level: TEMPLATE
    constraint: string_constraint
    clu_resource: feature_library/src/feature_library/deposit/interest/parameter_resource_defs/interest_application_time.resource.yaml
    optional: false
    triggers_pre_parameter_change_hook: false
    triggers_post_parameter_change_hook: false
    description: ""
    drives: ""
  - id: "&{application_precision}"
    clu_id: application_precision
    constant: APPLICATION_PRECISION_PARAM
    ownership: owned
    owner_feature: deposit.interest.interest_application
    level: TEMPLATE
    constraint: decimal_constraint
    clu_resource: feature_library/src/feature_library/common/parameter_resource_defs/application_precision.resource.yaml
    optional: false
    triggers_pre_parameter_change_hook: false
    triggers_post_parameter_change_hook: false
    description: ""
    drives: ""
  - id: "&{interest_paid_account}"
    clu_id: interest_paid_account
    constant: INTEREST_PAID_ACCOUNT_PARAM
    ownership: owned
    owner_feature: deposit.interest.interest_application
    level: TEMPLATE
    constraint: account_constraint
    clu_resource: feature_library/src/feature_library/deposit/interest/parameter_resource_defs/interest_paid_account.resource.yaml
    optional: false
    triggers_pre_parameter_change_hook: false
    triggers_post_parameter_change_hook: false
    description: ""
    drives: ""
  - id: "&{interest_received_account}"
    clu_id: interest_received_account
    constant: INTEREST_RECEIVED_ACCOUNT_PARAM
    ownership: owned
    owner_feature: deposit.interest.interest_application
    level: TEMPLATE
    constraint: account_constraint
    clu_resource: feature_library/src/feature_library/deposit/interest/parameter_resource_defs/interest_received_account.resource.yaml
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
  - fetcher_id: interest_application_params_et_pof
    kind: ParametersObservationFetcher
    declared_in: deposit.interest.interest_application
events:
  - APPLY_INTEREST
event_style: factory
notifications: []
balance_addresses:
  - ACCRUED_INTEREST_PAYABLE
  - ACCRUED_INTEREST_RECEIVABLE
interfaces:
  provides: []
  consumes: []
dependencies:
  features:
    - common.accrual_utils
    - common.balance_utils
    - common.denomination
    - common.fetchers
    - common.posting_utils
    - common.schedule_utils
    - common.state_utils
    - common.tuples
    - common.utils
    - deposit.addresses
    - deposit.interest.interest_accrual
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

# Interest Application

> Generated by `python3 -m fl docs`. Curated prose comes from `feature_library/src/feature_library/deposit/interest/interest_application.okf.yaml`; everything else is derived from the module source. Do not edit by hand.

| Property | Value |
|---|---|
| Module | `feature_library.deposit.interest.interest_application` |
| Domain | deposit |
| Status | undeclared |
| Version | — |
| Hooks | `activation_hook`, `scheduled_event_hook` |
| Source | `feature_library/src/feature_library/deposit/interest/interest_application.py` |

## What it does

_Not yet described._

## Traceability: configuration to outcome

Every input below is a value a bank configures. The diagram shows which function consumes it and which hook turns it into an outcome.

```mermaid
graph LR
  subgraph CONFIG[Configuration inputs]
    direction TB
    p_interest_application_day["&{interest_application_day}"]
    p_interest_application_frequency["&{interest_application_frequency}"]
    p_interest_application_time["&{interest_application_time}"]
    p_application_precision["&{application_precision}"]
    p_interest_paid_account["&{interest_paid_account}"]
    p_interest_received_account["&{interest_received_account}"]
    p_denomination["&{denomination}"]
  end
  subgraph DATA[Data fetched at execution]
    direction TB
    d_all_balances_et_bof[/"all_balances_et_bof\n(BalancesObservationFetcher)"/]
    d_interest_application_params_et_pof[/"interest_application_params_et_pof\n(ParametersObservationFetcher)"/]
  end
  subgraph FEAT["interest_application"]
    direction TB
    f_event_types("event_types()")
    f_get_scheduled_events("get_scheduled_events()")
    f_schedule_logic("schedule_logic()")
    f_update_next_schedule_execution("update_next_schedule_execution()")
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
    o_2["scheduled events: APPLY_INTEREST"]
    o_3["addresses: ACCRUED_INTEREST_PAYABLE, ACCRUED_INTEREST_RECEIVABLE"]
  end
  p_denomination --> f_get_scheduled_events
  p_interest_application_day --> f_event_types
  p_interest_application_frequency --> f_event_types
  p_interest_application_time --> f_event_types
  p_application_precision --> f_event_types
  p_interest_paid_account --> f_event_types
  p_interest_received_account --> f_event_types
  d_all_balances_et_bof --> f_event_types
  d_interest_application_params_et_pof --> f_event_types
  f_event_types --> h_activation_hook
  f_event_types --> h_scheduled_event_hook
  f_get_scheduled_events --> h_activation_hook
  f_get_scheduled_events --> h_scheduled_event_hook
  f_schedule_logic --> h_activation_hook
  f_schedule_logic --> h_scheduled_event_hook
  f_update_next_schedule_execution --> h_activation_hook
  f_update_next_schedule_execution --> h_scheduled_event_hook
  h_activation_hook --> o_0
  h_scheduled_event_hook --> o_0
  h_activation_hook --> o_1
  h_scheduled_event_hook --> o_1
  h_activation_hook --> o_2
  h_scheduled_event_hook --> o_2
  h_activation_hook --> o_3
  h_scheduled_event_hook --> o_3
```

## Inputs — parameters

| Reference | Meaning | Hierarchy level | Constraint | Required | CLU resource |
|---|---|---|---|---|---|
| `&{interest_application_day}` | _undocumented_ | — | decimal_constraint | required | `feature_library/src/feature_library/deposit/interest/parameter_resource_defs/interest_application_day.resource.yaml` |
| `&{interest_application_frequency}` | _undocumented_ | — | enumeration_constraint | required | `feature_library/src/feature_library/deposit/interest/parameter_resource_defs/interest_application_frequency.resource.yaml` |
| `&{interest_application_time}` | _undocumented_ | — | string_constraint | required | `feature_library/src/feature_library/deposit/interest/parameter_resource_defs/interest_application_time.resource.yaml` |
| `&{application_precision}` | _undocumented_ | — | decimal_constraint | required | `feature_library/src/feature_library/common/parameter_resource_defs/application_precision.resource.yaml` |
| `&{interest_paid_account}` | _undocumented_ | — | account_constraint | required | `feature_library/src/feature_library/deposit/interest/parameter_resource_defs/interest_paid_account.resource.yaml` |
| `&{interest_received_account}` | _undocumented_ | — | account_constraint | required | `feature_library/src/feature_library/deposit/interest/parameter_resource_defs/interest_received_account.resource.yaml` |
| `&{denomination}` | _undocumented_ | — | string_constraint | required | `feature_library/src/feature_library/common/parameter_resource_defs/denomination.resource.yaml` |

## Inputs — data fetched at execution

| Fetcher id | Type | Anchor | Filter |
|---|---|---|---|
| `all_balances_et_bof` | BalancesObservationFetcher | DefinedDateTime.EFFECTIVE_DATETIME | — |
| `interest_application_params_et_pof` | ParametersObservationFetcher | DefinedDateTime.EFFECTIVE_DATETIME | ParametersFilter(parameter_ids=[p.id for p in expected_parameters]) |

## Public API

| Function | Returns | Purpose |
|---|---|---|
| `event_types(product_name)` | `list[SmartContractEventType]` | Returns a list of SmartContractEventTypes for the interest application feature. |
| `get_parameters(vault, param_fetcher_id)` | `dict[str, datetime \| Decimal \| str \| None]` | Retrieves parameters for the interest application feature from the vault. |
| `get_scheduled_events(state, reference_datetime, fetchers_config)` | `dict[str, ScheduledEvent]` | Creates execution schedules for interest application. |
| `schedule_logic(state, account_type, application_fetchers_config, accrual_fetchers_config, interest_types)` | `common_tuples.ScheduleLogicResult` | Creates the posting instructions to consolidate accrued interest. |
| `update_next_schedule_execution(state)` | `UpdateAccountEventTypeDirective \| None` | Update next scheduled execution. |

## Outputs

| Kind | Values | Notes |
|---|---|---|
| Scheduled events | `APPLY_INTEREST` | per-product factory |
| Balance addresses | `ACCRUED_INTEREST_PAYABLE`, `ACCRUED_INTEREST_RECEIVABLE` | — |

## Where it sits in the library

```mermaid
graph BT
  me_interest_application["interest_application"]:::self
  dep_common_accrual_utils["common.accrual_utils"] --> me_interest_application
  dep_common_balance_utils["common.balance_utils"] --> me_interest_application
  dep_common_denomination["common.denomination"] --> me_interest_application
  dep_common_fetchers["common.fetchers"] --> me_interest_application
  dep_common_posting_utils["common.posting_utils"] --> me_interest_application
  dep_common_schedule_utils["common.schedule_utils"] --> me_interest_application
  dep_common_state_utils["common.state_utils"] --> me_interest_application
  dep_common_tuples["common.tuples"] --> me_interest_application
  dep_common_utils["common.utils"] --> me_interest_application
  dep_deposit_addresses["deposit.addresses"] --> me_interest_application
  dep_deposit_interest_interest_accrual["deposit.interest.interest_accrual"] --> me_interest_application
  me_interest_application ==> prod_corporate_current_account["corporate_current_account"]:::product
  me_interest_application ==> prod_personal_current_account["personal_current_account"]:::product
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
