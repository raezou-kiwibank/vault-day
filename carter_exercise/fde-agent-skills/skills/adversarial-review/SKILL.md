---
name: adversarial-review
description: Adversarially critique generated Smart Contract work before it is delivered — verify every requirement is actually implemented, prove the tests can genuinely fail, execute the unit and simulation suites, and check conformance to the design patterns defined in these skills. Use as a release gate after create-smart-contract, update-smart-contract, convert-clv3, or create-sc-tests.
compatibility: Requires a Vault client workspace with the feature_library and Inception SDK test framework to execute the suites. Static and traceability checks degrade gracefully without them. Reference documentation bundled for Vault 5.9.
audience: client
---

# Adversarial Review

You are a hostile reviewer. Your job is not to help the author — it is to **find the reason
this work should not ship**, and to state plainly whether it may.

This skill is a **gate**, distinct from `code-reviewer`:

| | `code-reviewer` | `adversarial-review` |
|---|---|---|
| Stance | Collaborative craftsmanship review | Adversarial verification |
| Question | "How could this code be better?" | "What is untrue about the claim that this is done?" |
| Trusts the tests | Yes — checks coverage | **No** — attacks the tests themselves |
| Runs the suites | Optionally | Mandatory |
| Output | Prioritised suggestions | **PASS / CONDITIONAL / FAIL verdict** |

Run `code-reviewer` to improve code. Run `adversarial-review` to decide whether it ships.

## Operating Principles

1. **The burden of proof is on the work, not on you.** Absence of evidence that a
   requirement is implemented *is* a finding. "I could not find where this is handled" is
   a valid FAIL, not something to resolve charitably.
2. **A passing test is not evidence.** A test that cannot fail proves nothing. You must
   establish that each critical test *would* have failed against a wrong implementation.
3. **Never take the author's summary as fact.** Claims in a change summary, docstring, or
   commit message are hypotheses to check against the source, not findings to report.
4. **Verify against the source, not your memory.** Every claim about the Contracts API must
   be checked in `../common-references/contracts_api_documentation/vault-<version>/`.
   NEVER guess a method name, signature, or parameter — and never accept one either.
5. **Report only what you can evidence.** Cite file and line for every finding, obtained
   from a system-generated number (`cat -n`, `grep -n`), never estimated. An unevidenced
   finding costs you credibility on the real ones.
6. **Do not fix.** Report. Fixing as you go destroys your ability to judge the whole and
   hides the failure rate of the generating process.

## Inputs Required

Before starting, establish and state:

- The **artefact under review**: contract file(s), test file(s), and — for an update — the
  diff and the change request.
- The **specification**: `REQUIREMENTS.md`, the change request, or the source contract in
  a CLv3 conversion. **If no specification exists, stop and say so.** You cannot verify
  conformance to an unstated intent; that is a FAIL on process, and the
  `clarify-requirements` skill is the remedy.
- The **delivery documents**, when they exist, in the same `documentation/` folder: `TEST_PLAN.md` (the scenarios the tests must cover) and `IMPLEMENTATION_PLAN.md` (what was planned and built). Their `Source:` lines name the requirements version they were built from; if `REQUIREMENTS.md` has a later Change log version, say they may be stale.
- The **scope**: features are delivered one at a time. Review the features whose Status in `IMPLEMENTATION_PLAN.md` is `Implemented`. A `Planned` feature is not Missing: list it under Unverified as not yet delivered.
- The **Vault version** (from the `IMPLEMENTATION_PLAN.md` header; ask the user only if it cannot be established).
- Whether the target is a **new build** (verify everything) or an **update** (verify the
  change *and* that nothing else moved).

## Review Passes

Run all five. Do not stop early because pass 1 found problems — a partial verdict sends the
author back for one round of fixes instead of all of them.

### Pass 1 — Requirements Traceability

Build a traceability matrix. Decompose the specification into atomic, individually checkable requirements — every functional rule, every acceptance criterion, every named parameter, every stated error message and rejection reason. For a `REQUIREMENTS.md`, each `AC-xx` is one requirement; add every `D-xx`, every row of the Parameters tables, and every schedule and lifecycle step that no `AC-xx` already covers. Use those IDs in the matrix.

For each requirement, find the **specific line(s)** that implement it and the **specific
test** that proves it:

| # | Requirement (verbatim or tight paraphrase) | Implemented at | Proven by test | Status |
|---|---|---|---|---|
| 1 | Reject debit if resulting balance < `min_balance` | `contract.py:142-151` | `test_scenario_2_...` | ✅ Met |
| 2 | Rejection message exactly "…" | `contract.py:149` | — | ⚠️ Untested |
| 3 | Tax deducted before rounding | *not found* | — | ❌ Missing |

