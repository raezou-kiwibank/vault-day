---
type: Vault Parameter
okf_version: "0.2"
profile: https://thoughtmachine.example/fde/schemas/feature-knowledge-bundle/1.0.json
profile_version: 1.0.0
title: interest_application_day
description: Vault parameter interest_application_day.
status: stable
tags:
  - parameter
identity:
  clu_id: interest_application_day
  reference: "&{interest_application_day}"
  constraint: decimal_constraint
  clu_resource: feature_library/src/feature_library/deposit/interest/parameter_resource_defs/interest_application_day.resource.yaml
generated:
  by: process:fl/0.1.0
used_by:
  - deposit.interest.interest_application
---

# `&{interest_application_day}`

_No description in the resource definition._

**Constraint:** `decimal_constraint`  
**CLU resource:** `feature_library/src/feature_library/deposit/interest/parameter_resource_defs/interest_application_day.resource.yaml`

## Referenced by

- [deposit.interest.interest_application](/features/deposit/interest/interest_application.md)

<!-- generated:end -->
