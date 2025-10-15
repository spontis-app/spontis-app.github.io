#!/usr/bin/env python3
"""Derive time-based views and weekly heatmap from events data."""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, time, timedelta
from pathlib import Path
from typing import Iterable, Optional
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Europe/Oslo")
WINDOW = timedelta(hours=6)
WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


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
                starts_at = None

        if starts_at is not None:
            if starts_at.tzinfo is None:
                starts_at = starts_at.replace(tzinfo=TZ)
            starts_at = starts_at.astimezone(TZ)

        return cls(raw=raw, starts_at=starts_at)


def load_events(path: Path) -> list[Event]:
    data = json.loads(path.read_text(encoding="utf-8"))
    events: list[Event] = []
    for raw in data:
        event = Event.from_raw(raw)
        events.append(event)
    return events


def build_today(events: Iterable[Event], now: datetime) -> list[dict]:
    window_start = now - WINDOW
    window_end = now + WINDOW
    filtered = [
        e for e in events
        if e.starts_at is not None
        and window_start <= e.starts_at <= window_end
    ]
    filtered.sort(key=lambda e: e.starts_at)
    return [e.raw for e in filtered]


def evening_start(now: datetime) -> datetime:
    """Return the start of the "tonight" window.

    The evening starts at 18:00 local time. If it is already past midnight but
    before 04:00 we still want to refer to the previous evening.
    """

    today_evening = now.replace(hour=18, minute=0, second=0, microsecond=0)

    if now.time() >= time(18, 0):
        return now

    if now.time() < time(4, 0):
        # Treat the very early hours as a continuation of the previous evening
        previous_day = (now - timedelta(days=1)).replace(
            hour=18, minute=0, second=0, microsecond=0
        )
        return previous_day

    return today_evening


def build_tonight(events: Iterable[Event], now: datetime) -> list[dict]:
    start = evening_start(now)
    end = start + WINDOW
    filtered = [
        e for e in events
        if e.starts_at is not None and start <= e.starts_at <= end
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
    path.parent.mkdir(parents=True, exist_ok=True)
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


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--events",
        help="Path to events.json (defaults to data/events.json)",
    )
    parser.add_argument(
        "--now",
        help="ISO formatted datetime override used for generating the views",
    )
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parent.parent
    default_events = repo_root / "data" / "events.json"
    events_path = Path(args.events).expanduser().resolve() if args.events else default_events
    data_dir = repo_root / "data"
    generated_dir = data_dir / "generated"

    events = load_events(events_path)
    now = parse_now(args.now)

    today = build_today(events, now)
    tonight = build_tonight(events, now)
    heatmap = build_heatmap(events)

    write_json(generated_dir / "today.json", today)
    write_json(generated_dir / "tonight.json", tonight)
    write_json(generated_dir / "heatmap.json", heatmap)


if __name__ == "__main__":
    main()
