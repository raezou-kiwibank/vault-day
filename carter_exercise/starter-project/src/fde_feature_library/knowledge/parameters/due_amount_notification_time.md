---
type: Vault Parameter
okf_version: "0.2"
profile: https://thoughtmachine.example/fde/schemas/feature-knowledge-bundle/1.0.json
profile_version: 1.0.0
title: due_amount_notification_time
description: Vault parameter due_amount_notification_time.
status: stable
tags:
  - parameter
identity:
  clu_id: due_amount_notification_time
  reference: "&{due_amount_notification_time}"
  constraint: string_constraint
  clu_resource: feature_library/src/feature_library/lending/amortisations/parameter_resource_defs/due_amount_notification_time.resource.yaml
generated:
  by: process:fl/0.1.0
used_by:
  - lending.amortisations.due_amount_notification
---

# `&{due_amount_notification_time}`

_No description in the resource definition._

**Constraint:** `string_constraint`  
**CLU resource:** `feature_library/src/feature_library/lending/amortisations/parameter_resource_defs/due_amount_notification_time.resource.yaml`

## Referenced by

- [lending.amortisations.due_amount_notification](/features/lending/amortisations/due_amount_notification.md)

<!-- generated:end -->
