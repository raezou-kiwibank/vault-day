# Notice Saver — Test Plan

Source: `src/notice_saver/documentation/REQUIREMENTS.md`, 12 decisions, 9 assumptions, 34 acceptance criteria. Generated 2026-10-22.

## 1. Testing scope

### 1.1 In scope

Test product setup and channel validation, notice-batch locking/cancellation/maturity,
daily interest accrual, monthly PIE tax application, emergency breaks, hardship waivers,
dormancy behavior, closure, CLV4 contract metadata and scheduled-event ordering. Use the
Inception SDK unit and simulation frameworks. Simulation supports event sequences over
explicit timestamps, schedules, flags, parameter values and expected contract/account
violations. Parameter updates can be represented in simulation events; schedule expectations
can be checked at explicit times.

Every scenario has a unit test. Simulate each contract behavior that Vault's simulator can
exercise. Scenarios for the upstream portfolio coordinator and external dormancy monitor
need unit tests in those owning components, which are not present in this workspace.
Recommended E2E journeys require a reachable, authorised Vault sandbox.

### 1.2 Not tested (Out of scope)

- Internal behavior of feature-library modules; test only that the product wires them
  correctly.
- Correctness or availability of the external aggregate-cap coordinator, dormant-account
  monitor, treasury rate governance, account onboarding, hardship approval or payment rails.
- Legal determinations for PIE/DCS treatment or production GL mappings.
- Live Core API integration until the sandbox is reachable and CLU configuration is ready.
- The requirement's deployment-only values (internal account IDs, flag IDs, exact opening
  rates, channel codes); use explicit test values without treating them as production
  defaults.
- E2E account cleanup; Vault E2E runs create persistent accounts and must run only in an
  approved sandbox.

---

## 2. Scenarios — Feature 1: Account setup, deposit channels and aggregate limit

**Types and priorities guide:**
- **Types**:
  - `core`: nominal path under normal operating conditions.
  - `edge`: single-variable boundary limit, threshold, or extreme value.
  - `corner`: multi-variable interaction, simultaneous events, or schedule/state collision.
- **Priorities**:
  - `must`: explicit requirement or core balance invariant; release blocker.
  - `should`: boundary limits, operational assumptions or wiring robustness.
  - `could`: lower-priority corner case or planner-added combination.

### F1-01 — Opening validation and zero funding
- **Origin**: AC-01, AC-02, AC-03, D-01, D-02, D-03 | **Priority**: must | **Tag**: [custom]
- **Levels**: Unit: yes, Simulation: yes, E2E: no
- **Steps**: Open valid 32-day and 90-day accounts with NZD 0.00, a nominated-account
  reference and each permitted PIR. Then try an unsupported horizon, missing nominated
  account, unsupported PIR and non-NZD denomination.
- **Expected Outcome**: Valid setup is accepted with the selected horizon and PIR; every
  invalid or missing required value is rejected; zero initial funding is accepted.

### F1-02 — Currency and permitted transaction channels
- **Origin**: AC-04, D-02, A-05 | **Priority**: must | **Tag**: [custom]
- **Levels**: Unit: yes, Simulation: yes, E2E: no
- **Steps**: Submit NZD direct credit, internal transfer and recurring-savings credits.
  Submit non-NZD credit and debit/ATM, cheque, direct-debit-authority and EFTPOS merchant
  debits.
- **Expected Outcome**: Permitted NZD credits are accepted; unsupported denominations and
  prohibited debit channels are rejected without balance changes.

### F1-03 — Upstream aggregate cap and atomic batch netting
- **Origin**: AC-05, D-04 | **Priority**: must | **Tag**: [custom]
- **Levels**: Unit: yes (upstream coordinator repository), Simulation: no, E2E: yes
- **Steps**: In the coordinator's unit suite, start with aggregate NZD 4,999,999.99. Verify
  one NZD 0.01 posting is accepted. Submit a batch with two NZD 0.01 credits to different
  accounts and verify the full batch is rejected. Add a concurrent-deposit case.
