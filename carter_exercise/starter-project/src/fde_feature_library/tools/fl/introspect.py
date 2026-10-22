"""Derive verifiable facts about feature modules from their source AST.

Smart Contract features follow a strict, repeatable module shape: reference
parameters are declared as ``ExpectedParameter`` constants keyed by ``&{id}``
strings, optimised data fetchers are declared as module-level constants, and
the module publishes ``expected_parameters`` / ``data_fetchers`` /
``event_types`` lists for a contract to aggregate.

Because the shape is strict, it can be read statically. That matters for two
reasons: the private ``contracts_api`` wheel is not importable in CI or in a
pre-commit hook, and importing contract code to inspect it would execute it.
Parsing gives the same answers with neither cost.

Resolution happens in two passes. The first pass reads each module in
isolation, recording references it cannot yet resolve (``denomination_module``
``.DENOMINATION_PARAM`` means nothing without the import table). The second
pass walks the whole tree and completes those references, including starred
re-exports such as ``*interest_accrual.expected_parameters``.
"""

from __future__ import annotations

import ast
import os
from typing import Iterable

from .model import (
    EventTypeDecl,
    FetcherRef,
    FunctionSig,
    InterfaceImpl,
    ModuleFacts,
    ParameterRef,
)

FEATURE_MARKER = "__smart_contract_feature__"
PACKAGE_ROOT = "feature_library"

FETCHER_CLASSES = {
    "BalancesObservationFetcher",
    "BalancesIntervalFetcher",
    "BalancesDiscreteIntervalFetcher",
    "ParametersObservationFetcher",
    "ParametersIntervalFetcher",
    "FlagsObservationFetcher",
    "FlagsIntervalFetcher",
    "CalendarsObservationFetcher",
    "CalendarsIntervalFetcher",
    "PostingsIntervalFetcher",
    "LastScheduledEventDateTimesObservationFetcher",
}

INTERFACE_MODULE_SUFFIXES = ("interfaces",)

# Function-name conventions that reveal which hook a feature plugs into.
# These are a *suggestion* only: the curated manifest declares the authoritative
# hook set and :mod:`fl.validate` flags any disagreement for a human to settle.
HOOK_AFFINITY_RULES: list[tuple[tuple[str, ...], str]] = [
    (("get_scheduled_events",), "activation_hook"),
    (("schedule_logic", "apply_fees", "apply_", "accrue_", "handle_schedule"), "scheduled_event_hook"),
    (("validate", "pre_posting", "reject_"), "pre_posting_hook"),
    (("post_posting", "charge_", "track_", "allocate_"), "post_posting_hook"),
    (("deactivation", "close_", "residual_cleanup"), "deactivation_hook"),
    (("derived_parameter", "get_attributes", "attribute"), "derived_parameter_hook"),
    (("validate_parameter", "pre_parameter"), "pre_parameter_change_hook"),
    (("post_parameter",), "post_parameter_change_hook"),
    (("conversion",), "conversion_hook"),
]


# --------------------------------------------------------------------------
# Small AST helpers
# --------------------------------------------------------------------------


def _literal(node: ast.AST) -> object | None:
    """Best-effort evaluation of a literal node.

    Args:
        node: Any AST node.

    Returns:
        The literal value, or ``None`` when the node is not a literal.
    """
    try:
        return ast.literal_eval(node)
    except (ValueError, SyntaxError, TypeError):
        return None


def _dotted(node: ast.AST) -> str | None:
    """Render a ``Name``/``Attribute`` chain back to dotted source text.

    Args:
        node: The node to render.

    Returns:
        The dotted name (``a.b.c``), or ``None`` for any other node type.
    """
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        base = _dotted(node.value)
        return f"{base}.{node.attr}" if base else None
    return None


