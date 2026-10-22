---
name: create-smart-contract
description: Build a Thought Machine Vault smart contract one feature at a time from REQUIREMENTS.md (and TEST_PLAN.md when it exists), using feature_library components. Writes an IMPLEMENTATION_PLAN.md first, then implements the feature the user chooses and returns control. Use after requirements have been clarified.
compatibility: Requires a Vault client workspace with the feature_library source tree. Reference documentation bundled for Vault 5.9.
audience: client
---

# Create Smart Contract

This skill builds a product's Smart Contract one feature at a time, using `feature_library` components. The first run writes an implementation plan for the whole product. Every run then implements one feature and returns control to the user. Features are delivered this way: each one is implemented, tested and validated by business stakeholders before the next one starts.

It builds the next planned feature of a product that is being delivered. When a feature that has already been delivered must change, use `update-smart-contract` instead. A feature is delivered once its tests pass and the business stakeholders have validated it. Until then it is still in its own delivery loop: when `create-sc-tests` reports a defect in it, this skill fixes it (see Fixing a Feature After Its Tests Failed).

## Workflow

### 1. Inputs and Orientation

- **Requirements**: `documentation/REQUIREMENTS.md` in the product directory. It is required. Each feature carries a Build Approach that is the starting point for the plan (see step 3). If the requirements are not provided, ask the user which features the product needs.
- **Test plan**: `documentation/TEST_PLAN.md` in the same folder. Use it when it exists and say so if it does not. It holds the agreed scenarios, worked examples and edge cases, and tags each scenario `[library]` or `[custom]`. Use them to shape the implementation. Do not implement behaviour that only a scenario asks for: where a scenario and the requirements disagree, raise a question.
- **Product layout**: follow the project's own layout (check its `AGENTS.md`/`README.md`; ask the user if unclear). In the standard client template the contract is `src/<product>/contracts/template/<product>.py`, and `src/<product>/contracts/<product>_rendered.py` is build output that stays empty (see Static Checks). If the user gives an output path, use it.
- **Existing state**: if `documentation/IMPLEMENTATION_PLAN.md` exists, read it and the contract written so far. This is a later run: refresh the plan if its source stamp no longer matches the requirements or the test plan (see Refreshing the plan), then go to step 4. Otherwise this is the first run: continue with step 2.

### 2. Smart Contract Reference Documentation

**Versions**: Never assume the target. Before any other work on the first run, you MUST know the **Vault version** (e.g. 5.9) the product targets. It decides which reference documentation and implementation standards apply, and it cannot be inferred from the project's installed packages. The Contracts API version is not a question: every contract this skill builds uses Contracts API 4 (CLV4).
- If the requirements name the Vault version, use it and say so.
- Otherwise ask the user, and wait for the answer. In the question, say that the bundled documentation covers Vault 5.9 (`vault-5-9/`) and give the `contracts-api` and `feature_library` versions installed in the project, so the user can see any difference.
- If the answer is a version the bundled documentation does not cover, say so and let the user decide how to proceed. Do not substitute another version silently.
- If the requirements or the user ask for CLV3, say that this skill builds CLV4 only and let the user decide how to proceed. Do not build a CLV3 contract.
- Record the Vault version in the plan header with its source (requirements or user), next to the installed `contracts-api` and `feature_library` versions. On later runs, use the version recorded there.

**STRICT MANDATE**: Always consult the authoritative reference documentation in `../common-references/contracts_api_documentation/vault-<version>/` for the specific Vault version being used (e.g., `vault-5-9/`). Note that the `common-references` folder is located in the same parent `skills/` directory as this skill folder. You MUST strictly verify methods and parameters of objects (e.g., the `vault` object)—NEVER guess method names, signatures, or parameters.

This skill builds every contract with Contracts API 4 (also known as **CLV4**, short for Contracts Language Version 4), so use only the V4 documentation:

- Base Path: `../common-references/contracts_api_documentation/vault-<version>/contracts_api_4xx/`

Key V4 reference paths:

