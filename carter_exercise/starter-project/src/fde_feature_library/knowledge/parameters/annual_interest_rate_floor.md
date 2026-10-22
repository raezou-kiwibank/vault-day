---
type: Vault Parameter
okf_version: "0.2"
profile: https://thoughtmachine.example/fde/schemas/feature-knowledge-bundle/1.0.json
profile_version: 1.0.0
title: annual_interest_rate_floor
description: Vault parameter annual_interest_rate_floor.
status: stable
tags:
  - parameter
identity:
  clu_id: annual_interest_rate_floor
  reference: "&{annual_interest_rate_floor}"
  constraint: decimal_constraint
  clu_resource: feature_library/src/feature_library/lending/interest/secondary/parameter_resource_defs/annual_interest_rate_floor.resource.yaml
generated:
  by: process:fl/0.1.0
used_by:
  - lending.interest.secondary.variable_rate
---

# `&{annual_interest_rate_floor}`

_No description in the resource definition._

**Constraint:** `decimal_constraint`  
**CLU resource:** `feature_library/src/feature_library/lending/interest/secondary/parameter_resource_defs/annual_interest_rate_floor.resource.yaml`

## Referenced by

- [lending.interest.secondary.variable_rate](/features/lending/interest/secondary/variable_rate.md)

<!-- generated:end -->
