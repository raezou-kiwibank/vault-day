---
type: Vault Parameter
okf_version: "0.2"
profile: https://thoughtmachine.example/fde/schemas/feature-knowledge-bundle/1.0.json
profile_version: 1.0.0
title: cooling_off_period
description: The number of days from the account activation datetime when a user can make a full withdrawal without incurring any fees.
status: stable
tags:
  - parameter
identity:
  clu_id: cooling_off_period
  reference: "&{cooling_off_period}"
  constraint: decimal_constraint
  clu_resource: feature_library/src/feature_library/deposit/temporal_features/parameter_resource_defs/cooling_off_period.resource.yaml
generated:
  by: process:fl/0.1.0
used_by:
  - deposit.temporal_features.cooling_off_period
---

# `&{cooling_off_period}`

The number of days from the account activation datetime when a user can make a full withdrawal without incurring any fees.

**Constraint:** `decimal_constraint`  
**CLU resource:** `feature_library/src/feature_library/deposit/temporal_features/parameter_resource_defs/cooling_off_period.resource.yaml`

## Referenced by

- [deposit.temporal_features.cooling_off_period](/features/deposit/temporal_features/cooling_off_period.md)

<!-- generated:end -->
