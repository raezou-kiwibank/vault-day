---
type: Vault Parameter
okf_version: "0.2"
profile: https://thoughtmachine.example/fde/schemas/feature-knowledge-bundle/1.0.json
profile_version: 1.0.0
title: interest_application_time
description: Vault parameter interest_application_time.
status: stable
tags:
  - parameter
identity:
  clu_id: interest_application_time
  reference: "&{interest_application_time}"
  constraint: string_constraint
  clu_resource: feature_library/src/feature_library/deposit/interest/parameter_resource_defs/interest_application_time.resource.yaml
generated:
  by: process:fl/0.1.0
used_by:
  - deposit.interest.interest_application
---

# `&{interest_application_time}`

_No description in the resource definition._

**Constraint:** `string_constraint`  
**CLU resource:** `feature_library/src/feature_library/deposit/interest/parameter_resource_defs/interest_application_time.resource.yaml`

## Referenced by

- [deposit.interest.interest_application](/features/deposit/interest/interest_application.md)

<!-- generated:end -->
