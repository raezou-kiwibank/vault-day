---
type: Vault Parameter
okf_version: "0.2"
profile: https://thoughtmachine.example/fde/schemas/feature-knowledge-bundle/1.0.json
profile_version: 1.0.0
title: early_closure_fee_income_account
description: Triggers pre-parameter change hook? No.  Optional? No.
status: stable
tags:
  - parameter
identity:
  clu_id: early_closure_fee_income_account
  reference: "&{early_closure_fee_income_account}"
  constraint: account_constraint
  clu_resource: feature_library/src/feature_library/deposit/fees/parameter_resource_defs/early_closure_fee_income_account.resource.yaml
generated:
  by: process:fl/0.1.0
used_by:
  - deposit.fees.early_closure_fee
---

# `&{early_closure_fee_income_account}`

Triggers pre-parameter change hook? No.  Optional? No.

**Constraint:** `account_constraint`  
**CLU resource:** `feature_library/src/feature_library/deposit/fees/parameter_resource_defs/early_closure_fee_income_account.resource.yaml`

## Referenced by

- [deposit.fees.early_closure_fee](/features/deposit/fees/early_closure_fee.md)

<!-- generated:end -->