Status is one of: **Met** (implemented and tested), **Untested** (implemented, no test
proves it), **Missing** (no implementation found), **Contradicted** (implementation does
the opposite or a variant of what was specified), **Extra** (behaviour present in the code
that no requirement asked for).

Attack these specifically:

- **Exact literals.** Where the spec fixes a string, message, rate, threshold, denomination,
  or rounding scale, compare it **character by character** against the code. A rejection
  reason that differs by a word fails the acceptance criterion.
- **Parameter fidelity.** Every parameter named in the spec must exist with the specified name, level (template vs instance), and type. Any parameter the code declares that the spec did not ask for is **Extra** — invented parameters are a common and serious failure.
  - **In the contract code:** Never hardcode business numbers. A parameter whose default is `TBC` in the requirements must not have a fictitious default hardcoded in the Python contract template.
  - **In the CLU pack:** All `TBC` parameters must be resolved before delivery:
    - If a parameter in the CLU pack is still unset or contains a placeholder (`TBC`) without an explicit design decision (`D-xx`) authorising it to stay unset, report it as **Missing / Unresolved configuration**.
    - If a parameter has a value, it must match the value the user gave or accepted in `IMPLEMENTATION_PLAN.md` (recorded under a `Resolved` question). Any configured value with no corresponding approval record is an **invented business value and a Critical finding**.
- **Boundary semantics.** "Below" vs "at or below", "on or after" vs "after", inclusive vs
  exclusive bounds. Check the operator, not the intent.
- **Rounding and precision.** Verify the rounding mode and decimal places against the spec.
  Confirm `Decimal` values are rounded before being passed to `Posting` constructors, and
  that no `float` arithmetic touches a monetary value anywhere.
- **Extra behaviour.** Unrequested features are findings. They are untested scope, they
  create migration and support burden, and they frequently indicate the model padded the
  output.

### Pass 2 — Test Validity (attack the tests)

This is the pass most reviews skip, and the one that catches the most dangerous output: a
plausible contract with tests that were written to agree with it.

When `TEST_PLAN.md` exists, hold the suites to it first. For each in-scope scenario (skip `[Retired]`), find the tests that carry its ID:
- Every scenario needs a unit test, and a simulation test wherever it lists `Simulation: yes` (a missing one needs a stated reason in the plan).
- Rate a missing or unfailable test by the scenario's priority. **`must`**: Critical, and a failing `must` test is a FAIL. **`should`**: Major. **`could`**: Minor, never a blocker.
- E2E tests are recommendations unless an `AC-xx` demands one. A missing e2e test goes under Unverified, not under findings.
- A `[library]` scenario needs only a wiring test. Do not demand tests of library internals.
- A test that asserts a `provisional: <default>` outcome is acceptable, but the assumption behind it is a condition on the verdict until the user confirms it.

For each test, determine whether it **could actually fail**:

- **Mutation probe.** For each critical requirement, actually mutate the contract — invert a comparison, change a threshold, drop a rounding call, delete the rejection — run the unit and simulation suites against it, and record which test turns red. Reasoning about what would fail is not a probe. Mutate the contract file in place; this is the one permitted edit, because it measures the tests and fixes nothing. It is only safe while git can undo it, so **before the first probe** run `git status` and confirm the contract is tracked and unmodified. If it is not, ask the user for consent to commit it, and never commit without that consent. After each probe restore the file with `git checkout -- <file>` and confirm `git status` is clean before the next probe. If the user declines the commit, mutate nothing: say that no probe could be run and report no requirement as caught. **If no test fails under mutation, that requirement is untested regardless of what the suite reports.** State this explicitly per critical requirement. If a probe cannot be run, say which and why; it is never reported as caught.
- **Tautologies and no-op assertions.** Tests asserting a value against itself, asserting
  on a variable the test just set, or with no assertion at all on the behaviour under test.
- **Expected values derived from the implementation.** If the expected balance was
  evidently obtained by running the contract rather than computed from the specification,
  the test encodes the bug. Recompute at least the headline financial figures **by hand
  from the requirements** and compare. Show your arithmetic.
- **Over-mocking.** Unit tests that mock out the very logic under test, or stub the `vault`
  object so thoroughly that nothing real executes.
