"""Canonical event schema definitions for the SPONTIS scraper."""

REQUIRED_FIELDS = ("source", "title", "url")

STRING_FIELDS = {
    "venue",
    "city",
    "when",
    "where",
    "description",
    "summary",
    "image",
    "price",
    "timezone",
    "category",
    "series",
    "region",
    "url_original",
    "ticket_url",
}

INTEGER_FIELDS = {"url_status"}
BOOLEAN_FIELDS = {"free"}
IDENTIFIER_FIELDS = {"urlHash", "url_hash"}
SOURCE_LINK_KEYS = {"sourceLinks", "source_links"}
