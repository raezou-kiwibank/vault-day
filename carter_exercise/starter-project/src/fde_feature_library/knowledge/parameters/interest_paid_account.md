---
type: Vault Parameter
okf_version: "0.2"
profile: https://thoughtmachine.example/fde/schemas/feature-knowledge-bundle/1.0.json
profile_version: 1.0.0
title: interest_paid_account
description: Vault parameter interest_paid_account.
status: stable
tags:
  - parameter
identity:
  clu_id: interest_paid_account
  reference: "&{interest_paid_account}"
  constraint: account_constraint
  clu_resource: feature_library/src/feature_library/deposit/interest/parameter_resource_defs/interest_paid_account.resource.yaml
generated:
  by: process:fl/0.1.0
used_by:
  - deposit.interest.interest_application
---

# `&{interest_paid_account}`

_No description in the resource definition._

**Constraint:** `account_constraint`  
**CLU resource:** `feature_library/src/feature_library/deposit/interest/parameter_resource_defs/interest_paid_account.resource.yaml`

## Referenced by

- [deposit.interest.interest_application](/features/deposit/interest/interest_application.md)

<!-- generated:end -->
