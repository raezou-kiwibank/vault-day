---
type: Vault Parameter
okf_version: "0.2"
profile: https://thoughtmachine.example/fde/schemas/feature-knowledge-bundle/1.0.json
profile_version: 1.0.0
title: early_repayment_flat_fee
description: Vault parameter early_repayment_flat_fee.
status: stable
tags:
  - parameter
identity:
  clu_id: early_repayment_flat_fee
  reference: "&{early_repayment_flat_fee}"
  constraint: decimal_constraint
  clu_resource: feature_library/src/feature_library/lending/repayments/parameter_resource_defs/early_repayment_flat_fee.resource.yaml
generated:
  by: process:fl/0.1.0
used_by:
  - lending.repayments.early_repayment
---

# `&{early_repayment_flat_fee}`

_No description in the resource definition._

**Constraint:** `decimal_constraint`  
**CLU resource:** `feature_library/src/feature_library/lending/repayments/parameter_resource_defs/early_repayment_flat_fee.resource.yaml`

## Referenced by

- [lending.repayments.early_repayment](/features/lending/repayments/early_repayment.md)

<!-- generated:end -->
