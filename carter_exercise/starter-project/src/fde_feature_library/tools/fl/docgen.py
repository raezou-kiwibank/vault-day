"""Generate per-feature and per-product reference documentation.

Documentation that is written by hand goes stale, and stale documentation about
a banking product is worse than none — the existing
``apex_reserve_card/README.md`` already points at a ``feature_library/apex/``
package that no longer exists. So everything here is generated from two
sources that cannot drift: the module AST, and the curated knowledge record
beside it.

Each feature page answers, in order: what the feature does for the bank's
customer, how a value flows from configuration into behaviour, what every
input means, what the feature emits, how it composes with other features, which
requirement it satisfies, and how to exercise it in a simulation.

The traceability diagram is the centrepiece. It is drawn from real extracted
facts — parameters, fetchers, functions, hooks, outputs — so it always shows
the wiring that is actually in the code.
"""

from __future__ import annotations

import os
from typing import Any

from .model import ModuleFacts
from .resources import ResourceIndex
from .tests_index import Coverage

HOOK_OUTPUTS = {
    "activation_hook": "ScheduledEvent map",
    "scheduled_event_hook": "CustomInstruction[] / directives",
    "pre_posting_hook": "Rejection | None",
    "post_posting_hook": "CustomInstruction[] / notifications",
    "deactivation_hook": "CustomInstruction[]",
    "derived_parameter_hook": "derived parameter values",
    "pre_parameter_change_hook": "Rejection | None",
    "post_parameter_change_hook": "CustomInstruction[]",
    "conversion_hook": "ScheduledEvent map",
}


def _mermaid_id(text: str, prefix: str) -> str:
    """Build a mermaid-safe node id.

    Args:
        text: Source text, typically a parameter or function name.
        prefix: Short prefix distinguishing node classes.

    Returns:
        An identifier containing only safe characters.
    """
    safe = "".join(ch if ch.isalnum() else "_" for ch in text)
    return f"{prefix}_{safe}"[:60]


def _q(text: str) -> str:
    """Quote a mermaid label, escaping characters that break the parser.

    Args:
        text: Label text.

    Returns:
        The escaped label, wrapped in double quotes.
    """
    return '"' + text.replace('"', "'").replace("\n", " ") + '"'


def traceability_diagram(facts: ModuleFacts, manifest: dict[str, Any] | None) -> str:
    """Draw the input-to-outcome flow for one feature.

    The diagram makes the library's traceability claim concrete: every
    configuration input on the left is connected through the function that
    reads it to the hook it influences and the directive it ultimately
    produces.

    Args:
        facts: Resolved module facts.
        manifest: The curated record, used for the declared hook set.

    Returns:
        A fenced mermaid block.
    """
    hooks = list((manifest or {}).get("hooks") or facts.hook_affinity) or ["scheduled_event_hook"]
    params = facts.expected_parameters
    fetchers = facts.data_fetchers
    fns = [f for f in facts.public_functions if not f.name.startswith("get_parameters")]

    lines = ["```mermaid", "graph LR"]

    if params or fetchers:
        lines.append("  subgraph CONFIG[Configuration inputs]")
        lines.append("    direction TB")
        for p in params[:14]:
            lines.append(f"    {_mermaid_id(p.bare_id, 'p')}[{_q(p.parameter_id)}]")
        if len(params) > 14:
            lines.append(f"    p_more[{_q(f'... {len(params) - 14} more parameters')}]")
        lines.append("  end")

    if fetchers:
        lines.append("  subgraph DATA[Data fetched at execution]")
        lines.append("    direction TB")
        for f in fetchers[:10]:
            label = f"{f.fetcher_id}\\n({f.fetcher_class})"
            lines.append(f"    {_mermaid_id(f.fetcher_id, 'd')}[/{_q(label)}/]")
        lines.append("  end")

    lines.append(f"  subgraph FEAT[{_q(facts.name)}]")
    lines.append("    direction TB")
    if fns:
        for fn in fns[:10]:
            lines.append(f"    {_mermaid_id(fn.name, 'f')}({_q(fn.name + '()')})")
    else:
        lines.append(f"    f_module({_q(facts.name)})")
    lines.append("  end")

    lines.append("  subgraph HOOKS[Contract hooks]")
    lines.append("    direction TB")
    for h in hooks:
        lines.append(f"    {_mermaid_id(h, 'h')}[[{_q(h)}]]")
    lines.append("  end")

    outputs: list[str] = []
    for h in hooks:
        out = HOOK_OUTPUTS.get(h)
        if out and out not in outputs:
            outputs.append(out)
    if facts.event_types.names:
        outputs.append("scheduled events: " + ", ".join(facts.event_types.names[:4]))
    if facts.notifications:
        outputs.append("notifications: " + ", ".join(facts.notifications[:3]))
    if facts.balance_addresses:
        outputs.append("addresses: " + ", ".join(facts.balance_addresses[:5]))

    lines.append("  subgraph OUT[Outcomes]")
    lines.append("    direction TB")
    for i, o in enumerate(outputs[:6]):
        lines.append(f"    o_{i}[{_q(o)}]")
    lines.append("  end")

    entry = fns[0].name if fns else facts.name
    entry_id = _mermaid_id(entry, "f") if fns else "f_module"
    shown = {p.parameter_id for p in params[:14]}

    # Prefer precise edges: connect each parameter to the function that actually
    # reads it. Fall back to the entry point only for parameters whose consumer
    # could not be resolved statically.
    wired: set[str] = set()
    for fn in fns[:10]:
        for pid in fn.reads_parameters:
            if pid not in shown:
                continue
            bare = pid[2:-1] if pid.startswith("&{") else pid
            lines.append(f"  {_mermaid_id(bare, 'p')} --> {_mermaid_id(fn.name, 'f')}")
            wired.add(pid)
    for p in params[:14]:
        if p.parameter_id not in wired:
            lines.append(f"  {_mermaid_id(p.bare_id, 'p')} --> {entry_id}")
    for f in fetchers[:10]:
        lines.append(f"  {_mermaid_id(f.fetcher_id, 'd')} --> {entry_id}")
    for fn in fns[:10]:
        for h in hooks:
            lines.append(f"  {_mermaid_id(fn.name, 'f')} --> {_mermaid_id(h, 'h')}")
    for i, _ in enumerate(outputs[:6]):
        for h in hooks:
            lines.append(f"  {_mermaid_id(h, 'h')} --> o_{i}")

    lines.append("```")
    return "\n".join(lines)


