---
type: Vault Parameter
okf_version: "0.2"
profile: https://thoughtmachine.example/fde/schemas/feature-knowledge-bundle/1.0.json
profile_version: 1.0.0
title: deposit_account
description: Vault parameter deposit_account.
status: stable
tags:
  - parameter
identity:
  clu_id: deposit_account
  reference: "&{deposit_account}"
  constraint: account_constraint
  clu_resource: feature_library/src/feature_library/lending/disbursal/parameter_resource_defs/deposit_account.resource.yaml
generated:
  by: process:fl/0.1.0
used_by:
  - lending.disbursal.disbursement
---

# `&{deposit_account}`

_No description in the resource definition._

**Constraint:** `account_constraint`  
**CLU resource:** `feature_library/src/feature_library/lending/disbursal/parameter_resource_defs/deposit_account.resource.yaml`

## Referenced by

- [lending.disbursal.disbursement](/features/lending/disbursal/disbursement.md)

<!-- generated:end -->
