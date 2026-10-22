---
type: Vault Parameter
okf_version: "0.2"
profile: https://thoughtmachine.example/fde/schemas/feature-knowledge-bundle/1.0.json
profile_version: 1.0.0
title: dormancy_flags
description: Triggers pre-parameter change hook? No.  Optional? No.
status: stable
tags:
  - parameter
identity:
  clu_id: dormancy_flags
  reference: "&{dormancy_flags}"
  constraint: string_constraint
  clu_resource: feature_library/src/feature_library/deposit/dormancy/parameter_resource_defs/dormancy_flags.resource.yaml
generated:
  by: process:fl/0.1.0
used_by:
  - deposit.dormancy.dormancy
---

# `&{dormancy_flags}`

Triggers pre-parameter change hook? No.  Optional? No.

**Constraint:** `string_constraint`  
**CLU resource:** `feature_library/src/feature_library/deposit/dormancy/parameter_resource_defs/dormancy_flags.resource.yaml`

## Referenced by

- [deposit.dormancy.dormancy](/features/deposit/dormancy/dormancy.md)

<!-- generated:end -->
