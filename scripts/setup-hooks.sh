#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HOOK_SOURCE="$ROOT_DIR/scripts/git-hooks/post-commit"
HOOK_TARGET="$ROOT_DIR/.git/hooks/post-commit"

if [[ ! -f "$HOOK_SOURCE" ]]; then
    echo "Hook script mangler: $HOOK_SOURCE" >&2
    exit 1
fi

chmod +x "$HOOK_SOURCE"
mkdir -p "$(dirname "$HOOK_TARGET")"
ln -sf "$HOOK_SOURCE" "$HOOK_TARGET"

echo "Lenket post-commit hook til $HOOK_TARGET"
echo "Commits med prefiks 'codex:' vil logges til docs/codex_log.md."
