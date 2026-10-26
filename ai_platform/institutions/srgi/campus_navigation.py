"""
SRGI Lucknow campus navigation.

Institution-specific implementation:
- SRGI campus locations
- SRGI location aliases
- SRGI location data source
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .profile import DATA_ROOT

DATA_FILE = DATA_ROOT / "campus_locations.json"


def load_locations() -> list[dict[str, Any]]:
    """
    Load SRGI Lucknow campus locations.

    Returns an empty list if the institution data file cannot be read.
    """
    try:
        with DATA_FILE.open("r", encoding="utf-8") as file:
            data = json.load(file)

        if not isinstance(data, list):
            return []

        return data

    except Exception as exc:
        print(
            f"[SRGI Campus Navigation] "
            f"Error loading locations: {exc}"
        )
        return []


def find_location(query: str) -> dict[str, Any] | None:
    """
    Find an SRGI Lucknow campus location by name or alias.

    Matching is case-insensitive and uses whole-word/phrase matching.
    """
    normalized_query = str(query or "").strip().lower()

    if not normalized_query:
        return None

    best_match = None
    best_match_len = 0

    for location in load_locations():
        name = str(location.get("name", "")).strip().lower()
        if name:
            pattern = r"\b" + re.escape(name) + r"\b"
            if re.search(pattern, normalized_query):
                match_len = len(name)
                if match_len > best_match_len:
                    best_match = location
                    best_match_len = match_len

        aliases = location.get("aliases", [])
        if not isinstance(aliases, list):
            continue

        for alias in aliases:
            alias_text = str(alias or "").strip().lower()
            if not alias_text:
                continue

            pattern = r"\b" + re.escape(alias_text) + r"\b"
            if re.search(pattern, normalized_query):
                match_len = len(alias_text)
                if match_len > best_match_len:
                    best_match = location
                    best_match_len = match_len

    return best_match
