---
type: Vault Parameter
okf_version: "0.2"
profile: https://thoughtmachine.example/fde/schemas/feature-knowledge-bundle/1.0.json
profile_version: 1.0.0
title: welcome_bonus_threshold
description: Cumulative spend threshold required to earn the welcome bonus.
status: stable
tags:
  - parameter
identity:
  clu_id: welcome_bonus_threshold
  reference: "&{welcome_bonus_threshold}"
  constraint: decimal_constraint
  clu_resource: feature_library/src/feature_library/lending/rewards/parameter_resource_defs/welcome_bonus_threshold.resource.yaml
generated:
  by: process:fl/0.1.0
used_by:
  - lending.rewards.welcome_bonus
---

# `&{welcome_bonus_threshold}`

Cumulative spend threshold required to earn the welcome bonus.

**Constraint:** `decimal_constraint`  
**CLU resource:** `feature_library/src/feature_library/lending/rewards/parameter_resource_defs/welcome_bonus_threshold.resource.yaml`

## Referenced by

- [lending.rewards.welcome_bonus](/features/lending/rewards/welcome_bonus.md)

<!-- generated:end -->