- **Smart Contract Metadata**: Required fields, versioning, and status.
  - Path: `../common-references/contracts_api_documentation/vault-<version>/contracts_api_4xx/smart_contracts_api_reference4xx/metadata/`
- **Supervisor Metadata**: Metadata fields specific to Supervisor contracts.
  - Path: `../common-references/contracts_api_documentation/vault-<version>/contracts_api_4xx/supervisor_contracts_api_reference4xx/metadata/`
- **Allowed Python Built-ins**: The definitive set of standard functions permitted in the sandbox.
  - Path: `../common-references/contracts_api_documentation/vault-<version>/contracts_api_4xx/common_types_4xx/builtins/`
- **Native Imports**: Permitted standard library and third-party modules (e.g., `math`, `datetime`, `decimal`).
  - Path: `../common-references/contracts_api_documentation/vault-<version>/contracts_api_4xx/common_types_4xx/native_objects/`
- **Contracts API Types**: Full class definitions, attributes, and methods (e.g., `Balance`, `Parameter`, `ScheduledEvent`).
  - Path: `../common-references/contracts_api_documentation/vault-<version>/contracts_api_4xx/common_types_4xx/classes/`
- **Enumerations**: All available API enums (e.g., `Tside`, `Phase`, `PostingInstructionType`).
  - Path: `../common-references/contracts_api_documentation/vault-<version>/contracts_api_4xx/common_types_4xx/enums/`
- **Vault Object API**: Methods and attributes available on the `vault` object for each hook.
  - Smart Contracts: `../common-references/contracts_api_documentation/vault-<version>/contracts_api_4xx/smart_contracts_api_reference4xx/vault/`
  - Supervisor Contracts: `../common-references/contracts_api_documentation/vault-<version>/contracts_api_4xx/supervisor_contracts_api_reference4xx/vault/`
- **Hook Definitions**: Detailed requirements and logic execution for each hook.
  - Smart Contracts: `../common-references/contracts_api_documentation/vault-<version>/contracts_api_4xx/smart_contracts_api_reference4xx/hooks/`
  - Supervisor Contracts: `../common-references/contracts_api_documentation/vault-<version>/contracts_api_4xx/supervisor_contracts_api_reference4xx/hooks/`
- **Decorators**: Usage and arguments for `@fetch_account_data` and `@requires`.
  - Path: `../common-references/contracts_api_documentation/vault-<version>/contracts_api_4xx/common_types_4xx/decorators/`

#### Disallowed Python Types and functions
Despite what is listed in the reference documentation, the following are strictly prohibited in all Smart Contract code:
- `class` keyword
- `collections.abc` package or any types contained therein
- `dataclass` decorator
- `datetime.strftime()` function
- `datetime.strptime()` function
- `date` constructor, although `datetime.date()` function is allowed
- `date` import statement and type annotation
- `except` keyword, unless it is a bare `except`, that is, without a class name following
- `hasattr` keyword
- `isinstance` keyword
- `raise` keyword
- `re` package or any types contained therein
- `type` keyword

### 3. Implementation Plan

On the first run, write the plan for the whole product before any code. The plan says, feature by feature, which Vault resources will enable the scenarios in the requirements. It is a document for people to review, so keep it mostly in prose.

**Analyse the requirements** against the available features in `feature_library/src/feature_library/` (in a client workspace this is usually the installed `feature_library` package). Using the requirements identify whether it is a lending or deposit product and use the correct set of relevant features. Common features can be used for all products. Identify the necessary interfaces and secondary features. The requirements already give a Build Approach for each feature: the approach (`Library`, `Mixed` or `Custom`), the library module, the custom code needed and any library behaviour to note. Use it as the starting point for the plan instead of choosing the composition again. Check it against the installed source, because an entry marked `not checked` was never verified and the installed version may differ from the one it was written against. Where the installed source or the requirements show it to be wrong or incomplete, depart from it and say why under Decisions.

