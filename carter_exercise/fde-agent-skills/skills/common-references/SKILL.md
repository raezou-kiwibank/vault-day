---
name: common-references
description: Authoritative reference documentation for Thought Machine Vault. Consult when you need to verify Contracts API methods, types, hooks, decorators, or Inception SDK test framework usage instead of guessing. Used by the other skills in this repository.
compatibility: Documentation covers Vault 5.9 (Contracts API, Core API OpenAPI specs, and CLU documentation).
audience: client
---

# Common References

This skill is a documentation library, not a workflow. Use it to look up
ground truth before writing or reviewing Smart Contract code. NEVER guess
method names, signatures, or parameters — verify them here.

## Contents

### Contracts API documentation

`contracts_api_documentation/vault-<version>/` contains the full Vault
Contracts API reference in AsciiDoc, per Vault version. Currently available:
`vault-5-9/`. If the user's Vault version is not present, tell them so and
use the closest available version, flagging the mismatch.

- **CLv4 (Contracts API 4.x)** — standard for new contracts:
  `contracts_api_documentation/vault-<version>/contracts_api_4xx/`
  - Smart Contract metadata: `smart_contracts_api_reference4xx/metadata/`
  - Vault object API: `smart_contracts_api_reference4xx/vault/`
  - Hooks: `smart_contracts_api_reference4xx/hooks/`
  - Supervisor equivalents: `supervisor_contracts_api_reference4xx/...`
  - Types/classes: `common_types_4xx/classes/`
  - Enums: `common_types_4xx/enums/`
  - Allowed built-ins: `common_types_4xx/builtins/`
  - Permitted native imports: `common_types_4xx/native_objects/`
  - Decorators (`@requires`, `@fetch_account_data`): `common_types_4xx/decorators/`
- **CLv3 (Contracts API 3.x)** — legacy contracts:
  `contracts_api_documentation/vault-<version>/contracts_api_3xx/`

Each directory contains an `index.adoc` and `nav.txt` to orient navigation.

### Inception SDK test framework documentation

`inception_sdk_documentation/` covers testing Smart Contracts:

- `inception_test_framework_approach.md` — framework overview and test tiers
- `unit.md` — unit testing patterns
- `inception_test_framework_contract_simulation_testing.md` — simulation tests
- `inception_test_framework_e2e.md` — end-to-end tests
- `debugging_smart_contracts.md` — debugging techniques

### Core API OpenAPI Specifications

`core_api_documentation/vault-<version>/core_api.json` contains raw OpenAPI specifications for Vault Core API endpoints. Supported versions: `vault-5-9` and `vault-5-10`.
Use these to verify exact payload formats and required fields for Core API resources (e.g., Accounts, Parameters, Calendars, Flag Definitions) as CLU payloads mimic these JSON schemas.

### Configuration Layer Utility (CLU) User Guide

`clu_documentation/vault-<version>/` contains official CLU documentation, tutorials, and examples. Supported versions: `vault-5-9` and `vault-5-10`.
Key references:
- `creating_a_config_pack/` — detailed guide for packaging smart contracts and parameter value mappings.
- `creating_and_importing_resources_tutorial/` — tutorial on scaffolding and applying resource definition YAML files.
- `index.adoc` — landing page and core concept index.

## Guardrails

- Treat this documentation as authoritative over your prior knowledge of the
  Contracts API.
- Always resolve the Vault version and CLv3/CLv4 choice before citing a
  reference path.
- Do not paste large documentation sections into responses; read what you
  need and cite the file path.
