---
type: Vault Parameter
okf_version: "0.2"
profile: https://thoughtmachine.example/fde/schemas/feature-knowledge-bundle/1.0.json
profile_version: 1.0.0
title: balloon_emi_amount
description: The fixed instalment the customer pays each period on a loan that ends with a balloon payment. When set, the balloon payment is derived from it; when zero, the instalment is derived from the balloon payment instead. Triggers pre-parameter change hook? No.  Optional? Yes.
status: stable
tags:
  - parameter
identity:
  clu_id: balloon_emi_amount
  reference: "&{balloon_emi_amount}"
  constraint: decimal_constraint
  clu_resource: feature_library/src/feature_library/lending/amortisations/parameter_resource_defs/balloon_emi_amount.resource.yaml
generated:
  by: process:fl/0.1.0
used_by:
  - lending.amortisations.amortisation_methods.minimum_repayment
---

# `&{balloon_emi_amount}`

The fixed instalment the customer pays each period on a loan that ends with a balloon payment. When set, the balloon payment is derived from it; when zero, the instalment is derived from the balloon payment instead. Triggers pre-parameter change hook? No.  Optional? Yes.

**Constraint:** `decimal_constraint`  
**CLU resource:** `feature_library/src/feature_library/lending/amortisations/parameter_resource_defs/balloon_emi_amount.resource.yaml`

## Referenced by

- [lending.amortisations.amortisation_methods.minimum_repayment](/features/lending/amortisations/amortisation_methods/minimum_repayment.md)

<!-- generated:end -->