def composition_diagram(
    facts: ModuleFacts,
    dependents: list[str],
    products: list[str],
) -> str:
    """Draw how the feature composes with the rest of the library.

    Args:
        facts: Resolved module facts.
        dependents: Modules that import this feature.
        products: Product ids composing this feature.

    Returns:
        A fenced mermaid block, or an empty string when there is nothing to show.
    """
    deps = [m for m in facts.imports_internal if m != facts.module]
    if not deps and not dependents and not products:
        return ""
    lines = ["```mermaid", "graph BT"]
    me = _mermaid_id(facts.name, "me")
    lines.append(f"  {me}[{_q(facts.name)}]:::self")
    for d in deps[:12]:
        short = d.replace("feature_library.", "")
        lines.append(f"  {_mermaid_id(short, 'dep')}[{_q(short)}] --> {me}")
    for d in dependents[:12]:
        short = d.replace("feature_library.", "")
        lines.append(f"  {me} --> {_mermaid_id(short, 'use')}[{_q(short)}]")
    for p in products[:8]:
        lines.append(f"  {me} ==> {_mermaid_id(p, 'prod')}[{_q(p)}]:::product")
    lines.append("  classDef self fill:#dbeafe,stroke:#1d4ed8,stroke-width:2px;")
    lines.append("  classDef product fill:#dcfce7,stroke:#15803d,stroke-width:2px;")
    lines.append("```")
    return "\n".join(lines)


def _table(headers: list[str], rows: list[list[str]]) -> str:
    """Render a markdown table.

    Args:
        headers: Column headings.
        rows: Row values; each row must match the header length.

    Returns:
        The rendered table, or an empty string when there are no rows.
    """
    if not rows:
        return ""
    out = ["| " + " | ".join(headers) + " |",
           "|" + "|".join("---" for _ in headers) + "|"]
    for row in rows:
        cells = [str(c).replace("|", "\\|").replace("\n", " ") for c in row]
        out.append("| " + " | ".join(cells) + " |")
    return "\n".join(out)


