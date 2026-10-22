---
type: Vault Feature
okf_version: "0.2"
profile: https://thoughtmachine.example/fde/schemas/feature-knowledge-bundle/1.0.json
profile_version: 1.0.0
title: Denomination
description: Smart Contract feature common.denomination.
status: draft
tags:
  - common
identity:
  id: feature_library.common.denomination
  module: feature_library.common.denomination
  source_path: feature_library/src/feature_library/common/denomination.py
  kind: primary
  domain: common
version:
  library_version: 1.0.0
  content_hash: sha256:56015231f72102b001e29df4ac9a30d8871e3dc4d9a89bd34e2a9cf11b93bcc5
generated:
  by: process:fl/0.1.0
hooks:
  - pre_posting_hook
entry_points:
  - name: get_parameters
    returns: dict[str, str | datetime | Decimal | None]
    reads_parameters: []
  - name: add_denomination_to_state
    returns: state_utils.SmartContractState
    reads_parameters: []
  - name: validate_denomination
    returns: Rejection | None
    reads_parameters: []
parameters:
  - id: "&{denomination}"
    clu_id: denomination
    constant: DENOMINATION_PARAM
    ownership: owned
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
  - fetcher_id: denomination_at_effective_datetime_fetcher
    kind: ParametersObservationFetcher
    declared_in: common.denomination
  - fetcher_id: denomination_live_fetcher
    kind: ParametersObservationFetcher
    declared_in: common.denomination
events: []
event_style: static
notifications: []
balance_addresses: []
interfaces:
  provides: []
  consumes: []
dependencies:
  features:
    - common.posting_utils
    - common.state_utils
  used_by:
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
    - lending.amortisations.eia
    - lending.closure.close_loan
    - lending.disbursal.disbursement
    - lending.fees.annual_fee
    - lending.fees.cash_advance_fee
    - lending.fees.credit_card_late_payment_fee
    - lending.fees.foreign_transaction_fee
    - lending.interest.credit_card_interest_accrual
    - lending.interest.interest_accrual
    - lending.interest.interest_application
    - lending.interest.interest_capitalisation
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
  unit: 42
  simulation: 41
  e2e: 38
traceability:
  business_requirements: []
  used_by_products: []
complete: false
---

# Denomination

> Generated by `python3 -m fl docs`. Curated prose comes from `feature_library/src/feature_library/common/denomination.okf.yaml`; everything else is derived from the module source. Do not edit by hand.

| Property | Value |
|---|---|
| Module | `feature_library.common.denomination` |
| Domain | common |
| Status | undeclared |
| Version | — |
| Hooks | `pre_posting_hook` |
| Source | `feature_library/src/feature_library/common/denomination.py` |

## What it does

_Not yet described._

## Traceability: configuration to outcome

Every input below is a value a bank configures. The diagram shows which function consumes it and which hook turns it into an outcome.

```mermaid
graph LR
  subgraph CONFIG[Configuration inputs]
    direction TB
    p_denomination["&{denomination}"]
  end
  subgraph DATA[Data fetched at execution]
    direction TB
    d_denomination_at_effective_datetime_fetcher[/"denomination_at_effective_datetime_fetcher\n(ParametersObservationFetcher)"/]
    d_denomination_live_fetcher[/"denomination_live_fetcher\n(ParametersObservationFetcher)"/]
  end
  subgraph FEAT["denomination"]
    direction TB
    f_add_denomination_to_state("add_denomination_to_state()")
    f_validate_denomination("validate_denomination()")
  end
  subgraph HOOKS[Contract hooks]
    direction TB
    h_pre_posting_hook[["pre_posting_hook"]]
  end
  subgraph OUT[Outcomes]
    direction TB
    o_0["Rejection | None"]
  end
  p_denomination --> f_add_denomination_to_state
  d_denomination_at_effective_datetime_fetcher --> f_add_denomination_to_state
  d_denomination_live_fetcher --> f_add_denomination_to_state
  f_add_denomination_to_state --> h_pre_posting_hook
  f_validate_denomination --> h_pre_posting_hook
  h_pre_posting_hook --> o_0
```

## Inputs — parameters

| Reference | Meaning | Hierarchy level | Constraint | Required | CLU resource |
|---|---|---|---|---|---|
| `&{denomination}` | _undocumented_ | — | string_constraint | required | `feature_library/src/feature_library/common/parameter_resource_defs/denomination.resource.yaml` |

## Inputs — data fetched at execution

| Fetcher id | Type | Anchor | Filter |
|---|---|---|---|
| `denomination_at_effective_datetime_fetcher` | ParametersObservationFetcher | DefinedDateTime.EFFECTIVE_DATETIME | ParametersFilter(parameter_ids=[DENOMINATION_PARAM_ID]) |
| `denomination_live_fetcher` | ParametersObservationFetcher | DefinedDateTime.LIVE | ParametersFilter(parameter_ids=[DENOMINATION_PARAM_ID]) |

## Public API

| Function | Returns | Purpose |
|---|---|---|
| `get_parameters(vault, fetcher_id)` | `dict[str, str \| datetime \| Decimal \| None]` | Retrieves the denomination parameters from a vault parameter observation. |
| `add_denomination_to_state(state, param_fetcher_id)` | `state_utils.SmartContractState` | Updates the contract state with denomination parameters fetched from the vault. |
| `validate_denomination(state, posting_instructions, denomination_param_id)` | `Rejection \| None` | Validates a list of Posting Instructions for denomination. |

## Where it sits in the library

```mermaid
graph BT
  me_denomination["denomination"]:::self
  dep_common_posting_utils["common.posting_utils"] --> me_denomination
  dep_common_state_utils["common.state_utils"] --> me_denomination
  me_denomination --> use_deposit_fees_early_closure_fee["deposit.fees.early_closure_fee"]
  me_denomination --> use_deposit_fees_inactivity_fee["deposit.fees.inactivity_fee"]
  me_denomination --> use_deposit_fees_maintenance_fees["deposit.fees.maintenance_fees"]
  me_denomination --> use_deposit_fees_minimum_monthly_balance["deposit.fees.minimum_monthly_balance"]
  me_denomination --> use_deposit_fees_overdraft_limit["deposit.fees.overdraft_limit"]
  me_denomination --> use_deposit_fees_paper_statement_fee["deposit.fees.paper_statement_fee"]
  me_denomination --> use_deposit_fees_partial_fee["deposit.fees.partial_fee"]
  me_denomination --> use_deposit_fees_unarranged_overdraft_fee["deposit.fees.unarranged_overdraft_fee"]
  me_denomination --> use_deposit_fees_withdrawal_early_withdrawal_fees["deposit.fees.withdrawal.early_withdrawal_fees"]
  me_denomination --> use_deposit_fees_withdrawal_excess_fee["deposit.fees.withdrawal.excess_fee"]
  me_denomination --> use_deposit_fees_withdrawal_payment_type_flat_fee["deposit.fees.withdrawal.payment_type_flat_fee"]
  me_denomination --> use_deposit_fees_withdrawal_payment_type_monthly_limit_fee["deposit.fees.withdrawal.payment_type_monthly_limit_fee"]
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
| Unit | yes | 42 |
| Simulation | yes | 41 |
| End-to-end | yes | 38 |

<!-- generated:end -->
