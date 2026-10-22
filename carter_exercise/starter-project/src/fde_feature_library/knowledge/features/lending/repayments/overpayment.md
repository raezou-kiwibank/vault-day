---
type: Vault Feature
okf_version: "0.2"
profile: https://thoughtmachine.example/fde/schemas/feature-knowledge-bundle/1.0.json
profile_version: 1.0.0
title: Overpayment
description: Smart Contract feature lending.repayments.overpayment.
status: draft
tags:
  - lending
identity:
  id: feature_library.lending.repayments.overpayment
  module: feature_library.lending.repayments.overpayment
  source_path: feature_library/src/feature_library/lending/repayments/overpayment.py
  kind: primary
  domain: lending
version:
  library_version: 1.0.0
  content_hash: sha256:8256d48e3a39dc7fc978a7500cbfd60f036e1eec09eb27ee9ad68933d0cca6d6
generated:
  by: process:fl/0.1.0
hooks:
  - post_posting_hook
  - pre_posting_hook
entry_points:
  - name: get_parameters
    returns: dict[str, str | Decimal | datetime | None]
    reads_parameters: []
  - name: get_max_overpayment_fee
    returns: Decimal
    reads_parameters: []
  - name: get_overpayment_fee
    returns: Decimal
    reads_parameters: []
  - name: charge_overpayment_fee_as_penalty
    returns: list[CustomInstruction]
    reads_parameters:
      - "&{denomination}"
      - "&{overpayment_fee_rate}"
      - "&{overpayment_fee_income_account}"
  - name: get_overpayment_fee_postings
    returns: list[Posting]
    reads_parameters: []
  - name: is_posting_an_overpayment
    returns: bool
    reads_parameters: []
  - name: validate_if_overpayment_is_greater_than_max
    returns: Rejection | None
    reads_parameters: []
  - name: get_max_overpayment_amount
    returns: Decimal
    reads_parameters:
      - "&{overpayment_fee_rate}"
      - "&{denomination}"
  - name: handle_overpayment
    returns: list[Posting]
    reads_parameters:
      - "&{denomination}"
  - name: get_early_repayment_overpayment_fee
    returns: Decimal
    reads_parameters:
      - "&{denomination}"
      - "&{overpayment_fee_rate}"
  - name: skip_charge_early_repayment_fee_for_overpayment
    returns: list[CustomInstruction]
    reads_parameters: []
  - name: get_residual_cleanup_postings
    returns: list[Posting]
    reads_parameters: []
parameters:
  - id: "&{overpayment_fee_rate}"
    clu_id: overpayment_fee_rate
    constant: OVERPAYMENT_FEE_RATE_PARAM
    ownership: owned
    owner_feature: lending.repayments.overpayment
    level: TEMPLATE
    constraint: decimal_constraint
    clu_resource: feature_library/src/feature_library/lending/repayments/parameter_resource_defs/overpayment_fee_rate.resource.yaml
    optional: false
    triggers_pre_parameter_change_hook: false
    triggers_post_parameter_change_hook: false
    description: ""
    drives: ""
  - id: "&{overpayment_fee_income_account}"
    clu_id: overpayment_fee_income_account
    constant: OVERPAYMENT_FEE_INCOME_ACCOUNT_PARAM
    ownership: owned
    owner_feature: lending.repayments.overpayment
    level: TEMPLATE
    constraint: account_constraint
    clu_resource: feature_library/src/feature_library/lending/repayments/parameter_resource_defs/overpayment_fee_income_account.resource.yaml
    optional: false
    triggers_pre_parameter_change_hook: false
    triggers_post_parameter_change_hook: false
    description: ""
    drives: ""
  - id: "&{overpayment_impact_preference}"
    clu_id: overpayment_impact_preference
    constant: OVERPAYMENT_IMPACT_PREFERENCE_PARAM
    ownership: owned
    owner_feature: lending.repayments.overpayment
    level: TEMPLATE
    constraint: string_constraint
    clu_resource: feature_library/src/feature_library/lending/repayments/parameter_resource_defs/overpayment_impact_preference.resource.yaml
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
  - fetcher_id: overpayment_params_pof
    kind: ParametersObservationFetcher
    declared_in: lending.repayments.overpayment
