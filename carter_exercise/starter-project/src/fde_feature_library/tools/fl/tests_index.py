"""Map features to the tests that exercise them, by import rather than by path.

Test directories in this repository broadly mirror the source tree, but not
reliably: some tiers are called ``simulation`` and some ``sim``, some features
share a test package, and harness contracts live beside the tests that use
them. Guessing coverage from paths therefore produces both false positives and
false negatives.

Reading each test module's imports is exact: a test that imports
``feature_library.deposit.interest.interest_accrual`` exercises that feature,
whatever directory it happens to live in. Harness contracts are followed too,
so a simulation test that drives a contract which composes three features is
credited against all three — which is the whole point of an end-to-end gate.
"""

from __future__ import annotations

import ast
import os
import re
from dataclasses import dataclass, field

PACKAGE_ROOT = "feature_library"

TIER_MARKERS = {
    "unit": "unit",
    "sim": "simulation",
    "simulation": "simulation",
    "e2e": "e2e",
}

_MARKER_RE = re.compile(r"@pytest\.mark\.(unit|sim|e2e|accelerated_e2e)\b")
_TEST_DEF_RE = re.compile(r"^\s*def (test_\w+)", re.MULTILINE)


@dataclass
class TestModule:
    """One test or harness module and what it touches.

    Attributes:
        path: Repo-relative path.
        tier: ``unit``, ``simulation``, ``e2e`` or ``unknown``.
        imports: Feature modules imported directly.
        markers: pytest markers found in the source.
        test_count: Number of ``test_*`` functions.
        is_harness: True when the module defines a contract (``api = "4.x"``)
            rather than tests.
        harness_refs: Paths of harness contracts this test module drives.
    """

    path: str
    tier: str = "unknown"
    imports: list[str] = field(default_factory=list)
    markers: list[str] = field(default_factory=list)
    test_count: int = 0
    is_harness: bool = False
    harness_refs: list[str] = field(default_factory=list)


@dataclass
class Coverage:
    """Test coverage for one feature module."""

    module: str
    unit: list[str] = field(default_factory=list)
    simulation: list[str] = field(default_factory=list)
    e2e: list[str] = field(default_factory=list)

    @property
    def has_unit(self) -> bool:
        """Whether any unit test exercises the feature."""
        return bool(self.unit)

    @property
    def has_simulation(self) -> bool:
        """Whether any simulation test exercises the feature."""
        return bool(self.simulation)

    @property
    def has_e2e(self) -> bool:
        """Whether any end-to-end test exercises the feature."""
        return bool(self.e2e)

    @property
    def tiers(self) -> list[str]:
        """The tiers with at least one test."""
        return [t for t in ("unit", "simulation", "e2e") if getattr(self, f"has_{t}")]


def _tier_from_path(path: str) -> str:
    """Infer a test tier from a path.

    Args:
        path: The test module path.

    Returns:
        ``unit``, ``simulation``, ``e2e`` or ``unknown``.
    """
    parts = {p.lower() for p in path.replace("\\", "/").split("/")}
    for marker, tier in TIER_MARKERS.items():
        if marker in parts:
            return tier
    return "unknown"


def _feature_imports(tree: ast.Module) -> list[str]:
    """Collect feature-library modules imported by a parsed module.

    Args:
        tree: The parsed module.

    Returns:
        Dotted feature module names.
    """
    found: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith(PACKAGE_ROOT + "."):
                    found.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            if not mod.startswith(PACKAGE_ROOT):
                continue
            found.append(mod)
            # `from feature_library.a.b import c` may import either a name from
            # module b, or module c from package b. Record both candidates and
            # let the caller keep whichever is a real feature module.
            for alias in node.names:
                found.append(f"{mod}.{alias.name}")
    return sorted(set(found))


def _harness_refs(source: str, tests_root: str) -> list[str]:
    """Find harness contract paths referenced as string literals.

    Simulation tests name their contract by path, e.g.
    ``Path("tests/deposit/.../smart_contract.py")``. Those references are how a
    test is tied to the composed contract it drives.

    Args:
        source: Test module source.
        tests_root: Root of the tests tree, used to normalise the match.

    Returns:
        Referenced paths as written.
    """
    refs = re.findall(r'["\']((?:tests|feature_library/tests)/[^"\']+\.py)["\']', source)
    return sorted(set(refs))


def scan_tests(tests_root: str) -> dict[str, TestModule]:
    """Read every module under the tests tree.

    Args:
        tests_root: Path to the tests directory.

    Returns:
        Mapping of path to :class:`TestModule`.
    """
    out: dict[str, TestModule] = {}
    for dirpath, dirnames, filenames in os.walk(tests_root):
        dirnames[:] = [d for d in dirnames if d != "__pycache__"]
        for fn in filenames:
            if not fn.endswith(".py") or fn == "__init__.py":
                continue
            path = os.path.join(dirpath, fn)
            try:
                with open(path, "r", encoding="utf-8") as fh:
                    source = fh.read()
                tree = ast.parse(source, filename=path)
            except (OSError, SyntaxError):
                continue
            tm = TestModule(path=path)
            tm.tier = _tier_from_path(path)
            tm.imports = _feature_imports(tree)
            tm.markers = sorted(set(_MARKER_RE.findall(source)))
            tm.test_count = len(_TEST_DEF_RE.findall(source))
            tm.is_harness = bool(re.search(r'^api\s*=\s*["\']4\.', source, re.MULTILINE))
            tm.harness_refs = _harness_refs(source, tests_root)
            if tm.tier == "unknown" and tm.markers:
                marker = tm.markers[0]
                tm.tier = {"sim": "simulation", "accelerated_e2e": "e2e"}.get(marker, marker)
            out[path] = tm
    return out


def build_coverage(
    tests: dict[str, TestModule],
    feature_modules: set[str],
    repo_root: str = ".",
) -> dict[str, Coverage]:
    """Attribute tests to features, following harness contracts.

    Args:
        tests: Result of :func:`scan_tests`.
        feature_modules: The set of dotted feature module names to score.
        repo_root: Root used to resolve harness path references.

    Returns:
        Mapping of feature module to :class:`Coverage`.
    """
    coverage = {m: Coverage(module=m) for m in feature_modules}

    harness_by_suffix: dict[str, TestModule] = {}
    for path, tm in tests.items():
        if tm.is_harness:
            norm = os.path.normpath(path).replace("\\", "/")
            harness_by_suffix[norm] = tm

    def resolve_harness(ref: str) -> TestModule | None:
        norm = ref.replace("\\", "/")
        for candidate in (
            norm,
            os.path.join(repo_root, norm).replace("\\", "/"),
            os.path.join(repo_root, "feature_library", norm).replace("\\", "/"),
        ):
            cand = os.path.normpath(candidate).replace("\\", "/")
            if cand in harness_by_suffix:
                return harness_by_suffix[cand]
        tail = norm.split("/")[-3:]
        needle = "/".join(tail)
        for key, tm in harness_by_suffix.items():
            if key.endswith(needle):
                return tm
        return None

    for path, tm in tests.items():
        if tm.is_harness or tm.test_count == 0:
            continue
        tier = tm.tier if tm.tier in {"unit", "simulation", "e2e"} else None
        if tier is None:
            continue
        touched = set(tm.imports)
        for ref in tm.harness_refs:
            harness = resolve_harness(ref)
            if harness is not None:
                touched.update(harness.imports)
        for module in touched:
            cov = coverage.get(module)
            if cov is None:
                continue
            getattr(cov, tier).append(path)

    return coverage
