"""The completeness gate for the feature library.

The rule this file enforces is the one the library is organised around:

    A feature is complete when it is documented, traceable from a business
    requirement through its parameters to a product, and exercised by a tested
    end-to-end product. Anything else is work in progress.

Every check below is mechanical. Findings carry a stable code so they can be
suppressed deliberately, counted over time, and wired into CI at whatever
severity the team is ready for — the point is to make the gap visible and
finite, not to fail the build on day one.
"""

from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass, field
from typing import Any, Iterable

from . import introspect, resources, schema, tests_index, yamlite
from .model import ModuleFacts

FEATURE_RECORD_SUFFIX = ".feature.yaml"
PRODUCT_RECORD_NAME = "product.yaml"

ERROR = "error"
WARNING = "warning"
INFO = "info"


@dataclass
class Finding:
    """One conformance problem.

    Attributes:
        code: Stable identifier, e.g. ``FL002``.
        severity: ``error``, ``warning`` or ``info``.
        subject: What the finding is about — a module, a path, a parameter.
        message: Human-readable description.
        location: File path, optionally with ``:line``.
        remedy: The concrete next action.
    """

    code: str
    severity: str
    subject: str
    message: str
    location: str = ""
    remedy: str = ""

    def render(self) -> str:
        """Format the finding as a single console line.

        Returns:
            The formatted line.
        """
        where = f" ({self.location})" if self.location else ""
        return f"[{self.code}] {self.severity.upper():7s} {self.subject}: {self.message}{where}"


@dataclass
class Context:
    """Everything the checks need, gathered once.

    Attributes:
        repo_root: Repository root.
        src_root: The ``src`` layout root.
        tests_root: The tests tree root.
        products_root: The products tree root.
        facts: Resolved module facts by dotted module name.
        features: The subset of facts marked as smart contract features.
        resource_index: CLU resource definitions.
        tests: Test modules by path.
        coverage: Feature test coverage.
        manifests: Feature manifests by module.
        products: Product records by product id.
    """

    repo_root: str
    src_root: str
    tests_root: str
    products_root: str
    facts: dict[str, ModuleFacts] = field(default_factory=dict)
    features: dict[str, ModuleFacts] = field(default_factory=dict)
    resource_index: resources.ResourceIndex = field(default_factory=resources.ResourceIndex)
    tests: dict[str, tests_index.TestModule] = field(default_factory=dict)
    coverage: dict[str, tests_index.Coverage] = field(default_factory=dict)
    manifests: dict[str, dict[str, Any]] = field(default_factory=dict)
    manifest_paths: dict[str, str] = field(default_factory=dict)
    products: dict[str, dict[str, Any]] = field(default_factory=dict)
    product_paths: dict[str, str] = field(default_factory=dict)
    load_errors: list[Finding] = field(default_factory=list)


def build_context(repo_root: str = ".") -> Context:
    """Gather every input the checks need.

    Args:
        repo_root: Repository root directory.

    Returns:
        A populated :class:`Context`.
    """
    src_root = os.path.join(repo_root, "feature_library", "src")
    tests_root = os.path.join(repo_root, "feature_library", "tests")
    products_root = os.path.join(repo_root, "products")

    ctx = Context(
        repo_root=repo_root,
        src_root=src_root,
        tests_root=tests_root,
        products_root=products_root,
    )
    ctx.facts = introspect.scan(src_root)
    ctx.features = {m: f for m, f in ctx.facts.items() if f.is_feature}
    ctx.resource_index = resources.scan_resources(src_root, products_root)
    ctx.tests = tests_index.scan_tests(tests_root)
    ctx.coverage = tests_index.build_coverage(ctx.tests, set(ctx.features), repo_root=repo_root)

    for module, facts in ctx.features.items():
        # One record per module, named after it, so a package holding several
        # features cannot collapse them into a single ambiguous document.
        candidate = facts.path[:-3] + FEATURE_RECORD_SUFFIX
        if os.path.isfile(candidate):
            doc = _load_yaml(candidate, ctx)
            if isinstance(doc, dict):
                ctx.manifests[module] = doc
                ctx.manifest_paths[module] = candidate

    if os.path.isdir(products_root):
        for dirpath, dirnames, filenames in os.walk(products_root):
            dirnames[:] = [d for d in dirnames if d != "__pycache__"]
            for fn in filenames:
                if fn == PRODUCT_RECORD_NAME:
                    path = os.path.join(dirpath, fn)
                    doc = _load_yaml(path, ctx)
                    if isinstance(doc, dict):
                        pid = str(doc.get("id") or os.path.basename(dirpath))
                        ctx.products[pid] = doc
                        ctx.product_paths[pid] = path
    return ctx


