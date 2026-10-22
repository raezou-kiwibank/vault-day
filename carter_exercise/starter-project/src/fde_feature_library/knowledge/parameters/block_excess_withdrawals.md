---
type: Vault Parameter
okf_version: "0.2"
profile: https://thoughtmachine.example/fde/schemas/feature-knowledge-bundle/1.0.json
profile_version: 1.0.0
title: block_excess_withdrawals
description: When configured, if the number of permitted withdrawals is exceeded, any subsequent withdrawals are blocked. If this is not configured, the withdrawal is accepted and the Excess Fee will be applied. Triggers pre-parameter change hook? No.  Optional? No.
status: stable
tags:
  - parameter
identity:
  clu_id: block_excess_withdrawals
  reference: "&{block_excess_withdrawals}"
  constraint: enumeration_constraint
  clu_resource: feature_library/src/feature_library/deposit/fees/withdrawal/parameter_resource_defs/block_excess_withdrawals.resource.yaml
generated:
  by: process:fl/0.1.0
used_by:
  - deposit.fees.withdrawal.excess_fee
---

# `&{block_excess_withdrawals}`

When configured, if the number of permitted withdrawals is exceeded, any subsequent withdrawals are blocked. If this is not configured, the withdrawal is accepted and the Excess Fee will be applied. Triggers pre-parameter change hook? No.  Optional? No.

**Constraint:** `enumeration_constraint`  
**CLU resource:** `feature_library/src/feature_library/deposit/fees/withdrawal/parameter_resource_defs/block_excess_withdrawals.resource.yaml`

## Referenced by

- [deposit.fees.withdrawal.excess_fee](/features/deposit/fees/withdrawal/excess_fee.md)

<!-- generated:end -->
