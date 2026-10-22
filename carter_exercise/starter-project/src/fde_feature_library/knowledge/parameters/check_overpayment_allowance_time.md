---
type: Vault Parameter
okf_version: "0.2"
profile: https://thoughtmachine.example/fde/schemas/feature-knowledge-bundle/1.0.json
profile_version: 1.0.0
title: check_overpayment_allowance_time
description: Vault parameter check_overpayment_allowance_time.
status: stable
tags:
  - parameter
identity:
  clu_id: check_overpayment_allowance_time
  reference: "&{check_overpayment_allowance_time}"
  constraint: string_constraint
  clu_resource: feature_library/src/feature_library/lending/repayments/parameter_resource_defs/check_overpayment_allowance_time.resource.yaml
generated:
  by: process:fl/0.1.0
used_by:
  - lending.repayments.overpayment_allowance
---

# `&{check_overpayment_allowance_time}`

_No description in the resource definition._

**Constraint:** `string_constraint`  
**CLU resource:** `feature_library/src/feature_library/lending/repayments/parameter_resource_defs/check_overpayment_allowance_time.resource.yaml`

## Referenced by

- [lending.repayments.overpayment_allowance](/features/lending/repayments/overpayment_allowance.md)

<!-- generated:end -->