def _load_yaml(path: str, ctx: Context) -> Any:
    """Load a YAML document, recording failures as findings.

    Args:
        path: File to read.
        ctx: Context whose ``load_errors`` collects failures.

    Returns:
        The parsed document, or ``None`` on failure.
    """
    try:
        return yamlite.load(path)
    except Exception as exc:  # noqa: BLE001 - report rather than crash the gate
        ctx.load_errors.append(
            Finding(
                code="FL000",
                severity=ERROR,
                subject=os.path.basename(path),
                message=f"could not be parsed: {exc}",
                location=path,
                remedy="Fix the YAML syntax.",
            )
        )
        return None


# --------------------------------------------------------------------------
# Derived facts digest
# --------------------------------------------------------------------------


def derived_block(facts: ModuleFacts) -> dict[str, Any]:
    """Build the ``derived`` block mirrored into a feature manifest.

    Args:
        facts: Resolved facts for the module.

    Returns:
        The derived block, including a digest over its own content so that a
        change to the feature's public surface invalidates any stale manifest.
    """
    block: dict[str, Any] = {
        "expected_parameters": [p.parameter_id for p in facts.expected_parameters],
        "data_fetchers": [f.fetcher_id for f in facts.data_fetchers],
        "event_types": list(facts.event_types.names),
        "notifications": list(facts.notifications),
        "balance_addresses": list(facts.balance_addresses),
        "public_functions": [f.name for f in facts.public_functions],
        "interfaces_provided": [i.interface for i in facts.interfaces_provided],
        "interfaces_consumed": sorted(set(facts.interfaces_consumed)),
        "depends_on": [m for m in facts.imports_internal if m != facts.module],
        "hook_affinity": list(facts.hook_affinity),
    }
    block["source_digest"] = digest_of(block)
    return block


def digest_of(block: dict[str, Any]) -> str:
    """Compute a stable digest of a derived block.

    Args:
        block: The derived block, with or without an existing digest.

    Returns:
        A short hex digest.
    """
    payload = {k: v for k, v in sorted(block.items()) if k != "source_digest"}
    text = repr(payload).encode("utf-8")
    return hashlib.sha256(text).hexdigest()[:16]


# --------------------------------------------------------------------------
# Checks
# --------------------------------------------------------------------------


