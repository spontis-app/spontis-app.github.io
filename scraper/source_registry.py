"""Registry of scraper sources and feature flags."""
from __future__ import annotations

from dataclasses import dataclass
from importlib import import_module
from typing import Callable, Iterable, Mapping


Fetcher = Callable[[], Iterable[dict]]


@dataclass(frozen=True)
class SourceConfig:
    name: str
    module: str
    attr: str = "fetch"
    env_flag: str | None = None
    default_enabled: bool = True

    def is_enabled(self, env: Mapping[str, str]) -> bool:
        if not self.env_flag:
            return True
        raw = env.get(self.env_flag)
        if raw is None:
            return self.default_enabled
        if self.default_enabled:
            return raw != "0"
        return raw == "1"

    def resolve(self) -> Fetcher:
        module = import_module(self.module)
        fetcher = getattr(module, self.attr, None)
        if not callable(fetcher):
            raise AttributeError(f"{self.module}.{self.attr} is not callable")
        return fetcher  # type: ignore[return-value]


SOURCE_CONFIGS: tuple[SourceConfig, ...] = (
    SourceConfig(name="Bergen Kino", module="scraper.sources.bergen_kino"),
    SourceConfig(name="Østre", module="scraper.sources.ostre", env_flag="SCRAPE_OSTRE", default_enabled=True),
    SourceConfig(name="USF Verftet", module="scraper.sources.usf_verftet", env_flag="ENABLE_USF", default_enabled=True),
    SourceConfig(name="Bergen Kjøtt", module="scraper.sources.bergen_kjott", env_flag="ENABLE_BERGEN_KJOTT", default_enabled=True),
    SourceConfig(name="Bergen Kunsthall", module="scraper.sources.bergen_kunsthall", env_flag="ENABLE_KUNSTHALL", default_enabled=True),
    SourceConfig(name="BIT Teatergarasjen", module="scraper.sources.bit_teatergarasjen", env_flag="ENABLE_BIT", default_enabled=True),
    SourceConfig(name="Litteraturhuset", module="scraper.sources.litteraturhuset", env_flag="ENABLE_LITTERATURHUSET", default_enabled=True),
    SourceConfig(name="Kulturhuset i Bergen", module="scraper.sources.kulturhuset", env_flag="ENABLE_KULTURHUSET", default_enabled=True),
    SourceConfig(name="Carte Blanche", module="scraper.sources.carte_blanche", env_flag="ENABLE_CARTE_BLANCHE", default_enabled=True),
    SourceConfig(name="Bergen Live", module="scraper.sources.bergen_live", env_flag="ENABLE_BERGEN_LIVE", default_enabled=True),
    SourceConfig(name="Nattjazz", module="scraper.sources.nattjazz", env_flag="ENABLE_NATTJAZZ", default_enabled=True),
    SourceConfig(name="Hordaland Kunstsenter", module="scraper.sources.hordaland_kunstsenter", env_flag="ENABLE_HKS", default_enabled=True),
    SourceConfig(name="Aerial Bergen", module="scraper.sources.aerial_bergen", env_flag="ENABLE_AERIAL_BERGEN", default_enabled=True),
    SourceConfig(name="Zip Collective", module="scraper.sources.zip_collective", env_flag="ENABLE_ZIP_COLLECTIVE", default_enabled=True),
    SourceConfig(name="Det Akademiske Kvarter", module="scraper.sources.kvarteret", env_flag="ENABLE_KVARTERET", default_enabled=True),
    SourceConfig(name="Hulen", module="scraper.sources.hulen", env_flag="ENABLE_HULEN", default_enabled=True),
    SourceConfig(name="Apollon Platebar", module="scraper.sources.apollon", env_flag="ENABLE_APOLLON", default_enabled=False),
    SourceConfig(name="Stereo", module="scraper.sources.stereo", env_flag="ENABLE_STEREO", default_enabled=False),
    SourceConfig(name="Vaskeriet", module="scraper.sources.vaskeriet", env_flag="ENABLE_VASKERIET", default_enabled=False),
    SourceConfig(name="Bastant", module="scraper.sources.bastant", env_flag="ENABLE_BASTANT", default_enabled=False),
    SourceConfig(name="Festspillene i Bergen", module="scraper.sources.festspillene", env_flag="ENABLE_FESTSPILLENE", default_enabled=True),
    SourceConfig(name="Bergen Filharmoniske Orkester", module="scraper.sources.bergen_philharmonic", env_flag="ENABLE_BERGEN_PHILHARMONIC", default_enabled=True),
    SourceConfig(name="Grieghallen", module="scraper.sources.grieghallen", env_flag="ENABLE_GRIEGHALLEN", default_enabled=True),
    SourceConfig(name="Den Nationale Scene", module="scraper.sources.den_nationale_scene", env_flag="ENABLE_DNS", default_enabled=True),
    SourceConfig(name="Resident Advisor", module="scraper.sources.resident_advisor", env_flag="SCRAPE_RA", default_enabled=False),
    SourceConfig(name="Kennel Vinylbar", module="scraper.sources.kennel_vinylbar", env_flag="ENABLE_IG_KENNEL", default_enabled=False),
)
