---
type: Vault Parameter
okf_version: "0.2"
profile: https://thoughtmachine.example/fde/schemas/feature-knowledge-bundle/1.0.json
profile_version: 1.0.0
title: maximum_monthly_payment_type_withdrawal_limit
description: Triggers pre-parameter change hook? No.  Optional? No.
status: stable
tags:
  - parameter
identity:
  clu_id: maximum_monthly_payment_type_withdrawal_limit
  reference: "&{maximum_monthly_payment_type_withdrawal_limit}"
  constraint: string_constraint
  clu_resource: feature_library/src/feature_library/deposit/fees/withdrawal/parameter_resource_defs/maximum_monthly_payment_type_withdrawal_limit.resource.yaml
generated:
  by: process:fl/0.1.0
used_by:
  - deposit.fees.withdrawal.payment_type_monthly_limit_fee
---

# `&{maximum_monthly_payment_type_withdrawal_limit}`

Triggers pre-parameter change hook? No.  Optional? No.

**Constraint:** `string_constraint`  
**CLU resource:** `feature_library/src/feature_library/deposit/fees/withdrawal/parameter_resource_defs/maximum_monthly_payment_type_withdrawal_limit.resource.yaml`

## Referenced by

- [deposit.fees.withdrawal.payment_type_monthly_limit_fee](/features/deposit/fees/withdrawal/payment_type_monthly_limit_fee.md)

<!-- generated:end -->
