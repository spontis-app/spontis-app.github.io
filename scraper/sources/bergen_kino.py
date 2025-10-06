# scraper/sources/bergen_kino.py
import re
from collections import defaultdict
from datetime import datetime
from urllib.parse import urljoin

import dateparser
from bs4 import BeautifulSoup
from requests import HTTPError

from scraper.http import get as http_get
from scraper.normalize import build_event, format_showtimes

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0 Safari/537.36 SpontisBot/0.1",
    "Accept-Language": "nb,en;q=0.8"
}

BASE = "https://www.bergenkino.no"
CANDIDATES = [
    "/program",
    "/kino/program",
    "/kinoprogram",
    "/film/program",
    "/filmer",           # prøver noen fornuftige varianter
    "/",
]

TIME_RX = re.compile(r"\b([01]?\d|2[0-3]):[0-5]\d\b")

def _get(url):
    return http_get(url, headers=HEADERS)

def _discover_program_url():
    # prøv kandidatstier
    for path in CANDIDATES:
        url = urljoin(BASE, path)
        try:
            r = _get(url)
        except HTTPError:
            continue
        # hvis siden inneholder tider, er vi sannsynligvis på riktig “program”-side
        if TIME_RX.search(r.text):
            return url, r.text
        # ellers: se om det finnes lenker som peker til noe med "program/kinoprogram"
        soup = BeautifulSoup(r.text, "html.parser")
        for a in soup.select("a[href]"):
            href = a.get("href") or ""
            label = (a.get_text() or "").lower()
            if any(k in href for k in ("/program", "kinoprogram")) or "program" in label:
                pu = urljoin(BASE, href)
                try:
                    r2 = _get(pu)
                    if TIME_RX.search(r2.text):
                        return pu, r2.text
                except HTTPError:
                    pass
    # siste utvei: bruk forsiden
    r = _get(BASE + "/")
    return BASE + "/", r.text

def _infer_tags(title: str) -> list[str]:
    base = {"cinema", "date"}
    lower = title.lower()
    if any(word in lower for word in ("barn", "familie", "kids", "junior")):
        base.add("family")
    if any(word in lower for word in ("premiere", "festival")):
        base.add("culture")
    if any(word in lower for word in ("horror", "skrekk", "thriller")):
        base.add("late-night")
    return sorted(base)


def fetch() -> list[dict]:
    url, html = _discover_program_url()
    soup = BeautifulSoup(html, "html.parser")
    grouped: dict[tuple[str, str], set[datetime]] = defaultdict(set)

    # grep filmkort som lenker til detaljer
    for card in soup.select("a[href*='/film/'], a[href*='/kino/']"):
        title = card.get_text(" ", strip=True)
        href = card.get("href") or ""
        if not title or "/film/" not in href:
            continue
        film_url = urljoin(BASE, href)
        text = card.get_text(" ", strip=True)
        times = TIME_RX.findall(text)

        the_date = dateparser.parse("today", languages=["nb"], settings={"TIMEZONE": "Europe/Oslo"})
        if not the_date:
            continue

        for t in times[:6]:
            dt = dateparser.parse(f"{the_date:%Y-%m-%d} {t}", settings={"TIMEZONE": "Europe/Oslo"})
            if not dt:
                continue
            grouped[(title, film_url)].add(dt)

    # ekstrem fallback: plukk tider hvor som helst på siden
    if not grouped:
        for m in TIME_RX.finditer(soup.get_text(" ", strip=True)):
            t = m.group(0)
            dt = dateparser.parse(f"today {t}", settings={"TIMEZONE":"Europe/Oslo"})
            if dt:
                grouped[("Kinovisning", url)].add(dt)

    items: list[dict] = []
    for (title, film_url), times in grouped.items():
        ordered = sorted(times)
        starts_at = ordered[0] if ordered else None
        label = format_showtimes(ordered)
        extra = {"where": "Bergen Kino"}
        if label:
            extra["when"] = label

        items.append(
            build_event(
                source="Bergen Kino",
                title=title,
                url=film_url,
                starts_at=starts_at,
                venue="Bergen Kino",
                tags=_infer_tags(title),
                extra=extra,
            )
        )

    return items
