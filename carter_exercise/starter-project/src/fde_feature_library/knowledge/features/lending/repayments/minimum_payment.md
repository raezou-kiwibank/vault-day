---
type: Vault Feature
okf_version: "0.2"
profile: https://thoughtmachine.example/fde/schemas/feature-knowledge-bundle/1.0.json
profile_version: 1.0.0
title: Minimum Payment
description: Smart Contract feature lending.repayments.minimum_payment.
status: draft
tags:
  - lending
identity:
  id: feature_library.lending.repayments.minimum_payment
  module: feature_library.lending.repayments.minimum_payment
  source_path: feature_library/src/feature_library/lending/repayments/minimum_payment.py
  kind: primary
  domain: lending
version:
  library_version: 1.0.0
  content_hash: sha256:d7992459960388b75e4bc7e6483c43a21beb68167bd0dd2bbed49aed3f86f2d3
generated:
  by: process:fl/0.1.0
hooks:
  - activation_hook
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
  - name: calculate_minimum_payment
    returns: Decimal
    reads_parameters: []
  - name: statement_cut_logic
    returns: list[CustomInstruction]
    reads_parameters: []
parameters:
  - id: "&{minimum_payment_percentage}"
    clu_id: minimum_payment_percentage
    constant: MINIMUM_PAYMENT_PERCENTAGE_PARAM
    ownership: owned
    owner_feature: lending.repayments.minimum_payment
    level: TEMPLATE
    constraint: decimal_constraint
    clu_resource: feature_library/src/feature_library/lending/repayments/parameter_resource_defs/minimum_payment_percentage.resource.yaml
    optional: false
    triggers_pre_parameter_change_hook: false
    triggers_post_parameter_change_hook: false
    description: ""
    drives: ""
  - id: "&{minimum_payment_fixed_amount}"
    clu_id: minimum_payment_fixed_amount
    constant: MINIMUM_PAYMENT_FIXED_AMOUNT_PARAM
    ownership: owned
    owner_feature: lending.repayments.minimum_payment
    level: TEMPLATE
    constraint: decimal_constraint
    clu_resource: feature_library/src/feature_library/lending/repayments/parameter_resource_defs/minimum_payment_fixed_amount.resource.yaml
    optional: false
    triggers_pre_parameter_change_hook: false
    triggers_post_parameter_change_hook: false
    description: ""
    drives: ""
  - id: "&{statement_day}"
    clu_id: statement_day
    constant: STATEMENT_DAY_PARAM
    ownership: owned
    owner_feature: lending.repayments.minimum_payment
    level: TEMPLATE
    constraint: decimal_constraint
    clu_resource: feature_library/src/feature_library/lending/repayments/parameter_resource_defs/statement_day.resource.yaml
    optional: false
    triggers_pre_parameter_change_hook: false
    triggers_post_parameter_change_hook: false
    description: ""
    drives: ""
  - id: "&{payment_due_days}"
    clu_id: payment_due_days
    constant: PAYMENT_DUE_DAYS_PARAM
    ownership: owned
    owner_feature: lending.repayments.minimum_payment
    level: TEMPLATE
    constraint: decimal_constraint
    clu_resource: feature_library/src/feature_library/lending/repayments/parameter_resource_defs/payment_due_days.resource.yaml
    optional: false
    triggers_pre_parameter_change_hook: false
    triggers_post_parameter_change_hook: false
    description: ""
    drives: ""
  - id: "&{statement_time}"
    clu_id: statement_time
    constant: STATEMENT_TIME_PARAM
    ownership: owned
    owner_feature: lending.repayments.minimum_payment
    level: TEMPLATE
    constraint: string_constraint
    clu_resource: feature_library/src/feature_library/lending/repayments/parameter_resource_defs/statement_time.resource.yaml
    optional: false
    triggers_pre_parameter_change_hook: false
    triggers_post_parameter_change_hook: false
    description: ""
    drives: ""
  - id: "&{statement_interest_receivable_account}"
    clu_id: statement_interest_receivable_account
    constant: INTEREST_RECEIVABLE_ACCOUNT_PARAM
    ownership: owned
    owner_feature: lending.repayments.minimum_payment
    level: TEMPLATE
    constraint: account_constraint
    clu_resource: feature_library/src/feature_library/lending/repayments/parameter_resource_defs/statement_interest_receivable_account.resource.yaml
    optional: false
    triggers_pre_parameter_change_hook: false
    triggers_post_parameter_change_hook: false
    description: ""
    drives: ""
