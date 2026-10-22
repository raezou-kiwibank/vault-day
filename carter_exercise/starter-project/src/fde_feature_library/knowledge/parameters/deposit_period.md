---
type: Vault Parameter
okf_version: "0.2"
profile: https://thoughtmachine.example/fde/schemas/feature-knowledge-bundle/1.0.json
profile_version: 1.0.0
title: deposit_period
description: Vault parameter deposit_period.
status: stable
tags:
  - parameter
identity:
  clu_id: deposit_period
  reference: "&{deposit_period}"
  constraint: decimal_constraint
  clu_resource: feature_library/src/feature_library/deposit/temporal_features/parameter_resource_defs/deposit_period.resource.yaml
generated:
  by: process:fl/0.1.0
used_by:
  - deposit.temporal_features.deposit_period
---

# `&{deposit_period}`

_No description in the resource definition._

**Constraint:** `decimal_constraint`  
**CLU resource:** `feature_library/src/feature_library/deposit/temporal_features/parameter_resource_defs/deposit_period.resource.yaml`

## Referenced by

- [deposit.temporal_features.deposit_period](/features/deposit/temporal_features/deposit_period.md)

<!-- generated:end -->
