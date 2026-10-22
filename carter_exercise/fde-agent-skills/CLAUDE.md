# FDE Agent Skills

This repository contains AI agent skills that support work on Thought Machine Vault client projects. The skills follow the open [Agent Skills](https://agentskills.io/specification) standard (`SKILL.md` with YAML frontmatter) and work with Claude Code, Gemini CLI, OpenAI Codex, and Kiro.

The canonical skill directory is `skills/`. The `.agents/skills`, `.claude/skills`, and `.kiro/skills` paths are symlinks to it so each tool discovers the same skills without duplication.

If your tool does not auto-discover skills, read the relevant `skills/<name>/SKILL.md` before performing a matching task below.

## Skills overview

| Skill | Audience | Use when |
|---|---|---|
| [`clarify-requirements`](skills/clarify-requirements/SKILL.md) | client | An ambiguous business brief needs to become a reviewed `REQUIREMENTS.md` before any code is written. |
| [`create-smart-contract`](skills/create-smart-contract/SKILL.md) | client | Building a Vault Smart Contract one feature at a time from `REQUIREMENTS.md` and `TEST_PLAN.md`, starting from an `IMPLEMENTATION_PLAN.md`, using `feature_library` components. |
| [`update-smart-contract`](skills/update-smart-contract/SKILL.md) | client | Surgically changing part of an existing contract — add a feature, modify a behaviour, remove a feature, fix a defect — with a minimal diff. |
| [`create-sc-tests`](skills/create-sc-tests/SKILL.md) | client | Creating a unit/simulation/e2e test suite for a Smart Contract with the Inception SDK test framework. |
| [`create-test-plan`](skills/create-test-plan/SKILL.md) | client | Producing a structured test plan from requirements or an existing resource's behaviour. |
| [`code-reviewer`](skills/code-reviewer/SKILL.md) | client | Reviewing new or modified Smart Contract Python code for correctness, style, efficiency, and test coverage. |
| [`adversarial-review`](skills/adversarial-review/SKILL.md) | client | Gating delivery: verify every requirement is implemented, prove the tests can actually fail, run the suites, and check design-pattern conformance. |
| [`convert-clv3`](skills/convert-clv3/SKILL.md) | client | Converting an existing CLv3 Smart Contract to CLv4. |
| [`modernise-feature`](skills/modernise-feature/SKILL.md) | client | Refactoring legacy Smart Contract features to current `feature_library` conventions. |
| [`explainer-skill`](skills/explainer-skill/SKILL.md) | client | Generating business-readable documentation (Mermaid diagrams, plain-language summaries) for a contract or feature. |
| [`create-clu-resources`](skills/create-clu-resources/SKILL.md) | client | Designing and programmatically generating a standard, compliant CLU Configuration Pack (manifest, smart contract version, parameter definitions, and flags) for newly generated banking products. |
| [`vault-core-operator`](skills/vault-core-operator/SKILL.md) | client | Building Vault Core API flows and quickly creating customers, products, and accounts for demos. |
| [`common-references`](skills/common-references/SKILL.md) | client | Looking up authoritative Vault Contracts API or Inception SDK reference documentation (used by the other skills). |

Each skill directory also carries an `agents/openai.yaml` file providing display metadata for OpenAI Codex; other tools ignore it.

## Skill audience

Every `SKILL.md` declares an `audience` in its frontmatter, and it is required — there is no default, because guessing wrong either leaks internal tooling or withholds a skill the client needs.

- **`client`** — shipped to clients as part of the distributable skill pack.
- **`internal`** — Thought Machine only. Depends on internal infrastructure, credentials, or repositories that a client cannot reach, and must never appear in a client bundle.

## The delivery pipeline

For a **new product build**, the skills chain together:

```
clarify-requirements -> create-test-plan
        -> for each feature: create-smart-contract -> create-clu-resources -> create-sc-tests
        -> code-reviewer -> adversarial-review -> explainer-skill
```

Features are delivered one at a time, so that each can be tested and validated by business stakeholders in its own sprint. `create-smart-contract` writes `IMPLEMENTATION_PLAN.md` on its first run, then implements one feature per run and returns control to the user. A feature goes through `create-smart-contract`, `create-clu-resources` and `create-sc-tests` before the next feature starts.

For a **change to a contract that already exists**, use the shorter, surgical path — do not re-run `create-smart-contract` over a working contract:

```
update-smart-contract -> create-sc-tests (new behaviour only) -> create-clu-resources
        -> adversarial-review -> explainer-skill
```

For a CLv3 migration, `convert-clv3` orchestrates the same downstream skills.

### Create vs update

`create-smart-contract` builds a contract from requirements, one planned feature at a time; success is "the feature is implemented and the features delivered before it did not move". `update-smart-contract` changes part of an existing contract; success is "the change is implemented **and nothing else moved**". Regenerating a live contract discards the reviewed, tested behaviour around it, so reach for `update` whenever a feature that has been delivered must change.

### Review vs gate

`code-reviewer` is a collaborative craftsmanship review that asks how the code could be better. `adversarial-review` is a release gate that assumes the work is wrong until evidenced: it traces every requirement to an implementing line and a test that can genuinely fail, executes the suites, and returns a PASS / CONDITIONAL / FAIL verdict. Run the reviewer to improve code; run the gate to decide whether it ships.

## Conventions

- Generated product documentation and test plans are written to a `documentation/` folder next to the resource being analysed.
- Requirements are captured in `REQUIREMENTS.md`, test plans in `TEST_PLAN.md` and implementation plans in `IMPLEMENTATION_PLAN.md`, all in the product's `documentation/` folder (e.g. `src/<product>/documentation/REQUIREMENTS.md`, `src/<product>/documentation/TEST_PLAN.md` and `src/<product>/documentation/IMPLEMENTATION_PLAN.md`).
- Reference documentation lives in `skills/common-references/` and is addressed by skills via paths relative to their own directory (`../common-references/...`). Keep the `skills/` tree intact when installing.

## Environment prerequisites

Most skills assume a Vault client workspace providing:

- the `feature_library` source tree,
- the Inception SDK (`inception_sdk`) and its test framework,
- Vault Contracts API documentation matching the client's Vault version (this repo currently bundles `vault-5-9`).

Each skill declares its specific requirements in the `compatibility` field of its frontmatter.
