---
type: Vault Parameter
okf_version: "0.2"
profile: https://thoughtmachine.example/fde/schemas/feature-knowledge-bundle/1.0.json
profile_version: 1.0.0
title: daily_withdrawal_limit_by_transaction_type
description: Triggers pre-parameter change hook? No.  Optional? True.
status: stable
tags:
  - parameter
identity:
  clu_id: daily_withdrawal_limit_by_transaction_type
  reference: "&{daily_withdrawal_limit_by_transaction_type}"
  constraint: string_constraint
  clu_resource: feature_library/src/feature_library/deposit/transaction_limits/withdrawal_limits/parameter_resource_defs/daily_withdrawal_limit_by_transaction_type.resource.yaml
generated:
  by: process:fl/0.1.0
used_by:
  - deposit.transaction_limits.withdrawal_limits.maximum_daily_withdrawal_by_transaction_type
---

# `&{daily_withdrawal_limit_by_transaction_type}`

Triggers pre-parameter change hook? No.  Optional? True.

**Constraint:** `string_constraint`  
**CLU resource:** `feature_library/src/feature_library/deposit/transaction_limits/withdrawal_limits/parameter_resource_defs/daily_withdrawal_limit_by_transaction_type.resource.yaml`

## Referenced by

- [deposit.transaction_limits.withdrawal_limits.maximum_daily_withdrawal_by_transaction_type](/features/deposit/transaction_limits/withdrawal_limits/maximum_daily_withdrawal_by_transaction_type.md)

<!-- generated:end -->