def check_parameter_references(ctx: Context) -> list[Finding]:
    """Verify every ``&{...}`` reference resolves to a CLU parameter resource.

    Args:
        ctx: The gathered context.

    Returns:
        Findings for malformed, undefined, duplicated and orphaned parameters.
    """
    out: list[Finding] = []
    defined = ctx.resource_index.parameters
    used: dict[str, set[str]] = {}

    for module, facts in ctx.features.items():
        for param in facts.expected_parameters:
            pid = param.parameter_id
            if not pid:
                out.append(
                    Finding("FL001", ERROR, module,
                            f"{param.constant} has no resolvable parameter id",
                            facts.path,
                            "Assign the ExpectedParameter's id from a *_PARAM_ID constant."))
                continue
            if not (pid.startswith("&{") and pid.endswith("}") and "}" not in pid[2:-1]):
                out.append(
                    Finding("FL001", ERROR, module,
                            f"malformed parameter reference {pid!r} on {param.constant}",
                            facts.path,
                            'Reference syntax is exactly "&{parameter_id}".'))
                continue
            used.setdefault(param.bare_id, set()).add(module)

    for bare_id, modules in sorted(used.items()):
        if bare_id not in defined:
            out.append(
                Finding("FL002", ERROR, bare_id,
                        f"referenced by {', '.join(sorted(modules))} but no PARAMETER resource defines it",
                        "",
                        f"Add a parameter_resource_defs/{bare_id}.resource.yaml declaring it."))

    for bare_id, rd in sorted(defined.items()):
        if bare_id not in used:
            out.append(
                Finding("FL003", WARNING, bare_id,
                        "PARAMETER resource is not referenced by any feature",
                        rd.path,
                        "Delete it, or fix the feature reference that should point at it."))

    # Two resource files sharing a parameter id are not the same problem twice.
    # Identical copies are duplication — annoying, mechanically fixable, and
    # harmless until someone edits one of them. Differing definitions mean two
    # genuinely different parameters have collided on one name, and whichever
    # config pack is applied last silently wins. Only the second is a defect.
    for bare_id, paths in sorted(ctx.resource_index.duplicate_parameter_ids().items()):
        bodies: list[str] = []
        for path in paths:
            try:
                with open(path, "r", encoding="utf-8") as fh:
                    bodies.append(fh.read())
            except OSError:
                bodies.append(path)
        identical = all(b == bodies[0] for b in bodies)
        if identical:
            out.append(
                Finding("FL004", WARNING, bare_id,
                        f"is defined identically in {len(paths)} places",
                        "; ".join(paths),
                        "Keep one definition in a shared parameter_resource_defs directory "
                        "and point the other features at it."))
        else:
            out.append(
                Finding("FL007", ERROR, bare_id,
                        f"is defined DIFFERENTLY in {len(paths)} places — these are distinct "
                        "parameters sharing one id, and a config pack containing both will "
                        "silently keep only one",
                        "; ".join(paths),
                        "Rename one of them so each parameter has a unique id "
                        f"(for example {bare_id}_deposit / {bare_id}_lending), or reconcile "
                        "the definitions if they are genuinely the same parameter."))

    for path, rd in sorted(ctx.resource_index.by_path.items()):
        for err in rd.errors:
            out.append(Finding("FL005", ERROR, os.path.basename(path), err, path,
                               "Fix the resource definition."))
        if rd.type == "PARAMETER" and rd.parameter_id and rd.id != rd.parameter_id:
            out.append(
                Finding("FL006", ERROR, rd.id,
                        f"resource id {rd.id!r} does not match payload parameter id {rd.parameter_id!r}",
                        path,
                        "Make the two ids identical."))
        # The file name is how a human finds a definition. When it disagrees with
        # the id, searching for the parameter fails even though deployment works.
        if rd.type == "PARAMETER" and rd.parameter_id:
            stem = os.path.basename(path)[: -len(resources.RESOURCE_SUFFIX)]
            if stem != rd.parameter_id:
                out.append(
                    Finding("FL008", WARNING, rd.parameter_id,
                            f"is defined in a file named {stem!r}; searching for the parameter "
                            "by name will not find it",
                            path,
                            f"Rename the file to {rd.parameter_id}{resources.RESOURCE_SUFFIX}."))
    return out


def check_manifests(ctx: Context) -> list[Finding]:
    """Verify each feature publishes a valid, current knowledge record.

    Args:
        ctx: The gathered context.

    Returns:
        Findings for missing, invalid or stale manifests.
    """
    out: list[Finding] = []
    for module, facts in sorted(ctx.features.items()):
        doc = ctx.manifests.get(module)
        if doc is None:
            out.append(
                Finding("FL010", WARNING, module,
                        "has no .feature.yaml knowledge record",
                        facts.path,
                        f"Run: python3 -m fl scaffold {module.replace('feature_library.', '')}"))
            continue
        path = ctx.manifest_paths[module]
        errors = schema.validate_instance(doc, schema.FEATURE_SCHEMA)
        for err in errors:
            out.append(Finding("FL011", ERROR, module, err, path,
                               "Correct the record against the OKF feature schema."))
        expected = derived_block(facts)
        actual = doc.get("derived") or {}
        if not isinstance(actual, dict) or actual.get("source_digest") != expected["source_digest"]:
            out.append(
                Finding("FL012", ERROR, module,
                        "derived block is stale — the module's public surface has changed",
                        path,
                        "Run: python3 -m fl derive --write"))
        declared_hooks = set(doc.get("hooks") or [])
        inferred = set(facts.hook_affinity)
        unexplained = inferred - declared_hooks
        if unexplained:
            out.append(
                Finding("FL013", WARNING, module,
                        f"code suggests {sorted(unexplained)} but the record does not declare them",
                        path,
                        "Declare the hook, or rename the function if the affinity is wrong."))
    return out


