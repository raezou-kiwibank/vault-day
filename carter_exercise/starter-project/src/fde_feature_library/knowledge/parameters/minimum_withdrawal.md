---
type: Vault Parameter
okf_version: "0.2"
profile: https://thoughtmachine.example/fde/schemas/feature-knowledge-bundle/1.0.json
profile_version: 1.0.0
title: minimum_withdrawal
description: Triggers pre-parameter change hook? No.  Optional? True.
status: stable
tags:
  - parameter
identity:
  clu_id: minimum_withdrawal
  reference: "&{minimum_withdrawal}"
  constraint: decimal_constraint
  clu_resource: feature_library/src/feature_library/deposit/transaction_limits/withdrawal_limits/parameter_resource_defs/minimum_withdrawal.resource.yaml
generated:
  by: process:fl/0.1.0
used_by:
  - deposit.transaction_limits.withdrawal_limits.minimum_single_withdrawal
---

# `&{minimum_withdrawal}`

Triggers pre-parameter change hook? No.  Optional? True.

**Constraint:** `decimal_constraint`  
**CLU resource:** `feature_library/src/feature_library/deposit/transaction_limits/withdrawal_limits/parameter_resource_defs/minimum_withdrawal.resource.yaml`

## Referenced by

- [deposit.transaction_limits.withdrawal_limits.minimum_single_withdrawal](/features/deposit/transaction_limits/withdrawal_limits/minimum_single_withdrawal.md)

<!-- generated:end -->