**Think about Vault resources.** For each feature, think through which of these it needs. The list is a starting point, not the full set: consult the reference documentation (section 2) for what exists and for exact names, and never guess.
- **Parameters**: an `ExpectedParameter` for each value the contract reads, with its shape, its level (template or instance), and any validation it needs.
- **Balance addresses and phases**: the addresses the feature reads or writes (`DEFAULT` or a custom address), and the denomination or asset.
- **Data fetchers**: what each hook has to read (balances, parameters, flags, calendars, postings or last scheduled event times), through the optimised fetchers declared with `@fetch_account_data`.
- **Hooks**: which hooks run the feature (`activation_hook`, `pre_posting_hook`, `post_posting_hook`, `scheduled_event_hook`, the parameter-change hooks, and so on) and what each one does.
- **Schedules**: the event types, how they are scheduled on activation, and how they are dispatched.
- **Posting instructions**: the instruction types the feature creates or accepts (for example custom instructions, inbound and outbound hard settlements, transfers, authorisations, settlements and releases) and any posting metadata (`instruction_details`).
- **Flags**: flag definitions the feature reads, or that change its behaviour.
- **Rejections and notifications**: the rejection reasons it returns, and any account or plan notifications it emits.

**Resolve what the requirements leave open** in this order, and record the source in the plan:
1. what the user said (the requirements, the test plan and the conversation);
2. what the installed `feature_library` does: read its source and name the version;
3. standard Vault platform behaviour (`../common-references/`);
4. only if none of these defines it, an open question with the simplest option as the proposed default.

Business values (rates, limits, amounts, account IDs) never come from the library: they stay `TBC`, as in the requirements. Where library behaviour would contradict an acceptance criterion or a confirmed decision, raise a Product question instead of choosing silently. Library behaviour the business is likely to find surprising is written up as a decision for review.

**Plan rules.**
- One section per feature, with the same names and order as in `REQUIREMENTS.md` and the scenario groups in `TEST_PLAN.md`, so each feature traces to both.
- Mostly prose. Pseudocode and diagrams are encouraged where they make the design clearer: for example pseudocode for custom logic or for the order a hook runs its checks, and Mermaid flowcharts or sequence diagrams for schedules, posting flows and hook interactions. Use pseudocode, not contract Python, so the plan does not become a first draft of the implementation.
- Do not restate acceptance criteria, parameter tables or formulas: refer to them by ID. Name the Vault resources and the library function behind each. For custom code, say what it does and why the library cannot. Name the shared definitions and hooks the feature touches.
- Decisions are numbered `I-xx` and carry a source: `user`, `feature_library <version>`, `Vault docs` or `proposed default`. Questions are numbered `Qn`, continuing the highest number in the requirements' Clarification log and the test plan's Open questions. Each has an owner (Product, Technical or Configuration), a Blocking or Non-blocking tag, a proposed default and the stage that closes it.
- Write it as a document: no first-person wording. Keep it proportional: a one-feature product gets a one-feature plan.
- After writing, check that every acceptance criterion, decision, assumption, schedule and lifecycle step appears in the Traceability table, and list anything that does not under Uncovered.

#### Document Structure

Every plan follows this structure. Do not change section order or headings between runs.

````markdown
# <Product Name> — Implementation Plan

Source: <path/REQUIREMENTS.md> v<n>, <path/TEST_PLAN.md> v<n> (or "no test plan"). Target: Vault <version> (source: requirements | user), Contracts API 4; installed contracts-api <version>, feature_library <version>. Generated <YYYY-MM-DD>.

## Overview
<Prose: deposit or lending, tside, denomination; what comes from the library and what is custom; the recommended build order and why. A Mermaid diagram of the hooks and schedules across the product is welcome here.>

## Foundation
<Prose: the shared contract definition built with the first feature: metadata, tside, denomination, shared parameters and fetchers, time zone.>

## Features

