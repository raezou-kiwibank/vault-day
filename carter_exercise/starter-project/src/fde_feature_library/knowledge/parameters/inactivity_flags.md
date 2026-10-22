---
type: Vault Parameter
okf_version: "0.2"
profile: https://thoughtmachine.example/fde/schemas/feature-knowledge-bundle/1.0.json
profile_version: 1.0.0
title: inactivity_flags
description: Triggers pre-parameter change hook? No.  Optional? No.
status: stable
tags:
  - parameter
identity:
  clu_id: inactivity_flags
  reference: "&{inactivity_flags}"
  constraint: string_constraint
  clu_resource: feature_library/src/feature_library/deposit/fees/parameter_resource_defs/inactivity_flags.resource.yaml
generated:
  by: process:fl/0.1.0
used_by:
  - deposit.fees.inactivity_fee
---

# `&{inactivity_flags}`

Triggers pre-parameter change hook? No.  Optional? No.

**Constraint:** `string_constraint`  
**CLU resource:** `feature_library/src/feature_library/deposit/fees/parameter_resource_defs/inactivity_flags.resource.yaml`

## Referenced by

- [deposit.fees.inactivity_fee](/features/deposit/fees/inactivity_fee.md)

<!-- generated:end -->
