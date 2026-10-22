# Feature Library Standards

This is the working standard for the FDE Feature Library. It exists to make one
rule operable:

> **A feature is complete when it is documented, traceable from a business
> requirement through its parameters to a product, and exercised by a tested
> end-to-end product. Anything else is work in progress.**

Every rule below is **enforced by something you can run** — an `fl` check code, a
semgrep rule, or a test. A rule with no enforcement is a preference, and
preferences belong in review comments, not in a standard. Where a rule is not yet
enforced it is marked `[unenforced]` and is a to-do for the toolchain, not a
licence to ignore it.

Run the whole gate with:

```shell
make fl-check      # the completeness gate  (no credentials needed)
make fl-test       # the toolchain's own tests
make check-all     # everything, including ruff/mypy/semgrep/pytest
```

---

## 1. Module structure

| # | Rule | Enforced by |
|---|---|---|
| 1.1 | A module that declares `expected_parameters` or `data_fetchers` is a feature and must set `__smart_contract_feature__ = True`, or the renderer will not inline it. | semgrep `feature-module-must-declare-marker` |
| 1.2 | Features import each other as `import feature_library.a.b as b` — never `from ... import name` — because the renderer rewrites module references, not names. | semgrep `enforce-import-as-syntax-for-features` |
| 1.3 | Dependency direction is products → features. A feature must not import a product. | semgrep `feature-must-not-import-from-products` |
| 1.4 | A deposit feature must not import a lending feature or vice versa. Shared logic belongs in `feature_library/common`. | semgrep `no-cross-domain-feature-import` |
| 1.5 | Smart Contracts do not support classes. Use functional `NamedTuple` syntax. | ruff `UP014` ignored + review |
| 1.6 | Every module carries a one-line docstring stating the capability. | `fl` **FL020** |
| 1.7 | Every public function carries a Google-style docstring with `Args:` and `Returns:`. | `fl` **FL021**, semgrep `vault-missing-typehints-docstrings` |

## 2. Parameters and the value hierarchy

A parameter id is a **deployment-time reference**, not a Python value. Python,
`ruff` and the unit tests all pass with a broken reference; only a config-pack
import fails. That is why these rules are strict.

| # | Rule | Enforced by |
|---|---|---|
| 2.1 | A `*_PARAM_ID` constant holds exactly `"&{parameter_id}"` — one `&`, balanced braces, lowercase snake_case id. | `fl` **FL001**, semgrep `clu-parameter-reference-must-be-wrapped`, `clu-parameter-reference-malformed-braces` |
| 2.2 | Every referenced parameter has a backing `PARAMETER` resource definition somewhere in the tree. | `fl` **FL002** |
| 2.3 | Every `PARAMETER` resource is referenced by at least one feature. Orphans are deleted or reconnected. | `fl` **FL003** |
| 2.4 | A parameter id is defined **once**. Identical copies are consolidated. | `fl` **FL004** |
| 2.5 | Two different parameters must never share an id. This is the rule that breaks cross-domain products: a config pack containing both definitions silently keeps one. | `fl` **FL007** |
| 2.6 | A resource file's `id`, its payload's `parameter.id`, and its filename are all the same string. | `fl` **FL006**, **FL008** |
| 2.7 | `ExpectedParameter(id=...)` takes the constant, never a literal, so the same reference is shared with `fetchers_config` and asserted in tests. | semgrep `expected-parameter-id-must-use-constant` |
| 2.8 | Every parameter a feature declares is documented in its knowledge record with its meaning, its hierarchy level, and the behaviour it drives. | `fl` **FL011** (schema requires `description`) |

**Using the hierarchy.** The point of `&{...}` shared definitions is that one
contract becomes many product variants without code change: the definition is
declared once, and each product version supplies its own values. A feature must
therefore never hard-code a value that a bank might reasonably want to vary —
rates, times, precisions, day counts, thresholds, internal account ids and
enable/disable switches are all parameters.

## 3. Data fetching

