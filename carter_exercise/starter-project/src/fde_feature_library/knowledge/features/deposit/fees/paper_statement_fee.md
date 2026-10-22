---
type: Vault Feature
okf_version: "0.2"
profile: https://thoughtmachine.example/fde/schemas/feature-knowledge-bundle/1.0.json
profile_version: 1.0.0
title: Paper Statement Fee
description: Smart Contract feature deposit.fees.paper_statement_fee.
status: draft
tags:
  - deposit
identity:
  id: feature_library.deposit.fees.paper_statement_fee
  module: feature_library.deposit.fees.paper_statement_fee
  source_path: feature_library/src/feature_library/deposit/fees/paper_statement_fee.py
  kind: primary
  domain: deposit
version:
  library_version: 1.0.0
  content_hash: sha256:f8aabf8a79cff2925a808959da2fdbf59ad48503d242f824cab83891ab3b8828
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
    reads_parameters: []
parameters:
  - id: "&{paper_statement_fee_rate}"
    clu_id: paper_statement_fee_rate
    constant: PAPER_STATEMENT_FEE_RATE_PARAM
    ownership: owned
    owner_feature: deposit.fees.paper_statement_fee
    level: TEMPLATE
    constraint: decimal_constraint
    clu_resource: feature_library/src/feature_library/deposit/fees/parameter_resource_defs/paper_statement_fee_rate.resource.yaml
    optional: false
    triggers_pre_parameter_change_hook: false
    triggers_post_parameter_change_hook: false
    description: ""
    drives: ""
  - id: "&{paper_statement_fee_day}"
    clu_id: paper_statement_fee_day
    constant: PAPER_STATEMENT_FEE_DAY_PARAM
    ownership: owned
    owner_feature: deposit.fees.paper_statement_fee
    level: TEMPLATE
    constraint: decimal_constraint
    clu_resource: feature_library/src/feature_library/deposit/fees/parameter_resource_defs/paper_statement_fee_day.resource.yaml
    optional: false
    triggers_pre_parameter_change_hook: false
    triggers_post_parameter_change_hook: false
    description: ""
    drives: ""
  - id: "&{paper_statement_fee_application_time}"
    clu_id: paper_statement_fee_application_time
    constant: PAPER_STATEMENT_FEE_TIME_PARAM
    ownership: owned
    owner_feature: deposit.fees.paper_statement_fee
    level: TEMPLATE
    constraint: string_constraint
    clu_resource: feature_library/src/feature_library/deposit/fees/parameter_resource_defs/paper_statement_fee_application_time.resource.yaml
    optional: false
    triggers_pre_parameter_change_hook: false
    triggers_post_parameter_change_hook: false
    description: ""
    drives: ""
  - id: "&{paper_statement_fee_income_account}"
    clu_id: paper_statement_fee_income_account
    constant: PAPER_STATEMENT_FEE_INCOME_ACCOUNT_PARAM
    ownership: owned
    owner_feature: deposit.fees.paper_statement_fee
    level: TEMPLATE
    constraint: account_constraint
    clu_resource: feature_library/src/feature_library/deposit/fees/parameter_resource_defs/paper_statement_fee_income_account.resource.yaml
    optional: false
    triggers_pre_parameter_change_hook: false
    triggers_post_parameter_change_hook: false
    description: ""
    drives: ""
  - id: "&{paper_statement_fee_enabled}"
    clu_id: paper_statement_fee_enabled
    constant: PAPER_STATEMENT_FEE_ENABLED_PARAM
    ownership: owned
    owner_feature: deposit.fees.paper_statement_fee
    level: TEMPLATE
    constraint: enumeration_constraint
    clu_resource: feature_library/src/feature_library/deposit/fees/parameter_resource_defs/paper_statement_fee_enabled.resource.yaml
    optional: false
    triggers_pre_parameter_change_hook: false
    triggers_post_parameter_change_hook: false
    description: ""
    drives: ""
  - id: "&{partial_paper_statement_fee_enabled}"
    clu_id: partial_paper_statement_fee_enabled
    constant: PAPER_STATEMENT_FEE_PARTIAL_FEE_ENABLED_PARAM
    ownership: owned
    owner_feature: deposit.fees.paper_statement_fee
    level: TEMPLATE
    constraint: enumeration_constraint
    clu_resource: feature_library/src/feature_library/deposit/fees/parameter_resource_defs/partial_paper_statement_fee_enabled.resource.yaml
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
  - fetcher_id: paper_statement_fee_pof
    kind: ParametersObservationFetcher
    declared_in: deposit.fees.paper_statement_fee
