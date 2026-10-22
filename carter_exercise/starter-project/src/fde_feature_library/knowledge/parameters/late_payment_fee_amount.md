---
type: Vault Parameter
okf_version: "0.2"
profile: https://thoughtmachine.example/fde/schemas/feature-knowledge-bundle/1.0.json
profile_version: 1.0.0
title: late_payment_fee_amount
description: Fee charged when minimum payment is not met by due date.
status: stable
tags:
  - parameter
identity:
  clu_id: late_payment_fee_amount
  reference: "&{late_payment_fee_amount}"
  constraint: decimal_constraint
  clu_resource: feature_library/src/feature_library/lending/fees/parameter_resource_defs/late_payment_fee_amount.resource.yaml
generated:
  by: process:fl/0.1.0
used_by:
  - lending.fees.credit_card_late_payment_fee
---

# `&{late_payment_fee_amount}`

Fee charged when minimum payment is not met by due date.

**Constraint:** `decimal_constraint`  
**CLU resource:** `feature_library/src/feature_library/lending/fees/parameter_resource_defs/late_payment_fee_amount.resource.yaml`

## Referenced by

- [lending.fees.credit_card_late_payment_fee](/features/lending/fees/credit_card_late_payment_fee.md)

<!-- generated:end -->
