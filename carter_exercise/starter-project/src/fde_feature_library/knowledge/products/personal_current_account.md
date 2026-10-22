---
type: Vault Product
okf_version: "0.2"
profile: https://thoughtmachine.example/fde/schemas/feature-knowledge-bundle/1.0.json
profile_version: 1.0.0
title: Personal Current Account
description: "An everyday current account with credit interest, an arranged overdraft, monthly maintenance and minimum-balance fees, and transaction limits. It is also the offset counterparty for the mortgage: its cleared balance is mirrored to the mortgage so the customer pays interest only on the difference."
status: draft
tags:
  - deposit
  - liability
identity:
  id: personal_current_account
  domain: deposit
  tside: LIABILITY
  contract: products/personal_current_account/contracts/template/personal_current_account.py
  contract_exists: false
generated:
  by: process:fl/0.1.0
features:
  - deposit.interest.interest_accrual
  - deposit.interest.interest_application
  - deposit.interest.secondary.flat_interest
  - deposit.interest.secondary.overdraft_interest
  - deposit.fees.overdraft_limit
  - deposit.fees.unarranged_overdraft_fee
  - deposit.fees.maintenance_fees
  - deposit.fees.minimum_monthly_balance
  - deposit.fees.partial_fee
  - deposit.transaction_limits.deposit_limits.maximum_balance_limit
  - deposit.transaction_limits.withdrawal_limits.maximum_daily_withdrawal
  - deposit.transaction_limits.withdrawal_limits.maximum_single_withdrawal
  - deposit.dormancy.dormancy
hooks:
  activation_hook:
    - deposit.interest.interest_accrual
    - deposit.interest.interest_application
    - deposit.fees.maintenance_fees
    - deposit.fees.minimum_monthly_balance
    - deposit.fees.unarranged_overdraft_fee
  pre_posting_hook:
    - deposit.dormancy.dormancy
    - deposit.fees.overdraft_limit
    - deposit.transaction_limits.deposit_limits.maximum_balance_limit
    - deposit.transaction_limits.withdrawal_limits.maximum_daily_withdrawal
    - deposit.transaction_limits.withdrawal_limits.maximum_single_withdrawal
  post_posting_hook:
    - deposit.fees.partial_fee
  scheduled_event_hook:
    - deposit.interest.interest_accrual
    - deposit.interest.interest_application
    - deposit.interest.secondary.overdraft_interest
    - deposit.fees.maintenance_fees
    - deposit.fees.minimum_monthly_balance
    - deposit.fees.unarranged_overdraft_fee
internal_accounts:
  - ACCRUED_INTEREST_PAYABLE
  - ACCRUED_INTEREST_RECEIVABLE
  - INTEREST_PAID
  - INTEREST_RECEIVED
  - OVERDRAFT_INTEREST_RECEIVABLE
  - OVERDRAFT_INTEREST_RECEIVED
  - MAINTENANCE_FEE_INCOME
  - MINIMUM_BALANCE_FEE_INCOME
  - UNARRANGED_OVERDRAFT_FEE_INCOME
balance_addresses:
  - ACCRUED_INTEREST_PAYABLE
  - ACCRUED_INTEREST_RECEIVABLE
  - PENALTIES
linked_products:
  - product: mortgage
    relationship: offset_source
    parameter: "&{offset_target_account}"
    description: When set, this account mirrors its cleared balance onto the mortgage's offset tracker address after every posting and on a daily schedule, so the mortgage can reduce its accrual base without reading another account's balances.
traceability:
  business_requirements:
    - REQ-PCA-001
    - REQ-PCA-002
    - REQ-PCA-003
tests:
  unit: 0
  simulation: 0
  e2e: 0
---

# Personal Current Account

An everyday current account with credit interest, an arranged overdraft, monthly maintenance and minimum-balance fees, and transaction limits. It is also the offset counterparty for the mortgage: its cleared balance is mirrored to the mortgage so the customer pays interest only on the difference.

**Ledger side:** `LIABILITY`  
**Contract:** `products/personal_current_account/contracts/template/personal_current_account.py`  *(not written yet)*

## Requirements

| Id | Statement | Satisfied by | Verified by |
|---|---|---|---|
| REQ-PCA-001 | The customer earns credit interest on cleared balances, accrued daily and applied monthly. | `deposit.interest.interest_accrual`, `deposit.interest.interest_application`, `deposit.interest.secondary.flat_interest` | **none** |
| REQ-PCA-002 | The customer may go overdrawn up to an arranged limit; beyond it the transaction is refused or an unarranged overdraft fee applies. | `deposit.fees.overdraft_limit`, `deposit.fees.unarranged_overdraft_fee`, `deposit.interest.secondary.overdraft_interest` | **none** |
| REQ-PCA-003 | Where the customer nominates this account as an offset against their mortgage, its cleared balance reduces the mortgage balance that interest is charged on, and the customer keeps full access to the money. | — | **none** |

## Hook wiring

### `activation_hook`

- [Interest Accrual](/features/deposit/interest/interest_accrual.md)
- [Interest Application](/features/deposit/interest/interest_application.md)
- [Maintenance Fees](/features/deposit/fees/maintenance_fees.md)
- [Minimum Monthly Balance](/features/deposit/fees/minimum_monthly_balance.md)
- [Unarranged Overdraft Fee](/features/deposit/fees/unarranged_overdraft_fee.md)

### `pre_posting_hook`

- [Dormancy](/features/deposit/dormancy/dormancy.md)
- [Overdraft Limit](/features/deposit/fees/overdraft_limit.md)
- [Maximum Balance Limit](/features/deposit/transaction_limits/deposit_limits/maximum_balance_limit.md)
- [Maximum Daily Withdrawal](/features/deposit/transaction_limits/withdrawal_limits/maximum_daily_withdrawal.md)
- [Maximum Single Withdrawal](/features/deposit/transaction_limits/withdrawal_limits/maximum_single_withdrawal.md)

### `post_posting_hook`

- [Partial Fee](/features/deposit/fees/partial_fee.md)

### `scheduled_event_hook`

- [Interest Accrual](/features/deposit/interest/interest_accrual.md)
- [Interest Application](/features/deposit/interest/interest_application.md)
- [Overdraft Interest](/features/deposit/interest/secondary/overdraft_interest.md)
- [Maintenance Fees](/features/deposit/fees/maintenance_fees.md)
- [Minimum Monthly Balance](/features/deposit/fees/minimum_monthly_balance.md)
- [Unarranged Overdraft Fee](/features/deposit/fees/unarranged_overdraft_fee.md)

## Relationships to other products

- **offset_source** → [mortgage](/products/mortgage.md) via `&{offset_target_account}`
  When set, this account mirrors its cleared balance onto the mortgage's offset tracker address after every posting and on a daily schedule, so the mortgage can reduce its accrual base without reading another account's balances.

<!-- generated:end -->