### Feature 1: <Name, as in REQUIREMENTS.md>
**Covers**: <AC-xx–AC-xx, D-xx, A-xx> · **Scenarios**: <TEST_PLAN IDs> · **Build approach**: Library | Custom | Mixed · **Depends on**: <features, or "Foundation"> · **Status**: Planned
<Prose, one to three short paragraphs: which Vault resources enable the feature (parameters, balance addresses, data fetchers, hooks, schedules, posting instruction types and metadata, flags, ...) and which library function supplies each. For custom code: what it does and why the library cannot. The shared definitions and hooks the feature touches.>
<Where it helps: pseudocode for custom logic or hook order, and a Mermaid diagram of the schedule, posting or hook flow.>
**Decisions**: <I-xx — decision (source: user / feature_library <version> / Vault docs / proposed default)>

### Feature 2: ...

## Traceability
| Requirement (AC, D, A, schedule, lifecycle) | Feature |
|---|---|
| <ID> | <Feature name> |

Uncovered: <list, or "None">

## Open questions
- **<Qn> (<Product / Technical / Configuration>, <Blocking / Non-blocking>)**: <description>. *Default*: <proposed default>. *Close at*: <stage>.

## Change log
| Version | Date | Author/Reviewer | Comment |
|---|---|---|---|
| 1 | <YYYY-MM-DD> | <author / reviewer> | Initial version. <counts: features, decisions, open questions> |
````

Each `v<n>` in the source line is the last row of the Change log of the file named before it.

**Persistence.** Write the plan to `documentation/IMPLEMENTATION_PLAN.md` in the product directory, next to `REQUIREMENTS.md` and `TEST_PLAN.md`.

#### Refreshing the plan

When the requirements or the test plan have changed, or questions have been answered:
- Update the affected feature sections in place. Keep `I-xx` and `Qn` stable: never renumber or reuse one.
- Resolved questions become `Resolved`, with the chosen answer, and the affected prose changes to match.
- Update the source stamp, Traceability and Open questions, and append a Change log row that says what changed and which requirement IDs are behind it.
- If a feature that is already `Implemented` is affected, mark its status `Needs update`. The code change itself is made with `update-smart-contract`.

### 4. Choose the Feature

- If the request is to fix a feature that `create-sc-tests` reported as failing (the user, or `create-sc-tests` itself, names the failing scenarios or tests, or passes its report), this is not a new feature. Follow Fixing a Feature After Its Tests Failed, after step 9, and skip the rest of this step.
- If the request names what to build (a feature, several features, or the whole contract), build that, in plan order, and carry on to step 5, running steps 5 to 9 for each feature in turn. The plan has already been written and saved, so the user can review it afterwards.
- Otherwise stop here. On the first run, give the path of the plan, summarise it, and ask the user to review it, applying any changes they want in place (see Refreshing the plan). On later runs, say what was refreshed, if anything. Then recommend a feature, say why, and ask which one to build. The user may choose any feature. The recommendation: the feature that other features depend on or, among features that do not depend on each other, the smallest self-contained one, so the first review is quick. If the user picks a feature whose dependencies are not implemented yet, say what it needs and let them decide.
- Ask the Blocking questions that concern the chosen feature now, with their proposed defaults. Non-blocking questions go ahead on their default.

### 5. Implementation

Implement the chosen feature in full, following its plan section. On the first feature, also build the Foundation so that the module loads. Write the whole feature (parameters, fetchers, event types, hooks and the helper functions they call) before running any check: a half-written feature does not lint.

**Adding to a contract that already holds features.** Earlier features have been validated by stakeholders and, usually, have tests. Add the new feature's entries to the shared definitions and hooks. Do not rewrite or reorder what an earlier feature put there, and change nothing in it unless the plan says so. If you must change earlier lines, say which and why in the report.

