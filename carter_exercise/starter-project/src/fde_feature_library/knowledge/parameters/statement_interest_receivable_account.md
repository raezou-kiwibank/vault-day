---
type: Vault Parameter
okf_version: "0.2"
profile: https://thoughtmachine.example/fde/schemas/feature-knowledge-bundle/1.0.json
profile_version: 1.0.0
title: statement_interest_receivable_account
description: Internal account for interest receivable used at statement cut.
status: stable
tags:
  - parameter
identity:
  clu_id: statement_interest_receivable_account
  reference: "&{statement_interest_receivable_account}"
  constraint: account_constraint
  clu_resource: feature_library/src/feature_library/lending/repayments/parameter_resource_defs/statement_interest_receivable_account.resource.yaml
generated:
  by: process:fl/0.1.0
used_by:
  - lending.repayments.minimum_payment
---

# `&{statement_interest_receivable_account}`

Internal account for interest receivable used at statement cut.

**Constraint:** `account_constraint`  
**CLU resource:** `feature_library/src/feature_library/lending/repayments/parameter_resource_defs/statement_interest_receivable_account.resource.yaml`

## Referenced by

- [lending.repayments.minimum_payment](/features/lending/repayments/minimum_payment.md)

<!-- generated:end -->