def render_feature(
    facts: ModuleFacts,
    manifest: dict[str, Any] | None,
    resource_index: ResourceIndex,
    coverage: Coverage | None,
    dependents: list[str],
    products: list[str],
    repo_root: str = "",
) -> str:
    """Render the reference page for one feature.

    Args:
        facts: Resolved module facts.
        manifest: The curated knowledge record, when one exists.
        resource_index: CLU resource definitions, used to describe parameters.
        coverage: Test coverage for the feature.
        dependents: Modules importing this feature.
        products: Products composing this feature.
        repo_root: Repository root, used to render paths relatively.

    Returns:
        The complete markdown page.
    """
    m = manifest or {}
    title = m.get("display_name") or facts.name.replace("_", " ").title()
    parts: list[str] = []

    rel_source = os.path.relpath(facts.path, repo_root) if repo_root else facts.path
    rel_record = rel_source[:-3] + ".okf.yaml"

    parts.append(f"# {title}")
    parts.append("")
    parts.append(
        "> Generated by `python3 -m fl docs`. Curated prose comes from "
        f"`{rel_record}`; everything else is derived from the module source. "
        "Do not edit by hand."
    )
    parts.append("")

    status = m.get("status", "undeclared")
    parts.append(_table(
        ["Property", "Value"],
        [
            ["Module", f"`{facts.module}`"],
            ["Domain", facts.domain or "—"],
            ["Status", status],
            ["Version", m.get("version", "—")],
            ["Hooks", ", ".join(f"`{h}`" for h in (m.get("hooks") or facts.hook_affinity)) or "—"],
            ["Source", f"`{rel_source}`"],
        ],
    ))
    parts.append("")

    capability = m.get("capability") or facts.summary or "_Not yet described._"
    parts.append("## What it does")
    parts.append("")
    parts.append(capability)
    parts.append("")

    if m.get("client_functionality"):
        parts.append("## What the customer experiences")
        parts.append("")
        parts.append(m["client_functionality"])
        parts.append("")

    if m.get("when_to_use") or m.get("when_not_to_use"):
        parts.append("## When to use it")
        parts.append("")
        if m.get("when_to_use"):
            parts.append(f"**Use it when** {m['when_to_use']}")
            parts.append("")
        if m.get("when_not_to_use"):
            parts.append(f"**Do not use it when** {m['when_not_to_use']}")
            parts.append("")

    parts.append("## Traceability: configuration to outcome")
    parts.append("")
    parts.append(
        "Every input below is a value a bank configures. The diagram shows which "
        "function consumes it and which hook turns it into an outcome."
    )
    parts.append("")
    parts.append(traceability_diagram(facts, manifest))
    parts.append("")

    param_docs = {p.get("parameter_id"): p for p in (m.get("parameters") or [])
                  if isinstance(p, dict)}
    rows = []
    for p in facts.expected_parameters:
        doc = param_docs.get(p.parameter_id, {})
        rd = resource_index.parameters.get(p.bare_id)
        rows.append([
            f"`{p.parameter_id}`",
            doc.get("description") or (rd.description if rd else "") or "_undocumented_",
            doc.get("level") or "—",
            doc.get("shape") or (rd.constraint_kind if rd else "") or "—",
            "optional" if p.optional else "required",
            f"`{os.path.relpath(rd.path, repo_root) if repo_root else rd.path}`" if rd else "**missing**",
        ])
    if rows:
        parts.append("## Inputs — parameters")
        parts.append("")
        parts.append(_table(
            ["Reference", "Meaning", "Hierarchy level", "Constraint", "Required", "CLU resource"],
            rows,
        ))
        parts.append("")

    if facts.data_fetchers:
        parts.append("## Inputs — data fetched at execution")
        parts.append("")
        parts.append(_table(
            ["Fetcher id", "Type", "Anchor", "Filter"],
            [[f"`{f.fetcher_id}`", f.fetcher_class, f.at or "—",
              (f.filter_summary or "—")[:80]] for f in facts.data_fetchers],
        ))
        parts.append("")

    if facts.public_functions:
        parts.append("## Public API")
        parts.append("")
        parts.append(_table(
            ["Function", "Returns", "Purpose"],
            [[f"`{fn.name}({', '.join(fn.args)})`", f"`{fn.returns or '—'}`",
              fn.summary or "_undocumented_"] for fn in facts.public_functions],
        ))
        parts.append("")

    outputs: list[list[str]] = []
    if facts.event_types.names:
        style = "per-product factory" if facts.event_types.style == "factory" else "static"
        outputs.append(["Scheduled events", ", ".join(f"`{n}`" for n in facts.event_types.names), style])
    if facts.notifications:
        outputs.append(["Notifications", ", ".join(f"`{n}`" for n in facts.notifications), "—"])
    if facts.balance_addresses:
        outputs.append(["Balance addresses", ", ".join(f"`{a}`" for a in facts.balance_addresses), "—"])
    if facts.account_attributes:
        outputs.append(["Account attributes", ", ".join(f"`{a}`" for a in facts.account_attributes), "—"])
    if outputs:
        parts.append("## Outputs")
        parts.append("")
        parts.append(_table(["Kind", "Values", "Notes"], outputs))
        parts.append("")

    if facts.interfaces_provided or facts.interfaces_consumed:
        parts.append("## Composition points")
        parts.append("")
        if facts.interfaces_provided:
            parts.append(_table(
                ["Provides interface", "As constant", "Members"],
                [[f"`{i.interface}`", f"`{i.constant}`", ", ".join(f"`{x}`" for x in i.members)]
                 for i in facts.interfaces_provided],
            ))
            parts.append("")
        if facts.interfaces_consumed:
            uniq = sorted(set(facts.interfaces_consumed))
            parts.append("Accepts: " + ", ".join(f"`{i}`" for i in uniq))
            parts.append("")

    comp = composition_diagram(facts, dependents, products)
    if comp:
        parts.append("## Where it sits in the library")
        parts.append("")
        parts.append(comp)
        parts.append("")

    reqs = m.get("requirements") or []
    parts.append("## Requirement traceability")
    parts.append("")
    if reqs:
        parts.append(_table(
            ["Requirement", "Statement", "Implemented by", "Verified by"],
            [[r.get("id", "—"), r.get("statement", "—"),
              ", ".join(f"`{x}`" for x in (r.get("satisfied_by") or [])) or "—",
              ", ".join(f"`{x}`" for x in (r.get("verified_by") or [])) or "**none**"]
             for r in reqs if isinstance(r, dict)],
        ))
    else:
        parts.append(
            "_No business requirement is linked to this feature yet, so it cannot be traced "
            "back to a stated need._"
        )
    parts.append("")

    parts.append("## Products using it")
    parts.append("")
    if products:
        parts.append("\n".join(f"- `{p}`" for p in products))
    else:
        parts.append(
            "_None. A feature that no product composes is not yet a proven building block._"
        )
    parts.append("")

    parts.append("## Testing")
    parts.append("")
    if coverage:
        parts.append(_table(
            ["Tier", "Status", "Test modules"],
            [
                ["Unit", "yes" if coverage.has_unit else "**missing**", str(len(coverage.unit))],
                ["Simulation", "yes" if coverage.has_simulation else "**missing**",
                 str(len(coverage.simulation))],
                ["End-to-end", "yes" if coverage.has_e2e else "**missing**", str(len(coverage.e2e))],
            ],
        ))
        parts.append("")
    if m.get("simulation_notes"):
        parts.append("### Exercising it in a simulation")
        parts.append("")
        parts.append(m["simulation_notes"])
        parts.append("")
    if m.get("determinism_notes"):
        parts.append("### Determinism")
        parts.append("")
        parts.append(m["determinism_notes"])
        parts.append("")

    return "\n".join(parts).rstrip() + "\n"


