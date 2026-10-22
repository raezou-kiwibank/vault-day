# FDE Feature Library

This repo is intended to hold some useful libraries and tools for use on client projects.

## Introduction

This repository contains the `feature_library` package. It uses a structured layout where the core library and its tests are placed inside the `feature_library` subdirectory, managed by a global `pyproject.toml` configuration file at the repository root and a package-specific `pyproject.toml` inside the subdirectory. It uses `uv` for dependency management and Pytest for testing.

## Feature Library

The Feature Library contains a set of converted features from the Inception Product Library. These features have been modernised following patterns defined in the modernise-feature skill. You can see more detail on some of these changes on Confluence.

### Running tests

Tests can be executed natively from the repository root. You do **not** need to `cd` into the `feature_library` folder.

The root `.env` file automatically sets environment variables for root-level execution. This includes the path to the repository's `environment_config.json` file and the target environment name:

```shell
INC_ENVIRONMENT_CONFIG_PATH=$HOME/config/environment_config.json
INC_FRAMEWORK_CONFIG_PATH=$HOME/config/framework_config.json
```

NB: it is recommended to create the files in `$HOME/config` with valid Vault environment configs. See the files in this repo's `config/` folder for example content structure.

To run the entire test suite (using the root makefile):

```bash
make test
```

To run a specific test file from the root:

```shell
uv run --env-file .env pytest <test-file-path>
```

For example:

```shell
uv run --env-file .env pytest tests/deposit/interest/interest_application/simulation/test_interest_application.py
```

### Refreshing Artifact Registry Credentials

If your access to the `tm-wheels` index expires or you get a "403 Forbidden" error, you can refresh your credentials by running:

```bash
# This triggers the authentication script without performing a full sync
source scripts/auth.sh
```

Alternatively, you can manually run the following if the script fails:

```bash
cloud-auth -t api -r cloudops tm-gcp-dh-clusters-0
export UV_INDEX_TM_WHEELS_USERNAME="oauth2accesstoken"
export UV_INDEX_TM_WHEELS_PASSWORD=$(gcloud auth print-access-token)
```

### IDE configuration

The Feature Library uses a `src` layout (e.g., `feature_library/src/feature_library`). To ensure your IDE (VS Code, PyCharm, etc.) correctly resolves these imports for type-hinting, autocompletion, and hover support, you must configure the `src` directories as source roots.

#### VS Code
The root `.vscode/settings.json` should be updated to include the `src` folder of each project you are working on. This project uses `python.analysis.extraPaths` for this purpose:

```json
{
    "python.analysis.extraPaths": [
        "./feature_library/src"
    ]
}
```

#### PyCharm

1. Right-click the `src` folder of the specific project (e.g., `feature_library/src`).
2. Select **Mark Directory as** -> **Sources Root**.

#### Why this is necessary

Standardizing on imports that exclude the `src.` prefix (e.g., `import feature_library...`) ensures the code remains production-ready and compatible with standard Python packaging. Explicitly marking these folders as source roots in your IDE allows the language server to "connect" these imports to the actual files in your workspace.

#### ty (Type Checker)

The project is configured to work with the `ty` type checker. Imports are resolved using the `extra-paths` configuration in the root `pyproject.toml`.

To run a check manually:

```bash
uv run ty check path/to/file.py
```

The VS Code extension will also automatically pick up these settings.

### Accessing the Feature Library in project repos

To access the Feature Library using UV you can add it as a dependency in your project's toml:

Access the latest commit of the provided branch

```toml
feature_library = { git = "ssh://git@github.com/thought-machine-external/fde_feature_library.git", subdirectory = "feature_library", branch = "master" }
```

Access a specific git tag

```toml
feature_library = { git = "ssh://git@github.com/thought-machine-external/fde_feature_library.git", tag = “<git tag>”, subdirectory = "feature_library" }
```

Access a specific commit

```toml
feature_library = { git = "ssh://git@github.com/thought-machine-external/fde_feature_library.git", rev = “<commit-hash>”, subdirectory = "feature_library" }
```

## Release Process

To create an official release of the `feature_library` when direct pushes to `master` are restricted, use the **Chore PR Branch** workflow to keep package versions in sync with Git tags.

1. **Create a Version Bump Branch**
   Create a new branch from `master` specifically for the version bump (e.g., `chore/bump-version-1.0.0`):

   ```bash
   git checkout master
   git pull
   git checkout -b chore/bump-version-1.0.0
   ```

2. **Bump the Versions**
   Update the `version` field to your target release version (e.g., `1.0.0`) in both:
   - `pyproject.toml` (root)
   - `feature_library/pyproject.toml`

3. **Commit and Open a Pull Request**
   Stage, commit, and push the version changes to open a PR into `master`:

   ```bash
   git add pyproject.toml feature_library/pyproject.toml
   git commit -m "chore: bump version to 1.0.0"
   git push origin chore/bump-version-1.0.0
   ```

4. **Merge the PR**
   Complete the review process and merge the PR into `master` on GitHub.

5. **Tag the Release Commit**
   Once merged, switch back to your local `master` branch, pull down the merged commit, create the annotated tag (`1.0.0`), and push the tag to GitHub:

   ```bash
   git checkout master
   git pull
   git tag -a 1.0.0 -m "Release 1.0.0"
   git push origin 1.0.0
   ```