- Where you need classes, enums etc. from the contracts_api import
- **Top-Level Definitions**: Define Smart Contract metadata like `expected_parameters`, `data_fetchers`, and `event_types` at the top of the file as module-level lists, combining the corresponding lists from the imported features. You MUST use the `distinct_expected_parameters` and `distinct_fetchers` helper methods from `feature_library.common.parameter_utils` and `feature_library.common.fetchers` respectively when defining these at the module level. Do NOT return these inside hooks (like `event_types_hook` which is deprecated). You can look at the metadata section in the documentation to identify the different metadata options.

    ```python
    from feature_library.common.fetchers import distinct_fetchers
    from feature_library.common.parameter_utils import distinct_expected_parameters

    expected_parameters = distinct_expected_parameters(
        feature_a.expected_parameters + feature_b.expected_parameters
    )
    data_fetchers = distinct_fetchers(
        feature_a.data_fetchers + feature_b.data_fetchers
    )
    ```

- **Implementation Checklist**:
  - **Fetcher Consolidation**: Ensure ALL fetchers required by features (e.g., `PRINCIPAL_ET_BOF_ID`) are included in the contract's top-level `data_fetchers` list. Use the `distinct_fetchers` helper to ensure they are unique.
  - **Decorator Accuracy**:
    - `@fetch_account_data` for `attribute_hook` MUST include the `attribute_name` keyword.
    - `activation_hook` decorators MUST NOT include the `balances` keyword (only `parameters` and `calendars` are allowed).
  - **Dependency Awareness**: If Feature A calls Feature B (e.g., `due_amount_calculation` calling `declining_principal`), ensure the hook calling Feature A fetches and initializes state with all parameters required by Feature B.
- **Hook Definitions**:
  - Use `@fetch_account_data` decorators on hooks (`activation_hook`, `pre_posting_hook`, `scheduled_event_hook`, etc.) to specify the required parameters and balances. This ensures the data is available in the `vault` object before the hook logic runs.
  - When using `@fetch_account_data` for a `scheduled_event_hook`, use the `event_type` argument to scope the data fetching to specific events.
  - **Omit Empty Hooks**: Do NOT include hooks in the smart contract that only return a default result object (e.g., `return DeactivationHookResult()`) without any actual logic or state manipulation. These are redundant.
  - **Attribute Hook Pattern**:
    - Use multiple `@fetch_account_data` decorators, each specifying a single `attribute_name`. This ensures only the data required for each specific attribute is fetched.
    - Inside the hook, use `hook_arguments.attribute_name` to determine which attribute is being requested and execute only the relevant logic.
    - Return `AttributeHookResult(attribute_value=...)` for the specific requested attribute.

    ```python
    @fetch_account_data(
        attribute_name=feature_a.ATTR_ID,
        parameters=[...],
        balances=[...]
    )
    @fetch_account_data(
        attribute_name=feature_b.ATTR_ID,
        parameters=[...],
        last_scheduled_event_datetimes=[...]
    )
    def attribute_hook(
        vault: SmartContractVault, hook_arguments: AttributeHookArguments
    ) -> AttributeHookResult | None:
        requested_attribute = hook_arguments.attribute_name

        if requested_attribute == feature_a.ATTR_ID:
            # logic for feature_a
            return AttributeHookResult(attribute_value=value_a)

        elif requested_attribute == feature_b.ATTR_ID:
            # logic for feature_b
            return AttributeHookResult(attribute_value=value_b)

        return AttributeHookResult()
    ```

- **State Initialization in Hooks**:
  - When initializing state in hooks using `state_utils.initialise_state`, explicitly pass the balances retrieved via `@fetch_account_data` to the `initialise_state` call.
  - **Avoid Redundant Parameters**: Do NOT add parameters to the `initialise_state` call if they are already internally managed and appended to the state within the feature functions you are invoking (e.g., features that call an internal `_append_to_state` helper).
  - **Include Required Secondary Parameters**: You MUST explicitly include parameters in the `initialise_state` call if they are required by features that DO NOT internally manage their own state (e.g., `principal`, `term`, or secondary amortisation features like `declining_principal`). Always check the implementation of the features you are calling to see if they rely on parameters that they don't explicitly fetch themselves.

  ```python
    @fetch_account_data(
        parameters=[denomination.DENOMINATION_ET_POF_ID, principal.PRINCIPAL_POF_ID],
        balances=[fetchers.ALL_BALANCES_ET_BOF_ID]
    )
    def some_hook(vault: SmartContractVault, hook_arguments: SomeHookArguments):
        # Parameters like those for 'some_feature' are NOT passed here if
        # 'some_feature.some_function' appends them to state internally.
        # However, 'principal' MUST be passed if 'some_secondary_feature' needs it but doesn't fetch it.
        state = state_utils.initialise_state(
            vault=vault,
            effective_datetime=hook_arguments.effective_datetime,
            parameters={
                **denomination.get_parameters(vault),
                **principal.get_parameters(vault),
            },
            balances=vault.get_balances_observation(fetcher_id=fetchers.ALL_BALANCES_ET_BOF_ID).balances
        )
        # some_feature.some_function(state=state)
  ```

