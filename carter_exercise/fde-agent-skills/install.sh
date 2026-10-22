#!/usr/bin/env bash
# Install the FDE agent skills at user scope by symlinking each skill into
# the discovery directories of every supported AI coding tool found on this
# machine. Safe to re-run; existing links are refreshed.
#
# Usage:
#   ./install.sh            # install for all detected tools
#   ./install.sh --uninstall
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILLS_DIR="$REPO_DIR/skills"
UNINSTALL=false
[[ "${1:-}" == "--uninstall" ]] && UNINSTALL=true

if [[ "$(uname -s)" != "Darwin" && "$(uname -s)" != "Linux" ]]; then
  echo "ERROR: this installer supports macOS and Linux only." >&2
  echo "On Windows, use WSL or copy skills/ into each tool's skills directory manually." >&2
  exit 1
fi

# Target user-scope skill directories per tool:
#   ~/.agents/skills  - Codex and Gemini CLI (shared open-standard path)
#   ~/.claude/skills  - Claude Code
#   ~/.kiro/skills    - Kiro
TARGETS=(
  "$HOME/.agents/skills"
  "$HOME/.claude/skills"
  "$HOME/.kiro/skills"
)

for target in "${TARGETS[@]}"; do
  mkdir -p "$target"
  for skill in "$SKILLS_DIR"/*/; do
    name="$(basename "$skill")"
    link="$target/$name"
    if $UNINSTALL; then
      if [[ -L "$link" ]]; then
        rm "$link"
        echo "removed  $link"
      fi
    else
      ln -sfn "${skill%/}" "$link"
      echo "linked   $link -> ${skill%/}"
    fi
  done
done

if $UNINSTALL; then
  echo "Done. Skills unlinked."
else
  cat <<'EOF'
Done. Skills installed at user scope for Claude Code, Codex, Gemini CLI, and Kiro.

Notes:
- Skills resolve shared documentation via ../common-references, which works
  because every skill (including common-references) is linked side by side.
- Gemini CLI users can alternatively install this repo as an extension:
    gemini extensions install <repo-url>
- To remove: ./install.sh --uninstall
EOF
fi
