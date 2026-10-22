---
type: Vault Parameter
okf_version: "0.2"
profile: https://thoughtmachine.example/fde/schemas/feature-knowledge-bundle/1.0.json
profile_version: 1.0.0
title: days_in_year_option
description: Vault parameter days_in_year_option.
status: stable
tags:
  - parameter
identity:
  clu_id: days_in_year_option
  reference: "&{days_in_year_option}"
  constraint: enumeration_constraint
  clu_resource: feature_library/src/feature_library/deposit/interest/parameter_resource_defs/days_in_year_option.resource.yaml
generated:
  by: process:fl/0.1.0
used_by:
  - deposit.interest.interest_accrual
---

# `&{days_in_year_option}`

_No description in the resource definition._

**Constraint:** `enumeration_constraint`  
**CLU resource:** `feature_library/src/feature_library/deposit/interest/parameter_resource_defs/days_in_year_option.resource.yaml`

## Referenced by

- [deposit.interest.interest_accrual](/features/deposit/interest/interest_accrual.md)

<!-- generated:end -->
