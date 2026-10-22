# Notice Saver — Requirements

## Overview

Kiwibank Notice Saver is an NZD savings product for retail, business, trust and commercial
customers. Each account uses either a 32-calendar-day or 90-calendar-day notice horizon.
Funds earn a treasury-managed variable rate, monthly interest is taxed under the PIE regime,
and approved emergency breaks preserve principal by limiting any fee to net interest earned.

## Confirmed decisions

- **D-01 - Product type (Brief)**: Deposit savings product structured as a PIE.
- **D-02 - Currency (Brief)**: NZD only.
- **D-03 - Target Vault version (Q1)**: Vault Core 5.9; use CLV4 and the bundled Vault 5.9
  reference documentation.
- **D-04 - Portfolio cap enforcement (Q2, Q6)**: The NZD 5,000,000 limit applies across
  accounts and must be enforced by an upstream coordinator. The per-account contract does
  not claim to enforce this aggregate limit.
- **D-05 - Opening carded rates (Q3)**: The exact launch rates are TBC. The 32-day rate must
  be within 4.00%–4.10% p.a.; the 90-day rate must be within 4.25%–4.60% p.a.
- **D-06 - Day count (Brief)**: Use a fixed 365-day divisor, including leap years. This is
  the brief's “Actual / 365” rule; it is not the feature-library `"actual"` convention,
  which uses 366 in leap years.
- **D-07 - Notice counting and payout time (Q4, Q12)**: Lodgement date is day 0. A 32-day
  notice is due on the lodgement date plus 32 calendar days; a 90-day notice is due on the
  lodgement date plus 90 calendar days. Pay matured funds at 00:02 Pacific/Auckland on that
  due date. Weekends and public holidays do not shift the due date.
- **D-08 - Break-fee cap (Q5, Q10)**: Calculate the fee on the broken principal and cap it
  at net interest attributable to that principal after PIE tax.
- **D-09 - Closure with active notices (Q7)**: Close immediately. Treat each still-locked
  notice amount as an emergency break and apply the lesser-of fee, unless an approved
  hardship waiver applies.
- **D-10 - Dormancy trigger (Q8)**: An external monitor identifies accounts with at least
  three years without customer-initiated transactions and applies the configured dormancy
  flag.
- **D-11 - Dormancy payout exceptions (Q11)**: Dormancy blocks customer-initiated debits and
  new notice lodgements, but does not block automatic maturity payouts or account-closure
  sweeps.
- **D-12 - Schedule ordering (Q9, Q12)**: Accrue interest at 23:59:59 on the final calendar
  day. Apply PIE tax and net monthly interest at 00:01 on the first day of the following
  month. Run a maturity payout at 00:02, so it follows interest application when both occur
  on the same date.

## Standing assumptions

- **A-01 - Product variants**: The selected notice horizon is fixed per account at opening;
  32-day and 90-day rates are configured separately. Source: product matrix.
- **A-02 - Rate changes**: Treasury updates the effective-dated carded rate for a variant.
  Existing notice balances earn the prevailing rate each day through payout. Source: the
  brief's “carded variable” and “prevailing carded variable rate” requirements.
- **A-03 - Rounding**: Use the feature-library convention of rounding the daily rate to
  10 decimal places and daily accrual to 5 decimal places, with `ROUND_HALF_UP`; apply
  monetary amounts and calculate PIE tax to NZD cents (2 decimal places), also with
  `ROUND_HALF_UP`. The library helper uses these rate/accrual conventions; cents follow NZD
  minor units. Confirm before production configuration.
- **A-04 - Schedule timezone**: Use Pacific/Auckland wall-clock time for schedules, including
  daylight-saving transitions. The brief says NZST; the local-zone interpretation is
  provisional and should be confirmed.
- **A-05 - Ordinary withdrawals**: Customer withdrawals require notice. The only outward
  payment routes are matured notice payouts, authorised emergency breaks and closure sweeps.
  Source: the permitted/prohibited channel lists.
- **A-06 - Incoming transactions**: A valid top-up does not change the release date or
  amount of any existing notice batch. Source: product baseline.
- **A-07 - Interest rate for a break**: Use the carded rate effective when the break is
  processed for the calculated charge; cap it using the notice batch's attributable net
  interest. This follows the variable-rate design and remains subject to correction.
- **A-08 - Channel and account integrations**: The upstream coordinator, account-opening
  process and Vault payment rails authenticate customers and validate/link the nominated
  domestic account. The product contract only consumes the configured account reference.
- **A-09 - Posting dates**: Backdated and future-dated postings follow Vault Core's standard
  behaviour; the product contract adds no custom rejection based only on posting date.

## Open items