events:
  - APPLY_PAPER_STATEMENT_FEE
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
    - common.date_and_time
    - common.denomination
    - common.fetchers
    - common.posting_utils
    - common.state_utils
    - common.utils
    - deposit.fees.partial_fee
    - deposit.interfaces
  used_by: []
tests:
  unit: 1
  simulation: 1
  e2e: 2
traceability:
  business_requirements: []
  used_by_products:
    - corporate_current_account
complete: true
---

# Paper Statement Fee

> Generated by `python3 -m fl docs`. Curated prose comes from `feature_library/src/feature_library/deposit/fees/paper_statement_fee.okf.yaml`; everything else is derived from the module source. Do not edit by hand.

| Property | Value |
|---|---|
| Module | `feature_library.deposit.fees.paper_statement_fee` |
| Domain | deposit |
| Status | undeclared |
| Version | — |
| Hooks | `activation_hook`, `scheduled_event_hook` |
| Source | `feature_library/src/feature_library/deposit/fees/paper_statement_fee.py` |

## What it does

_Not yet described._

## Traceability: configuration to outcome

Every input below is a value a bank configures. The diagram shows which function consumes it and which hook turns it into an outcome.

```mermaid
graph LR
  subgraph CONFIG[Configuration inputs]
    direction TB
    p_paper_statement_fee_rate["&{paper_statement_fee_rate}"]
    p_paper_statement_fee_day["&{paper_statement_fee_day}"]
    p_paper_statement_fee_application_time["&{paper_statement_fee_application_time}"]
    p_paper_statement_fee_income_account["&{paper_statement_fee_income_account}"]
    p_paper_statement_fee_enabled["&{paper_statement_fee_enabled}"]
    p_partial_paper_statement_fee_enabled["&{partial_paper_statement_fee_enabled}"]
    p_denomination["&{denomination}"]
  end
  subgraph DATA[Data fetched at execution]
    direction TB
    d_all_balances_et_bof[/"all_balances_et_bof\n(BalancesObservationFetcher)"/]
    d_paper_statement_fee_pof[/"paper_statement_fee_pof\n(ParametersObservationFetcher)"/]
  end
  subgraph FEAT["paper_statement_fee"]
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
    o_2["scheduled events: APPLY_PAPER_STATEMENT_FEE"]
  end
  p_paper_statement_fee_rate --> f_get_scheduled_events
  p_paper_statement_fee_day --> f_get_scheduled_events
  p_paper_statement_fee_application_time --> f_get_scheduled_events
  p_paper_statement_fee_income_account --> f_get_scheduled_events
  p_paper_statement_fee_enabled --> f_get_scheduled_events
  p_partial_paper_statement_fee_enabled --> f_get_scheduled_events
  p_denomination --> f_get_scheduled_events
  d_all_balances_et_bof --> f_get_scheduled_events
  d_paper_statement_fee_pof --> f_get_scheduled_events
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
| `&{paper_statement_fee_rate}` | Triggers pre-parameter change hook? No.  Optional? No. | — | decimal_constraint | required | `feature_library/src/feature_library/deposit/fees/parameter_resource_defs/paper_statement_fee_rate.resource.yaml` |
| `&{paper_statement_fee_day}` | Triggers pre-parameter change hook? No.  Optional? No. | — | decimal_constraint | required | `feature_library/src/feature_library/deposit/fees/parameter_resource_defs/paper_statement_fee_day.resource.yaml` |
| `&{paper_statement_fee_application_time}` | Format "HH:mm:ss".  Triggers pre-parameter change hook? No.  Optional? No. | — | string_constraint | required | `feature_library/src/feature_library/deposit/fees/parameter_resource_defs/paper_statement_fee_application_time.resource.yaml` |
| `&{paper_statement_fee_income_account}` | Triggers pre-parameter change hook? No.  Optional? No. | — | account_constraint | required | `feature_library/src/feature_library/deposit/fees/parameter_resource_defs/paper_statement_fee_income_account.resource.yaml` |
| `&{paper_statement_fee_enabled}` | Triggers pre-parameter change hook? No.  Optional? No. | — | enumeration_constraint | required | `feature_library/src/feature_library/deposit/fees/parameter_resource_defs/paper_statement_fee_enabled.resource.yaml` |
| `&{partial_paper_statement_fee_enabled}` | Triggers pre-parameter change hook? No.  Optional? No. | — | enumeration_constraint | required | `feature_library/src/feature_library/deposit/fees/parameter_resource_defs/partial_paper_statement_fee_enabled.resource.yaml` |
| `&{denomination}` | _undocumented_ | — | string_constraint | required | `feature_library/src/feature_library/common/parameter_resource_defs/denomination.resource.yaml` |

## Inputs — data fetched at execution

| Fetcher id | Type | Anchor | Filter |
|---|---|---|---|
| `all_balances_et_bof` | BalancesObservationFetcher | DefinedDateTime.EFFECTIVE_DATETIME | — |
| `paper_statement_fee_pof` | ParametersObservationFetcher | DefinedDateTime.EFFECTIVE_DATETIME | ParametersFilter(parameter_ids=[p.id for p in expected_parameters]) |

## Public API

| Function | Returns | Purpose |
|---|---|---|
| `get_parameters(vault, param_fetcher_id)` | `dict[str, datetime \| Decimal \| str \| None]` | Retrieves configuration parameters for the paper statement fee feature. |
| `get_scheduled_events(state, fetchers_config)` | `dict[str, ScheduledEvent]` | Get scheduled event for paper statement fee application. |
| `apply_fees(state, account_type, available_balance_feature, fetchers_config)` | `list[CustomInstruction]` | Applies the paper statement fee if enabled. |

## Outputs

| Kind | Values | Notes |
|---|---|---|
| Scheduled events | `APPLY_PAPER_STATEMENT_FEE` | static |

## Composition points

| Provides interface | As constant | Members |
|---|---|---|
| `PartialFeeCollection` | `PARTIAL_FEE_DETAILS` | `outstanding_fee_address`, `fee_type`, `internal_account_parameter_id` |

Accepts: `AvailableBalance`

## Where it sits in the library

```mermaid
graph BT
  me_paper_statement_fee["paper_statement_fee"]:::self
  dep_common_date_and_time["common.date_and_time"] --> me_paper_statement_fee
  dep_common_denomination["common.denomination"] --> me_paper_statement_fee
  dep_common_fetchers["common.fetchers"] --> me_paper_statement_fee
  dep_common_posting_utils["common.posting_utils"] --> me_paper_statement_fee
  dep_common_state_utils["common.state_utils"] --> me_paper_statement_fee
  dep_common_utils["common.utils"] --> me_paper_statement_fee
  dep_deposit_fees_partial_fee["deposit.fees.partial_fee"] --> me_paper_statement_fee
  dep_deposit_interfaces["deposit.interfaces"] --> me_paper_statement_fee
  me_paper_statement_fee ==> prod_corporate_current_account["corporate_current_account"]:::product
  classDef self fill:#dbeafe,stroke:#1d4ed8,stroke-width:2px;
  classDef product fill:#dcfce7,stroke:#15803d,stroke-width:2px;
```

## Requirement traceability

_No business requirement is linked to this feature yet, so it cannot be traced back to a stated need._

## Products using it

- `corporate_current_account`

## Testing

| Tier | Status | Test modules |
|---|---|---|
| Unit | yes | 1 |
| Simulation | yes | 1 |
| End-to-end | yes | 2 |

<!-- generated:end -->
