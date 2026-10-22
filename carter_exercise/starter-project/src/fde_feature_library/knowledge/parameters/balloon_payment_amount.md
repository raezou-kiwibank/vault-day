---
type: Vault Parameter
okf_version: "0.2"
profile: https://thoughtmachine.example/fde/schemas/feature-knowledge-bundle/1.0.json
profile_version: 1.0.0
title: balloon_payment_amount
description: The lump sum of principal deferred to the end of the loan term, payable with the final instalment. Defaults to zero, which amortises the loan fully over its term. Triggers pre-parameter change hook? No.  Optional? Yes.
status: stable
tags:
  - parameter
identity:
  clu_id: balloon_payment_amount
  reference: "&{balloon_payment_amount}"
  constraint: decimal_constraint
  clu_resource: feature_library/src/feature_library/lending/amortisations/parameter_resource_defs/balloon_payment_amount.resource.yaml
generated:
  by: process:fl/0.1.0
used_by:
  - lending.amortisations.amortisation_methods.minimum_repayment
---

# `&{balloon_payment_amount}`

The lump sum of principal deferred to the end of the loan term, payable with the final instalment. Defaults to zero, which amortises the loan fully over its term. Triggers pre-parameter change hook? No.  Optional? Yes.

**Constraint:** `decimal_constraint`  
**CLU resource:** `feature_library/src/feature_library/lending/amortisations/parameter_resource_defs/balloon_payment_amount.resource.yaml`

## Referenced by

- [lending.amortisations.amortisation_methods.minimum_repayment](/features/lending/amortisations/amortisation_methods/minimum_repayment.md)

<!-- generated:end -->
