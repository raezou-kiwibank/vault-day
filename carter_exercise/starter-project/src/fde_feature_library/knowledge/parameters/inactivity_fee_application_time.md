---
type: Vault Parameter
okf_version: "0.2"
profile: https://thoughtmachine.example/fde/schemas/feature-knowledge-bundle/1.0.json
profile_version: 1.0.0
title: inactivity_fee_application_time
description: Format "HH:mm:ss".  Triggers pre-parameter change hook? No.  Optional? No.
status: stable
tags:
  - parameter
identity:
  clu_id: inactivity_fee_application_time
  reference: "&{inactivity_fee_application_time}"
  constraint: string_constraint
  clu_resource: feature_library/src/feature_library/deposit/fees/parameter_resource_defs/inactivity_fee_application_time.resource.yaml
generated:
  by: process:fl/0.1.0
used_by:
  - deposit.fees.inactivity_fee
---

# `&{inactivity_fee_application_time}`

Format "HH:mm:ss".  Triggers pre-parameter change hook? No.  Optional? No.

**Constraint:** `string_constraint`  
**CLU resource:** `feature_library/src/feature_library/deposit/fees/parameter_resource_defs/inactivity_fee_application_time.resource.yaml`

## Referenced by

- [deposit.fees.inactivity_fee](/features/deposit/fees/inactivity_fee.md)

<!-- generated:end -->