events: []
event_style: static
notifications: []
balance_addresses:
  - INTERNAL_CONTRA
  - PRINCIPAL
interfaces:
  provides:
    - Overpayment
    - EarlyRepaymentFee
    - ResidualCleanup
  consumes:
    - RepaymentHierarchyConfig
dependencies:
  features:
    - common.addresses
    - common.balance_utils
    - common.denomination
    - common.fees
    - common.posting_utils
    - common.state_utils
    - common.utils
    - lending.addresses
    - lending.interfaces
  used_by:
    - lending.repayments.overpayment_allowance
tests:
  unit: 1
  simulation: 3
  e2e: 0
traceability:
  business_requirements: []
  used_by_products:
    - mortgage
complete: true
---

# Overpayment

> Generated by `python3 -m fl docs`. Curated prose comes from `feature_library/src/feature_library/lending/repayments/overpayment.okf.yaml`; everything else is derived from the module source. Do not edit by hand.

| Property | Value |
|---|---|
| Module | `feature_library.lending.repayments.overpayment` |
| Domain | lending |
| Status | undeclared |
| Version | — |
| Hooks | `post_posting_hook`, `pre_posting_hook` |
| Source | `feature_library/src/feature_library/lending/repayments/overpayment.py` |

## What it does

_Not yet described._

## Traceability: configuration to outcome

Every input below is a value a bank configures. The diagram shows which function consumes it and which hook turns it into an outcome.

```mermaid
graph LR
  subgraph CONFIG[Configuration inputs]
    direction TB
    p_overpayment_fee_rate["&{overpayment_fee_rate}"]
    p_overpayment_fee_income_account["&{overpayment_fee_income_account}"]
    p_overpayment_impact_preference["&{overpayment_impact_preference}"]
    p_denomination["&{denomination}"]
  end
  subgraph DATA[Data fetched at execution]
    direction TB
    d_overpayment_params_pof[/"overpayment_params_pof\n(ParametersObservationFetcher)"/]
  end
  subgraph FEAT["overpayment"]
    direction TB
    f_get_max_overpayment_fee("get_max_overpayment_fee()")
    f_get_overpayment_fee("get_overpayment_fee()")
    f_charge_overpayment_fee_as_penalty("charge_overpayment_fee_as_penalty()")
    f_get_overpayment_fee_postings("get_overpayment_fee_postings()")
    f_is_posting_an_overpayment("is_posting_an_overpayment()")
    f_validate_if_overpayment_is_greater_than_max("validate_if_overpayment_is_greater_than_max()")
    f_get_max_overpayment_amount("get_max_overpayment_amount()")
    f_handle_overpayment("handle_overpayment()")
    f_get_early_repayment_overpayment_fee("get_early_repayment_overpayment_fee()")
    f_skip_charge_early_repayment_fee_for_overpayment("skip_charge_early_repayment_fee_for_overpayment()")
  end
  subgraph HOOKS[Contract hooks]
    direction TB
    h_post_posting_hook[["post_posting_hook"]]
    h_pre_posting_hook[["pre_posting_hook"]]
  end
  subgraph OUT[Outcomes]
    direction TB
    o_0["CustomInstruction[] / notifications"]
    o_1["Rejection | None"]
    o_2["addresses: INTERNAL_CONTRA, PRINCIPAL"]
  end
  p_denomination --> f_charge_overpayment_fee_as_penalty
  p_overpayment_fee_rate --> f_charge_overpayment_fee_as_penalty
  p_overpayment_fee_income_account --> f_charge_overpayment_fee_as_penalty
  p_overpayment_fee_rate --> f_get_max_overpayment_amount
  p_denomination --> f_get_max_overpayment_amount
  p_denomination --> f_handle_overpayment
  p_denomination --> f_get_early_repayment_overpayment_fee
  p_overpayment_fee_rate --> f_get_early_repayment_overpayment_fee
  p_overpayment_impact_preference --> f_get_max_overpayment_fee
  d_overpayment_params_pof --> f_get_max_overpayment_fee
  f_get_max_overpayment_fee --> h_post_posting_hook
  f_get_max_overpayment_fee --> h_pre_posting_hook
  f_get_overpayment_fee --> h_post_posting_hook
  f_get_overpayment_fee --> h_pre_posting_hook
  f_charge_overpayment_fee_as_penalty --> h_post_posting_hook
  f_charge_overpayment_fee_as_penalty --> h_pre_posting_hook
  f_get_overpayment_fee_postings --> h_post_posting_hook
  f_get_overpayment_fee_postings --> h_pre_posting_hook
  f_is_posting_an_overpayment --> h_post_posting_hook
  f_is_posting_an_overpayment --> h_pre_posting_hook
  f_validate_if_overpayment_is_greater_than_max --> h_post_posting_hook
  f_validate_if_overpayment_is_greater_than_max --> h_pre_posting_hook
  f_get_max_overpayment_amount --> h_post_posting_hook
  f_get_max_overpayment_amount --> h_pre_posting_hook
  f_handle_overpayment --> h_post_posting_hook
  f_handle_overpayment --> h_pre_posting_hook
  f_get_early_repayment_overpayment_fee --> h_post_posting_hook
  f_get_early_repayment_overpayment_fee --> h_pre_posting_hook
  f_skip_charge_early_repayment_fee_for_overpayment --> h_post_posting_hook
  f_skip_charge_early_repayment_fee_for_overpayment --> h_pre_posting_hook
  h_post_posting_hook --> o_0
  h_pre_posting_hook --> o_0
  h_post_posting_hook --> o_1
  h_pre_posting_hook --> o_1
  h_post_posting_hook --> o_2
  h_pre_posting_hook --> o_2
```

