from datetime import datetime, timedelta
import json
from pathlib import Path

from normalize import TZ
from sources import bergen_kino, resident_advisor

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "events.json"

def _dedupe_keep_latest(items):
    seen = set()
    out = []
    for e in items:
        key = (e["title"], e["when"], e["where"])
        if key in seen:
            continue
        seen.add(key)
        out.append(e)
    return out

def _filter_next_days(items, days=14):
    now = datetime.now(TZ)
    limit = now + timedelta(days=days)
    # our 'when' is label; we keep all for now. (Optional: attach ISO for sorting later)
    return items

def main():
    items = []
    try:
        items += bergen_kino.fetch()
    except Exception as e:
        print("Bergen Kino failed:", e)
    try:
        items += resident_advisor.fetch()
    except Exception as e:
        print("Resident Advisor failed:", e)

    items = _dedupe_keep_latest(items)
    items = _filter_next_days(items, days=14)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)
    print(f"Wrote {len(items)} events → {OUT}")

if __name__ == "__main__":
    main()
