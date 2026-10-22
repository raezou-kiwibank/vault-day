---
type: Vault Parameter
okf_version: "0.2"
profile: https://thoughtmachine.example/fde/schemas/feature-knowledge-bundle/1.0.json
profile_version: 1.0.0
title: overpayment_allowance_fee_income_account
description: Vault parameter overpayment_allowance_fee_income_account.
status: stable
tags:
  - parameter
identity:
  clu_id: overpayment_allowance_fee_income_account
  reference: "&{overpayment_allowance_fee_income_account}"
  constraint: account_constraint
  clu_resource: feature_library/src/feature_library/lending/repayments/parameter_resource_defs/overpayment_allowance_fee_income_account.resource.yaml
generated:
  by: process:fl/0.1.0
used_by:
  - lending.repayments.overpayment_allowance
---

# `&{overpayment_allowance_fee_income_account}`

_No description in the resource definition._

**Constraint:** `account_constraint`  
**CLU resource:** `feature_library/src/feature_library/lending/repayments/parameter_resource_defs/overpayment_allowance_fee_income_account.resource.yaml`

## Referenced by

- [lending.repayments.overpayment_allowance](/features/lending/repayments/overpayment_allowance.md)

<!-- generated:end -->