## Inputs — parameters

| Reference | Meaning | Hierarchy level | Constraint | Required | CLU resource |
|---|---|---|---|---|---|
| `&{overpayment_fee_rate}` | _undocumented_ | — | decimal_constraint | required | `feature_library/src/feature_library/lending/repayments/parameter_resource_defs/overpayment_fee_rate.resource.yaml` |
| `&{overpayment_fee_income_account}` | _undocumented_ | — | account_constraint | required | `feature_library/src/feature_library/lending/repayments/parameter_resource_defs/overpayment_fee_income_account.resource.yaml` |
| `&{overpayment_impact_preference}` | _undocumented_ | — | string_constraint | required | `feature_library/src/feature_library/lending/repayments/parameter_resource_defs/overpayment_impact_preference.resource.yaml` |
| `&{denomination}` | _undocumented_ | — | string_constraint | required | `feature_library/src/feature_library/common/parameter_resource_defs/denomination.resource.yaml` |

## Inputs — data fetched at execution

| Fetcher id | Type | Anchor | Filter |
|---|---|---|---|
| `overpayment_params_pof` | ParametersObservationFetcher | DefinedDateTime.EFFECTIVE_DATETIME | ParametersFilter(parameter_ids=[p.id for p in expected_parameters]) |

## Public API

