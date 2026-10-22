"""Publish the library as a Feature Knowledge Bundle.

The bundle is the artefact an AI agent or a downstream team consumes. It
conforms to Google Cloud's **Open Knowledge Format v0.2**, whose conformance
rules are deliberately small:

1. every non-reserved ``.md`` file in the tree carries parseable YAML
   frontmatter,
2. every frontmatter block has a non-empty ``type``,
3. the reserved filenames ``index.md`` and ``log.md`` follow the spec's
   structure when present.

Everything else OKF defines is optional and extensible — "Producers MAY include
any additional keys" — so the bundle layers a domain profile on top, carrying
the Vault-specific facts (parameters and their CLU resources, fetchers, hooks,
events, interfaces, tests, traceability) that make the library usable without
reading Python.

Two deliberate choices:

* **The format is called a Feature Knowledge Bundle, not "OKF".** ``okf_version``
  appears as a field, never as this project's own name — partly because the spec
  is Google's, and partly because "OKF" has meant the Open Knowledge Foundation
  since 2004.
* **No wall-clock timestamp is written.** The generator is expected to run in CI
  and its output diffed against the committed bundle; a ``generated.at`` of "now"
  would make every run differ. Provenance is carried instead by a content digest
  of the source the document was derived from, which changes only when the
  source does. OKF makes ``generated.at`` optional, so this stays conformant.
"""

from __future__ import annotations

import hashlib
import os
import re
from typing import Any

from . import docgen
from .model import ModuleFacts
from .resources import ResourceIndex
from .tests_index import Coverage

OKF_VERSION = "0.2"
PROFILE = "https://thoughtmachine.example/fde/schemas/feature-knowledge-bundle/1.0.json"
PROFILE_VERSION = "1.0.0"

TYPE_FEATURE = "Vault Feature"
TYPE_PRODUCT = "Vault Product"
TYPE_PARAMETER = "Vault Parameter"
TYPE_INTERFACE = "Vault Interface"
TYPE_INDEX = "Index"

GENERATED_END = "<!-- generated:end -->"

_NUMERIC_RE = re.compile(r"^[+-]?(\d+|\d*\.\d+)([eE][+-]?\d+)?$")


def _fm_scalar(value: Any) -> str:
    """Render a frontmatter scalar.

    Args:
        value: The value to render.

    Returns:
        YAML text for the value.
    """
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    text = str(value).replace("\n", " ").strip()
    # A string that would parse back as a number must be quoted, or a version
    # like "0.2" silently round-trips as the float 0.2.
    looks_numeric = bool(_NUMERIC_RE.match(text))
    needs_quotes = (
        not text
        or looks_numeric
        or text[0] in "&*?|-<>=!%@`{[\"'#"
        or ": " in text
        or text.endswith(":")
        or text in {"true", "false", "null", "yes", "no"}
    )
    if needs_quotes:
        return '"' + text.replace("\\", "\\\\").replace('"', '\\"') + '"'
    return text


def _frontmatter(fields: dict[str, Any], indent: int = 0) -> list[str]:
    """Render a frontmatter mapping as YAML lines.

    Args:
        fields: The mapping to render; insertion order is preserved.
        indent: Current indentation depth.

    Returns:
        The rendered lines, without the surrounding ``---`` fences.
    """
    pad = " " * indent
    lines: list[str] = []
    for key, value in fields.items():
        if isinstance(value, dict):
            if not value:
                continue
            lines.append(f"{pad}{key}:")
            lines.extend(_frontmatter(value, indent + 2))
        elif isinstance(value, list):
            if not value:
                lines.append(f"{pad}{key}: []")
                continue
            lines.append(f"{pad}{key}:")
            for item in value:
                if isinstance(item, dict):
                    inner = _frontmatter(item, indent + 4)
                    if inner:
                        first = inner[0].strip()
                        lines.append(f"{pad}  - {first}")
                        lines.extend(inner[1:])
                else:
                    lines.append(f"{pad}  - {_fm_scalar(item)}")
        else:
            lines.append(f"{pad}{key}: {_fm_scalar(value)}")
    return lines


