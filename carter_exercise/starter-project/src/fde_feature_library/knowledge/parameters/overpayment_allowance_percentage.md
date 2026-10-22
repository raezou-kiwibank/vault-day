---
type: Vault Parameter
okf_version: "0.2"
profile: https://thoughtmachine.example/fde/schemas/feature-knowledge-bundle/1.0.json
profile_version: 1.0.0
title: overpayment_allowance_percentage
description: Vault parameter overpayment_allowance_percentage.
status: stable
tags:
  - parameter
identity:
  clu_id: overpayment_allowance_percentage
  reference: "&{overpayment_allowance_percentage}"
  constraint: decimal_constraint
  clu_resource: feature_library/src/feature_library/lending/repayments/parameter_resource_defs/overpayment_allowance_percentage.resource.yaml
generated:
  by: process:fl/0.1.0
used_by:
  - lending.repayments.overpayment_allowance
---

# `&{overpayment_allowance_percentage}`

_No description in the resource definition._

**Constraint:** `decimal_constraint`  
**CLU resource:** `feature_library/src/feature_library/lending/repayments/parameter_resource_defs/overpayment_allowance_percentage.resource.yaml`

## Referenced by

- [lending.repayments.overpayment_allowance](/features/lending/repayments/overpayment_allowance.md)

<!-- generated:end -->