- **Expected Outcome**: Exact NZD 5,000,000.00 is allowed; a combined total of
  NZD 5,000,000.01 is rejected atomically. The product contract alone cannot prove this
  integration; the coordinator component and a post-deployment E2E are required.

### F1-04 — Top-up does not reset an active notice
- **Origin**: AC-06, A-06 | **Priority**: must | **Tag**: [custom]
- **Levels**: Unit: yes, Simulation: yes, E2E: no
- **Steps**: Create a notice for NZD 4,000.00, record its release date, then accept an
  additional NZD 500.00 deposit.
- **Expected Outcome**: The existing batch remains NZD 4,000.00 with its original release
  date; the top-up is available separately.

---

## 3. Scenarios — Feature 2: Notice lodgement and cancellation

### F2-01 — Partial, full and invalid notice amounts
- **Origin**: AC-07, AC-08, AC-09 | **Priority**: must | **Tag**: [custom]
- **Levels**: Unit: yes, Simulation: yes, E2E: no
- **Steps**: With NZD 10,000.00 available, lodge NZD 4,000.00 and then a separate
  NZD 10,000.00 full-balance notice in an independent test. Also try NZD 6,000.01, NZD 0.00
  and a negative amount.
- **Expected Outcome**: Partial lodgement leaves NZD 6,000.00 available and locks
  NZD 4,000.00. Full lodgement locks NZD 10,000.00. Invalid amounts are rejected with no
  balance change.

### F2-02 — Independent notice batches and incoming deposits
- **Origin**: AC-10, A-01, A-06 | **Priority**: must | **Tag**: [custom]
- **Levels**: Unit: yes, Simulation: yes, E2E: no
- **Steps**: In a 32-day account, lodge NZD 4,000.00 on 2026-01-01 and NZD 2,000.00 on
  2026-01-10. Add a permitted top-up after both notices.
- **Expected Outcome**: The batches retain release dates 2026-02-02 and 2026-02-11,
  respectively. The top-up does not change either batch amount or date.

### F2-03 — Cancellation before and at maturity
- **Origin**: AC-11, AC-12 | **Priority**: must | **Tag**: [custom]
- **Levels**: Unit: yes, Simulation: yes, E2E: no
- **Steps**: Cancel an unmatured NZD 4,000.00 batch; separately request cancellation at its
  due date.
- **Expected Outcome**: Before maturity, NZD 4,000.00 returns to available funds with no
  fee. At or after maturity, cancellation is rejected and the maturity flow executes.

---

## 4. Scenarios — Feature 3: Notice maturity and disbursement

### F3-01 — Calendar-day maturity calculation
- **Origin**: AC-13, AC-14, D-07 | **Priority**: must | **Tag**: [custom]
- **Depends**: A-04
- **Levels**: Unit: yes, Simulation: yes, E2E: no
- **Steps**: Lodge notices on 2026-01-01. Check a 32-day notice at 2026-02-02 and a
  90-day notice at 2026-04-01. Repeat a due date that falls on a weekend/public holiday.
- **Expected Outcome**: The release date is lodge date plus exactly 32 or 90 calendar days,
  with lodgement day zero; a weekend or holiday does not shift it. Provisional: schedule
  times follow Pacific/Auckland wall-clock time.

### F3-02 — Principal-only payout and coincident monthly application
- **Origin**: AC-15, AC-16, D-07, D-11, D-12 | **Priority**: must | **Tag**: [custom]
- **Depends**: A-04
- **Levels**: Unit: yes, Simulation: yes, E2E: no
- **Steps**: Arrange for a batch to mature on the first day of a month while the account is
  dormant and has a monthly application due. Apply interest at 00:01 and execute maturity at
  00:02.
