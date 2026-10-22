---
type: Vault Product
okf_version: "0.2"
profile: https://thoughtmachine.example/fde/schemas/feature-knowledge-bundle/1.0.json
profile_version: 1.0.0
title: Corporate Current Account
description: An operating account for a corporate customer, divided into named sub-accounts such as operating, payroll and tax reserve. Each sub-account carries its own balance, its own transaction limits and its own entitlements, while interest, fees and regulatory reporting are assessed on the pooled position across all of them.
status: draft
tags:
  - corporate
  - liability
identity:
  id: corporate_current_account
  domain: corporate
  tside: LIABILITY
  contract: products/corporate_current_account/contracts/template/corporate_current_account.py
  contract_exists: false
generated:
  by: process:fl/0.1.0
features:
  - deposit.transaction_limits.deposit_limits.maximum_single_deposit
  - deposit.transaction_limits.deposit_limits.maximum_daily_deposit
  - deposit.transaction_limits.deposit_limits.maximum_balance_limit
  - deposit.transaction_limits.withdrawal_limits.maximum_single_withdrawal
  - deposit.transaction_limits.withdrawal_limits.maximum_daily_withdrawal
  - deposit.transaction_limits.withdrawal_limits.maximum_daily_withdrawal_by_transaction_type
  - deposit.transaction_limits.withdrawal_limits.minimum_single_withdrawal
  - deposit.fees.overdraft_limit
  - deposit.fees.unarranged_overdraft_fee
  - deposit.interest.secondary.overdraft_interest
  - deposit.interest.interest_accrual
  - deposit.interest.interest_application
  - deposit.interest.secondary.tiered_interest
  - deposit.fees.maintenance_fees
  - deposit.fees.minimum_monthly_balance
  - deposit.fees.paper_statement_fee
  - deposit.fees.partial_fee
  - deposit.fees.withdrawal.payment_type_flat_fee
  - deposit.fees.withdrawal.payment_type_threshold_fee
  - deposit.dormancy.dormancy
hooks:
  activation_hook:
    - deposit.interest.interest_accrual
    - deposit.interest.interest_application
    - deposit.fees.maintenance_fees
    - deposit.fees.minimum_monthly_balance
    - deposit.fees.paper_statement_fee
    - deposit.fees.unarranged_overdraft_fee
  pre_posting_hook:
    - deposit.dormancy.dormancy
    - deposit.fees.overdraft_limit
    - deposit.transaction_limits.deposit_limits.maximum_single_deposit
    - deposit.transaction_limits.deposit_limits.maximum_daily_deposit
    - deposit.transaction_limits.deposit_limits.maximum_balance_limit
    - deposit.transaction_limits.withdrawal_limits.maximum_single_withdrawal
    - deposit.transaction_limits.withdrawal_limits.maximum_daily_withdrawal
    - deposit.transaction_limits.withdrawal_limits.maximum_daily_withdrawal_by_transaction_type
    - deposit.transaction_limits.withdrawal_limits.minimum_single_withdrawal
  post_posting_hook:
    - deposit.fees.partial_fee
  scheduled_event_hook:
    - deposit.interest.interest_accrual
    - deposit.interest.interest_application
    - deposit.interest.secondary.overdraft_interest
    - deposit.fees.maintenance_fees
    - deposit.fees.minimum_monthly_balance
    - deposit.fees.paper_statement_fee
    - deposit.fees.unarranged_overdraft_fee
    - deposit.fees.withdrawal.payment_type_flat_fee
    - deposit.fees.withdrawal.payment_type_threshold_fee
internal_accounts:
  - ACCRUED_INTEREST_PAYABLE
  - ACCRUED_INTEREST_RECEIVABLE
  - INTEREST_PAID
  - INTEREST_RECEIVED
  - OVERDRAFT_INTEREST_RECEIVABLE
  - OVERDRAFT_INTEREST_RECEIVED
  - MAINTENANCE_FEE_INCOME
  - MINIMUM_BALANCE_FEE_INCOME
  - PAPER_STATEMENT_FEE_INCOME
  - UNARRANGED_OVERDRAFT_FEE_INCOME
  - PAYMENT_TYPE_FEE_INCOME
balance_addresses:
  - ACCRUED_INTEREST_PAYABLE
  - ACCRUED_INTEREST_RECEIVABLE
  - PENALTIES
  - INTERNAL_CONTRA
