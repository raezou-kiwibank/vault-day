---
type: Vault Parameter
okf_version: "0.2"
profile: https://thoughtmachine.example/fde/schemas/feature-knowledge-bundle/1.0.json
profile_version: 1.0.0
title: early_withdrawal_flat_fee
description: Triggers pre-parameter change hook? No.  Optional? No.
status: stable
tags:
  - parameter
identity:
  clu_id: early_withdrawal_flat_fee
  reference: "&{early_withdrawal_flat_fee}"
  constraint: decimal_constraint
  clu_resource: feature_library/src/feature_library/deposit/fees/withdrawal/parameter_resource_defs/early_withdrawal_flat_fee.resource.yaml
generated:
  by: process:fl/0.1.0
used_by:
  - deposit.fees.withdrawal.early_withdrawal_fees
---

# `&{early_withdrawal_flat_fee}`

Triggers pre-parameter change hook? No.  Optional? No.

**Constraint:** `decimal_constraint`  
**CLU resource:** `feature_library/src/feature_library/deposit/fees/withdrawal/parameter_resource_defs/early_withdrawal_flat_fee.resource.yaml`

## Referenced by

- [deposit.fees.withdrawal.early_withdrawal_fees](/features/deposit/fees/withdrawal/early_withdrawal_fees.md)

<!-- generated:end -->
