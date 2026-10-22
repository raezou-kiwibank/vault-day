---
type: Vault Parameter
okf_version: "0.2"
profile: https://thoughtmachine.example/fde/schemas/feature-knowledge-bundle/1.0.json
profile_version: 1.0.0
title: capitalise_penalty_interest
description: Vault parameter capitalise_penalty_interest.
status: stable
tags:
  - parameter
identity:
  clu_id: capitalise_penalty_interest
  reference: "&{capitalise_penalty_interest}"
  constraint: enumeration_constraint
  clu_resource: feature_library/src/feature_library/lending/interest/parameter_resource_defs/capitalise_penalty_interest.resource.yaml
generated:
  by: process:fl/0.1.0
used_by:
  - lending.interest.interest_capitalisation
---

# `&{capitalise_penalty_interest}`

_No description in the resource definition._

**Constraint:** `enumeration_constraint`  
**CLU resource:** `feature_library/src/feature_library/lending/interest/parameter_resource_defs/capitalise_penalty_interest.resource.yaml`

## Referenced by

- [lending.interest.interest_capitalisation](/features/lending/interest/interest_capitalisation.md)

<!-- generated:end -->
