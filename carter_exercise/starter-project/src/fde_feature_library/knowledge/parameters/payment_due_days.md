---
type: Vault Parameter
okf_version: "0.2"
profile: https://thoughtmachine.example/fde/schemas/feature-knowledge-bundle/1.0.json
profile_version: 1.0.0
title: payment_due_days
description: Number of days after statement cut that payment is due.
status: stable
tags:
  - parameter
identity:
  clu_id: payment_due_days
  reference: "&{payment_due_days}"
  constraint: decimal_constraint
  clu_resource: feature_library/src/feature_library/lending/repayments/parameter_resource_defs/payment_due_days.resource.yaml
generated:
  by: process:fl/0.1.0
used_by:
  - lending.repayments.minimum_payment
---

# `&{payment_due_days}`

Number of days after statement cut that payment is due.

**Constraint:** `decimal_constraint`  
**CLU resource:** `feature_library/src/feature_library/lending/repayments/parameter_resource_defs/payment_due_days.resource.yaml`

## Referenced by

- [lending.repayments.minimum_payment](/features/lending/repayments/minimum_payment.md)

<!-- generated:end -->
