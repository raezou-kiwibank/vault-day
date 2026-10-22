---
type: Vault Parameter
okf_version: "0.2"
profile: https://thoughtmachine.example/fde/schemas/feature-knowledge-bundle/1.0.json
profile_version: 1.0.0
title: term
description: Vault parameter term.
status: stable
tags:
  - parameter
identity:
  clu_id: term
  reference: "&{term}"
  constraint: decimal_constraint
  clu_resource: feature_library/src/feature_library/lending/term/parameter_resource_defs/term.resource.yaml
generated:
  by: process:fl/0.1.0
used_by:
  - lending.amortisations.amortisation_methods.minimum_repayment
  - lending.term.term
---

# `&{term}`

_No description in the resource definition._

**Constraint:** `decimal_constraint`  
**CLU resource:** `feature_library/src/feature_library/lending/term/parameter_resource_defs/term.resource.yaml`

## Referenced by

- [lending.amortisations.amortisation_methods.minimum_repayment](/features/lending/amortisations/amortisation_methods/minimum_repayment.md)
- [lending.term.term](/features/lending/term/term.md)

<!-- generated:end -->
