---
type: Vault Parameter
okf_version: "0.2"
profile: https://thoughtmachine.example/fde/schemas/feature-knowledge-bundle/1.0.json
profile_version: 1.0.0
title: cash_advance_interest_rate
description: Annual interest rate for cash advances (e.g. 0.299 for 29.9% APR).
status: stable
tags:
  - parameter
identity:
  clu_id: cash_advance_interest_rate
  reference: "&{cash_advance_interest_rate}"
  constraint: decimal_constraint
  clu_resource: feature_library/src/feature_library/lending/interest/parameter_resource_defs/cash_advance_interest_rate.resource.yaml
generated:
  by: process:fl/0.1.0
used_by:
  - lending.interest.credit_card_interest_accrual
---

# `&{cash_advance_interest_rate}`

Annual interest rate for cash advances (e.g. 0.299 for 29.9% APR).

**Constraint:** `decimal_constraint`  
**CLU resource:** `feature_library/src/feature_library/lending/interest/parameter_resource_defs/cash_advance_interest_rate.resource.yaml`

## Referenced by

- [lending.interest.credit_card_interest_accrual](/features/lending/interest/credit_card_interest_accrual.md)

<!-- generated:end -->
