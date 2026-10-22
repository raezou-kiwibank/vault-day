---
name: update-smart-contract
description: Make a surgical, minimal-diff change to an existing Thought Machine Vault Smart Contract — add one feature, modify one behaviour, remove a feature, or fix a defect — while preserving all untouched behaviour. Use when a contract already exists and only part of it must change, instead of regenerating it with create-smart-contract.
compatibility: Requires a Vault client workspace with the feature_library source tree and an existing Smart Contract to modify. Reference documentation bundled for Vault 5.9.
audience: client
---

# Update Smart Contract

This skill performs **surgical modification** of a Smart Contract that already exists and is (or soon will be) in production. It is deliberately distinct from `create-smart-contract`:

| | `create-smart-contract` | `update-smart-contract` |
|---|---|---|
| Starting point | REQUIREMENTS.md, IMPLEMENTATION_PLAN.md and the features built so far | A working contract + a change request |
| Success measure | The planned feature is implemented and earlier features did not move | Change is implemented **and nothing else moved** |
| Output | One more feature in the contract | A minimal diff |
| Risk | Getting the product wrong | Silently breaking live accounts |

**Governing rule: every line you change must be justified by the change request.** If you cannot name the requirement that forces a line to change, revert that line. Reformatting, renaming, re-ordering, "while I'm here" cleanups and opportunistic refactors are defects in this skill, not improvements. If you spot unrelated problems, report them in the Follow-ups section — do not fix them in this diff.

## Workflow

### 0. Version Identification

Before starting any work, you MUST establish:

1. The **Vault version** (e.g. 5.9) of the contract being modified. Read it from `documentation/IMPLEMENTATION_PLAN.md` or the `api = "..."` line in the contract itself, and confirm with the user.
2. Whether the contract is **already deployed to any environment with live accounts**. This single answer decides whether Step 5 (Migration Safety) is advisory or mandatory.

### 1. Reference Documentation

**STRICT MANDATE**: Consult the authoritative reference documentation in `../common-references/contracts_api_documentation/vault-<version>/` for the version in use (e.g. `vault-5-9/`). NEVER guess method names, signatures, or parameters — verify them. The layout of that folder, and the full set of CLv4 reference paths (metadata, allowed built-ins, native imports, types, enums, the `vault` object, hooks, decorators), is documented in `../create-smart-contract/SKILL.md` § 2. Follow the same paths.

The **Disallowed Python Types and functions** list in `../create-smart-contract/SKILL.md` § 2 applies here in full. Newly introduced code must obey it even if the surrounding legacy code does not.

### 2. Classify the Change

Every request maps to one of five change types. State which one you are doing before you edit anything — the type determines the blast radius you must check.

| Type | Description | Highest-risk blast radius |
|---|---|---|
| **A. Add feature** | New behaviour from `feature_library` or bespoke logic | New parameters, fetchers, event types, hook wiring |
| **B. Modify behaviour** | Existing feature behaves differently | Rounding, thresholds, ordering, existing balances |
| **C. Remove feature** | Behaviour retired | Orphaned parameters/fetchers/schedules, stranded balance addresses |
| **D. Fix defect** | Existing behaviour is wrong | Corrective postings for accounts already affected |
| **E. Parameter change** | Value, type, level, or shape of a parameter | Live accounts holding the old value |

If the request bundles several of these, split it. Do one change type at a time, verify it, then move to the next. A single diff that both adds a feature and refactors an existing one cannot be reviewed or rolled back safely.

### 3. Establish the Baseline

Never edit a contract you have not first understood and pinned down.

1. **Read the target region only.** For files over 300 lines, use `grep -n` to locate the hooks, features, and helpers involved, then read those line ranges. Do not read the whole file into context if you do not need it.
2. **Map the current wiring.** Record, for the contract as it stands today:
   - module-level `expected_parameters`, `data_fetchers`, `event_types`, `event_types_groups`, `tside`, `api`, `version`
   - which hooks exist and which `@fetch_account_data` / `@requires` decorators they carry
   - which `feature_library` features are imported and where each is invoked
   - which balance addresses the contract writes to
