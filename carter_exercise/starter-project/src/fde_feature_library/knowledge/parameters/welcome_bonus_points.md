---
type: Vault Parameter
okf_version: "0.2"
profile: https://thoughtmachine.example/fde/schemas/feature-knowledge-bundle/1.0.json
profile_version: 1.0.0
title: welcome_bonus_points
description: Number of bonus points awarded when the welcome bonus spend threshold is met.
status: stable
tags:
  - parameter
identity:
  clu_id: welcome_bonus_points
  reference: "&{welcome_bonus_points}"
  constraint: decimal_constraint
  clu_resource: feature_library/src/feature_library/lending/rewards/parameter_resource_defs/welcome_bonus_points.resource.yaml
generated:
  by: process:fl/0.1.0
used_by:
  - lending.rewards.welcome_bonus
---

# `&{welcome_bonus_points}`

Number of bonus points awarded when the welcome bonus spend threshold is met.

**Constraint:** `decimal_constraint`  
**CLU resource:** `feature_library/src/feature_library/lending/rewards/parameter_resource_defs/welcome_bonus_points.resource.yaml`

## Referenced by

- [lending.rewards.welcome_bonus](/features/lending/rewards/welcome_bonus.md)

<!-- generated:end -->
