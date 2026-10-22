---
type: Vault Parameter
okf_version: "0.2"
profile: https://thoughtmachine.example/fde/schemas/feature-knowledge-bundle/1.0.json
profile_version: 1.0.0
title: grace_period
description: The number of days from the account creation datetime when a user can make amendments to a deposit account without incurring any fees or penalties.
status: stable
tags:
  - parameter
identity:
  clu_id: grace_period
  reference: "&{grace_period}"
  constraint: decimal_constraint
  clu_resource: feature_library/src/feature_library/deposit/temporal_features/parameter_resource_defs/grace_period.resource.yaml
generated:
  by: process:fl/0.1.0
used_by:
  - deposit.temporal_features.grace_period
  - lending.delinquency.delinquency
---

# `&{grace_period}`

The number of days from the account creation datetime when a user can make amendments to a deposit account without incurring any fees or penalties.

**Constraint:** `decimal_constraint`  
**CLU resource:** `feature_library/src/feature_library/deposit/temporal_features/parameter_resource_defs/grace_period.resource.yaml`

## Referenced by

- [deposit.temporal_features.grace_period](/features/deposit/temporal_features/grace_period.md)
- [lending.delinquency.delinquency](/features/lending/delinquency/delinquency.md)

<!-- generated:end -->
