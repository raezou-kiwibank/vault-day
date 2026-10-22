---
type: Vault Parameter
okf_version: "0.2"
profile: https://thoughtmachine.example/fde/schemas/feature-knowledge-bundle/1.0.json
profile_version: 1.0.0
title: check_overdue_time
description: Vault parameter check_overdue_time.
status: stable
tags:
  - parameter
identity:
  clu_id: check_overdue_time
  reference: "&{check_overdue_time}"
  constraint: string_constraint
  clu_resource: feature_library/src/feature_library/lending/overdue/parameter_resource_defs/check_overdue_time.resource.yaml
generated:
  by: process:fl/0.1.0
used_by:
  - lending.overdue.overdue
---

# `&{check_overdue_time}`

_No description in the resource definition._

**Constraint:** `string_constraint`  
**CLU resource:** `feature_library/src/feature_library/lending/overdue/parameter_resource_defs/check_overdue_time.resource.yaml`

## Referenced by

- [lending.overdue.overdue](/features/lending/overdue/overdue.md)

<!-- generated:end -->