data_fetchers:
  - fetcher_id: statement_cut_pof
    kind: ParametersObservationFetcher
    declared_in: lending.repayments.minimum_payment
events:
  - STATEMENT_CUT
event_style: factory
notifications: []
balance_addresses:
  - CASH_ADVANCE
  - FEES
  - INTEREST_ACCRUED_CASH_ADVANCE
  - INTEREST_ACCRUED_PURCHASE
  - INTEREST_CHARGED
  - MINIMUM_PAYMENT_DUE_TRACKER
  - PURCHASE
  - STATEMENT_BALANCE_TRACKER
  - TOTAL_REPAYMENTS_TRACKER
interfaces:
  provides: []
  consumes: []
dependencies:
  features:
    - common.accrual_utils
    - common.date_and_time
    - common.denomination
    - common.fetchers
    - common.posting_utils
    - common.state_utils
    - lending.addresses
  used_by: []
tests:
  unit: 1
  simulation: 0
  e2e: 0
traceability:
  business_requirements: []
  used_by_products: []
complete: false
---

# Minimum Payment

> Generated by `python3 -m fl docs`. Curated prose comes from `feature_library/src/feature_library/lending/repayments/minimum_payment.okf.yaml`; everything else is derived from the module source. Do not edit by hand.

| Property | Value |
|---|---|
| Module | `feature_library.lending.repayments.minimum_payment` |
| Domain | lending |
| Status | undeclared |
| Version | — |
| Hooks | `activation_hook` |
| Source | `feature_library/src/feature_library/lending/repayments/minimum_payment.py` |

## What it does

_Not yet described._

## Traceability: configuration to outcome

Every input below is a value a bank configures. The diagram shows which function consumes it and which hook turns it into an outcome.

```mermaid
graph LR
  subgraph CONFIG[Configuration inputs]
    direction TB
    p_minimum_payment_percentage["&{minimum_payment_percentage}"]
    p_minimum_payment_fixed_amount["&{minimum_payment_fixed_amount}"]
    p_statement_day["&{statement_day}"]
    p_payment_due_days["&{payment_due_days}"]
    p_statement_time["&{statement_time}"]
    p_statement_interest_receivable_account["&{statement_interest_receivable_account}"]
  end
  subgraph DATA[Data fetched at execution]
    direction TB
    d_statement_cut_pof[/"statement_cut_pof\n(ParametersObservationFetcher)"/]
  end
  subgraph FEAT["minimum_payment"]
    direction TB
    f_event_types("event_types()")
    f_get_scheduled_events("get_scheduled_events()")
    f_calculate_minimum_payment("calculate_minimum_payment()")
    f_statement_cut_logic("statement_cut_logic()")
  end
  subgraph HOOKS[Contract hooks]
    direction TB
    h_activation_hook[["activation_hook"]]
  end
  subgraph OUT[Outcomes]
    direction TB
    o_0["ScheduledEvent map"]
    o_1["scheduled events: STATEMENT_CUT"]
    o_2["addresses: CASH_ADVANCE, FEES, INTEREST_ACCRUED_CASH_ADVANCE, INTEREST_ACCRUED_PURCHASE, INTEREST_CHARGED"]
  end
  p_minimum_payment_percentage --> f_event_types
  p_minimum_payment_fixed_amount --> f_event_types
  p_statement_day --> f_event_types
  p_payment_due_days --> f_event_types
  p_statement_time --> f_event_types
  p_statement_interest_receivable_account --> f_event_types
  d_statement_cut_pof --> f_event_types
  f_event_types --> h_activation_hook
  f_get_scheduled_events --> h_activation_hook
  f_calculate_minimum_payment --> h_activation_hook
  f_statement_cut_logic --> h_activation_hook
  h_activation_hook --> o_0
  h_activation_hook --> o_1
  h_activation_hook --> o_2
```

