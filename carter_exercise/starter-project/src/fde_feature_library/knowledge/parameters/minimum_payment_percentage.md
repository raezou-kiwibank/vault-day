---
type: Vault Parameter
okf_version: "0.2"
profile: https://thoughtmachine.example/fde/schemas/feature-knowledge-bundle/1.0.json
profile_version: 1.0.0
title: minimum_payment_percentage
description: Minimum payment as a percentage of total balance (e.g. 0.02 for 2%).
status: stable
tags:
  - parameter
identity:
  clu_id: minimum_payment_percentage
  reference: "&{minimum_payment_percentage}"
  constraint: decimal_constraint
  clu_resource: feature_library/src/feature_library/lending/repayments/parameter_resource_defs/minimum_payment_percentage.resource.yaml
generated:
  by: process:fl/0.1.0
used_by:
  - lending.repayments.minimum_payment
---

# `&{minimum_payment_percentage}`

Minimum payment as a percentage of total balance (e.g. 0.02 for 2%).

**Constraint:** `decimal_constraint`  
**CLU resource:** `feature_library/src/feature_library/lending/repayments/parameter_resource_defs/minimum_payment_percentage.resource.yaml`

## Referenced by

- [lending.repayments.minimum_payment](/features/lending/repayments/minimum_payment.md)

<!-- generated:end -->
