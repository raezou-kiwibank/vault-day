---
name: create-clu-resources
description: Design and generate a standard, compliant CLU Configuration Pack for Vault banking products. Use when packaging a rendered Smart Contract, parameters, and flags for deployment to a Vault environment.
compatibility: Requires a Vault client workspace with the feature_library, Inception SDK, and the CLU (Configuration Layer Utility) command-line tool as project dependencies. Reference documentation bundled for Vault 5.9.
audience: client
---

# CLU Configuration Pack Generation

This skill outlines the standard workflow for generating a standard, compliant CLU (Configuration Layer Utility) Configuration Pack for newly built or updated Vault Core banking products.

**Autonomous Resource Determination:** The complete list of required resource files must be determined autonomously by analyzing the smart contract's requirements, metadata, and the project's implementation plan. Rather than relying on explicit user prompts, the contract metadata, features, and dependencies must be parsed to compile the necessary list of files.

Each banking product is unique and will require a different set of resources depending on the features and configurations it integrates (such as parameters, global parameters, parameter value mappings, calendars, and flag definitions). Only the directories and files required for the specific product's resources should be scaffolded and generated.

## Inputs and Scope

Read these from the product's `documentation/` folder (written by the earlier skills):
- `IMPLEMENTATION_PLAN.md`: the header gives the Vault version, and each feature's Status says what has been built. Package the features marked `Implemented`, not those still `Planned`.
- `REQUIREMENTS.md`: each feature's Parameters table (level, default, range) and Accounting Entries (internal account names), the Schedules Summary, the Lifecycle and the Open items.

Features are delivered one at a time, so this skill runs once per delivered feature. Add the resources the newly implemented feature needs to the existing pack and update `manifest.yaml`. Do not regenerate or edit the resources of earlier features unless the new feature changes them, and say so in the report if it does.

## Reference Documentation

**STRICT MANDATE**: Always consult the authoritative reference files inside `../common-references/` to ensure exact API payloads and CLU schemas. DO NOT guess payload schemas, parameter constraints, or CLU properties.

Refer to:
- **Core API OpenAPI Specs:** `../common-references/core_api_documentation/vault-<version>/core_api.json` — Inspect JSON schemas for specific resources (e.g., `v1parametersParameter` for parameters, `v1flagsFlagDefinition` for flags) to ensure CLU payloads match the required Core API structures.
- **CLU Official Documentation:** `../common-references/clu_documentation/vault-<version>/` — Review detailed guides on building packs, resource structures, and directory setups.

## Directory Layout

**Direct Integration:** CLU resources must be merged directly into the existing directories of the product alongside the smart contract and tests. Place CLU files directly into subfolders of the product directory (e.g., `contracts/`, `account_schedule_tags/`, `flag_definitions/`, `internal_accounts/`, `parameters/`, `calendars/`) as siblings to `tests/` and `constants/`.

```
<product_name>/
├── manifest.yaml
├── contracts/
│   ├── <product_name>_contract.resource.yaml
│   └── <product_name>_rendered.py   # empty placeholder until deployment
├── account_schedule_tags/
│   ├── <tag_1>.resource.yaml
│   └── <tag_2>.resource.yaml
├── flag_definitions/
│   └── <flag_1>.resource.yaml
├── internal_accounts/
│   └── <internal_account_1>.resource.yaml
├── parameters/
│   └── <parameter_1>.resource.yaml
└── calendars/
    └── <calendar_1>.resource.yaml
```
*Note*: Scaffold only the directories (such as `account_schedule_tags/`, `flag_definitions/`, or `internal_accounts/`) that autonomous determination reveals are required by the product's features.

## Step-by-Step Workflow

