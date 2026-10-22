# Notice Saver — Implementation Plan

Source: `src/notice_saver/documentation/REQUIREMENTS.md` v1,
`src/notice_saver/documentation/TEST_PLAN.md` v1. Target: Vault 5.9 (source: requirements),
Contracts API 4; installed contracts-api 0.0.0+latest, feature_library 1.0.0 (bundled source).
Generated 2026-10-22.

## Overview

Notice Saver is an NZD deposit account with liability t-side. The contract will use the
feature library for denomination validation, effective-dated interest-rate retrieval,
daily accrual calculation and schedule helpers. Notice batches, channel policy, monthly PIE
tax allocation, break-fee attribution, maturity payments and closure settlement require
product-specific code.

The implementation order follows the requirements: establish contract metadata and account
validation first; add batch locking and cancellation before maturity processing; then add
interest accrual and its monthly tax treatment; finally add breaks, dormancy exceptions and
closure. The upstream portfolio-cap coordinator and external dormancy monitor are not in this
repository and will remain explicit integration dependencies.

## Foundation

The first feature establishes CLV4 contract metadata for Vault 5.9, `Tside.LIABILITY`, the
NZD denomination and Pacific/Auckland event timezone. Account parameters cover the 32- or
90-day term, nominated account and permitted PIR. Product parameters cover the effective-dated
carded rates, schedule times, rounding and required internal account IDs. Deployment values
that are TBC in the requirements remain TBC.

Use effective-dated parameter fetchers and an unfiltered `BalancesObservationFetcher` for
custom batch addresses. In Vault 5.9, `BalanceCoordinate.account_address` identifies a
balance and `BalancesObservationFetcher.filter` is optional; paired custom balance addresses
can therefore hold durable, zero-net attribution state without adding to spendable `DEFAULT`.
Hook data requirements will be declared with `@fetch_account_data`. Daily accrual, monthly
application and maturity use separate event types at 23:59:59, 00:01 and 00:02 respectively,
in the account operating timezone.

## Features

### Feature 1: Account setup, deposit channels and aggregate limit
**Covers**: AC-01–AC-05, AC-34, D-01–D-05 · **Scenarios**: F1-01–F1-04, X-01, X-03 ·
**Build approach**: Mixed · **Depends on**: Foundation · **Status**: Implemented and unit
validated (2026-10-22; six test methods and 21 subtests pass; compile, render, mypy,
formatting, prohibited-construct scan and workspace smoke test pass). Simulation, CLU
validation and E2E remain blocked by missing CLU, unresolved deployment mappings and
unreachable Vault Core.

The contract validates NZD using `feature_library.common.denomination.validate_denomination`.
Activation requires a supported term, nominated-account reference and PIR. Pre-posting
validation permits only positive NZD inbound hard settlements or transfers with an explicit
test channel label. Channel identifiers remain deployment mappings; no unverified production
codes are embedded. Unit tests cover all supported term/PIR combinations, invalid setup,
permitted channels, prohibited instruction types and pre-posting hook decisions.

The per-account `maximum_balance_limit` feature is deliberately not used for the
NZD 5,000,000 portfolio cap: it only evaluates one account's balance and proposed postings.
The upstream coordinator owns atomic cross-account enforcement. Inbound credits do not alter
existing notice batches. Backdated and future-dated requests receive no additional product
date rejection beyond Vault Core processing.

**Decisions**: I-01 — enforce the portfolio cap only in the upstream coordinator (source:
user); I-02 — use NZD and the specified account-level term/PIR values without deployment
defaults (source: user); I-16 — keep required account parameters optional in the schema with
no business default, and reject missing values in activation (source: Vault docs); I-17 — use
the `notice_saver_channel` instruction detail with explicit test channel labels, accepting
only inbound hard settlements or positive-credit transfers (source: proposed default).

### Feature 2: Notice lodgement and cancellation
**Covers**: AC-06–AC-12, D-07, A-01, A-04, A-06 · **Scenarios**: F1-04, F2-01–F2-03,
F3-01, X-02 · **Build approach**: Custom · **Depends on**: Feature 1 · **Status**: Planned

