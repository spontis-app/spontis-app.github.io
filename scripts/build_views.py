#!/usr/bin/env python3
"""Derive time-based views and weekly heatmap from events data."""
from __future__ import annotations

import argparse
import json
import logging
from dataclasses import dataclass
from datetime import datetime, time, timedelta
from pathlib import Path
from typing import Iterable, Optional, Sequence
from zoneinfo import ZoneInfo

LOG_FORMAT = "%(asctime)s [%(levelname)s] %(message)s"
TZ = ZoneInfo("Europe/Oslo")
WINDOW = timedelta(hours=6)
WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


logger = logging.getLogger("spontis.build_views")


@dataclass
class Event:
    raw: dict
    starts_at: datetime | None

    @classmethod
    def from_raw(cls, raw: dict) -> "Event":
        starts_at = None
        value = raw.get("starts_at")
        if isinstance(value, str):
            try:
                starts_at = datetime.fromisoformat(value)
            except ValueError:
                logger.debug("Invalid starts_at on event %s", raw.get("title"))
                starts_at = None

        if starts_at is not None:
            if starts_at.tzinfo is None:
                starts_at = starts_at.replace(tzinfo=TZ)
            starts_at = starts_at.astimezone(TZ)

        return cls(raw=raw, starts_at=starts_at)


def configure_logging(level: str) -> None:
    logging.basicConfig(level=level, format=LOG_FORMAT)


def load_events(path: Path) -> list[Event]:
    if not path.exists():
        logger.warning("No events file at %s, producing empty outputs", path)
        return []

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid JSON in {path}: {exc}") from exc

    events: list[Event] = []
    for raw in data:
        events.append(Event.from_raw(raw))
    return events


def build_today(events: Iterable[Event], now: datetime) -> list[dict]:
    window_start = now - WINDOW
    window_end = now + WINDOW
    filtered = [
        e
        for e in events
        if e.starts_at is not None and window_start <= e.starts_at <= window_end
    ]
    filtered.sort(key=lambda e: e.starts_at)
    return [e.raw for e in filtered]


def evening_start(now: datetime) -> datetime:
    """Return the start of the "tonight" window."""

    today_evening = now.replace(hour=18, minute=0, second=0, microsecond=0)

    if now.time() >= time(18, 0):
        return now

    if now.time() < time(4, 0):
        previous_day = (now - timedelta(days=1)).replace(
            hour=18, minute=0, second=0, microsecond=0
        )
        return previous_day

    return today_evening


def build_tonight(events: Iterable[Event], now: datetime) -> list[dict]:
    start = evening_start(now)
    end = start + WINDOW
    filtered = [
        e for e in events if e.starts_at is not None and start <= e.starts_at <= end
    ]

    filtered.sort(key=lambda e: e.starts_at)
    return [e.raw for e in filtered]


def build_heatmap(events: Iterable[Event]) -> dict[str, int]:
    counts = {day: 0 for day in WEEKDAYS}
    for event in events:
        if event.starts_at is None:
            continue
        counts[WEEKDAYS[event.starts_at.weekday()]] += 1
    return counts


def write_json(path: Path, payload) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def parse_now(value: Optional[str]) -> datetime:
    if not value:
        return datetime.now(TZ)

    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise SystemExit(f"Invalid --now value: {value}") from exc

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=TZ)
    return parsed.astimezone(TZ)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--events",
        default=str(Path(__file__).resolve().parent.parent / "data" / "events.json"),
        help="Path to events.json (default: %(default)s)",
    )
    parser.add_argument(
        "--out-dir",
        default=str(Path(__file__).resolve().parent.parent / "data"),
        help="Directory where derived JSON files are written (default: %(default)s)",
    )
    parser.add_argument(
        "--now",
        help="ISO formatted datetime override used for generating the views",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        help="Logging level (default: %(default)s)",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    configure_logging(args.log_level.upper())

    events_path = Path(args.events)
    out_dir = Path(args.out_dir)
    now = parse_now(args.now)

    events = load_events(events_path)
    logger.info("Loaded %d events from %s", len(events), events_path)

    today = build_today(events, now)
    tonight = build_tonight(events, now)
    heatmap = build_heatmap(events)

    out_dir.mkdir(parents=True, exist_ok=True)
    write_json(out_dir / "today.json", today)
    write_json(out_dir / "tonight.json", tonight)
    write_json(out_dir / "heatmap.json", heatmap)

    logger.info("today.json → %d events", len(today))
    logger.info("tonight.json → %d events", len(tonight))
    logger.info("heatmap.json updated")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