| Item | Type | Needed for | Owner |
|---|---|---|---|
| Exact opening 32-day and 90-day rates within their stated ranges | Parameter value | Initial product configuration and worked deployment values | Treasury |
| Upstream coordinator design, owner and atomic enforcement of the NZD 5,000,000 portfolio cap | External dependency | Prevent concurrent deposits from breaching the aggregate limit | Product/platform team |
| Internal account IDs and GL mapping for accrued interest expense/payable, net interest, PIE tax payable/remittance, break-fee income and payment settlement | Parameter value / external dependency | CLU pack, accounting entries and deployment | Finance / Vault administrator |
| Treasury rate-change approval, publication and effective-time process | External dependency | Updating the prevailing rate without repricing history incorrectly | Treasury |
| Dormancy-monitor owner, activity-event definition, flag ID and flag-clearing process | External dependency | Setting and clearing the three-year dormancy hold | Operations |
| Hardship approval authority, evidence process and flag ID | External dependency | Authorising fee waivers for hardship, terminal illness or bereavement | Operations / Compliance |
| Core transaction codes and payment-rail mappings for permitted inward/outward channels | External dependency | Distinguishing allowed credits, transfers, maturity payouts, emergency breaks and prohibited debits | Payments / Vault administrator |
| Nominated-account validation and same-bank / interbank settlement behavior | External dependency | Onboarding and automated maturity/closure payments | Product/platform team |
| Production confirmation of the rounding assumptions and Auckland local-time interpretation | Business decision | Final configuration and acceptance testing | Product owner |
| Legal confirmation of PIE tax, DCS eligibility and statutory reporting/account mappings | External dependency | Production readiness; not determined by the contract | Legal / Compliance |

## Lifecycle

1. **Opening**: Create an NZD account with a fixed 32- or 90-day horizon, a nominated
   domestic transactional account and a PIR of 0%, 10.5%, 17.5% or 28%.
2. **Available**: Cleared deposits remain available for notice lodgement. The customer may
   top up at any time; a top-up does not restart existing notice batches.
3. **Notice locked**: A valid partial or full notice request moves the requested cleared
   amount from available funds to a separate notice batch. Each batch has its own release
   date. Cancellation before maturity returns that batch immediately to available funds
   without penalty.
4. **Matured**: At 00:02 Pacific/Auckland on the due date, the batch is automatically paid
   to the nominated account.
5. **Emergency break**: An authorised break pays the requested locked principal immediately
   and charges the lesser of the formula amount and net interest attributable to the broken
   principal. An approved hardship flag waives the fee.
6. **Dormant**: After the external monitor applies the dormancy flag, reject customer-led
   debits and new notice lodgements. Continue inbound transfers and interest accrual; allow
   automatic maturity payouts and closure sweeps.
7. **Closed**: The customer may close at any time. Break still-locked notices under D-09,
   calculate and tax any mid-cycle accrued interest, and sweep the remaining net balance to
   the nominated account.

## Features

### Feature 1: Account setup, deposit channels and aggregate limit

**User Story:**
> As a Notice Saver customer,  
> I want to open the 32-day or 90-day variant and add funds through approved channels,  
> so that I can earn the applicable variable rate while respecting product controls.

#### Overview

At opening, require one supported notice horizon, a nominated-account reference and a
permitted PIR. Accept NZD only. Permit direct credits, internal transfers and automated
recurring savings. Reject card, ATM, cheque, direct-debit-authority and EFTPOS merchant
debits. The upstream coordinator enforces the NZD 5,000,000 aggregate cap across accounts;
the account contract cannot safely derive that cap from its own balance.

#### Build Approach

- **Approach**: Mixed
- **Library module**: `feature_library.common.denomination`;
  `feature_library.deposit.transaction_limits.deposit_limits.maximum_balance_limit` is
  available only for a per-account limit.
- **Custom code**: Validate product-specific opening fields and channel policy; integrate
  with the upstream aggregate-cap decision.
- **Library behaviour to note**: `maximum_balance_limit.validate` compares the current
  account's live balance and proposed postings only; it is not a portfolio-wide control.
- **Status**: verified against the bundled library source

#### Parameters

| Parameter Name | Type | Level | Description | Default Value | Min Max Values |
|---|---|---|---|---|---|
| denomination | string | Product | Supported account denomination | NZD | Fixed to NZD |
| notice_period_days | integer | Account | Selected notice horizon | TBC at opening | 32 or 90 |
| nominated_account_id | string | Account | Domestic transactional account for payouts | TBC at opening | Required |
| pir_tax_rate | decimal | Account | Customer's PIE prescribed investor rate | TBC at opening | 0, 0.105, 0.175, 0.28 |
| carded_variable_rate | decimal | Product | Treasury-managed annual rate for the selected variant | TBC | 0.0400–0.0410 for 32-day; 0.0425–0.0460 for 90-day |
| portfolio_balance_limit | decimal | Global / external | Aggregate maximum balance coordinated across accounts | 5,000,000 NZD | Fixed to 5,000,000; enforced upstream |

