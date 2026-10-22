---
type: Vault Parameter
okf_version: "0.2"
profile: https://thoughtmachine.example/fde/schemas/feature-knowledge-bundle/1.0.json
profile_version: 1.0.0
title: payment_type_fee_income_account
description: Triggers pre-parameter change hook? No.  Optional? No.
status: stable
tags:
  - parameter
identity:
  clu_id: payment_type_fee_income_account
  reference: "&{payment_type_fee_income_account}"
  constraint: account_constraint
  clu_resource: feature_library/src/feature_library/deposit/fees/withdrawal/parameter_resource_defs/payment_type_fee_income_account.resource.yaml
generated:
  by: process:fl/0.1.0
used_by:
  - deposit.fees.withdrawal.payment_type_flat_fee
  - deposit.fees.withdrawal.payment_type_monthly_limit_fee
  - deposit.fees.withdrawal.payment_type_threshold_fee
---

# `&{payment_type_fee_income_account}`

Triggers pre-parameter change hook? No.  Optional? No.

**Constraint:** `account_constraint`  
**CLU resource:** `feature_library/src/feature_library/deposit/fees/withdrawal/parameter_resource_defs/payment_type_fee_income_account.resource.yaml`

## Referenced by

- [deposit.fees.withdrawal.payment_type_flat_fee](/features/deposit/fees/withdrawal/payment_type_flat_fee.md)
- [deposit.fees.withdrawal.payment_type_monthly_limit_fee](/features/deposit/fees/withdrawal/payment_type_monthly_limit_fee.md)
- [deposit.fees.withdrawal.payment_type_threshold_fee](/features/deposit/fees/withdrawal/payment_type_threshold_fee.md)

<!-- generated:end -->
