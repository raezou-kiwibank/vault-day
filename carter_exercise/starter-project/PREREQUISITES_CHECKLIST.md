# Thought Machine FDE Agent Skills: Pre-Workshop Checklist

Complete this checklist on your development machine **before the workshop** so the live session goes straight to building the Notice Saver product.

> **Your team may already have much of this.** Each section below starts with a **quick check**. If it passes, skip the rest of that section. `bash preflight.sh` (from `starter-project/`) runs every check in one go.

> **What you receive**: one bundle. Unzip it and work inside `starter-project/`:
> ```text
> workshop/
> ├── contracts_sdk/contracts_sdk/     Contracts SDK (already extracted)
> ├── inception_sdk/                   Inception SDK
> ├── fde-agent-skills/                the AI skills and bundled Vault 5.9 reference documentation
> └── starter-project/                 <-- this folder
> ```
> * The smart contract, tests and CLU pack are *not* in it: you generate them during the workshop.
> * **No internal repositories needed.** Python packages come from PyPI. The Contracts SDK, the Inception SDK, the feature library and the CLU binary are in the bundle (you only download a different version from the Thought Machine Documentation Portal if you need one).
> * **Vault version.** The bundled reference documentation covers Vault 5.9. A newer Vault 5.x environment (for example 5.11) works for the simulator and CLU 5.x.

---

## Summary

| # | Requirement | Quick check (skip if it passes) |
| :-- | :--- | :--- |
| 1 | macOS, Linux, or Windows with WSL2 | `uname -s` prints `Linux` or `Darwin` |
| 2 | Python 3.10+ with `venv` | `python3 --version` |
| 3 | Packages from `requirements.txt` in a virtual environment | `bash preflight.sh`, "requirements.txt packages importable" |
| 4 | Contracts SDK, Inception SDK, Feature Library, importable workspace | `python3 -c "import contracts_api, inception_sdk, feature_library, notice_saver"` |
| 5 | CLU 5.x binary | `<path-to-clu> --help` |
| 6 | Vault Core environment and service account token | `bash preflight.sh`, "Vault Core reachable (HTTP 200)" |
| 7 | An AI coding tool | `claude --version` (or `gemini`, `kiro`, `codex`) |

---

## 1. Operating system

The skills and test runners need a POSIX shell.

* **macOS** and **Linux** (Ubuntu 20.04+, Debian, Fedora) work natively.
* **Windows**: use **WSL2** with Ubuntu 22.04 or newer. Native PowerShell and Command Prompt are not supported (shell scripts and symlinks).

---

## 2. Python 3.10+

**Quick check:** `python3 --version` shows 3.10 or newer, and `python3 -m venv --help` works.

If `venv` is missing on Ubuntu or Debian: `sudo apt-get install python3-venv python3-pip`.

---

## 3. Python dependencies (`requirements.txt`)

**Quick check:** with your virtual environment active, `python3 -c "import absl, dateutil, yaml, requests, pydantic, semantic_version, git, confluent_kafka, jsonpath_ng, pytest"` prints nothing. If your team has its own environment with the Inception SDK already working, you already have these.

Create the virtual environment **inside the `starter-project/` folder** (the folder that contains `requirements.txt`). It creates a hidden `.venv/` folder there. Always run the project's commands from `starter-project/`, with the environment active.
```bash
cd starter-project
python3 -m venv .venv
source .venv/bin/activate        # your prompt now starts with (.venv)
pip install -r requirements.txt
```
Each time you open a new terminal, run `cd starter-project && source .venv/bin/activate` again.

If a corporate proxy blocks PyPI, ask for `pypi.org` and `files.pythonhosted.org` to be allowed in advance, or use your internal mirror (`pip install --index-url <mirror> -r requirements.txt`).

| Packages | Why they are needed |
| :--- | :--- |
| `pytest`, `pytest-xdist`, `parameterized`, `freezegun` | Running the unit and simulation tests (in parallel), timezone-parameterised tests |
| `requests`, `pydantic`, `PyYAML`, `python_dateutil`, `semantic_version`, `absl_py` | The simulator client, data objects, CLU resource parsing, date maths, Vault version checks |
| `gitpython` | Imported by the contract renderer |
| `confluent_kafka`, `jsonpath_ng` | Imported by the end-to-end test framework |
| `black`, `isort`, `flake8`, `mypy`, `types-*`, `coverage` | Formatting, linting, type checking and coverage the skills run on the code they write |

---

## 4. Contracts SDK, Inception SDK, Feature Library

**Quick check:** `python3 -c "import contracts_api, inception_sdk, feature_library, notice_saver"` succeeds. If your team already uses its own copies of the Inception SDK and Feature Library, keep them (use the same Vault version) and only make sure `starter-project/src` is on the path (the last line of the `.pth` file below).

### 4.1 Contracts SDK (`contracts_api`)
The Contracts SDK is in the bundle and already extracted, in `contracts_sdk/contracts_sdk` next to `starter-project/` (that inner folder holds `setup.py`). Install it from `starter-project/`, with the venv active:
```bash
pip install ../contracts_sdk/contracts_sdk
python3 -c "import contracts_api; print('Contracts SDK OK')"
```
If you need a different Vault version, log in to the Thought Machine Documentation Portal, go to **Vault Core, Reference, Contracts SDK Download**, download that version, and install it the same way.

### 4.2 Make the workspace importable
The bundle includes two plain source folders (not installed with `pip`):

| Folder | Where it is |
| :--- | :--- |
| `inception_sdk/` | In the workspace folder, next to `starter-project/` |
| `fde_feature_library/` | In `starter-project/src/` |