#### Calculation Formula

N/A - this feature validates setup and routes; it does not calculate interest.

#### Acceptance Criteria

- **AC-01 - Opening fields**: **GIVEN** an opening request, **WHEN** the notice horizon,
  nominated account or PIR is missing or invalid, **THEN** the system must reject the
  request.
- **AC-02 - Product horizon**: **GIVEN** a valid opening request, **WHEN** the selected
  horizon is 32 or 90 days, **THEN** the system must bind that horizon to the account.
- **AC-03 - Zero funding**: **GIVEN** a valid opening request with an initial balance of
  NZD 0.00, **WHEN** the account opens, **THEN** the system must accept the opening.
- **AC-04 - Denomination and channels**: **GIVEN** an open account, **WHEN** a permitted
  NZD credit arrives, **THEN** the contract must accept it; **AND WHEN** a non-NZD posting
  or prohibited debit arrives, **THEN** the contract must reject it.
- **AC-05 - Aggregate cap and batch netting**: **GIVEN** the upstream aggregate is
  NZD 4,999,999.99, **WHEN** a batch contains two NZD 0.01 credits to different accounts,
  **THEN** the upstream coordinator must reject the entire batch because the combined
  aggregate would exceed NZD 5,000,000.00.
- **AC-06 - Top-ups**: **GIVEN** one or more active notices, **WHEN** an allowed top-up is
  accepted, **THEN** the system must preserve every existing notice amount and release date.
- **AC-34 - Posting dates**: **GIVEN** a valid backdated or future-dated posting,
  **WHEN** Vault Core submits it to the contract, **THEN** the contract must apply no custom
  date-based rejection and Vault Core must determine the outcome.

#### Accounting Entries

| Account Type | Internal Account Name | Balance Address | Dr/Cr | Amount | value_timestamp |
|---|---|---|---|---|---|
| Customer | N/A | DEFAULT | Cr | Accepted deposit amount | current_time |
| Internal | Funding / settlement account (TBC) | N/A | Dr | Accepted deposit amount | current_time |

#### Notification Details

N/A - no customer notification type is specified in the brief.

### Feature 2: Notice lodgement and cancellation

**User Story:**
> As a Notice Saver customer,  
> I want to lodge or cancel a withdrawal notice,  
> so that I can schedule access to a partial or full cleared balance.

#### Overview

Create independent notice batches for each valid request. Move only the requested cleared
amount from `DEFAULT` to a custom `NOTICE_LOCKED` address. Do not change other batches when
the customer deposits more funds. Cancellation before maturity reverses the lock without a
fee.

#### Build Approach

- **Approach**: Custom
- **Library module**: `feature_library.common.balance_utils` and
  `feature_library.common.posting_utils` may be reused for balance and posting helpers.
- **Custom code**: Notice-batch state, amount segregation, release-date calculation,
  cancellation and validation.
- **Library behaviour to note**: No supplied deposit feature models multiple notice batches
  with separate release dates.
- **Status**: verified against the bundled library catalogue

#### Parameters

| Parameter Name | Type | Level | Description | Default Value | Min Max Values |
|---|---|---|---|---|---|
| notice_period_days | integer | Account | Horizon used for a new batch | Account selection | 32 or 90 |
| notice_batch_amount | decimal | Account / batch | Cleared amount moved into notice | Customer request | Greater than NZD 0.00 and no more than available cleared balance |

#### Calculation Formula

`release_date = lodge_date + notice_period_days calendar days`

`available_after_lodgement = available_before_lodgement - notice_amount`

`notice_locked_after_lodgement = notice_locked_before_lodgement + notice_amount`

Lodgement date is day 0. Use calendar-date arithmetic in Pacific/Auckland; weekends and
public holidays do not alter the release date.

#### Acceptance Criteria

- **AC-07 - Partial lodgement**: **GIVEN** NZD 10,000.00 of cleared available funds,
  **WHEN** the customer lodges NZD 4,000.00, **THEN** the contract must lock NZD 4,000.00
  and leave NZD 6,000.00 available.
- **AC-08 - Full lodgement**: **GIVEN** NZD 10,000.00 of cleared available funds,
  **WHEN** the customer lodges NZD 10,000.00, **THEN** the contract must lock the full
  amount.
- **AC-09 - Invalid lodgement**: **GIVEN** NZD 6,000.00 available, **WHEN** a customer
  lodges NZD 6,000.01, zero or a negative amount, **THEN** the contract must reject the
  request without changing balances.
- **AC-10 - Independent batches**: **GIVEN** two active notices, **WHEN** the customer
  lodges or funds another notice, **THEN** the contract must preserve each existing batch's
  amount and release date.