def render_document(fields: dict[str, Any], body: str, preserved: str = "") -> str:
    """Assemble one OKF document.

    Args:
        fields: Frontmatter fields. ``type`` must be present and non-empty.
        body: Generated markdown body.
        preserved: Hand-written prose to place below the generated marker, which
            the generator carries forward untouched on the next run.

    Returns:
        The complete document text.
    """
    assert fields.get("type"), "OKF requires a non-empty `type` in every document"
    out = ["---"]
    out.extend(_frontmatter(fields))
    out.append("---")
    out.append("")
    out.append(body.rstrip())
    out.append("")
    out.append(GENERATED_END)
    if preserved.strip():
        out.append("")
        out.append(preserved.strip())
    out.append("")
    return "\n".join(out)


def read_preserved(path: str) -> str:
    """Recover hand-written prose from an existing document.

    Args:
        path: Path to a previously generated document.

    Returns:
        Everything below the generated marker, or an empty string.
    """
    if not os.path.isfile(path):
        return ""
    try:
        with open(path, "r", encoding="utf-8") as fh:
            text = fh.read()
    except OSError:
        return ""
    _, marker, tail = text.partition(GENERATED_END)
    return tail if marker else ""


def digest_of_file(path: str) -> str:
    """Compute the sha256 of a source file.

    Args:
        path: File to hash.

    Returns:
        ``sha256:<hex>``, or an empty string when unreadable.
    """
    try:
        with open(path, "rb") as fh:
            return "sha256:" + hashlib.sha256(fh.read()).hexdigest()
    except OSError:
        return ""


# --------------------------------------------------------------------------
# Documents
# --------------------------------------------------------------------------


def feature_document(
    facts: ModuleFacts,
    record: dict[str, Any] | None,
    resource_index: ResourceIndex,
    coverage: Coverage | None,
    dependents: list[str],
    products: list[str],
    repo_root: str,
    library_version: str,
    generator: str,
) -> tuple[dict[str, Any], str]:
    """Build the frontmatter and body for one feature.

    Args:
        facts: Resolved module facts.
        record: The curated authoring record, when one exists.
        resource_index: CLU resource definitions.
        coverage: Test coverage for the feature.
        dependents: Modules importing this feature.
        products: Products composing this feature.
        repo_root: Repository root, for relative paths.
        library_version: The feature library package version.
        generator: Generator identity for provenance.

    Returns:
        ``(frontmatter, body)``.
    """
    rec = record or {}
    short = facts.module.replace("feature_library.", "")
    rel_source = os.path.relpath(facts.path, repo_root)

    kind = "primary"
    if facts.name in {"addresses"}:
        kind = "addresses"
    elif facts.name in {"interfaces"}:
        kind = "interface"
    elif facts.name.endswith("_utils") or facts.name in {"tuples", "fetchers", "common"}:
        kind = "utility"
    elif facts.module.split(".")[-2:-1] == ["secondary"]:
        kind = "secondary"

    parameters = []
    for p in facts.expected_parameters:
        rd = resource_index.parameters.get(p.bare_id)
        doc = next(
            (d for d in (rec.get("parameters") or [])
             if isinstance(d, dict) and d.get("parameter_id") == p.parameter_id),
            {},
        )
        parameters.append({
            "id": p.parameter_id,
            "clu_id": p.bare_id,
            "constant": p.constant,
            "ownership": "owned" if p.defined_in == facts.module else "consumed",
            "owner_feature": p.defined_in.replace("feature_library.", ""),
            "level": (doc.get("level") or "template").upper(),
            "constraint": rd.constraint_kind if rd else "",
            "clu_resource": os.path.relpath(rd.path, repo_root) if rd else "",
            "optional": p.optional,
            "triggers_pre_parameter_change_hook": p.triggers_pre_parameter_change_hook,
            "triggers_post_parameter_change_hook": p.triggers_post_parameter_change_hook,
            "description": doc.get("description", ""),
            "drives": doc.get("drives", ""),
        })

    fields: dict[str, Any] = {
        "type": TYPE_FEATURE,
        "okf_version": OKF_VERSION,
        "profile": PROFILE,
        "profile_version": PROFILE_VERSION,
        "title": rec.get("display_name") or facts.name.replace("_", " ").title(),
        "description": (rec.get("capability") or facts.summary
                        or f"Smart Contract feature {short}."),
        "status": {"supported": "stable", "draft": "draft",
                   "deprecated": "deprecated"}.get(rec.get("status", ""), "draft"),
        "tags": rec.get("tags") or [facts.domain or "common"],
        "identity": {
            "id": facts.module,
            "module": facts.module,
            "source_path": rel_source,
            "kind": kind,
            "domain": facts.domain or "common",
        },
        "version": {
            "library_version": library_version,
            "content_hash": digest_of_file(facts.path),
        },
        "generated": {"by": generator},
        "hooks": rec.get("hooks") or facts.hook_affinity,
        "entry_points": [
            {"name": fn.name, "returns": fn.returns or "", "reads_parameters": fn.reads_parameters}
            for fn in facts.public_functions
        ],
        "parameters": parameters,
        "data_fetchers": [
            {"fetcher_id": f.fetcher_id, "kind": f.fetcher_class,
             "declared_in": f.defined_in.replace("feature_library.", "")}
            for f in facts.data_fetchers
        ],
        "events": facts.event_types.names,
        "event_style": facts.event_types.style,
        "notifications": facts.notifications,
        "balance_addresses": facts.balance_addresses,
        "interfaces": {
            "provides": [i.interface for i in facts.interfaces_provided],
            "consumes": sorted(set(facts.interfaces_consumed)),
        },
        "dependencies": {
            "features": [m.replace("feature_library.", "")
                         for m in facts.imports_internal if m != facts.module],
            "used_by": [m.replace("feature_library.", "") for m in dependents],
        },
        "tests": {
            "unit": len(coverage.unit) if coverage else 0,
            "simulation": len(coverage.simulation) if coverage else 0,
            "e2e": len(coverage.e2e) if coverage else 0,
        },
        "traceability": {
            "business_requirements": [r.get("id") for r in (rec.get("requirements") or [])
                                      if isinstance(r, dict)],
            "used_by_products": products,
        },
        "complete": bool(
            coverage and coverage.has_unit and coverage.has_simulation and products
        ),
    }

    body = docgen.render_feature(
        facts, record, resource_index, coverage, dependents, products, repo_root=repo_root
    )
    return fields, body


