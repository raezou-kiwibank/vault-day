---
type: Vault Parameter
okf_version: "0.2"
profile: https://thoughtmachine.example/fde/schemas/feature-knowledge-bundle/1.0.json
profile_version: 1.0.0
title: annual_fee_amount
description: Annual fee amount charged to the credit card account.
status: stable
tags:
  - parameter
identity:
  clu_id: annual_fee_amount
  reference: "&{annual_fee_amount}"
  constraint: decimal_constraint
  clu_resource: feature_library/src/feature_library/lending/fees/parameter_resource_defs/annual_fee_amount.resource.yaml
generated:
  by: process:fl/0.1.0
used_by:
  - lending.fees.annual_fee
---

# `&{annual_fee_amount}`

Annual fee amount charged to the credit card account.

**Constraint:** `decimal_constraint`  
**CLU resource:** `feature_library/src/feature_library/lending/fees/parameter_resource_defs/annual_fee_amount.resource.yaml`

## Referenced by

- [lending.fees.annual_fee](/features/lending/fees/annual_fee.md)

<!-- generated:end -->
