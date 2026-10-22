---
type: Vault Parameter
okf_version: "0.2"
profile: https://thoughtmachine.example/fde/schemas/feature-knowledge-bundle/1.0.json
profile_version: 1.0.0
title: equated_instalment_amount
description: Vault parameter equated_instalment_amount.
status: stable
tags:
  - parameter
identity:
  clu_id: equated_instalment_amount
  reference: "&{equated_instalment_amount}"
  constraint: decimal_constraint
  clu_resource: feature_library/src/feature_library/lending/amortisations/parameter_resource_defs/equated_instalment_amount.resource.yaml
generated:
  by: process:fl/0.1.0
used_by:
  - lending.amortisations.eia
---

# `&{equated_instalment_amount}`

_No description in the resource definition._

**Constraint:** `decimal_constraint`  
**CLU resource:** `feature_library/src/feature_library/lending/amortisations/parameter_resource_defs/equated_instalment_amount.resource.yaml`

## Referenced by

- [lending.amortisations.eia](/features/lending/amortisations/eia.md)

<!-- generated:end -->
