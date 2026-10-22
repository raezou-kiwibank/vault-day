---
type: Vault Parameter
okf_version: "0.2"
profile: https://thoughtmachine.example/fde/schemas/feature-knowledge-bundle/1.0.json
profile_version: 1.0.0
title: maximum_payment_type_withdrawal
description: Triggers pre-parameter change hook? No.  Optional? True.
status: stable
tags:
  - parameter
identity:
  clu_id: maximum_payment_type_withdrawal
  reference: "&{maximum_payment_type_withdrawal}"
  constraint: string_constraint
  clu_resource: feature_library/src/feature_library/deposit/transaction_limits/withdrawal_limits/parameter_resource_defs/maximum_payment_type_withdrawal.resource.yaml
generated:
  by: process:fl/0.1.0
used_by:
  - deposit.transaction_limits.withdrawal_limits.maximum_withdrawal_by_payment_type
---

# `&{maximum_payment_type_withdrawal}`

Triggers pre-parameter change hook? No.  Optional? True.

**Constraint:** `string_constraint`  
**CLU resource:** `feature_library/src/feature_library/deposit/transaction_limits/withdrawal_limits/parameter_resource_defs/maximum_payment_type_withdrawal.resource.yaml`

## Referenced by

- [deposit.transaction_limits.withdrawal_limits.maximum_withdrawal_by_payment_type](/features/deposit/transaction_limits/withdrawal_limits/maximum_withdrawal_by_payment_type.md)

<!-- generated:end -->
