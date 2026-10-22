---
type: Vault Parameter
okf_version: "0.2"
profile: https://thoughtmachine.example/fde/schemas/feature-knowledge-bundle/1.0.json
profile_version: 1.0.0
title: partial_maintenance_fee_enabled
description: Triggers pre-parameter change hook? No.  Optional? Yes.
status: stable
tags:
  - parameter
identity:
  clu_id: partial_maintenance_fee_enabled
  reference: "&{partial_maintenance_fee_enabled}"
  constraint: enumeration_constraint
  clu_resource: feature_library/src/feature_library/deposit/fees/parameter_resource_defs/partial_maintenance_fee_enabled.resource.yaml
generated:
  by: process:fl/0.1.0
used_by:
  - deposit.fees.maintenance_fees
---

# `&{partial_maintenance_fee_enabled}`

Triggers pre-parameter change hook? No.  Optional? Yes.

**Constraint:** `enumeration_constraint`  
**CLU resource:** `feature_library/src/feature_library/deposit/fees/parameter_resource_defs/partial_maintenance_fee_enabled.resource.yaml`

## Referenced by

- [deposit.fees.maintenance_fees](/features/deposit/fees/maintenance_fees.md)

<!-- generated:end -->
