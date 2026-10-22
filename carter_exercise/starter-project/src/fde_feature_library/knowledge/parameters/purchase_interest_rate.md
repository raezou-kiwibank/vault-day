---
type: Vault Parameter
okf_version: "0.2"
profile: https://thoughtmachine.example/fde/schemas/feature-knowledge-bundle/1.0.json
profile_version: 1.0.0
title: purchase_interest_rate
description: Annual interest rate for purchases (e.g. 0.249 for 24.9% APR).
status: stable
tags:
  - parameter
identity:
  clu_id: purchase_interest_rate
  reference: "&{purchase_interest_rate}"
  constraint: decimal_constraint
  clu_resource: feature_library/src/feature_library/lending/interest/parameter_resource_defs/purchase_interest_rate.resource.yaml
generated:
  by: process:fl/0.1.0
used_by:
  - lending.interest.credit_card_interest_accrual
---

# `&{purchase_interest_rate}`

Annual interest rate for purchases (e.g. 0.249 for 24.9% APR).

**Constraint:** `decimal_constraint`  
**CLU resource:** `feature_library/src/feature_library/lending/interest/parameter_resource_defs/purchase_interest_rate.resource.yaml`

## Referenced by

- [lending.interest.credit_card_interest_accrual](/features/lending/interest/credit_card_interest_accrual.md)

<!-- generated:end -->
