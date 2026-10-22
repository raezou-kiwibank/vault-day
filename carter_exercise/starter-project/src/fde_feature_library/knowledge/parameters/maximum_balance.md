---
type: Vault Parameter
okf_version: "0.2"
profile: https://thoughtmachine.example/fde/schemas/feature-knowledge-bundle/1.0.json
profile_version: 1.0.0
title: maximum_balance
description: Triggers pre-parameter change hook? No.  Optional? No.
status: stable
tags:
  - parameter
identity:
  clu_id: maximum_balance
  reference: "&{maximum_balance}"
  constraint: decimal_constraint
  clu_resource: feature_library/src/feature_library/deposit/transaction_limits/deposit_limits/parameter_resource_defs/maximum_balance.resource.yaml
generated:
  by: process:fl/0.1.0
used_by:
  - deposit.transaction_limits.deposit_limits.maximum_balance_limit
---

# `&{maximum_balance}`

Triggers pre-parameter change hook? No.  Optional? No.

**Constraint:** `decimal_constraint`  
**CLU resource:** `feature_library/src/feature_library/deposit/transaction_limits/deposit_limits/parameter_resource_defs/maximum_balance.resource.yaml`

## Referenced by

- [deposit.transaction_limits.deposit_limits.maximum_balance_limit](/features/deposit/transaction_limits/deposit_limits/maximum_balance_limit.md)

<!-- generated:end -->