def _unparse(node: ast.AST | None) -> str | None:
    """Render a node back to source, tolerating unsupported nodes.

    Args:
        node: The node to render, or ``None``.

    Returns:
        Source text, or ``None``.
    """
    if node is None:
        return None
    try:
        return ast.unparse(node)
    except Exception:  # pragma: no cover - defensive; ast.unparse is total in 3.10+
        return None


def _kwarg(call: ast.Call, name: str) -> ast.AST | None:
    """Fetch a keyword argument node from a call by name.

    Args:
        call: The call node.
        name: Keyword name to look for.

    Returns:
        The value node, or ``None`` when the keyword is absent.
    """
    for kw in call.keywords:
        if kw.arg == name:
            return kw.value
    return None


def _first_docstring_line(node: ast.AST) -> str:
    """Return the first line of a node's docstring.

    Args:
        node: A module, function or class node.

    Returns:
        The summary line, or an empty string when undocumented.
    """
    doc = ast.get_docstring(node) or ""
    return doc.strip().split("\n", 1)[0].strip()


def _call_name(node: ast.AST) -> str | None:
    """Return the dotted callee name of a call node.

    Args:
        node: Candidate call node.

    Returns:
        The callee name, or ``None`` when the node is not a call.
    """
    if isinstance(node, ast.Call):
        return _dotted(node.func)
    return None


# --------------------------------------------------------------------------
# Discovery
# --------------------------------------------------------------------------


def module_name_for(path: str, src_root: str) -> str:
    """Convert a file path into its dotted module name.

    Args:
        path: Absolute or relative path to a ``.py`` file.
        src_root: The directory that is on ``sys.path`` (the ``src`` layout
            root), such that ``src_root/feature_library/...`` holds the package.

    Returns:
        The dotted module name, e.g. ``feature_library.deposit.interest.interest_accrual``.
    """
    rel = os.path.relpath(os.path.abspath(path), os.path.abspath(src_root))
    rel = rel[:-3] if rel.endswith(".py") else rel
    parts = [p for p in rel.split(os.sep) if p]
    if parts and parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts)


def domain_for(module: str) -> str:
    """Infer the domain segment of a module path.

    Args:
        module: Dotted module name.

    Returns:
        The domain (``common``, ``deposit``, ``lending``, ...), or an empty
        string when the module sits directly under the package root.
    """
    parts = module.split(".")
    if len(parts) >= 2 and parts[0] == PACKAGE_ROOT:
        return parts[1]
    return ""


def discover_modules(src_root: str) -> list[str]:
    """Find every Python module under the package root.

    Args:
        src_root: The ``src`` layout root containing ``feature_library/``.

    Returns:
        Sorted list of file paths, excluding ``__init__.py`` files, which carry
        no feature content in this library.
    """
    package_dir = os.path.join(src_root, PACKAGE_ROOT)
    found: list[str] = []
    for dirpath, dirnames, filenames in os.walk(package_dir):
        dirnames[:] = [d for d in dirnames if d != "__pycache__"]
        for fn in filenames:
            if fn.endswith(".py") and fn != "__init__.py":
                found.append(os.path.join(dirpath, fn))
    return sorted(found)


# --------------------------------------------------------------------------
# Pass 1 — per-module extraction
# --------------------------------------------------------------------------


