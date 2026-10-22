---
type: Vault Parameter
okf_version: "0.2"
profile: https://thoughtmachine.example/fde/schemas/feature-knowledge-bundle/1.0.json
profile_version: 1.0.0
title: excess_fee
description: Fee charged for every withdrawal that exceeds the monthly withdrawal limit. Triggers pre-parameter change hook? No.  Optional? No.
status: stable
tags:
  - parameter
identity:
  clu_id: excess_fee
  reference: "&{excess_fee}"
  constraint: decimal_constraint
  clu_resource: feature_library/src/feature_library/deposit/fees/withdrawal/parameter_resource_defs/excess_fee.resource.yaml
generated:
  by: process:fl/0.1.0
used_by:
  - deposit.fees.withdrawal.excess_fee
---

# `&{excess_fee}`

Fee charged for every withdrawal that exceeds the monthly withdrawal limit. Triggers pre-parameter change hook? No.  Optional? No.

**Constraint:** `decimal_constraint`  
**CLU resource:** `feature_library/src/feature_library/deposit/fees/withdrawal/parameter_resource_defs/excess_fee.resource.yaml`

## Referenced by

- [deposit.fees.withdrawal.excess_fee](/features/deposit/fees/withdrawal/excess_fee.md)

<!-- generated:end -->
