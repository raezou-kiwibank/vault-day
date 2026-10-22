---
type: Vault Feature
okf_version: "0.2"
profile: https://thoughtmachine.example/fde/schemas/feature-knowledge-bundle/1.0.json
profile_version: 1.0.0
title: Minimum Monthly Balance
description: Smart Contract feature deposit.fees.minimum_monthly_balance.
status: draft
tags:
  - deposit
identity:
  id: feature_library.deposit.fees.minimum_monthly_balance
  module: feature_library.deposit.fees.minimum_monthly_balance
  source_path: feature_library/src/feature_library/deposit/fees/minimum_monthly_balance.py
  kind: primary
  domain: deposit
version:
  library_version: 1.0.0
  content_hash: sha256:bf58d7c2440750c8ab8739f25d1d4bca338a9cb9ff33b97ff5be489a9abb9e0f
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
  - name: apply_fees
    returns: list[CustomInstruction]
    reads_parameters:
      - "&{denomination}"
parameters:
  - id: "&{minimum_balance_fee}"
    clu_id: minimum_balance_fee
    constant: MINIMUM_BALANCE_FEE_PARAM
    ownership: owned
    owner_feature: deposit.fees.minimum_monthly_balance
    level: TEMPLATE
    constraint: decimal_constraint
    clu_resource: feature_library/src/feature_library/deposit/fees/parameter_resource_defs/minimum_balance_fee.resource.yaml
    optional: false
    triggers_pre_parameter_change_hook: false
    triggers_post_parameter_change_hook: false
    description: ""
    drives: ""
  - id: "&{minimum_balance_threshold_by_tier}"
    clu_id: minimum_balance_threshold_by_tier
    constant: MINIMUM_BALANCE_THRESHOLD_BY_TIER_PARAM
    ownership: owned
    owner_feature: deposit.fees.minimum_monthly_balance
    level: TEMPLATE
    constraint: string_constraint
    clu_resource: feature_library/src/feature_library/deposit/fees/parameter_resource_defs/minimum_balance_threshold_by_tier.resource.yaml
    optional: false
    triggers_pre_parameter_change_hook: false
    triggers_post_parameter_change_hook: false
    description: ""
    drives: ""
  - id: "&{minimum_balance_fee_income_account}"
    clu_id: minimum_balance_fee_income_account
    constant: MINIMUM_BALANCE_FEE_INCOME_ACCOUNT_PARAM
    ownership: owned
    owner_feature: deposit.fees.minimum_monthly_balance
    level: TEMPLATE
    constraint: account_constraint
    clu_resource: feature_library/src/feature_library/deposit/fees/parameter_resource_defs/minimum_balance_fee_income_account.resource.yaml
    optional: false
    triggers_pre_parameter_change_hook: false
    triggers_post_parameter_change_hook: false
    description: ""
    drives: ""
  - id: "&{minimum_balance_fee_application_day}"
    clu_id: minimum_balance_fee_application_day
    constant: MINIMUM_BALANCE_FEE_APPLICATION_DAY_PARAM
    ownership: owned
    owner_feature: deposit.fees.minimum_monthly_balance
    level: TEMPLATE
    constraint: decimal_constraint
    clu_resource: feature_library/src/feature_library/deposit/fees/parameter_resource_defs/minimum_balance_fee_application_day.resource.yaml
    optional: false
    triggers_pre_parameter_change_hook: false
    triggers_post_parameter_change_hook: false
    description: ""
    drives: ""
  - id: "&{minimum_balance_fee_application_time}"
    clu_id: minimum_balance_fee_application_time
    constant: MINIMUM_BALANCE_FEE_APPLICATION_TIME_PARAM
    ownership: owned
    owner_feature: deposit.fees.minimum_monthly_balance
    level: TEMPLATE
    constraint: string_constraint
    clu_resource: feature_library/src/feature_library/deposit/fees/parameter_resource_defs/minimum_balance_fee_application_time.resource.yaml
    optional: false
    triggers_pre_parameter_change_hook: false
    triggers_post_parameter_change_hook: false
    description: ""
    drives: ""
  - id: "&{partial_minimum_balance_fee_application_enabled}"
    clu_id: partial_minimum_balance_fee_application_enabled
    constant: MINIMUM_BALANCE_PARTIAL_FEE_ENABLED_PARAM
    ownership: owned
    owner_feature: deposit.fees.minimum_monthly_balance
    level: TEMPLATE
    constraint: enumeration_constraint
    clu_resource: feature_library/src/feature_library/deposit/fees/parameter_resource_defs/partial_minimum_balance_fee_application_enabled.resource.yaml
    optional: true
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
  - fetcher_id: minimum_balance_fee_pof
    kind: ParametersObservationFetcher
    declared_in: deposit.fees.minimum_monthly_balance
