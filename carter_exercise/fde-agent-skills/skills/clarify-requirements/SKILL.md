---
name: clarify-requirements
description: Turn an ambiguous business brief for a Thought Machine smart contract into a reviewed REQUIREMENTS.md via structured multi-turn questioning. Runs BEFORE code-writing or testing skills.
compatibility: Works best in a Vault client workspace with the feature_library available for feature discovery; degrades gracefully without it.
audience: client
---

# Clarify Requirements

This skill produces a reviewed `REQUIREMENTS.md` from a product brief.
It does not write contract code or design test suites. Its job is to question
the brief until the requirements are unambiguous, structured, and ready
for engineering, test planning, or architectural review.

The skill is conversational. Go multiple turns with the user,
asking the fewest questions needed to close real ambiguities. Do not ask for
information you can derive from the brief, the `feature_library/`, or the repository.

---

## Workflow

### 1. Inputs & Preparation

You receive:
- A **starting point**: `new` (a new product), `extend` (add to an existing contract), or
  `explore` (analyse without changing anything).
- A **product name** and a **brief** (free text from the user).
- Optionally: an existing `REQUIREMENTS.md` to revise (see Step 6),
  or a path to an existing contract to extend or analyse (e.g. under `src/<product_name>/contracts/`).

Before asking anything:
1. **Derive the product path:** Follow the workspace layout, typically `src/<product_name>/`,
   and write the file to its `documentation/` folder
   (e.g. "basic savings account" -> `src/basic_savings_account/documentation/REQUIREMENTS.md`). If the layout is unclear, ask.
2. **Classify the financial domain:** Silently classify the product as **deposit**,
   **lending**, or **hybrid / unknown**.
3. **Inspect the feature library:** Scan `feature_library/src/feature_library/` for
   candidate features and note them for each feature's Build Approach. Use the library as your
   baseline for capabilities, parameter constraints, code-level defaults, and calculation algorithms.

---

### 2. Ambiguity Detection & Checklist

Scan the brief against this checklist. Every unstated, contradictory, or
under-specified item is a candidate question.

**Money & denomination**
- Currency (single or multi-currency).
- Rounding policy and precision split (e.g. 5 dp for daily accrual vs. 2 dp for capitalisation).
- Sub-penny residue at application and closure (e.g. carry forward under 0.005 vs. clear).
- Balance limits, minimum opening balances, and transaction thresholds.

**Lifecycle & closure**
- Activation prerequisites (initial funding, KYC status, linked account).
- Closure conditions: zero balance required, or automatic balance sweep? Who can initiate closure?
- Accrued interest at closure: capitalise, clear/forfeit, or sweep?
- Part-day accrual for closure on the final day.
- Dormancy rules and restrictions.

**Interest & calculation mechanics**
- Accrual cadence (daily, per-posting) and capitalisation cadence (monthly, annual).
- Day-count basis (library default: `DEFAULT_DAYS_IN_YEAR = "actual"`, or explicit 365/360).
- Rate calculation: quote the exact library formula (e.g. daily rate
  rounded to 10 dp before multiplication), not generic textbook math.
- Interest rate bounds (e.g. `0.0 <= rate <= 1.0`).
- Tiering, teaser rates, promotional periods.
- Payable (deposit) vs. receivable (lending).

**Lending-specific (if applicable)**
- Amortisation type (declining balance / fixed repayment / minimum payment / interest-only).
- Repayment schedule, repayment holidays, and grace / cure periods.
- Delinquency treatment, penalty interest, fee schedules, and charge-off policy.
- Collateral, Loan-to-Value (LTV), and credit limit rules.

**Deposit-specific (if applicable)**
- Overdraft policy (arranged / unarranged) and limits.
- Withdrawal limits, maximum deposit caps, and notice periods.
- Maturity and roll-over behaviour for fixed-term deposit products.

**Fees & charges**
- Which fees exist (monthly maintenance, transaction fees, late fees, exit fees).
- Accrual cadence, trigger events, and destination accounts for fee postings.
- Fee waivers, caps, and reversal policies.

**Transaction handling & limits**
- Accepted posting instruction types (e.g. hard settlements only, transfers, pre-authorisations).
- Batch evaluation against limits (the library checks the combined net amount).
- Single withdrawal limits and payment routing restrictions.

**Schedules & notifications**
- Scheduled event timings and time zone.
- Schedule clashes: offset events that would run at the same moment by at least 1 minute
  (e.g. accrual at 00:00:00, application at 00:01:00).