| # | Rule | Enforced by |
|---|---|---|
| 3.1 | Fetcher constants use the suffix matching their type: `_BOF`, `_BIF`, `_BDIF`, `_POF`, `_PIF`, `_COF`, `_CIF`, `_FOF`, `_FIF`, `_POSTIF`, `_SOF`. | semgrep `*-naming-convention` (11 rules) |
| 3.2 | A fetcher id is defined by exactly one module. Several features may *share* one definition from `common.fetchers`; two features must not each define the same id. | `fl` **FL042** |
| 3.3 | A composing contract deduplicates with `fetchers.distinct_fetchers(...)` and `parameter_utils.distinct_expected_parameters(...)`. | `[unenforced]` — planned contract-composition check |
| 3.4 | A feature accepts a `FetchersConfig` NamedTuple so a composing contract can remap fetcher and parameter ids without the feature changing. | `[unenforced]` — convention, visible in generated docs |

## 4. Hooks and determinism

Contract execution must be reproducible: the same hook, replayed at the same
`effective_datetime`, must produce byte-identical directives. Simulation,
backdating and replay all depend on it.

| # | Rule | Enforced by |
|---|---|---|
| 4.1 | Never read wall-clock time. Use `effective_datetime`. | semgrep `avoid-datetime-now`, `no-nondeterministic-sources-in-contracts` |
| 4.2 | No randomness, no `uuid1`/`uuid4`, no `time.time()`, no `date.today()`. | semgrep `no-nondeterministic-sources-in-contracts` |
| 4.3 | Never iterate a `set` to produce postings — the order is unstable. Sort first. | semgrep `no-set-iteration-in-contract-output` |
| 4.4 | Never build a `Decimal` from a float. Amounts must match the simulator exactly. | semgrep `decimal-must-not-be-built-from-float` |
| 4.5 | Do not mutate Contracts API objects in place; construct new ones so validation runs. | semgrep `forbid-inplace-mutation`, `avoid-inplace-mutation-contract-api` |
| 4.6 | A zero-amount result produces **no** instruction, so replay stays idempotent and the ledger stays clean. | semgrep `vault-unhandled-zero-amount-posting` |
| 4.7 | A returned `Rejection` is always propagated, never discarded. | semgrep `vault-ignored-rejection-return` |
| 4.8 | Empty hooks are removed — they cost execution budget for nothing. | semgrep `avoid-empty-hooks` |
| 4.9 | The knowledge record declares which hooks the feature is designed for, and the declaration must not contradict the code. | `fl` **FL013** |

## 5. Composition into products

| # | Rule | Enforced by |
|---|---|---|
| 5.1 | A product is declared as data in `products/<id>/product.yaml` before it is written as Python, so the composition can be checked and read by tooling. | `fl` **FL040** (schema) |
| 5.2 | Every feature a product names must exist. | `fl` **FL041** |
| 5.3 | A product spanning two domains must not use a parameter id that is defined differently in each. | `fl` **FL043** |
| 5.4 | A product's declared contract file exists. | `fl` **FL045** |
| 5.5 | A product declares simulation and end-to-end suites. | `fl` **FL046** |
| 5.6 | Every behaviour-bearing feature is composed by at least one product. | `fl` **FL044** |
| 5.7 | Cross-account behaviour is achieved by one contract posting to another account (as `lending.disbursal.disbursement` does), not by reading another account's balances. Reading across accounts requires a Supervisor Contract. | `[unenforced]` — design rule |

## 6. Documentation

| # | Rule | Enforced by |
|---|---|---|
| 6.1 | Every feature publishes a knowledge record (`<module>.feature.yaml`) beside it. | `fl` **FL010** |
| 6.2 | The record validates against the feature knowledge record schema. | `fl` **FL011** |
| 6.3 | The record's `derived` block matches the module's current public surface. Stale records fail the build. | `fl` **FL012** |
| 6.4 | Reference documentation is **generated**, never hand-written, so it cannot drift. | `fl` **FL022** |
| 6.5 | Each feature page carries a traceability diagram wiring configuration inputs through the functions that read them to the hooks and outcomes they drive. | generated by `fl docs` |
| 6.6 | The published bundle conforms to Open Knowledge Format v0.2: every `.md` carries parseable YAML frontmatter with a non-empty `type`, and `index.md` is reserved for indexes. | `tools/tests/test_bundle.py::OkfConformanceTests` |
| 6.7 | The bundle is byte-reproducible, so CI can regenerate it and fail on any diff. No wall-clock timestamps are written; provenance is a content hash of the source. | `test_bundle.py::ReproducibilityTests` |
| 6.8 | Hand-written prose lives below the `<!-- generated:end -->` marker and survives regeneration. | `test_bundle.py::test_hand_written_prose_survives_regeneration` |
| 6.9 | Every directory in the bundle carries an `index.md`, every internal link resolves, and the root publishes `llms.txt`. | `test_bundle.py::BundleProfileTests` |

