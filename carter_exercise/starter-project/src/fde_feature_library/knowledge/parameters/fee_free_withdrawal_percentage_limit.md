---
type: Vault Parameter
okf_version: "0.2"
profile: https://thoughtmachine.example/fde/schemas/feature-knowledge-bundle/1.0.json
profile_version: 1.0.0
title: fee_free_withdrawal_percentage_limit
description: Triggers pre-parameter change hook? No.  Optional? No.
status: stable
tags:
  - parameter
identity:
  clu_id: fee_free_withdrawal_percentage_limit
  reference: "&{fee_free_withdrawal_percentage_limit}"
  constraint: decimal_constraint
  clu_resource: feature_library/src/feature_library/deposit/fees/withdrawal/parameter_resource_defs/fee_free_withdrawal_percentage_limit.resource.yaml
generated:
  by: process:fl/0.1.0
used_by:
  - deposit.fees.withdrawal.early_withdrawal_fees
---

# `&{fee_free_withdrawal_percentage_limit}`

Triggers pre-parameter change hook? No.  Optional? No.

**Constraint:** `decimal_constraint`  
**CLU resource:** `feature_library/src/feature_library/deposit/fees/withdrawal/parameter_resource_defs/fee_free_withdrawal_percentage_limit.resource.yaml`

## Referenced by

- [deposit.fees.withdrawal.early_withdrawal_fees](/features/deposit/fees/withdrawal/early_withdrawal_fees.md)

<!-- generated:end -->
