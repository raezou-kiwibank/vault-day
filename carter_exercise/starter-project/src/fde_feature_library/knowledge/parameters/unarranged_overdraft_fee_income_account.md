---
type: Vault Parameter
okf_version: "0.2"
profile: https://thoughtmachine.example/fde/schemas/feature-knowledge-bundle/1.0.json
profile_version: 1.0.0
title: unarranged_overdraft_fee_income_account
description: Triggers pre-parameter change hook? No.  Optional? Yes.
status: stable
tags:
  - parameter
identity:
  clu_id: unarranged_overdraft_fee_income_account
  reference: "&{unarranged_overdraft_fee_income_account}"
  constraint: account_constraint
  clu_resource: feature_library/src/feature_library/deposit/fees/parameter_resource_defs/unarranged_overdraft_fee_income_account.resource.yaml
generated:
  by: process:fl/0.1.0
used_by:
  - deposit.fees.unarranged_overdraft_fee
---

# `&{unarranged_overdraft_fee_income_account}`

Triggers pre-parameter change hook? No.  Optional? Yes.

**Constraint:** `account_constraint`  
**CLU resource:** `feature_library/src/feature_library/deposit/fees/parameter_resource_defs/unarranged_overdraft_fee_income_account.resource.yaml`

## Referenced by

- [deposit.fees.unarranged_overdraft_fee](/features/deposit/fees/unarranged_overdraft_fee.md)

<!-- generated:end -->
