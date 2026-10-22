---
type: Vault Parameter
okf_version: "0.2"
profile: https://thoughtmachine.example/fde/schemas/feature-knowledge-bundle/1.0.json
profile_version: 1.0.0
title: check_delinquency_time
description: Vault parameter check_delinquency_time.
status: stable
tags:
  - parameter
identity:
  clu_id: check_delinquency_time
  reference: "&{check_delinquency_time}"
  constraint: string_constraint
  clu_resource: feature_library/src/feature_library/lending/delinquency/parameter_resource_defs/check_delinquency_time.resource.yaml
generated:
  by: process:fl/0.1.0
used_by:
  - lending.delinquency.delinquency
---

# `&{check_delinquency_time}`

_No description in the resource definition._

**Constraint:** `string_constraint`  
**CLU resource:** `feature_library/src/feature_library/lending/delinquency/parameter_resource_defs/check_delinquency_time.resource.yaml`

## Referenced by

- [lending.delinquency.delinquency](/features/lending/delinquency/delinquency.md)

<!-- generated:end -->
