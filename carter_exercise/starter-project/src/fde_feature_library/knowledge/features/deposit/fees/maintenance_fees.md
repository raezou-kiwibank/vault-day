---
type: Vault Feature
okf_version: "0.2"
profile: https://thoughtmachine.example/fde/schemas/feature-knowledge-bundle/1.0.json
profile_version: 1.0.0
title: Maintenance Fees
description: Smart Contract feature deposit.fees.maintenance_fees.
status: draft
tags:
  - deposit
identity:
  id: feature_library.deposit.fees.maintenance_fees
  module: feature_library.deposit.fees.maintenance_fees
  source_path: feature_library/src/feature_library/deposit/fees/maintenance_fees.py
  kind: primary
  domain: deposit
version:
  library_version: 1.0.0
  content_hash: sha256:802dd37b4891fd8ab26f39277222393be08d57e7a6200359489c3fd6d7951df4
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
    reads_parameters: []
  - name: update_next_annual_schedule_execution
    returns: UpdateAccountEventTypeDirective | None
    reads_parameters: []
  - name: apply_monthly_fee
    returns: list[CustomInstruction]
    reads_parameters: []
  - name: apply_annual_fee
    returns: list[CustomInstruction]
    reads_parameters: []
parameters:
  - id: "&{maintenance_fee_application_day}"
    clu_id: maintenance_fee_application_day
    constant: MAINTENANCE_FEE_APPLICATION_DAY_PARAM
    ownership: owned
    owner_feature: deposit.fees.maintenance_fees
    level: TEMPLATE
    constraint: decimal_constraint
    clu_resource: feature_library/src/feature_library/deposit/fees/parameter_resource_defs/maintenance_fee_application_day.resource.yaml
    optional: false
    triggers_pre_parameter_change_hook: false
    triggers_post_parameter_change_hook: false
    description: ""
    drives: ""
  - id: "&{maintenance_fee_application_time}"
    clu_id: maintenance_fee_application_time
    constant: MAINTENANCE_FEE_APPLICATION_TIME_PARAM
    ownership: owned
    owner_feature: deposit.fees.maintenance_fees
    level: TEMPLATE
    constraint: string_constraint
    clu_resource: feature_library/src/feature_library/deposit/fees/parameter_resource_defs/maintenance_fee_application_time.resource.yaml
    optional: false
    triggers_pre_parameter_change_hook: false
    triggers_post_parameter_change_hook: false
    description: ""
    drives: ""
  - id: "&{monthly_maintenance_fee_by_tier}"
    clu_id: monthly_maintenance_fee_by_tier
    constant: MONTHLY_MAINTENANCE_FEE_BY_TIER_PARAM
    ownership: owned
    owner_feature: deposit.fees.maintenance_fees
    level: TEMPLATE
    constraint: string_constraint
    clu_resource: feature_library/src/feature_library/deposit/fees/parameter_resource_defs/monthly_maintenance_fee_by_tier.resource.yaml
    optional: false
    triggers_pre_parameter_change_hook: false
    triggers_post_parameter_change_hook: false
    description: ""
    drives: ""
  - id: "&{monthly_maintenance_fee_income_account}"
    clu_id: monthly_maintenance_fee_income_account
    constant: MONTHLY_MAINTENANCE_FEE_INCOME_ACCOUNT_PARAM
    ownership: owned
    owner_feature: deposit.fees.maintenance_fees
    level: TEMPLATE
    constraint: account_constraint
    clu_resource: feature_library/src/feature_library/deposit/fees/parameter_resource_defs/monthly_maintenance_fee_income_account.resource.yaml
    optional: false
    triggers_pre_parameter_change_hook: false
    triggers_post_parameter_change_hook: false
    description: ""
    drives: ""
  - id: "&{partial_maintenance_fee_enabled}"
    clu_id: partial_maintenance_fee_enabled
    constant: MONTHLY_MAINTENANCE_FEE_PARTIAL_FEE_ENABLED_PARAM
    ownership: owned
    owner_feature: deposit.fees.maintenance_fees
    level: TEMPLATE
    constraint: enumeration_constraint
    clu_resource: feature_library/src/feature_library/deposit/fees/parameter_resource_defs/partial_maintenance_fee_enabled.resource.yaml
    optional: true
    triggers_pre_parameter_change_hook: false
    triggers_post_parameter_change_hook: false
    description: ""
    drives: ""
  - id: "&{annual_maintenance_fee_by_tier}"
    clu_id: annual_maintenance_fee_by_tier
    constant: ANNUAL_MAINTENANCE_FEE_BY_TIER_PARAM
    ownership: owned
    owner_feature: deposit.fees.maintenance_fees
    level: TEMPLATE
    constraint: string_constraint
    clu_resource: feature_library/src/feature_library/deposit/fees/parameter_resource_defs/annual_maintenance_fee_by_tier.resource.yaml
    optional: false
    triggers_pre_parameter_change_hook: false
    triggers_post_parameter_change_hook: false
    description: ""
    drives: ""
  - id: "&{annual_maintenance_fee_income_account}"
    clu_id: annual_maintenance_fee_income_account
    constant: ANNUAL_MAINTENANCE_FEE_INCOME_ACCOUNT_PARAM
    ownership: owned
    owner_feature: deposit.fees.maintenance_fees
    level: TEMPLATE
    constraint: account_constraint
    clu_resource: feature_library/src/feature_library/deposit/fees/parameter_resource_defs/annual_maintenance_fee_income_account.resource.yaml
    optional: false
    triggers_pre_parameter_change_hook: false
    triggers_post_parameter_change_hook: false
    description: ""
    drives: ""
  - id: "&{account_tier}"
    clu_id: account_tier
    constant: ACCOUNT_TIER_PARAM
    ownership: consumed
    owner_feature: deposit.common
    level: TEMPLATE
    constraint: string_constraint
    clu_resource: feature_library/src/feature_library/deposit/fees/parameter_resource_defs/account_tier.resource.yaml
    optional: true
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
  - fetcher_id: maintenance_fees_pof
    kind: ParametersObservationFetcher
    declared_in: deposit.fees.maintenance_fees
