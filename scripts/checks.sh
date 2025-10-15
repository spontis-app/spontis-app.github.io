#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP_EVENTS="$(mktemp "${TMPDIR:-/tmp}/spontis-events.XXXXXX.json")"
trap 'rm -f "$TMP_EVENTS"' EXIT

echo ">> Running scraper in offline mode"
python -m scraper.run --offline --no-update-views --output "$TMP_EVENTS"

echo ">> Refreshing derived views"
python "${ROOT_DIR}/scripts/build_views.py" --events "$TMP_EVENTS"

if python -c "import importlib; importlib.import_module('pytest')" >/dev/null 2>&1; then
    echo ">> Running pytest"
    python -m pytest
else
    echo ">> pytest not installed, skipping tests" >&2
fi
