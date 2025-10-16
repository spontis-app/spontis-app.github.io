#!/usr/bin/env python3
"""Summarise discovery pipeline status and scraper metadata."""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = REPO_ROOT / "data"
DOCS_DIR = REPO_ROOT / "docs"

META_PATH = DATA_DIR / "generated" / "meta.json"
CANDIDATES_PATH = DOCS_DIR / "discovery" / "candidates.json"


def _load_json(path: Path) -> Any:
    if not path.exists():
        return None
    raw = path.read_text(encoding="utf-8")
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


def build_report() -> Dict[str, Any]:
    report: Dict[str, Any] = {}

    meta = _load_json(META_PATH) or {}
    report["events"] = {
        "last_updated": meta.get("last_updated"),
        "total_events": meta.get("total_events", 0),
        "source_count": meta.get("source_count", 0),
    }

    stats = meta.get("source_stats") or []
    failures = meta.get("source_failures") or []

    grouped: Dict[str, list[Dict[str, Any]]] = defaultdict(list)
    for entry in stats:
        status = entry.get("status") or "unknown"
        grouped[status].append(entry)

    failing = []
    inactive = []
    for entry in stats:
        status = str(entry.get("status", "")).lower()
        if status in {"error", "fallback", "offline"}:
            failing.append({
                "name": entry.get("name"),
                "status": status,
                "events": entry.get("events", 0),
            })
        elif (entry.get("events") or 0) == 0:
            inactive.append({
                "name": entry.get("name"),
                "status": status or "inactive",
            })

    report["sources"] = {
        "ok": len(grouped.get("ok", [])),
        "error": len(grouped.get("error", [])),
        "fallback": len(grouped.get("fallback", [])),
        "offline": len(grouped.get("offline", [])),
        "total": len(stats),
        "failing": failing,
        "inactive": inactive,
    }
    if failures:
        report["failures"] = failures

    candidates = _load_json(CANDIDATES_PATH) or []
    status_counts = Counter()
    source_counts = Counter()
    for entry in candidates:
        status_counts[entry.get("status", "unknown")] += 1
        source_counts[entry.get("source", "unknown")] += 1
    report["candidates"] = {
        "total": len(candidates),
        "by_status": dict(status_counts),
        "by_source": dict(source_counts),
        "entries": candidates,
    }

    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    payload = build_report()
    if args.json:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return

    events = payload["events"]
    print("== Events ==")
    print(f"Last updated: {events.get('last_updated') or 'n/a'}")
    print(f"Total events: {events.get('total_events', 0)} (from {events.get('source_count', 0)} sources)")

    sources = payload["sources"]
    print("\n== Sources ==")
    print(
        f"OK:{sources.get('ok', 0)}  Error:{sources.get('error', 0)}  "
        f"Fallback:{sources.get('fallback', 0)}  Offline:{sources.get('offline', 0)}"
    )
    if payload.get("failures"):
        print("Failures:")
        for failure in payload["failures"]:
            name = failure.get("name", "Unknown")
            error = failure.get("error", "").strip()
            print(f" - {name}: {error}")

    candidates = payload["candidates"]
    print("\n== Discovery Candidates ==")
    print(f"Total candidates: {candidates.get('total', 0)}")
    if candidates.get("by_status"):
        print("By status:")
        for status, count in sorted(candidates["by_status"].items()):
            print(f" - {status}: {count}")
    if candidates.get("by_source"):
        print("By source:")
        for source, count in sorted(candidates["by_source"].items()):
            print(f" - {source}: {count}")


if __name__ == "__main__":
    main()