3. **Confirm the existing tests are green before you change anything.** Run the existing unit and simulation suites and record the result. If they are already failing, stop and report that — you cannot attribute a regression to your change if the baseline is red.
4. **Snapshot the file.** Keep the pre-change content available (e.g. via version control) so you can produce and inspect a true diff in Step 6.

### 4. Impact Analysis (before writing code)

Write down the answers to these before editing. This is the step that separates a surgical update from an accidental rewrite.

- **Parameters**: Does the change add, remove, retype, or re-level (template vs instance) a parameter? Re-levelling and retyping are breaking changes for existing accounts.
- **Fetchers**: Does the new logic need balances, postings, parameters, or flags that the target hook does not currently fetch? Add them to that hook's `@fetch_account_data` and to the module-level `data_fetchers` via `distinct_fetchers`. A feature that reads data the hook never fetched fails at runtime, not at lint time.
- **Feature dependencies**: If you invoke feature A and feature A internally calls feature B, the hook must supply everything B needs too. Read the feature source — do not infer from its name.
- **State**: Does `state_utils.initialise_state` need new parameters or balances passed explicitly? Features that manage their own state append internally; features that do not (e.g. `principal`, `term`, secondary amortisation features) must be supplied.
- **Schedules**: Does the change add, retime, or remove an `event_type`? Changed schedule timing does not retroactively apply to already-scheduled events on live accounts.
- **Balance addresses**: Does the change introduce a new address, or stop writing to an existing one? Removing a writer strands any non-zero balance at that address.
- **Ordering**: If the contract uses `event_types_groups`, does the change alter the required execution order between schedules?
- **Downstream resources**: Which CLU resources (smart contract version, parameter definitions, flag definitions) must change to match? Note them for Step 8.
- **Blast list**: Enumerate the hooks and features you expect to touch. Anything you end up editing that is not on this list is a signal you have misjudged the change — stop and redo this analysis.

### 5. Migration Safety (mandatory if live accounts exist)

Smart Contracts are versioned and immutable once deployed. A change is not a find-and-replace on a running system; it produces a **new contract version** that existing accounts must be moved onto.

- **New version, not an in-place edit.** Bump the contract `version` per the project's convention. The old version continues to serve accounts until they are upgraded.
- **New parameters need a value for existing accounts.** A newly added template parameter needs a default in the CLU resource. A newly added *instance* parameter has no value on accounts that already exist — either supply one during the account update, or make the contract tolerate its absence. Never assume a new instance parameter is populated.
- **Removed parameters** must stay declared until every account is off the old version if any hook still reads them.
- **Retyped or re-levelled parameters** are breaking. Call this out explicitly to the user and confirm the migration approach before proceeding.
- **Schedules on existing accounts** are created at activation. Adding an `event_type` means live accounts have no such schedule until upgraded; changing a schedule's expression does not rewrite already-materialised events.
- **Corrective action for defect fixes (type D).** Fixing the logic does not repair accounts already affected by the bug. State plainly whether remediation postings or a back-dated correction are needed, and flag it — do not silently ship a forward-only fix for a defect with historical impact.
- **Record the outcome.** Summarise the migration implications in the change summary (Step 9) even when the answer is "none — no live accounts".

### 6. Implement the Minimal Diff

- **Edit in place.** Apply targeted edits to the existing file. Do not regenerate the contract from scratch and do not write a "v2" alongside it.
- **Preserve everything untouched**: existing import order and grouping, existing naming, existing helper signatures, existing comments, existing blank-line layout, and the existing style of untouched code — even where it differs from current convention.
- **Match the local idiom.** New code should be indistinguishable in style from the code around it. This overrides personal preference; consistency within the file wins.
- **Additive wiring uses the helpers.** When adding to module-level lists, extend the existing `distinct_expected_parameters(...)` / `distinct_fetchers(...)` calls rather than introducing a parallel list.
- **Prefer `feature_library` over bespoke code.** Before writing new logic, check `feature_library/src/feature_library/` for a feature that already does it. Reusing a library feature is a smaller and safer change than hand-rolling equivalent logic.
- **Removals must be complete.** When removing a feature (type C), also remove its now-unused parameters, fetchers, event types, imports, and state contributions. A partial removal that leaves an orphaned fetcher is worse than no removal — it costs performance and misleads the next reader.
- **Do not create empty hooks.** If a change empties a hook of real logic, delete the hook rather than leaving it returning a bare result object; empty hooks slow Vault Core down.
- **New code obeys current standards** (100-char lines, type annotations, functional idioms, sets for membership, `Decimal` rounded before `Posting` construction) even inside a legacy file. See `../create-smart-contract/SKILL.md` §§ 6–7.

