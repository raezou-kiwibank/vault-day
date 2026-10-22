---
type: Vault Parameter
okf_version: "0.2"
profile: https://thoughtmachine.example/fde/schemas/feature-knowledge-bundle/1.0.json
profile_version: 1.0.0
title: late_repayment_fee
description: Vault parameter late_repayment_fee.
status: stable
tags:
  - parameter
identity:
  clu_id: late_repayment_fee
  reference: "&{late_repayment_fee}"
  constraint: decimal_constraint
  clu_resource: feature_library/src/feature_library/lending/repayments/parameter_resource_defs/late_repayment_fee.resource.yaml
generated:
  by: process:fl/0.1.0
used_by:
  - lending.repayments.late_repayment
---

# `&{late_repayment_fee}`

_No description in the resource definition._

**Constraint:** `decimal_constraint`  
**CLU resource:** `feature_library/src/feature_library/lending/repayments/parameter_resource_defs/late_repayment_fee.resource.yaml`

## Referenced by

- [lending.repayments.late_repayment](/features/lending/repayments/late_repayment.md)

<!-- generated:end -->
