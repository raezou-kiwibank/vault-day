---
type: Vault Parameter
okf_version: "0.2"
profile: https://thoughtmachine.example/fde/schemas/feature-knowledge-bundle/1.0.json
profile_version: 1.0.0
title: accrual_precision
description: Vault parameter accrual_precision.
status: stable
tags:
  - parameter
identity:
  clu_id: accrual_precision
  reference: "&{accrual_precision}"
  constraint: decimal_constraint
  clu_resource: feature_library/src/feature_library/deposit/interest/parameter_resource_defs/accrual_precision.resource.yaml
generated:
  by: process:fl/0.1.0
used_by:
  - deposit.interest.interest_accrual
  - lending.interest.interest_accrual
---

# `&{accrual_precision}`

_No description in the resource definition._

**Constraint:** `decimal_constraint`  
**CLU resource:** `feature_library/src/feature_library/deposit/interest/parameter_resource_defs/accrual_precision.resource.yaml`

## Referenced by

- [deposit.interest.interest_accrual](/features/deposit/interest/interest_accrual.md)
- [lending.interest.interest_accrual](/features/lending/interest/interest_accrual.md)

<!-- generated:end -->
