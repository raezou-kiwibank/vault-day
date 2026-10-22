---
type: Vault Parameter
okf_version: "0.2"
profile: https://thoughtmachine.example/fde/schemas/feature-knowledge-bundle/1.0.json
profile_version: 1.0.0
title: early_repayment_fee_income_account
description: Vault parameter early_repayment_fee_income_account.
status: stable
tags:
  - parameter
identity:
  clu_id: early_repayment_fee_income_account
  reference: "&{early_repayment_fee_income_account}"
  constraint: account_constraint
  clu_resource: feature_library/src/feature_library/lending/repayments/parameter_resource_defs/early_repayment_fee_income_account.resource.yaml
generated:
  by: process:fl/0.1.0
used_by:
  - lending.repayments.early_repayment
---

# `&{early_repayment_fee_income_account}`

_No description in the resource definition._

**Constraint:** `account_constraint`  
**CLU resource:** `feature_library/src/feature_library/lending/repayments/parameter_resource_defs/early_repayment_fee_income_account.resource.yaml`

## Referenced by

- [lending.repayments.early_repayment](/features/lending/repayments/early_repayment.md)

<!-- generated:end -->
