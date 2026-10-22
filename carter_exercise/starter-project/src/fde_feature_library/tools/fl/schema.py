"""The knowledge records this library authors, and a validator for them.

These are the *authoring* formats. The *published* artefact is a Feature
Knowledge Bundle (see :mod:`fl.bundle`), which conforms to Google Cloud's Open
Knowledge Format v0.2 — a tree of markdown files carrying YAML frontmatter. Per
that spec's own guidance the bundle records ``okf_version`` as a field and does
not take the OKF name for this project's schemas, not least because "OKF" was
already the Open Knowledge Foundation's acronym for twenty years.

Two authoring record types are defined:

``<module>.feature.yaml``
    Sits beside a feature module and carries the business knowledge that source
    code cannot express — what capability the feature delivers, which business
    requirements it satisfies, which products consume it, how to configure and
    simulate it. Technical facts (parameters, fetchers, events, hooks) are
    *derived* from the AST and mirrored into the record so that a consumer gets
    one complete document, and so that drift between the record and the code is
    a mechanical failure rather than a review opinion.

``products/<id>/product.yaml``
    Declares a product as a composition of features plus the parameter values
    that configure it, its hook wiring, its test artefacts and its relationships
    to other products.

Both are plain YAML so a human can read them in a pull request, and both are
schema-validated so an agent can rely on their shape. The schemas are expressed
as JSON Schema (2020-12 vocabulary) and checked by a small validator here,
because ``jsonschema`` is not a dependency this repo can assume at hook time.
"""

from __future__ import annotations

import re
from typing import Any

# The authoring records below are OUR format. The published bundle (see
# fl/bundle.py) is what conforms to Google Cloud's Open Knowledge Format; per
# that spec's guidance we carry `okf_version` as a field and never take the OKF
# name for our own schema.
RECORD_SCHEMA_VERSION = "feature-knowledge-record/0.1"
PRODUCT_SCHEMA_VERSION = "product-knowledge-record/0.1"
OKF_VERSION = "0.2"
PROFILE = "https://thoughtmachine.example/fde/schemas/feature-knowledge-bundle/1.0.json"

# --------------------------------------------------------------------------
# Shared fragments
# --------------------------------------------------------------------------

_ID_PATTERN = r"^[a-z0-9]+([._-][a-z0-9]+)*$"

_REQUIREMENT = {
    "type": "object",
    "required": ["id", "statement"],
    "additionalProperties": False,
    "properties": {
        "id": {"type": "string", "minLength": 1,
               "description": "Stable requirement id, e.g. REQ-DEP-014."},
        "statement": {"type": "string", "minLength": 1,
                      "description": "The requirement in the analyst's own words."},
        "source": {"type": "string",
                   "description": "Where it came from: a REQUIREMENTS.md heading, ticket or regulation."},
        "satisfied_by": {"type": "array", "items": {"type": "string"},
                         "description": "Functions or parameters in this feature that implement it."},
        "verified_by": {"type": "array", "items": {"type": "string"},
                        "description": "Test node ids that prove it, e.g. tests/...::TestX::test_y."},
    },
}

_PARAMETER_DOC = {
    "type": "object",
    "required": ["parameter_id", "description"],
    "additionalProperties": False,
    "properties": {
        "parameter_id": {"type": "string", "pattern": r"^&\{[a-z0-9_]+\}$",
                         "description": "The CLU reference, e.g. &{denomination}."},
        "display_name": {"type": "string"},
        "description": {"type": "string", "minLength": 1,
                        "description": "What the value means to the business."},
        "level": {"type": "string", "enum": ["template", "instance", "global", ""],
                  "description": "Where in the parameter value hierarchy the value is set."},
        "shape": {"type": "string",
                  "description": "The Vault shape/constraint, e.g. decimal_constraint."},
        "example": {"type": "string"},
        "resource": {"type": "string",
                     "description": "Repo-relative path of the backing *.resource.yaml."},
        "drives": {"type": "string",
                   "description": "The behaviour this value changes — the client-facing effect."},
    },
}