## Inputs — parameters

| Reference | Meaning | Hierarchy level | Constraint | Required | CLU resource |
|---|---|---|---|---|---|
| `&{minimum_payment_percentage}` | Minimum payment as a percentage of total balance (e.g. 0.02 for 2%). | — | decimal_constraint | required | `feature_library/src/feature_library/lending/repayments/parameter_resource_defs/minimum_payment_percentage.resource.yaml` |
| `&{minimum_payment_fixed_amount}` | Fixed minimum payment amount. | — | decimal_constraint | required | `feature_library/src/feature_library/lending/repayments/parameter_resource_defs/minimum_payment_fixed_amount.resource.yaml` |
| `&{statement_day}` | Day of month for statement cut. | — | decimal_constraint | required | `feature_library/src/feature_library/lending/repayments/parameter_resource_defs/statement_day.resource.yaml` |
| `&{payment_due_days}` | Number of days after statement cut that payment is due. | — | decimal_constraint | required | `feature_library/src/feature_library/lending/repayments/parameter_resource_defs/payment_due_days.resource.yaml` |
| `&{statement_time}` | Time of day for statement cut. Format: HH:MM:SS. | — | string_constraint | required | `feature_library/src/feature_library/lending/repayments/parameter_resource_defs/statement_time.resource.yaml` |
| `&{statement_interest_receivable_account}` | Internal account for interest receivable used at statement cut. | — | account_constraint | required | `feature_library/src/feature_library/lending/repayments/parameter_resource_defs/statement_interest_receivable_account.resource.yaml` |

## Inputs — data fetched at execution

| Fetcher id | Type | Anchor | Filter |
|---|---|---|---|
| `statement_cut_pof` | ParametersObservationFetcher | DefinedDateTime.EFFECTIVE_DATETIME | ParametersFilter(parameter_ids=[p.id for p in expected_parameters]) |

## Public API

| Function | Returns | Purpose |
|---|---|---|
| `event_types(product_name)` | `list[SmartContractEventType]` | Return the event types for the statement cut feature. |
| `get_parameters(vault, param_fetcher_id)` | `dict[str, datetime \| Decimal \| str \| None]` | Retrieves configuration parameters for the statement cut feature. |
| `get_scheduled_events(state, fetchers_config)` | `dict[str, ScheduledEvent]` | Get scheduled event for monthly statement cut. |
| `calculate_minimum_payment(total_balance, accrued_interest, fees, percentage, fixed_amount)` | `Decimal` | Calculates the minimum payment due. |
| `statement_cut_logic(state, account_type, fetchers_config)` | `list[CustomInstruction]` | Performs statement cut logic. |

## Outputs

| Kind | Values | Notes |
|---|---|---|
| Scheduled events | `STATEMENT_CUT` | per-product factory |
| Balance addresses | `CASH_ADVANCE`, `FEES`, `INTEREST_ACCRUED_CASH_ADVANCE`, `INTEREST_ACCRUED_PURCHASE`, `INTEREST_CHARGED`, `MINIMUM_PAYMENT_DUE_TRACKER`, `PURCHASE`, `STATEMENT_BALANCE_TRACKER`, `TOTAL_REPAYMENTS_TRACKER` | — |

## Where it sits in the library

```mermaid
graph BT
  me_minimum_payment["minimum_payment"]:::self
  dep_common_accrual_utils["common.accrual_utils"] --> me_minimum_payment
  dep_common_date_and_time["common.date_and_time"] --> me_minimum_payment
  dep_common_denomination["common.denomination"] --> me_minimum_payment
  dep_common_fetchers["common.fetchers"] --> me_minimum_payment
  dep_common_posting_utils["common.posting_utils"] --> me_minimum_payment
  dep_common_state_utils["common.state_utils"] --> me_minimum_payment
  dep_lending_addresses["lending.addresses"] --> me_minimum_payment
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
| Simulation | **missing** | 0 |
| End-to-end | **missing** | 0 |

<!-- generated:end -->