**Then read your own diff.** Produce the actual diff (e.g. `git diff`) and walk it line by line. For every hunk ask: *which sentence of the change request requires this?* Revert any hunk that has no answer. Whitespace-only and import-reorder hunks are the most common offenders.

### 7. Verify — Regression First

Verification for an update is different from verification for a new contract. New behaviour working is the *second* thing you check.

1. **Regression: run the pre-existing test suite unchanged.** Every test that passed at Step 3 must still pass, with no edits to the test file. A pre-existing test that now needs modifying is either (a) a genuine, intended behaviour change that must be called out explicitly in the change summary, or (b) proof your change broke something. Treat it as (b) until you have positively established (a).
2. **New behaviour: add coverage for the change only.** Use the `create-sc-tests` skill to add unit and simulation tests for the new or modified behaviour. Add tests; do not rewrite the existing suite.
3. **Boundaries.** Cover the edges the change introduces: the parameter's new bounds, the first and last schedule run, zero and negative amounts, and the "parameter absent on a pre-existing account" case from Step 5.
4. **Lint.** Run the repo's configured linters/formatters (ruff, black, flake8, isort, mypy — whichever the project actually configures) and confirm the change introduces no new findings. Pre-existing findings in untouched code stay untouched.
5. **Adversarial gate.** Run the `adversarial-review` skill (`../adversarial-review/SKILL.md`) against the change. It checks the diff against the change request, validates that the new tests can actually fail, and confirms design-pattern conformance. Treat its verdict as a gate, not a suggestion.

### 8. Update Downstream Resources

A contract change is not complete until the things that reference it agree with it.

- **CLU resources**: use `../create-clu-resources/SKILL.md` to update the smart contract version resource, parameter definitions (including defaults for new template parameters), and any flag definitions the change adds or retires.
- **Documentation**: use `../explainer-skill/SKILL.md` to refresh the affected sections of the product documentation in `documentation/`. Regenerate only the parts the change affects — the same minimal-diff principle applies to docs.
- **REQUIREMENTS.md**: if the change alters the product's specified behaviour, update the requirements file so it continues to describe the shipped product. A change request applied to code but not to requirements guarantees the next update starts from a false baseline.

### 9. Report the Change

Produce a change summary containing:

- **Change type**: A/B/C/D/E and a one-line statement of intent.
- **Diff inventory**: every file touched, and for each, the hooks/features changed and why.
- **Behaviour preserved**: what you deliberately did *not* change, and the evidence (baseline suite green, unchanged).
- **Behaviour changed**: the before/after of each intended behavioural difference, including any pre-existing test that legitimately had to change.
- **Migration implications**: the Step 5 outcome, explicitly, even when it is "none".
- **Downstream resources updated**: CLU, docs, requirements.
- **Follow-ups**: unrelated issues spotted and deliberately left alone.

## Anti-patterns

Reject these in your own output:

- Regenerating the whole contract because it was faster than locating the change surface.
- Reformatting or re-sorting imports in a file you only needed to add one line to.
- Renaming an existing helper to a "better" name as part of an unrelated change.
- Editing an existing test until it passes, instead of investigating why it started failing.
- Adding a parameter without a default and without checking what existing accounts will do.
- Removing a feature's invocation but leaving its parameters and fetchers declared.
- Shipping a defect fix without stating whether already-affected accounts need remediation.
- Bundling an "obvious" second improvement into the diff because it seemed related.
