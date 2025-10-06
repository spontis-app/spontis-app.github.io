"""JSON schema validation helpers for scraper outputs."""
from __future__ import annotations

from functools import lru_cache
from typing import Iterable

from jsonschema import Draft7Validator, FormatChecker


EVENT_SCHEMA: dict = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "required": ["source", "title", "url", "city"],
    "properties": {
        "source": {"type": "string", "minLength": 1},
        "title": {"type": "string", "minLength": 1},
        "url": {"type": "string", "format": "uri"},
        "city": {"type": "string", "minLength": 1},
        "venue": {"type": "string", "minLength": 1},
        "starts_at": {"type": "string", "format": "date-time"},
        "ends_at": {"type": "string", "format": "date-time"},
        "when": {"type": "string", "minLength": 1},
        "where": {"type": "string", "minLength": 1},
        "tags": {
            "type": "array",
            "items": {"type": "string", "minLength": 1},
            "uniqueItems": True,
        },
        "sources": {
            "type": "array",
            "items": {"type": "string", "minLength": 1},
            "uniqueItems": True,
        },
    },
    "additionalProperties": True,
}


@lru_cache(maxsize=1)
def _get_validator() -> Draft7Validator:
    return Draft7Validator(EVENT_SCHEMA, format_checker=FormatChecker())


def validate_event(payload: dict) -> tuple[bool, list[str]]:
    """Validate a single event dictionary.

    Returns a tuple ``(is_valid, errors)`` where ``errors`` is a list of
    human-readable error messages. The validator instance is cached so calling
    this helper repeatedly is cheap.
    """

    validator = _get_validator()
    errors = [
        f"{'.'.join(str(p) for p in error.path) or '<root>'}: {error.message}"
        for error in validator.iter_errors(payload)
    ]
    return (len(errors) == 0, errors)


def validate_events(events: Iterable[dict]) -> tuple[list[dict], list[tuple[dict, list[str]]]]:
    """Validate a collection of events.

    Returns a tuple ``(valid, invalid)`` where ``invalid`` is a list of pairs
    containing the rejected event payload and its corresponding error messages.
    """

    valid: list[dict] = []
    invalid: list[tuple[dict, list[str]]] = []

    for event in events:
        ok, errs = validate_event(event)
        if ok:
            valid.append(event)
        else:
            invalid.append((event, errs))

    return valid, invalid

