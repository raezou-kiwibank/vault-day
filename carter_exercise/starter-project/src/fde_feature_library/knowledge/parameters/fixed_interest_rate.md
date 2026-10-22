---
type: Vault Parameter
okf_version: "0.2"
profile: https://thoughtmachine.example/fde/schemas/feature-knowledge-bundle/1.0.json
profile_version: 1.0.0
title: fixed_interest_rate
description: Vault parameter fixed_interest_rate.
status: stable
tags:
  - parameter
identity:
  clu_id: fixed_interest_rate
  reference: "&{fixed_interest_rate}"
  constraint: decimal_constraint
  clu_resource: feature_library/src/feature_library/deposit/interest/parameter_resource_defs/fixed_interest_rate.resource.yaml
generated:
  by: process:fl/0.1.0
used_by:
  - deposit.interest.secondary.flat_interest
  - lending.interest.secondary.fixed_rate
---

# `&{fixed_interest_rate}`

_No description in the resource definition._

**Constraint:** `decimal_constraint`  
**CLU resource:** `feature_library/src/feature_library/deposit/interest/parameter_resource_defs/fixed_interest_rate.resource.yaml`

## Referenced by

- [deposit.interest.secondary.flat_interest](/features/deposit/interest/secondary/flat_interest.md)
- [lending.interest.secondary.fixed_rate](/features/lending/interest/secondary/fixed_rate.md)

<!-- generated:end -->
