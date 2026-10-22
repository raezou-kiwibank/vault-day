"""A ratchet for the completeness gate.

Turning on a strict gate against an existing codebase has one predictable
outcome: the build goes red, nobody can merge, and the gate gets switched off.
So the gate ships with a baseline — an explicit, reviewable record of the debt
that exists today.

The contract is simple. A finding already in the baseline does not fail the
build. Anything new does. Clearing debt shrinks the baseline; the file is
committed, so a pull request that adds to it is visibly asking for an
exception rather than quietly acquiring one.

Entries are keyed by ``(code, subject)`` and never by line number, so ordinary
edits do not invalidate them.
"""

from __future__ import annotations

import json
import os
from typing import Any, Iterable

from .validate import Finding

BASELINE_FILENAME = os.path.join("tools", "fl-baseline.json")


def key_of(finding: Finding) -> str:
    """Build the stable key for a finding.

    Args:
        finding: The finding to key.

    Returns:
        A ``CODE::subject`` key, stable across reformatting and line moves.
    """
    return f"{finding.code}::{finding.subject}"


def load(repo_root: str) -> dict[str, Any]:
    """Read the baseline, tolerating its absence.

    Args:
        repo_root: Repository root.

    Returns:
        The baseline document. A missing file yields an empty baseline.
    """
    path = os.path.join(repo_root, BASELINE_FILENAME)
    if not os.path.isfile(path):
        return {"accepted": {}, "notes": {}}
    try:
        with open(path, "r", encoding="utf-8") as fh:
            doc = json.load(fh)
    except (OSError, ValueError):
        return {"accepted": {}, "notes": {}}
    doc.setdefault("accepted", {})
    doc.setdefault("notes", {})
    return doc


def save(repo_root: str, findings: Iterable[Finding], notes: dict[str, str] | None = None) -> str:
    """Write a baseline covering the given findings.

    Args:
        repo_root: Repository root.
        findings: The findings to accept.
        notes: Optional per-code commentary explaining why the debt is accepted
            and what would clear it.

    Returns:
        The path written.
    """
    accepted: dict[str, str] = {}
    for f in findings:
        accepted[key_of(f)] = f.severity
    doc = {
        "_comment": (
            "Accepted findings from `python3 -m fl check`. A finding listed here does not "
            "fail the build; anything new does. Shrink this file, never grow it. "
            "Regenerate deliberately with `python3 -m fl baseline --write`."
        ),
        "counts": _counts(accepted),
        "notes": notes or {},
        "accepted": dict(sorted(accepted.items())),
    }
    path = os.path.join(repo_root, BASELINE_FILENAME)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=2)
        fh.write("\n")
    return path


def _counts(accepted: dict[str, str]) -> dict[str, int]:
    """Count accepted entries by finding code.

    Args:
        accepted: The accepted map.

    Returns:
        Mapping of code to count, sorted by code.
    """
    out: dict[str, int] = {}
    for key in accepted:
        code = key.split("::", 1)[0]
        out[code] = out.get(code, 0) + 1
    return dict(sorted(out.items()))


def partition(
    findings: list[Finding], baseline: dict[str, Any]
) -> tuple[list[Finding], list[Finding]]:
    """Split findings into new and already-accepted.

    Args:
        findings: All findings from the gate.
        baseline: The loaded baseline.

    Returns:
        ``(new, accepted)``.
    """
    known = set(baseline.get("accepted") or {})
    new: list[Finding] = []
    accepted: list[Finding] = []
    for f in findings:
        (accepted if key_of(f) in known else new).append(f)
    return new, accepted


def stale_entries(findings: list[Finding], baseline: dict[str, Any]) -> list[str]:
    """Find baseline entries that no longer correspond to any finding.

    A stale entry means the debt was cleared. Reporting it lets the baseline be
    tightened instead of silently granting an exception forever.

    Args:
        findings: All findings from the gate.
        baseline: The loaded baseline.

    Returns:
        Sorted keys that are accepted but no longer observed.
    """
    seen = {key_of(f) for f in findings}
    return sorted(set(baseline.get("accepted") or {}) - seen)
