import types

import pytest

from scraper.sources import (
    bergen_kjott,
    bergen_kunsthall,
    bergen_philharmonic,
    den_nationale_scene,
    grieghallen,
)


class FakeResponse:
    def __init__(self, text: str, status: int = 200, encoding: str = "utf-8") -> None:
        self.text = text
        self.status_code = status
        self.encoding = encoding
        self.apparent_encoding = encoding

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


@pytest.mark.parametrize(
    "html,detail_url,detail_html,expected_titles",
    [
        (
            """
            <div>
              <a href="/en/events/3184-2025-10-07/">Conversation VOLT: Filipa Ramos Tue 7 Oct 19:00, Landmark</a>
              <a href="/en/visit-us/">Visit Us</a>
              <a href="/en/become-a-member/">Become a member</a>
            </div>
            """,
            "https://www.kunsthall.no/en/events/3184-2025-10-07/",
            """
            <div class="event">
              <time datetime="2025-10-07T19:00">7 Oct 19:00</time>
            </div>
            """,
            ["Conversation VOLT: Filipa Ramos Tue 7 Oct 19:00, Landmark"],
        ),
    ],
)
def test_kunsthall_filters_navigation(monkeypatch, html, detail_url, detail_html, expected_titles):
    def fake_http_get(url: str, **_kwargs):
        if url.endswith('/events/') or url.endswith('/whats-on/'):
            return FakeResponse(html)
        if url == detail_url:
            return FakeResponse(detail_html)
        return FakeResponse("", status=404)

    monkeypatch.setattr(bergen_kunsthall, 'http_get', fake_http_get)

    events = bergen_kunsthall.fetch()
    titles = [event['title'] for event in events]
    assert titles == expected_titles
    assert all('/events/' in event['url'] for event in events)


def test_bergen_kjott_filters_static_pages(monkeypatch):
    listing_html = """
    <ul>
      <li><a href="/events/performance-lab">Performance Lab</a></li>
      <li><a href="/kontakt">Kontakt + Tilgjengelighet</a></li>
      <li><a href="/program/opplaering">Opplæring</a></li>
    </ul>
    """
    detail_html = """
    <article>
      <time datetime="2025-05-24T20:00">24.05.2025 20:00</time>
    </article>
    """

    def fake_http_get(url: str, **_kwargs):
        if url == bergen_kjott.PROGRAM_URL:
            return FakeResponse(listing_html)
        if url.endswith('/events/performance-lab'):
            return FakeResponse(detail_html)
        return FakeResponse("", status=404)

    monkeypatch.setattr(bergen_kjott, 'http_get', fake_http_get)

    events = bergen_kjott.fetch()
    assert [event['title'] for event in events] == ['Performance Lab']


def test_grieghallen_filters_navigation(monkeypatch):
    listing_html = """
    <div>
      <a href="/arrangement/konsert-1">
        <time datetime="2025-06-01T19:30">1. juni 19:30</time>
        Konsert 1
      </a>
      <a href="/arrangement/abonnement">Abonnement</a>
    </div>
    """
    detail_html = """
    <div>
      <time datetime="2025-06-01T19:30"></time>
    </div>
    """

    def fake_get(url: str, **_kwargs):
        if url == grieghallen.PROGRAM_URL:
            return FakeResponse(listing_html)
        if url.endswith('/arrangement/konsert-1'):
            return FakeResponse(detail_html)
        return FakeResponse("", status=404)

    monkeypatch.setattr(grieghallen, 'requests', types.SimpleNamespace(get=lambda url, **_: fake_get(url)))

    events = grieghallen.fetch()
    assert [event['title'] for event in events] == ['Konsert 1']


def test_bergen_philharmonic_filters_navigation(monkeypatch):
    listing_html = """
    <section>
      <article>
        <a href="/program/mahler-2">
          <time datetime="2025-09-10T19:30">10.09 19:30</time>
          Mahler 2
        </a>
      </article>
      <article>
        <a href="/program/abonnement">Abonnement</a>
      </article>
    </section>
    """
    detail_html = """
    <div>
      <time datetime="2025-09-10T19:30"></time>
    </div>
    """

    def fake_get(url: str, **_kwargs):
        if url == bergen_philharmonic.PROGRAM_URL:
            return FakeResponse(listing_html)
        if url.endswith('/program/mahler-2'):
            return FakeResponse(detail_html)
        return FakeResponse("", status=404)

    monkeypatch.setattr(bergen_philharmonic, 'requests', types.SimpleNamespace(get=lambda url, **_: fake_get(url)))

    events = bergen_philharmonic.fetch()
    assert [event['title'] for event in events] == ['Mahler 2']


def test_dns_filters_navigation(monkeypatch):
    listing_html = """
    <div>
      <a href="/forestillinger/dronningen">Dronningen</a>
      <a href="/forestillinger/annet">Annet</a>
    </div>
    """
    detail_html = """
    <div>
      <time datetime="2025-11-02T19:00"></time>
    </div>
    """

    def fake_get(url: str, **_kwargs):
        if url == den_nationale_scene.PROGRAM_URL:
            return FakeResponse(listing_html)
        if url.endswith('/forestillinger/dronningen'):
            return FakeResponse(detail_html)
        return FakeResponse("", status=404)

    monkeypatch.setattr(den_nationale_scene, 'requests', types.SimpleNamespace(get=lambda url, **_: fake_get(url)))

    events = den_nationale_scene.fetch()
    assert [event['title'] for event in events] == ['Dronningen']
