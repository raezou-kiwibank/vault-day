---
type: Vault Parameter
okf_version: "0.2"
profile: https://thoughtmachine.example/fde/schemas/feature-knowledge-bundle/1.0.json
profile_version: 1.0.0
title: interest_accrual_precision
description: Decimal places for interest accrual rounding.
status: stable
tags:
  - parameter
identity:
  clu_id: interest_accrual_precision
  reference: "&{interest_accrual_precision}"
  constraint: decimal_constraint
  clu_resource: feature_library/src/feature_library/lending/interest/parameter_resource_defs/interest_accrual_precision.resource.yaml
generated:
  by: process:fl/0.1.0
used_by:
  - lending.interest.credit_card_interest_accrual
---

# `&{interest_accrual_precision}`

Decimal places for interest accrual rounding.

**Constraint:** `decimal_constraint`  
**CLU resource:** `feature_library/src/feature_library/lending/interest/parameter_resource_defs/interest_accrual_precision.resource.yaml`

## Referenced by

- [lending.interest.credit_card_interest_accrual](/features/lending/interest/credit_card_interest_accrual.md)

<!-- generated:end -->