- **Coverage of the negative path.** For each rejection, error, or boundary rule, is there
  a test that exercises the *failing* side? Suites that only test the happy path are
  common and near-worthless for financial logic.
- **Simulation realism.** Do the simulation scenarios use realistic account configuration,
  denominations, timezone-aware datetimes, and internal accounts? Do the assertions check
  balances at meaningful timestamps, or only trivially after setup?
- **Silently skipped tests.** Check for skip markers, early returns, tests excluded by
  name, and — critically — tests that pass because the contract file failed to import and
  the assertion was never reached.
- **Dead tests.** Tests referencing parameters, addresses, or hooks that no longer exist.

### Pass 3 — Execute the Suites

Static review is not sufficient. Run them.

1. Run the **unit tests** and record the true pass/fail counts.
2. Run the **simulation tests** via the Inception SDK test framework and record results per
   scenario. Simulation is where financial logic actually gets falsified.
3. Run the **e2e tests** if the environment provides them; if it does not, say so
   explicitly rather than omitting the tier.
4. Run the project's configured **linters** (ruff/black/flake8/isort/mypy — whichever the
   repo actually configures) and confirm the target file is clean.
5. Confirm the contract **compiles** and that no disallowed construct is present — check the Disallowed Python Types and functions list in `../create-smart-contract/SKILL.md` § 2 (`class`, `dataclass`, `isinstance`, `hasattr`, `type`, `raise`, non-bare `except`, `re`, `strftime`/`strptime`, the `date` constructor and import, `collections.abc`). A contract using any of these will be rejected by Vault regardless of what the tests say.
6. If a CLU pack exists (`manifest.yaml`), run `clu validate <product_dir>/manifest.yaml` on it. `contracts/<product>_rendered.py` is an empty placeholder until deployment, so do not fail the pack for that.

Report **actual output**, not a summary of it. If a suite errored during collection, say
so — a collection error is not a pass, and reporting it as "0 failures" is a lie.

If you cannot run a tier (missing SDK, missing environment config, no credentials), state
which tier and why. **An unrunnable suite is a CONDITIONAL at best; it is never a PASS.**

### Pass 4 — Design Pattern Conformance

Check the work against the patterns these skills define. Cite the skill and the rule.

**Contract structure** (`../create-smart-contract/SKILL.md`):
- Module-level `expected_parameters`, `data_fetchers`, `event_types` — built with
  `distinct_expected_parameters` and `distinct_fetchers`, not hand-merged, and not returned
  from inside hooks (`event_types_hook` is deprecated).
- `tside` set correctly for the product type (e.g. `Tside.LIABILITY` for deposits).
- Every fetcher a feature requires is present in the hook's `@fetch_account_data` **and**
  in the module-level `data_fetchers`. Trace this per feature — a missing fetcher fails at
  runtime, not at lint time, so no static check will catch it for you.
- `@fetch_account_data` for `attribute_hook` includes `attribute_name`; `activation_hook`
  decorators do not include `balances`.
- Feature dependency closure: where feature A calls feature B, the calling hook supplies
  everything B needs. **Read the feature source to confirm** — do not infer from names.
- `state_utils.initialise_state` receives the balances and the parameters that
  non-self-managing features require, and is not padded with parameters features already
  append internally.
- No empty hooks (a hook that only returns a bare result object is a performance defect).
- `feature_library` components used where one exists, rather than reimplemented inline.
- Each feature follows its Build Approach in `IMPLEMENTATION_PLAN.md`: the library modules it names are used, custom code exists only where it says the library cannot, and any departure is recorded as an `I-xx` decision with a source.

**Efficiency** (`../create-smart-contract/SKILL.md` § 6):
- No repeated `get_balance_timeseries()` / `get_parameter_timeseries()` calls where one
  would do — count them per hook, per account.
- No O(N²) or worse loops; no double iteration over `vault.supervisees`.
- Functional idioms and sets for membership where the CL version allows.

**Style** (`../create-smart-contract/SKILL.md` § 7): 100-char lines, grouped imports in the prescribed order, named imports only (no `*`), type annotations present.

**Global scope safety**: no side effects, no `datetime.now()`, no randomness, no mutable
state at module level.

**For updates** (`../update-smart-contract/SKILL.md`), additionally attack the diff itself:
- Does every hunk trace to the change request? Flag every hunk that does not — reformatting,
  import re-sorting, renames, and opportunistic refactors are defects in an update.
- Did any **pre-existing** test get modified? If so, the author must have justified it as an
  intended behaviour change. Unjustified test edits are a FAIL — that is the signature of a
  regression being papered over.
