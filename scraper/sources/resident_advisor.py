from datetime import datetime
import requests
from bs4 import BeautifulSoup
import dateparser
from scraper.normalize import event, TZ  # <-- absolute

HEADERS = {"User-Agent":"SpontisBot/0.1 (+https://spontis-app.github.io)","Accept-Language":"en,nb;q=0.7"}
BASE = "https://ra.co"
CITY_URL = f"{BASE}/events/no/bergen"

def fetch() -> list[dict]:
    r = requests.get(CITY_URL, headers=HEADERS, timeout=20)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")

    items = []
    for a in soup.select("a[href^='/events/']"):
        title = a.get_text(" ", strip=True)
        if not title: 
            continue
        url = BASE + a.get("href")
        block = a.find_parent()
        text = block.get_text(" ", strip=True) if block else title

        dt = dateparser.parse(text, settings={"TIMEZONE":"Europe/Oslo"})
        if not dt:
            continue

        where = "Bergen"
        for sep in ("—","-","•","|"):
            if sep in text:
                where = text.split(sep)[-1].strip()
                break

        items.append(event(title=title, dt=dt, where=where, tags=["rave"], url=url))
    return items