- Outbound notifications: statements, overdue alerts, threshold breach warnings.

**Edge cases the user is likely to have ignored**
- Backdated and future-dated postings: default to Vault platform behaviour
  (accepted) unless the business demands custom rejection.
- Open authorisations at closure or limit checks.
- Rate changes mid-cycle and leap-year treatment.
- Zero-balance cycles.
- Grace-period deposits after the repayment due date (lending).
- Adjustments: continuous across account history, or one-off corrections?

**Non-functional & architectural constraints**
- Parameter scope: product-level (fixed across accounts), account-level (per customer), or global / node.
- Tenant constraints: calendar configurations, System of Record (SoT) integration.
- High Volume Accounts (HVA): more than 20 transactions per second to a single account.
- Minimal data fetching: request only the parameters and balances each decision needs.

---

### 3. Asking Questions

Ask at most **five questions per batch**. Lead with high-impact architectural
choices (deposit vs. lending, amortisation type, currency scope, closure mechanism).

For each question:
- **Number it:** Use `Q1`, `Q2`, … continuously across batches, so each question and its answer
  can be recorded in the Clarification log (Step 5) and cited by decisions.
- **Disclose build cost:** Label every option `[library: <feature>]`
  (existing tested code) or `[custom code needed]` (new contract logic). If the user
  requests a custom rule, note the maintenance cost and offer the library alternative.
- **Separate behaviour from concrete values:** Never ask a combined question where
  answering "use defaults" produces an invented number. Split behavioural rules from
  numeric inputs:
  - *Behaviour (with default):* `[library: maximum_balance_limit] Reject deposits that would breach the maximum balance? (default: yes)`
  - *Value (no default):* `Maximum balance threshold (no default; specify an amount or reply TBC)`
- **Resolve unspecified details in this order of precedence:**
  1. What the user explicitly stated.
  2. What the installed `feature_library` defines (quote the module/function).
  3. Standard Vault platform behaviour (`common-references`).
  4. If undefined by all three: ask the user, or propose `TBC`.

After each batch, update your working requirements. Three batches are usually
enough; do not probe for details the user does not have.

---

### 4. Surfacing Assumptions

At the end of each turn, restate all **assumptions** as `- **A-xx - Title**: <statement>`:
- Cite the source, e.g. `- **A-01 - Rounding method**: Half-up rounding (ROUND_HALF_UP). Source: feature_library common.utils.round_decimal. (Not a user decision)`.
- **Never misattribute agent assumptions or accepted defaults as something the user confirmed.**
- **Ask for corrections:** End the turn with "Reply with any corrections; silence means accepted." Record an accepted assumption as an assumption, and a corrected one as a decision with its `Qn` source.

---

### 5. Finalising REQUIREMENTS.md

When ambiguities are resolved, generate `REQUIREMENTS.md` at the path from Step 1, creating the
`documentation/` folder if it does not exist.

#### Architecture: Product-Level Sections and Feature Sections

`REQUIREMENTS.md` has product-level sections and feature sections:

1. **Product-level sections:** Identity, commercial decisions, standing assumptions, lifecycle states, clarification log.
2. **Feature sections (`## Features`):** One per capability (e.g. *Denomination & Overdraft Prevention*, *Daily Interest Accrual*), each with the subsections listed below.

#### Authoring Standards

##### 1. Confirmed Decisions: Lightweight ADR Format
Record choices in product-level sections as:
`- **D-xx - <Topic> (<Source>)**: <Choice>. <Consequence or boundary>.`

* **Source:** `(Brief)`, `(Q1)` (the answer to Q1 in the Clarification log), or `(Default)`. Every `Qn` cited must have a log row.
* **Direct statements:** State choice and boundary directly (e.g. `GBP only. Non-GBP postings are rejected with WRONG_DENOMINATION.`).
* **No boilerplate:** Do not prefix with "The contract must...".
* **Business rules only:** Keep library module and parameter names out of decisions; put them in Build Approach and Implementation notes.

##### 2. Standard Feature Sections
Every feature under `## Features` must contain these eight subsections in order. Write `N/A - <reason>` (e.g. `N/A - validation only, no ledger postings`) for any that does not apply:

