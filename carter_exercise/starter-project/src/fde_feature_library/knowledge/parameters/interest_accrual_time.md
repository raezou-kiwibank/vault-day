---
type: Vault Parameter
okf_version: "0.2"
profile: https://thoughtmachine.example/fde/schemas/feature-knowledge-bundle/1.0.json
profile_version: 1.0.0
title: interest_accrual_time
description: Vault parameter interest_accrual_time.
status: stable
tags:
  - parameter
identity:
  clu_id: interest_accrual_time
  reference: "&{interest_accrual_time}"
  constraint: string_constraint
  clu_resource: feature_library/src/feature_library/deposit/interest/parameter_resource_defs/interest_accrual_time.resource.yaml
generated:
  by: process:fl/0.1.0
used_by:
  - deposit.interest.interest_accrual
  - lending.interest.interest_accrual
---

# `&{interest_accrual_time}`

_No description in the resource definition._

**Constraint:** `string_constraint`  
**CLU resource:** `feature_library/src/feature_library/deposit/interest/parameter_resource_defs/interest_accrual_time.resource.yaml`

## Referenced by

- [deposit.interest.interest_accrual](/features/deposit/interest/interest_accrual.md)
- [lending.interest.interest_accrual](/features/lending/interest/interest_accrual.md)

<!-- generated:end -->
