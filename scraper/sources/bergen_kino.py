import re
from datetime import datetime
import requests
from bs4 import BeautifulSoup
import dateparser
from ..normalize import event, TZ

HEADERS = {
    "User-Agent": "SpontisBot/0.1 (+https://spontis-app.github.io)",
    "Accept-Language": "nb,en;q=0.8"
}

BASE = "https://www.bergenkino.no"
PROGRAM_URL = f"{BASE}/program"   # justeres hvis nødvendig

def fetch() -> list[dict]:
    """Returner liste med event-dicts fra Bergen Kino sin programside."""
    r = requests.get(PROGRAM_URL, headers=HEADERS, timeout=20)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")

    items = []

    # 1) Prøv 'kort' som typisk inneholder film + dagens tider
    # Finn alle lenker som ser ut som filmkort
    for card in soup.select("a[href*='/film/'], a.card, a.block"):
        title = card.get_text(" ", strip=True)
        href = card.get("href") or ""
        if not title or "/film/" not in href:
            continue
        url = href if href.startswith("http") else BASE + href

        # Finn tider i samme kort (mønster 12:30, 19:15 ...)
        text = card.get_text(" ", strip=True)
        times = re.findall(r"\b([01]?\d|2[0-3]):[0-5]\d\b", text)

        # Prøv å finne dato i kontekst (i dag eller fremover)
        # Fall-back: bruk "i dag" for demo (du kan utvide senere)
        the_date = dateparser.parse("today", languages=["nb"], settings={"TIMEZONE":"Europe/Oslo"})

        for t in times[:6]:  # begrens første 6 visninger per film
            dt = dateparser.parse(f"{the_date:%Y-%m-%d} {t}", settings={"TIMEZONE":"Europe/Oslo"})
            if not dt:
                continue
            dt = TZ.localize(dt) if dt.tzinfo is None else dt.astimezone(TZ)
            items.append(event(
                title=title,
                dt=dt,
                where="Bergen Kino",
                tags=["cinema","date"],
                url=url
            ))

    # 2) Hvis ingen kort ble funnet, prøv tabell/rute
    if not items:
        for row in soup.find_all(text=re.compile(r"\b(\d{1,2}:\d{2})\b")):
            try:
                t = re.search(r"(\d{1,2}:\d{2})", row).group(1)
            except Exception:
                continue
            title = row.parent.get_text(" ", strip=True)[:80]
            dt = dateparser.parse(f"today {t}", settings={"TIMEZONE":"Europe/Oslo"})
            if not dt:
                continue
            dt = TZ.localize(dt) if dt.tzinfo is None else dt.astimezone(TZ)
            items.append(event(title=title, dt=dt, where="Bergen Kino", tags=["cinema","date"], url=PROGRAM_URL))

    return items