| Function | Returns | Purpose |
|---|---|---|
| `get_parameters(vault, param_fetcher_id)` | `dict[str, str \| Decimal \| datetime \| None]` | Retrieves configuration parameters for the overpayment feature from the vault. |
| `get_max_overpayment_fee(fee_rate, balances, denomination, precision, principal_address)` | `Decimal` | The maximum overpayment fee is the maximum_overpayment_amount * overpayment_fee_rate. |
| `get_overpayment_fee(principal_repaid, overpayment_fee_rate, precision)` | `Decimal` | Determines the overpayment fee for a given amount of principal being repaid. |
| `charge_overpayment_fee_as_penalty(state, vault, overpayment_amount, precision, fetchers_config)` | `list[CustomInstruction]` | Calculates and generates instructions to charge an overpayment fee as a penalty. |
| `get_overpayment_fee_postings(overpayment_fee, denomination, customer_account_id, customer_account_address, internal_account)` | `list[Posting]` | Creates postings to charge the overpayment fee. |
| `is_posting_an_overpayment(state, repayment_hierarchy_config, repayment_amount, fetchers_config)` | `bool` | Checks whether the given posting involves an overpayment amount. |
| `validate_if_overpayment_is_greater_than_max(state, repayment_amount, repayment_hierarchy_config, fetchers_config)` | `Rejection \| None` | Rejects repayments if the amount exceeds total owed, including Principal, + overpayment fee. |
| `get_max_overpayment_amount(state, repayment_hierarchy_config, fetchers_config)` | `Decimal` | Calculates the maximum allowed overpayment amount. |
| `handle_overpayment(state, overpayment_amount, repay_accrued_interest_callable, principal_address, overpayment_address, fetchers_config)` | `list[Posting]` | Creates postings to handle standard overpayments to principal and accrued interest. |
| `get_early_repayment_overpayment_fee(state, precision, fetchers_config)` | `Decimal` | Get the early repayment overpayment fee amount. |
| `skip_charge_early_repayment_fee_for_overpayment(state, amount_to_charge, fee_name, fetchers_config)` | `list[CustomInstruction]` | Skip the charge for the overpayment fee within an early repayment. |
| `get_residual_cleanup_postings(balances, account_id, denomination)` | `list[Posting]` | Generates postings to net out the overpayment tracker balance. |

## Outputs

| Kind | Values | Notes |
|---|---|---|
| Balance addresses | `INTERNAL_CONTRA`, `PRINCIPAL` | — |

## Composition points

| Provides interface | As constant | Members |
|---|---|---|
| `Overpayment` | `OverpaymentFeature` | `handle_overpayment` |
| `EarlyRepaymentFee` | `EarlyRepaymentOverpaymentFee` | `get_early_repayment_fee_amount`, `charge_early_repayment_fee`, `fee_name` |
| `ResidualCleanup` | `OverpaymentResidualCleanupFeature` | `get_residual_cleanup_postings` |

Accepts: `RepaymentHierarchyConfig`

## Where it sits in the library

```mermaid
graph BT
  me_overpayment["overpayment"]:::self
  dep_common_addresses["common.addresses"] --> me_overpayment
  dep_common_balance_utils["common.balance_utils"] --> me_overpayment
  dep_common_denomination["common.denomination"] --> me_overpayment
  dep_common_fees["common.fees"] --> me_overpayment
  dep_common_posting_utils["common.posting_utils"] --> me_overpayment
  dep_common_state_utils["common.state_utils"] --> me_overpayment
  dep_common_utils["common.utils"] --> me_overpayment
  dep_lending_addresses["lending.addresses"] --> me_overpayment
  dep_lending_interfaces["lending.interfaces"] --> me_overpayment
  me_overpayment --> use_lending_repayments_overpayment_allowance["lending.repayments.overpayment_allowance"]
  me_overpayment ==> prod_mortgage["mortgage"]:::product
  classDef self fill:#dbeafe,stroke:#1d4ed8,stroke-width:2px;
  classDef product fill:#dcfce7,stroke:#15803d,stroke-width:2px;
```

## Requirement traceability

_No business requirement is linked to this feature yet, so it cannot be traced back to a stated need._

## Products using it

- `mortgage`

## Testing

| Tier | Status | Test modules |
|---|---|---|
| Unit | yes | 1 |
| Simulation | yes | 3 |
| End-to-end | **missing** | 0 |

<!-- generated:end -->