class _ModuleReader:
    """Extracts facts from a single parsed module."""

    def __init__(self, module: str, path: str, tree: ast.Module) -> None:
        """Initialise the reader.

        Args:
            module: Dotted module name.
            path: Source file path.
            tree: Parsed module AST.
        """
        self.module = module
        self.path = path
        self.tree = tree
        self.facts = ModuleFacts(module=module, path=path, domain=domain_for(module))

    def read(self) -> ModuleFacts:
        """Run every extraction step.

        Returns:
            The populated (but not yet cross-module resolved) facts.
        """
        f = self.facts
        f.docstring = ast.get_docstring(self.tree) or ""
        f.summary = _first_docstring_line(self.tree)

        self._read_imports()
        self._read_assignments()
        self._read_functions()
        self._infer_hook_affinity()
        return f

    # -- imports ---------------------------------------------------------

    def _read_imports(self) -> None:
        """Record the import table, aliases and contracts_api surface."""
        f = self.facts
        for node in self.tree.body:
            if isinstance(node, ast.Import):
                for alias in node.names:
                    local = alias.asname or alias.name.split(".")[0]
                    f.import_aliases[local] = alias.name
                    if alias.name.startswith(PACKAGE_ROOT + "."):
                        f.imports_internal.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                mod = node.module or ""
                if mod == "contracts_api":
                    f.imports_contracts_api.extend(a.name for a in node.names)
                for alias in node.names:
                    local = alias.asname or alias.name
                    f.import_aliases[local] = f"{mod}.{alias.name}" if mod else alias.name
                if mod.startswith(PACKAGE_ROOT):
                    f.imports_internal.append(mod)
        f.imports_internal = sorted(set(f.imports_internal))
        f.imports_contracts_api = sorted(set(f.imports_contracts_api))

    # -- assignments -----------------------------------------------------

    def _read_assignments(self) -> None:
        """Walk module-level assignments and classify each one."""
        for node in self.tree.body:
            if not isinstance(node, (ast.Assign, ast.AnnAssign)):
                continue
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            value = node.value
            if value is None:
                continue
            for target in targets:
                name = _dotted(target)
                if not name or "." in name:
                    continue
                self._classify_assignment(name, value, node.lineno)

    def _classify_assignment(self, name: str, value: ast.AST, lineno: int) -> None:
        """Classify one module-level assignment.

        Args:
            name: The assigned constant name.
            value: The assigned value node.
            lineno: Source line, retained for diagnostics.
        """
        f = self.facts

        if name == FEATURE_MARKER:
            f.is_feature = _literal(value) is True
            return

        literal = _literal(value)

        # Parameter id constants: FOO_PARAM_ID = "&{foo}"
        if isinstance(literal, str):
            if name.endswith("_PARAM_ID") or (literal.startswith("&{") and literal.endswith("}")):
                f.param_id_constants[name] = literal
            elif name.endswith(("_POF_ID", "_BOF_ID", "_BIF_ID", "_BDIF_ID", "_PIF_ID",
                                "_FOF_ID", "_FIF_ID", "_COF_ID", "_CIF_ID", "_POSTIF_ID",
                                "_SOF_ID", "_FETCHER_ID")):
                f.fetcher_id_constants[name] = literal
            elif "NOTIFICATION" in name:
                f.notifications.append(literal)
            # Address modules are plain UPPER = "UPPER" constant tables.
            if self.module.endswith(".addresses") and name.isupper():
                f.address_constants[name] = literal

        callee = _call_name(value)

        if callee and callee.endswith("ExpectedParameter"):
            self._read_expected_parameter(name, value, lineno)
            return

        if callee and callee.split(".")[-1] in FETCHER_CLASSES:
            self._read_fetcher(name, value, callee)
            return

        if callee and callee.split(".")[-1] == "Attribute":
            attr_name = _kwarg(value, "name")
            lit = _literal(attr_name) if attr_name is not None else None
            if isinstance(lit, str):
                f.account_attributes.append(lit)
            return

        if callee and self._is_interface_call(callee):
            f.interfaces_provided.append(
                InterfaceImpl(
                    constant=name,
                    interface=callee.split(".")[-1],
                    members=[kw.arg for kw in value.keywords if kw.arg],  # type: ignore[union-attr]
                    lineno=lineno,
                )
            )
            return

        if callee and callee.split(".")[-1] == "NamedTuple" and name.endswith("FetchersConfig"):
            f.fetchers_config_types.append(name)
            return

        # DEFAULT_X_FETCHERS_CONFIG = XFetchersConfig(denomination_param_id=DENOMINATION_PARAM_ID, ...)
        # This is the table that lets a function's `fetchers_config.<field>` access be
        # resolved back to the concrete parameter it reads.
        if callee and callee.endswith("FetchersConfig") and isinstance(value, ast.Call):
            for kw in value.keywords:
                if not kw.arg or not kw.arg.endswith("_param_id"):
                    continue
                lit = _literal(kw.value)
                if isinstance(lit, str):
                    f.fetchers_config_fields[kw.arg] = lit
                    continue
                ref = _dotted(kw.value)
                if ref:
                    f.fetchers_config_fields[kw.arg] = f"@unresolved:{ref}"
            return

        if name == "expected_parameters":
            f.raw_parameter_refs.extend(self._collect_refs(value))
            return

        if name == "data_fetchers":
            f.raw_fetcher_refs.extend(self._collect_refs(value))
            return

        if name == "event_types":
            f.event_types = self._read_static_event_types(value)
            return

        if name == "attributes":
            return

    def _is_interface_call(self, callee: str) -> bool:
        """Whether a callee names an interface constructor.

        Args:
            callee: Dotted callee name.

        Returns:
            True when the call targets a NamedTuple from an ``interfaces``
            module, e.g. ``deposit_interfaces.InterestType``.
        """
        parts = callee.split(".")
        if len(parts) < 2:
            return False
        base = parts[0]
        resolved = self.facts.import_aliases.get(base, base)
        return any(resolved.endswith(sfx) for sfx in INTERFACE_MODULE_SUFFIXES)

    def _read_expected_parameter(self, name: str, call: ast.AST, lineno: int) -> None:
        """Record an ``ExpectedParameter`` constant.

        Args:
            name: Constant name.
            call: The ``ExpectedParameter(...)`` call node.
            lineno: Source line.
        """
        assert isinstance(call, ast.Call)
        f = self.facts
        id_node = _kwarg(call, "id")
        pid = ""
        if id_node is not None:
            lit = _literal(id_node)
            if isinstance(lit, str):
                pid = lit
            else:
                ref = _dotted(id_node)
                if ref:
                    pid = f.param_id_constants.get(ref, "")
                    if not pid and "." in ref:
                        pid = f"@unresolved:{ref}"
        f.expected_parameters.append(
            ParameterRef(
                constant=name,
                parameter_id=pid,
                optional=bool(_literal(_kwarg(call, "optional") or ast.Constant(False))),
                triggers_pre_parameter_change_hook=bool(
                    _literal(_kwarg(call, "triggers_pre_parameter_change_hook") or ast.Constant(False))
                ),
                triggers_post_parameter_change_hook=bool(
                    _literal(_kwarg(call, "triggers_post_parameter_change_hook") or ast.Constant(False))
                ),
                defined_in=self.module,
            )
        )

    def _read_fetcher(self, name: str, call: ast.AST, callee: str) -> None:
        """Record a data fetcher constant.

        Args:
            name: Constant name.
            call: The fetcher constructor call node.
            callee: Dotted callee name.
        """
        assert isinstance(call, ast.Call)
        f = self.facts
        fid_node = _kwarg(call, "fetcher_id")
        fid = ""
        if fid_node is not None:
            lit = _literal(fid_node)
            if isinstance(lit, str):
                fid = lit
            else:
                ref = _dotted(fid_node)
                if ref:
                    fid = f.fetcher_id_constants.get(ref, f"@unresolved:{ref}")
        at_node = _kwarg(call, "at") or _kwarg(call, "start")
        filt = _kwarg(call, "filter")
        f.data_fetchers.append(
            FetcherRef(
                constant=name,
                fetcher_id=fid,
                fetcher_class=callee.split(".")[-1],
                at=_unparse(at_node),
                filter_summary=_unparse(filt),
                defined_in=self.module,
            )
        )

    def _collect_refs(self, value: ast.AST) -> list[tuple[str, str]]:
        """Collect entries of an aggregation list.

        Args:
            value: The list node assigned to ``expected_parameters`` or
                ``data_fetchers``.

        Returns:
            ``(kind, reference)`` pairs where kind is ``name`` for a direct
            reference and ``star`` for a ``*module.attr`` re-export.
        """
        refs: list[tuple[str, str]] = []
        if isinstance(value, ast.Call):
            # e.g. parameter_utils.distinct_expected_parameters([...])
            for arg in value.args:
                refs.extend(self._collect_refs(arg))
            return refs
        if not isinstance(value, (ast.List, ast.Tuple)):
            dotted = _dotted(value)
            if dotted:
                refs.append(("name", dotted))
            return refs
        for elt in value.elts:
            if isinstance(elt, ast.Starred):
                inner = _dotted(elt.value)
                if inner:
                    refs.append(("star", inner))
                elif isinstance(elt.value, ast.ListComp):
                    refs.append(("star", "@listcomp"))
            else:
                dotted = _dotted(elt)
                if dotted:
                    refs.append(("name", dotted))
        return refs

    def _read_static_event_types(self, value: ast.AST) -> EventTypeDecl:
        """Extract event names from a module-level ``event_types`` list.

        Args:
            value: The assigned list node.

        Returns:
            A static :class:`EventTypeDecl`.
        """
        names: list[str] = []
        if isinstance(value, (ast.List, ast.Tuple)):
            for elt in value.elts:
                if isinstance(elt, ast.Call):
                    name_node = _kwarg(elt, "name")
                    lit = _literal(name_node) if name_node is not None else None
                    if isinstance(lit, str):
                        names.append(lit)
                    else:
                        ref = _dotted(name_node) if name_node is not None else None
                        if ref:
                            names.append(f"@ref:{ref}")
                elif isinstance(elt, ast.Starred):
                    inner = _dotted(elt.value)
                    if inner:
                        names.append(f"@star:{inner}")
        return EventTypeDecl(names=names, style="static")

    # -- functions -------------------------------------------------------

    def _read_functions(self) -> None:
        """Record every module-level function signature."""
        f = self.facts
        for node in self.tree.body:
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if node.name == "event_types":
                f.event_types = EventTypeDecl(
                    names=self._event_names_from_factory(node),
                    style="factory",
                    factory_args=[a.arg for a in node.args.args + node.args.kwonlyargs],
                )
            args = [a.arg for a in node.args.posonlyargs + node.args.args + node.args.kwonlyargs]
            f.functions.append(
                FunctionSig(
                    name=node.name,
                    args=args,
                    returns=_unparse(node.returns),
                    summary=_first_docstring_line(node),
                    has_docstring=ast.get_docstring(node) is not None,
                    is_public=not node.name.startswith("_"),
                    lineno=node.lineno,
                    reads_parameters=self._config_fields_read(node),
                )
            )
            self._read_consumed_interfaces(node)

    def _config_fields_read(self, node: ast.AST) -> list[str]:
        """Collect ``fetchers_config.<field>`` accesses inside a function.

        Features read parameters indirectly: the caller supplies a
        ``fetchers_config`` naming which parameter id to use, and the function
        looks the value up by that id. Recording the fields accessed therefore
        records which parameters the function depends on, remapping and all.

        Args:
            node: The function node.

        Returns:
            The ``*_param_id`` field names accessed, in first-seen order.
        """
        seen: list[str] = []
        for sub in ast.walk(node):
            if isinstance(sub, ast.Attribute) and isinstance(sub.value, ast.Name):
                if sub.value.id in {"fetchers_config", "config"} and sub.attr.endswith("_param_id"):
                    if sub.attr not in seen:
                        seen.append(sub.attr)
        return seen

    def _event_names_from_factory(self, node: ast.AST) -> list[str]:
        """Extract event-name expressions from an ``event_types`` factory.

        Args:
            node: The factory function node.

        Returns:
            Rendered name expressions, e.g. ``f'{product_name}_ACCRUE_INTEREST'``.
        """
        names: list[str] = []
        for sub in ast.walk(node):
            if isinstance(sub, ast.Call) and (_dotted(sub.func) or "").endswith(
                "SmartContractEventType"
            ):
                name_node = _kwarg(sub, "name")
                rendered = _unparse(name_node) if name_node is not None else None
                if rendered:
                    names.append(rendered)
        return names

    def _read_consumed_interfaces(self, node: ast.AST) -> None:
        """Record interfaces a function accepts as arguments.

        Args:
            node: The function node whose annotations are inspected.
        """
        f = self.facts
        assert isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        all_args = node.args.posonlyargs + node.args.args + node.args.kwonlyargs
        for arg in all_args:
            ann = _unparse(arg.annotation)
            if not ann:
                continue
            if "interfaces." in ann:
                for token in ann.replace("|", " ").replace("[", " ").replace("]", " ").split():
                    if "interfaces." in token:
                        f.interfaces_consumed.append(token.split("interfaces.")[-1].strip(",()"))

    # -- hooks -----------------------------------------------------------

    def _infer_hook_affinity(self) -> None:
        """Suggest the hooks this feature plugs into from its function names."""
        f = self.facts
        found: list[str] = []
        for fn in f.public_functions:
            for prefixes, hook in HOOK_AFFINITY_RULES:
                if any(fn.name == p or fn.name.startswith(p) for p in prefixes):
                    found.append(hook)
                    break
        # A function returning Rejection is a validation function regardless of name.
        for fn in f.public_functions:
            if fn.returns and "Rejection" in fn.returns and "pre_posting_hook" not in found:
                found.append("pre_posting_hook")
        seen: list[str] = []
        for h in found:
            if h not in seen:
                seen.append(h)
        f.hook_affinity = seen


