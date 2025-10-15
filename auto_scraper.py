"""Spontis auto-scraper coordinator.

This script discovers potential new sources, scaffolds scraper modules,
and executes every known scraper (registered + generated) before writing
the merged list to ``data/events.json``.

Usage examples::

    # run discovery (prints suggestions)
    python auto_scraper.py --discover

    # scaffold a new scraper module for a URL
    python auto_scraper.py --generate https://example.com/program

    # run all scrapers and write data/events.json
    python auto_scraper.py
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import sys
from importlib import import_module
from pathlib import Path
from typing import Iterable, Iterator, Optional
from urllib.parse import urlparse

import requests

from scraper.run import (  # type: ignore
    DEFAULT_RETENTION_HOURS,
    LOGGER as SCRAPER_LOGGER,
    _dedupe,
    _filter_stale,
    _merge_related,
    _sanitize_event,
    _sort,
    _parse_now,
)
from scraper.source_registry import SOURCE_CONFIGS  # type: ignore

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
EVENTS_PATH = DATA_DIR / "events.json"
GENERATED_DIR = ROOT / "scraper" / "generated"
DISCOVERY_FILE = ROOT / "docs" / "discovery" / "candidates.json"

LOGGER = logging.getLogger("spontis.auto_scraper")
LOGGER.setLevel(logging.INFO)


def discover_sources(city: str = "Bergen", limit: int = 20) -> list[dict]:
    """Return a list of candidate sources for the given city.

    The discovery routine prefers the curated ``candidates.json`` file, and
    falls back to a lightweight web search. All network requests are wrapped
    in try/except so the script never crashes offline.
    """

    candidates: list[dict] = []

    if DISCOVERY_FILE.exists():
        try:
            with DISCOVERY_FILE.open("r", encoding="utf-8") as handle:
                payload = json.load(handle)
                if isinstance(payload, list):
                    candidates.extend(payload)
        except Exception as exc:
            LOGGER.warning("Failed to read %s: %s", DISCOVERY_FILE, exc)

    if len(candidates) >= limit:
        return candidates[:limit]

    # Lightweight web discovery via VisitBergen (if available).
    search_url = "https://www.visitbergen.com/whats-on/"
    try:
        response = requests.get(search_url, timeout=10)
        response.raise_for_status()
        for match in re.findall(r'href="([^"]+)"', response.text):
            if city.lower() not in match.lower():
                continue
            parsed = urlparse(match)
            if not parsed.netloc:
                continue
            cleaned = f"{parsed.scheme or 'https'}://{parsed.netloc}{parsed.path}"
            if any(cleaned == entry.get("url") for entry in candidates):
                continue
            candidates.append(
                {
                    "name": parsed.netloc,
                    "url": cleaned,
                    "source": "visitbergen",
                    "status": "new",
                }
            )
            if len(candidates) >= limit:
                break
    except Exception as exc:
        LOGGER.info("VisitBergen discovery failed (%s)", exc)

    return candidates[:limit]


SCRAPER_TEMPLATE = """\"\"\"Auto-generated scraper placeholder for {name}.\"\"\"\n\nfrom __future__ import annotations\n\nfrom bs4 import BeautifulSoup\nimport requests\n\nfrom scraper.normalize import build_event\n\nURL = {url!r}\nHEADERS = {{\"User-Agent\": \"SpontisAutoScraper/0.1\"}}\n\n\ndef fetch() -> list[dict]:\n    \"\"\"Fetch events for {name}.\n\n    This module is a scaffold – fill in selectors and mapping before enabling.\n    \"\"\"\n    try:\n        resp = requests.get(URL, headers=HEADERS, timeout=20)\n        resp.raise_for_status()\n    except Exception as exc:\n        raise RuntimeError(f\"Failed to fetch {{URL}}: {{exc}}\").with_traceback(exc.__traceback__)\n\n    soup = BeautifulSoup(resp.text, \"html.parser\")\n    events: list[dict] = []\n\n    for card in soup.select(\"REPLACE_WITH_SELECTOR\"):\n        title = card.get_text(\" \", strip=True)\n        if not title:\n            continue\n        events.append(\n            build_event(\n                source={source_name!r},\n                title=title,\n                url=URL,\n            )\n        )\n\n    return events\n"""


def _slugify(url: str) -> str:
    parsed = urlparse(url)
    raw = f"{parsed.netloc}{parsed.path}"
    slug = re.sub(r"[^a-z0-9]+", "-", raw.lower())
    return slug.strip("-") or "generated-source"


