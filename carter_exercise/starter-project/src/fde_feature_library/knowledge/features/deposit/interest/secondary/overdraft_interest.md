---
type: Vault Feature
okf_version: "0.2"
profile: https://thoughtmachine.example/fde/schemas/feature-knowledge-bundle/1.0.json
profile_version: 1.0.0
title: Overdraft Interest
description: Smart Contract feature deposit.interest.secondary.overdraft_interest.
status: draft
tags:
  - deposit
identity:
  id: feature_library.deposit.interest.secondary.overdraft_interest
  module: feature_library.deposit.interest.secondary.overdraft_interest
  source_path: feature_library/src/feature_library/deposit/interest/secondary/overdraft_interest.py
  kind: secondary
  domain: deposit
version:
  library_version: 1.0.0
  content_hash: sha256:d8c9e721baec8bdbe83b02e183ec2d06f0b884a9d3cc6a5bb328bc3bc7583dc8
generated:
  by: process:fl/0.1.0
hooks:
  - scheduled_event_hook
entry_points:
  - name: get_parameters
    returns: dict[str, datetime | Decimal | str | None]
    reads_parameters: []
  - name: get_interest_rate
    returns: common_tuples.InterestRateTuple
    reads_parameters: []
  - name: accrue_interest
    returns: list[CustomInstruction]
    reads_parameters: []
  - name: calculate_accrual_balance
    returns: Balance
    reads_parameters: []
  - name: overdraft_interest_capitalisation_custom_instruction
    returns: list[CustomInstruction]
    reads_parameters: []
  - name: apply_interest
    returns: list[CustomInstruction]
    reads_parameters: []
  - name: get_interest_reversal_postings
    returns: list[CustomInstruction]
    reads_parameters: []
  - name: get_overdraft_accrual_amount
    returns: common_tuples.AccrualDetail
    reads_parameters: []
  - name: get_accrual_payable_customer_address
    returns: str
    reads_parameters: []
  - name: get_accrual_receivable_customer_address
    returns: str
    reads_parameters: []
  - name: get_accrual_payable_internal_account
    returns: str
    reads_parameters: []
  - name: get_accrual_receivable_internal_account
    returns: str
    reads_parameters: []
parameters:
  - id: "&{overdraft_interest_rate}"
    clu_id: overdraft_interest_rate
    constant: OVERDRAFT_INTEREST_RATE_PARAM
    ownership: owned
    owner_feature: deposit.interest.secondary.overdraft_interest
    level: TEMPLATE
    constraint: decimal_constraint
    clu_resource: feature_library/src/feature_library/deposit/interest/parameter_resource_defs/overdraft_interest_rate.resource.yaml
    optional: false
    triggers_pre_parameter_change_hook: false
    triggers_post_parameter_change_hook: false
    description: ""
    drives: ""
  - id: "&{overdraft_interest_receivable_account}"
    clu_id: overdraft_interest_receivable_account
    constant: OVERDRAFT_INTEREST_RECEIVABLE_ACCOUNT_PARAM
    ownership: owned
    owner_feature: deposit.interest.secondary.overdraft_interest
    level: TEMPLATE
    constraint: account_constraint
    clu_resource: feature_library/src/feature_library/deposit/interest/parameter_resource_defs/overdraft_interest_receivable_account.resource.yaml
    optional: false
    triggers_pre_parameter_change_hook: false
    triggers_post_parameter_change_hook: false
    description: ""
    drives: ""
  - id: "&{overdraft_interest_received_account}"
    clu_id: overdraft_interest_received_account
    constant: OVERDRAFT_INTEREST_RECEIVED_ACCOUNT_PARAM
    ownership: owned
    owner_feature: deposit.interest.secondary.overdraft_interest
    level: TEMPLATE
    constraint: account_constraint
    clu_resource: feature_library/src/feature_library/deposit/interest/parameter_resource_defs/overdraft_interest_received_account.resource.yaml
    optional: false
    triggers_pre_parameter_change_hook: false
    triggers_post_parameter_change_hook: false
    description: ""
    drives: ""
  - id: "&{interest_free_buffer_days}"
    clu_id: interest_free_buffer_days
    constant: INTEREST_FREE_BUFFER_DAYS_PARAM
    ownership: owned
    owner_feature: deposit.interest.secondary.overdraft_interest
    level: TEMPLATE
    constraint: decimal_constraint
    clu_resource: feature_library/src/feature_library/deposit/interest/parameter_resource_defs/interest_free_buffer_days.resource.yaml
    optional: false
    triggers_pre_parameter_change_hook: false
    triggers_post_parameter_change_hook: false
    description: ""
    drives: ""
  - id: "&{interest_free_buffer_amount}"
    clu_id: interest_free_buffer_amount
    constant: INTEREST_FREE_BUFFER_AMOUNT_PARAM
    ownership: owned
    owner_feature: deposit.interest.secondary.overdraft_interest
    level: TEMPLATE
    constraint: decimal_constraint
    clu_resource: feature_library/src/feature_library/deposit/interest/parameter_resource_defs/interest_free_buffer_amount.resource.yaml
    optional: false
    triggers_pre_parameter_change_hook: false
    triggers_post_parameter_change_hook: false
    description: ""
    drives: ""
