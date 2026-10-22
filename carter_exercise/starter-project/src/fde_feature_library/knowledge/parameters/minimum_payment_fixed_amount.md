---
type: Vault Parameter
okf_version: "0.2"
profile: https://thoughtmachine.example/fde/schemas/feature-knowledge-bundle/1.0.json
profile_version: 1.0.0
title: minimum_payment_fixed_amount
description: Fixed minimum payment amount.
status: stable
tags:
  - parameter
identity:
  clu_id: minimum_payment_fixed_amount
  reference: "&{minimum_payment_fixed_amount}"
  constraint: decimal_constraint
  clu_resource: feature_library/src/feature_library/lending/repayments/parameter_resource_defs/minimum_payment_fixed_amount.resource.yaml
generated:
  by: process:fl/0.1.0
used_by:
  - lending.repayments.minimum_payment
---

# `&{minimum_payment_fixed_amount}`

Fixed minimum payment amount.

**Constraint:** `decimal_constraint`  
**CLU resource:** `feature_library/src/feature_library/lending/repayments/parameter_resource_defs/minimum_payment_fixed_amount.resource.yaml`

## Referenced by

- [lending.repayments.minimum_payment](/features/lending/repayments/minimum_payment.md)

<!-- generated:end -->
