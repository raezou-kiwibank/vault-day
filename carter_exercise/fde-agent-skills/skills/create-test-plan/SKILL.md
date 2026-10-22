---
name: create-test-plan
description: Generate a structured test plan for a Thought Machine Vault smart contract or feature from requirements, acceptance criteria, and any existing tests. Use before writing tests, or when planning the test approach for a conversion or upgrade.
compatibility: Assumes the Inception SDK test framework (unit / simulation / e2e tiers) will be used to execute the plan.
audience: client
---

# Create Test Plan

This skill turns requirements into a test plan: every requirement traced to scenarios, each scenario
with the levels it will be tested at. It does not write test code; `create-sc-tests` does that.

## Workflow

### 1. Requirements Analysis

Read the requirements (normally `documentation/REQUIREMENTS.md` in the product directory) and any
examples of the expected behaviour. They are the foundation of the plan.

When the file comes from `clarify-requirements`, use its structure:
- **Acceptance criteria** (`AC-xx`, under each feature) are the criteria the plan must cover.
- **Decisions** (`D-xx`), **standing assumptions** (`A-xx`), **parameters**, the **Schedules Summary**
  and the **Lifecycle** are also covered by scenarios.
- **Build Approach** says, per feature, what is library code and what is custom code.
- **Open items** and the **Clarification log** (`Qn`) record what is already asked or owned.
- **Out of scope** and the **Change log** are not tested.

If the requirements use another structure, treat their stated rules, criteria and schedules as the
criteria and give each an ID in the plan.

### 2. Analyse other existing resources

If this is for a conversion or upgrade to an existing resource, analyse the current behaviour of the
existing resource and its available tests. Determine which scenarios they capture that are still
relevant to the new desired behaviour.

### 3. Check what the test framework can do

Before choosing levels, read the simulation documentation in
`../common-references/inception_sdk_documentation/` and note what simulation supports (for example
parameter changes mid-run, posting types, schedule control). Write scenarios to match.

The documentation does not list everything the framework can do. Where it is silent on something you need, check the installed `inception_sdk` package before you conclude that simulation cannot do it. Leave a hedge only where the documentation and the SDK source are both silent.

### 4. Generate the test plan

Make sure the plan includes:

- **A header** with the source: its path, the counts of decisions, assumptions and acceptance
  criteria, and the date. (`Source: …/REQUIREMENTS.md, 13 decisions, 10 assumptions, 41 acceptance criteria. Generated 2026-10-05.`)
- **The testing scope**, including what is not tested. Do not re-test the feature library's internals.
- **Scenarios.** Each has:
  - a stable ID, a concise summary, detailed steps and the expected outcome;
  - a type (core, edge or corner);
  - its **origin**: the `AC-xx` or `D-xx` it covers, or `added by planner`;
  - a **priority** (must, should or could);
  - a tag, `[library]` or `[custom]` (see below), and `depends: A-xx` if it rests on an assumption
    the user has not confirmed. Mark that outcome `provisional: <default>`;
  - its test levels.
- **A coverage table** that lists every acceptance criterion, decision, schedule and lifecycle
  transition with the scenarios that cover it, and ends with an explicit list of anything uncovered.
- **Open questions** (see below).
- **A Change log table** at the end of the file, starting with version 1 (`Version`, `Date`,
  `Author/Reviewer`, `Comment`), so that revisions append to it.

**Test levels.** The Inception SDK test framework is the assumed way to run the plan. Give each
scenario its levels like this:
- **Unit:** every scenario has a unit test. It checks the rule with injected inputs, typically per
  Python function. For behaviour that runs over time, unit-test the function that works out the
  outcome with explicit dates and balances.
- **Simulation:** every scenario also has a simulation test wherever the framework can do it. Useful
  for behaviour through time. If it cannot, say why in the scenario.
- **E2E:** only the most important end-to-end journeys and the integration points a simulator cannot
  prove. A run is expensive. Put them in their own group, give the reason for each, and treat them as
  a recommendation unless the requirements make them acceptance criteria.

**Scenario types and priorities.**
- **Types:**
  - **`core`**: nominal happy-path under standard operating conditions.
  - **`edge`**: boundary limit, threshold, or extreme value along a single variable (e.g. zero balance, full-balance withdrawal, off-by-one penny, rounding cutoffs, leap days).
  - **`corner`**: multi-variable interaction, simultaneous events, or schedule/state collisions (e.g. batch netting, pending authorisations active during accrual, DST midnight transitions, schedule execution order).