events:
  - event_name
event_style: factory
notifications: []
balance_addresses: []
interfaces:
  provides:
    - PartialFeeCollection
  consumes:
    - AvailableBalance
    - WaiveFeeCondition
dependencies:
  features:
    - common.date_and_time
    - common.denomination
    - common.fetchers
    - common.posting_utils
    - common.state_utils
    - common.utils
    - deposit.common
    - deposit.fees.partial_fee
    - deposit.interfaces
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

# Maintenance Fees

> Generated by `python3 -m fl docs`. Curated prose comes from `feature_library/src/feature_library/deposit/fees/maintenance_fees.okf.yaml`; everything else is derived from the module source. Do not edit by hand.

| Property | Value |
|---|---|
| Module | `feature_library.deposit.fees.maintenance_fees` |
| Domain | deposit |
| Status | undeclared |
| Version | — |
| Hooks | `activation_hook`, `scheduled_event_hook` |
| Source | `feature_library/src/feature_library/deposit/fees/maintenance_fees.py` |

## What it does

_Not yet described._

## Traceability: configuration to outcome

Every input below is a value a bank configures. The diagram shows which function consumes it and which hook turns it into an outcome.

```mermaid
graph LR
  subgraph CONFIG[Configuration inputs]
    direction TB
    p_maintenance_fee_application_day["&{maintenance_fee_application_day}"]
    p_maintenance_fee_application_time["&{maintenance_fee_application_time}"]
    p_monthly_maintenance_fee_by_tier["&{monthly_maintenance_fee_by_tier}"]
    p_monthly_maintenance_fee_income_account["&{monthly_maintenance_fee_income_account}"]
    p_partial_maintenance_fee_enabled["&{partial_maintenance_fee_enabled}"]
    p_annual_maintenance_fee_by_tier["&{annual_maintenance_fee_by_tier}"]
    p_annual_maintenance_fee_income_account["&{annual_maintenance_fee_income_account}"]
    p_account_tier["&{account_tier}"]
    p_denomination["&{denomination}"]
  end
  subgraph DATA[Data fetched at execution]
    direction TB
    d_all_balances_et_bof[/"all_balances_et_bof\n(BalancesObservationFetcher)"/]
    d_maintenance_fees_pof[/"maintenance_fees_pof\n(ParametersObservationFetcher)"/]
  end
  subgraph FEAT["maintenance_fees"]
    direction TB
    f_event_types("event_types()")
    f_get_scheduled_events("get_scheduled_events()")
    f_update_next_annual_schedule_execution("update_next_annual_schedule_execution()")
    f_apply_monthly_fee("apply_monthly_fee()")
    f_apply_annual_fee("apply_annual_fee()")
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
    o_2["scheduled events: event_name"]
  end
  p_maintenance_fee_application_day --> f_event_types
  p_maintenance_fee_application_time --> f_event_types
  p_monthly_maintenance_fee_by_tier --> f_event_types
  p_monthly_maintenance_fee_income_account --> f_event_types
  p_partial_maintenance_fee_enabled --> f_event_types
  p_annual_maintenance_fee_by_tier --> f_event_types
  p_annual_maintenance_fee_income_account --> f_event_types
  p_account_tier --> f_event_types
  p_denomination --> f_event_types
  d_all_balances_et_bof --> f_event_types
  d_maintenance_fees_pof --> f_event_types
  f_event_types --> h_activation_hook
  f_event_types --> h_scheduled_event_hook
  f_get_scheduled_events --> h_activation_hook
  f_get_scheduled_events --> h_scheduled_event_hook
  f_update_next_annual_schedule_execution --> h_activation_hook
  f_update_next_annual_schedule_execution --> h_scheduled_event_hook
  f_apply_monthly_fee --> h_activation_hook
  f_apply_monthly_fee --> h_scheduled_event_hook
  f_apply_annual_fee --> h_activation_hook
  f_apply_annual_fee --> h_scheduled_event_hook
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
| `&{maintenance_fee_application_day}` | Triggers pre-parameter change hook? No.  Optional? No. | — | decimal_constraint | required | `feature_library/src/feature_library/deposit/fees/parameter_resource_defs/maintenance_fee_application_day.resource.yaml` |
| `&{maintenance_fee_application_time}` | Format "HH:mm:ss". Triggers pre-parameter change hook? No.  Optional? No. | — | string_constraint | required | `feature_library/src/feature_library/deposit/fees/parameter_resource_defs/maintenance_fee_application_time.resource.yaml` |
| `&{monthly_maintenance_fee_by_tier}` | Triggers pre-parameter change hook? No.  Optional? No. | — | string_constraint | required | `feature_library/src/feature_library/deposit/fees/parameter_resource_defs/monthly_maintenance_fee_by_tier.resource.yaml` |
| `&{monthly_maintenance_fee_income_account}` | Triggers pre-parameter change hook? No.  Optional? No. | — | account_constraint | required | `feature_library/src/feature_library/deposit/fees/parameter_resource_defs/monthly_maintenance_fee_income_account.resource.yaml` |
| `&{partial_maintenance_fee_enabled}` | Triggers pre-parameter change hook? No.  Optional? Yes. | — | enumeration_constraint | optional | `feature_library/src/feature_library/deposit/fees/parameter_resource_defs/partial_maintenance_fee_enabled.resource.yaml` |
| `&{annual_maintenance_fee_by_tier}` | Triggers pre-parameter change hook? No.  Optional? No. | — | string_constraint | required | `feature_library/src/feature_library/deposit/fees/parameter_resource_defs/annual_maintenance_fee_by_tier.resource.yaml` |
| `&{annual_maintenance_fee_income_account}` | Triggers pre-parameter change hook? No.  Optional? No. | — | account_constraint | required | `feature_library/src/feature_library/deposit/fees/parameter_resource_defs/annual_maintenance_fee_income_account.resource.yaml` |
| `&{account_tier}` | Triggers pre-parameter change hook? No.  Optional? No. | — | string_constraint | optional | `feature_library/src/feature_library/deposit/fees/parameter_resource_defs/account_tier.resource.yaml` |
| `&{denomination}` | _undocumented_ | — | string_constraint | required | `feature_library/src/feature_library/common/parameter_resource_defs/denomination.resource.yaml` |

## Inputs — data fetched at execution

| Fetcher id | Type | Anchor | Filter |
|---|---|---|---|
| `all_balances_et_bof` | BalancesObservationFetcher | DefinedDateTime.EFFECTIVE_DATETIME | — |
| `maintenance_fees_pof` | ParametersObservationFetcher | DefinedDateTime.EFFECTIVE_DATETIME | ParametersFilter(parameter_ids=[p.id for p in expected_parameters]) |

## Public API

| Function | Returns | Purpose |
|---|---|---|
| `event_types(product_name, frequency)` | `list[SmartContractEventType]` | Creates monthly or annual event to apply maintenance fees. |
| `get_parameters(vault, param_fetcher_id)` | `dict[str, datetime \| Decimal \| str \| None]` | Retrieves configuration parameters for the maintenance fees feature. |
| `get_scheduled_events(state, frequency, fetchers_config)` | `dict[str, ScheduledEvent]` | Create monthly or annual scheduled event to apply maintenance fees. |
| `update_next_annual_schedule_execution(state, fetchers_config)` | `UpdateAccountEventTypeDirective \| None` | Update next annual scheduled execution with intended month not february. |
| `apply_monthly_fee(state, account_type, fetchers_config, monthly_fee_waive_conditions, available_balance_feature)` | `list[CustomInstruction]` | Gets monthly maintenance fees and the account where it will be credited. |
| `apply_annual_fee(state, account_type, fetchers_config)` | `list[CustomInstruction]` | Gets annual maintenance fees and the account where it will be credited. |

## Outputs

| Kind | Values | Notes |
|---|---|---|
| Scheduled events | `event_name` | per-product factory |

## Composition points

| Provides interface | As constant | Members |
|---|---|---|
| `PartialFeeCollection` | `PARTIAL_FEE_DETAILS` | `outstanding_fee_address`, `fee_type`, `internal_account_parameter_id` |

Accepts: `AvailableBalance`, `WaiveFeeCondition`

## Where it sits in the library

```mermaid
graph BT
  me_maintenance_fees["maintenance_fees"]:::self
  dep_common_date_and_time["common.date_and_time"] --> me_maintenance_fees
  dep_common_denomination["common.denomination"] --> me_maintenance_fees
  dep_common_fetchers["common.fetchers"] --> me_maintenance_fees
  dep_common_posting_utils["common.posting_utils"] --> me_maintenance_fees
  dep_common_state_utils["common.state_utils"] --> me_maintenance_fees
  dep_common_utils["common.utils"] --> me_maintenance_fees
  dep_deposit_common["deposit.common"] --> me_maintenance_fees
  dep_deposit_fees_partial_fee["deposit.fees.partial_fee"] --> me_maintenance_fees
  dep_deposit_interfaces["deposit.interfaces"] --> me_maintenance_fees
  me_maintenance_fees ==> prod_corporate_current_account["corporate_current_account"]:::product
  me_maintenance_fees ==> prod_personal_current_account["personal_current_account"]:::product
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
