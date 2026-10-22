---
type: Vault Parameter
okf_version: "0.2"
profile: https://thoughtmachine.example/fde/schemas/feature-knowledge-bundle/1.0.json
profile_version: 1.0.0
title: minimum_balance_fee_income_account
description: Triggers pre-parameter change hook? No.  Optional? No.
status: stable
tags:
  - parameter
identity:
  clu_id: minimum_balance_fee_income_account
  reference: "&{minimum_balance_fee_income_account}"
  constraint: account_constraint
  clu_resource: feature_library/src/feature_library/deposit/fees/parameter_resource_defs/minimum_balance_fee_income_account.resource.yaml
generated:
  by: process:fl/0.1.0
used_by:
  - deposit.fees.minimum_monthly_balance
---

# `&{minimum_balance_fee_income_account}`

Triggers pre-parameter change hook? No.  Optional? No.

**Constraint:** `account_constraint`  
**CLU resource:** `feature_library/src/feature_library/deposit/fees/parameter_resource_defs/minimum_balance_fee_income_account.resource.yaml`

## Referenced by

- [deposit.fees.minimum_monthly_balance](/features/deposit/fees/minimum_monthly_balance.md)

<!-- generated:end -->
