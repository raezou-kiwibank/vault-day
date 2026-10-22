# FDE Agent Skills

AI agent skills that support work on Thought Machine Vault client projects.

The skills follow the open [Agent Skills](https://agentskills.io/specification)
standard (`SKILL.md` directories), so a single copy of this repository works
with **Claude Code, Gemini CLI, OpenAI Codex, and Kiro**. See
[AGENTS.md](AGENTS.md) for the skill index and conventions.

## Installation

### Option 1 — clone into your project (all tools)

Clone (or vendor) this repository inside your project workspace. The repo
ships redirects for every supported tool:

| Tool | Discovery path | Provided by |
|---|---|---|
| OpenAI Codex | `.agents/skills/` | symlink → `skills/` |
| Gemini CLI | `.agents/skills/` | symlink → `skills/` |
| Claude Code | `.claude/skills/` | symlink → `skills/` |
| Kiro | `.kiro/skills/` | symlink → `skills/` |

`AGENTS.md` is the shared context file; `CLAUDE.md` and `GEMINI.md` are
symlinks to it.

> **Windows**: git must be configured with `core.symlinks=true` (requires
> Developer Mode). Otherwise use WSL, or copy `skills/` into each tool's
> skills directory.

### Option 2 — user-scope install (all tools, all projects)

```shell
git clone <this-repo> && cd fde_agent_skills
./install.sh
```

This symlinks every skill into `~/.agents/skills`, `~/.claude/skills`, and
`~/.kiro/skills`. Pull the repo to update; run `./install.sh --uninstall` to
remove.

### Option 3 — Gemini CLI extension

The repo remains a Gemini CLI extension (skills are auto-discovered from
`skills/`):

```shell
gemini extensions install git@github.com:thought-machine-external/fde_agent_skills.git
```

Add `--auto-update` to keep it current, or update manually:

```shell
gemini extensions update fde-agent-skills
```

## Using the skills

Skills activate in two ways: **implicitly** (the agent matches your request
against each skill's description) or **explicitly** (you name the skill).
The full skill catalogue and the recommended delivery pipeline are in
[AGENTS.md](AGENTS.md).

| Tool | List installed skills | Invoke explicitly |
|---|---|---|
| Claude Code | `/` shows skills as slash commands | `/clarify-requirements ...` |
| OpenAI Codex | `/skills` | `$clarify-requirements` mention, or describe the task |
| Gemini CLI | `/skills list` (enable/disable with `/skills enable <name>`) | describe the task; skills load on demand |
| Kiro | skills listed in the agent panel | `/clarify-requirements` |

Each skill directory also ships an `agents/openai.yaml` with Codex display
metadata, including whether the skill may be invoked implicitly. Skills with
side effects beyond the workspace — cloning repositories, installing
dependencies — and skills that act as release gates have implicit invocation
disabled; call those by name.

### Typical flow for a new product build

1. `clarify-requirements` — produce a reviewed `REQUIREMENTS.md`.
2. `create-test-plan` — agree what will be tested.
3. `create-smart-contract` — plan the product in `IMPLEMENTATION_PLAN.md`, then build the contract one feature at a time from `feature_library` components. Repeat steps 3 to 5 for each feature.
4. `create-clu-resources` — design and generate standard, compliant CLU resource files.
5. `create-sc-tests` — implement the unit/simulation/e2e suites.
6. `code-reviewer` — review before raising a PR.
7. `adversarial-review` — gate delivery: requirements traced, tests proven able
   to fail, suites executed, verdict returned.
8. `explainer-skill` — generate business-facing documentation.

### Changing a contract that already exists

Use `update-smart-contract` instead of re-running `create-smart-contract`. It
makes a surgical, minimal diff and verifies the pre-existing suite still passes
untouched, so reviewed behaviour around the change is not discarded:

```
update-smart-contract → create-sc-tests (new behaviour only)
    → create-clu-resources → adversarial-review → explainer-skill
```

## Verifying your installation

After installing by any option above:

1. **Check discovery** — start your tool inside the project and list skills
   (see table above). You should see the full catalogue from
   [AGENTS.md](AGENTS.md), including `common-references`.
2. **Smoke-test a skill** — ask: *"Use the create-test-plan skill to outline
   a test plan for a simple savings account."* The agent should follow the
   skill's workflow and offer to write `documentation/TEST_PLAN.md`.

**Troubleshooting**

- *Skills don't appear*: restart the tool (Codex and Gemini detect changes
  automatically; others may cache). Confirm the symlinks survived checkout
  with `ls -l .claude/skills` — on Windows see the symlink note above.
- *Skill found but references missing docs*: keep the `skills/` tree intact;
  skills resolve shared documentation via `../common-references/`.
- *Gemini extension users*: `gemini extensions update fde-agent-skills`
  after pulling changes.

## Requirements

Most skills operate on a Vault client workspace and expect the
`feature_library` and Inception SDK to be available there. Bundled reference
documentation currently covers **Vault 5.9**. Each skill declares its
prerequisites in the `compatibility` field of its `SKILL.md`.

