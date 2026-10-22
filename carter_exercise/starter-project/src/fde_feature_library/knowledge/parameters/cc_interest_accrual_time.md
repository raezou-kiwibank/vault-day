---
type: Vault Parameter
okf_version: "0.2"
profile: https://thoughtmachine.example/fde/schemas/feature-knowledge-bundle/1.0.json
profile_version: 1.0.0
title: cc_interest_accrual_time
description: "Time of day for daily interest accrual. Format: HH:MM:SS."
status: stable
tags:
  - parameter
identity:
  clu_id: cc_interest_accrual_time
  reference: "&{cc_interest_accrual_time}"
  constraint: string_constraint
  clu_resource: feature_library/src/feature_library/lending/interest/parameter_resource_defs/cc_interest_accrual_time.resource.yaml
generated:
  by: process:fl/0.1.0
used_by:
  - lending.interest.credit_card_interest_accrual
---

# `&{cc_interest_accrual_time}`

Time of day for daily interest accrual. Format: HH:MM:SS.

**Constraint:** `string_constraint`  
**CLU resource:** `feature_library/src/feature_library/lending/interest/parameter_resource_defs/cc_interest_accrual_time.resource.yaml`

## Referenced by

- [lending.interest.credit_card_interest_accrual](/features/lending/interest/credit_card_interest_accrual.md)

<!-- generated:end -->
