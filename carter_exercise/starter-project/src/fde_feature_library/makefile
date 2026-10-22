.PHONY: sync format check scan test check-all \
        fl-scan fl-check fl-docs fl-derive fl-export fl-bundle fl-graph fl-test \
        knowledge verify help

# `fl` is the feature library knowledge toolchain in tools/. It is deliberately
# dependency-free so every target below runs with the system Python, before
# `make sync` has fetched the private contracts-api / inception-sdk wheels.
PY ?= python3
FL := PYTHONPATH=tools $(PY) -m fl

help:
	@echo "Setup"
	@echo "  make sync         Authenticate to Artifact Registry and install all dependencies"
	@echo ""
	@echo "Code quality (needs the venv)"
	@echo "  make format       ruff format + ruff check --fix"
	@echo "  make check        ruff check + mypy"
	@echo "  make scan         semgrep Smart Contract logic scan"
	@echo "  make test         full pytest suite with coverage"
	@echo ""
	@echo "Knowledge layer (no dependencies, no credentials)"
	@echo "  make fl-scan      Summarise the library"
	@echo "  make fl-check     Completeness gate: parameters, records, docs, tests, products"
	@echo "  make fl-derive    Refresh derived facts inside knowledge records"
	@echo "  make fl-docs      Regenerate feature reference documentation"
	@echo "  make fl-export    Emit the machine-readable knowledge pack"
	@echo "  make fl-bundle    Publish the OKF Feature Knowledge Bundle"
	@echo "  make fl-graph     Emit the feature/product composition graph"
	@echo "  make fl-test      Test the toolchain itself"
	@echo ""
	@echo "Aggregates"
	@echo "  make knowledge    fl-derive + fl-docs + fl-export + fl-bundle"
	@echo "  make verify       Everything a pull request must pass"

# Authenticate to Artifact registry & Github and then run uv sync
sync:
	@chmod +x scripts/auth.sh
	# Source the auth script and run uv in the same shell session
	/bin/bash -c "source scripts/auth.sh && uv sync --all-packages --all-groups"

# Format code (replaces black and isort)
format:
	uv run ruff format .
	uv run ruff check --fix .

# Linting & Typechecking
check:
	uv run ruff check
	uv run mypy .

# Smart Contract Logic Scan
scan:
	uv run semgrep scan --config semgrep.yaml --error

# Coverage
test:
	@chmod +x scripts/auth.sh
	/bin/bash -c "source scripts/auth.sh && uv run --env-file .env coverage run -m pytest feature_library/tests && uv run coverage report"

# ---------------------------------------------------------------------------
# Knowledge layer
# ---------------------------------------------------------------------------

fl-scan:
	@$(FL) scan

# The gate fails the build only on errors. Warnings are the visible backlog:
# missing knowledge records, missing simulation cover, features no product uses.
fl-check:
	@$(FL) check --fail-on error --verbose

fl-derive:
	@$(FL) derive --write

fl-docs:
	@$(FL) docs --write

fl-export:
	@$(FL) export -o docs/knowledge-pack.json

fl-bundle:
	@$(FL) bundle

fl-graph:
	@$(FL) graph

fl-test:
	@$(PY) -m unittest discover -s tools/tests -t tools

knowledge: fl-derive fl-docs fl-export fl-bundle
	@echo "Knowledge layer regenerated. Commit the changes."

# Run everything. Ordered cheapest-first so a failure surfaces quickly, and so
# the credential-free checks still run when the private wheels are unavailable.
check-all: fl-test fl-check format check scan test

verify: check-all