def product_document(
    product: dict[str, Any],
    repo_root: str,
    generator: str,
    feature_titles: dict[str, str],
) -> tuple[dict[str, Any], str]:
    """Build the frontmatter and body for one product.

    Args:
        product: The product authoring record.
        repo_root: Repository root.
        generator: Generator identity.
        feature_titles: Feature id to display title, for the body listing.

    Returns:
        ``(frontmatter, body)``.
    """
    pid = product.get("id", "")
    contract = product.get("contract", "")
    fields: dict[str, Any] = {
        "type": TYPE_PRODUCT,
        "okf_version": OKF_VERSION,
        "profile": PROFILE,
        "profile_version": PROFILE_VERSION,
        "title": product.get("display_name") or pid,
        "description": " ".join((product.get("summary") or "").split()),
        "status": "draft",
        "tags": [product.get("domain", ""), product.get("tside", "").lower()],
        "identity": {
            "id": pid,
            "domain": product.get("domain", ""),
            "tside": product.get("tside", ""),
            "contract": contract,
            "contract_exists": os.path.isfile(os.path.join(repo_root, contract)),
        },
        "generated": {"by": generator},
        "features": product.get("features") or [],
        "hooks": product.get("hooks") or {},
        "internal_accounts": product.get("internal_accounts") or [],
        "balance_addresses": product.get("balance_addresses") or [],
        "linked_products": product.get("linked_products") or [],
        "traceability": {
            "business_requirements": [r.get("id") for r in (product.get("requirements") or [])
                                      if isinstance(r, dict)],
        },
        "tests": {k: len(v or []) for k, v in (product.get("tests") or {}).items()},
    }

    lines = [f"# {fields['title']}", "", fields["description"], ""]
    lines.append(f"**Ledger side:** `{product.get('tside')}`  ")
    lines.append(f"**Contract:** `{contract}`"
                 + ("" if fields["identity"]["contract_exists"] else "  *(not written yet)*"))
    lines.append("")

    reqs = product.get("requirements") or []
    if reqs:
        lines += ["## Requirements", "",
                  "| Id | Statement | Satisfied by | Verified by |",
                  "|---|---|---|---|"]
        for r in reqs:
            if not isinstance(r, dict):
                continue
            lines.append(
                f"| {r.get('id','')} | {' '.join((r.get('statement') or '').split())} "
                f"| {', '.join(f'`{x}`' for x in (r.get('satisfied_by') or [])) or '—'} "
                f"| {', '.join(f'`{x}`' for x in (r.get('verified_by') or [])) or '**none**'} |"
            )
        lines.append("")

    hooks = product.get("hooks") or {}
    if hooks:
        lines += ["## Hook wiring", ""]
        for hook, feats in hooks.items():
            lines.append(f"### `{hook}`")
            lines.append("")
            for fid in feats or []:
                lines.append(f"- [{feature_titles.get(fid, fid)}](/features/{fid.replace('.', '/')}.md)")
            lines.append("")

    links = product.get("linked_products") or []
    if links:
        lines += ["## Relationships to other products", ""]
        for link in links:
            if not isinstance(link, dict):
                continue
            lines.append(f"- **{link.get('relationship')}** → "
                         f"[{link.get('product')}](/products/{link.get('product')}.md)"
                         + (f" via `{link.get('parameter')}`" if link.get("parameter") else ""))
            if link.get("description"):
                lines.append(f"  {' '.join(link['description'].split())}")
        lines.append("")

    return fields, "\n".join(lines)