_DERIVED = {
    "type": "object",
    "additionalProperties": True,
    "description": "Mirrored from the source AST by `fl derive`. Never hand-edit.",
    "properties": {
        "expected_parameters": {"type": "array", "items": {"type": "string"}},
        "data_fetchers": {"type": "array", "items": {"type": "string"}},
        "event_types": {"type": "array", "items": {"type": "string"}},
        "notifications": {"type": "array", "items": {"type": "string"}},
        "balance_addresses": {"type": "array", "items": {"type": "string"}},
        "public_functions": {"type": "array", "items": {"type": "string"}},
        "interfaces_provided": {"type": "array", "items": {"type": "string"}},
        "interfaces_consumed": {"type": "array", "items": {"type": "string"}},
        "depends_on": {"type": "array", "items": {"type": "string"}},
        "hook_affinity": {"type": "array", "items": {"type": "string"}},
        "source_digest": {"type": "string",
                          "description": "Digest of the derived facts; changes when the code's public surface changes."},
    },
}

HOOKS = [
    "activation_hook",
    "conversion_hook",
    "deactivation_hook",
    "derived_parameter_hook",
    "post_parameter_change_hook",
    "post_posting_hook",
    "pre_parameter_change_hook",
    "pre_posting_hook",
    "scheduled_event_hook",
]

# --------------------------------------------------------------------------
# Feature record
# --------------------------------------------------------------------------

FEATURE_SCHEMA: dict[str, Any] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "https://thoughtmachine.example/fde/schemas/feature-knowledge-record-0.1.json",
    "title": "Feature Knowledge Record",
    "type": "object",
    "required": ["schema", "id", "module", "domain", "status", "capability",
                 "client_functionality", "hooks"],
    "additionalProperties": False,
    "properties": {
        "schema": {"type": "string", "enum": [RECORD_SCHEMA_VERSION],
                   "description": "Authoring record schema version."},
        "id": {"type": "string", "pattern": _ID_PATTERN,
               "description": "Stable feature id, e.g. deposit.interest.interest_accrual."},
        "module": {"type": "string", "minLength": 1,
                   "description": "Dotted Python module implementing the feature."},
        "version": {"type": "string", "pattern": r"^\d+\.\d+\.\d+$"},
        "domain": {"type": "string",
                   "enum": ["common", "deposit", "lending", "corporate", "shared"]},
        "status": {"type": "string", "enum": ["draft", "supported", "deprecated"]},
        "capability": {"type": "string", "minLength": 10,
                       "description": "One sentence: the business capability delivered."},
        "client_functionality": {"type": "string", "minLength": 20,
                                 "description": "What the bank's customer actually experiences."},
        "when_to_use": {"type": "string"},
        "when_not_to_use": {"type": "string"},
        "hooks": {"type": "array", "minItems": 1,
                  "items": {"type": "string", "enum": HOOKS},
                  "description": "The contract hooks this feature is designed to be called from."},
        "parameters": {"type": "array", "items": _PARAMETER_DOC},
        "requirements": {"type": "array", "items": _REQUIREMENT},
        "products": {"type": "array", "items": {"type": "string"},
                     "description": "Product ids that compose this feature. A feature with none is incomplete."},
        "simulation_notes": {"type": "string",
                             "description": "How to exercise the feature in a simulation test."},
        "determinism_notes": {"type": "string",
                              "description": "Anything a reader must know to reason about repeatability."},
        "owner": {"type": "string"},
        "tags": {"type": "array", "items": {"type": "string"}},
        "derived": _DERIVED,
    },
}

# --------------------------------------------------------------------------
# Product record
# --------------------------------------------------------------------------

