---
type: Vault Feature
okf_version: "0.2"
profile: https://thoughtmachine.example/fde/schemas/feature-knowledge-bundle/1.0.json
profile_version: 1.0.0
title: State Utils
description: Smart Contract feature common.state_utils.
status: draft
tags:
  - common
identity:
  id: feature_library.common.state_utils
  module: feature_library.common.state_utils
  source_path: feature_library/src/feature_library/common/state_utils.py
  kind: utility
  domain: common
version:
  library_version: 1.0.0
  content_hash: sha256:4c73589438dd365f9476879308bfa3ff4a46b875431637934e21496f3d1fbea7
generated:
  by: process:fl/0.1.0
hooks:
  - pre_posting_hook
entry_points:
  - name: initialise_state
    returns: SmartContractState
    reads_parameters: []
  - name: append_to_state
    returns: SmartContractState
    reads_parameters: []
  - name: check_parameters_exist
    returns: Rejection | None
    reads_parameters: []
  - name: is_coordinates_in_state
    returns: bool
    reads_parameters: []
  - name: get_balance_from_state
    returns: Decimal
    reads_parameters: []
parameters: []
data_fetchers: []
events: []
event_style: static
notifications: []
balance_addresses: []
interfaces:
  provides: []
  consumes: []
dependencies:
  features:
    - common.balance_utils
  used_by:
    - common.application_precision
    - common.denomination
    - common.fetchers
    - deposit.dormancy.dormancy
    - deposit.fees.early_closure_fee
    - deposit.fees.inactivity_fee
    - deposit.fees.maintenance_fees
    - deposit.fees.minimum_monthly_balance
    - deposit.fees.overdraft_limit
    - deposit.fees.paper_statement_fee
    - deposit.fees.partial_fee
    - deposit.fees.unarranged_overdraft_fee
    - deposit.fees.withdrawal.early_withdrawal_fees
    - deposit.fees.withdrawal.excess_fee
    - deposit.fees.withdrawal.payment_type_flat_fee
    - deposit.fees.withdrawal.payment_type_monthly_limit_fee
    - deposit.fees.withdrawal.payment_type_threshold_fee
    - deposit.interest.deposit_interest_accrual_utils
    - deposit.interest.interest_accrual
    - deposit.interest.interest_application
    - deposit.interest.secondary.flat_interest
    - deposit.interest.secondary.overdraft_interest
    - deposit.interest.secondary.tiered_interest
    - deposit.temporal_features.cooling_off_period
    - deposit.temporal_features.deposit_period
    - deposit.temporal_features.grace_period
    - deposit.transaction_limits.deposit_limits.maximum_balance_limit
    - deposit.transaction_limits.deposit_limits.maximum_daily_deposit
    - deposit.transaction_limits.deposit_limits.maximum_single_deposit
    - deposit.transaction_limits.deposit_limits.minimum_initial_deposit
    - deposit.transaction_limits.deposit_limits.minimum_single_deposit
    - deposit.transaction_limits.withdrawal_limits.maximum_daily_withdrawal
    - deposit.transaction_limits.withdrawal_limits.maximum_daily_withdrawal_by_transaction_type
    - deposit.transaction_limits.withdrawal_limits.maximum_single_withdrawal
    - deposit.transaction_limits.withdrawal_limits.maximum_withdrawal_by_payment_type
    - deposit.transaction_limits.withdrawal_limits.minimum_balance_by_tier
    - deposit.transaction_limits.withdrawal_limits.minimum_single_withdrawal
    - lending.account_attributes
    - lending.amortisations.amortisation_methods.declining_principal
    - lending.amortisations.amortisation_methods.flat_interest
    - lending.amortisations.amortisation_methods.interest_only
    - lending.amortisations.amortisation_methods.minimum_repayment
    - lending.amortisations.amortisation_methods.no_repayment
    - lending.amortisations.amortisation_methods.rule_of_78
    - lending.amortisations.due_amount_notification
    - lending.amortisations.eia
    - lending.closure.close_loan
    - lending.delinquency.delinquency
    - lending.disbursal.disbursement
    - lending.fees.annual_fee
    - lending.fees.cash_advance_fee
    - lending.fees.credit_card_late_payment_fee
    - lending.fees.foreign_transaction_fee
    - lending.interest.credit_card_interest_accrual
    - lending.interest.interest_accrual
    - lending.interest.interest_application
    - lending.interest.interest_capitalisation
    - lending.interest.secondary.fixed_rate
    - lending.interest.secondary.variable_rate
    - lending.limits.credit_limit
    - lending.overdue.overdue
    - lending.principal.maximum_loan_principal
    - lending.principal.minimum_loan_principal
    - lending.redraw.redraw
    - lending.repayments.early_repayment
    - lending.repayments.late_repayment
    - lending.repayments.minimum_payment
    - lending.repayments.overpayment
    - lending.repayments.overpayment_allowance
    - lending.repayments.payments
    - lending.repayments.secondary.horizontal_repayment_hierarchy
    - lending.repayments.secondary.vertical_repayment_hierarchy
    - lending.rewards.points_accrual
    - lending.rewards.welcome_bonus