data_fetchers:
  - fetcher_id: all_balances_et_bof
    kind: BalancesObservationFetcher
    declared_in: common.fetchers
  - fetcher_id: overdraft_interest_pof
    kind: ParametersObservationFetcher
    declared_in: deposit.interest.secondary.overdraft_interest
events: []
event_style: static
notifications: []
balance_addresses: []
interfaces:
  provides:
    - InterestType
  consumes: []
dependencies:
  features:
    - common.accrual_utils
    - common.application_precision
    - common.balance_utils
    - common.denomination
    - common.fetchers
    - common.parameter_utils
    - common.posting_utils
    - common.state_utils
    - common.tuples
    - common.utils
    - deposit.interest.interest_accrual
    - deposit.interfaces
  used_by: []
tests:
  unit: 1
  simulation: 2
  e2e: 0
traceability:
  business_requirements: []
  used_by_products:
    - corporate_current_account
    - personal_current_account
complete: true
---

# Overdraft Interest

> Generated by `python3 -m fl docs`. Curated prose comes from `feature_library/src/feature_library/deposit/interest/secondary/overdraft_interest.okf.yaml`; everything else is derived from the module source. Do not edit by hand.

| Property | Value |
|---|---|
| Module | `feature_library.deposit.interest.secondary.overdraft_interest` |
| Domain | deposit |
| Status | undeclared |
| Version | — |
| Hooks | `scheduled_event_hook` |
| Source | `feature_library/src/feature_library/deposit/interest/secondary/overdraft_interest.py` |

## What it does

_Not yet described._

## Traceability: configuration to outcome

Every input below is a value a bank configures. The diagram shows which function consumes it and which hook turns it into an outcome.

```mermaid
graph LR
  subgraph CONFIG[Configuration inputs]
    direction TB
    p_overdraft_interest_rate["&{overdraft_interest_rate}"]
    p_overdraft_interest_receivable_account["&{overdraft_interest_receivable_account}"]
    p_overdraft_interest_received_account["&{overdraft_interest_received_account}"]
    p_interest_free_buffer_days["&{interest_free_buffer_days}"]
    p_interest_free_buffer_amount["&{interest_free_buffer_amount}"]
  end
  subgraph DATA[Data fetched at execution]
    direction TB
    d_all_balances_et_bof[/"all_balances_et_bof\n(BalancesObservationFetcher)"/]
    d_overdraft_interest_pof[/"overdraft_interest_pof\n(ParametersObservationFetcher)"/]
  end
  subgraph FEAT["overdraft_interest"]
    direction TB
    f_get_interest_rate("get_interest_rate()")
    f_accrue_interest("accrue_interest()")
    f_calculate_accrual_balance("calculate_accrual_balance()")
    f_overdraft_interest_capitalisation_custom_instruction("overdraft_interest_capitalisation_custom_instruction()")
    f_apply_interest("apply_interest()")
    f_get_interest_reversal_postings("get_interest_reversal_postings()")
    f_get_overdraft_accrual_amount("get_overdraft_accrual_amount()")
    f_get_accrual_payable_customer_address("get_accrual_payable_customer_address()")
    f_get_accrual_receivable_customer_address("get_accrual_receivable_customer_address()")
    f_get_accrual_payable_internal_account("get_accrual_payable_internal_account()")
  end
  subgraph HOOKS[Contract hooks]
    direction TB
    h_scheduled_event_hook[["scheduled_event_hook"]]
  end
  subgraph OUT[Outcomes]
    direction TB
    o_0["CustomInstruction[] / directives"]
  end
  p_overdraft_interest_rate --> f_get_interest_rate
  p_overdraft_interest_receivable_account --> f_get_interest_rate
  p_overdraft_interest_received_account --> f_get_interest_rate
  p_interest_free_buffer_days --> f_get_interest_rate
  p_interest_free_buffer_amount --> f_get_interest_rate
  d_all_balances_et_bof --> f_get_interest_rate
  d_overdraft_interest_pof --> f_get_interest_rate
  f_get_interest_rate --> h_scheduled_event_hook
  f_accrue_interest --> h_scheduled_event_hook
  f_calculate_accrual_balance --> h_scheduled_event_hook
  f_overdraft_interest_capitalisation_custom_instruction --> h_scheduled_event_hook
  f_apply_interest --> h_scheduled_event_hook
  f_get_interest_reversal_postings --> h_scheduled_event_hook
  f_get_overdraft_accrual_amount --> h_scheduled_event_hook
  f_get_accrual_payable_customer_address --> h_scheduled_event_hook
  f_get_accrual_receivable_customer_address --> h_scheduled_event_hook
  f_get_accrual_payable_internal_account --> h_scheduled_event_hook
  h_scheduled_event_hook --> o_0
```

## Inputs — parameters

