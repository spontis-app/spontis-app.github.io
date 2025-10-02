from datetime import datetime
import requests
from bs4 import BeautifulSoup
import dateparser
from ..normalize import event, TZ

HEADERS = {
    "User-Agent": "SpontisBot/0.1 (+https://spontis-app.github.io)",
    "Accept-Language": "en;q=0.8,nb;q=0.7"
}

BASE = "https://ra.co"
CITY_URL = f"{BASE}/events/no/bergen"   # RA: Bergen events

def fetch() -> list[dict]:
    r = requests.get(CITY_URL, headers=HEADERS, timeout=20)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")

    items = []
    # RA har ofte kort med <a href="/events/xxx">... og dato/venue i nærheten
    for a in soup.select("a[href^='/events/']"):
        title = a.get_text(" ", strip=True)
        if not title:
            continue
        url = BASE + a.get("href")

        # Finn dato/venue i søsken/parent
        block = a.find_parent()
        text = block.get_text(" ", strip=True) if block else title

        # Eksempel: "Fri, 23:59 — USF Verftet" eller "12 Oct 2025 23:00"
        # Vi bruker dateparser og håper på en naturlig frasering
        dt = dateparser.parse(text, settings={"TIMEZONE":"Europe/Oslo"})
        if not dt:
            continue
        dt = TZ.localize(dt) if dt.tzinfo is None else dt.astimezone(TZ)

        where = "Bergen"
        # Prøv å trekke ut venue-navn hvis finnes (etter et tankestrek/punkt)
        for sep in ("—", "-", "•", "|"):
            if sep in text:
                where = text.split(sep)[-1].strip()
                break

        items.append(event(
            title=title,
            dt=dt,
            where=where or "Bergen",
            tags=["rave"],             # du kan mappe til club/party senere
            url=url
        ))

    return items