- **Expected Outcome**: Monthly net interest is credited first; only matured principal is
  paid to the nominated account; net interest remains in `DEFAULT`; dormancy does not block
  maturity. Provisional: the local timezone is Pacific/Auckland.

---

## 5. Scenarios — Feature 4: Daily variable interest accrual

### F4-01 — Accrual across available and notice balances
- **Origin**: AC-17, D-06 | **Priority**: must | **Tag**: [custom]
- **Depends**: A-03
- **Levels**: Unit: yes, Simulation: yes, E2E: no
- **Steps**: Set NZD 40,000.00 in `DEFAULT` and NZD 10,000.00 in `NOTICE_LOCKED`; use a
  4.00% annual rate and execute one daily accrual.
- **Expected Outcome**: The contract accrues NZD 5.47945 using 50,000 × ROUND_HALF_UP
  (0.04 / 365, 10 decimal places), then rounds the daily amount to 5 decimal places.
  Provisional: A-03 precision and rounding.

### F4-02 — Fixed 365 divisor, leap day and zero balance
- **Origin**: AC-18, AC-19, D-06, A-03 | **Priority**: must | **Tag**: [library]
- **Depends**: A-03
- **Levels**: Unit: yes, Simulation: yes, E2E: no
- **Steps**: Accrue NZD 50,000.00 at 4.00% on 2024-02-29, then on a zero-balance date.
  Compare the leap-day result with the library `"actual"` divisor behavior.
- **Expected Outcome**: Fixed divisor result is NZD 5.47945, not the 366-day result
  NZD 5.46448; zero balance creates no posting. Provisional: A-03 rounding.

### F4-03 — Effective-dated rate change during a notice
- **Origin**: AC-20, A-02 | **Priority**: should | **Tag**: [library]
- **Depends**: A-02
- **Levels**: Unit: yes, Simulation: yes, E2E: no
- **Steps**: Keep a notice active across an effective-dated rate change from 4.00% to
  4.10%. Accrue immediately before and after the change.
- **Expected Outcome**: The accrual before the change uses 4.00%; subsequent accruals use
  4.10% through the batch's maturity. Provisional: the effective-dated rate update is the
  treasury mechanism.

---

## 6. Scenarios — Feature 5: Monthly PIE tax and interest application

### F5-01 — PIR withholding and rounding boundaries
- **Origin**: AC-21, AC-22 | **Priority**: must | **Tag**: [custom]
- **Depends**: A-03
- **Levels**: Unit: yes, Simulation: yes, E2E: no
- **Steps**: Apply NZD 27.40 gross interest at PIRs 0%, 10.5%, 17.5% and 28%. Include a
  value that rounds a half-cent boundary.
- **Expected Outcome**: At 0%, tax is NZD 0.00 and net interest is NZD 27.40. At 28%, tax
  is NZD 7.67 and net interest is NZD 19.73. At 10.5%, tax is NZD 2.88 and net interest
  is NZD 24.52. Provisional: A-03 half-up rounding.

### F5-02 — Month-end, leap February and schedule ordering
- **Origin**: AC-23, D-06, D-12, A-04 | **Priority**: must | **Tag**: [custom]
- **Depends**: A-03, A-04
- **Levels**: Unit: yes, Simulation: yes, E2E: no
- **Steps**: Accrue each day through 2024-02-29 at 23:59:59; run monthly application on
  2024-03-01 at 00:01. Include a notice maturity due on 2024-03-01 at 00:02.
- **Expected Outcome**: The 29 February accrual is included using divisor 365. Tax and net
  interest apply before the principal-only maturity payout. Provisional: A-03 rounding and
  A-04 local timezone.

### F5-03 — Mid-cycle closure tax
- **Origin**: AC-24, D-09 | **Priority**: must | **Tag**: [custom]
- **Depends**: A-03
- **Levels**: Unit: yes, Simulation: yes, E2E: no
- **Steps**: Close an account with NZD 27.40 gross mid-cycle accrued interest and a 28% PIR.
- **Expected Outcome**: Withhold NZD 7.67, credit/pay NZD 19.73 net interest and include it
  in the closure settlement. Provisional: A-03 rounding.

