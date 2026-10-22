---
type: Vault Parameter
okf_version: "0.2"
profile: https://thoughtmachine.example/fde/schemas/feature-knowledge-bundle/1.0.json
profile_version: 1.0.0
title: account_tier
description: Triggers pre-parameter change hook? No.  Optional? No.
status: stable
tags:
  - parameter
identity:
  clu_id: account_tier
  reference: "&{account_tier}"
  constraint: string_constraint
  clu_resource: feature_library/src/feature_library/deposit/fees/parameter_resource_defs/account_tier.resource.yaml
generated:
  by: process:fl/0.1.0
used_by:
  - deposit.common
  - deposit.fees.maintenance_fees
  - deposit.fees.minimum_monthly_balance
  - deposit.transaction_limits.withdrawal_limits.maximum_daily_withdrawal_by_transaction_type
  - deposit.transaction_limits.withdrawal_limits.minimum_balance_by_tier
---

# `&{account_tier}`

Triggers pre-parameter change hook? No.  Optional? No.

**Constraint:** `string_constraint`  
**CLU resource:** `feature_library/src/feature_library/deposit/fees/parameter_resource_defs/account_tier.resource.yaml`

## Referenced by

- [deposit.common](/features/deposit/common.md)
- [deposit.fees.maintenance_fees](/features/deposit/fees/maintenance_fees.md)
- [deposit.fees.minimum_monthly_balance](/features/deposit/fees/minimum_monthly_balance.md)
- [deposit.transaction_limits.withdrawal_limits.maximum_daily_withdrawal_by_transaction_type](/features/deposit/transaction_limits/withdrawal_limits/maximum_daily_withdrawal_by_transaction_type.md)
- [deposit.transaction_limits.withdrawal_limits.minimum_balance_by_tier](/features/deposit/transaction_limits/withdrawal_limits/minimum_balance_by_tier.md)

<!-- generated:end -->
