# Project Context: FDE Feature Library

A dedicated repository for developing and testing the Feature Library, utilizing Thought Machine's `contracts-api` and `inception-sdk`.

## Project Overview

- **Architecture:** Dedicated repository containing the `feature_library` package, with tests and sources symlinked to the root for ease of use.
- **Tech Stack:** Python 3.10+, `uv` (dependency management), `ruff` (formatting and linting), `mypy` (type checking), `pytest` (testing).
- **Core Libraries:** `contracts-api` (TM Smart Contract API), `inception-sdk` (Simulation and testing framework).

## Key Commands

All commands should be executed from the **repository root**:

### Dependency Management

- **Install & Sync Dependencies:** `make sync` (runs `uv sync --all-packages --all-groups` to install both root and package dev groups)

### Verification & Testing

- **Format code:** `make format` (runs `ruff format` and `ruff check --fix`)
- **Lint & Typecheck:** `make check` (runs `ruff` and `mypy`)
- **Run all tests:** `make test` (runs the full test suite with coverage from root)
- **Run a specific test:** `uv run --env-file .env pytest tests/path/to/test.py`
- **Security Scan:** `make scan` (runs `semgrep` for Smart Contract logic)
- **Full Verification:** `make check-all`

## Development Conventions

### Smart Contract Constraints

- **Class Support:** Smart Contracts do **NOT** support Python classes. Use Functional `NamedTuple` syntax for data structures.
- **Imports:** Adhere to strict import ordering: `future`, `standard-library`, `third-party`, `library`, `feature_library`, `features`, `contracts_api`, `inception_sdk`, `first-party`, `local-folder`.
- **Type Annotations:** Functional SC code should use type annotations. `ANN401` (allowing `Any`) is permitted where more specific types are not feasible.

### Testing Practices

- **Unit Tests:** Located in `tests/**/unit/`. Use `inception_sdk.test_framework.contracts.unit.common.FeatureTest` and `initialise_mock_state` from `tests.utils`.
- **Simulation Tests:** Located in `tests/**/simulation/`. Use `inception_sdk.test_framework.contracts.simulation.utils.SimulationTestCase`.
- **Cleanup:** Always use `self.addCleanup(patcher.stop)` when starting manual patches in `setUp` to prevent mock pollution across the test suite.

### IDE Configuration

- **Source Roots:** IDEs must be configured to treat the `src` directory (pointing to `feature_library/src`) as a source root to resolve imports correctly.
- **VS Code:** `python.analysis.extraPaths` is configured in `.vscode/settings.json`.

## Directory Structure

- `feature_library/`: Core library of Smart Contract features (accruals, interest, limits).
- `config/`: Global environment configurations (contains `environment_config.json`).
- `tests/`: Root-level symbolic link pointing to `feature_library/tests/`.
- `src/`: Root-level symbolic link pointing to `feature_library/src/`.
- `makefile`: Root-level automation.
- `pyproject.toml`: Global linting, workspace, and pytest configuration.