---

## 7. Scenarios — Feature 6: Emergency break and hardship waiver

### F6-01 — Lesser-of charge formula for both terms
- **Origin**: AC-25, D-08 | **Priority**: must | **Tag**: [custom]
- **Depends**: A-03, A-07
- **Levels**: Unit: yes, Simulation: yes, E2E: no
- **Steps**: Break NZD 50,000.00 after 60 days with sufficient interest. Calculate a 32-day
  charge at 4.00%, then a 90-day charge at 4.25%.
- **Expected Outcome**: The 32-day calculated charge is NZD 175.34; the 90-day calculated
  charge is NZD 523.97. Where net attributable interest exceeds the formula amount, charge
  exactly the formula amount. Provisional: A-03 rounding and A-07 rate choice.

### F6-02 — Net-interest cap protects broken principal
- **Origin**: AC-26, D-08, A-03 | **Priority**: must | **Tag**: [custom]
- **Depends**: A-03
- **Levels**: Unit: yes, Simulation: yes, E2E: no
- **Steps**: Break NZD 50,000.00 after five days at 4.00% and 28% PIR. Use gross accrued
  interest NZD 27.40 and tax NZD 7.67.
- **Expected Outcome**: Charge no more than NZD 19.73 net attributable interest; return
  the full NZD 50,000.00 principal. A gross-interest cap of NZD 27.40 would be the wrong
  result. Provisional: A-03 rounding.

### F6-03 — Hardship waiver and invalid break
- **Origin**: AC-27, AC-28 | **Priority**: must | **Tag**: [custom]
- **Levels**: Unit: yes, Simulation: yes, E2E: no
- **Steps**: Process an approved hardship break, then try an unauthorised break and a break
  greater than the locked principal.
- **Expected Outcome**: Approved hardship charges NZD 0.00. Unauthorised or overdrawn
  breaks are rejected; principal and notice balances remain unchanged.

---

## 8. Scenarios — Feature 7: Dormancy and account closure

### F7-01 — Dormancy flag restrictions and permitted exceptions
- **Origin**: AC-29, AC-30, D-11 | **Priority**: must | **Tag**: [custom]
- **Levels**: Unit: yes, Simulation: yes, E2E: no
- **Steps**: Set the configured dormancy flag. Attempt a customer-led debit and a new
  notice; submit an allowed inbound credit, daily accrual, scheduled maturity and closure.
- **Expected Outcome**: Customer-led debit and new notice are rejected. Inbound credit,
  accrual, maturity and closure are accepted. The unit test also verifies the product does
  not use the library's generic dormancy rejection to block these exceptions.

### F7-02 — External dormancy-monitor threshold
- **Origin**: AC-33, D-10 | **Priority**: should | **Tag**: [custom]
- **Levels**: Unit: yes (monitor repository), Simulation: no, E2E: yes
- **Steps**: In the monitor's unit tests, evaluate accounts with customer activity just
  under three years old and with no customer-initiated activity for three years or longer.
- **Expected Outcome**: Do not apply dormancy before three years; apply the configured flag
  at or after the threshold. The monitor is outside this repository; verify flag delivery
  in the recommended E2E.

### F7-03 — Closure with active notices and mid-cycle interest
- **Origin**: AC-31, AC-32, D-09, D-11 | **Priority**: must | **Tag**: [custom]
- **Depends**: A-03
- **Levels**: Unit: yes, Simulation: yes, E2E: yes
- **Steps**: Close a dormant account containing available principal, two notice batches,
  accrued mid-cycle interest of NZD 27.40 and PIR 28%. Apply the break formula per locked
  batch and settle the account.
