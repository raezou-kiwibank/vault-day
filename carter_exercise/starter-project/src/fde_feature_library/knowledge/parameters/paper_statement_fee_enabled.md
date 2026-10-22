---
type: Vault Parameter
okf_version: "0.2"
profile: https://thoughtmachine.example/fde/schemas/feature-knowledge-bundle/1.0.json
profile_version: 1.0.0
title: paper_statement_fee_enabled
description: Triggers pre-parameter change hook? No.  Optional? No.
status: stable
tags:
  - parameter
identity:
  clu_id: paper_statement_fee_enabled
  reference: "&{paper_statement_fee_enabled}"
  constraint: enumeration_constraint
  clu_resource: feature_library/src/feature_library/deposit/fees/parameter_resource_defs/paper_statement_fee_enabled.resource.yaml
generated:
  by: process:fl/0.1.0
used_by:
  - deposit.fees.paper_statement_fee
---

# `&{paper_statement_fee_enabled}`

Triggers pre-parameter change hook? No.  Optional? No.

**Constraint:** `enumeration_constraint`  
**CLU resource:** `feature_library/src/feature_library/deposit/fees/parameter_resource_defs/paper_statement_fee_enabled.resource.yaml`

## Referenced by

- [deposit.fees.paper_statement_fee](/features/deposit/fees/paper_statement_fee.md)

<!-- generated:end -->
