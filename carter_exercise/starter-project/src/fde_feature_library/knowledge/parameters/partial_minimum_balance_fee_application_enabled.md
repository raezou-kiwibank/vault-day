---
type: Vault Parameter
okf_version: "0.2"
profile: https://thoughtmachine.example/fde/schemas/feature-knowledge-bundle/1.0.json
profile_version: 1.0.0
title: partial_minimum_balance_fee_application_enabled
description: Triggers pre-parameter change hook? No.  Optional? No.
status: stable
tags:
  - parameter
identity:
  clu_id: partial_minimum_balance_fee_application_enabled
  reference: "&{partial_minimum_balance_fee_application_enabled}"
  constraint: enumeration_constraint
  clu_resource: feature_library/src/feature_library/deposit/fees/parameter_resource_defs/partial_minimum_balance_fee_application_enabled.resource.yaml
generated:
  by: process:fl/0.1.0
used_by:
  - deposit.fees.minimum_monthly_balance
---

# `&{partial_minimum_balance_fee_application_enabled}`

Triggers pre-parameter change hook? No.  Optional? No.

**Constraint:** `enumeration_constraint`  
**CLU resource:** `feature_library/src/feature_library/deposit/fees/parameter_resource_defs/partial_minimum_balance_fee_application_enabled.resource.yaml`

## Referenced by

- [deposit.fees.minimum_monthly_balance](/features/deposit/fees/minimum_monthly_balance.md)

<!-- generated:end -->