- **Expected Outcome**: Apply NZD 7.67 PIE tax and pay NZD 19.73 net mid-cycle interest.
  Break fees cannot exceed each batch's net attributable interest; principal is not reduced
  by fees. Complete the closure sweep despite dormancy. Provisional: A-03 rounding.

---

## 9. Scenarios — Contract shape and cross-cutting

### X-01 — CLV4 metadata, parameters and activation
- **Origin**: D-02, D-03 | **Priority**: must | **Tag**: [custom]
- **Levels**: Unit: yes, Simulation: yes, E2E: no
- **Steps**: Render/import the contract in tests, verify CLV4 metadata and required template
  and account parameters, then activate a valid zero-funded NZD account.
- **Expected Outcome**: Contract metadata targets the agreed Vault 5.9 / CLV4 API; required
  resources resolve and activation succeeds with valid parameters.

### X-02 — Pacific/Auckland daylight-saving boundaries
- **Origin**: A-04, D-07, D-12 | **Priority**: should | **Tag**: [custom]
- **Depends**: A-04
- **Levels**: Unit: yes, Simulation: yes, E2E: no
- **Steps**: Simulate accrual, monthly application and notice maturity across the 2026
  Pacific/Auckland daylight-saving transitions, including a maturity on each transition
  boundary.
- **Expected Outcome**: Each event runs once at its configured local wall-clock time;
  notice calendar-date arithmetic is not shifted by a UTC-offset change. Provisional: A-04.

### X-03 — Backdated and future-dated postings
- **Origin**: AC-34, A-09 | **Priority**: should | **Tag**: [library]
- **Depends**: A-09
- **Levels**: Unit: yes, Simulation: yes, E2E: no
- **Steps**: Submit otherwise-valid backdated and future-dated postings through the product
  hook and simulator.
- **Expected Outcome**: The product adds no custom date-only rejection; Vault Core's
  standard processing rules determine acceptance or rejection. Provisional: A-09.

### X-04 — Repeated accrual calculation is deterministic
- **Origin**: added by planner | **Priority**: should | **Tag**: [library]
- **Levels**: Unit: yes, Simulation: no, E2E: no
- **Steps**: Invoke the accrual calculation twice with identical effective balance,
  timestamp, rate and parameters.
- **Expected Outcome**: Both calls return identical instruction content for NZD 5.47945
  accrued on NZD 50,000.00 at 4.00%; this does not assert that duplicate runtime events are
  suppressed.

---

## 10. E2E recommendations

Run only after all planned features are implemented and an authorised sandbox is reachable.
E2E accounts persist; confirm the environment is safe to write to before running.

1. **Notice journey (Features 1–3)**: Open a 32-day account, deposit, lodge two notices,
   top up, cancel one batch and let the other mature. Verify exact release date, principal-only
   payout and remaining available funds.
2. **PIE lifecycle (Features 4–5)**: Open a 90-day account, accrue across a month boundary
   and leap day with a non-zero PIR, then verify tax payable, net interest and effective
   balance addresses.
3. **Break and hardship (Feature 6)**: Verify the 28% PIR after-tax cap on an emergency
   break and a separately approved hardship fee waiver.
4. **Dormancy and closure (Feature 7)**: Apply the external dormancy flag, confirm blocked
   customer-led debits and allowed maturity/closure exceptions, then verify the settlement
   account postings.
5. **Aggregate cap integration (Feature 1)**: With the upstream coordinator enabled,
   submit concurrent deposits across accounts near NZD 5,000,000 and prove atomic rejection
   without exceeding the aggregate.

---

## 11. Coverage table

### Acceptance criteria

