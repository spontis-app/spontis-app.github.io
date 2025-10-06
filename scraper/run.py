# scraper/run.py
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Callable, Iterable, List, Tuple

from scraper.sources import bergen_kino, ostre

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "events.json"

USE_RA = os.getenv("SCRAPE_RA", "0") == "1"
USE_OSTRE = os.getenv("SCRAPE_OSTRE", "1") != "0"
USE_USF = os.getenv("ENABLE_USF", "1") != "0"
USE_BERGEN_KJOTT = os.getenv("ENABLE_BERGEN_KJOTT", "1") != "0"
USE_KUNSTHALL = os.getenv("ENABLE_KUNSTHALL", "1") != "0"
USE_KENNEL = os.getenv("ENABLE_IG_KENNEL", "0") == "1"

if USE_RA:
    from scraper.sources import resident_advisor

if USE_USF:
    from scraper.sources import usf_verftet

if USE_BERGEN_KJOTT:
    from scraper.sources import bergen_kjott

if USE_KUNSTHALL:
    from scraper.sources import bergen_kunsthall

if USE_KENNEL:
    from scraper.sources import kennel_vinylbar


Source = Tuple[str, Callable[[], Iterable[dict]]]


def _sources() -> List[Source]:
    sources: List[Source] = [("Bergen Kino", bergen_kino.fetch)]
    if USE_OSTRE:
        sources.append(("Østre", ostre.fetch))
    if USE_USF:
        sources.append(("USF Verftet", usf_verftet.fetch))
    if USE_BERGEN_KJOTT:
        sources.append(("Bergen Kjøtt", bergen_kjott.fetch))
    if USE_KUNSTHALL:
        sources.append(("Bergen Kunsthall", bergen_kunsthall.fetch))
    if USE_RA:
        sources.append(("Resident Advisor", resident_advisor.fetch))
    if USE_KENNEL:
        sources.append(("Kennel Vinylbar", kennel_vinylbar.fetch))
    return sources


def _run_source(name: str, fetch: Callable[[], Iterable[dict]]) -> List[dict]:
    try:
        events = list(fetch())
        print(f"{name}: {len(events)} events")
        return events
    except Exception as exc:
        print(f"{name} failed: {exc}")
        return []


def _dedupe(events: Iterable[dict]) -> List[dict]:
    seen = set()
    deduped: List[dict] = []
    for event in events:
        key = (
            event.get("title"),
            event.get("starts_at"),
            event.get("url"),
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(event)
    return deduped


def _sort(events: List[dict]) -> List[dict]:
    def sort_key(ev: dict):
        starts_at = ev.get("starts_at")
        title = (ev.get("title") or "").lower()
        if starts_at:
            return (0, starts_at, title)
        return (1, title)

    return sorted(events, key=sort_key)


def main():
    collected: List[dict] = []
    for name, fetch in _sources():
        collected.extend(_run_source(name, fetch))

    events = _sort(_dedupe(collected))

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(events, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {len(events)} events → {OUT}")


if __name__ == "__main__":
    main()