From `starter-project/` with the virtual environment active, add them and the product package to its Python path:
```bash
SITE_PACKAGES=$(python3 -c "import sysconfig; print(sysconfig.get_paths()['purelib'])")
printf '%s\n%s\n%s\n' "$(cd .. && pwd)" "$(cd src/fde_feature_library/src && pwd)" "$(cd src && pwd)" > "$SITE_PACKAGES/workspace.pth"
python3 -c "import contracts_api, inception_sdk, feature_library, notice_saver; print('Imports OK')"
```
`.vscode/settings.json` already points VS Code at the same folders.

---

## 5. CLU (Configuration Layer Utility)

CLU validates and imports the configuration pack that `/create-clu-resources` generates.

**Quick check:** `clu --help` (or the full path to your binary) prints "Configuration layer utility for Vault version 5.x".

1. The bundle has a CLU 5.x binary under `starter-project/src/notice_saver/tools/`, one folder per operating system. Use the one for your computer. If there is none for your system, download **CLU 5.x** from the Documentation Portal (the major version must match Vault Core 5.x) and put it in that folder (any sub-folder is fine).
2. Make it executable and check it runs:
   ```bash
   chmod +x "src/notice_saver/tools/<your-os-folder>/<clu-binary>"
   "src/notice_saver/tools/<your-os-folder>/<clu-binary>" --help
   ```
3. **Mac:** macOS may block a downloaded program ("cannot be opened because the developer cannot be verified"). Run `xattr -d com.apple.quarantine "<path-to-the-binary>"` and try again. Pick the Apple Silicon (arm64) or Intel (amd64) version that matches your Mac.
4. **Windows:** use the Linux binary inside WSL2.
5. Keep the binary out of git.

If CLU is already on your `PATH`, nothing else is needed: the skills look on the `PATH` and in the repository.

---

## 6. Vault Core environment and service account

Simulation and end-to-end tests, and `clu import`, need a running Vault Core and a service account. Unit tests and `clu validate` do not.

**Quick check:** `bash preflight.sh` shows "Vault Core reachable and token accepted (HTTP 200)". If your team already has a connection config for the Inception SDK, set `INC_ENVIRONMENT_CONFIG_PATH` and `INC_ENVIRONMENT_NAME` to it and skip 6.2.

### 6.1 Ask your Vault administrator for
1. The **Core API URL** of a sandbox or development environment.
2. A **service account** that may call the Core API: `POST /v1/contracts:simulate`, and the account, parameter, flag and calendar endpoints.
3. The service account **token**.

Use a non-production environment. The skills create and import resources.

### 6.2 Configure
```bash
cp environment.json.example environment.json
```
```json
{
  "sandbox": {
    "core_api_url": "https://<your-vault-core-api-host>",
    "auth": { "service_account": { "token": "<your-service-account-token>" } }
  }
}
```
Tell the test framework where it is, in every terminal you run tests from:
```bash
export INC_ENVIRONMENT_CONFIG_PATH=environment.json
export INC_ENVIRONMENT_NAME=sandbox
```
`environment.json` is gitignored. Never commit a token.

### 6.3 Verify
```bash
curl -s -o /dev/null -w "%{http_code}\n" -H "X-Auth-Token: <token>" "<core-api-url>/v1/vault-version"
```
Expect `200`. A `401` means a bad or expired token, and a timeout usually means you need the VPN.

---

## 7. AI coding tool

**Quick check:** your tool starts and answers a prompt.

* **Claude Code**: `npm install -g @anthropic-ai/claude-code` (Node.js 18+), then run `claude` and sign in.
* **Gemini CLI**, **Codex**, **Kiro**: install and sign in as your organisation requires.

Any editor works for reading the output; the project ships VS Code settings (Python, Pylance and YAML extensions help).

---

## 8. Pre-flight check

From `starter-project/`, with the virtual environment active and the two `INC_` variables exported:
```bash
bash preflight.sh
```
It checks the OS, Python, packages, SDK imports, the CLU binary, the Vault connection and the AI tool, and tells you which of the steps above you still need. A ✅ on a line means you can skip that step.

---

## 9. Troubleshooting

| Issue | Cause | Resolution |
| :--- | :--- | :--- |
| `python3: command not found` | Python missing or not on PATH | Install Python 3.10+ (`brew` on macOS, `apt` on Linux/WSL2). |
| `pip install` blocked or SSL error | Corporate proxy | Use your mirror (`--index-url`), or add your CA bundle: `pip config set global.cert /path/to/ca.crt`. |
| `No module named contracts_api` | SDK not installed in the active venv | Section 4.1, with the venv active. |
| Mac: "cannot be opened because the developer cannot be verified" (CLU) | macOS blocks downloaded programs | `xattr -d com.apple.quarantine "<path-to-the-binary>"` |
| `No module named notice_saver` (or `inception_sdk`) | `workspace.pth` missing a line | Re-run the section 4.2 command. |
| `ValueError: No environment_name found` when running tests | The two `INC_` variables are not exported | Section 6.2. |
| `401 Unauthorized` from Vault | Expired or wrong token | Ask your Vault administrator for a new token. |
| Cannot reach the Vault URL | VPN or firewall | Connect to the VPN that routes to your Vault cluster. |
| CLU fails with a version mismatch | CLU major version differs from Vault Core | Use CLU 5.x with Vault Core 5.x. |
| `Permission denied` running CLU or `install.sh` | Execute bit not set | `chmod +x <file>`. |
| Symlink errors on Windows | Running in PowerShell or CMD | Use WSL2. |