- **Event Types Groups**: If the contract has multiple related schedules that must run in a specific order, define `event_types_groups` using `EventTypesGroup`.
- **Tside**: Ensure `tside` is set appropriately at the module level (e.g., `tside = Tside.LIABILITY` for deposits).

### 6. Performance Considerations
Do not create empty hooks, as these cause Vault Core to run more slowly.
Avoid O(N log N), O(N^2), O(2^N), or O(N!) algorithmic complexity wherever possible.
Use Function Programming idioms such as Python comprehensions, map, filter, and sum, instead of Imperative ones such as `for` loops.
Use Generator comprehensions and Generator functions where possible, to permit lazy evaluation and avoid allocating memory needlessly.
Use Python sets to check membership instead of Python lists.
Use NamedTuples to organise frequently-used variables such as vault, parameters, balances, custom_instructions, and notifications.

### 7. Coding Conventions
Maximum line length is 100 characters, unless the repo configures another. Run the repo's formatter rather than adjusting line lengths by hand. For lines it cannot shorten, such as long import statements and unsplittable string literals, mark them with a comment `# noqa: E501` at the end.
Use type annotations liberally, unless the type is obvious, such as string literal initialisations, integer/Decimal initialisations, or object initialisations via a constructor.  Take care to type `dict`s with as much detail as possible.
Organise imports under the following commented headings:
   1. standard libs
   2. third party
   3. features
   4. contracts api
   5. inception sdk
Import each Python type by name, do not use bulk * imports, as these are disallowed in the contracts language.

Use the linters and code formatter tools configured in the local repo (e.g. ruff, black, flake8, isort, mypy) — check what is installed and follow the repo's own configuration.

### 8. Static Checks

Run the checks once per feature, after the feature is fully written, not after each edit. Use the repo's own tooling, and find it before running anything: look at the makefile or task runner, the project config (`pyproject.toml` or equivalent), the CI workflow, and any README or agent instructions. The client template wraps its checks in `make format`, `make check` and `make scan`, but a repo that did not start from the template may use different tools, commands and config, so treat those as an example. The steps below say what each check is for, not which tool must run it. If the repo has no tool for a check, say so in the report. Do not install tools, and do not change the repo's lint, type or build config to make a check pass.

1. Format and lint the product directory with the repo's formatter and linter, and fix what is reported.
2. Type-check it with the repo's type checker.
3. Run the Smart Contract scan, or any other contract-specific check, that the repo configures, if there is one.
4. Render to validate. Render the template with the Inception SDK renderer, using the repo's own render command if it has one, and check the output against the disallowed list in section 2. The renderer is `inception_sdk.tools.renderer.main`, for example `uv run python -m inception_sdk.tools.renderer.main --input_template=<template> --output_filepath=<scratch path> --force --nouse_git --nouse_full_filepath_in_headers`, with the runner adjusted to how the repo runs Python. Rendering inlines the feature library, so the output is thousands of generated lines and breaks lint and type checks that scan it. Write it to a scratch path that the repo's linters, type checkers and version control do not pick up (the gitignored `build/` in the client template, or a temporary directory outside the repo). If the repo keeps a rendered file for the product, leave it as you found it, never edit it by hand, and confirm afterwards that it is unchanged. In the client template that file is `contracts/<product>_rendered.py`, which is an empty placeholder for build output that `create-clu-resources` includes at packaging.
5. Run the repo-wide checks, meaning the full lint, type and scan targets, or whatever CI runs. Each feature is delivered on its own and must leave the repository clean.
6. If tests from earlier features exist, run their unit and simulation tests (not e2e) with the repo's test command. A failure caused by this feature is fixed in the contract, never by editing the tests. If a simulation test cannot reach Vault (the environment config is missing or invalid, the connection is refused, or authentication fails), do not work around it: report those tests as not run and say that the user needs to set up the connection to a Vault Core environment.

