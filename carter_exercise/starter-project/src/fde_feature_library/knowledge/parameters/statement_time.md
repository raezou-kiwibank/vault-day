---
type: Vault Parameter
okf_version: "0.2"
profile: https://thoughtmachine.example/fde/schemas/feature-knowledge-bundle/1.0.json
profile_version: 1.0.0
title: statement_time
description: "Time of day for statement cut. Format: HH:MM:SS."
status: stable
tags:
  - parameter
identity:
  clu_id: statement_time
  reference: "&{statement_time}"
  constraint: string_constraint
  clu_resource: feature_library/src/feature_library/lending/repayments/parameter_resource_defs/statement_time.resource.yaml
generated:
  by: process:fl/0.1.0
used_by:
  - lending.repayments.minimum_payment
---

# `&{statement_time}`

Time of day for statement cut. Format: HH:MM:SS.

**Constraint:** `string_constraint`  
**CLU resource:** `feature_library/src/feature_library/lending/repayments/parameter_resource_defs/statement_time.resource.yaml`

## Referenced by

- [lending.repayments.minimum_payment](/features/lending/repayments/minimum_payment.md)

<!-- generated:end -->