- **AC-11 - Cancellation**: **GIVEN** an unmatured NZD 4,000.00 batch, **WHEN** the
  customer cancels it, **THEN** the contract must return NZD 4,000.00 to `DEFAULT` with no
  penalty.
- **AC-12 - Matured cancellation**: **GIVEN** a batch at or after its due date, **WHEN** a
  cancellation is requested, **THEN** the contract must reject cancellation and process the
  maturity payout.

#### Accounting Entries

| Account Type | Internal Account Name | Balance Address | Dr/Cr | Amount | value_timestamp |
|---|---|---|---|---|---|
| Customer | N/A | DEFAULT | Dr | Notice amount | current_time |
| Customer | N/A | NOTICE_LOCKED | Cr | Notice amount | current_time |
| Customer | N/A | NOTICE_LOCKED | Dr | Cancelled notice amount | current_time |
| Customer | N/A | DEFAULT | Cr | Cancelled notice amount | current_time |

#### Notification Details

N/A - no customer notification type is specified in the brief.

### Feature 3: Notice maturity and disbursement

**User Story:**
> As a Notice Saver customer,  
> I want matured funds to be paid automatically to my nominated account,  
> so that I do not need to make a further withdrawal request.

#### Overview

Pay each matured batch to the nominated account at 00:02 Pacific/Auckland on its due date.
When monthly interest application also occurs on that date, it runs first at 00:01. A
maturity payout remains allowed when the account is dormant. Pay only the matured notice
principal; net interest previously credited to `DEFAULT` remains available in the account.

#### Build Approach

- **Approach**: Custom
- **Library module**: `feature_library.common.calendar_utils` may assist with date operations.
- **Custom code**: Per-batch maturity scheduling and nominated-account payout.
- **Library behaviour to note**: No supplied feature implements notice maturity payments.
- **Status**: verified against the bundled library catalogue

#### Parameters

| Parameter Name | Type | Level | Description | Default Value | Min Max Values |
|---|---|---|---|---|---|
| notice_period_days | integer | Account | Horizon for a notice batch | Account selection | 32 or 90 |
| nominated_account_id | string | Account | Payment destination | Required at opening | TBC pending validation/routing |

#### Calculation Formula

`maturity_due_date = lodge_date + 32 days` for 32-day accounts, or
`lodge_date + 90 days` for 90-day accounts. Pay at 00:02 local time on the due date.

#### Acceptance Criteria

- **AC-13 - 32-day maturity**: **GIVEN** a notice lodged on 2026-01-01 in a 32-day
  account, **WHEN** 2026-02-02 reaches 00:02 Pacific/Auckland, **THEN** the system must
  pay the batch to the nominated account.
- **AC-14 - 90-day maturity**: **GIVEN** a notice lodged on 2026-01-01 in a 90-day
  account, **WHEN** 2026-04-01 reaches 00:02 Pacific/Auckland, **THEN** the system must
  pay the batch to the nominated account.
- **AC-15 - Dormant maturity**: **GIVEN** a matured batch on a dormant account, **WHEN**
  its due-time event executes, **THEN** the system must make the maturity payout.
- **AC-16 - Distinct batches**: **GIVEN** batches with different due dates, **WHEN** one
  batch matures, **THEN** the system must pay only that batch's principal and leave all
  interest credited to `DEFAULT` available.

#### Accounting Entries

| Account Type | Internal Account Name | Balance Address | Dr/Cr | Amount | value_timestamp |
|---|---|---|---|---|---|
| Customer | N/A | NOTICE_LOCKED | Dr | Matured batch principal | current_time |
| External / Internal | Nominated-account settlement (TBC) | N/A | Cr | Matured batch principal | current_time |

#### Notification Details

N/A - no customer notification type is specified in the brief.

### Feature 4: Daily variable interest accrual

**User Story:**
> As a Notice Saver customer,  
> I want cleared available and notice-locked funds to earn the prevailing carded rate daily,  
> so that placing funds on notice does not stop their yield.

#### Overview

Accrue gross interest daily at 23:59:59 Pacific/Auckland over cleared credit funds in both
`DEFAULT` and `NOTICE_LOCKED`. Use the rate effective for that day and a fixed 365-day divisor
in both ordinary and leap years. Record accrual against the NZD customer account and the
configured interest-expense internal account.

#### Build Approach

- **Approach**: Mixed
- **Library module**: `feature_library.deposit.interest.interest_accrual`,
  `feature_library.deposit.interest.secondary.flat_interest`, and common accrual helpers.
- **Custom code**: Include the custom notice-locked address and retain interest attribution
  needed for a later break-fee cap.
- **Library behaviour to note**: The library `"actual"` day-count option uses 366 in leap
  years. Configure `"365"` to meet this brief's fixed-divisor requirement.
