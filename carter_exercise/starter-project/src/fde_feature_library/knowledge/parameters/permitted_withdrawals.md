---
type: Vault Parameter
okf_version: "0.2"
profile: https://thoughtmachine.example/fde/schemas/feature-knowledge-bundle/1.0.json
profile_version: 1.0.0
title: permitted_withdrawals
description: Number of monthly permitted withdrawals. Please note that only transactions with the specified transaction type are counted towards this excess fee. Triggers pre-parameter change hook? No.  Optional? No.
status: stable
tags:
  - parameter
identity:
  clu_id: permitted_withdrawals
  reference: "&{permitted_withdrawals}"
  constraint: decimal_constraint
  clu_resource: feature_library/src/feature_library/deposit/fees/withdrawal/parameter_resource_defs/permitted_withdrawals.resource.yaml
generated:
  by: process:fl/0.1.0
used_by:
  - deposit.fees.withdrawal.excess_fee
---

# `&{permitted_withdrawals}`

Number of monthly permitted withdrawals. Please note that only transactions with the specified transaction type are counted towards this excess fee. Triggers pre-parameter change hook? No.  Optional? No.

**Constraint:** `decimal_constraint`  
**CLU resource:** `feature_library/src/feature_library/deposit/fees/withdrawal/parameter_resource_defs/permitted_withdrawals.resource.yaml`

## Referenced by

- [deposit.fees.withdrawal.excess_fee](/features/deposit/fees/withdrawal/excess_fee.md)

<!-- generated:end -->