Use `feature_library.common.balance_utils.get_available_balance` and
`feature_library.common.posting_utils.create_postings` for cleared-balance checks and balanced
address movements. Custom posting logic will lock each request in a `NOTICE_LOCKED_<batch-id>`
address and calculate its due date from the local lodgement date plus the account term.
Cancellation identifies the batch, rejects requests on or after its due date, and returns
only that batch's remaining principal to `DEFAULT`.

The batch ID and action will be supplied in the agreed posting interface. Paired, zero-net
custom balance addresses will retain batch gross-interest, net-interest and fee-attribution
state; a full balances observation permits enumeration at later hooks. This state is needed
because no library feature models independently cancellable batches or their separate release
dates.

**Decisions**: I-03 — use persistent, paired custom balance addresses keyed by a required
batch ID, with due-date data retained for scheduling and settlement (source: Vault docs and
proposed default); I-04 — use Pacific/Auckland calendar dates, with lodgement day zero and no
weekend/holiday shift (source: user).

### Feature 3: Notice maturity and disbursement
**Covers**: AC-13–AC-16, D-07, D-11, D-12 · **Scenarios**: F3-01–F3-02, F7-01, X-02 ·
**Build approach**: Custom · **Depends on**: Feature 2 · **Status**: Planned

A daily `NOTICE_MATURITY_DISBURSEMENT` event at 00:02 Pacific/Auckland will inspect the
batch addresses and settle only batches whose due date has arrived. Use an
`OutboundHardSettlement` to the configured nominated account and settlement account; remove
the matured principal and its no-longer-needed attribution state. Net interest already
credited to `DEFAULT` remains there. The maturity event is independent of customer-debit
dormancy restrictions.

The daily scan avoids creating a new Vault schedule for every customer request and supports
multiple due dates on one account. A coincident monthly application is scheduled at 00:01,
so it precedes the 00:02 payout.

**Decisions**: I-05 — use a daily maturity sweep over active batch addresses rather than a
per-batch schedule (source: proposed default); I-06 — pay principal only, including on dormant
accounts (source: user).

### Feature 4: Daily variable interest accrual
**Covers**: AC-17–AC-20, D-05–D-06, A-02–A-03, S-01 · **Scenarios**: F4-01–F4-03,
F5-02 · **Build approach**: Mixed · **Depends on**: Features 1–2 · **Status**: Planned

Use `feature_library.deposit.interest.interest_accrual.get_scheduled_events` and
`schedule_logic` for the 23:59:59 event. Use
`feature_library.deposit.interest.secondary.flat_interest.get_interest_rate` with an
effective-dated carded-rate parameter, then
`get_fixed_interest_accrual_amount` for the configured 10-decimal daily rate and 5-decimal
daily gross accrual. Configure `days_in_year_option` as `"365"`; the library's `"actual"`
option uses 366 in leap years. Custom logic will attribute daily gross interest to the
available pool or the active notice batch without changing the earning balance.

**Decisions**: I-07 — use the effective-dated carded rate for each accrual date (source:
user); I-08 — use a fixed 365-day divisor and the documented rounding assumptions (source:
user and requirements).

### Feature 5: Monthly PIE tax and interest application
**Covers**: AC-21–AC-24, D-06, D-09, D-12, A-03–A-04, S-02 · **Scenarios**: F5-01–F5-03,
F3-02, F7-03, X-02 · **Build approach**: Mixed · **Depends on**: Feature 4 · **Status**:
Planned

Use `feature_library.deposit.interest.interest_application.get_scheduled_events` to define
the first-of-month 00:01 event; custom application logic will total gross accrual, calculate
PIE tax at the account PIR to cents, post tax to the configured payable account and credit
net interest to `DEFAULT`. The custom logic is required because the library application
feature does not implement PIE withholding. Closure will invoke the same tax calculation for
mid-cycle accrued interest before settlement.