Hand-written documentation is not banned, but it is not trusted: the existing
`apex_reserve_card/README.md` still points at a `feature_library/apex/` package
that no longer exists, which is exactly the failure mode generation prevents.

## 7. Traceability

The chain the library must be able to show, in both directions, for anything it
ships:

```
business requirement -> parameter -> feature function -> hook -> product -> test
```

| # | Rule | Enforced by |
|---|---|---|
| 7.1 | Every feature links at least one business requirement with a stable id and the statement in the analyst's words. | `fl` **FL050** |
| 7.2 | Every requirement names the tests that verify it. | `fl` **FL051** |
| 7.3 | Requirement ids are stable and reused across features and products, so one requirement can be traced to everything implementing it. | `[unenforced]` — planned cross-record check |

## 8. Testing

| # | Rule | Enforced by |
|---|---|---|
| 8.1 | Every feature has unit tests. | `fl` **FL030** |
| 8.2 | Every feature has simulation tests. | `fl` **FL031** |
| 8.3 | Every feature is covered by a product's end-to-end suite. | `fl` **FL032** |
| 8.4 | Coverage is attributed by what a test *imports*, including through the harness contract it drives — not by directory naming. | `fl/tests_index.py` |
| 8.5 | Simulation tests parameterise over timezones to prove processing-group behaviour. | `[unenforced]` — convention, see `tests/sim_utils.py` |
| 8.6 | Determinism tests assert that replaying a hook at the same effective datetime yields identical directives. | `[unenforced]` — planned test base class |

## 9. Developer experience

| # | Rule | Enforced by |
|---|---|---|
| 9.1 | The knowledge layer runs with the system Python and no credentials, so it works in a pre-commit hook and in CI before dependencies are installed. | `tools/fl/` imports stdlib only; `make fl-test` |
| 9.2 | The gate ships with a committed baseline of accepted debt. New violations fail; existing debt stays visible. | `tools/fl-baseline.json` |
| 9.3 | The baseline only shrinks. A pull request that grows it is visibly asking for an exception. | review + `fl baseline` reports stale entries |
| 9.4 | Generated artefacts are committed, so a diff shows when behaviour changed. | `make knowledge` |

### The debt today

`make fl-check` currently accepts **390** findings and blocks on anything new.
The two error classes that must clear before the cross-domain products ship:

- **FL007 × 2** — `grace_period` and `account_tier` are each defined differently
  in two places. `grace_period` in particular means two genuinely different
  parameters (deposit: days to amend fee-free; lending: days before delinquency,
  capped at 27). A Corporate Account and a Mortgage in one config pack will
  collide on it.
- **FL030 × 4** — features with no unit tests at all.

---

## Adding a feature

```shell
# 1. Write the module under feature_library/src/feature_library/<domain>/...
# 2. Add its parameter resource definitions next to it.
python3 -m fl scaffold <domain>.<path>.<module>   # creates <module>.feature.yaml
# 3. Fill in capability, client_functionality, parameter meanings, requirements.
# 4. Write unit and simulation tests.
# 5. Add it to a product's feature list.
make knowledge        # refresh derived facts, docs and the knowledge pack
make fl-check         # must report no new findings
```

## Consuming the library from an agent

Two published artefacts, for two different consumers:

**`knowledge/` — the Feature Knowledge Bundle.** A tree of markdown documents
with YAML frontmatter, conforming to [Open Knowledge Format
v0.2](https://github.com/GoogleCloudPlatform/knowledge-catalog) — 288 documents
covering every feature, product and parameter, with `index.md` navigation and an
`llms.txt` at the root. This is what you point an agent or a documentation site
at. Regenerate with `make fl-bundle`.

A note on the name: the bundle *conforms to* OKF and records `okf_version: "0.2"`
as a field, but the format is called a **Feature Knowledge Bundle**. OKF is
Google Cloud's spec, and the acronym has belonged to the Open Knowledge
Foundation since 2004 — claiming it for our profile would be wrong on both
counts.

**`docs/knowledge-pack.json` — a single-file index.** The same facts in one JSON
document, for tooling that would rather parse once than walk a tree. Regenerate
with `make fl-export`.

Both exist so that `create-smart-contract` and `create-clu-resources` can select
and compose features from a declared contract instead of grepping the source.
