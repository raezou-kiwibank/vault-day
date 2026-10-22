---
type: Vault Parameter
okf_version: "0.2"
profile: https://thoughtmachine.example/fde/schemas/feature-knowledge-bundle/1.0.json
profile_version: 1.0.0
title: repayment_period
description: Vault parameter repayment_period.
status: stable
tags:
  - parameter
identity:
  clu_id: repayment_period
  reference: "&{repayment_period}"
  constraint: decimal_constraint
  clu_resource: feature_library/src/feature_library/lending/overdue/parameter_resource_defs/repayment_period.resource.yaml
generated:
  by: process:fl/0.1.0
used_by:
  - lending.overdue.overdue
---

# `&{repayment_period}`

_No description in the resource definition._

**Constraint:** `decimal_constraint`  
**CLU resource:** `feature_library/src/feature_library/lending/overdue/parameter_resource_defs/repayment_period.resource.yaml`

## Referenced by

- [lending.overdue.overdue](/features/lending/overdue/overdue.md)

<!-- generated:end -->
