---
type: Vault Parameter
okf_version: "0.2"
profile: https://thoughtmachine.example/fde/schemas/feature-knowledge-bundle/1.0.json
profile_version: 1.0.0
title: minimum_initial_deposit
description: Triggers pre-parameter change hook? No.  Optional? No.
status: stable
tags:
  - parameter
identity:
  clu_id: minimum_initial_deposit
  reference: "&{minimum_initial_deposit}"
  constraint: decimal_constraint
  clu_resource: feature_library/src/feature_library/deposit/transaction_limits/deposit_limits/parameter_resource_defs/minimum_initial_deposit.resource.yaml
generated:
  by: process:fl/0.1.0
used_by:
  - deposit.transaction_limits.deposit_limits.minimum_initial_deposit
---

# `&{minimum_initial_deposit}`

Triggers pre-parameter change hook? No.  Optional? No.

**Constraint:** `decimal_constraint`  
**CLU resource:** `feature_library/src/feature_library/deposit/transaction_limits/deposit_limits/parameter_resource_defs/minimum_initial_deposit.resource.yaml`

## Referenced by

- [deposit.transaction_limits.deposit_limits.minimum_initial_deposit](/features/deposit/transaction_limits/deposit_limits/minimum_initial_deposit.md)

<!-- generated:end -->
