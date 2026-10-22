---
type: Vault Parameter
okf_version: "0.2"
profile: https://thoughtmachine.example/fde/schemas/feature-knowledge-bundle/1.0.json
profile_version: 1.0.0
title: tiered_interest_rates
description: Vault parameter tiered_interest_rates.
status: stable
tags:
  - parameter
identity:
  clu_id: tiered_interest_rates
  reference: "&{tiered_interest_rates}"
  constraint: string_constraint
  clu_resource: feature_library/src/feature_library/deposit/interest/parameter_resource_defs/tiered_interest_rates.resource.yaml
generated:
  by: process:fl/0.1.0
used_by:
  - deposit.interest.secondary.tiered_interest
---

# `&{tiered_interest_rates}`

_No description in the resource definition._

**Constraint:** `string_constraint`  
**CLU resource:** `feature_library/src/feature_library/deposit/interest/parameter_resource_defs/tiered_interest_rates.resource.yaml`

## Referenced by

- [deposit.interest.secondary.tiered_interest](/features/deposit/interest/secondary/tiered_interest.md)

<!-- generated:end -->