- **Priorities:**
  - **`must`**: directly validates an explicit requirement (`AC-xx`, `D-xx`) or core balance invariant.
    Hard release blocker; failing a `must` test fails `adversarial-review`.
  - **`should`**: validates boundary limits, operational assumptions (`A-xx`), or wiring robustness.
    Expected for production quality; does not immediately block an initial prototype.
  - **`could`**: probes corner cases, tie-breakers, or planner-added combinations. Lowest priority;
    never blocks delivery.
Introduce these type and priority definitions briefly under `## 2. Scenarios` before the first
scenario so readers of the plan understand how to interpret them.

**Choose scenarios with care.**
- Use the Build Approach. For library-owned behaviour, plan one scenario that shows the product wires
  it correctly (`[library]`). For custom code, plan the full boundary and corner set (`[custom]`).
  Add a scenario for each "Library behaviour to note".
- Give worked numbers for every calculated outcome. Include at least one scenario where the correct
  behaviour and the most likely wrong one give different results. If a case cannot be built end to
  end, say so and cover it at unit level with injected inputs.
- Do not restate the acceptance criteria. A scenario refers to its `AC-xx` and adds the set-up and
  levels. Add scenarios beyond the requirements (for example leap years or compounding) only where
  they find real defects, and tag them `added by planner`. Keep the plan proportional to the
  requirements.
- Identify edge and corner cases from the requirements and label them.

**Open questions.** Where the requirements are silent, list the gap under "Open questions" instead
of assuming an outcome. Do not repeat anything already under the requirements' Open items; treat
deployment values such as account IDs as test inputs. For each question:
- number it `Qn`, continuing the requirements' Clarification log (Q6, Q7, …);
- tag an owner, **Product** (loop back to `clarify-requirements`), **Technical** (settled in the
  build or simulation, and say how) or **Configuration** (needed before deployment);
- tag it **Blocking** (changes behaviour or the contract's shape) or **Non-blocking** (a test
  detail), with a proposed default and the stage that must close it;
- write it as a list item, for example `- **Q6 (Product, Blocking)**: …`.

**Resolving questions and non-default technical choices (Single Decision).**
When an open question is answered—for example, if the user or engineer provides a technical answer
different from the proposed default, or after a product loopback returns:
1. **Record in the test plan:** In the `## Open questions` section, update the question's status to
   `Resolved` and record the chosen approach:
   `- **Qn (Owner, Resolved)**: <Description>. *Resolution*: <chosen answer>. *Close at*: Closed.`.
2. **Update affected scenarios in place:** Update the scenario's steps and expected outcome to reflect
   the chosen resolution. Remove any `provisional: <default>` or `depends: Qn` markers. If the technical
   resolution enables or disables a test tier (such as confirming simulation feasibility), update the
   scenario's level tags.
3. **Do not alter document structure:** The section remains `## <N+4>. Open questions` (no renaming to
   `## Questions` and no subheadings). All questions stay as list items. Downstream skills
   (`create-smart-contract`, `create-sc-tests`) run in fresh sessions and read from disk.

#### Document Structure

Every generated test plan must follow this standard document structure:

