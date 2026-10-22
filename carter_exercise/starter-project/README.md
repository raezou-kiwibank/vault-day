# Notice Saver Smart Contract Workspace

This is the starter workspace for building, testing and packaging the **Notice Saver** deposit product on Thought Machine Vault Core using AI agent skills. The smart contract, its tests and its CLU pack are the workshop exercise: you generate them in this workspace.

## Where things are

You received one bundle. Do all the work in `starter-project/`:
```text
workshop/
├── contracts_sdk/contracts_sdk/     Contracts SDK (already extracted)
├── inception_sdk/                   Inception SDK
├── fde-agent-skills/                the AI skills (install.sh is here)
└── starter-project/                 <-- this folder; run every command from here
```

---

## Already have part of this? Check, then skip

Your engineering team may already have some of these pieces. Run the check for each; if it passes, skip that step.

| You may already have | Quick check (from `starter-project/`) | If it passes |
| :--- | :--- | :--- |
| Python 3.10+, a virtual environment, the packages in `requirements.txt` | `bash preflight.sh` | Skip Steps 1.1 and 1.2 |
| Contracts SDK (`contracts_api`) | `python3 -c "import contracts_api"` | Skip Step 1.3 |
| Your own `inception_sdk` and `feature_library` | `python3 -c "import inception_sdk, feature_library"` | Skip Step 1.4. Use yours if it targets the same Vault version, and only add `src` to the `.pth` file. |
| CLU 5.x binary | `clu --help` (or the path to your binary) | Skip Step 1.5 |
| A Vault Core environment and service account | `bash preflight.sh` shows HTTP 200 | Skip Step 1.6. Point `INC_ENVIRONMENT_CONFIG_PATH` at your own config file if you have one. |
| An AI coding tool | `claude --version` (or your tool) | Skip Step 2.3 |

`bash preflight.sh` runs all of these checks in one go and tells you which setup steps you still need.

---

## 1. Before the workshop

Do these steps from `starter-project/`. Details and troubleshooting are in `PREREQUISITES_CHECKLIST.md`.

### Step 1.1: Create a virtual environment
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### Step 1.2: Install the dependencies
```bash
pip install -r requirements.txt
```

### Step 1.3: Install the Contracts SDK
The Contracts SDK is already in the bundle and already extracted. Install it from the `contracts_sdk/contracts_sdk` folder (the one that holds `setup.py`), next to `starter-project/`:
```bash
pip install ../contracts_sdk/contracts_sdk
python3 -c "import contracts_api; print('Contracts SDK OK')"
```
If you need a different Vault version, download that Contracts SDK from the Thought Machine Documentation Portal (**Vault Core, Reference, Contracts SDK Download**) and install it the same way.

### Step 1.4: Make the Inception SDK, the Feature Library and the product package importable
The bundle already contains `inception_sdk/` (next to `starter-project/`, so the `.pth` file picks it up through `..`) and `fde_feature_library/` (inside `starter-project/src/`). Add them and the product package to the virtual environment's Python path:
```bash
SITE_PACKAGES=$(python3 -c "import sysconfig; print(sysconfig.get_paths()['purelib'])")
printf '%s\n%s\n%s\n' "$(cd .. && pwd)" "$(cd src/fde_feature_library/src && pwd)" "$(cd src && pwd)" > "$SITE_PACKAGES/workspace.pth"
python3 -c "import contracts_api, inception_sdk, feature_library, notice_saver; print('Imports OK')"
```

### Step 1.5: Check the CLU binary
The bundle has a CLU 5.x binary under `src/notice_saver/tools/`, in a folder for each operating system it supports. Use the one for your computer. If there is none for your system, download **CLU 5.x** from the Documentation Portal (the major version must match Vault Core 5.x) and put it in the same folder. Make it executable and check it runs:
```bash
chmod +x "src/notice_saver/tools/<your-os-folder>/<clu-binary>"
"src/notice_saver/tools/<your-os-folder>/<clu-binary>" --help
```
**On a Mac**, macOS may block a downloaded program ("cannot be opened because the developer cannot be verified"). Remove the block with `xattr -d com.apple.quarantine "<path-to-the-binary>"`, then run it again. Use the Apple Silicon (arm64) or Intel (amd64) version that matches your Mac. **On Windows**, use the Linux binary inside WSL2.