A pass here is not a behavioural test of the new feature, which has no tests yet. Say so in the report.

### 9. Update the Plan and Report

- Update `IMPLEMENTATION_PLAN.md` in place: set the feature's Status to `Implemented` with the date and the static-check result (and any check that could not run), record decisions made during the build (`I-xx`) and new questions (`Qn`), correct any prose that no longer matches what was built, update Traceability if it changed, and append a Change log row. Write no other documentation in this skill.
- Report: the feature built, the files changed, the Vault resources it added or changed, the result of each check, any lines changed in earlier features, the open questions raised, that the feature has no tests yet, and the features still `Planned`.
- Then say that the feature is implemented and return control to the user. Say that the usual next step is `create-clu-resources` for this feature. Start nothing.

## Fixing a Feature After Its Tests Failed

Use this when the request is to fix a feature that `create-sc-tests` reported as failing (see step 4), whether the user makes it or `create-sc-tests` makes it as part of its fix rounds. Steps 5 to 8 apply, with these changes.

1. **Find the feature and the evidence.** Take the feature from the `Scenarios` line of its plan section. Read each failing scenario in `TEST_PLAN.md` (its steps and expected outcome), the `AC-xx` or `D-xx` it comes from in `REQUIREMENTS.md`, and the report's diagnosis (expected against actual).
2. **Confirm that the contract is what is wrong.** The expected values come from the plan, and the tests are not yours to change. If the contract differs from what the requirement asks for, fix the contract. If the scenario's expected outcome contradicts the requirements or a recorded decision, the test plan is wrong: change nothing, say so, and recommend revising the scenario with `create-test-plan`. If you cannot tell, give both readings and ask.
3. **Fix, do not rebuild.** Change only the lines the failing scenarios implicate, in this feature's code and the shared definitions it touches. Do not rewrite the feature, do not touch other features, and never edit a test or its expected values.
4. **Check.** Run the static checks in step 8 as for a new feature. Also run the failing tests named in the report: they and every earlier test must now pass. If your fix makes a test that passed before fail, or the failing tests still fail with the same message, stop and do not edit again. Two scenarios that cannot both pass for the same inputs contradict each other: report both scenario IDs as a test plan defect and recommend revising them with `create-test-plan`.
5. **Update the plan and report.** The Status stays `Implemented`. Append a Change log row that names the scenario IDs and what was wrong, add an `I-xx` decision if you had to choose between readings, and correct any prose that no longer matches the contract. Report what was wrong, the lines changed, the tests that now pass, and the evidence that earlier features did not move. If the fix added, removed or changed a parameter, a schedule or another Vault resource, say that the CLU pack for this feature is out of date and that `create-clu-resources` is the next step. Otherwise the next step is `create-sc-tests` for this feature. Return control. Start nothing. When `create-sc-tests` called this section, the report goes back to it, and it decides what happens next.

## Guardrails

- Build only the feature or features chosen. Do not start the next feature, and do not start any other skill.
- Prefer composition over novelty: use `feature_library` components, and write custom code only where the plan says the library cannot, with the reason.
- Never invent a business value, and never hard-code one that belongs to a parameter.
- Never make a check pass by removing behaviour: a hook, a parameter, a fetcher or a library import.
- Follow the standard plan structure. Keep `I-xx` and `Qn` IDs stable. Write the plan as a document, not a chat.
