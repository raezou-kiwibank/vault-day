---
type: Vault Parameter
okf_version: "0.2"
profile: https://thoughtmachine.example/fde/schemas/feature-knowledge-bundle/1.0.json
profile_version: 1.0.0
title: foreign_transaction_fee_percentage
description: Foreign transaction fee as a percentage (e.g. 0.03 for 3%). Set to 0 for no FX fee.
status: stable
tags:
  - parameter
identity:
  clu_id: foreign_transaction_fee_percentage
  reference: "&{foreign_transaction_fee_percentage}"
  constraint: decimal_constraint
  clu_resource: feature_library/src/feature_library/lending/fees/parameter_resource_defs/foreign_transaction_fee_percentage.resource.yaml
generated:
  by: process:fl/0.1.0
used_by:
  - lending.fees.foreign_transaction_fee
---

# `&{foreign_transaction_fee_percentage}`

Foreign transaction fee as a percentage (e.g. 0.03 for 3%). Set to 0 for no FX fee.

**Constraint:** `decimal_constraint`  
**CLU resource:** `feature_library/src/feature_library/lending/fees/parameter_resource_defs/foreign_transaction_fee_percentage.resource.yaml`

## Referenced by

- [lending.fees.foreign_transaction_fee](/features/lending/fees/foreign_transaction_fee.md)

<!-- generated:end -->