1. **User Story:** Blockquote (`> As a <persona>, > I want <capability>, > so that <outcome>.`).
2. **Overview (`#### Overview`):** Mechanism, lifecycle phases, execution triggers, affected balance addresses, and ledger alignment.
3. **Build Approach (`#### Build Approach`):** How the feature is built:
   - `Approach`: `Library`, `Mixed`, or `Custom`.
   - `Library module`: the reused `feature_library` module path(s), or `None found`.
   - `Custom code`: what must be written and why, or `None`.
   - `Library behaviour to note`: library behaviour that differs from the requirement, or `None`.
   - `Status`: `verified` against the library, or `not checked` if unavailable.
4. **Parameters (`#### Parameters`):** Table (`| Parameter Name | Type | Level | Description | Default Value | Min Max Values |`). Level: `Global`, `Node`, `Product`, or `Account`, set where the value is actually set (a value fixed for all accounts is `Product`). Default: value, or `TBC` if unset (never invent values). Min Max Values: the range left open after applying decisions; if a decision fixes the value, write `Fixed to <value> (D-xx)` instead of the library's full range. `N/A - <reason>` if none.
5. **Calculation Formula (`#### Calculation Formula`):** Plain-text equations (no LaTeX), `Where:` definitions (balance timing, day-count, balance composition), and a worked example showing intermediate precision and rounding. Use the same names for amounts here and in Accounting Entries. `N/A - <reason>` if no calculation.
6. **Acceptance Criteria (`#### Acceptance Criteria`):** BDD criteria formatted per ASD-STE-100:
   `- **AC-xx - <Topic>**: **GIVEN** <precondition>, **WHEN** <trigger>, **THEN** the contract must <action> [**AND** the contract must <action>].` (or table: `| AC Number | Scenario | Description |`).
   - Active voice (`THEN the contract must...`, never passive); strict modal verbs (`must` / `must not`).
   - One outcome per clause (≤ 20 words); include test values for calculations and limits.
   - Include month lengths (28/30/31 days, leap February), leap years, and DST where relevant.
   - Cover: happy path, zero balance, negative/excess balance, value timestamps (e.g. accruals dated to the end of the previous day), and rejections.
   - Walk the Step 2 checklist and add a scenario for every applicable item, including a batch of several postings against any limit or balance check, and backdated / future-dated postings.
7. **Accounting Entries (`#### Accounting Entries`):** Table (`| Account Type | Internal Account Name | Balance Address | Dr/Cr | Amount | value_timestamp |`). `Account Type`: `Customer` or `Internal` (`N/A` as internal account name for customer rows). `value_timestamp`: `end of previous day (23:59:59)` or `current_time`. Use sub-tables for multiple posting events. `N/A - <reason>` if no postings.
8. **Notification Details (`#### Notification Details`):** Type, trigger event, payload fields. `N/A - <reason>` if none emitted.

#### Document Structure

Keep the document readable by non-technical reviewers; put module paths and internal codes in Implementation notes and Build Approach.
End every `REQUIREMENTS.md` with a `## Change log` table, starting with version 1, so that revisions (Step 6) only add rows to it:

