---
type: Vault Parameter
okf_version: "0.2"
profile: https://thoughtmachine.example/fde/schemas/feature-knowledge-bundle/1.0.json
profile_version: 1.0.0
title: tiered_daily_withdrawal_limits
description: Triggers pre-parameter change hook? No.  Optional? True.
status: stable
tags:
  - parameter
identity:
  clu_id: tiered_daily_withdrawal_limits
  reference: "&{tiered_daily_withdrawal_limits}"
  constraint: string_constraint
  clu_resource: feature_library/src/feature_library/deposit/transaction_limits/withdrawal_limits/parameter_resource_defs/tiered_daily_withdrawal_limits.resource.yaml
generated:
  by: process:fl/0.1.0
used_by:
  - deposit.transaction_limits.withdrawal_limits.maximum_daily_withdrawal_by_transaction_type
---

# `&{tiered_daily_withdrawal_limits}`

Triggers pre-parameter change hook? No.  Optional? True.

**Constraint:** `string_constraint`  
**CLU resource:** `feature_library/src/feature_library/deposit/transaction_limits/withdrawal_limits/parameter_resource_defs/tiered_daily_withdrawal_limits.resource.yaml`

## Referenced by

- [deposit.transaction_limits.withdrawal_limits.maximum_daily_withdrawal_by_transaction_type](/features/deposit/transaction_limits/withdrawal_limits/maximum_daily_withdrawal_by_transaction_type.md)

<!-- generated:end -->