def check_documentation(ctx: Context) -> list[Finding]:
    """Verify features and their public functions are documented.

    Args:
        ctx: The gathered context.

    Returns:
        Findings for undocumented modules and functions.
    """
    out: list[Finding] = []
    for module, facts in sorted(ctx.features.items()):
        if not facts.summary:
            out.append(
                Finding("FL020", WARNING, module,
                        "module has no docstring summary line",
                        facts.path,
                        "Add a one-line module docstring describing the capability."))
        for fn in facts.public_functions:
            if not fn.has_docstring:
                out.append(
                    Finding("FL021", WARNING, module,
                            f"public function {fn.name}() has no docstring",
                            f"{facts.path}:{fn.lineno}",
                            "Document arguments and return value (Google style)."))
        doc_path = os.path.join(
            os.path.dirname(facts.path), "documentation", f"{facts.name}.md"
        )
        if not os.path.isfile(doc_path):
            out.append(
                Finding("FL022", WARNING, module,
                        "has no generated reference documentation",
                        facts.path,
                        "Run: python3 -m fl docs --write"))
    return out


def check_test_coverage(ctx: Context) -> list[Finding]:
    """Verify each feature is exercised at the required test tiers.

    Args:
        ctx: The gathered context.

    Returns:
        Findings for missing unit, simulation and end-to-end coverage.
    """
    out: list[Finding] = []
    for module, facts in sorted(ctx.features.items()):
        cov = ctx.coverage.get(module)
        if cov is None:
            continue
        if not cov.has_unit:
            out.append(
                Finding("FL030", ERROR, module, "has no unit tests", facts.path,
                        "Add unit tests under feature_library/tests/... marked @pytest.mark.unit."))
        if not cov.has_simulation:
            out.append(
                Finding("FL031", WARNING, module, "has no simulation tests", facts.path,
                        "Add a simulation test driving a contract that composes this feature."))
        if not cov.has_e2e:
            out.append(
                Finding("FL032", WARNING, module, "has no end-to-end tests", facts.path,
                        "Cover it through a product end-to-end suite."))
    return out


def check_product_composition(ctx: Context) -> list[Finding]:
    """Verify products are valid and that every feature reaches one.

    This is the check that makes the library's central rule real: a feature
    that no product composes is not a building block, it is unused code.

    Args:
        ctx: The gathered context.

    Returns:
        Findings for invalid products, unknown feature references, collisions
        within a composition, and features no product uses.
    """
    out: list[Finding] = []
    module_by_id: dict[str, str] = {}
    for module in ctx.features:
        module_by_id[module] = module
        short = module.replace("feature_library.", "")
        module_by_id.setdefault(short, module)

    composed: set[str] = set()

    for pid, doc in sorted(ctx.products.items()):
        path = ctx.product_paths[pid]
        for err in schema.validate_instance(doc, schema.PRODUCT_SCHEMA):
            out.append(Finding("FL040", ERROR, pid, err, path,
                               "Correct the record against the OKF product schema."))

        feature_ids = list(doc.get("features") or [])
        resolved: list[str] = []
        for fid in feature_ids:
            module = module_by_id.get(fid)
            if module is None:
                out.append(
                    Finding("FL041", ERROR, pid,
                            f"composes unknown feature {fid!r}", path,
                            "Use the feature's dotted module id."))
                continue
            resolved.append(module)
            composed.add(module)

        # Several features legitimately share one fetcher declared in
        # common.fetchers — that is reuse, and `fetchers.distinct_fetchers`
        # collapses it. A real collision is one id *defined* by two different
        # modules, because then the two definitions may disagree.
        definers: dict[str, set[str]] = {}
        seen_params: dict[str, str] = {}
        for module in resolved:
            facts = ctx.features[module]
            for f in facts.data_fetchers:
                definers.setdefault(f.fetcher_id, set()).add(f.defined_in or module)
            for p in facts.expected_parameters:
                seen_params.setdefault(p.bare_id, module)
        for fetcher_id, owners in sorted(definers.items()):
            if len(owners) > 1:
                out.append(
                    Finding("FL042", ERROR, pid,
                            f"fetcher id {fetcher_id!r} is defined by more than one module "
                            f"({', '.join(sorted(owners))}); the composed contract can only "
                            "register one definition",
                            path,
                            "Move the fetcher to a shared module, or give each its own id."))

        contract = doc.get("contract") or ""
        if contract and not os.path.isfile(os.path.join(ctx.repo_root, contract)):
            out.append(
                Finding("FL045", WARNING, pid,
                        f"declares a contract at {contract} that does not exist yet",
                        path,
                        "Write the contract template composing the declared features."))
        declared_tests = doc.get("tests") or {}
        for tier in ("simulation", "e2e"):
            if not (declared_tests.get(tier) or []):
                out.append(
                    Finding("FL046", WARNING, pid,
                            f"declares no {tier} tests, so the features it composes are not "
                            "proven end to end",
                            path,
                            f"Add a {tier} suite and list it under tests.{tier}."))

        cross_domain = {ctx.features[m].domain for m in resolved} - {"common", ""}
        if len(cross_domain) > 1:
            dupes = ctx.resource_index.duplicate_parameter_ids()
            colliding = sorted(set(dupes) & set(seen_params))
            if colliding:
                out.append(
                    Finding("FL043", ERROR, pid,
                            f"spans domains {sorted(cross_domain)} and uses parameters defined "
                            f"twice in the tree: {colliding}",
                            path,
                            "Promote those parameter resources to a single shared definition."))

    for module, facts in sorted(ctx.features.items()):
        if facts.domain == "common" or not is_composable(facts):
            continue
        if module not in composed:
            out.append(
                Finding("FL044", WARNING, module,
                        "is not composed by any product — it cannot be considered complete",
                        facts.path,
                        "Add it to a product's feature list, or retire it."))
    return out


