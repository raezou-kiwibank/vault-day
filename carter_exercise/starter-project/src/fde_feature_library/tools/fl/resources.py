"""Index the CLU resource definitions that back a feature's configuration.

A feature declares the parameters it needs as ``&{parameter_id}`` references.
Those references only mean something once a matching ``PARAMETER`` resource
exists in a CLU config pack: the reference is resolved at deployment time, not
at contract-authoring time, so a typo in a reference is invisible to Python,
to ``ruff`` and to the unit tests, and only fails when someone tries to deploy.

Indexing the resource definitions lets the toolchain close that gap — every
reference can be checked against a real definition on every commit.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any

from . import yamlite

RESOURCE_SUFFIX = ".resource.yaml"


@dataclass
class ResourceDef:
    """One CLU resource definition file.

    Attributes:
        path: Path to the ``*.resource.yaml`` file.
        type: The CLU resource type, e.g. ``PARAMETER`` or ``FLAG_DEFINITION``.
        id: The resource id CLU addresses it by.
        payload: The parsed payload, when it could be read.
        payload_raw: The payload as written, retained for diagnostics.
        errors: Problems found while reading this file.
    """

    path: str
    type: str = ""
    id: str = ""
    payload: Any = None
    payload_raw: str = ""
    errors: list[str] = field(default_factory=list)

    @property
    def parameter_id(self) -> str:
        """The parameter id declared inside a ``PARAMETER`` payload.

        Returns:
            The nested ``parameter.id``, or an empty string when absent or when
            this is not a parameter resource.
        """
        if not isinstance(self.payload, dict):
            return ""
        param = self.payload.get("parameter")
        if isinstance(param, dict):
            return str(param.get("id") or "")
        return ""

    @property
    def constraint_kind(self) -> str:
        """The constraint type declared for a parameter, if any.

        Returns:
            e.g. ``decimal_constraint``, ``string_constraint``, or an empty
            string when no constraint is declared.
        """
        if not isinstance(self.payload, dict):
            return ""
        param = self.payload.get("parameter")
        if not isinstance(param, dict):
            return ""
        constraint = param.get("constraint")
        if isinstance(constraint, dict) and constraint:
            return next(iter(constraint))
        return ""

    @property
    def description(self) -> str:
        """The parameter's metadata description, when present.

        Returns:
            The description text, or an empty string.
        """
        if not isinstance(self.payload, dict):
            return ""
        param = self.payload.get("parameter")
        if not isinstance(param, dict):
            return ""
        meta = param.get("metadata")
        if isinstance(meta, dict):
            return str(meta.get("description") or "")
        return ""


@dataclass
class ResourceIndex:
    """All resource definitions discovered under a set of roots."""

    by_path: dict[str, ResourceDef] = field(default_factory=dict)

    @property
    def parameters(self) -> dict[str, ResourceDef]:
        """Parameter resources keyed by their declared parameter id.

        Returns:
            Mapping of parameter id to its definition. When two files declare
            the same id the first by sorted path wins; the duplicate is
            reported separately by :meth:`duplicate_parameter_ids`.
        """
        out: dict[str, ResourceDef] = {}
        for path in sorted(self.by_path):
            rd = self.by_path[path]
            if rd.type != "PARAMETER":
                continue
            key = rd.parameter_id or rd.id
            if key and key not in out:
                out[key] = rd
        return out

    def duplicate_parameter_ids(self) -> dict[str, list[str]]:
        """Find parameter ids declared by more than one resource file.

        Returns:
            Mapping of parameter id to the paths that declare it, for ids with
            more than one declaration.
        """
        seen: dict[str, list[str]] = {}
        for path in sorted(self.by_path):
            rd = self.by_path[path]
            if rd.type != "PARAMETER":
                continue
            key = rd.parameter_id or rd.id
            if key:
                seen.setdefault(key, []).append(path)
        return {k: v for k, v in seen.items() if len(v) > 1}

    def by_type(self, resource_type: str) -> list[ResourceDef]:
        """All resources of a given CLU type.

        Args:
            resource_type: e.g. ``PARAMETER``, ``FLAG_DEFINITION``.

        Returns:
            Matching definitions, sorted by path.
        """
        return [self.by_path[p] for p in sorted(self.by_path) if self.by_path[p].type == resource_type]


def read_resource(path: str) -> ResourceDef:
    """Read one CLU resource definition.

    Args:
        path: Path to a ``*.resource.yaml`` file.

    Returns:
        The parsed definition. Read and parse failures are recorded on the
        result rather than raised.
    """
    rd = ResourceDef(path=path)
    try:
        with open(path, "r", encoding="utf-8") as fh:
            text = fh.read()
    except OSError as exc:
        rd.errors.append(f"unreadable: {exc}")
        return rd
    try:
        doc = yamlite.loads(text)
    except Exception as exc:  # noqa: BLE001 - surface any parse problem as data
        rd.errors.append(f"invalid yaml: {exc}")
        return rd
    if not isinstance(doc, dict):
        rd.errors.append("top level is not a mapping")
        return rd
    rd.type = str(doc.get("type") or "")
    rd.id = str(doc.get("id") or "")
    payload = doc.get("payload")
    if isinstance(payload, str):
        rd.payload_raw = payload
        try:
            rd.payload = yamlite.loads(payload)
        except Exception as exc:  # noqa: BLE001
            rd.errors.append(f"invalid payload yaml: {exc}")
    else:
        rd.payload = payload
    return rd


def scan_resources(*roots: str) -> ResourceIndex:
    """Discover and read every resource definition under the given roots.

    Args:
        *roots: Directories to walk.

    Returns:
        The populated index.
    """
    index = ResourceIndex()
    for root in roots:
        if not os.path.isdir(root):
            continue
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d != "__pycache__"]
            for fn in filenames:
                if fn.endswith(RESOURCE_SUFFIX):
                    path = os.path.join(dirpath, fn)
                    index.by_path[path] = read_resource(path)
    return index
