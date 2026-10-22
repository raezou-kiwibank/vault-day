---
type: Vault Parameter
okf_version: "0.2"
profile: https://thoughtmachine.example/fde/schemas/feature-knowledge-bundle/1.0.json
profile_version: 1.0.0
title: minimum_deposit
description: Triggers pre-parameter change hook? No.  Optional? Yes.
status: stable
tags:
  - parameter
identity:
  clu_id: minimum_deposit
  reference: "&{minimum_deposit}"
  constraint: decimal_constraint
  clu_resource: feature_library/src/feature_library/deposit/transaction_limits/deposit_limits/parameter_resource_defs/minimum_deposit.resource.yaml
generated:
  by: process:fl/0.1.0
used_by:
  - deposit.transaction_limits.deposit_limits.minimum_single_deposit
---

# `&{minimum_deposit}`

Triggers pre-parameter change hook? No.  Optional? Yes.

**Constraint:** `decimal_constraint`  
**CLU resource:** `feature_library/src/feature_library/deposit/transaction_limits/deposit_limits/parameter_resource_defs/minimum_deposit.resource.yaml`

## Referenced by

- [deposit.transaction_limits.deposit_limits.minimum_single_deposit](/features/deposit/transaction_limits/deposit_limits/minimum_single_deposit.md)

<!-- generated:end -->