```markdown
# <Product Name> — Requirements

## Overview
<one paragraph — business purpose of the product and target customer segment>

## Confirmed decisions
- **D-01 - Product type (Brief)**: Deposit (liability to the bank), new product.
- **D-02 - Currency (Brief)**: GBP only. Postings in any other denomination are rejected.
- **D-03 - Day count and rounding (Q2)**: Actual day count; accrue to 5 dp; apply at 2 dp using ROUND_HALF_UP.

## Standing assumptions
- **A-01 - <Topic>**: <assumption, with source cited (feature_library or platform default)>

## Open items
| Item | Type | Needed for | Owner |
|---|---|---|---|
| <name> | <parameter value / business decision / external dependency> | <e.g. deployment, test plan> | <who supplies it> |

## Lifecycle
<ordered states (e.g. PENDING -> OPEN -> CLOSED) with trigger conditions and closure rules>

---

## Features

### Feature 1: <Feature Name>

**User Story:**
> As a <persona>,
> I want to <business action>,
> so that <business outcome>.

#### Overview
<mechanism, lifecycle phases, triggers, balance addresses affected, ledger alignment>

#### Build Approach
- **Approach**: <Library / Mixed / Custom>
- **Library module**: <module path, or None found>
- **Custom code**: <what and why, or None>
- **Library behaviour to note**: <differences from the requirement, or None>
- **Status**: <verified / not checked>

#### Parameters
| Parameter Name | Type | Level | Description | Default Value | Min Max Values |
|---|---|---|---|---|---|
| <name> | <type> | <Global / Node / Product / Account> | <description> | <value or TBC> | <constraints> |

#### Calculation Formula
<equations, Where: definitions, worked example — or N/A - reason>

#### Acceptance Criteria
- **AC-01 - <Topic>**: **GIVEN** <state/balances>, **WHEN** <trigger/posting>, **THEN** the contract must <action>.

#### Accounting Entries
| Account Type | Internal Account Name | Balance Address | Dr/Cr | Amount | value_timestamp |
|---|---|---|---|---|---|
| <Customer / Internal> | <name or N/A> | <address> | <Dr / Cr> | <amount or formula> | <timing rule> |

#### Notification Details
<type, trigger, payload fields — or N/A - reason>

---

## Schedules Summary
| Event Type | Schedule (Time / Cadence) | Offset | Purpose |
|---|---|---|---|
| <EVENT_NAME> | <cadence & time> | <offset, e.g. 00:00:00 vs 00:01:00> | <feature and purpose> |

## Out of scope
<explicit exclusions to prevent downstream scope creep>

## Clarification log
| ID | Question | Answer | Feeds |
|---|---|---|---|
| Q1 | <question as asked> | <user's answer, or "no answer - defaulted"> | <D-xx / A-xx it produced> |

## Implementation notes
<technical notes for the contract author: internal flag names, rejection reasons, wiring details>

## Change log
| Version | Date | Author/Reviewer | Comment |
|---|---|---|---|
| 1 | <date> | <author / reviewer> | Initial version. <what it covers, e.g. the brief and the answers it was built from> |
```

---

### 6. Revising an Existing REQUIREMENTS.md

When updating an existing `REQUIREMENTS.md` based on new inputs, test plan feedback,
or loop-backs:
1. **Reconcile:** Read the full existing file and cross-check new answers against earlier decisions.
2. **Supersede conflicts:** If a new rule contradicts an earlier decision, update it or mark it `[Superseded by D-xx: reason]` so the document never conflicts with itself.
3. **Cascade updates:** Update all affected sections (Overview, Parameters, Lifecycle, Acceptance criteria, Build approach).
4. **Preserve stable IDs:** Never renumber existing `D-xx`, `A-xx`, `AC-xx`, or `Qn` IDs. Append new questions and answers to the Clarification log. When an item is withdrawn, label it `[Withdrawn: reason]`.
5. **Add a row to the `## Change log`** table at the end of the file (it exists from version 1). Increment the version by one. The Comment says what changed from the previous version: the IDs added, changed or superseded, and why.
   ```markdown
   | <n> | <date> | <author / reviewer> | <what was updated, added, or superseded since version n-1, and why> |
   ```

---

### 7. Handoff

Write the file to the path from Step 1. Report its path and a summary, and list the standing assumptions and open items for the user to accept, correct, or assign an owner. Once the user has responded, update the file and **stop**.

Do not start planning, writing contract code, or designing test suites. Return
control to the user or workflow orchestrator, who decides the next stage.

---

## Guardrails

- **Never invent numbers or dummy placeholders.** If a parameter is unset, write `TBC` in Default. Record every `TBC` parameter, and any other unresolved decision or dependency, in `## Open items`.
- **Never defer the deposit-vs-lending question.** Resolve this in the first batch.
- **Prefer the library over custom code.** Check `feature_library` first; disclose custom code costs.
- **Keep decisions scannable.** Record choices as Lightweight ADRs (`- **D-xx - Topic (Source)**:`) without boilerplate prefixes.
- **Put worked numbers in Acceptance Criteria.** Include test amounts and boundary cases for calculations and limits.
- **Keep stable IDs.** Use `D-xx`, `A-xx`, `AC-xx`, and `Qn`. Log every question asked in the Clarification log.
- **Always end with a Change log.** It is a table with the columns Version, Date, Author/Reviewer and Comment. Version 1 starts it with `Initial version`; revisions add a row that says what changed from the previous version.
- **Keep all eight feature subsections, in order** (`User Story`, `Overview`, `Build Approach`, `Parameters`, `Calculation Formula`, `Acceptance Criteria`, `Accounting Entries`, `Notification Details`). Write `N/A - <reason>` when one does not apply.
- **Stop probing once ambiguity is closed.** Default using the Step 3 precedence and surface the defaults as assumptions.