def read_module(path: str, src_root: str) -> ModuleFacts:
    """Parse one module and extract its facts.

    Args:
        path: Path to the ``.py`` file.
        src_root: The ``src`` layout root.

    Returns:
        The module's facts. Parse failures are captured in
        :attr:`ModuleFacts.parse_errors` rather than raised, so one bad file
        cannot stop a whole-tree scan.
    """
    module = module_name_for(path, src_root)
    try:
        with open(path, "r", encoding="utf-8") as fh:
            source = fh.read()
        tree = ast.parse(source, filename=path)
    except (OSError, SyntaxError) as exc:
        facts = ModuleFacts(module=module, path=path, domain=domain_for(module))
        facts.parse_errors.append(str(exc))
        return facts
    return _ModuleReader(module, path, tree).read()


# --------------------------------------------------------------------------
# Pass 2 — cross-module resolution
# --------------------------------------------------------------------------


def _resolve_ref(
    ref: str,
    owner: ModuleFacts,
    index: dict[str, ModuleFacts],
) -> tuple[ModuleFacts | None, str]:
    """Resolve a dotted reference to its defining module and attribute.

    Args:
        ref: Dotted reference as written in source, e.g.
            ``denomination_module.DENOMINATION_PARAM`` or ``MAX_WITHDRAWAL_PARAM``.
        owner: The module the reference appears in.
        index: Whole-tree module index keyed by dotted module name.

    Returns:
        ``(defining_module_facts, attribute_name)``. The module is ``None``
        when the reference is local or cannot be resolved.
    """
    if "." not in ref:
        return owner, ref
    base, _, attr = ref.rpartition(".")
    target = owner.import_aliases.get(base)
    if target and target in index:
        return index[target], attr
    if base in index:
        return index[base], attr
    return None, attr


