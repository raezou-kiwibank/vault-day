---
type: Vault Parameter
okf_version: "0.2"
profile: https://thoughtmachine.example/fde/schemas/feature-knowledge-bundle/1.0.json
profile_version: 1.0.0
title: variable_interest_rate
description: Vault parameter variable_interest_rate.
status: stable
tags:
  - parameter
identity:
  clu_id: variable_interest_rate
  reference: "&{variable_interest_rate}"
  constraint: decimal_constraint
  clu_resource: feature_library/src/feature_library/lending/interest/secondary/parameter_resource_defs/variable_interest_rate.resource.yaml
generated:
  by: process:fl/0.1.0
used_by:
  - lending.interest.secondary.variable_rate
---

# `&{variable_interest_rate}`

_No description in the resource definition._

**Constraint:** `decimal_constraint`  
**CLU resource:** `feature_library/src/feature_library/lending/interest/secondary/parameter_resource_defs/variable_interest_rate.resource.yaml`

## Referenced by

- [lending.interest.secondary.variable_rate](/features/lending/interest/secondary/variable_rate.md)

<!-- generated:end -->
