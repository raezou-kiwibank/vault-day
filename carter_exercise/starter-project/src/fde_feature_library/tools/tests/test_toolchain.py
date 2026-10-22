"""Tests for the feature library toolchain.

These run with plain ``python3`` and no third-party packages, because the
toolchain has to work in a pre-commit hook and in CI before the private
``contracts-api`` / ``inception-sdk`` wheels have been installed. Run them with::

    python3 -m unittest discover -s tools/tests -t tools

Several tests use the real repository as a fixture. That is deliberate: the
parser's job is to understand *this* code, so the repository is the only
corpus that proves it does.
"""

from __future__ import annotations

import os
import sys
import tempfile
import textwrap
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fl import docgen, introspect, resources, schema, tests_index, validate, yamlite  # noqa: E402

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SRC_ROOT = os.path.join(REPO_ROOT, "feature_library", "src")


def write(tmp: str, relative: str, body: str) -> str:
    """Write a source file into a temporary tree.

    Args:
        tmp: Temporary directory.
        relative: Path relative to ``tmp``.
        body: File contents; leading indentation is stripped.

    Returns:
        The absolute path written.
    """
    path = os.path.join(tmp, relative)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(textwrap.dedent(body).lstrip("\n"))
    return path


class YamliteTests(unittest.TestCase):
    """The YAML subset parser must handle everything the repo actually contains."""

    def test_parses_every_resource_file_in_the_repository(self) -> None:
        index = resources.scan_resources(SRC_ROOT)
        self.assertGreater(len(index.by_path), 100, "expected the resource corpus to be found")
        broken = {p: r.errors for p, r in index.by_path.items() if r.errors}
        self.assertEqual(broken, {}, "every resource definition must parse")

    def test_block_scalar_preserves_newlines(self) -> None:
        doc = yamlite.loads(
            textwrap.dedent(
                """
                ---
                type: PARAMETER
                payload: |
                  parameter:
                    id: x
                """
            )
        )
        self.assertEqual(doc["payload"], "parameter:\n  id: x\n")

    def test_folded_scalar_joins_lines(self) -> None:
        doc = yamlite.loads("key: >\n  one\n  two\n")
        self.assertEqual(doc["key"], "one two\n")

    def test_comments_outside_quotes_are_stripped_but_kept_inside(self) -> None:
        doc = yamlite.loads('a: 1  # trailing\nb: "has # inside"\n')
        self.assertEqual(doc, {"a": 1, "b": "has # inside"})

    def test_sequence_of_mappings(self) -> None:
        doc = yamlite.loads("items:\n  - id: a\n    n: 1\n  - id: b\n    n: 2\n")
        self.assertEqual(doc, {"items": [{"id": "a", "n": 1}, {"id": "b", "n": 2}]})

    def test_round_trip_preserves_structure(self) -> None:
        value = {
            "okf": "0.1",
            "hooks": ["pre_posting_hook"],
            "nested": {"flag": True, "none": None, "num": 3},
            "block": "line one\nline two\n",
            "empty_list": [],
        }
        self.assertEqual(yamlite.loads(yamlite.dumps(value)), value)

    def test_reference_strings_are_quoted_so_they_survive(self) -> None:
        text = yamlite.dumps({"parameter_id": "&{denomination}"})
        self.assertEqual(yamlite.loads(text)["parameter_id"], "&{denomination}")


