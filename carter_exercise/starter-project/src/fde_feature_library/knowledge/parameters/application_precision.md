---
type: Vault Parameter
okf_version: "0.2"
profile: https://thoughtmachine.example/fde/schemas/feature-knowledge-bundle/1.0.json
profile_version: 1.0.0
title: application_precision
description: Vault parameter application_precision.
status: stable
tags:
  - parameter
identity:
  clu_id: application_precision
  reference: "&{application_precision}"
  constraint: decimal_constraint
  clu_resource: feature_library/src/feature_library/common/parameter_resource_defs/application_precision.resource.yaml
generated:
  by: process:fl/0.1.0
used_by:
  - common.application_precision
  - deposit.interest.interest_application
  - lending.amortisations.amortisation_methods.minimum_repayment
  - lending.interest.interest_application
---

# `&{application_precision}`

_No description in the resource definition._

**Constraint:** `decimal_constraint`  
**CLU resource:** `feature_library/src/feature_library/common/parameter_resource_defs/application_precision.resource.yaml`

## Referenced by

- [common.application_precision](/features/common/application_precision.md)
- [deposit.interest.interest_application](/features/deposit/interest/interest_application.md)
- [lending.amortisations.amortisation_methods.minimum_repayment](/features/lending/amortisations/amortisation_methods/minimum_repayment.md)
- [lending.interest.interest_application](/features/lending/interest/interest_application.md)

<!-- generated:end -->