| Reference | Meaning | Hierarchy level | Constraint | Required | CLU resource |
|---|---|---|---|---|---|
| `&{overdraft_interest_rate}` | _undocumented_ | — | decimal_constraint | required | `feature_library/src/feature_library/deposit/interest/parameter_resource_defs/overdraft_interest_rate.resource.yaml` |
| `&{overdraft_interest_receivable_account}` | _undocumented_ | — | account_constraint | required | `feature_library/src/feature_library/deposit/interest/parameter_resource_defs/overdraft_interest_receivable_account.resource.yaml` |
| `&{overdraft_interest_received_account}` | _undocumented_ | — | account_constraint | required | `feature_library/src/feature_library/deposit/interest/parameter_resource_defs/overdraft_interest_received_account.resource.yaml` |
| `&{interest_free_buffer_days}` | _undocumented_ | — | decimal_constraint | required | `feature_library/src/feature_library/deposit/interest/parameter_resource_defs/interest_free_buffer_days.resource.yaml` |
| `&{interest_free_buffer_amount}` | _undocumented_ | — | decimal_constraint | required | `feature_library/src/feature_library/deposit/interest/parameter_resource_defs/interest_free_buffer_amount.resource.yaml` |

## Inputs — data fetched at execution

| Fetcher id | Type | Anchor | Filter |
|---|---|---|---|
| `all_balances_et_bof` | BalancesObservationFetcher | DefinedDateTime.EFFECTIVE_DATETIME | — |
| `overdraft_interest_pof` | ParametersObservationFetcher | DefinedDateTime.EFFECTIVE_DATETIME | ParametersFilter(parameter_ids=[p.id for p in expected_parameters]) |

## Public API

| Function | Returns | Purpose |
|---|---|---|
| `get_parameters(vault, param_fetcher_id)` | `dict[str, datetime \| Decimal \| str \| None]` | Retrieves configuration parameters for the overdraft interest feature. |
| `get_interest_rate(state, fetchers_config)` | `common_tuples.InterestRateTuple` | Retrieves the overdraft interest rate from the contract state. |
| `accrue_interest(state, account_type, fetchers_config)` | `list[CustomInstruction]` | Creates the posting instructions to accrue overdraft interest on the specified balances. |
| `calculate_accrual_balance(state, fetchers_config)` | `Balance` | Factor in optional interest free buffer days and amount to determine the balance. |
| `overdraft_interest_capitalisation_custom_instruction(customer_account, denomination, application_amount, accrual_amount, instruction_details, accrual_customer_address, accrual_internal_account, application_customer_address, application_internal_account)` | `list[CustomInstruction]` | Create a Custom Instruction for applying (capitalising) accrued overdraft interest. |
| `apply_interest(state, account_type, fetchers_config)` | `list[CustomInstruction]` | Creates the postings instructions to apply the accrued overdraft interest. |
| `get_interest_reversal_postings(state, event_name, account_type, fetchers_config)` | `list[CustomInstruction]` | Reverse any accrued overdraft interest and apply back to the internal account. |
| `get_overdraft_accrual_amount(effective_balance, effective_datetime, interest_rates, days_in_year, precision, state, fetchers_config)` | `common_tuples.AccrualDetail` | Calculates overdraft interest accrual amount using specialized buffer logic. |
| `get_accrual_payable_customer_address()` | `str` | _undocumented_ |
| `get_accrual_receivable_customer_address()` | `str` | _undocumented_ |
| `get_accrual_payable_internal_account(state)` | `str` | Returns the internal account where overdraft interest is accrued. |
| `get_accrual_receivable_internal_account(state)` | `str` | Returns the internal account where overdraft interest is accrued. |

## Composition points

| Provides interface | As constant | Members |
|---|---|---|
| `InterestType` | `InterestType` | `get_interest_rate`, `get_accrual_amount`, `get_accrual_payable_customer_address`, `get_accrual_receivable_customer_address`, `get_accrual_payable_internal_account`, `get_accrual_receivable_internal_account` |

## Where it sits in the library

```mermaid
graph BT
  me_overdraft_interest["overdraft_interest"]:::self
  dep_common_accrual_utils["common.accrual_utils"] --> me_overdraft_interest
  dep_common_application_precision["common.application_precision"] --> me_overdraft_interest
  dep_common_balance_utils["common.balance_utils"] --> me_overdraft_interest
  dep_common_denomination["common.denomination"] --> me_overdraft_interest
  dep_common_fetchers["common.fetchers"] --> me_overdraft_interest
  dep_common_parameter_utils["common.parameter_utils"] --> me_overdraft_interest
  dep_common_posting_utils["common.posting_utils"] --> me_overdraft_interest
  dep_common_state_utils["common.state_utils"] --> me_overdraft_interest
  dep_common_tuples["common.tuples"] --> me_overdraft_interest
  dep_common_utils["common.utils"] --> me_overdraft_interest
  dep_deposit_interest_interest_accrual["deposit.interest.interest_accrual"] --> me_overdraft_interest
  dep_deposit_interfaces["deposit.interfaces"] --> me_overdraft_interest
  me_overdraft_interest ==> prod_corporate_current_account["corporate_current_account"]:::product
  me_overdraft_interest ==> prod_personal_current_account["personal_current_account"]:::product
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
| Simulation | yes | 2 |
| End-to-end | **missing** | 0 |

<!-- generated:end -->
