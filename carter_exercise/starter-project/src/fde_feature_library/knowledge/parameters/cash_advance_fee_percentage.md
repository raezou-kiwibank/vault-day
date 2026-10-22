---
type: Vault Parameter
okf_version: "0.2"
profile: https://thoughtmachine.example/fde/schemas/feature-knowledge-bundle/1.0.json
profile_version: 1.0.0
title: cash_advance_fee_percentage
description: Cash advance fee as a percentage of the transaction amount (e.g. 0.03 for 3%).
status: stable
tags:
  - parameter
identity:
  clu_id: cash_advance_fee_percentage
  reference: "&{cash_advance_fee_percentage}"
  constraint: decimal_constraint
  clu_resource: feature_library/src/feature_library/lending/fees/parameter_resource_defs/cash_advance_fee_percentage.resource.yaml
generated:
  by: process:fl/0.1.0
used_by:
  - lending.fees.cash_advance_fee
---

# `&{cash_advance_fee_percentage}`

Cash advance fee as a percentage of the transaction amount (e.g. 0.03 for 3%).

**Constraint:** `decimal_constraint`  
**CLU resource:** `feature_library/src/feature_library/lending/fees/parameter_resource_defs/cash_advance_fee_percentage.resource.yaml`

## Referenced by

- [lending.fees.cash_advance_fee](/features/lending/fees/cash_advance_fee.md)

<!-- generated:end -->
