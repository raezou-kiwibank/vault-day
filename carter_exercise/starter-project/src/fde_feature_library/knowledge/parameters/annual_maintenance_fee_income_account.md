---
type: Vault Parameter
okf_version: "0.2"
profile: https://thoughtmachine.example/fde/schemas/feature-knowledge-bundle/1.0.json
profile_version: 1.0.0
title: annual_maintenance_fee_income_account
description: Triggers pre-parameter change hook? No.  Optional? No.
status: stable
tags:
  - parameter
identity:
  clu_id: annual_maintenance_fee_income_account
  reference: "&{annual_maintenance_fee_income_account}"
  constraint: account_constraint
  clu_resource: feature_library/src/feature_library/deposit/fees/parameter_resource_defs/annual_maintenance_fee_income_account.resource.yaml
generated:
  by: process:fl/0.1.0
used_by:
  - deposit.fees.maintenance_fees
---

# `&{annual_maintenance_fee_income_account}`

Triggers pre-parameter change hook? No.  Optional? No.

**Constraint:** `account_constraint`  
**CLU resource:** `feature_library/src/feature_library/deposit/fees/parameter_resource_defs/annual_maintenance_fee_income_account.resource.yaml`

## Referenced by

- [deposit.fees.maintenance_fees](/features/deposit/fees/maintenance_fees.md)

<!-- generated:end -->
