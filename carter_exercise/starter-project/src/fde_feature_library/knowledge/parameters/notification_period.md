---
type: Vault Parameter
okf_version: "0.2"
profile: https://thoughtmachine.example/fde/schemas/feature-knowledge-bundle/1.0.json
profile_version: 1.0.0
title: notification_period
description: Vault parameter notification_period.
status: stable
tags:
  - parameter
identity:
  clu_id: notification_period
  reference: "&{notification_period}"
  constraint: decimal_constraint
  clu_resource: feature_library/src/feature_library/lending/amortisations/parameter_resource_defs/notification_period.resource.yaml
generated:
  by: process:fl/0.1.0
used_by:
  - lending.amortisations.due_amount_notification
---

# `&{notification_period}`

_No description in the resource definition._

**Constraint:** `decimal_constraint`  
**CLU resource:** `feature_library/src/feature_library/lending/amortisations/parameter_resource_defs/notification_period.resource.yaml`

## Referenced by

- [lending.amortisations.due_amount_notification](/features/lending/amortisations/due_amount_notification.md)

<!-- generated:end -->
