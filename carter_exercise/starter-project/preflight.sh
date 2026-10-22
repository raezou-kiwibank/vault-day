#!/usr/bin/env bash
# Pre-flight check for the Notice Saver workshop. Run from starter-project/ with the venv active.
# Every check is independent: a passing line means you can skip that setup step.
cd "$(dirname "$0")" || exit 1
ok()   { echo "✅ $1"; }
warn() { echo "❌ $1"; FAILED=1; }
FAILED=0

echo "=== WORKSTATION READINESS CHECK ==="

# 1. OS and Python
case "$(uname -s)" in Linux|Darwin) ok "POSIX environment ($(uname -s))";; *) warn "Windows must use WSL2";; esac
python3 -c 'import sys; assert sys.version_info >= (3, 10)' 2>/dev/null \
  && ok "Python >= 3.10 ($(python3 --version))" || warn "Python 3.10+ required"

# 2. Virtual environment and requirements.txt
if [[ -n "$VIRTUAL_ENV" ]]; then
  ok "Virtual environment active: $VIRTUAL_ENV"
  python3 -c 'import absl, dateutil, yaml, requests, pydantic, semantic_version, git, confluent_kafka, jsonpath_ng, pytest' 2>/dev/null \
    && ok "requirements.txt packages importable" \
    || warn "Missing packages: pip install -r requirements.txt"
else
  warn "No active virtual environment: python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt"
fi

# 3. Contracts SDK, Inception SDK, Feature Library and the product package
python3 -c 'import contracts_api' 2>/dev/null && ok "contracts_api (Contracts SDK)" \
  || warn "contracts_api missing: pip install ../contracts_sdk/contracts_sdk"
python3 -c 'import inception_sdk, feature_library' 2>/dev/null \
  && ok "inception_sdk and feature_library importable" \
  || warn "inception_sdk / feature_library not importable: see 'Make the workspace importable' in PREREQUISITES_CHECKLIST.md"
python3 -c 'import notice_saver' 2>/dev/null && ok "notice_saver package importable" \
  || warn "notice_saver not importable: add starter-project/src to workspace.pth"

# 4. CLU binary (version 5.x) on PATH or inside the repository
CLU="$(command -v clu 2>/dev/null)"
[[ -z "$CLU" ]] && CLU="$(find src tools -type f -name 'clu*' 2>/dev/null | grep -v '\.md$' | head -1)"
if [[ -n "$CLU" && -x "$CLU" ]]; then
  ok "CLU binary: $CLU"
else
  warn "CLU binary not found or not executable (place it under src/notice_saver/tools/ and chmod +x)"
fi

# 5. Vault Core connection config and reachability
CONFIG="${INC_ENVIRONMENT_CONFIG_PATH:-environment.json}"
ENVNAME="${INC_ENVIRONMENT_NAME:-sandbox}"
if [[ -f "$CONFIG" ]]; then
  ok "Environment config found: $CONFIG (environment '$ENVNAME')"
  URL="$(python3 -c "import json;print(json.load(open('$CONFIG'))['$ENVNAME']['core_api_url'])" 2>/dev/null)"
  TOKEN="$(python3 -c "import json;print(json.load(open('$CONFIG'))['$ENVNAME']['auth']['service_account']['token'])" 2>/dev/null)"
  if [[ -n "$URL" && -n "$TOKEN" && "$URL" != *"your-org"* && "$TOKEN" != "<"* ]]; then
    CODE="$(curl -s -o /dev/null -w '%{http_code}' --max-time 20 -H "X-Auth-Token: $TOKEN" "$URL/v1/vault-version")"
    [[ "$CODE" == "200" ]] && ok "Vault Core reachable and token accepted (HTTP 200)" \
      || warn "Vault Core check returned HTTP $CODE (401 = bad token, 000 = unreachable, check VPN)"
  else
    warn "$CONFIG still has placeholder values: set core_api_url and the service account token"
  fi
  [[ -n "$INC_ENVIRONMENT_CONFIG_PATH" && -n "$INC_ENVIRONMENT_NAME" ]] \
    && ok "INC_ENVIRONMENT_CONFIG_PATH and INC_ENVIRONMENT_NAME exported" \
    || warn "Before running simulation tests: export INC_ENVIRONMENT_CONFIG_PATH=environment.json INC_ENVIRONMENT_NAME=sandbox"
else
  warn "No $CONFIG: cp environment.json.example environment.json and fill it in"
fi

# 6. AI coding assistant
for cli in claude gemini kiro codex; do
  command -v "$cli" >/dev/null 2>&1 && { ok "AI CLI detected: $cli"; FOUND_AI=1; break; }
done
[[ -z "$FOUND_AI" ]] && warn "No AI CLI found on PATH (claude, gemini, kiro, codex)"

echo "==================================="
if [[ $FAILED -eq 0 ]]; then
  echo "All checks passed: you are ready."
else
  echo "Fix the ❌ lines above. If you already have that piece set up another way, skip it."
fi