class IntrospectTests(unittest.TestCase):
    """Static extraction must reproduce what the contract code declares."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.index = introspect.scan(SRC_ROOT)
        cls.features = {m: f for m, f in cls.index.items() if f.is_feature}

    def test_whole_library_parses(self) -> None:
        failed = {m: f.parse_errors for m, f in self.index.items() if f.parse_errors}
        self.assertEqual(failed, {}, "every feature module must parse")

    def test_finds_a_substantial_number_of_features(self) -> None:
        self.assertGreater(len(self.features), 80)

    def test_resolves_parameters_re_exported_from_another_module(self) -> None:
        facts = self.index["feature_library.deposit.interest.interest_accrual"]
        ids = [p.parameter_id for p in facts.expected_parameters]
        self.assertIn("&{denomination}", ids,
                      "denomination is declared in another module and must resolve")
        self.assertIn("&{accrual_precision}", ids)

    def test_records_optionality_from_the_expected_parameter(self) -> None:
        facts = self.index[
            "feature_library.deposit.transaction_limits.withdrawal_limits.maximum_single_withdrawal"
        ]
        by_id = {p.parameter_id: p for p in facts.expected_parameters}
        self.assertTrue(by_id["&{maximum_withdrawal}"].optional)
        self.assertFalse(by_id["&{denomination}"].optional)

    def test_distinguishes_static_and_factory_event_declarations(self) -> None:
        static = self.index["feature_library.deposit.interest.interest_accrual"]
        factory = self.index["feature_library.deposit.interest.interest_application"]
        self.assertEqual(static.event_types.style, "static")
        self.assertEqual(static.event_types.names, ["INTEREST_ACCRUAL"])
        self.assertEqual(factory.event_types.style, "factory")
        self.assertIn("product_name", factory.event_types.factory_args)

    def test_attributes_parameters_to_the_function_that_reads_them(self) -> None:
        facts = self.index["feature_library.deposit.interest.interest_accrual"]
        by_name = {f.name: f for f in facts.public_functions}
        self.assertEqual(
            by_name["get_scheduled_events"].reads_parameters, ["&{interest_accrual_time}"]
        )
        self.assertIn("&{days_in_year_option}", by_name["schedule_logic"].reads_parameters)
        self.assertNotIn("&{interest_accrual_time}", by_name["schedule_logic"].reads_parameters)

    def test_detects_interfaces_provided(self) -> None:
        facts = self.index["feature_library.deposit.interest.secondary.flat_interest"]
        self.assertIn("InterestType", [i.interface for i in facts.interfaces_provided])

    def test_infers_pre_posting_affinity_from_a_rejection_return(self) -> None:
        facts = self.index[
            "feature_library.deposit.transaction_limits.withdrawal_limits.maximum_single_withdrawal"
        ]
        self.assertIn("pre_posting_hook", facts.hook_affinity)

    def test_a_synthetic_feature_is_read_correctly(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            write(tmp, "feature_library/__init__.py", "")
            write(tmp, "feature_library/demo/__init__.py", "")
            write(
                tmp,
                "feature_library/demo/thing.py",
                '''
                """Does a demo thing."""
                __smart_contract_feature__ = True
                from contracts_api import ExpectedParameter, ParametersObservationFetcher

                LIMIT_PARAM_ID = "&{demo_limit}"
                LIMIT_PARAM = ExpectedParameter(id=LIMIT_PARAM_ID, optional=True)
                expected_parameters = [LIMIT_PARAM]

                DEMO_POF_ID = "demo_pof"
                DEMO_POF = ParametersObservationFetcher(fetcher_id=DEMO_POF_ID)
                data_fetchers = [DEMO_POF]

                def validate(state, postings, fetchers_config=None):
                    """Reject anything over the limit."""
                    return None
                ''',
            )
            index = introspect.scan(os.path.join(tmp))
            facts = index["feature_library.demo.thing"]
            self.assertTrue(facts.is_feature)
            self.assertEqual(facts.summary, "Does a demo thing.")
            self.assertEqual([p.parameter_id for p in facts.expected_parameters], ["&{demo_limit}"])
            self.assertTrue(facts.expected_parameters[0].optional)
            self.assertEqual([f.fetcher_id for f in facts.data_fetchers], ["demo_pof"])


class ResourceTests(unittest.TestCase):
    """Resource indexing underpins the parameter reference checks."""

    def test_reads_type_id_and_nested_parameter_id(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = write(
                tmp,
                "p/demo_limit.resource.yaml",
                """
                ---
                type: PARAMETER
                id: demo_limit
                payload: |
                  parameter:
                    id: demo_limit
                    constraint:
                      decimal_constraint:
                        min_value: "0"
                    metadata:
                      description: A demo limit.
                """,
            )
            rd = resources.read_resource(path)
            self.assertEqual(rd.type, "PARAMETER")
            self.assertEqual(rd.parameter_id, "demo_limit")
            self.assertEqual(rd.constraint_kind, "decimal_constraint")
            self.assertEqual(rd.description, "A demo limit.")

    def test_detects_duplicate_parameter_definitions(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            for n in ("a", "b"):
                write(
                    tmp,
                    f"{n}/dup.resource.yaml",
                    """
                    ---
                    type: PARAMETER
                    id: dup
                    payload: |
                      parameter:
                        id: dup
                    """,
                )
            index = resources.scan_resources(tmp)
            self.assertIn("dup", index.duplicate_parameter_ids())


class SchemaTests(unittest.TestCase):
    """The JSON Schema subset validator must reject what it claims to."""

    def _record(self, **overrides: object) -> dict:
        base = {
            "schema": schema.RECORD_SCHEMA_VERSION,
            "id": "deposit.demo",
            "module": "feature_library.deposit.demo",
            "domain": "deposit",
            "status": "supported",
            "capability": "Does something useful for the bank.",
            "client_functionality": "The customer sees a clear and specific outcome here.",
            "hooks": ["pre_posting_hook"],
        }
        base.update(overrides)
        return base

    def test_accepts_a_minimal_valid_record(self) -> None:
        self.assertEqual(schema.validate_instance(self._record(), schema.FEATURE_SCHEMA), [])

    def test_rejects_a_missing_required_field(self) -> None:
        record = self._record()
        del record["capability"]
        errors = schema.validate_instance(record, schema.FEATURE_SCHEMA)
        self.assertTrue(any("capability" in e for e in errors))

    def test_rejects_an_empty_required_field(self) -> None:
        errors = schema.validate_instance(self._record(capability=""), schema.FEATURE_SCHEMA)
        self.assertTrue(any("capability" in e for e in errors))

    def test_rejects_an_unknown_hook(self) -> None:
        errors = schema.validate_instance(
            self._record(hooks=["magic_hook"]), schema.FEATURE_SCHEMA
        )
        self.assertTrue(any("magic_hook" in e for e in errors))

    def test_rejects_an_unexpected_property(self) -> None:
        errors = schema.validate_instance(self._record(surprise=1), schema.FEATURE_SCHEMA)
        self.assertTrue(any("surprise" in e for e in errors))

    def test_rejects_a_parameter_reference_without_the_wrapper(self) -> None:
        record = self._record(parameters=[{"parameter_id": "denomination",
                                           "description": "The currency."}])
        errors = schema.validate_instance(record, schema.FEATURE_SCHEMA)
        self.assertTrue(any("denomination" in e for e in errors))

    def test_accepts_a_correct_parameter_reference(self) -> None:
        record = self._record(parameters=[{"parameter_id": "&{denomination}",
                                           "description": "The currency."}])
        self.assertEqual(schema.validate_instance(record, schema.FEATURE_SCHEMA), [])

    def test_product_schema_requires_at_least_one_feature(self) -> None:
        product = {
            "schema": schema.PRODUCT_SCHEMA_VERSION,
            "id": "demo.product",
            "display_name": "Demo",
            "domain": "deposit",
            "tside": "LIABILITY",
            "summary": "A demo product used only for testing the schema.",
            "contract": "products/demo/contract.py",
            "features": [],
        }
        errors = schema.validate_instance(product, schema.PRODUCT_SCHEMA)
        self.assertTrue(any("features" in e for e in errors))

    def test_booleans_are_not_accepted_as_integers(self) -> None:
        errors = schema.validate_instance(True, {"type": "integer"})
        self.assertTrue(errors)


class ValidationTests(unittest.TestCase):
    """The gate must flag exactly the conditions it promises to."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.ctx = validate.build_context(REPO_ROOT)

    def test_flags_a_malformed_parameter_reference(self) -> None:
        # Behaviour, not a snapshot of today's defects: build a feature whose
        # reference has a stray brace and confirm the gate rejects it.
        with tempfile.TemporaryDirectory() as tmp:
            write(tmp, "feature_library/__init__.py", "")
            write(tmp, "feature_library/demo/__init__.py", "")
            write(
                tmp,
                "feature_library/demo/broken.py",
                '''
                """Feature with a broken reference."""
                __smart_contract_feature__ = True
                from contracts_api import ExpectedParameter

                BAD_PARAM_ID = "&{demo_limit}}"
                BAD_PARAM = ExpectedParameter(id=BAD_PARAM_ID)
                expected_parameters = [BAD_PARAM]
                ''',
            )
            ctx = validate.Context(
                repo_root=tmp, src_root=tmp, tests_root=tmp, products_root=tmp
            )
            ctx.facts = introspect.scan(tmp)
            ctx.features = {m: f for m, f in ctx.facts.items() if f.is_feature}
            ctx.resource_index = resources.scan_resources(tmp)
            findings = validate.check_parameter_references(ctx)
            self.assertIn("FL001", {f.code for f in findings})

    def test_accepts_a_well_formed_parameter_reference(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            write(tmp, "feature_library/__init__.py", "")
            write(tmp, "feature_library/demo/__init__.py", "")
            write(
                tmp,
                "feature_library/demo/good.py",
                '''
                """Feature with a valid reference."""
                __smart_contract_feature__ = True
                from contracts_api import ExpectedParameter

                OK_PARAM_ID = "&{demo_limit}"
                OK_PARAM = ExpectedParameter(id=OK_PARAM_ID)
                expected_parameters = [OK_PARAM]
                ''',
            )
            write(
                tmp,
                "feature_library/demo/parameter_resource_defs/demo_limit.resource.yaml",
                """
                ---
                type: PARAMETER
                id: demo_limit
                payload: |
                  parameter:
                    id: demo_limit
                """,
            )
            ctx = validate.Context(
                repo_root=tmp, src_root=tmp, tests_root=tmp, products_root=tmp
            )
            ctx.facts = introspect.scan(tmp)
            ctx.features = {m: f for m, f in ctx.facts.items() if f.is_feature}
            ctx.resource_index = resources.scan_resources(tmp)
            codes = {f.code for f in validate.check_parameter_references(ctx)}
            self.assertNotIn("FL001", codes)
            self.assertNotIn("FL002", codes)

    def test_the_repository_has_no_malformed_references_left(self) -> None:
        codes = {f.code for f in validate.check_parameter_references(self.ctx)}
        self.assertNotIn("FL001", codes)
        self.assertNotIn("FL002", codes)

    def test_every_finding_carries_a_remedy(self) -> None:
        findings = validate.run(self.ctx)
        missing = [f.code for f in findings if not f.remedy]
        self.assertEqual(sorted(set(missing)), [], "a finding without a remedy is not actionable")

    def test_derived_digest_changes_when_the_surface_changes(self) -> None:
        facts = self.ctx.features["feature_library.deposit.interest.interest_accrual"]
        before = validate.derived_block(facts)
        facts.expected_parameters = facts.expected_parameters[:-1]
        after = validate.derived_block(facts)
        self.assertNotEqual(before["source_digest"], after["source_digest"])

    def test_derived_digest_is_stable_for_unchanged_input(self) -> None:
        facts = self.ctx.features["feature_library.deposit.interest.interest_accrual"]
        self.assertEqual(
            validate.derived_block(facts)["source_digest"],
            validate.derived_block(facts)["source_digest"],
        )

    def test_findings_are_sorted_by_code(self) -> None:
        findings = validate.run(self.ctx)
        codes = [f.code for f in findings]
        self.assertEqual(codes, sorted(codes))


class CoverageTests(unittest.TestCase):
    """Coverage is attributed by import, including through harness contracts."""

    def test_repository_coverage_is_computed(self) -> None:
        index = introspect.scan(SRC_ROOT)
        features = {m for m, f in index.items() if f.is_feature}
        tests = tests_index.scan_tests(os.path.join(REPO_ROOT, "feature_library", "tests"))
        coverage = tests_index.build_coverage(tests, features, repo_root=REPO_ROOT)
        self.assertEqual(set(coverage), features)
        with_tests = [m for m, c in coverage.items() if c.tiers]
        self.assertGreater(len(with_tests), 50)

    def test_module_imported_via_from_package_import_module_is_credited(self) -> None:
        # `from feature_library.a.b import c` imports module c, not a name in b.
        # Missing this under-reports unit coverage.
        index = introspect.scan(SRC_ROOT)
        features = {m for m, f in index.items() if f.is_feature}
        tests = tests_index.scan_tests(os.path.join(REPO_ROOT, "feature_library", "tests"))
        coverage = tests_index.build_coverage(tests, features, repo_root=REPO_ROOT)
        target = (
            "feature_library.deposit.transaction_limits.withdrawal_limits"
            ".maximum_single_withdrawal"
        )
        self.assertTrue(coverage[target].has_unit)

    def test_harness_contracts_are_not_counted_as_tests(self) -> None:
        tests = tests_index.scan_tests(os.path.join(REPO_ROOT, "feature_library", "tests"))
        harnesses = [t for t in tests.values() if t.is_harness]
        self.assertGreater(len(harnesses), 10)
        self.assertTrue(all(t.test_count == 0 for t in harnesses),
                        "a harness contract defines no test functions")


class DocgenTests(unittest.TestCase):
    """Generated documentation must be well formed and honest."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.ctx = validate.build_context(REPO_ROOT)
        cls.facts = cls.ctx.features["feature_library.deposit.interest.interest_accrual"]

    def test_diagram_is_balanced_and_non_empty(self) -> None:
        block = docgen.traceability_diagram(self.facts, self.ctx.manifests.get(self.facts.module))
        self.assertTrue(block.startswith("```mermaid"))
        self.assertTrue(block.rstrip().endswith("```"))
        self.assertEqual(block.count("subgraph"), block.count("  end"))
        self.assertIn("-->", block)

    def test_diagram_labels_never_contain_raw_double_quotes(self) -> None:
        for module, facts in self.ctx.features.items():
            block = docgen.traceability_diagram(facts, self.ctx.manifests.get(module))
            for line in block.split("\n"):
                if "[" in line and '"' in line:
                    self.assertLessEqual(
                        line.count('"'), line.count('"') // 2 * 2,
                        f"unbalanced quotes in {module}: {line}",
                    )

    def test_page_renders_for_every_feature(self) -> None:
        for module, facts in self.ctx.features.items():
            page = docgen.render_feature(
                facts, self.ctx.manifests.get(module), self.ctx.resource_index,
                self.ctx.coverage.get(module), [], [], repo_root=REPO_ROOT,
            )
            self.assertIn("# ", page, module)
            self.assertIn("## Traceability: configuration to outcome", page, module)

    def test_page_states_plainly_when_no_product_uses_the_feature(self) -> None:
        page = docgen.render_feature(
            self.facts, self.ctx.manifests.get(self.facts.module), self.ctx.resource_index,
            self.ctx.coverage.get(self.facts.module), [], [], repo_root=REPO_ROOT,
        )
        self.assertIn("not yet a proven building block", page)


if __name__ == "__main__":
    unittest.main(verbosity=2)