def resolve_tree(facts_by_module: dict[str, ModuleFacts], max_depth: int = 6) -> None:
    """Complete cross-module references in place.

    Expands ``*module.expected_parameters`` re-exports and resolves references
    such as ``denomination_module.DENOMINATION_PARAM`` to the concrete
    ``&{denomination}`` parameter, so each feature's declared surface is the
    full transitive set a contract must satisfy.

    Args:
        facts_by_module: The whole-tree index, mutated in place.
        max_depth: Recursion limit guarding against import cycles.
    """
    param_cache: dict[str, list[ParameterRef]] = {}
    fetcher_cache: dict[str, list[FetcherRef]] = {}

    def params_for(mod: ModuleFacts, depth: int) -> list[ParameterRef]:
        if mod.module in param_cache:
            return param_cache[mod.module]
        if depth > max_depth:
            return []
        param_cache[mod.module] = []  # cycle guard
        local = {p.constant: p for p in mod.expected_parameters}
        out: list[ParameterRef] = []
        for kind, ref in mod.raw_parameter_refs:
            if kind == "star":
                target, attr = _resolve_ref(ref, mod, facts_by_module)
                if target is not None and attr == "expected_parameters":
                    out.extend(params_for(target, depth + 1))
                continue
            target, attr = _resolve_ref(ref, mod, facts_by_module)
            if target is mod or target is None:
                if attr in local:
                    out.append(local[attr])
                continue
            match = next((p for p in target.expected_parameters if p.constant == attr), None)
            if match is not None:
                out.append(match)
        param_cache[mod.module] = _dedupe_params(out)
        return param_cache[mod.module]

    def fetchers_for(mod: ModuleFacts, depth: int) -> list[FetcherRef]:
        if mod.module in fetcher_cache:
            return fetcher_cache[mod.module]
        if depth > max_depth:
            return []
        fetcher_cache[mod.module] = []
        local = {f.constant: f for f in mod.data_fetchers}
        out: list[FetcherRef] = []
        for kind, ref in mod.raw_fetcher_refs:
            if kind == "star":
                target, attr = _resolve_ref(ref, mod, facts_by_module)
                if target is not None and attr == "data_fetchers":
                    out.extend(fetchers_for(target, depth + 1))
                continue
            target, attr = _resolve_ref(ref, mod, facts_by_module)
            if target is mod or target is None:
                if attr in local:
                    out.append(local[attr])
                continue
            match = next((f for f in target.data_fetchers if f.constant == attr), None)
            if match is not None:
                out.append(match)
        fetcher_cache[mod.module] = _dedupe_fetchers(out)
        return fetcher_cache[mod.module]

    for mod in facts_by_module.values():
        declared_params = params_for(mod, 0)
        if declared_params:
            mod.expected_parameters = declared_params
        declared_fetchers = fetchers_for(mod, 0)
        if declared_fetchers:
            mod.data_fetchers = declared_fetchers

    _resolve_addresses(facts_by_module)
    _resolve_event_refs(facts_by_module)
    _resolve_parameter_reads(facts_by_module)