### 0. Version Identification & Context Verification
Before starting any work, you MUST verify the target **Vault version** (e.g., 5.9) and **Contracts API version** (CLV3 or CLV4) associated with the product:
- Read them from the header of `documentation/IMPLEMENTATION_PLAN.md`, which `create-smart-contract` writes. If the product came from `convert-clv3`, retrieve the version established in that step.
- If there is no plan and no earlier step established the version, ask the user explicitly to provide the target Vault version.
- Use this target version to substitute all `<version>` placeholders in reference paths (e.g., mapping to `vault-5-9/`) and to locate the correct `core_api.json` and CLU guides.

#### CLU Dependency & Version Alignment
The CLU command-line utility must be available in the repository as a project dependency (similar to `feature-library` or `inception_sdk`). You MUST align and validate the CLU binary version according to the following strict guidelines:

1. **Major Version Strict Matching:**
   To ensure complete schema compatibility, the CLU binary major version must align exactly with your Vault Core instance's major version:
   - **CLU 5.x.y** is designed to work with **Vault Core 5.x.y** (built/released from the `master` branch).
   - **CLU 4.x.y** is designed to work with **Vault Core 4.x.y** (built/released from the `vault-4.7` branch).

2. **Programmatic Version Validation (The API Check):**
   When CLU executes, it queries the target Vault Core API's `/v1/vault-version` endpoint, parses the returned JSON, and extracts the major version:
   ```go
   semver, ok := vaultVersion["version"].(map[string]interface{})
   major, ok := semver["major"].(float64)
   ```
   It compares this against the CLU binary's compiled `TargetVaultVersionMajor` constant (defined in `version.go`). If they don't match, CLU fails with a `versionMismatchError`:
   > "this version of CLU is designed to work with Vault version %d.x, but the provided API is version %d.x; please use a version of CLU compatible with your Vault version"
   
   *(Note: If the major version is 0 (mock/local environment) or > 2000 (year-based internal development tag), the major version mismatch validation is bypassed for development ease).*

3. **Fine-Grained Schema Checks (EarliestVersion & VersionedPaths):**
   Even if the major version check passes, CLU runs granular checks on resources and fields using explicit metadata declarations.
   - **Earliest Version Check (`EarliestVersion`):** Each resource has a defined version check before CLU attempts to validate or import. If the detected Vault Core version is older than this value, it raises an error.
     - *Smart Contract Versions:* Requires earliest Vault Core version `3.5`.
     - *Edge Functions:* Requires earliest Vault Core version `5.5`.
   - **Path-Level Version Check (`VersionedPaths`):** Certain fields or attributes inside configuration resources are restricted to specific Vault Core releases.
     - `product_version.parameter_id_by_instance_parameter_name`: Requires minimum version `5.0`.
     - `product_version.adjustments_patch_version_id`: Requires minimum version `5.9`.
   
   If an unsupported field is included in your configuration bundle, CLU raises a compilation/linting error:
   > "the paths [%s] for %s resource are not supported in the detected Vault Core version (%d.%d). Please check the resource's supported paths"

### 1. Resource Identification (Dual-Source Discovery)
Compile the initial list of required resources using two complementary discovery pillars:

- **Pillar A: Bottom-Up (Smart Contract Driven):** Parse the smart contract python code to extract resources required for execution:
  - *Schedules $\rightarrow$ `ACCOUNT_SCHEDULE_TAG`:* Extract every schedule from `event_types` and scheduling hook logic.
  - *Feature Parameters $\rightarrow$ `PARAMETER`:* Look at `expected_parameters` and locate standard feature parameters in the `feature_library` (under `.venv/lib/python3.10/site-packages/feature_library/<feature_path>/parameter_resource_defs/`).
  - *Core Ledger Routing $\rightarrow$ Internal `ACCOUNT`:* Identify general ledger accounts referenced by parameters (e.g., fee income, interest paid) and map their corresponding internal accounts.