- **Status**: verified against the bundled library source

#### Parameters

| Parameter Name | Type | Level | Description | Default Value | Min Max Values |
|---|---|---|---|---|---|
| carded_variable_rate | decimal | Product | Effective annual rate for the selected variant | TBC | 0.0400–0.0410 or 0.0425–0.0460 |
| days_in_year_option | string | Product | Fixed day-count divisor | 365 | Fixed to 365 |
| accrual_precision | integer | Product | Decimal places for daily accrual | 5 (assumption A-03) | NZD accounting precision |
| interest_accrual_time | time | Product | Local daily accrual time | 23:59:59 | Fixed |
| accrued_interest_payable_account | string | Product | Internal liability/accrual account | TBC | Required |
| interest_expense_account | string | Product | Internal interest expense account | TBC | Required |

#### Calculation Formula

`daily_rate = ROUND_HALF_UP(annual_rate / 365, 10)`

`daily_gross_interest = ROUND_HALF_UP((cleared_available + cleared_notice_locked) * daily_rate, 5)`

Where balances are NZD credit balances effective for the accrual date. Daily accrual is
recorded at the end of that date.

Worked example: NZD 50,000.00 at 4.00% p.a. gives a daily rate of 0.0001095890 and daily
gross accrual of NZD 5.47945. Five days accrue NZD 27.39725 before application rounding.

#### Acceptance Criteria

- **AC-17 - Combined balances**: **GIVEN** NZD 40,000.00 available and NZD 10,000.00
  locked at 4.00%, **WHEN** daily accrual executes, **THEN** the contract must accrue
  NZD 5.47945 using the fixed 365 divisor.
- **AC-18 - Fixed leap-year divisor**: **GIVEN** NZD 50,000.00 at 4.00% on 2024-02-29,
  **WHEN** daily accrual executes, **THEN** the contract must accrue NZD 5.47945, not use
  a 366-day divisor.
- **AC-19 - Zero balance**: **GIVEN** zero cleared credit balance, **WHEN** daily accrual
  executes, **THEN** the contract must create no interest posting.
- **AC-20 - Rate change**: **GIVEN** an effective-dated rate change, **WHEN** daily
  accrual runs, **THEN** the contract must use the rate effective on that accrual date.

#### Accounting Entries

| Account Type | Internal Account Name | Balance Address | Dr/Cr | Amount | value_timestamp |
|---|---|---|---|---|---|
| Internal | Interest expense account (TBC) | N/A | Dr | Daily gross interest | end of accrual date |
| Customer | N/A | ACCRUED_INTEREST_PAYABLE | Cr | Daily gross interest | end of accrual date |

#### Notification Details

N/A - no customer notification type is specified in the brief.

### Feature 5: Monthly PIE tax and interest application

**User Story:**
> As a Notice Saver customer,  
> I want accrued interest taxed at my PIR and net interest credited monthly,  
> so that my account compounds the correct after-tax amount.

#### Overview

At 00:01 Pacific/Auckland on the first day of each month, apply the previous month's gross
accrued interest after the preceding day's accrual. Calculate PIE tax using the customer's
PIR, remit the tax to the configured IRD payable/settlement accounts, and credit net
interest to available funds. Interest credited on the first day compounds from that day.
On account closure, calculate and tax the mid-cycle accrual and pay the net amount with the
remaining balance.

#### Build Approach

- **Approach**: Mixed
- **Library module**: `feature_library.deposit.interest.interest_application` can apply
  accrued interest.
- **Custom code**: Calculate and post the PIE tax split, remittance liability and closure
  mid-cycle tax treatment.
- **Library behaviour to note**: The library interest-application feature does not implement
  this product's PIR withholding.
- **Status**: verified against the bundled library source

#### Parameters

| Parameter Name | Type | Level | Description | Default Value | Min Max Values |
|---|---|---|---|---|---|
| pir_tax_rate | decimal | Account | PIE prescribed investor rate | TBC at opening | 0, 0.105, 0.175, 0.28 |
| application_precision | integer | Product | Decimal places for net interest and tax | 2 (assumption A-03) | NZD cents |
| interest_application_time | time | Product | Monthly application time | 00:01 | Fixed |
| accrued_interest_payable_account | string | Product | Accrued gross interest account | TBC | Required |
| pie_tax_payable_account | string | Product | Tax withheld pending IRD remittance | TBC | Required |
| interest_expense_account | string | Product | Interest expense account | TBC | Required |

#### Calculation Formula

`gross_monthly_interest = sum(daily_gross_interest for the month)`

`pie_tax_withheld = ROUND_HALF_UP(gross_monthly_interest * pir_tax_rate, 2)`

`net_interest = ROUND_HALF_UP(gross_monthly_interest, 2) - pie_tax_withheld`