def _resolve_parameter_reads(index: dict[str, ModuleFacts]) -> None:
    """Turn each function's config-field accesses into concrete parameter ids.

    Args:
        index: The whole-tree module index, mutated in place.
    """
    for mod in index.values():
        table: dict[str, str] = {}
        for field_name, value in mod.fetchers_config_fields.items():
            if value.startswith("@unresolved:"):
                ref = value[len("@unresolved:") :]
                if "." not in ref:
                    resolved = mod.param_id_constants.get(ref)
                else:
                    target, attr = _resolve_ref(ref, mod, index)
                    resolved = target.param_id_constants.get(attr) if target else None
                if resolved:
                    table[field_name] = resolved
            else:
                table[field_name] = value
        mod.fetchers_config_fields = table

        declared = {p.parameter_id for p in mod.expected_parameters}
        for fn in mod.functions:
            resolved_ids: list[str] = []
            for field_name in fn.reads_parameters:
                pid = table.get(field_name)
                if pid and pid in declared and pid not in resolved_ids:
                    resolved_ids.append(pid)
            fn.reads_parameters = resolved_ids


def _dedupe_params(items: Iterable[ParameterRef]) -> list[ParameterRef]:
    """Remove duplicate parameters, keeping first occurrence.

    Args:
        items: Parameter references, possibly with repeats.

    Returns:
        Deduplicated list preserving order.
    """
    seen: set[str] = set()
    out: list[ParameterRef] = []
    for p in items:
        key = p.parameter_id or p.constant
        if key in seen:
            continue
        seen.add(key)
        out.append(p)
    return out