def generate_scraper(url: str, source_name: Optional[str] = None) -> Path:
    """Create a scaffold scraper file under ``scraper/generated``."""

    GENERATED_DIR.mkdir(parents=True, exist_ok=True)
    (GENERATED_DIR / "__init__.py").touch(exist_ok=True)

    slug = _slugify(url)
    path = GENERATED_DIR / f"{slug}.py"
    if path.exists():
        LOGGER.info("Scraper %s already exists", path)
        return path

    name = source_name or slug.replace("-", " ").title()
    template = SCRAPER_TEMPLATE.format(name=name, url=url, source_name=name)
    path.write_text(template, encoding="utf-8")
    LOGGER.info("Generated scraper scaffold at %s", path)
    return path


def _load_registered_fetchers() -> Iterator[tuple[str, callable]]:
    env = os.environ
    for config in SOURCE_CONFIGS:
        if not config.is_enabled(env):
            continue
        try:
            fetcher = config.resolve()
        except Exception as exc:
            LOGGER.warning("Unable to import %s: %s", config.name, exc)
            continue
        yield config.name, fetcher


def _load_generated_fetchers() -> Iterator[tuple[str, callable]]:
    if not GENERATED_DIR.exists():
        return iter(())

    sys.path.insert(0, str(ROOT))
    package = "scraper.generated"
    for file in sorted(GENERATED_DIR.glob("*.py")):
        module_name = f"{package}.{file.stem}"
        try:
            module = import_module(module_name)
            fetcher = getattr(module, "fetch", None)
            if callable(fetcher):
                yield file.stem.replace("-", " ").title(), fetcher
        except Exception as exc:
            LOGGER.warning("Failed to load generated scraper %s: %s", module_name, exc)
    sys.path.pop(0)


def _collect(fetchers: Iterable[tuple[str, callable]]) -> list[dict]:
    events: list[dict] = []
    for name, fetch in fetchers:
        LOGGER.info("Fetching %s", name)
        try:
            pulled = list(fetch())
        except Exception as exc:
            LOGGER.warning("%s failed: %s", name, exc)
            continue
        LOGGER.info("%s: %d events", name, len(pulled))
        events.extend(pulled)
    return events


def run_all_scrapers(output: Path = EVENTS_PATH, retention_hours: int = DEFAULT_RETENTION_HOURS) -> None:
    """Run every scraper (static + generated) and write the merged feed."""

    raw_events = _collect(_load_registered_fetchers())
    raw_events.extend(_collect(_load_generated_fetchers()))

    validated: list[dict] = []
    for idx, event in enumerate(raw_events, start=1):
        cleaned = _sanitize_event(event, idx)
        if cleaned is not None:
            validated.append(cleaned)

    now = _parse_now(None)
    deduped = _dedupe(validated)
    merged, _ = _merge_related(deduped)
    filtered = _filter_stale(merged, now=now, retention_hours=retention_hours)
    sorted_events = _sort(filtered)

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(sorted_events, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    LOGGER.info("Wrote %d events → %s", len(sorted_events), output)

    # Update derived views via existing build script.
    # Regenerate derived views by invoking the existing script.
    import subprocess

    subprocess.run([sys.executable, str(ROOT / "scripts" / "build_views.py")], check=True)


def parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--discover", action="store_true", help="Print discovered sources and exit.")
    parser.add_argument("--generate", help="Generate scraper scaffold for the given URL.")
    parser.add_argument("--name", help="Human friendly name for generated scraper.")
    parser.add_argument("--output", type=Path, default=EVENTS_PATH, help="Destination for events.json.")
    parser.add_argument("--retention-hours", type=int, default=DEFAULT_RETENTION_HOURS)
    parser.add_argument("--city", default="Bergen")
    parser.add_argument("--limit", type=int, default=20)
    return parser.parse_args(argv)


def main(argv: Optional[list[str]] = None) -> None:
    args = parse_args(argv)

    if args.discover:
        suggestions = discover_sources(city=args.city, limit=args.limit)
        print(json.dumps(suggestions, indent=2, ensure_ascii=False))
        return

    if args.generate:
        generate_scraper(args.generate, source_name=args.name)
        return

    LOGGER.info("Running all scrapers")
    run_all_scrapers(output=args.output, retention_hours=args.retention_hours)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )
    main()