tests:
  unit: 16
  simulation: 42
  e2e: 39
traceability:
  business_requirements: []
  used_by_products: []
complete: false
---

# State Utils

> Generated by `python3 -m fl docs`. Curated prose comes from `feature_library/src/feature_library/common/state_utils.okf.yaml`; everything else is derived from the module source. Do not edit by hand.

| Property | Value |
|---|---|
| Module | `feature_library.common.state_utils` |
| Domain | common |
| Status | undeclared |
| Version | — |
| Hooks | `pre_posting_hook` |
| Source | `feature_library/src/feature_library/common/state_utils.py` |

## What it does

_Not yet described._

## Traceability: configuration to outcome

Every input below is a value a bank configures. The diagram shows which function consumes it and which hook turns it into an outcome.

```mermaid
graph LR
  subgraph FEAT["state_utils"]
    direction TB
    f_initialise_state("initialise_state()")
    f_append_to_state("append_to_state()")
    f_check_parameters_exist("check_parameters_exist()")
    f_is_coordinates_in_state("is_coordinates_in_state()")
    f_get_balance_from_state("get_balance_from_state()")
  end
  subgraph HOOKS[Contract hooks]
    direction TB
    h_pre_posting_hook[["pre_posting_hook"]]
  end
  subgraph OUT[Outcomes]
    direction TB
    o_0["Rejection | None"]
  end
  f_initialise_state --> h_pre_posting_hook
  f_append_to_state --> h_pre_posting_hook
  f_check_parameters_exist --> h_pre_posting_hook
  f_is_coordinates_in_state --> h_pre_posting_hook
  f_get_balance_from_state --> h_pre_posting_hook
  h_pre_posting_hook --> o_0
```

## Public API

| Function | Returns | Purpose |
|---|---|---|
| `initialise_state(vault, effective_datetime, parameters, balances, inflight_postings)` | `SmartContractState` | Initialises a SmartContractState object with the provided vault and values. |
| `append_to_state(state, vault, effective_datetime, parameters, balances, inflight_postings)` | `SmartContractState` | Creates a new SmartContractState by merging provided values with an existing state. |
| `check_parameters_exist(state, param_ids)` | `Rejection \| None` | Validates that the required parameter IDs are present in the SmartContractState. |
| `is_coordinates_in_state(state, coordinates)` | `bool` | Checks if all specified balance coordinates are present in the state's balances. |
| `get_balance_from_state(state, fetcher_id, account_address, denomination, asset, phase)` | `Decimal` | Attempts to get Balance Observation Value from State object. |

## Where it sits in the library

```mermaid
graph BT
  me_state_utils["state_utils"]:::self
  dep_common_balance_utils["common.balance_utils"] --> me_state_utils
  me_state_utils --> use_common_application_precision["common.application_precision"]
  me_state_utils --> use_common_denomination["common.denomination"]
  me_state_utils --> use_common_fetchers["common.fetchers"]
  me_state_utils --> use_deposit_dormancy_dormancy["deposit.dormancy.dormancy"]
  me_state_utils --> use_deposit_fees_early_closure_fee["deposit.fees.early_closure_fee"]
  me_state_utils --> use_deposit_fees_inactivity_fee["deposit.fees.inactivity_fee"]
  me_state_utils --> use_deposit_fees_maintenance_fees["deposit.fees.maintenance_fees"]
  me_state_utils --> use_deposit_fees_minimum_monthly_balance["deposit.fees.minimum_monthly_balance"]
  me_state_utils --> use_deposit_fees_overdraft_limit["deposit.fees.overdraft_limit"]
  me_state_utils --> use_deposit_fees_paper_statement_fee["deposit.fees.paper_statement_fee"]
  me_state_utils --> use_deposit_fees_partial_fee["deposit.fees.partial_fee"]
  me_state_utils --> use_deposit_fees_unarranged_overdraft_fee["deposit.fees.unarranged_overdraft_fee"]
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
| Unit | yes | 16 |
| Simulation | yes | 42 |
| End-to-end | yes | 39 |

<!-- generated:end -->