def _dedupe_fetchers(items: Iterable[FetcherRef]) -> list[FetcherRef]:
    """Remove duplicate fetchers, keeping first occurrence.

    Args:
        items: Fetcher references, possibly with repeats.

    Returns:
        Deduplicated list preserving order.
    """
    seen: set[str] = set()
    out: list[FetcherRef] = []
    for f in items:
        key = f.fetcher_id or f.constant
        if key in seen:
            continue
        seen.add(key)
        out.append(f)
    return out


def _resolve_addresses(index: dict[str, ModuleFacts]) -> None:
    """Attribute balance addresses to the features that reference them.

    Args:
        index: The whole-tree module index, mutated in place.
    """
    address_tables: dict[str, dict[str, str]] = {
        mod.module: mod.address_constants for mod in index.values() if mod.address_constants
    }
    for mod in index.values():
        if mod.address_constants:
            mod.balance_addresses = sorted(set(mod.address_constants.values()))
            continue
        used: set[str] = set()
        try:
            with open(mod.path, "r", encoding="utf-8") as fh:
                source = fh.read()
        except OSError:
            continue
        for target_module, table in address_tables.items():
            alias = next(
                (a for a, full in mod.import_aliases.items() if full == target_module), None
            )
            if not alias:
                continue
            for const, literal in table.items():
                if f"{alias}.{const}" in source:
                    used.add(literal)
        mod.balance_addresses = sorted(used)


