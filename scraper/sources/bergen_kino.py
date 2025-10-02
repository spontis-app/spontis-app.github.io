import re
from datetime import datetime
import requests
from bs4 import BeautifulSoup
import dateparser
from scraper.normalize import event, TZ  # <-- absolute

HEADERS = {
    "User-Agent": "SpontisBot/0.1 (+https://spontis-app.github.io)",
    "Accept-Language": "nb,en;q=0.8"
}

BASE = "https://www.bergenkino.no"
PROGRAM_URL = f"{BASE}/program"

def fetch() -> list[dict]:
    r = requests.get(PROGRAM_URL, headers=HEADERS, timeout=20)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")

    items = []
    for card in soup.select("a[href*='/film/'], a.card, a.block"):
        title = card.get_text(" ", strip=True)
        href = card.get("href") or ""
        if not title or "/film/" not in href:
            continue
        url = href if href.startswith("http") else BASE + href
        text = card.get_text(" ", strip=True)
        times = re.findall(r"\b([01]?\d|2[0-3]):[0-5]\d\b", text)

        the_date = dateparser.parse("today", languages=["nb"], settings={"TIMEZONE":"Europe/Oslo"})
        for t in times[:6]:
            dt = dateparser.parse(f"{the_date:%Y-%m-%d} {t}", settings={"TIMEZONE":"Europe/Oslo"})
            if not dt:
                continue
            items.append(event(
                title=title,
                dt=dt,
                where="Bergen Kino",
                tags=["cinema","date"],
                url=url
            ))
    return items
