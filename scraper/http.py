"""HTTP helpers with retry-aware sessions for the SPONTIS scraper."""
from __future__ import annotations

import os
from functools import lru_cache
from typing import Any, Mapping, MutableMapping, Optional

import requests
from requests import Response
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

DEFAULT_TIMEOUT = float(os.getenv("SPONTIS_HTTP_TIMEOUT", "25"))


def _default_headers() -> dict[str, str]:
    headers: dict[str, str] = {
        "User-Agent": os.getenv(
            "SPONTIS_HTTP_USER_AGENT",
            "SpontisBot/1.1 (+https://spontis-app.github.io)",
        ),
        "Accept-Language": os.getenv("SPONTIS_HTTP_LANG", "nb,en;q=0.8"),
    }
    return headers


def _build_retry() -> Retry:
    return Retry(
        total=int(os.getenv("SPONTIS_HTTP_RETRIES", "3")),
        connect=int(os.getenv("SPONTIS_HTTP_RETRIES", "3")),
        read=int(os.getenv("SPONTIS_HTTP_RETRIES", "3")),
        backoff_factor=float(os.getenv("SPONTIS_HTTP_BACKOFF", "0.6")),
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=("GET", "HEAD", "OPTIONS"),
        raise_on_status=False,
    )


@lru_cache(maxsize=1)
def get_session() -> requests.Session:
    session = requests.Session()
    retry = _build_retry()
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    session.headers.update(_default_headers())
    return session


def get(
    url: str,
    *,
    timeout: Optional[float] = None,
    headers: Optional[Mapping[str, str]] = None,
    **kwargs: Any,
) -> Response:
    session = get_session()
    request_headers: MutableMapping[str, str]
    if headers:
        request_headers = session.headers.copy()
        request_headers.update(headers)
    else:
        request_headers = session.headers
    response = session.get(url, timeout=timeout or DEFAULT_TIMEOUT, headers=request_headers, **kwargs)
    response.raise_for_status()
    return response