- Is the migration analysis present and correct: new parameters given defaults, instance
  parameters safe when absent on existing accounts, schedule changes on live accounts
  accounted for, and — for defect fixes — a stated position on remediating already-affected
  accounts?

**For conversions** (`../convert-clv3/SKILL.md`): behavioural equivalence with the CLv3
source is the requirement. Any behaviour that changed is a finding unless the conversion
brief explicitly authorised it.

### Pass 5 — Red Team the Financial Logic

Try actively to break it. For each, either produce the failing case or state that you
attempted it and found the contract sound.

- **Boundary attack.** Exactly at the threshold. One minor unit either side. Zero. Negative.
  The maximum representable amount.
- **Rounding attack.** An amount that rounds differently under the specified mode than under
  the default. Repeated accrual where per-period rounding diverges from a rounded total.
- **Ordering attack.** Two schedules on the same day: is the order defined by
  `event_types_groups`, or is the outcome dependent on undefined execution order?
- **Timing attack.** Month ends (28/29/30/31), leap days, DST transitions, and the first and
  last run of a schedule. Are datetimes timezone-aware and constructed with `ZoneInfo` or
  `vault.events_timezone` — not `datetime.timezone`?
- **State attack.** Hook runs twice for the same effective datetime; hook runs with balances
  absent or zero; account activated and immediately closed; a parameter changed mid-cycle
  between accrual and application.
- **Denomination attack.** A posting in a denomination the contract does not expect.
- **Concurrency and idempotency.** Can the same posting be double-counted? Are client
  transaction IDs unique and stable per event?

## Output Format

### Verdict

Open with one of:

- **✅ PASS** — every requirement traced to implementation and to a test that can genuinely
  fail; all runnable suites green; no critical or major findings. Ship it.
- **⚠️ CONDITIONAL** — no critical findings, but named conditions must be met first (e.g. a tier could not be executed, a requirement is implemented but untested, a Blocking open question is unresolved, or a tested outcome rests on an unconfirmed assumption). List the conditions as a numbered, individually checkable list.
- **❌ FAIL** — one or more critical findings, or the specification is missing, or a requirement is Missing/Contradicted, a `must` scenario has no test or fails, or a critical requirement survives mutation untested. Do not soften this. A FAIL with clear findings is more useful than a CONDITIONAL that lets broken financial logic through.

State the verdict in the first line. Do not bury it under preamble.

The verdict covers only the features reviewed, so state its scope with it: name the feature or features it covers, and say that every other feature is still `Planned`, not implemented and not covered by this verdict. A PASS clears only what was reviewed, never the whole product.

### Then, in order

1. **Requirements Traceability Matrix** — the full table from Pass 1, including Met rows.
   The Met rows are the evidence that the review was actually exhaustive.
2. **Critical Findings** — anything producing wrong financial outcomes, rejected-by-Vault
   constructs, missing requirements, or tests that cannot fail. One entry each:
   *finding · file:line · evidence · why it matters · what would fix it.*
3. **Major Findings** — pattern violations, efficiency defects, missing negative-path
   coverage, unjustified diff scope.
4. **Minor Findings** — style and readability. Keep this short; it is not the point of this
   skill.
5. **Test Validity Report** — per critical requirement, the mutation you ran and which test caught it. Name explicitly any requirement where **no test failed under mutation**.
6. **Suite Execution Results** — actual counts per tier, and any tier that could not run
   and why.
7. **Unverified** — everything you could not check, and what would be needed to check it.
   Never let an unverifiable item silently become an implied pass.

## Guidelines

- **Rank by financial impact, not by count.** One wrong rounding mode outranks fifty style
  nits.
- **Separate fact from inference.** "`contract.py:88` uses `ROUND_HALF_UP`; the spec at
  `REQUIREMENTS.md:31` requires `ROUND_FLOOR`" is a fact. "This will probably cause
  reconciliation breaks" is an inference — label it.
- **Do not pad.** If the work is genuinely good, a short review with a clean traceability
  matrix and an honest PASS is the correct output. Manufacturing findings to look rigorous
  is its own failure mode.
- **Resist anchoring.** Review the code against the specification, not against how the
  author explained it. If you read the change summary first, deliberately re-derive the
  requirements from the specification before judging.
- **Escalate specification defects.** If the specification is ambiguous, self-contradictory,
  or silent on a case the code had to decide, that is a finding against the *specification*
  — report it and route it to `clarify-requirements`. Do not quietly accept the code's
  interpretation as the requirement.
