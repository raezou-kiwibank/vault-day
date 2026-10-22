---
type: Vault Product
okf_version: "0.2"
profile: https://thoughtmachine.example/fde/schemas/feature-knowledge-bundle/1.0.json
profile_version: 1.0.0
title: Offset Mortgage
description: A capital-and-interest repayment mortgage on declining-principal amortisation, with daily interest accrual, monthly due amount calculation, overdue and delinquency handling, overpayment with an annual allowance, redraw, and an optional offset against a linked Personal Current Account that reduces the balance interest is charged on.
status: draft
tags:
  - lending
  - asset
identity:
  id: mortgage
  domain: lending
  tside: ASSET
  contract: products/mortgage/contracts/template/mortgage.py
  contract_exists: false
generated:
  by: process:fl/0.1.0
features:
  - lending.disbursal.disbursement
  - lending.principal.principal
  - lending.principal.minimum_loan_principal
  - lending.principal.maximum_loan_principal
  - lending.term.term
  - lending.interest.interest_accrual
  - lending.interest.interest_application
  - lending.interest.interest_capitalisation
  - lending.interest.secondary.fixed_rate
  - lending.interest.secondary.variable_rate
  - lending.amortisations.amortisation_methods.declining_principal
  - lending.amortisations.eia
  - lending.amortisations.due_amount_notification
  - lending.overdue.overdue
  - lending.delinquency.delinquency
  - lending.repayments.late_repayment
  - lending.repayments.payments
  - lending.repayments.secondary.horizontal_repayment_hierarchy
  - lending.repayments.overpayment
  - lending.repayments.overpayment_allowance
  - lending.repayments.early_repayment
  - lending.redraw.redraw
  - lending.closure.close_loan
  - lending.account_attributes
hooks:
  activation_hook:
    - lending.disbursal.disbursement
    - lending.interest.interest_accrual
    - lending.repayments.late_repayment
  pre_posting_hook:
    - lending.principal.minimum_loan_principal
    - lending.principal.maximum_loan_principal
    - lending.repayments.overpayment
    - lending.redraw.redraw
    - lending.closure.close_loan
  post_posting_hook:
    - lending.repayments.payments
    - lending.repayments.overpayment
    - lending.repayments.early_repayment
  scheduled_event_hook:
    - lending.interest.interest_accrual
    - lending.amortisations.amortisation_methods.declining_principal
    - lending.amortisations.due_amount_notification
    - lending.overdue.overdue
    - lending.delinquency.delinquency
    - lending.repayments.late_repayment
  derived_parameter_hook:
    - lending.account_attributes
internal_accounts:
  - ACCRUED_INTEREST_RECEIVABLE
  - INTEREST_RECEIVED
  - CAPITALISED_INTEREST_RECEIVABLE
  - CAPITALISED_INTEREST_RECEIVED
  - LATE_REPAYMENT_FEE_INCOME
  - EARLY_REPAYMENT_FEE_INCOME
  - OVERPAYMENT_FEE_INCOME
  - PENALTY_INTEREST_RECEIVED
balance_addresses:
  - PRINCIPAL
  - PRINCIPAL_DUE
  - PRINCIPAL_OVERDUE
  - ACCRUED_INTEREST_RECEIVABLE
  - INTEREST_DUE
  - INTEREST_OVERDUE
  - PENALTIES
  - EIA
  - TERM_COUNTER
  - ACCRUED_INTEREST_PENDING_CAPITALISATION
  - CAPITALISED_INTEREST_TRACKER
linked_products:
  - product: personal_current_account
    relationship: offset
    parameter: "&{offset_account}"
    description: "The linked current account's cleared balance is mirrored onto this account's offset tracker address and subtracted from the principal that interest accrues on. Modelled as a PrincipalAdjustment so the accrual engine itself needs no change, and deliberately without a Supervisor Contract: the current account pushes the mirror posting, exactly as lending.disbursal.disbursement already posts across accounts."
traceability:
  business_requirements:
    - REQ-MTG-001
    - REQ-MTG-002
    - REQ-MTG-003
    - REQ-MTG-004
tests:
  unit: 0
  simulation: 0
  e2e: 0
---

# Offset Mortgage

A capital-and-interest repayment mortgage on declining-principal amortisation, with daily interest accrual, monthly due amount calculation, overdue and delinquency handling, overpayment with an annual allowance, redraw, and an optional offset against a linked Personal Current Account that reduces the balance interest is charged on.

**Ledger side:** `ASSET`  
**Contract:** `products/mortgage/contracts/template/mortgage.py`  *(not written yet)*

## Requirements

| Id | Statement | Satisfied by | Verified by |
|---|---|---|---|
| REQ-MTG-001 | The customer repays capital and interest in equal monthly instalments over an agreed term, recalculated whenever the rate or term changes. | `lending.amortisations.amortisation_methods.declining_principal`, `lending.amortisations.eia` | **none** |
| REQ-MTG-002 | Interest is charged daily on the outstanding principal, reduced by any balance held in a linked offset account, so a customer with savings pays less interest without losing access to those savings. | — | **none** |
| REQ-MTG-003 | A missed instalment moves the amount to overdue, notifies the customer, and after the configured grace period marks the account delinquent. | `lending.overdue.overdue`, `lending.delinquency.delinquency`, `lending.repayments.late_repayment` | **none** |
| REQ-MTG-004 | The customer may overpay up to an annual allowance without charge, may redraw previous overpayments, and is charged an early repayment fee beyond the allowance. | `lending.repayments.overpayment`, `lending.repayments.overpayment_allowance`, `lending.redraw.redraw`, `lending.repayments.early_repayment` | **none** |

## Hook wiring

### `activation_hook`

- [Disbursement](/features/lending/disbursal/disbursement.md)
- [Interest Accrual](/features/lending/interest/interest_accrual.md)
- [Late Repayment](/features/lending/repayments/late_repayment.md)

### `pre_posting_hook`

- [Minimum Loan Principal](/features/lending/principal/minimum_loan_principal.md)
- [Maximum Loan Principal](/features/lending/principal/maximum_loan_principal.md)
- [Overpayment](/features/lending/repayments/overpayment.md)
- [Redraw](/features/lending/redraw/redraw.md)
- [Close Loan](/features/lending/closure/close_loan.md)

### `post_posting_hook`

- [Payments](/features/lending/repayments/payments.md)
- [Overpayment](/features/lending/repayments/overpayment.md)
- [Early Repayment](/features/lending/repayments/early_repayment.md)

### `scheduled_event_hook`

- [Interest Accrual](/features/lending/interest/interest_accrual.md)
- [Declining Principal](/features/lending/amortisations/amortisation_methods/declining_principal.md)
- [Due Amount Notification](/features/lending/amortisations/due_amount_notification.md)
- [Overdue](/features/lending/overdue/overdue.md)
- [Delinquency](/features/lending/delinquency/delinquency.md)
- [Late Repayment](/features/lending/repayments/late_repayment.md)

### `derived_parameter_hook`

- [Account Attributes](/features/lending/account_attributes.md)

## Relationships to other products

- **offset** → [personal_current_account](/products/personal_current_account.md) via `&{offset_account}`
  The linked current account's cleared balance is mirrored onto this account's offset tracker address and subtracted from the principal that interest accrues on. Modelled as a PrincipalAdjustment so the accrual engine itself needs no change, and deliberately without a Supervisor Contract: the current account pushes the mirror posting, exactly as lending.disbursal.disbursement already posts across accounts.

<!-- generated:end -->
