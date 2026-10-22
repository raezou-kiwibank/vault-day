---
type: Vault Parameter
okf_version: "0.2"
profile: https://thoughtmachine.example/fde/schemas/feature-knowledge-bundle/1.0.json
profile_version: 1.0.0
title: points_rate_travel_portal
description: Points earned per unit of currency spent on travel portal bookings.
status: stable
tags:
  - parameter
identity:
  clu_id: points_rate_travel_portal
  reference: "&{points_rate_travel_portal}"
  constraint: decimal_constraint
  clu_resource: feature_library/src/feature_library/lending/rewards/parameter_resource_defs/points_rate_travel_portal.resource.yaml
generated:
  by: process:fl/0.1.0
used_by:
  - lending.rewards.points_accrual
---

# `&{points_rate_travel_portal}`

Points earned per unit of currency spent on travel portal bookings.

**Constraint:** `decimal_constraint`  
**CLU resource:** `feature_library/src/feature_library/lending/rewards/parameter_resource_defs/points_rate_travel_portal.resource.yaml`

## Referenced by

- [lending.rewards.points_accrual](/features/lending/rewards/points_accrual.md)

<!-- generated:end -->
