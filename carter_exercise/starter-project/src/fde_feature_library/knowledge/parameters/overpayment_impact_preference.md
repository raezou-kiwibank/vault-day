---
type: Vault Parameter
okf_version: "0.2"
profile: https://thoughtmachine.example/fde/schemas/feature-knowledge-bundle/1.0.json
profile_version: 1.0.0
title: overpayment_impact_preference
description: Vault parameter overpayment_impact_preference.
status: stable
tags:
  - parameter
identity:
  clu_id: overpayment_impact_preference
  reference: "&{overpayment_impact_preference}"
  constraint: string_constraint
  clu_resource: feature_library/src/feature_library/lending/repayments/parameter_resource_defs/overpayment_impact_preference.resource.yaml
generated:
  by: process:fl/0.1.0
used_by:
  - lending.repayments.overpayment
---

# `&{overpayment_impact_preference}`

_No description in the resource definition._

**Constraint:** `string_constraint`  
**CLU resource:** `feature_library/src/feature_library/lending/repayments/parameter_resource_defs/overpayment_impact_preference.resource.yaml`

## Referenced by

- [lending.repayments.overpayment](/features/lending/repayments/overpayment.md)

<!-- generated:end -->
