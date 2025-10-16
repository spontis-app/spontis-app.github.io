#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

echo ">> Running primary scraper"
python -m scraper.run

echo ">> Running auto scraper"
python "${ROOT_DIR}/auto_scraper.py"

echo ">> Running targeted tests"
python -m pytest tests/sources/test_scrapers.py -k 'festspillene or kino'
