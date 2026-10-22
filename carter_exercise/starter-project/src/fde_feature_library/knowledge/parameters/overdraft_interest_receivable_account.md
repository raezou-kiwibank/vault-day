---
type: Vault Parameter
okf_version: "0.2"
profile: https://thoughtmachine.example/fde/schemas/feature-knowledge-bundle/1.0.json
profile_version: 1.0.0
title: overdraft_interest_receivable_account
description: Vault parameter overdraft_interest_receivable_account.
status: stable
tags:
  - parameter
identity:
  clu_id: overdraft_interest_receivable_account
  reference: "&{overdraft_interest_receivable_account}"
  constraint: account_constraint
  clu_resource: feature_library/src/feature_library/deposit/interest/parameter_resource_defs/overdraft_interest_receivable_account.resource.yaml
generated:
  by: process:fl/0.1.0
used_by:
  - deposit.interest.secondary.overdraft_interest
---

# `&{overdraft_interest_receivable_account}`

_No description in the resource definition._

**Constraint:** `account_constraint`  
**CLU resource:** `feature_library/src/feature_library/deposit/interest/parameter_resource_defs/overdraft_interest_receivable_account.resource.yaml`

## Referenced by

- [deposit.interest.secondary.overdraft_interest](/features/deposit/interest/secondary/overdraft_interest.md)

<!-- generated:end -->