def parameter_document(
    clu_id: str,
    constraint: str,
    resource_path: str,
    used_by: list[str],
    description: str,
    generator: str,
) -> tuple[dict[str, Any], str]:
    """Build the frontmatter and body for one parameter.

    Args:
        clu_id: The bare parameter id.
        constraint: The declared constraint kind.
        resource_path: Repo-relative path of the backing resource.
        used_by: Feature ids referencing it.
        description: The resource's metadata description.
        generator: Generator identity.

    Returns:
        ``(frontmatter, body)``.
    """
    fields: dict[str, Any] = {
        "type": TYPE_PARAMETER,
        "okf_version": OKF_VERSION,
        "profile": PROFILE,
        "profile_version": PROFILE_VERSION,
        "title": clu_id,
        "description": description or f"Vault parameter {clu_id}.",
        "status": "stable",
        "tags": ["parameter"],
        "identity": {
            "clu_id": clu_id,
            "reference": "&{" + clu_id + "}",
            "constraint": constraint,
            "clu_resource": resource_path,
        },
        "generated": {"by": generator},
        "used_by": used_by,
    }
    body = [
        f"# `&{{{clu_id}}}`",
        "",
        description or "_No description in the resource definition._",
        "",
        f"**Constraint:** `{constraint or 'none declared'}`  ",
        f"**CLU resource:** `{resource_path}`",
        "",
        "## Referenced by",
        "",
    ]
    body += [f"- [{f}](/features/{f.replace('.', '/')}.md)" for f in used_by] or ["_Nothing._"]
    return fields, "\n".join(body)


def index_document(
    title: str,
    description: str,
    children: list[tuple[str, str, str]],
    generator: str,
) -> tuple[dict[str, Any], str]:
    """Build a directory index.

    Args:
        title: Index title.
        description: One-line summary.
        children: ``(label, absolute_bundle_path, note)`` triples.
        generator: Generator identity.

    Returns:
        ``(frontmatter, body)``.
    """
    fields: dict[str, Any] = {
        "type": TYPE_INDEX,
        "okf_version": OKF_VERSION,
        "profile": PROFILE,
        "profile_version": PROFILE_VERSION,
        "title": title,
        "description": description,
        "generated": {"by": generator},
        "entries": len(children),
    }
    body = [f"# {title}", "", description, ""]
    for label, path, note in children:
        body.append(f"- [{label}]({path})" + (f" — {note}" if note else ""))
    return fields, "\n".join(body)


def llms_txt(library: str, summary: str, sections: dict[str, list[tuple[str, str]]]) -> str:
    """Render an ``llms.txt`` navigation file for the bundle root.

    Args:
        library: The library name, used as the H1.
        summary: One-sentence blockquote summary.
        sections: Heading to ``(label, path)`` link lists.

    Returns:
        The file text.
    """
    lines = [f"# {library}", "", f"> {summary}", ""]
    for heading, links in sections.items():
        lines.append(f"## {heading}")
        lines.append("")
        for label, path in links:
            lines.append(f"- [{label}]({path})")
        lines.append("")
    return "\n".join(lines)
