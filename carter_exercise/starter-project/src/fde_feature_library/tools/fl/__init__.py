"""Feature Library tooling.

A dependency-free toolkit that derives machine-readable knowledge about the
Smart Contract feature library directly from source, so that manifests,
documentation and traceability can never drift away from the code they
describe.

The package deliberately depends on nothing outside the Python standard
library: it must run in CI, in a pre-commit hook and on a developer laptop
without access to the private ``contracts-api`` / ``inception-sdk`` wheels.
"""

__all__ = ["introspect", "model", "schema", "validate", "docgen", "graph", "cli"]

VERSION = "0.1.0"
