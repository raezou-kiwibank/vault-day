---
type: Vault Parameter
okf_version: "0.2"
profile: https://thoughtmachine.example/fde/schemas/feature-knowledge-bundle/1.0.json
profile_version: 1.0.0
title: number_of_permitted_deposits
description: Vault parameter number_of_permitted_deposits.
status: stable
tags:
  - parameter
identity:
  clu_id: number_of_permitted_deposits
  reference: "&{number_of_permitted_deposits}"
  constraint: enumeration_constraint
  clu_resource: feature_library/src/feature_library/deposit/temporal_features/parameter_resource_defs/number_of_permitted_deposits.resource.yaml
generated:
  by: process:fl/0.1.0
used_by:
  - deposit.temporal_features.deposit_period
---

# `&{number_of_permitted_deposits}`

_No description in the resource definition._

**Constraint:** `enumeration_constraint`  
**CLU resource:** `feature_library/src/feature_library/deposit/temporal_features/parameter_resource_defs/number_of_permitted_deposits.resource.yaml`

## Referenced by

- [deposit.temporal_features.deposit_period](/features/deposit/temporal_features/deposit_period.md)

<!-- generated:end -->