| Criterion | Scenarios |
|---|---|
| AC-01 | F1-01 |
| AC-02 | F1-01 |
| AC-03 | F1-01 |
| AC-04 | F1-02 |
| AC-05 | F1-03 |
| AC-06 | F1-04, F2-02 |
| AC-07 | F2-01 |
| AC-08 | F2-01 |
| AC-09 | F2-01 |
| AC-10 | F2-02 |
| AC-11 | F2-03 |
| AC-12 | F2-03 |
| AC-13 | F3-01 |
| AC-14 | F3-01 |
| AC-15 | F3-02 |
| AC-16 | F3-02 |
| AC-17 | F4-01 |
| AC-18 | F4-02 |
| AC-19 | F4-02 |
| AC-20 | F4-03 |
| AC-21 | F5-01 |
| AC-22 | F5-01 |
| AC-23 | F5-02 |
| AC-24 | F5-03 |
| AC-25 | F6-01 |
| AC-26 | F6-02 |
| AC-27 | F6-03 |
| AC-28 | F6-03 |
| AC-29 | F7-01 |
| AC-30 | F7-01 |
| AC-31 | F7-03 |
| AC-32 | F7-03 |
| AC-33 | F7-02 |
| AC-34 | X-03 |

### Decisions

| Decision | Scenarios |
|---|---|
| D-01 | F1-01 |
| D-02 | F1-01, F1-02, X-01 |
| D-03 | X-01 |
| D-04 | F1-03 |
| D-05 | F1-01, F4-03 |
| D-06 | F4-01, F4-02, F5-02 |
| D-07 | F3-01, F3-02, F5-02, X-02 |
| D-08 | F6-01, F6-02 |
| D-09 | F5-03, F7-03 |
| D-10 | F7-02 |
| D-11 | F3-02, F7-01, F7-03 |
| D-12 | F3-02, F5-02, X-02 |

### Standing assumptions

| Assumption | Scenarios |
|---|---|
| A-01 | F2-02 |
| A-02 | F4-03 |
| A-03 | F4-01, F4-02, F5-01, F5-02, F5-03, F6-01, F6-02, F7-03 |
| A-04 | F3-01, F3-02, F5-02, X-02 |
| A-05 | F1-02 |
| A-06 | F1-04, F2-02 |
| A-07 | F6-01 |
| A-08 | F1-01, F1-02, F3-02 |
| A-09 | X-03 |

### Schedules and lifecycle

| Item | Scenarios |
|---|---|
| Opening -> Available | F1-01, X-01 |
| Available -> Notice locked | F2-01 |
| Notice locked -> Available (cancellation) | F2-03 |
| Notice locked -> Matured / payout | F3-01, F3-02 |
| Daily accrual | F4-01, F4-02, F4-03, F5-02 |
| Month-end accrual -> monthly application | F5-01, F5-02 |
| Emergency break -> payout | F6-01, F6-02, F6-03 |
| Dormancy flag -> restricted account | F7-01, F7-02 |
| Dormant -> maturity or closure payout | F7-01, F7-03 |
| Closure -> final tax and settlement | F5-03, F7-03 |

### Uncovered

- The upstream coordinator and external dormancy monitor are absent from this repository.
  Their unit tests belong in their owning projects; this product plan cannot prove their
  implementation until those components and integrations are available.
- Production payment-rail behavior, exact internal-account mappings, legal PIE/DCS
  compliance and live Core connectivity are external to this contract test suite.

---

## 12. Open questions

- **Q14 (Technical, Blocking)**: How will per-batch interest attribution remain correct
  across monthly interest application, tax withholding, cancellation, break and maturity?
  *Default*: Maintain deterministic batch-level accrued-interest and after-tax attribution
  through each settlement, with a unit test for every lifecycle transition. *Close at*:
  implementation plan, before contract code is written.

## Change log

| Version | Date | Author/Reviewer | Comment |
|---|---|---|---|
| 1 | 2026-10-22 | Copilot | Initial plan: 25 scenarios (25 unit, 22 simulation), 5 E2E recommendations, 1 planner-added scenario; 4 `[library]`, 21 `[custom]`; 12 decisions, 9 assumptions and 34 acceptance criteria. |
