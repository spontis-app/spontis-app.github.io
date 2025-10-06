from datetime import datetime

import dateparser
from bs4 import BeautifulSoup

from scraper.normalize import TZ, build_event, to_weekday_label
from scraper.http import get as http_get

HEADERS = {"User-Agent":"SpontisBot/0.1 (+https://spontis-app.github.io)","Accept-Language":"en,nb;q=0.7"}
BASE = "https://ra.co"
CITY_URL = f"{BASE}/events/no/bergen"

def fetch() -> list[dict]:
    r = http_get(CITY_URL, headers=HEADERS, timeout=20)
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

        extra = {"where": where}
        label = to_weekday_label(dt)
        if label:
            extra["when"] = label

        items.append(
            build_event(
                source="Resident Advisor",
                title=title,
                url=url,
                starts_at=dt,
                venue=where,
                tags=["rave"],
                extra=extra,
            )
        )
    return items