For batch attribution, calculate tax once on the account-wide monthly gross amount, then
apportion cents across the available and notice buckets by largest remainder. Track fee
amounts charged against each batch. If final tax allocation shows a prior provisional break
fee exceeded that batch's finalized after-tax interest, reverse the excess from fee income
and refund it to `DEFAULT`. This preserves the account-level tax formula while keeping the
break-fee cap auditable.

**Decisions**: I-09 — tax is computed on aggregate account interest and allocated by largest
remainder for attribution (source: user for aggregate taxation; proposed default for
allocation); I-10 — reconcile and refund any provisional overcharge when tax allocation is
finalized (source: user, Q14).

### Feature 6: Emergency break and hardship waiver
**Covers**: AC-25–AC-28, D-08, A-03, A-07 · **Scenarios**: F6-01–F6-03, F7-03 ·
**Build approach**: Custom · **Depends on**: Features 2, 4 and 5 · **Status**: Planned

Custom break handling will validate the action and batch amount, read the current carded rate,
and calculate the term-based fee. It will cap the fee at the batch's available net-interest
attribution and honour the externally controlled hardship flag. Settle full principal
independently of the fee and take the fee only from attributable interest; never debit notice
principal for the fee. The library's flat/percentage withdrawal-fee feature does not implement
the required formula or tax-aware cap.

**Decisions**: I-11 — use the current effective carded rate and cap the fee after PIE tax
(source: user); I-12 — allow an approved hardship flag to waive the fee (source: user).

### Feature 7: Dormancy and account closure
**Covers**: AC-29–AC-33, D-09–D-11, A-05, A-08 · **Scenarios**: F7-01–F7-03, F3-02,
F5-03 · **Build approach**: Mixed · **Depends on**: Features 3, 5 and 6 · **Status**: Planned

Use `feature_library.deposit.dormancy.dormancy.is_account_dormant` to read the externally
set flag, but do not call its generic `validate_account_transaction` as a blanket rejection:
that would also block permitted inbound credits. Custom posting validation will reject
customer-led debits and new notices only, while scheduled maturity and closure payouts remain
allowed. The external monitor that measures three years of inactivity and sets or clears the
flag is outside this contract.

Closure settlement will break each active batch under Feature 6, finalize mid-cycle PIE tax
under Feature 5, and sweep remaining principal and net interest to the nominated account.
Vault 5.9 provides a `deactivation_hook`; its permitted posting directives and ordering will
be verified against the hook reference before implementing the close path.

**Decisions**: I-13 — the external monitor owns the three-year dormancy trigger (source:
user); I-14 — dormancy allows inbound credits, scheduled maturity and closure sweeps (source:
user); I-15 — closure breaks locked amounts immediately under the same fee/waiver rules
(source: user).

## Traceability

| Requirement | Feature |
|---|---|
| AC-01–AC-05, AC-34 | Feature 1 |
| AC-06–AC-12 | Features 1–2 |
| AC-13–AC-16 | Feature 3 |
| AC-17–AC-20 | Feature 4 |
| AC-21–AC-24 | Feature 5 |
| AC-25–AC-28 | Feature 6 |
| AC-29–AC-33 | Feature 7 |
| D-01, D-02, D-04 | Feature 1 |
| D-03 | Foundation |
| D-05 | Features 1, 4 |
| D-06 | Features 4, 5 |
| D-07 | Features 2, 3 |
| D-08 | Feature 6 |
| D-09 | Features 5, 7 |
| D-10 | Feature 7 (external monitor) |
| D-11 | Features 3, 7 |
| D-12 | Features 3, 5 |
| A-01, A-04, A-06 | Feature 2 |
| A-02, A-03 | Features 4–6 |
| A-05, A-08 | Features 1, 7 |
| A-07 | Feature 6 |
| A-09 | Feature 1 |
| S-01: daily accrual at 23:59:59 | Feature 4 |
| S-02: monthly application at 00:01 | Feature 5 |
| S-03: maturity payout at 00:02 | Feature 3 |
| Lifecycle 1: opening | Feature 1 |
| Lifecycle 2: available funds | Features 1–2 |
| Lifecycle 3: notice locked and cancellation | Feature 2 |
| Lifecycle 4: maturity and payout | Feature 3 |
| Lifecycle 5: emergency break | Feature 6 |
| Lifecycle 6: dormant account | Feature 7 |
| Lifecycle 7: closure and final settlement | Features 5, 7 |