- **Pillar B: Top-Down (Requirements & Specs Driven):** Analyze the `REQUIREMENTS.md` or design specifications to capture platform-level configurations that never appear inside the contract code. Cross-check Pillar A against the Parameters tables, the Accounting Entries (internal account names) and the Schedules Summary of the implemented features:
  - *Compliance/Blocking Rules $\rightarrow$ `RESTRICTION_SET_DEFINITION_VERSION`:* Search for transactional blocking requirements (e.g., *"frozen account blocks outbound payments"*). Map these to platform-level restriction definitions.
  - *Working Days & Adjustments $\rightarrow$ `CALENDAR`:* Search for schedule adjustment rules (e.g., *"interest application schedule delays over bank holidays"*). Map these to calendar dependencies.

### 2. Dynamic CLU Verification & Reverse Checklist Audit
Before generating any resource files, verify your planned list against the target version's capabilities **AND** use the supported list to catch any missed resources:

- **Locate Supported List:** 
  - For **Vault 5.9**, consult the exact authoritative file: `../common-references/clu_documentation/vault-5-9/clu_features/resources_supported_for_import.adoc`
  - For other versions, run a fuzzy search across the version's `clu_documentation` directory for filenames containing `supported` or `import`.
- **Verify Planned Resources:** Ensure every resource planned in Step 1 is supported for import by the target version's CLU.
- **The Reverse Checklist Audit (Catching Omissions):** Scan the supported list and reconcile it against the requirements to check for overlooked resources:
  - `CALENDAR`: Did we plan a calendar? Does the contract check bank holidays? If yes, and we didn't plan one, add it now.
  - `RESTRICTION_SET_DEFINITION_VERSION`: Do the requirements mention blocking or freezing transactions? If yes, and we missed it, add it now.
  - `GLOBAL_PARAMETER`: Do the requirements describe shared parameters (like tax rates or interest caps) across multiple products? If yes, add it now.

- **🚫 Strict Scope Boundaries & Exclusions:**
  The following resource categories from the supported import list are strictly **out of scope** and must **NOT** be generated:
  1. *Edge Function API resources:* Out of scope for now given it's not yet in the active agentic workflow we are building.
  2. *Workflow API resources:* Out of scope since they are deprecated.
  3. *Access Control API resources:* Out of scope as they are not directly related to product builds.
  Only **Core API resources** are in scope for now.

### 3. Schema-First Resource Payload Compilation
For every verified and reconciled resource in your final plan, query its JSON schema under `core_api_documentation/vault-<version>/core_api.json` and compile compliant payloads. Common resource templates include:

#### ACCOUNT_SCHEDULE_TAG
```yaml
type: ACCOUNT_SCHEDULE_TAG
id: <TAG_ID>
payload: |
  account_schedule_tag:
    id: <TAG_ID>
    description: <Description>
    sends_scheduled_operation_reports: false
    schedule_status_override: ACCOUNT_SCHEDULE_TAG_SCHEDULE_STATUS_OVERRIDE_NO_OVERRIDE
    schedule_status_override_start_timestamp: null
    schedule_status_override_end_timestamp: null
    test_pause_at_timestamp: null
```

#### ACCOUNT (Internal Account)
```yaml
type: ACCOUNT
id: <ACCOUNT_ID>
vault_id: <VAULT_ID>
payload: |
  account:
    id: <VAULT_ID>
    type: ACCOUNT_TYPE_INTERNAL
    status: ACCOUNT_STATUS_OPEN
    t_side: T_SIDE_LIABILITY  # or T_SIDE_ASSET
```

#### FLAG_DEFINITION
```yaml
type: FLAG_DEFINITION
id: <FLAG_ID>
payload: |
  flag_definition:
    id: <FLAG_ID>
    name: <Name>
    description: <Description>
    required_flag_level: FLAG_LEVEL_ACCOUNT  # or FLAG_LEVEL_CUSTOMER
```

