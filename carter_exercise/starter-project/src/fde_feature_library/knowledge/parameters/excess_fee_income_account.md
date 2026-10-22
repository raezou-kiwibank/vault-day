---
type: Vault Parameter
okf_version: "0.2"
profile: https://thoughtmachine.example/fde/schemas/feature-knowledge-bundle/1.0.json
profile_version: 1.0.0
title: excess_fee_income_account
description: Internal account for excess fee income balance. Triggers pre-parameter change hook? No.  Optional? No.
status: stable
tags:
  - parameter
identity:
  clu_id: excess_fee_income_account
  reference: "&{excess_fee_income_account}"
  constraint: account_constraint
  clu_resource: feature_library/src/feature_library/deposit/fees/withdrawal/parameter_resource_defs/excess_fee_income_account.resource.yaml
generated:
  by: process:fl/0.1.0
used_by:
  - deposit.fees.withdrawal.excess_fee
---

# `&{excess_fee_income_account}`

Internal account for excess fee income balance. Triggers pre-parameter change hook? No.  Optional? No.

**Constraint:** `account_constraint`  
**CLU resource:** `feature_library/src/feature_library/deposit/fees/withdrawal/parameter_resource_defs/excess_fee_income_account.resource.yaml`

## Referenced by

- [deposit.fees.withdrawal.excess_fee](/features/deposit/fees/withdrawal/excess_fee.md)

<!-- generated:end -->