def _resolve_event_refs(index: dict[str, ModuleFacts]) -> None:
    """Replace ``@ref:``/``@star:`` placeholders in event type names.

    Args:
        index: The whole-tree module index, mutated in place.
    """
    for mod in index.values():
        resolved: list[str] = []
        for name in mod.event_types.names:
            if mod.event_types.style == "factory" and name.isidentifier():
                # A factory that names a module constant, e.g. `APPLICATION_EVENT`.
                resolved.append(_lookup_string_constant(mod, name) or name)
            elif name.startswith("@ref:"):
                ref = name[len("@ref:") :]
                target, attr = _resolve_ref(ref, mod, index)
                literal = None
                if target is not None:
                    literal = _lookup_string_constant(target, attr)
                resolved.append(literal or ref)
            elif name.startswith("@star:"):
                ref = name[len("@star:") :]
                target, attr = _resolve_ref(ref, mod, index)
                if target is not None and attr == "event_types":
                    resolved.extend(target.event_types.names)
                else:
                    resolved.append(ref)
            else:
                resolved.append(name)
        mod.event_types.names = resolved


def _lookup_string_constant(mod: ModuleFacts, name: str) -> str | None:
    """Find a module-level string constant by name.

    Args:
        mod: The module to search.
        name: Constant name.

    Returns:
        The string value, or ``None``.
    """
    for table in (mod.param_id_constants, mod.fetcher_id_constants, mod.address_constants):
        if name in table:
            return table[name]
    try:
        with open(mod.path, "r", encoding="utf-8") as fh:
            tree = ast.parse(fh.read(), filename=mod.path)
    except (OSError, SyntaxError):
        return None
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name) and t.id == name:
                    lit = _literal(node.value)
                    if isinstance(lit, str):
                        return lit
    return None


def scan(src_root: str) -> dict[str, ModuleFacts]:
    """Scan the whole feature library and return fully resolved facts.

    Args:
        src_root: The ``src`` layout root containing ``feature_library/``.

    Returns:
        Mapping of dotted module name to resolved :class:`ModuleFacts`.
    """
    index: dict[str, ModuleFacts] = {}
    for path in discover_modules(src_root):
        facts = read_module(path, src_root)
        index[facts.module] = facts
    resolve_tree(index)
    return index