### 4. Scaffold and Generate Files
**First, close the open values of the feature in this pack.** `REQUIREMENTS.md` marks a value that nobody has supplied as `TBC`, and this is the stage that closes Configuration values (the implementation plan's open questions name the stage). Before writing any file, collect the `TBC` values in the Parameters tables and the Open items of the features this pack packages, and only those. A value that belongs to a feature still `Planned` is asked about in the run that packages that feature. If none is open, ask nothing. Otherwise ask the user for the final value of each, in one list that names the parameter and what the requirements say it is for. Put your proposed default next to each, with where it comes from (the contract's or library's default, the internal account names in the requirements' Accounting Entries, or the simplest option). The user either gives a value or accepts your default. Wait for the answer, then mark the plan's open question that covers each value `Resolved` with the value and whether it is the user's or your proposed default, and append a Change log row, as `create-smart-contract` does when it refreshes the plan.

No `TBC` value of this feature is left after this. Never write a value the user has not been shown, and never use a stand-in marker for a value that is not known.

Then directly integrate CLU files inside the product's subdirectory structure (e.g., `<product_name>/`).
- Copy any standard feature parameters directly from the `feature_library` into `parameters/` under the product folder.
- Create custom `.resource.yaml` definitions for planned internal accounts, calendars, flag definitions, and restriction definitions in their respective subdirectories.
- Leave `contracts/<product_name>_rendered.py` as `create-smart-contract` left it: an empty placeholder for build output. Do not render the contract in this skill. It is rendered when the pack is about to be deployed with `clu import`, which this skill does not do. The file must exist, because the contract resource below refers to it and `clu validate` fails when it is missing.
- Create the contract version resource file under `contracts/<product_name>_contract.resource.yaml`. Use the external file inclusion syntax to reference the source code. The path is relative to the resource file that holds it, not to the manifest, so from `contracts/` it is `@{<product_name>_rendered.py}`. Map all parameters to their string-serialized defaults.
  - **Never invent a business value.** A value you set is the contract's own declared default, the user's answer, or your proposed default that the user accepted. A parameter that a recorded decision (`D-xx`) leaves unset stays unset.

### 5. Create the manifest.yaml
Construct the `manifest.yaml` listing the overall pack metadata (`pack_version`, `pack_name`) and the allowlist of all created resource IDs. Place it directly inside the product's root directory (`<product_name>/`).

### 6. Resolve Topological Linking & Paths
- Traverse dependencies and link resources using CLU reference syntax `&{resource_id}` for internal lookups (e.g., referencing an internal account ID or flag ID inside parameter value mappings or contract parameters).
- Ensure all relative path references (like `@{...}`) are correct relative to the resource file that holds them, not to the manifest file. A wrong path makes `clu validate` fail with `no such file or directory`.

### 7. Validate with CLU
Once all files and the `manifest.yaml` have been generated and paths are topologically resolved, you MUST run a validation step to ensure they are structurally and syntactically valid:

1. **Verify CLU availability:** Ensure that the `clu` executable is present in your environment or repository path as a dependency.
2. **Execute Validation:** Run the `clu validate` command against the generated Configuration Pack's manifest (`clu validate [pack manifest path | bundle path]`):
   ```bash
   clu validate <path_to_product_directory>/manifest.yaml
   ```
   *Note: If a target environment API is reachable, you can optionally provide connection flags to run online validation, which checks schemas against the actual Vault Core instance.*
3. **Analyze and Rectify Errors:**
   - If CLU reports syntactical errors, check-level mismatch errors (e.g., `EarliestVersion` or `VersionedPaths`), or reference/reference-linking (`&{...}`) syntax issues, immediately trace them back to the source YAML files, modify them, and re-run validation.
   - A CLU Configuration Pack is not considered complete until it passes the `clu validate` check successfully.

### 8. Report and Hand Back
Report the resources added or changed, any change to an earlier feature's resources, the `clu validate` result, the values set (from the user's answers and from accepted defaults) and the plan questions you marked `Resolved`. Then return control to the user. The usual next step is `create-sc-tests` for this feature. Start nothing.
