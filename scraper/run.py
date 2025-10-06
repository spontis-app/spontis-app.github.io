# scraper/run.py
import os, json
from pathlib import Path
from scraper.normalize import TZ
from scraper.sources import bergen_kino
# importer RA kun hvis aktivert
USE_RA = os.getenv("SCRAPE_RA", "0") == "1"
if USE_RA:
    from scraper.sources import resident_advisor

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "events.json"

def _dedupe(items):
    seen, out = set(), []
    for e in items:
        key = (e["title"], e["when"], e["where"])
        if key in seen: continue
        seen.add(key); out.append(e)
    return out

def _load_existing():
    if OUT.exists():
        try:
            return json.loads(OUT.read_text(encoding="utf-8"))
        except Exception:
            return []
    return []

def main():
    items = []
    try:
        items += bergen_kino.fetch()
    except Exception as e:
        print("Bergen Kino failed:", e)

    if USE_RA:
        try:
            items += resident_advisor.fetch()
        except Exception as e:
            print("Resident Advisor failed:", e)

    items = _dedupe(items)

    if not items:
        print("No new items; keeping previous events.json")
        return  # IKKE overwrite med tom liste

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {len(items)} events → {OUT}")

if __name__ == "__main__":
    main()
