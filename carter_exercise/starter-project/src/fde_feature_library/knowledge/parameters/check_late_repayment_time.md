---
type: Vault Parameter
okf_version: "0.2"
profile: https://thoughtmachine.example/fde/schemas/feature-knowledge-bundle/1.0.json
profile_version: 1.0.0
title: check_late_repayment_time
description: Vault parameter check_late_repayment_time.
status: stable
tags:
  - parameter
identity:
  clu_id: check_late_repayment_time
  reference: "&{check_late_repayment_time}"
  constraint: string_constraint
  clu_resource: feature_library/src/feature_library/lending/repayments/parameter_resource_defs/check_late_repayment_time.resource.yaml
generated:
  by: process:fl/0.1.0
used_by:
  - lending.repayments.late_repayment
---

# `&{check_late_repayment_time}`

_No description in the resource definition._

**Constraint:** `string_constraint`  
**CLU resource:** `feature_library/src/feature_library/lending/repayments/parameter_resource_defs/check_late_repayment_time.resource.yaml`

## Referenced by

- [lending.repayments.late_repayment](/features/lending/repayments/late_repayment.md)

<!-- generated:end -->