PRODUCT_SCHEMA: dict[str, Any] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "https://thoughtmachine.example/fde/schemas/product-knowledge-record-0.1.json",
    "title": "Product Knowledge Record",
    "type": "object",
    "required": ["schema", "id", "display_name", "domain", "tside", "summary",
                 "contract", "features"],
    "additionalProperties": False,
    "properties": {
        "schema": {"type": "string", "enum": [PRODUCT_SCHEMA_VERSION]},
        "id": {"type": "string", "pattern": _ID_PATTERN},
        "display_name": {"type": "string", "minLength": 1},
        "version": {"type": "string"},
        "domain": {"type": "string",
                   "enum": ["deposit", "lending", "corporate", "shared"]},
        "tside": {"type": "string", "enum": ["ASSET", "LIABILITY"]},
        "summary": {"type": "string", "minLength": 20},
        "contract": {"type": "string", "minLength": 1,
                     "description": "Repo-relative path to the contract template."},
        "features": {"type": "array", "minItems": 1, "items": {"type": "string"},
                     "description": "Feature ids composed by this product."},
        "hooks": {"type": "object", "additionalProperties": {"type": "array", "items": {"type": "string"}},
                  "description": "Hook name -> the feature ids wired into it."},
        "parameters": {"type": "object", "additionalProperties": True,
                       "description": "Default parameter values, by parameter id."},
        "internal_accounts": {"type": "array", "items": {"type": "string"}},
        "balance_addresses": {"type": "array", "items": {"type": "string"}},
        "requirements": {"type": "array", "items": _REQUIREMENT},
        "tests": {"type": "object",
                  "additionalProperties": {"type": "array", "items": {"type": "string"}},
                  "description": "Tier -> test paths, e.g. {unit: [...], simulation: [...], e2e: [...]}."},
        "linked_products": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["product", "relationship"],
                "additionalProperties": False,
                "properties": {
                    "product": {"type": "string"},
                    "relationship": {"type": "string",
                                     "description": "e.g. offset, sweep_source, pooling_member."},
                    "description": {"type": "string"},
                    "parameter": {"type": "string",
                                  "description": "The parameter carrying the linked account id."},
                },
            },
            "description": "Relationships to other products, e.g. a current account offsetting a mortgage.",
        },
    },
}


# --------------------------------------------------------------------------
# Minimal JSON Schema validator
# --------------------------------------------------------------------------


def validate_instance(instance: Any, schema: dict[str, Any], path: str = "$") -> list[str]:
    """Validate a value against the JSON Schema subset used by this module.

    Supports ``type``, ``required``, ``properties``, ``additionalProperties``,
    ``items``, ``minItems``, ``enum``, ``pattern``, ``minLength`` and
    ``additionalProperties`` as a schema. That is everything the two schemas
    above use; anything richer would be a reason to take a real dependency
    rather than to grow this function.

    Args:
        instance: The value to check.
        schema: The schema to check it against.
        path: JSON-pointer-ish location used in messages.

    Returns:
        A list of human-readable error strings; empty when valid.
    """
    errors: list[str] = []
    expected = schema.get("type")

    if expected:
        if not _type_ok(instance, expected):
            actual = type(instance).__name__
            return [f"{path}: expected {expected}, got {actual}"]

    if "enum" in schema and instance not in schema["enum"]:
        errors.append(f"{path}: {instance!r} is not one of {schema['enum']}")

    if isinstance(instance, str):
        if "minLength" in schema and len(instance) < schema["minLength"]:
            errors.append(
                f"{path}: string is shorter than {schema['minLength']} characters"
            )
        pattern = schema.get("pattern")
        if pattern and not re.match(pattern, instance):
            errors.append(f"{path}: {instance!r} does not match {pattern}")

    if isinstance(instance, list):
        if "minItems" in schema and len(instance) < schema["minItems"]:
            errors.append(f"{path}: needs at least {schema['minItems']} item(s)")
        item_schema = schema.get("items")
        if isinstance(item_schema, dict):
            for i, item in enumerate(instance):
                errors.extend(validate_instance(item, item_schema, f"{path}[{i}]"))

    if isinstance(instance, dict):
        for key in schema.get("required", []):
            if key not in instance or instance[key] in (None, "", [], {}):
                errors.append(f"{path}: missing required property {key!r}")
        props = schema.get("properties", {})
        additional = schema.get("additionalProperties", True)
        for key, value in instance.items():
            if key in props:
                errors.extend(validate_instance(value, props[key], f"{path}.{key}"))
            elif isinstance(additional, dict):
                errors.extend(validate_instance(value, additional, f"{path}.{key}"))
            elif additional is False:
                errors.append(f"{path}: unexpected property {key!r}")

    return errors


def _type_ok(instance: Any, expected: str | list[str]) -> bool:
    """Check a value against a JSON Schema ``type`` keyword.

    Args:
        instance: The value.
        expected: A type name or list of type names.

    Returns:
        True when the value matches at least one named type.
    """
    if isinstance(expected, list):
        return any(_type_ok(instance, e) for e in expected)
    mapping = {
        "object": dict,
        "array": list,
        "string": str,
        "number": (int, float),
        "integer": int,
        "boolean": bool,
        "null": type(None),
    }
    py = mapping.get(expected)
    if py is None:
        return True
    if expected in {"number", "integer"} and isinstance(instance, bool):
        return False
    return isinstance(instance, py)
