---
type: Vault Parameter
okf_version: "0.2"
profile: https://thoughtmachine.example/fde/schemas/feature-knowledge-bundle/1.0.json
profile_version: 1.0.0
title: annual_fee_month
description: Month when the annual fee is applied.
status: stable
tags:
  - parameter
identity:
  clu_id: annual_fee_month
  reference: "&{annual_fee_month}"
  constraint: decimal_constraint
  clu_resource: feature_library/src/feature_library/lending/fees/parameter_resource_defs/annual_fee_month.resource.yaml
generated:
  by: process:fl/0.1.0
used_by:
  - lending.fees.annual_fee
---

# `&{annual_fee_month}`

Month when the annual fee is applied.

**Constraint:** `decimal_constraint`  
**CLU resource:** `feature_library/src/feature_library/lending/fees/parameter_resource_defs/annual_fee_month.resource.yaml`

## Referenced by

- [lending.fees.annual_fee](/features/lending/fees/annual_fee.md)

<!-- generated:end -->
