---
type: Vault Parameter
okf_version: "0.2"
profile: https://thoughtmachine.example/fde/schemas/feature-knowledge-bundle/1.0.json
profile_version: 1.0.0
title: interest_free_buffer_days
description: Vault parameter interest_free_buffer_days.
status: stable
tags:
  - parameter
identity:
  clu_id: interest_free_buffer_days
  reference: "&{interest_free_buffer_days}"
  constraint: decimal_constraint
  clu_resource: feature_library/src/feature_library/deposit/interest/parameter_resource_defs/interest_free_buffer_days.resource.yaml
generated:
  by: process:fl/0.1.0
used_by:
  - deposit.interest.secondary.overdraft_interest
---

# `&{interest_free_buffer_days}`

_No description in the resource definition._

**Constraint:** `decimal_constraint`  
**CLU resource:** `feature_library/src/feature_library/deposit/interest/parameter_resource_defs/interest_free_buffer_days.resource.yaml`

## Referenced by

- [deposit.interest.secondary.overdraft_interest](/features/deposit/interest/secondary/overdraft_interest.md)

<!-- generated:end -->
