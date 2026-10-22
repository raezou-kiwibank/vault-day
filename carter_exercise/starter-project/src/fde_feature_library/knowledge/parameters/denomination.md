---
type: Vault Parameter
okf_version: "0.2"
profile: https://thoughtmachine.example/fde/schemas/feature-knowledge-bundle/1.0.json
profile_version: 1.0.0
title: denomination
description: Vault parameter denomination.
status: stable
tags:
  - parameter
identity:
  clu_id: denomination
  reference: "&{denomination}"
  constraint: string_constraint
  clu_resource: feature_library/src/feature_library/common/parameter_resource_defs/denomination.resource.yaml
generated:
  by: process:fl/0.1.0
used_by:
  - common.denomination
  - deposit.fees.early_closure_fee
  - deposit.fees.inactivity_fee
  - deposit.fees.maintenance_fees
  - deposit.fees.minimum_monthly_balance
  - deposit.fees.overdraft_limit
  - deposit.fees.paper_statement_fee
  - deposit.fees.unarranged_overdraft_fee
  - deposit.fees.withdrawal.early_withdrawal_fees
  - deposit.fees.withdrawal.excess_fee
  - deposit.fees.withdrawal.payment_type_flat_fee
  - deposit.fees.withdrawal.payment_type_monthly_limit_fee
  - deposit.fees.withdrawal.payment_type_threshold_fee
  - deposit.interest.interest_accrual
  - deposit.interest.interest_application
  - deposit.temporal_features.cooling_off_period
  - deposit.temporal_features.grace_period
  - deposit.transaction_limits.deposit_limits.maximum_balance_limit
  - deposit.transaction_limits.deposit_limits.maximum_daily_deposit
  - deposit.transaction_limits.deposit_limits.maximum_single_deposit
  - deposit.transaction_limits.deposit_limits.minimum_initial_deposit
  - deposit.transaction_limits.deposit_limits.minimum_single_deposit
  - deposit.transaction_limits.withdrawal_limits.maximum_daily_withdrawal
  - deposit.transaction_limits.withdrawal_limits.maximum_daily_withdrawal_by_transaction_type
  - deposit.transaction_limits.withdrawal_limits.maximum_single_withdrawal
  - deposit.transaction_limits.withdrawal_limits.maximum_withdrawal_by_payment_type
  - deposit.transaction_limits.withdrawal_limits.minimum_balance_by_tier
  - deposit.transaction_limits.withdrawal_limits.minimum_single_withdrawal
  - lending.disbursal.disbursement
  - lending.interest.interest_accrual
  - lending.interest.interest_application
  - lending.principal.maximum_loan_principal
  - lending.principal.minimum_loan_principal
  - lending.repayments.early_repayment
  - lending.repayments.late_repayment
  - lending.repayments.overpayment
  - lending.repayments.overpayment_allowance
---

# `&{denomination}`

_No description in the resource definition._

**Constraint:** `string_constraint`  
**CLU resource:** `feature_library/src/feature_library/common/parameter_resource_defs/denomination.resource.yaml`

## Referenced by

- [common.denomination](/features/common/denomination.md)
- [deposit.fees.early_closure_fee](/features/deposit/fees/early_closure_fee.md)
- [deposit.fees.inactivity_fee](/features/deposit/fees/inactivity_fee.md)
- [deposit.fees.maintenance_fees](/features/deposit/fees/maintenance_fees.md)
- [deposit.fees.minimum_monthly_balance](/features/deposit/fees/minimum_monthly_balance.md)
- [deposit.fees.overdraft_limit](/features/deposit/fees/overdraft_limit.md)
- [deposit.fees.paper_statement_fee](/features/deposit/fees/paper_statement_fee.md)
- [deposit.fees.unarranged_overdraft_fee](/features/deposit/fees/unarranged_overdraft_fee.md)
- [deposit.fees.withdrawal.early_withdrawal_fees](/features/deposit/fees/withdrawal/early_withdrawal_fees.md)
- [deposit.fees.withdrawal.excess_fee](/features/deposit/fees/withdrawal/excess_fee.md)
- [deposit.fees.withdrawal.payment_type_flat_fee](/features/deposit/fees/withdrawal/payment_type_flat_fee.md)
- [deposit.fees.withdrawal.payment_type_monthly_limit_fee](/features/deposit/fees/withdrawal/payment_type_monthly_limit_fee.md)
- [deposit.fees.withdrawal.payment_type_threshold_fee](/features/deposit/fees/withdrawal/payment_type_threshold_fee.md)
- [deposit.interest.interest_accrual](/features/deposit/interest/interest_accrual.md)
- [deposit.interest.interest_application](/features/deposit/interest/interest_application.md)
- [deposit.temporal_features.cooling_off_period](/features/deposit/temporal_features/cooling_off_period.md)
- [deposit.temporal_features.grace_period](/features/deposit/temporal_features/grace_period.md)
- [deposit.transaction_limits.deposit_limits.maximum_balance_limit](/features/deposit/transaction_limits/deposit_limits/maximum_balance_limit.md)
- [deposit.transaction_limits.deposit_limits.maximum_daily_deposit](/features/deposit/transaction_limits/deposit_limits/maximum_daily_deposit.md)
- [deposit.transaction_limits.deposit_limits.maximum_single_deposit](/features/deposit/transaction_limits/deposit_limits/maximum_single_deposit.md)
- [deposit.transaction_limits.deposit_limits.minimum_initial_deposit](/features/deposit/transaction_limits/deposit_limits/minimum_initial_deposit.md)
- [deposit.transaction_limits.deposit_limits.minimum_single_deposit](/features/deposit/transaction_limits/deposit_limits/minimum_single_deposit.md)
- [deposit.transaction_limits.withdrawal_limits.maximum_daily_withdrawal](/features/deposit/transaction_limits/withdrawal_limits/maximum_daily_withdrawal.md)
- [deposit.transaction_limits.withdrawal_limits.maximum_daily_withdrawal_by_transaction_type](/features/deposit/transaction_limits/withdrawal_limits/maximum_daily_withdrawal_by_transaction_type.md)
- [deposit.transaction_limits.withdrawal_limits.maximum_single_withdrawal](/features/deposit/transaction_limits/withdrawal_limits/maximum_single_withdrawal.md)
- [deposit.transaction_limits.withdrawal_limits.maximum_withdrawal_by_payment_type](/features/deposit/transaction_limits/withdrawal_limits/maximum_withdrawal_by_payment_type.md)
- [deposit.transaction_limits.withdrawal_limits.minimum_balance_by_tier](/features/deposit/transaction_limits/withdrawal_limits/minimum_balance_by_tier.md)
- [deposit.transaction_limits.withdrawal_limits.minimum_single_withdrawal](/features/deposit/transaction_limits/withdrawal_limits/minimum_single_withdrawal.md)
- [lending.disbursal.disbursement](/features/lending/disbursal/disbursement.md)
- [lending.interest.interest_accrual](/features/lending/interest/interest_accrual.md)
- [lending.interest.interest_application](/features/lending/interest/interest_application.md)
- [lending.principal.maximum_loan_principal](/features/lending/principal/maximum_loan_principal.md)
- [lending.principal.minimum_loan_principal](/features/lending/principal/minimum_loan_principal.md)
- [lending.repayments.early_repayment](/features/lending/repayments/early_repayment.md)
- [lending.repayments.late_repayment](/features/lending/repayments/late_repayment.md)
- [lending.repayments.overpayment](/features/lending/repayments/overpayment.md)
- [lending.repayments.overpayment_allowance](/features/lending/repayments/overpayment_allowance.md)

<!-- generated:end -->
