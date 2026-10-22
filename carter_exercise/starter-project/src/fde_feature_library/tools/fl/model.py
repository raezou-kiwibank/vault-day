"""Data model describing a Smart Contract feature and a product built from features.

These dataclasses are the in-memory form of the Open Knowledge Format (OKF)
records that the library publishes. Every field is either

* **derived** — extracted from the source AST by :mod:`fl.introspect`, and
  therefore guaranteed to match the code, or
* **curated** — authored by a human (or an agent) in the feature's
  ``feature.okf.yaml``, carrying the business meaning that source code cannot
  express.

The split is the whole point: derived fields are regenerated and diffed on
every commit so documentation cannot rot, while curated fields capture the
business intent that reviewers actually need to read.
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field
from typing import Any

# --------------------------------------------------------------------------
# Derived records
# --------------------------------------------------------------------------


@dataclass
class ParameterRef:
    """A Vault parameter a feature expects to be able to read.

    Attributes:
        constant: The module-level constant holding the ``ExpectedParameter``.
        parameter_id: The Vault parameter reference, e.g. ``&{denomination}``.
        optional: Whether the ``ExpectedParameter`` is declared optional.
        triggers_pre_parameter_change_hook: Declared trigger flag.
        triggers_post_parameter_change_hook: Declared trigger flag.
        defined_in: Dotted module that declares the ``ExpectedParameter``. This
            differs from the consuming module whenever a shared parameter such
            as ``denomination`` is re-exported.
    """

    constant: str
    parameter_id: str
    optional: bool = False
    triggers_pre_parameter_change_hook: bool = False
    triggers_post_parameter_change_hook: bool = False
    defined_in: str = ""

    @property
    def bare_id(self) -> str:
        """The parameter id with the ``&{...}`` reference wrapper removed."""
        pid = self.parameter_id
        if pid.startswith("&{") and pid.endswith("}"):
            return pid[2:-1]
        return pid


@dataclass
class FetcherRef:
    """An optimised data fetcher a feature declares.

    Attributes:
        constant: Module-level constant holding the fetcher.
        fetcher_id: The ``fetcher_id`` string the contract addresses it by.
        fetcher_class: The ``contracts_api`` class, e.g.
            ``ParametersObservationFetcher``.
        at: The ``at``/``start`` anchor, when statically determinable.
        filter_summary: Human-readable summary of the fetcher's filter.
        defined_in: Dotted module that declares the fetcher.
    """

    constant: str
    fetcher_id: str
    fetcher_class: str
    at: str | None = None
    filter_summary: str | None = None
    defined_in: str = ""

    @property
    def kind(self) -> str:
        """Coarse classification used for grouping in documentation."""
        cls = self.fetcher_class
        if cls.startswith("Balances"):
            return "balances"
        if cls.startswith("Parameters"):
            return "parameters"
        if cls.startswith("Flags"):
            return "flags"
        if cls.startswith("Calendars"):
            return "calendars"
        if cls.startswith("Postings"):
            return "postings"
        if cls.startswith("LastScheduledEventDateTimes"):
            return "schedules"
        return "other"


@dataclass
class FunctionSig:
    """A public function exposed by a feature module."""

    name: str
    args: list[str] = field(default_factory=list)
    returns: str | None = None
    summary: str = ""
    has_docstring: bool = False
    is_public: bool = True
    lineno: int = 0
    reads_parameters: list[str] = field(default_factory=list)
    """Parameter ids this function reads, resolved through its fetchers_config."""


@dataclass
class InterfaceImpl:
    """A feature's implementation of a library interface.

    Interfaces are ``NamedTuple``\\ s of callables declared in
    ``deposit/interfaces.py`` and ``lending/interfaces.py``. A feature
    "provides" an interface by constructing one at module level; another
    feature "consumes" it by accepting it as an argument.
    """

    constant: str
    interface: str
    members: list[str] = field(default_factory=list)
    lineno: int = 0


@dataclass
class EventTypeDecl:
    """A scheduled event a feature contributes to a contract.

    ``static`` events come from a module-level ``event_types`` list. ``dynamic``
    events come from an ``event_types(product_name=...)`` factory, which
    namespaces the event per product so two features cannot collide.
    """

    names: list[str] = field(default_factory=list)
    style: str = "static"  # static | factory
    factory_args: list[str] = field(default_factory=list)


@dataclass
class ModuleFacts:
    """Everything :mod:`fl.introspect` can prove about one feature module."""

    module: str
    path: str
    domain: str
    is_feature: bool = False
    docstring: str = ""
    summary: str = ""

    expected_parameters: list[ParameterRef] = field(default_factory=list)
    data_fetchers: list[FetcherRef] = field(default_factory=list)
    event_types: EventTypeDecl = field(default_factory=EventTypeDecl)
    notifications: list[str] = field(default_factory=list)
    balance_addresses: list[str] = field(default_factory=list)
    address_constants: dict[str, str] = field(default_factory=dict)
    account_attributes: list[str] = field(default_factory=list)

    functions: list[FunctionSig] = field(default_factory=list)
    interfaces_provided: list[InterfaceImpl] = field(default_factory=list)
    interfaces_consumed: list[str] = field(default_factory=list)
    fetchers_config_types: list[str] = field(default_factory=list)
    fetchers_config_fields: dict[str, str] = field(default_factory=dict)

    imports_internal: list[str] = field(default_factory=list)
    imports_contracts_api: list[str] = field(default_factory=list)

    # Unresolved references, kept so cross-module resolution can complete them.
    raw_parameter_refs: list[tuple[str, str]] = field(default_factory=list)
    raw_fetcher_refs: list[tuple[str, str]] = field(default_factory=list)
    param_id_constants: dict[str, str] = field(default_factory=dict)
    fetcher_id_constants: dict[str, str] = field(default_factory=dict)
    import_aliases: dict[str, str] = field(default_factory=dict)

    hook_affinity: list[str] = field(default_factory=list)
    parse_errors: list[str] = field(default_factory=list)

    @property
    def name(self) -> str:
        """The final segment of the dotted module path."""
        return self.module.rsplit(".", 1)[-1]

    @property
    def public_functions(self) -> list[FunctionSig]:
        """Public functions only, in source order."""
        return [f for f in self.functions if f.is_public]


# --------------------------------------------------------------------------
# Curated records
# --------------------------------------------------------------------------


@dataclass
class RequirementLink:
    """Traceability from a business requirement to this feature.

    Attributes:
        id: Stable requirement identifier, e.g. ``REQ-DEP-014``.
        statement: The requirement in the business analyst's own words.
        source: Where the requirement came from — a ``REQUIREMENTS.md``
            heading, a ticket, a regulation.
        satisfied_by: Names of functions/parameters in this feature that
            implement it, so a reviewer can jump straight to the code.
        verified_by: Test node ids that prove it.
    """

    id: str
    statement: str = ""
    source: str = ""
    satisfied_by: list[str] = field(default_factory=list)
    verified_by: list[str] = field(default_factory=list)


@dataclass
class ParameterDoc:
    """Curated business meaning for one parameter."""

    parameter_id: str
    display_name: str = ""
    description: str = ""
    level: str = ""  # template | instance | global
    shape: str = ""
    example: str = ""
    resource: str = ""  # path to the backing *.resource.yaml
    drives: str = ""  # the behaviour this value changes


@dataclass
class FeatureManifest:
    """The curated half of a feature's OKF record.

    Read from ``feature.okf.yaml`` alongside the module. Everything here is
    business knowledge a compiler cannot infer.
    """

    id: str = ""
    module: str = ""
    version: str = "1.0.0"
    domain: str = ""
    status: str = "draft"  # draft | supported | deprecated
    capability: str = ""
    client_functionality: str = ""
    when_to_use: str = ""
    when_not_to_use: str = ""
    hooks: list[str] = field(default_factory=list)
    parameters: list[ParameterDoc] = field(default_factory=list)
    requirements: list[RequirementLink] = field(default_factory=list)
    products: list[str] = field(default_factory=list)
    simulation_notes: str = ""
    determinism_notes: str = ""
    owner: str = ""
    tags: list[str] = field(default_factory=list)
    source_path: str = ""


@dataclass
class FeatureRecord:
    """A complete OKF record: derived facts joined to curated meaning."""

    facts: ModuleFacts
    manifest: FeatureManifest | None = None

    @property
    def id(self) -> str:
        """Stable identifier for the feature, defaulting to its module path."""
        if self.manifest and self.manifest.id:
            return self.manifest.id
        return self.facts.module

    @property
    def has_manifest(self) -> bool:
        """Whether a curated manifest was found for this feature."""
        return self.manifest is not None


@dataclass
class ProductSpec:
    """A declarative product definition.

    A product is a named composition of features plus the parameter values that
    configure them. Declaring it as data — rather than only as a contract
    template — is what lets the toolchain prove that every feature is exercised
    by a tested product, and lets an agent answer "what would I need to build
    product X" without reading Python.
    """

    id: str = ""
    display_name: str = ""
    domain: str = ""
    tside: str = ""
    version: str = "0.0.1"
    summary: str = ""
    contract: str = ""  # path to the contract template
    features: list[str] = field(default_factory=list)
    hooks: dict[str, list[str]] = field(default_factory=dict)
    parameters: dict[str, Any] = field(default_factory=dict)
    internal_accounts: list[str] = field(default_factory=list)
    balance_addresses: list[str] = field(default_factory=list)
    requirements: list[RequirementLink] = field(default_factory=list)
    tests: dict[str, list[str]] = field(default_factory=dict)
    linked_products: list[dict[str, str]] = field(default_factory=list)
    source_path: str = ""


def asdict(obj: Any) -> Any:
    """Recursively convert a dataclass tree to plain built-ins.

    Args:
        obj: Any dataclass, list, dict or scalar.

    Returns:
        The same structure using only ``dict``, ``list`` and scalars, suitable
        for YAML/JSON serialisation.
    """
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        return {k: asdict(v) for k, v in dataclasses.asdict(obj).items()}
    if isinstance(obj, dict):
        return {k: asdict(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [asdict(v) for v in obj]
    return obj