Uncovered: Atomic aggregate-cap enforcement, three-year inactivity detection, production
payment-rail behavior, nominated-account ownership checks, legal PIE/DCS determinations and
production GL mappings belong to external systems or owners. The coordinator and dormancy
monitor are absent from this repository; their behavior requires tests in their owning
projects and integration validation.

## Open questions

- **Q14 (Technical, Blocking) — Resolved at implementation plan**: How will per-batch
  interest attribution remain correct across monthly application, tax withholding,
  cancellation, break and maturity? **Answer**: use paired, zero-net batch attribution
  balances; calculate monthly tax on account-wide gross interest; apportion tax by largest
  remainder; reconcile and refund a break-fee overcharge after final tax allocation. *Source*:
  user and proposed default.
- **Q15 (Configuration, Blocking for deployment)**: What are the exact initial 32-day and
  90-day carded rates within the approved ranges? *Default*: keep both TBC. *Close at*:
  product configuration.
- **Q16 (Configuration, Blocking for deployment)**: Which internal account IDs and GL
  mappings apply to accrued interest, tax, break-fee income and settlements? *Default*: keep
  all IDs TBC. *Close at*: CLU configuration.
- **Q17 (Technical, Blocking for deployment)**: Which transaction codes, instruction details
  and payment-rail mappings represent permitted credits, notices, cancellations, breaks,
  maturity and closure? *Default*: use explicit test mappings only. *Close at*: integration
  design and CLU validation.
- **Q18 (Technical, Blocking for deployment)**: Which upstream coordinator atomically
  enforces the NZD 5,000,000 aggregate cap? *Default*: no account-contract enforcement.
  *Close at*: coordinator integration.
- **Q19 (Technical, Blocking for deployment)**: Which dormancy monitor, activity definition,
  flag ID and clearing process apply? *Default*: the external monitor sets the configured
  flag; the contract does not infer inactivity. *Close at*: operations integration.
- **Q20 (Product, Blocking for deployment)**: Which authority and process approve hardship
  waivers and set the flag? *Default*: only an externally approved flag waives the fee.
  *Close at*: operations and compliance sign-off.
- **Q21 (Product, Blocking for deployment)**: How are nominated-account ownership and
  domestic settlement behavior validated? *Default*: onboarding and payment systems own
  validation; the contract consumes the configured reference. *Close at*: integration
  design.
- **Q22 (Product, Non-blocking for implementation)**: Are the rounding precision and
  Pacific/Auckland local-time assumptions approved for production? *Default*: retain A-03
  and A-04. *Close at*: product sign-off.
- **Q23 (Compliance, Blocking for production)**: Are PIE tax, DCS eligibility and statutory
  reporting treatments legally approved? *Default*: no legal determination is made by this
  contract. *Close at*: legal and compliance sign-off.
- **Q24 (Configuration, Non-blocking for implementation)**: What is Treasury's approval and
  publication process for effective-dated rate updates? *Default*: consume the rate effective
  at each accrual/break time. *Close at*: treasury operating-model design.

## Change log

| Version | Date | Author/Reviewer | Comment |
|---|---|---|---|
| 1 | 2026-10-22 | Copilot | Initial plan for seven features; records Q14 resolution, 15 implementation decisions and 10 open deployment questions. |
| 2 | 2026-10-22 | Copilot | Implemented Feature 1; added decisions I-16 and I-17 and recorded static-check results. |
| 3 | 2026-10-22 | Copilot | Added and passed Feature 1 unit tests; recorded simulator, CLU and E2E blockers. |