```markdown
# <Product Name> — Test Plan

Source: <path/to/REQUIREMENTS.md>, <D count> decisions, <A count> assumptions, <AC count> acceptance criteria. Generated <YYYY-MM-DD>.

## 1. Testing scope

### 1.1 In scope
<Summary of functional capabilities, schedules, and parameters covered>

### 1.2 Not tested (Out of scope)
<Explicit list of excluded behaviour, out-of-scope items from requirements, and feature library internals>

---

## 2. Scenarios — <Feature 1: Name>

**Types and priorities guide:**
- **Types**:
  - `core`: nominal path under normal operating conditions.
  - `edge`: single-variable boundary limit, threshold, or extreme value (e.g. zero, full balance, off-by-one, rounding cutoff).
  - `corner`: multi-variable interaction, simultaneous events, or schedule/state collisions (e.g. batch netting, pending items during accrual, DST shifts).
- **Priorities**:
  - `must`: validates an explicit requirement (`AC-xx`, `D-xx`) or core balance invariant; release blocker.
  - `should`: validates boundary limits, operational assumptions (`A-xx`), or wiring robustness.
  - `could`: probes corner cases, tie-breakers, or planner-added combinations.

### <SCENARIO_ID> — <Concise Summary>
<!-- Scenario IDs must use prefix F<N>- (e.g. F1-01, F2-01) matching the feature in REQUIREMENTS.md, and X- (e.g. X-01) for contract shape and cross-cutting scenarios. -->
- **Origin**: <AC-xx / D-xx / added by planner> | **Priority**: <must / should / could> | **Tag**: <[library] / [custom]>
- **Levels**: Unit: <yes / no>, Simulation: <yes / no>, E2E: <yes / no>
- **Steps**: <Detailed sequence of actions, postings, or schedule triggers>
- **Expected Outcome**: <Specific outcome with worked numerical calculations, or provisional: <default>>

<!-- Repeat for each scenario in Feature 1 -->

---

<!-- Repeat ## Scenarios for each Feature (## 3 .. ## N) -->

---

## <N+1>. Scenarios — Contract shape and cross-cutting
<Scenarios covering contract metadata, lifecycle activation, parameter hierarchy, and ledger balance invariants>

---

## <N+2>. E2E recommendations
<High-priority end-to-end customer journeys and simulator-unprovable integration points, with rationale for each>

---

## <N+3>. Coverage table

### Acceptance criteria
| Criterion | Scenarios |
|---|---|
| <AC-xx> | <SCENARIO_IDs> |

### Decisions
| Decision | Scenarios |
|---|---|
| <D-xx> | <SCENARIO_IDs> |

### Standing assumptions
| Assumption | Scenarios |
|---|---|
| <A-xx> | <SCENARIO_IDs> |

### Schedules and lifecycle
| Item | Scenarios |
|---|---|
| <Schedule / Transition> | <SCENARIO_IDs> |

### Uncovered
<Explicit list of anything uncovered with rationale, or "None">

---

## <N+4>. Open questions
- **<Qn> (<Owner>, <Blocking / Non-blocking>)**: <Description>. *Default*: <proposed default>. *Close at*: <stage>.
<!-- If resolved: - **<Qn> (<Owner>, Resolved)**: <Description>. *Resolution*: <chosen answer>. *Close at*: Closed. -->

---

## Change log
| Version | Date | Author/Reviewer | Comment |
|---|---|---|---|
| 1 | <YYYY-MM-DD> | <author / reviewer> | Initial version. <counts: D, A, AC, scenarios by level, open questions> |
```

### 5. Documentation Persistence

You MUST persist the generated test plan to a markdown file:

- **Location**: Create or update a `documentation/` folder within the same directory as the resource being analyzed.
- **Filename**: Name the file `TEST_PLAN.md` (e.g., `src/<product>/documentation/TEST_PLAN.md`), matching the `REQUIREMENTS.md` convention.

### 6. Refreshing an existing plan

When the requirements have changed or questions are resolved:
- Keep scenario IDs stable. Never renumber or reuse one. Mark a withdrawn scenario `[Retired: reason]`
  and add new scenarios at the end of their group.
- When questions are answered (e.g. non-default technical choices): update their status to `Resolved`
  in `Open questions`, update affected scenarios' steps, outcomes and levels, and remove provisional tags.
- Update the header (date and counts), the coverage table and the open questions.
- Append a row to the `## Change log` table at the end of the file (it exists from version 1).
  Increment the version by one. The Comment states what changed: the scenario IDs added, changed,
  or retired, questions resolved, and the requirement IDs behind them (the requirements' Change log
  shows what moved).
- After writing, check that every cross-reference (IDs in the coverage table, the index and the
  scenarios) still points at a real scenario.

### 7. Report

In the reply, give the file path and the exact scenario counts: the total, the split by level, how
many are `added by planner`, and how many are `[library]` and `[custom]`. List anything uncovered and
the open questions by owner and by blocking status.

## Guardrails

- The test plan is a planning artefact: do NOT write test code in this skill.
  Test implementation is handled by the `create-sc-tests` skill.
- Follow the standard document structure: do not alter section order, omit sections, or invent
  ad-hoc schemas between runs. End every test plan with a `## Change log` table starting at version 1.
- Every acceptance criterion in the requirements MUST map to at least one
  scenario; call out any criterion you could not cover and why.
- Every scenario MUST have a unit test. E2E is only for the most important journeys.
- Do not invent behaviour: where requirements are silent, list the gap under
  an "Open questions" section instead of assuming an expected outcome.
- Resolved questions MUST be updated in the "Open questions" section and reflected in the affected
  scenarios, not left in ephemeral chat.
- Write the plan as a document, not a chat: no first-person wording, and no assumptions hidden
  inside scenarios or questions.
- Keep IDs stable: a scenario ID is never reused, even after a refresh. Scenario IDs MUST use the feature prefix from `REQUIREMENTS.md` (e.g. `F1-01`, `F2-01`) and `X-` for contract shape/cross-cutting (e.g. `X-01`).
