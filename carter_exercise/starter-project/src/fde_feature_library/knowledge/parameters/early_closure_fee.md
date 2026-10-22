---
type: Vault Parameter
okf_version: "0.2"
profile: https://thoughtmachine.example/fde/schemas/feature-knowledge-bundle/1.0.json
profile_version: 1.0.0
title: early_closure_fee
description: Triggers pre-parameter change hook? No.  Optional? No.
status: stable
tags:
  - parameter
identity:
  clu_id: early_closure_fee
  reference: "&{early_closure_fee}"
  constraint: decimal_constraint
  clu_resource: feature_library/src/feature_library/deposit/fees/parameter_resource_defs/early_closure_fee.resource.yaml
generated:
  by: process:fl/0.1.0
used_by:
  - deposit.fees.early_closure_fee
---

# `&{early_closure_fee}`

Triggers pre-parameter change hook? No.  Optional? No.

**Constraint:** `decimal_constraint`  
**CLU resource:** `feature_library/src/feature_library/deposit/fees/parameter_resource_defs/early_closure_fee.resource.yaml`

## Referenced by

- [deposit.fees.early_closure_fee](/features/deposit/fees/early_closure_fee.md)

<!-- generated:end -->
