---
type: Vault Parameter
okf_version: "0.2"
profile: https://thoughtmachine.example/fde/schemas/feature-knowledge-bundle/1.0.json
profile_version: 1.0.0
title: overpayment_fee_rate
description: Vault parameter overpayment_fee_rate.
status: stable
tags:
  - parameter
identity:
  clu_id: overpayment_fee_rate
  reference: "&{overpayment_fee_rate}"
  constraint: decimal_constraint
  clu_resource: feature_library/src/feature_library/lending/repayments/parameter_resource_defs/overpayment_fee_rate.resource.yaml
generated:
  by: process:fl/0.1.0
used_by:
  - lending.repayments.overpayment
---

# `&{overpayment_fee_rate}`

_No description in the resource definition._

**Constraint:** `decimal_constraint`  
**CLU resource:** `feature_library/src/feature_library/lending/repayments/parameter_resource_defs/overpayment_fee_rate.resource.yaml`

## Referenced by

- [lending.repayments.overpayment](/features/lending/repayments/overpayment.md)

<!-- generated:end -->
