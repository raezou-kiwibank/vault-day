"""Command line entry point for the feature library toolchain.

Run from the repository root with no dependencies beyond the standard library::

    python3 -m fl scan                 # what is in the library
    python3 -m fl check                # the completeness gate
    python3 -m fl scaffold <module>    # start a knowledge record
    python3 -m fl derive --write       # refresh derived facts in records
    python3 -m fl docs --write         # regenerate reference documentation
    python3 -m fl export               # emit the whole knowledge pack as JSON
    python3 -m fl graph                # emit the composition graph

``check`` is the command the pre-commit hook and CI run. It exits non-zero only
on findings at or above the severity given by ``--fail-on`` (default ``error``),
so the gate can be tightened as the backlog is cleared instead of blocking
every commit from day one.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any

from . import VERSION, baseline as baseline_mod, bundle as bundle_mod, docgen, schema, validate, yamlite
from .model import asdict
from .validate import ERROR, INFO, WARNING

SEVERITY_ORDER = {INFO: 0, WARNING: 1, ERROR: 2}


def _repo_root(explicit: str | None) -> str:
    """Resolve the repository root.

    Args:
        explicit: A path supplied on the command line, if any.

    Returns:
        The resolved root directory.
    """
    if explicit:
        return os.path.abspath(explicit)
    here = os.path.abspath(os.getcwd())
    probe = here
    while True:
        if os.path.isdir(os.path.join(probe, "feature_library", "src")):
            return probe
        parent = os.path.dirname(probe)
        if parent == probe:
            return here
        probe = parent


def _products_by_feature(ctx: validate.Context) -> dict[str, list[str]]:
    """Invert the product-to-feature mapping.

    Args:
        ctx: The gathered context.

    Returns:
        Mapping of feature module to the product ids composing it.
    """
    out: dict[str, list[str]] = {}
    known = set(ctx.features)
    for pid, doc in ctx.products.items():
        for fid in doc.get("features") or []:
            module = fid if fid in known else f"feature_library.{fid}"
            if module in known:
                out.setdefault(module, []).append(pid)
    return {k: sorted(v) for k, v in out.items()}


def _dependents(ctx: validate.Context) -> dict[str, list[str]]:
    """Compute reverse dependencies between feature modules.

    Args:
        ctx: The gathered context.

    Returns:
        Mapping of module to the modules importing it.
    """
    out: dict[str, list[str]] = {m: [] for m in ctx.features}
    for module, facts in ctx.features.items():
        for dep in facts.imports_internal:
            if dep in out and dep != module:
                out[dep].append(module)
    return {k: sorted(set(v)) for k, v in out.items()}


# --------------------------------------------------------------------------
# Commands
# --------------------------------------------------------------------------


def cmd_scan(args: argparse.Namespace) -> int:
    """Print a summary of the library's contents.

    Args:
        args: Parsed arguments.

    Returns:
        Process exit code.
    """
    ctx = validate.build_context(_repo_root(args.repo))
    products_by_feature = _products_by_feature(ctx)

    by_domain: dict[str, int] = {}
    for facts in ctx.features.values():
        by_domain[facts.domain or "root"] = by_domain.get(facts.domain or "root", 0) + 1

    params = {p.bare_id for f in ctx.features.values() for p in f.expected_parameters}
    events = {e for f in ctx.features.values() for e in f.event_types.names}
    tested = sum(1 for m in ctx.features if ctx.coverage.get(m) and ctx.coverage[m].tiers)
    simulated = sum(1 for m in ctx.features if ctx.coverage.get(m) and ctx.coverage[m].has_simulation)
    in_product = len(products_by_feature)

    print(f"Feature library scan  (fl {VERSION})")
    print(f"  repository        : {ctx.repo_root}")
    print(f"  feature modules   : {len(ctx.features)}")
    for domain in sorted(by_domain):
        print(f"      {domain:<12s}  {by_domain[domain]}")
    print(f"  knowledge records : {len(ctx.manifests)} / {len(ctx.features)}")
    print(f"  parameters used   : {len(params)}")
    print(f"  CLU resources     : {len(ctx.resource_index.by_path)}"
          f" ({len(ctx.resource_index.parameters)} parameters)")
    print(f"  scheduled events  : {len(events)}")
    print(f"  test modules      : {sum(1 for t in ctx.tests.values() if t.test_count)}"
          f"  ({sum(t.test_count for t in ctx.tests.values())} test functions)")
    print(f"  harness contracts : {sum(1 for t in ctx.tests.values() if t.is_harness)}")
    print(f"  products          : {len(ctx.products)}")
    print()
    print("Completeness")
    print(f"  has any test      : {tested} / {len(ctx.features)}")
    print(f"  has simulation    : {simulated} / {len(ctx.features)}")
    print(f"  used by a product : {in_product} / {len(ctx.features)}")
    return 0


def cmd_check(args: argparse.Namespace) -> int:
    """Run the completeness gate.

    Args:
        args: Parsed arguments.

    Returns:
        Process exit code: non-zero when findings reach the fail threshold.
    """
    ctx = validate.build_context(_repo_root(args.repo))
    findings = validate.run(ctx, only=args.only)

    if args.code:
        findings = [f for f in findings if f.code in set(args.code)]

    base = {} if args.no_baseline else baseline_mod.load(ctx.repo_root)
    new_findings, accepted = baseline_mod.partition(findings, base)
    stale = baseline_mod.stale_entries(findings, base)

    threshold = SEVERITY_ORDER[args.fail_on]
    candidates = findings if args.no_baseline else new_findings
    blocking = [f for f in candidates if SEVERITY_ORDER[f.severity] >= threshold]

    if args.format == "json":
        print(json.dumps({
            "findings": [asdict(f) for f in findings],
            "new": [asdict(f) for f in new_findings],
            "accepted": len(accepted),
            "stale_baseline_entries": stale,
            "summary": validate.summarise(findings),
            "blocking": len(blocking),
        }, indent=2))
    else:
        current = ""
        for f in findings:
            if f.code != current:
                current = f.code
                print()
            print("  " + f.render())
            if args.verbose and f.remedy:
                print(f"          -> {f.remedy}")
        counts = validate.summarise(findings)
        print()
        print(f"  {counts.get(ERROR, 0)} error(s), {counts.get(WARNING, 0)} warning(s), "
              f"{counts.get(INFO, 0)} info")
        by_code = sorted((c, n) for c, n in counts.items() if c.startswith("FL"))
        if by_code:
            print("  by code: " + ", ".join(f"{c}={n}" for c, n in by_code))
        if accepted:
            print(f"  {len(accepted)} finding(s) accepted by the baseline "
                  f"({len(new_findings)} new)")
        if stale:
            print(f"  {len(stale)} baseline entry(s) no longer apply — "
                  "tighten with `fl baseline --write`")
        if blocking:
            print(f"\n  FAILING: {len(blocking)} new finding(s) at or above '{args.fail_on}'.")
            for f in blocking[:20]:
                print("    " + f.render())
        else:
            print(f"\n  PASSING at threshold '{args.fail_on}'.")

    return 1 if blocking else 0


def cmd_baseline(args: argparse.Namespace) -> int:
    """Show or rewrite the accepted-debt baseline.

    Args:
        args: Parsed arguments.

    Returns:
        Process exit code.
    """
    ctx = validate.build_context(_repo_root(args.repo))
    findings = validate.run(ctx)
    current = baseline_mod.load(ctx.repo_root)
    new_findings, accepted = baseline_mod.partition(findings, current)
    stale = baseline_mod.stale_entries(findings, current)

    if args.write:
        notes = dict(current.get("notes") or {})
        notes.setdefault(
            "FL007",
            "Two resource files define the same parameter id differently. Must be resolved "
            "before any product composes features from both domains.",
        )
        notes.setdefault("FL030", "Feature has no unit tests.")
        notes.setdefault("FL010", "Feature has no OKF knowledge record yet.")
        path = baseline_mod.save(ctx.repo_root, findings, notes)
        print(f"  wrote {os.path.relpath(path, ctx.repo_root)} accepting {len(findings)} finding(s)")
        return 0

    print(f"  accepted : {len(accepted)}")
    print(f"  new      : {len(new_findings)}")
    print(f"  stale    : {len(stale)}")
    for code, count in sorted((current.get("counts") or {}).items()):
        print(f"      {code}  {count}")
    return 0


def cmd_scaffold(args: argparse.Namespace) -> int:
    """Create a knowledge record stub for one or more features.

    Args:
        args: Parsed arguments.

    Returns:
        Process exit code.
    """
    ctx = validate.build_context(_repo_root(args.repo))
    targets = args.module or sorted(m for m in ctx.features if m not in ctx.manifests)
    written = 0
    for target in targets:
        module = target if target in ctx.features else f"feature_library.{target}"
        facts = ctx.features.get(module)
        if facts is None:
            print(f"  unknown feature: {target}", file=sys.stderr)
            continue
        path = facts.path[:-3] + validate.FEATURE_RECORD_SUFFIX
        if os.path.exists(path) and not args.force:
            continue
        record = _stub_record(ctx, module, facts)
        yamlite.dump(record, path, header=(
            "Feature knowledge record (OKF).\n"
            "Curated fields describe business meaning; the `derived` block is\n"
            "regenerated by `python3 -m fl derive --write` and must not be edited."
        ))
        written += 1
        print(f"  wrote {os.path.relpath(path, ctx.repo_root)}")
    print(f"\n  {written} record(s) written.")
    return 0


def _stub_record(ctx: validate.Context, module: str, facts: Any) -> dict[str, Any]:
    """Build a knowledge record stub pre-filled with everything derivable.

    Args:
        ctx: The gathered context.
        module: Dotted module name.
        facts: Resolved module facts.

    Returns:
        The record, ready to be written.
    """
    short = module.replace("feature_library.", "")
    param_docs = []
    for p in facts.expected_parameters:
        rd = ctx.resource_index.parameters.get(p.bare_id)
        param_docs.append({
            "parameter_id": p.parameter_id,
            "display_name": p.bare_id.replace("_", " ").title(),
            "description": (rd.description if rd else "") or "TODO: what this value means to the business.",
            "level": "template",
            "shape": (rd.constraint_kind if rd else "") or "TODO",
            "example": "",
            "resource": os.path.relpath(rd.path, ctx.repo_root) if rd else "",
            "drives": "TODO: the behaviour this value changes.",
        })
    return {
        "schema": schema.RECORD_SCHEMA_VERSION,
        "id": short,
        "module": module,
        "version": "1.0.0",
        "domain": facts.domain or "common",
        "status": "draft",
        "capability": facts.summary or "TODO: one sentence describing the business capability.",
        "client_functionality": "TODO: what the bank's customer actually experiences.",
        "when_to_use": "",
        "when_not_to_use": "",
        "hooks": list(facts.hook_affinity) or ["scheduled_event_hook"],
        "parameters": param_docs,
        "requirements": [],
        "products": sorted(_products_by_feature(ctx).get(module, [])),
        "simulation_notes": "",
        "determinism_notes": "",
        "owner": "",
        "tags": [],
        "derived": validate.derived_block(facts),
    }


def cmd_derive(args: argparse.Namespace) -> int:
    """Refresh the derived block in every knowledge record.

    Args:
        args: Parsed arguments.

    Returns:
        Process exit code; non-zero in ``--check`` mode when records are stale.
    """
    ctx = validate.build_context(_repo_root(args.repo))
    stale: list[str] = []
    for module, doc in sorted(ctx.manifests.items()):
        facts = ctx.features[module]
        fresh = validate.derived_block(facts)
        current = doc.get("derived") or {}
        if current.get("source_digest") == fresh["source_digest"]:
            continue
        stale.append(module)
        if args.write:
            doc["derived"] = fresh
            doc["products"] = sorted(_products_by_feature(ctx).get(module, []))
            yamlite.dump(doc, ctx.manifest_paths[module], header=(
                "Feature knowledge record (OKF).\n"
                "Curated fields describe business meaning; the `derived` block is\n"
                "regenerated by `python3 -m fl derive --write` and must not be edited."
            ))
            print(f"  refreshed {os.path.relpath(ctx.manifest_paths[module], ctx.repo_root)}")
    if not args.write:
        for module in stale:
            print(f"  STALE {module}")
    print(f"\n  {len(stale)} record(s) {'refreshed' if args.write else 'stale'}.")
    return 1 if (stale and not args.write) else 0


def cmd_docs(args: argparse.Namespace) -> int:
    """Generate reference documentation for every feature.

    Args:
        args: Parsed arguments.

    Returns:
        Process exit code.
    """
    ctx = validate.build_context(_repo_root(args.repo))
    products_by_feature = _products_by_feature(ctx)
    dependents = _dependents(ctx)
    written = 0

    for module, facts in sorted(ctx.features.items()):
        page = docgen.render_feature(
            facts,
            ctx.manifests.get(module),
            ctx.resource_index,
            ctx.coverage.get(module),
            dependents.get(module, []),
            products_by_feature.get(module, []),
            repo_root=ctx.repo_root,
        )
        out_dir = os.path.join(os.path.dirname(facts.path), "documentation")
        out_path = os.path.join(out_dir, f"{facts.name}.md")
        if args.write:
            os.makedirs(out_dir, exist_ok=True)
            # Never discard prose the generator did not write. A file carrying
            # the marker keeps everything below it; a pre-existing hand-written
            # file is preserved whole, because losing it would be worse than a
            # duplicated heading.
            preserved = bundle_mod.read_preserved(out_path)
            if not preserved and os.path.isfile(out_path):
                with open(out_path, "r", encoding="utf-8") as fh:
                    existing = fh.read()
                if bundle_mod.GENERATED_END not in existing:
                    preserved = "\n".join(
                        ["## Authored notes", "",
                         "_Written by hand before this page was generated; kept verbatim._",
                         "", existing.strip()]
                    )
            with open(out_path, "w", encoding="utf-8") as fh:
                fh.write(page.rstrip() + "\n\n" + bundle_mod.GENERATED_END + "\n")
                if preserved.strip():
                    fh.write("\n" + preserved.strip() + "\n")
            written += 1
        elif args.module and module.endswith(args.module):
            print(page)

    index = docgen.render_index(ctx.features, ctx.manifests, ctx.coverage, products_by_feature)
    index_path = os.path.join(ctx.repo_root, "docs", "FEATURE_CATALOGUE.md")
    if args.write:
        os.makedirs(os.path.dirname(index_path), exist_ok=True)
        with open(index_path, "w", encoding="utf-8") as fh:
            fh.write(index)
        print(f"  {written} feature page(s) written")
        print(f"  catalogue: {os.path.relpath(index_path, ctx.repo_root)}")
    elif not args.module:
        print(index)
    return 0


def cmd_export(args: argparse.Namespace) -> int:
    """Emit the whole knowledge pack as a single JSON document.

    This is the artefact an agent consumes: one file describing every feature,
    its inputs, its outputs, its composition points, its tests and the products
    that use it.

    Args:
        args: Parsed arguments.

    Returns:
        Process exit code.
    """
    ctx = validate.build_context(_repo_root(args.repo))
    products_by_feature = _products_by_feature(ctx)
    dependents = _dependents(ctx)

    features: list[dict[str, Any]] = []
    for module, facts in sorted(ctx.features.items()):
        man = ctx.manifests.get(module, {})
        cov = ctx.coverage.get(module)
        features.append({
            "id": man.get("id") or module.replace("feature_library.", ""),
            "module": module,
            "domain": facts.domain,
            "status": man.get("status", "undeclared"),
            "capability": man.get("capability") or facts.summary,
            "client_functionality": man.get("client_functionality", ""),
            "hooks": man.get("hooks") or facts.hook_affinity,
            "parameters": [
                {
                    "id": p.parameter_id,
                    "optional": p.optional,
                    "resource": (
                        os.path.relpath(ctx.resource_index.parameters[p.bare_id].path, ctx.repo_root)
                        if p.bare_id in ctx.resource_index.parameters else None
                    ),
                    "constraint": (
                        ctx.resource_index.parameters[p.bare_id].constraint_kind
                        if p.bare_id in ctx.resource_index.parameters else None
                    ),
                }
                for p in facts.expected_parameters
            ],
            "data_fetchers": [
                {"id": f.fetcher_id, "type": f.fetcher_class, "kind": f.kind}
                for f in facts.data_fetchers
            ],
            "event_types": facts.event_types.names,
            "event_style": facts.event_types.style,
            "notifications": facts.notifications,
            "balance_addresses": facts.balance_addresses,
            "public_functions": [
                {"name": fn.name, "args": fn.args, "returns": fn.returns, "summary": fn.summary}
                for fn in facts.public_functions
            ],
            "interfaces_provided": [i.interface for i in facts.interfaces_provided],
            "interfaces_consumed": sorted(set(facts.interfaces_consumed)),
            "depends_on": [m for m in facts.imports_internal if m != facts.module],
            "used_by": dependents.get(module, []),
            "products": products_by_feature.get(module, []),
            "requirements": man.get("requirements", []),
            "tests": {
                "unit": cov.unit if cov else [],
                "simulation": cov.simulation if cov else [],
                "e2e": cov.e2e if cov else [],
            },
            "source": os.path.relpath(facts.path, ctx.repo_root),
        })

    pack = {
        "schema": schema.RECORD_SCHEMA_VERSION,
        "generator": f"fl {VERSION}",
        "library": "fde_feature_library",
        "counts": {
            "features": len(features),
            "products": len(ctx.products),
            "parameters": len(ctx.resource_index.parameters),
        },
        "features": features,
        "products": list(ctx.products.values()),
    }

    text = json.dumps(pack, indent=2, sort_keys=False)
    if args.output:
        os.makedirs(os.path.dirname(os.path.abspath(args.output)) or ".", exist_ok=True)
        with open(args.output, "w", encoding="utf-8") as fh:
            fh.write(text + "\n")
        print(f"  wrote {args.output} ({len(features)} features, {len(ctx.products)} products)")
    else:
        print(text)
    return 0


def cmd_bundle(args: argparse.Namespace) -> int:
    """Publish the library as an OKF-conformant Feature Knowledge Bundle.

    Args:
        args: Parsed arguments.

    Returns:
        Process exit code.
    """
    ctx = validate.build_context(_repo_root(args.repo))
    products_by_feature = _products_by_feature(ctx)
    dependents = _dependents(ctx)
    root = os.path.join(ctx.repo_root, args.out)
    generator = f"process:fl/{VERSION}"
    library_version = _library_version(ctx.repo_root)

    written: list[str] = []

    def emit(rel: str, fields: dict[str, Any], body: str) -> None:
        path = os.path.join(root, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        preserved = bundle_mod.read_preserved(path)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(bundle_mod.render_document(fields, body, preserved))
        written.append(rel)

    feature_titles: dict[str, str] = {}
    by_domain: dict[str, list[tuple[str, str, str]]] = {}

    for module, facts in sorted(ctx.features.items()):
        short = module.replace("feature_library.", "")
        rel = os.path.join("features", *short.split(".")) + ".md"
        fields, body = bundle_mod.feature_document(
            facts, ctx.manifests.get(module), ctx.resource_index, ctx.coverage.get(module),
            dependents.get(module, []), products_by_feature.get(module, []),
            ctx.repo_root, library_version, generator,
        )
        feature_titles[short] = fields["title"]
        emit(rel, fields, body)
        by_domain.setdefault(facts.domain or "common", []).append(
            (fields["title"], "/" + rel.replace(os.sep, "/"),
             "complete" if fields["complete"] else "incomplete")
        )

    # OKF navigation: every directory in the bundle carries an index listing its
    # children, so a consumer can walk the tree without a manifest.
    tree: dict[str, list[tuple[str, str, str]]] = {}
    for module, facts in sorted(ctx.features.items()):
        short = module.replace("feature_library.", "")
        parts = short.split(".")
        rel_dir = os.path.join("features", *parts[:-1])
        label = feature_titles.get(short, parts[-1])
        target = "/" + os.path.join("features", *parts).replace(os.sep, "/") + ".md"
        tree.setdefault(rel_dir, []).append((label, target, ""))
        # register each ancestor directory with its child directory
        for depth in range(len(parts) - 1, 0, -1):
            parent = os.path.join("features", *parts[:depth - 1]) if depth > 1 else "features"
            child_dir = os.path.join("features", *parts[:depth])
            entry = (parts[depth - 1], "/" + child_dir.replace(os.sep, "/") + "/index.md", "")
            existing = tree.setdefault(parent, [])
            if entry not in existing:
                existing.append(entry)

    for rel_dir, children in sorted(tree.items()):
        if rel_dir == "features":
            continue
        name = rel_dir.split(os.sep)[-1]
        fields, body = bundle_mod.index_document(
            f"{name.replace('_', ' ').title()}",
            f"Contents of `{rel_dir.replace(os.sep, '/')}`.",
            sorted(set(children)), generator,
        )
        emit(os.path.join(rel_dir, "index.md"), fields, body)

    fields, body = bundle_mod.index_document(
        "Features",
        "All Smart Contract features, by domain.",
        [(f"{d.title()} features", f"/features/{d}/index.md", f"{len(c)} features")
         for d, c in sorted(by_domain.items())],
        generator,
    )
    emit(os.path.join("features", "index.md"), fields, body)

    product_children: list[tuple[str, str, str]] = []
    for pid, doc in sorted(ctx.products.items()):
        fields, body = bundle_mod.product_document(doc, ctx.repo_root, generator, feature_titles)
        rel = os.path.join("products", f"{pid}.md")
        emit(rel, fields, body)
        product_children.append(
            (fields["title"], "/" + rel.replace(os.sep, "/"),
             f"{len(doc.get('features') or [])} features")
        )
    fields, body = bundle_mod.index_document(
        "Products", "Banking products composed from the feature library.",
        product_children, generator)
    emit(os.path.join("products", "index.md"), fields, body)

    used_by: dict[str, list[str]] = {}
    for module, facts in ctx.features.items():
        for p in facts.expected_parameters:
            used_by.setdefault(p.bare_id, []).append(module.replace("feature_library.", ""))

    param_children: list[tuple[str, str, str]] = []
    for clu_id, rd in sorted(ctx.resource_index.parameters.items()):
        fields, body = bundle_mod.parameter_document(
            clu_id, rd.constraint_kind, os.path.relpath(rd.path, ctx.repo_root),
            sorted(used_by.get(clu_id, [])), rd.description, generator,
        )
        rel = os.path.join("parameters", f"{clu_id}.md")
        emit(rel, fields, body)
        param_children.append(
            (clu_id, "/" + rel.replace(os.sep, "/"),
             f"{len(used_by.get(clu_id, []))} feature(s)")
        )
    fields, body = bundle_mod.index_document(
        "Parameters",
        "Every Vault parameter the library references, and its CLU definition.",
        param_children, generator)
    emit(os.path.join("parameters", "index.md"), fields, body)

    complete = sum(1 for m in ctx.features
                   if ctx.coverage.get(m) and ctx.coverage[m].has_unit
                   and ctx.coverage[m].has_simulation and products_by_feature.get(m))
    fields, body = bundle_mod.index_document(
        "FDE Feature Library",
        f"{len(ctx.features)} Smart Contract features, {len(ctx.products)} products and "
        f"{len(ctx.resource_index.parameters)} parameters for Thought Machine Vault "
        f"(Contracts API 4.x). {complete} features currently meet the completeness bar.",
        [("Features", "/features/index.md", f"{len(ctx.features)} modules"),
         ("Products", "/products/index.md", f"{len(ctx.products)} products"),
         ("Parameters", "/parameters/index.md",
          f"{len(ctx.resource_index.parameters)} definitions")],
        generator)
    emit("index.md", fields, body)

    with open(os.path.join(root, "llms.txt"), "w", encoding="utf-8") as fh:
        fh.write(bundle_mod.llms_txt(
            "FDE Feature Library",
            "Composable Thought Machine Vault Smart Contract features and the products built "
            "from them.",
            {
                "Start here": [("Bundle index", "/index.md")],
                "Features": [(f"{d.title()} features", f"/features/{d}/index.md")
                             for d in sorted(by_domain)],
                "Products": [(t, p) for t, p, _ in product_children],
                "Reference": [("Parameters", "/parameters/index.md")],
            },
        ))

    print(f"  wrote {len(written)} document(s) + llms.txt to {args.out}/")
    print(f"  {complete}/{len(ctx.features)} features meet the completeness bar")
    return 0


def _library_version(repo_root: str) -> str:
    """Read the feature library package version.

    Args:
        repo_root: Repository root.

    Returns:
        The version string, or "0.0.0" when it cannot be read.
    """
    path = os.path.join(repo_root, "feature_library", "pyproject.toml")
    try:
        with open(path, "r", encoding="utf-8") as fh:
            for line in fh:
                if line.startswith("version"):
                    return line.split("=", 1)[1].strip().strip('"')
    except OSError:
        pass
    return "0.0.0"


def cmd_graph(args: argparse.Namespace) -> int:
    """Emit the feature/product composition graph.

    Args:
        args: Parsed arguments.

    Returns:
        Process exit code.
    """
    ctx = validate.build_context(_repo_root(args.repo))
    products_by_feature = _products_by_feature(ctx)

    if args.format == "json":
        nodes = [{"id": m, "kind": "feature", "domain": f.domain} for m, f in ctx.features.items()]
        nodes += [{"id": p, "kind": "product"} for p in ctx.products]
        edges = []
        for module, facts in ctx.features.items():
            for dep in facts.imports_internal:
                if dep in ctx.features and dep != module:
                    edges.append({"from": module, "to": dep, "kind": "depends_on"})
        for module, prods in products_by_feature.items():
            for p in prods:
                edges.append({"from": p, "to": module, "kind": "composes"})
        print(json.dumps({"nodes": nodes, "edges": edges}, indent=2))
        return 0

    print("```mermaid")
    print("graph LR")
    for pid in sorted(ctx.products):
        print(f'  {docgen._mermaid_id(pid, "P")}[{docgen._q(pid)}]:::product')
    seen: set[str] = set()
    for module, prods in sorted(products_by_feature.items()):
        short = module.replace("feature_library.", "")
        node = docgen._mermaid_id(short, "F")
        if node not in seen:
            print(f"  {node}[{docgen._q(short)}]")
            seen.add(node)
        for p in prods:
            print(f'  {docgen._mermaid_id(p, "P")} --> {node}')
    print("  classDef product fill:#dcfce7,stroke:#15803d,stroke-width:2px;")
    print("```")
    return 0


# --------------------------------------------------------------------------
# Argument parsing
# --------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    """Construct the argument parser.

    Returns:
        The configured parser.
    """
    p = argparse.ArgumentParser(
        prog="fl", description="Feature library knowledge and completeness toolchain."
    )
    p.add_argument("--repo", help="Repository root (defaults to the nearest ancestor with feature_library/src).")
    sub = p.add_subparsers(dest="command", required=True)

    s = sub.add_parser("scan", help="Summarise the library.")
    s.set_defaults(func=cmd_scan)

    s = sub.add_parser("check", help="Run the completeness gate.")
    s.add_argument("--fail-on", choices=[INFO, WARNING, ERROR], default=ERROR,
                   help="Severity at which to exit non-zero (default: error).")
    s.add_argument("--only", nargs="*", choices=sorted(validate.ALL_CHECKS),
                   help="Run only these check groups.")
    s.add_argument("--code", nargs="*", help="Show only these finding codes, e.g. FL002.")
    s.add_argument("--format", choices=["text", "json"], default="text")
    s.add_argument("-v", "--verbose", action="store_true", help="Show the remedy for each finding.")
    s.add_argument("--no-baseline", action="store_true",
                   help="Ignore the accepted-debt baseline and judge every finding.")
    s.set_defaults(func=cmd_check)

    s = sub.add_parser("baseline", help="Inspect or rewrite the accepted-debt baseline.")
    s.add_argument("--write", action="store_true", help="Accept every current finding.")
    s.set_defaults(func=cmd_baseline)

    s = sub.add_parser("scaffold", help="Create knowledge record stubs.")
    s.add_argument("module", nargs="*", help="Feature modules; defaults to every feature lacking one.")
    s.add_argument("--force", action="store_true", help="Overwrite existing records.")
    s.set_defaults(func=cmd_scaffold)

    s = sub.add_parser("derive", help="Refresh derived facts inside knowledge records.")
    s.add_argument("--write", action="store_true", help="Write changes (otherwise report staleness).")
    s.set_defaults(func=cmd_derive)

    s = sub.add_parser("docs", help="Generate reference documentation.")
    s.add_argument("--write", action="store_true", help="Write pages to disk.")
    s.add_argument("--module", help="Print one module's page instead of writing.")
    s.set_defaults(func=cmd_docs)

    s = sub.add_parser("export", help="Emit the knowledge pack as JSON.")
    s.add_argument("-o", "--output", help="Destination file (default: stdout).")
    s.set_defaults(func=cmd_export)

    s = sub.add_parser("bundle", help="Publish the OKF-conformant Feature Knowledge Bundle.")
    s.add_argument("--out", default="knowledge", help="Bundle root directory (default: knowledge).")
    s.set_defaults(func=cmd_bundle)

    s = sub.add_parser("graph", help="Emit the composition graph.")
    s.add_argument("--format", choices=["mermaid", "json"], default="mermaid")
    s.set_defaults(func=cmd_graph)

    return p


def main(argv: list[str] | None = None) -> int:
    """Run the CLI.

    Args:
        argv: Argument vector, defaulting to ``sys.argv[1:]``.

    Returns:
        Process exit code.
    """
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