def is_composable(facts: ModuleFacts) -> bool:
    """Whether a module is a feature a product composes, or supporting code.

    Address tables, interface declarations and shared utilities are inlined by
    the renderer but are never wired into a hook, so holding them to the
    "must appear in a product" bar would be noise rather than signal.

    Args:
        facts: Resolved module facts.

    Returns:
        True when the module contributes behaviour a product wires up.
    """
    if facts.name in {"addresses", "interfaces", "common", "fetchers", "tuples"}:
        return False
    if facts.name.endswith("_utils"):
        return False
    return bool(facts.hook_affinity or facts.event_types.names or facts.interfaces_provided)


def check_traceability(ctx: Context) -> list[Finding]:
    """Verify requirements trace through to code and tests.

    Args:
        ctx: The gathered context.

    Returns:
        Findings for features with no requirement, and requirements with no
        verifying test.
    """
    out: list[Finding] = []
    for module, doc in sorted(ctx.manifests.items()):
        reqs = doc.get("requirements") or []
        if not reqs:
            out.append(
                Finding("FL050", WARNING, module,
                        "declares no business requirement — it is untraceable",
                        ctx.manifest_paths[module],
                        "Add at least one requirement with an id and statement."))
            continue
        for req in reqs:
            if not isinstance(req, dict):
                continue
            if not req.get("verified_by"):
                out.append(
                    Finding("FL051", WARNING, module,
                            f"requirement {req.get('id')} names no verifying test",
                            ctx.manifest_paths[module],
                            "Add the test node id to verified_by."))
    return out


ALL_CHECKS = {
    "parameters": check_parameter_references,
    "manifests": check_manifests,
    "documentation": check_documentation,
    "tests": check_test_coverage,
    "products": check_product_composition,
    "traceability": check_traceability,
}


def run(ctx: Context, only: Iterable[str] | None = None) -> list[Finding]:
    """Run the checks and return every finding.

    Args:
        ctx: The gathered context.
        only: Optional subset of check names to run.

    Returns:
        All findings, ordered by code then subject.
    """
    selected = list(only) if only else list(ALL_CHECKS)
    findings = list(ctx.load_errors)
    for name in selected:
        check = ALL_CHECKS.get(name)
        if check is None:
            continue
        findings.extend(check(ctx))
    return sorted(findings, key=lambda f: (f.code, f.subject))


def summarise(findings: list[Finding]) -> dict[str, int]:
    """Count findings by severity and by code.

    Args:
        findings: The findings to count.

    Returns:
        Mapping of ``error``/``warning``/``info`` and each code to its count.
    """
    counts: dict[str, int] = {ERROR: 0, WARNING: 0, INFO: 0}
    for f in findings:
        counts[f.severity] = counts.get(f.severity, 0) + 1
        counts[f.code] = counts.get(f.code, 0) + 1
    return counts