Worked example: five days on NZD 50,000.00 at 4.00% accrue NZD 27.39725, rounded to
NZD 27.40. At a 28% PIR, tax is NZD 7.67 and net interest is NZD 19.73.

#### Acceptance Criteria

- **AC-21 - Monthly tax**: **GIVEN** NZD 27.40 gross interest and a 28% PIR, **WHEN**
  monthly application executes, **THEN** the system must withhold NZD 7.67 and credit
  NZD 19.73 net interest.
- **AC-22 - Zero PIR**: **GIVEN** NZD 27.40 gross interest and a 0% PIR, **WHEN**
  monthly application executes, **THEN** the system must withhold NZD 0.00 and credit
  NZD 27.40.
- **AC-23 - Leap month**: **GIVEN** daily accruals during February 2024, **WHEN** the
  month-end application executes, **THEN** the system must include the 29 February accrual
  and use the fixed 365 divisor for every day.
- **AC-24 - Closure application**: **GIVEN** positive mid-cycle gross accrued interest,
  **WHEN** the customer closes the account, **THEN** the system must calculate PIR tax and
  pay only net interest with the remaining balance.

#### Accounting Entries

| Account Type | Internal Account Name | Balance Address | Dr/Cr | Amount | value_timestamp |
|---|---|---|---|---|---|
| Customer | N/A | ACCRUED_INTEREST_PAYABLE | Dr | Gross monthly interest | current_time |
| Customer | N/A | DEFAULT | Cr | Net monthly interest | current_time |
| Internal | PIE tax payable account (TBC) | N/A | Cr | PIE tax withheld | current_time |
| Internal | PIE tax payable account (TBC) | N/A | Dr | Tax remitted | current_time |
| External / Internal | IRD settlement account (TBC) | N/A | Cr | Tax remitted | current_time |

#### Notification Details

N/A - no customer notification type is specified in the brief.

### Feature 6: Emergency break and hardship waiver

**User Story:**
> As a Notice Saver customer with an urgent need,  
> I want an authorised immediate break with principal protection,  
> so that an early withdrawal never consumes my principal.

#### Overview

Allow an authorised emergency break of a partial or full notice-locked principal amount.
Calculate the fee from the principal broken, the applicable current carded rate and the
account's 32- or 90-day notice period. Cap the fee at net interest attributable to that
principal after PIE tax. An approved hardship, terminal-illness or bereavement flag waives
the fee. The released amount is paid to the nominated account.

#### Build Approach

- **Approach**: Custom
- **Library module**: `feature_library.deposit.fees.withdrawal.early_withdrawal_fees` offers
  configurable flat/percentage withdrawal fees and related helpers.
- **Custom code**: Calculate a term-based fee, associate net accrued interest with broken
  principal, ensure principal protection, and apply the hardship waiver.
- **Library behaviour to note**: The library fee feature does not implement the stated
  lesser-of formula or its tax-aware cap.
- **Status**: verified against the bundled library source

#### Parameters

| Parameter Name | Type | Level | Description | Default Value | Min Max Values |
|---|---|---|---|---|---|
| carded_variable_rate | decimal | Product | Current effective annual rate | TBC | Variant range in Feature 1 |
| notice_period_days | integer | Account | Fee term | Account selection | 32 or 90 |
| pir_tax_rate | decimal | Account | Rate used for interest net of PIE tax | Account selection | 0, 0.105, 0.175, 0.28 |
| hardship_approved | flag | Account | Approved exception to the fee | false | true only after external approval |

#### Calculation Formula

`calculated_charge = principal_broken * annual_rate * notice_period_days / 365`

`break_fee = min(ROUND_HALF_UP(calculated_charge, 2), net_interest_attributable_to_broken_principal)`

`net_interest_attributable = gross_attributable_interest - PIE_tax_attributable`

If `hardship_approved` is true, `break_fee = 0`.

Worked example: NZD 50,000.00 at 4.00% for a 32-day notice gives a calculated charge of
NZD 175.34. After five days, gross interest is NZD 27.40. At 0% PIR the fee is capped at
NZD 27.40; at 28% PIR, net interest is NZD 19.73 and the fee is capped at NZD 19.73.
Neither case may reduce the NZD 50,000.00 principal.

#### Acceptance Criteria

- **AC-25 - Full charge**: **GIVEN** NZD 50,000.00 broken at 4.00% after 60 days with
  sufficient net attributable interest, **WHEN** the 32-day break is processed, **THEN**
  the fee must be NZD 175.34.
- **AC-26 - Principal-protection cap**: **GIVEN** NZD 50,000.00 broken at 4.00% after
  five days and a 28% PIR, **WHEN** the 32-day break is processed, **THEN** the fee must
  not exceed NZD 19.73 and the returned principal must remain NZD 50,000.00.
