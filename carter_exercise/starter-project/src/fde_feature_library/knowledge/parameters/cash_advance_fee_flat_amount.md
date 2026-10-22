---
type: Vault Parameter
okf_version: "0.2"
profile: https://thoughtmachine.example/fde/schemas/feature-knowledge-bundle/1.0.json
profile_version: 1.0.0
title: cash_advance_fee_flat_amount
description: Minimum flat fee for cash advance transactions.
status: stable
tags:
  - parameter
identity:
  clu_id: cash_advance_fee_flat_amount
  reference: "&{cash_advance_fee_flat_amount}"
  constraint: decimal_constraint
  clu_resource: feature_library/src/feature_library/lending/fees/parameter_resource_defs/cash_advance_fee_flat_amount.resource.yaml
generated:
  by: process:fl/0.1.0
used_by:
  - lending.fees.cash_advance_fee
---

# `&{cash_advance_fee_flat_amount}`

Minimum flat fee for cash advance transactions.

**Constraint:** `decimal_constraint`  
**CLU resource:** `feature_library/src/feature_library/lending/fees/parameter_resource_defs/cash_advance_fee_flat_amount.resource.yaml`

## Referenced by

- [lending.fees.cash_advance_fee](/features/lending/fees/cash_advance_fee.md)

<!-- generated:end -->
