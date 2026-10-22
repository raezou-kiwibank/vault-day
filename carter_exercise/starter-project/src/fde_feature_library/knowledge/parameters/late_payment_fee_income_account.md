---
type: Vault Parameter
okf_version: "0.2"
profile: https://thoughtmachine.example/fde/schemas/feature-knowledge-bundle/1.0.json
profile_version: 1.0.0
title: late_payment_fee_income_account
description: Internal account for late payment fee income.
status: stable
tags:
  - parameter
identity:
  clu_id: late_payment_fee_income_account
  reference: "&{late_payment_fee_income_account}"
  constraint: account_constraint
  clu_resource: feature_library/src/feature_library/lending/fees/parameter_resource_defs/late_payment_fee_income_account.resource.yaml
generated:
  by: process:fl/0.1.0
used_by:
  - lending.fees.credit_card_late_payment_fee
---

# `&{late_payment_fee_income_account}`

Internal account for late payment fee income.

**Constraint:** `account_constraint`  
**CLU resource:** `feature_library/src/feature_library/lending/fees/parameter_resource_defs/late_payment_fee_income_account.resource.yaml`

## Referenced by

- [lending.fees.credit_card_late_payment_fee](/features/lending/fees/credit_card_late_payment_fee.md)

<!-- generated:end -->
