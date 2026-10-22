---
type: Vault Parameter
okf_version: "0.2"
profile: https://thoughtmachine.example/fde/schemas/feature-knowledge-bundle/1.0.json
profile_version: 1.0.0
title: credit_limit
description: Maximum credit limit for the account.
status: stable
tags:
  - parameter
identity:
  clu_id: credit_limit
  reference: "&{credit_limit}"
  constraint: decimal_constraint
  clu_resource: feature_library/src/feature_library/lending/limits/parameter_resource_defs/credit_limit.resource.yaml
generated:
  by: process:fl/0.1.0
used_by:
  - lending.limits.credit_limit
---

# `&{credit_limit}`

Maximum credit limit for the account.

**Constraint:** `decimal_constraint`  
**CLU resource:** `feature_library/src/feature_library/lending/limits/parameter_resource_defs/credit_limit.resource.yaml`

## Referenced by

- [lending.limits.credit_limit](/features/lending/limits/credit_limit.md)

<!-- generated:end -->
