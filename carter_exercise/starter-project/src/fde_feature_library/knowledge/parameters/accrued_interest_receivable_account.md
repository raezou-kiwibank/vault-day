---
type: Vault Parameter
okf_version: "0.2"
profile: https://thoughtmachine.example/fde/schemas/feature-knowledge-bundle/1.0.json
profile_version: 1.0.0
title: accrued_interest_receivable_account
description: Vault parameter accrued_interest_receivable_account.
status: stable
tags:
  - parameter
identity:
  clu_id: accrued_interest_receivable_account
  reference: "&{accrued_interest_receivable_account}"
  constraint: account_constraint
  clu_resource: feature_library/src/feature_library/deposit/interest/parameter_resource_defs/accrued_interest_receivable_account.resource.yaml
generated:
  by: process:fl/0.1.0
used_by:
  - deposit.interest.interest_accrual
  - lending.interest.interest_accrual
---

# `&{accrued_interest_receivable_account}`

_No description in the resource definition._

**Constraint:** `account_constraint`  
**CLU resource:** `feature_library/src/feature_library/deposit/interest/parameter_resource_defs/accrued_interest_receivable_account.resource.yaml`

## Referenced by

- [deposit.interest.interest_accrual](/features/deposit/interest/interest_accrual.md)
- [lending.interest.interest_accrual](/features/lending/interest/interest_accrual.md)

<!-- generated:end -->
