# scraper/sources/bergen_kino.py
import re
from datetime import datetime
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup
import dateparser
from scraper.normalize import event, TZ

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
    r = requests.get(url, headers=HEADERS, timeout=25)
    r.raise_for_status()
    return r

def _discover_program_url():
    # prøv kandidatstier
    for path in CANDIDATES:
        url = urljoin(BASE, path)
        try:
            r = _get(url)
        except requests.HTTPError:
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
                except requests.HTTPError:
                    pass
    # siste utvei: bruk forsiden
    r = _get(BASE + "/")
    return BASE + "/", r.text

def fetch() -> list[dict]:
    url, html = _discover_program_url()
    soup = BeautifulSoup(html, "html.parser")
    items = []

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
            items.append(event(
                title=title,
                dt=dt,
                where="Bergen Kino",
                tags=["cinema", "date"],
                url=film_url
            ))

    # ekstrem fallback: plukk tider hvor som helst på siden
    if not items:
        for m in TIME_RX.finditer(soup.get_text(" ", strip=True)):
            t = m.group(0)
            dt = dateparser.parse(f"today {t}", settings={"TIMEZONE":"Europe/Oslo"})
            if dt:
                items.append(event("Kinovisning", dt, "Bergen Kino", ["cinema","date"], url))

    return items