events:
  - APPLY_MINIMUM_BALANCE_FEE
event_style: static
notifications: []
balance_addresses: []
interfaces:
  provides:
    - PartialFeeCollection
  consumes:
    - AvailableBalance
dependencies:
  features:
    - common.balance_utils
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

# Minimum Monthly Balance

> Generated by `python3 -m fl docs`. Curated prose comes from `feature_library/src/feature_library/deposit/fees/minimum_monthly_balance.okf.yaml`; everything else is derived from the module source. Do not edit by hand.

| Property | Value |
|---|---|
| Module | `feature_library.deposit.fees.minimum_monthly_balance` |
| Domain | deposit |
| Status | undeclared |
| Version | — |
| Hooks | `activation_hook`, `scheduled_event_hook` |
| Source | `feature_library/src/feature_library/deposit/fees/minimum_monthly_balance.py` |

## What it does

_Not yet described._

## Traceability: configuration to outcome

Every input below is a value a bank configures. The diagram shows which function consumes it and which hook turns it into an outcome.

```mermaid
graph LR
  subgraph CONFIG[Configuration inputs]
    direction TB
    p_minimum_balance_fee["&{minimum_balance_fee}"]
    p_minimum_balance_threshold_by_tier["&{minimum_balance_threshold_by_tier}"]
    p_minimum_balance_fee_income_account["&{minimum_balance_fee_income_account}"]
    p_minimum_balance_fee_application_day["&{minimum_balance_fee_application_day}"]
    p_minimum_balance_fee_application_time["&{minimum_balance_fee_application_time}"]
    p_partial_minimum_balance_fee_application_enabled["&{partial_minimum_balance_fee_application_enabled}"]
    p_account_tier["&{account_tier}"]
    p_denomination["&{denomination}"]
  end
  subgraph DATA[Data fetched at execution]
    direction TB
    d_all_balances_et_bof[/"all_balances_et_bof\n(BalancesObservationFetcher)"/]
    d_minimum_balance_fee_pof[/"minimum_balance_fee_pof\n(ParametersObservationFetcher)"/]
  end
  subgraph FEAT["minimum_monthly_balance"]
    direction TB
    f_get_scheduled_events("get_scheduled_events()")
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
    o_2["scheduled events: APPLY_MINIMUM_BALANCE_FEE"]
  end
  p_denomination --> f_apply_fees
  p_minimum_balance_fee --> f_get_scheduled_events
  p_minimum_balance_threshold_by_tier --> f_get_scheduled_events
  p_minimum_balance_fee_income_account --> f_get_scheduled_events
  p_minimum_balance_fee_application_day --> f_get_scheduled_events
  p_minimum_balance_fee_application_time --> f_get_scheduled_events
  p_partial_minimum_balance_fee_application_enabled --> f_get_scheduled_events
  p_account_tier --> f_get_scheduled_events
  d_all_balances_et_bof --> f_get_scheduled_events
  d_minimum_balance_fee_pof --> f_get_scheduled_events
  f_get_scheduled_events --> h_activation_hook
  f_get_scheduled_events --> h_scheduled_event_hook
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
| `&{minimum_balance_fee}` | Triggers pre-parameter change hook? No.  Optional? No. | — | decimal_constraint | required | `feature_library/src/feature_library/deposit/fees/parameter_resource_defs/minimum_balance_fee.resource.yaml` |
| `&{minimum_balance_threshold_by_tier}` | Triggers pre-parameter change hook? No.  Optional? No. | — | string_constraint | required | `feature_library/src/feature_library/deposit/fees/parameter_resource_defs/minimum_balance_threshold_by_tier.resource.yaml` |
| `&{minimum_balance_fee_income_account}` | Triggers pre-parameter change hook? No.  Optional? No. | — | account_constraint | required | `feature_library/src/feature_library/deposit/fees/parameter_resource_defs/minimum_balance_fee_income_account.resource.yaml` |
| `&{minimum_balance_fee_application_day}` | Triggers pre-parameter change hook? No.  Optional? No. | — | decimal_constraint | required | `feature_library/src/feature_library/deposit/fees/parameter_resource_defs/minimum_balance_fee_application_day.resource.yaml` |
| `&{minimum_balance_fee_application_time}` | Format "HH:mm:ss".  Triggers pre-parameter change hook? No.  Optional? No. | — | string_constraint | required | `feature_library/src/feature_library/deposit/fees/parameter_resource_defs/minimum_balance_fee_application_time.resource.yaml` |
| `&{partial_minimum_balance_fee_application_enabled}` | Triggers pre-parameter change hook? No.  Optional? No. | — | enumeration_constraint | optional | `feature_library/src/feature_library/deposit/fees/parameter_resource_defs/partial_minimum_balance_fee_application_enabled.resource.yaml` |
| `&{account_tier}` | Triggers pre-parameter change hook? No.  Optional? No. | — | string_constraint | optional | `feature_library/src/feature_library/deposit/fees/parameter_resource_defs/account_tier.resource.yaml` |
| `&{denomination}` | _undocumented_ | — | string_constraint | required | `feature_library/src/feature_library/common/parameter_resource_defs/denomination.resource.yaml` |

## Inputs — data fetched at execution

| Fetcher id | Type | Anchor | Filter |
|---|---|---|---|
| `all_balances_et_bof` | BalancesObservationFetcher | DefinedDateTime.EFFECTIVE_DATETIME | — |
| `minimum_balance_fee_pof` | ParametersObservationFetcher | DefinedDateTime.EFFECTIVE_DATETIME | ParametersFilter(parameter_ids=[p.id for p in expected_parameters]) |

## Public API

| Function | Returns | Purpose |
|---|---|---|
| `get_parameters(vault, param_fetcher_id)` | `dict[str, datetime \| Decimal \| str \| None]` | Retrieves configuration parameters for the minimum monthly balance fee feature. |
| `get_scheduled_events(state, fetchers_config)` | `dict[str, ScheduledEvent]` | Returns the scheduled events for applying the minimum monthly balance fee. |
| `apply_fees(state, account_type, fetchers_config, available_balance_feature)` | `list[CustomInstruction]` | Calculates and applies minimum monthly balance fees if mean balance is below threshold. |

## Outputs

| Kind | Values | Notes |
|---|---|---|
| Scheduled events | `APPLY_MINIMUM_BALANCE_FEE` | static |

## Composition points

| Provides interface | As constant | Members |
|---|---|---|
| `PartialFeeCollection` | `PARTIAL_FEE_DETAILS` | `outstanding_fee_address`, `fee_type`, `internal_account_parameter_id` |

Accepts: `AvailableBalance`

## Where it sits in the library

```mermaid
graph BT
  me_minimum_monthly_balance["minimum_monthly_balance"]:::self
  dep_common_balance_utils["common.balance_utils"] --> me_minimum_monthly_balance
  dep_common_date_and_time["common.date_and_time"] --> me_minimum_monthly_balance
  dep_common_denomination["common.denomination"] --> me_minimum_monthly_balance
  dep_common_fetchers["common.fetchers"] --> me_minimum_monthly_balance
  dep_common_posting_utils["common.posting_utils"] --> me_minimum_monthly_balance
  dep_common_state_utils["common.state_utils"] --> me_minimum_monthly_balance
  dep_common_utils["common.utils"] --> me_minimum_monthly_balance
  dep_deposit_common["deposit.common"] --> me_minimum_monthly_balance
  dep_deposit_fees_partial_fee["deposit.fees.partial_fee"] --> me_minimum_monthly_balance
  dep_deposit_interfaces["deposit.interfaces"] --> me_minimum_monthly_balance
  me_minimum_monthly_balance ==> prod_corporate_current_account["corporate_current_account"]:::product
  me_minimum_monthly_balance ==> prod_personal_current_account["personal_current_account"]:::product
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
