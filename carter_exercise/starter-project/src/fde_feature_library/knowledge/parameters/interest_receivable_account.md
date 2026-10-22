---
type: Vault Parameter
okf_version: "0.2"
profile: https://thoughtmachine.example/fde/schemas/feature-knowledge-bundle/1.0.json
profile_version: 1.0.0
title: interest_receivable_account
description: Internal account for interest receivable.
status: stable
tags:
  - parameter
identity:
  clu_id: interest_receivable_account
  reference: "&{interest_receivable_account}"
  constraint: account_constraint
  clu_resource: feature_library/src/feature_library/lending/interest/parameter_resource_defs/interest_receivable_account.resource.yaml
generated:
  by: process:fl/0.1.0
used_by:
  - lending.interest.credit_card_interest_accrual
---

# `&{interest_receivable_account}`

Internal account for interest receivable.

**Constraint:** `account_constraint`  
**CLU resource:** `feature_library/src/feature_library/lending/interest/parameter_resource_defs/interest_receivable_account.resource.yaml`

## Referenced by

- [lending.interest.credit_card_interest_accrual](/features/lending/interest/credit_card_interest_accrual.md)

<!-- generated:end -->
