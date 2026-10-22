---
type: Vault Parameter
okf_version: "0.2"
profile: https://thoughtmachine.example/fde/schemas/feature-knowledge-bundle/1.0.json
profile_version: 1.0.0
title: late_repayment_fee_income_account
description: Vault parameter late_repayment_fee_income_account.
status: stable
tags:
  - parameter
identity:
  clu_id: late_repayment_fee_income_account
  reference: "&{late_repayment_fee_income_account}"
  constraint: account_constraint
  clu_resource: feature_library/src/feature_library/lending/repayments/parameter_resource_defs/late_repayment_fee_income_account.resource.yaml
generated:
  by: process:fl/0.1.0
used_by:
  - lending.repayments.late_repayment
---

# `&{late_repayment_fee_income_account}`

_No description in the resource definition._

**Constraint:** `account_constraint`  
**CLU resource:** `feature_library/src/feature_library/lending/repayments/parameter_resource_defs/late_repayment_fee_income_account.resource.yaml`

## Referenced by

- [lending.repayments.late_repayment](/features/lending/repayments/late_repayment.md)

<!-- generated:end -->
