---
type: Vault Parameter
okf_version: "0.2"
profile: https://thoughtmachine.example/fde/schemas/feature-knowledge-bundle/1.0.json
profile_version: 1.0.0
title: tiered_minimum_balance_threshold
description: Triggers pre-parameter change hook? No.  Optional? True.
status: stable
tags:
  - parameter
identity:
  clu_id: tiered_minimum_balance_threshold
  reference: "&{tiered_minimum_balance_threshold}"
  constraint: string_constraint
  clu_resource: feature_library/src/feature_library/deposit/transaction_limits/withdrawal_limits/parameter_resource_defs/tiered_minimum_balance_threshold.resource.yaml
generated:
  by: process:fl/0.1.0
used_by:
  - deposit.transaction_limits.withdrawal_limits.minimum_balance_by_tier
---

# `&{tiered_minimum_balance_threshold}`

Triggers pre-parameter change hook? No.  Optional? True.

**Constraint:** `string_constraint`  
**CLU resource:** `feature_library/src/feature_library/deposit/transaction_limits/withdrawal_limits/parameter_resource_defs/tiered_minimum_balance_threshold.resource.yaml`

## Referenced by

- [deposit.transaction_limits.withdrawal_limits.minimum_balance_by_tier](/features/deposit/transaction_limits/withdrawal_limits/minimum_balance_by_tier.md)

<!-- generated:end -->
