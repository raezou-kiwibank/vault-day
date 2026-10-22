---
type: Vault Parameter
okf_version: "0.2"
profile: https://thoughtmachine.example/fde/schemas/feature-knowledge-bundle/1.0.json
profile_version: 1.0.0
title: days_in_year
description: Vault parameter days_in_year.
status: stable
tags:
  - parameter
identity:
  clu_id: days_in_year
  reference: "&{days_in_year}"
  constraint: enumeration_constraint
  clu_resource: feature_library/src/feature_library/lending/interest/parameter_resource_defs/days_in_year.resource.yaml
generated:
  by: process:fl/0.1.0
used_by:
  - lending.interest.interest_accrual
---

# `&{days_in_year}`

_No description in the resource definition._

**Constraint:** `enumeration_constraint`  
**CLU resource:** `feature_library/src/feature_library/lending/interest/parameter_resource_defs/days_in_year.resource.yaml`

## Referenced by

- [lending.interest.interest_accrual](/features/lending/interest/interest_accrual.md)

<!-- generated:end -->