### Step 1.6: Configure the Vault Core connection
```bash
cp environment.json.example environment.json
```
Edit `environment.json`: set `core_api_url` and the service account `token` for the environment named `sandbox`. The simulation and end-to-end tests read this file through two variables, which you export in every terminal you run tests from:
```bash
export INC_ENVIRONMENT_CONFIG_PATH=environment.json
export INC_ENVIRONMENT_NAME=sandbox
```
`environment.json` is gitignored. Never commit it.

### Step 1.7: Run the pre-flight check
```bash
bash preflight.sh
```
Every line should be a ✅. Fix any ❌ line, or skip it if you already have that piece set up another way.

---

## 2. Workshop day

### Step 2.1: Register the skills
The skills are already in the bundle, in `fde-agent-skills/` next to `starter-project/`. Register them with your AI tool, then come back:
```bash
cd ../fde-agent-skills && chmod +x install.sh && ./install.sh
cd ../starter-project
```
For Gemini CLI you can use `gemini extensions install $(pwd)` from `fde-agent-skills/` instead.

### Step 2.2: Start your AI tool from `starter-project/`
With the virtual environment active and the two `INC_` variables exported, start `claude`, `gemini` or your tool. The slash commands `/clarify-requirements`, `/create-test-plan`, `/create-smart-contract` and so on should be listed.

### Step 2.3: Build the product, one feature at a time
1. **`/clarify-requirements`**: turn the brief in `src/notice_saver/documentation/` (the product requirements PDF) into `REQUIREMENTS.md`.
2. **`/create-test-plan`**: write `TEST_PLAN.md`.
3. **For each feature**, in this order:
   1. **`/create-smart-contract`**: the first run writes `IMPLEMENTATION_PLAN.md`, then each run builds one feature.
   2. **`/create-clu-resources`**: add that feature's parameters, flags, accounts and schedules to the CLU pack, then validate it.
   3. **`/create-sc-tests`**: write and run the unit and simulation tests for that feature.
4. After the last feature: end-to-end tests (`/create-sc-tests`), then `/code-reviewer`, `/adversarial-review` and `/explainer-skill`.

If your team already has a stage's output, see the skip table in `WORKSHOP_AGENDA.md`.

### Running things
Use these **after** the skills have created the files they work on. Before that, the commands have nothing to run: pytest prints "no tests ran" (exit code 5) until `/create-sc-tests` has written tests, and the CLU command fails until `/create-clu-resources` has created `manifest.yaml`. This is normal. To check your setup before the workshop, use `bash preflight.sh` instead.
```bash
# all tests, in parallel (unit tests need no Vault; simulation tests do)
python -m pytest src/notice_saver/tests -n 4

# only the unit tests
python -m pytest src/notice_saver/tests/unit

# check the CLU pack (offline)
"src/notice_saver/tools/<your-os-folder>/<clu-binary>" validate src/notice_saver/manifest.yaml
```

---

## Workspace structure

What you receive, and what the skills generate (marked ➕):
```
starter-project/
├── PREREQUISITES_CHECKLIST.md  # Detailed setup checklist
├── preflight.sh                # One-command readiness check
├── environment.json.example    # Template for the Vault Core connection
├── requirements.txt
├── src/
│   ├── fde_feature_library/    # Feature library (included in the bundle)
│   └── notice_saver/
│       ├── documentation/      # Product requirements PDF (the brief)
│       │   ├── REQUIREMENTS.md          ➕ /clarify-requirements
│       │   ├── TEST_PLAN.md             ➕ /create-test-plan
│       │   └── IMPLEMENTATION_PLAN.md   ➕ /create-smart-contract
│       ├── contracts/template/ ➕ the recipe contract (wires the features together)
│       ├── features/           ➕ product-specific features (reusable business capabilities)
│       ├── common/             ➕ helpers that are not features
│       ├── parameters/, parameter_values/, parameter_value_hierarchy_nodes/,
│       │   internal_accounts/, flag_definitions/, account_schedule_tags/,
│       │   manifest.yaml       ➕ CLU configuration pack (/create-clu-resources)
│       ├── tests/{unit,simulation,e2e}/  ➕ /create-sc-tests
│       └── tools/              # CLU binary
├── tests/test_smoke.py         # Workspace smoke test
└── .vscode/                    # VS Code interpreter and pytest settings
```