- **AC-27 - Hardship waiver**: **GIVEN** an externally approved hardship flag, **WHEN** an
  emergency break is processed, **THEN** the contract must charge NZD 0.00.
- **AC-28 - Unauthorised break**: **GIVEN** no valid authorisation or insufficient locked
  principal, **WHEN** a break is requested, **THEN** the contract must reject it without
  debiting principal.

#### Accounting Entries

| Account Type | Internal Account Name | Balance Address | Dr/Cr | Amount | value_timestamp |
|---|---|---|---|---|---|
| Customer | N/A | NOTICE_LOCKED | Dr | Principal broken | current_time |
| External / Internal | Nominated-account settlement (TBC) | N/A | Cr | Full principal broken | current_time |
| Customer | N/A | Accrued / available net interest | Dr | Break fee, never more than net attributable interest | current_time |
| Internal | Break-fee income account (TBC) | N/A | Cr | Break fee | current_time |

#### Notification Details

N/A - the brief specifies no outbound notification. The operation must retain an audit
record of the fee and any waiver.

### Feature 7: Dormancy and account closure

**User Story:**
> As a Notice Saver customer,  
> I want dormancy safeguards and a clear closure path,  
> so that my funds remain protected and can be paid out under the product rules.

#### Overview

An external monitor applies a dormancy flag after three or more years without customer-led
transactions. Dormancy blocks customer-initiated debits and new notice lodgements, but
permits inbound transfers, daily accrual, scheduled maturity payouts and closure sweeps.
The customer may close at any time. Closing breaks still-locked notices under Feature 6,
taxes any mid-cycle accrued interest at the account PIR and pays the remaining balance to
the nominated account.

#### Build Approach

- **Approach**: Mixed
- **Library module**: `feature_library.deposit.dormancy.dormancy` checks configured Vault
  flags in the posting hook.
- **Custom code**: Respect the required credit and scheduled-payout exceptions, invoke the
  external dormancy monitor contract, and perform closure/mid-cycle settlement.
- **Library behaviour to note**: The library checks a flag; it does not calculate inactivity
  or set/clear the flag. Its generic rejection must not block permitted credits or scheduled
  maturity and closure exceptions.
- **Status**: verified against the bundled library source

#### Parameters

| Parameter Name | Type | Level | Description | Default Value | Min Max Values |
|---|---|---|---|---|---|
| dormancy_flag | flag | Account | External monitor's dormancy state | false | Set after 3 or more years without customer-initiated transactions |
| hardship_approved | flag | Account | Approved fee-waiver status | false | Externally approved |
| pir_tax_rate | decimal | Account | PIE rate applied at closure | Account selection | 0, 0.105, 0.175, 0.28 |
| nominated_account_id | string | Account | Closure sweep destination | Account selection | Required |

#### Calculation Formula

`closure_net_interest = round_to_cents(mid_cycle_gross_interest - PIE_tax_withheld)`

`closure_payout = remaining principal + net interest credited or accrued - break_fees`

Apply Feature 6's fee only to locked principal being broken, and do not debit customer
principal for fees. Collect any fee from available net interest attributable to the broken
principal; the principal payout remains intact.

#### Acceptance Criteria

- **AC-29 - Dormancy restrictions**: **GIVEN** an account with the dormancy flag,
  **WHEN** a customer requests a new notice or customer-led debit, **THEN** the contract
  must reject it.
- **AC-30 - Dormant credits and scheduled events**: **GIVEN** a dormant account, **WHEN**
  an allowed inbound credit, daily accrual, maturity payout or closure sweep occurs,
  **THEN** the system must process it.
- **AC-31 - Closure with notices**: **GIVEN** an account with available and notice-locked
  funds, **WHEN** the customer closes it, **THEN** the system must break locked funds under
  Feature 6 and sweep remaining principal and net accrued interest to the nominated account.
- **AC-32 - Closure tax**: **GIVEN** NZD 27.40 gross mid-cycle interest and a 28% PIR,
  **WHEN** the account closes, **THEN** the system must withhold NZD 7.67 and include
  NZD 19.73 net interest in the payout.
- **AC-33 - Dormancy boundary**: **GIVEN** the external monitor reports fewer than three
  years without customer activity, **WHEN** it evaluates the account, **THEN** it must not
  apply the dormancy flag.

#### Accounting Entries

| Account Type | Internal Account Name | Balance Address | Dr/Cr | Amount | value_timestamp |
|---|---|---|---|---|---|
| Customer | N/A | DEFAULT / NOTICE_LOCKED | Dr | Remaining principal and accrued balance | current_time |
| Customer | N/A | DEFAULT | Cr | Net mid-cycle interest | current_time |
| Internal | PIE tax payable account (TBC) | N/A | Cr | Tax withheld | current_time |
| External / Internal | Nominated-account settlement (TBC) | N/A | Cr | Closure payout net of fees and tax | current_time |

