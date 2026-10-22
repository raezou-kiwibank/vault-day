---
type: Vault Parameter
okf_version: "0.2"
profile: https://thoughtmachine.example/fde/schemas/feature-knowledge-bundle/1.0.json
profile_version: 1.0.0
title: principal
description: Vault parameter principal.
status: stable
tags:
  - parameter
identity:
  clu_id: principal
  reference: "&{principal}"
  constraint: decimal_constraint
  clu_resource: feature_library/src/feature_library/lending/principal/parameter_resource_defs/principal.resource.yaml
generated:
  by: process:fl/0.1.0
used_by:
  - lending.amortisations.amortisation_methods.minimum_repayment
  - lending.disbursal.disbursement
  - lending.principal.principal
---

# `&{principal}`

_No description in the resource definition._

**Constraint:** `decimal_constraint`  
**CLU resource:** `feature_library/src/feature_library/lending/principal/parameter_resource_defs/principal.resource.yaml`

## Referenced by

- [lending.amortisations.amortisation_methods.minimum_repayment](/features/lending/amortisations/amortisation_methods/minimum_repayment.md)
- [lending.disbursal.disbursement](/features/lending/disbursal/disbursement.md)
- [lending.principal.principal](/features/lending/principal/principal.md)

<!-- generated:end -->