def render_index(
    features: dict[str, ModuleFacts],
    manifests: dict[str, dict[str, Any]],
    coverage: dict[str, Coverage],
    products_by_feature: dict[str, list[str]],
) -> str:
    """Render the catalogue page listing every feature.

    Args:
        features: Resolved facts for every feature module.
        manifests: Curated records by module.
        coverage: Test coverage by module.
        products_by_feature: Product ids by module.

    Returns:
        The markdown catalogue.
    """
    parts = ["# Feature catalogue", "",
             "> Generated by `python3 -m fl docs`. One row per feature module.", ""]

    by_domain: dict[str, list[str]] = {}
    for module, facts in features.items():
        by_domain.setdefault(facts.domain or "root", []).append(module)

    total = len(features)
    complete = sum(
        1 for m in features
        if coverage.get(m) and coverage[m].has_unit and coverage[m].has_simulation
        and products_by_feature.get(m)
    )
    parts.append(
        f"**{complete} of {total}** features currently meet the completeness bar "
        "(unit tested, simulated, and composed by a product)."
    )
    parts.append("")

    for domain in sorted(by_domain):
        parts.append(f"## {domain}")
        parts.append("")
        rows = []
        for module in sorted(by_domain[domain]):
            facts = features[module]
            man = manifests.get(module, {})
            cov = coverage.get(module)
            tiers = "/".join(cov.tiers) if cov and cov.tiers else "**none**"
            prods = products_by_feature.get(module) or []
            rows.append([
                f"[{facts.name}]({os.path.relpath(os.path.join(os.path.dirname(facts.path), 'documentation', facts.name + '.md'))})",
                man.get("capability") or facts.summary or "_undescribed_",
                str(len(facts.expected_parameters)),
                tiers,
                ", ".join(prods) or "**none**",
            ])
        parts.append(_table(
            ["Feature", "Capability", "Params", "Tests", "Products"], rows
        ))
        parts.append("")
    return "\n".join(parts).rstrip() + "\n"