#### Notification Details

N/A - no customer notification type is specified in the brief.

## Schedules Summary

| Event Type | Schedule (Time / Cadence) | Offset | Purpose |
|---|---|---|---|
| INTEREST_ACCRUAL | Daily at 23:59:59 Pacific/Auckland | Month-end accrual precedes application by at least 1 minute | Accrue interest through the end of each calendar date |
| INTEREST_APPLICATION | 00:01 Pacific/Auckland on day 1 of each month | 1 minute before a coincident 00:02 maturity payout | Calculate PIE tax and credit net monthly interest |
| NOTICE_MATURITY_DISBURSEMENT | Each batch due date at 00:02 Pacific/Auckland | 1 minute after a coincident monthly application | Pay the matured batch to the nominated account |

## Out of scope

- Contract-level enforcement of the NZD 5,000,000 aggregate portfolio cap; the upstream
  coordinator owns that control.
- Customer identity, eligibility, nominated-account ownership and domestic payment-rail
  validation; the onboarding/payment systems own these checks.
- Treasury's rate-setting and approval workflow; the contract consumes an effective-dated
  rate.
- Operation of the dormancy monitor and approval of hardship cases; external systems set
  the relevant flags.
- Legal determination of PIE tax treatment, DCS eligibility and regulatory reporting.
- Product statements, notifications and maturity rollover; the brief does not specify them.

## Clarification log

| ID | Question | Answer | Feeds |
|---|---|---|---|
| Q1 | Which Vault Core version does the product target? | 5.9 | D-03 |
| Q2 | Is the NZD 5,000,000 limit aggregate or per account, and where is it enforced? | Aggregate across accounts; Q6 clarified that an upstream coordinator enforces it, not the account contract. | D-04 |
| Q3 | What are the exact opening 32-day and 90-day carded rates? | TBC; the brief's ranges remain the permitted bounds. | D-05 and open item |
| Q4 | Does the lodgement date count, and when does maturity payout occur? | Lodgement date is day 0; initially selected 00:01. Q12 moves payout to 00:02 to avoid a schedule collision. | D-07, D-12 |
| Q5 | Which interest pool caps an emergency-break fee? | Net interest attributable to the broken principal, after tax confirmed in Q10. | D-08 |
| Q6 | Where is the cross-account cap enforced? | By an upstream coordinator. | D-04 |
| Q7 | How does closure treat active notice batches? | Close immediately; break each locked amount and apply the fee unless waived. | D-09 |
| Q8 | Who applies dormancy? | An external monitor applies a flag after three years without customer-initiated transactions. | D-10 |
| Q9 | How should month-end accrual and application be offset? | Accrue at 23:59:59; apply at 00:01 on the following month's first day. | D-12 |
| Q10 | Is the break-fee cap gross or net of PIE tax? | Net interest after PIE tax. | D-08 |
| Q11 | Do dormancy debit restrictions block maturity and closure payouts? | No; allow automatic maturity payouts and closure sweeps. | D-11 |
| Q12 | How should a maturity payout avoid a 00:01 monthly-application collision? | Apply interest at 00:01 and pay maturity at 00:02; Q13 clarified that the payout remains principal-only. | D-07, D-12 |
| Q13 | Does maturity include interest attributable to that batch? | Pay only matured principal; net monthly interest remains in `DEFAULT`. | D-07 |

## Implementation notes

- The CLV4 recipe contract should keep each feature separate and wire shared requirements
  through its metadata. Use `DEFAULT` for available funds and a product-specific address for
  notice-locked principal.
- Maintain per-batch amount, lodge date, due date and interest attribution. Multiple batches
  must remain independent.
- The feature library's `"actual"` day-count means 365 or 366 based on the year. Use its
  explicit `"365"` option for this product.
- Record daily accrued interest to five decimal places, using a ten-decimal daily rate;
  apply NZD amounts and PIE tax to two decimal places with half-up rounding, subject to
  A-03 confirmation.
- Track the after-tax interest attributable to each notice batch so a break fee cannot
  consume principal. Monthly tax application and closure must keep this attribution
  consistent.
- Wire dormancy checks selectively: permitted inbound credits and the scheduled maturity
  and closure exceptions must not be rejected by a generic dormancy hook.
- Do not claim the upstream portfolio cap, rate governance, hardship approval, dormancy
  monitoring, account validation or tax remittance is implemented by the account contract.
- The implementation plan and CLU pack must list the required account IDs, flag IDs,
  transaction-code mappings and upstream integration owners before deployment.

## Change log

| Version | Date | Author/Reviewer | Comment |
|---|---|---|---|
| 1 | 2026-10-22 | Copilot | Initial requirements from KB-PRD-NS-2026-V2 and answers Q1–Q13. |
