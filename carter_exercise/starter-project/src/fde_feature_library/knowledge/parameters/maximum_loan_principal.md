---
type: Vault Parameter
okf_version: "0.2"
profile: https://thoughtmachine.example/fde/schemas/feature-knowledge-bundle/1.0.json
profile_version: 1.0.0
title: maximum_loan_principal
description: Vault parameter maximum_loan_principal.
status: stable
tags:
  - parameter
identity:
  clu_id: maximum_loan_principal
  reference: "&{maximum_loan_principal}"
  constraint: decimal_constraint
  clu_resource: feature_library/src/feature_library/lending/principal/parameter_resource_defs/maximum_loan_principal.resource.yaml
generated:
  by: process:fl/0.1.0
used_by:
  - lending.principal.maximum_loan_principal
---

# `&{maximum_loan_principal}`

_No description in the resource definition._

**Constraint:** `decimal_constraint`  
**CLU resource:** `feature_library/src/feature_library/lending/principal/parameter_resource_defs/maximum_loan_principal.resource.yaml`

## Referenced by

- [lending.principal.maximum_loan_principal](/features/lending/principal/maximum_loan_principal.md)

<!-- generated:end -->