linked_products: []
traceability:
  business_requirements:
    - REQ-CORP-001
    - REQ-CORP-002
    - REQ-CORP-003
    - REQ-CORP-004
    - REQ-CORP-005
tests:
  unit: 0
  simulation: 0
  e2e: 0
---

# Corporate Current Account

An operating account for a corporate customer, divided into named sub-accounts such as operating, payroll and tax reserve. Each sub-account carries its own balance, its own transaction limits and its own entitlements, while interest, fees and regulatory reporting are assessed on the pooled position across all of them.

**Ledger side:** `LIABILITY`  
**Contract:** `products/corporate_current_account/contracts/template/corporate_current_account.py`  *(not written yet)*

## Requirements

| Id | Statement | Satisfied by | Verified by |
|---|---|---|---|
| REQ-CORP-001 | A corporate customer can hold several named sub-accounts under one banking relationship, each with its own balance and its own transaction limits, so that operating cash, payroll and tax reserves are ring-fenced from one another. | — | **none** |
| REQ-CORP-002 | Interest and fees are assessed on the pooled balance across all sub-accounts, so the customer is not penalised for organising their money into several pots. | — | **none** |
| REQ-CORP-003 | A shortfall on one sub-account can be covered automatically from a nominated funding sub-account, up to a configured limit, before any overdraft is used. | — | **none** |
| REQ-CORP-004 | Each sub-account can restrict which payment types and counterparties may debit it, so a payroll pot cannot be spent on card transactions. | — | **none** |
| REQ-CORP-005 | Every posting is attributed to exactly one sub-account, and a statement can be produced per sub-account as well as for the relationship as a whole. | — | **none** |

## Hook wiring

### `activation_hook`

- [Interest Accrual](/features/deposit/interest/interest_accrual.md)
- [Interest Application](/features/deposit/interest/interest_application.md)
- [Maintenance Fees](/features/deposit/fees/maintenance_fees.md)
- [Minimum Monthly Balance](/features/deposit/fees/minimum_monthly_balance.md)
- [Paper Statement Fee](/features/deposit/fees/paper_statement_fee.md)
- [Unarranged Overdraft Fee](/features/deposit/fees/unarranged_overdraft_fee.md)

### `pre_posting_hook`

- [Dormancy](/features/deposit/dormancy/dormancy.md)
- [Overdraft Limit](/features/deposit/fees/overdraft_limit.md)
- [Maximum Single Deposit](/features/deposit/transaction_limits/deposit_limits/maximum_single_deposit.md)
- [Maximum Daily Deposit](/features/deposit/transaction_limits/deposit_limits/maximum_daily_deposit.md)
- [Maximum Balance Limit](/features/deposit/transaction_limits/deposit_limits/maximum_balance_limit.md)
- [Maximum Single Withdrawal](/features/deposit/transaction_limits/withdrawal_limits/maximum_single_withdrawal.md)
- [Maximum Daily Withdrawal](/features/deposit/transaction_limits/withdrawal_limits/maximum_daily_withdrawal.md)
- [Maximum Daily Withdrawal By Transaction Type](/features/deposit/transaction_limits/withdrawal_limits/maximum_daily_withdrawal_by_transaction_type.md)
- [Minimum Single Withdrawal](/features/deposit/transaction_limits/withdrawal_limits/minimum_single_withdrawal.md)

### `post_posting_hook`

- [Partial Fee](/features/deposit/fees/partial_fee.md)

### `scheduled_event_hook`

- [Interest Accrual](/features/deposit/interest/interest_accrual.md)
- [Interest Application](/features/deposit/interest/interest_application.md)
- [Overdraft Interest](/features/deposit/interest/secondary/overdraft_interest.md)
- [Maintenance Fees](/features/deposit/fees/maintenance_fees.md)
- [Minimum Monthly Balance](/features/deposit/fees/minimum_monthly_balance.md)
- [Paper Statement Fee](/features/deposit/fees/paper_statement_fee.md)
- [Unarranged Overdraft Fee](/features/deposit/fees/unarranged_overdraft_fee.md)
- [Payment Type Flat Fee](/features/deposit/fees/withdrawal/payment_type_flat_fee.md)
- [Payment Type Threshold Fee](/features/deposit/fees/withdrawal/payment_type_threshold_fee.md)

<!-- generated:end -->
