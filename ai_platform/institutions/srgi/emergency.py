"""
SRGI Lucknow emergency-contact lookup.

This module contains institution-specific emergency-contact behavior
and reads only SRGI Lucknow's structured emergency-contact data.
It strictly guards against intercepting general informational, transport,
or facility queries.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .profile import DATA_ROOT

DATA_FILE = DATA_ROOT / "emergency_contacts.json"

EMERGENCY_INTENT_PATTERN = re.compile(
    r"\b(?:emergency|breakdown|break down|broke down|accident|urgent|sos|helpline|whom to contact|who should i (?:call|contact)|who to (?:call|contact)|contact (?:number|person|cell) (?:if|in case of|for emergency))\b",
    re.IGNORECASE,
)


def load_emergency_contacts() -> list[dict[str, Any]]:
    """
    Load SRGI Lucknow emergency contacts.

    Returns an empty list when the data file cannot be read or does not
    contain a JSON list.
    """
    try:
        with DATA_FILE.open("r", encoding="utf-8") as file:
            data = json.load(file)

        if not isinstance(data, list):
            return []

        return data

    except Exception as exc:
        print(
            f"[SRGI Emergency] "
            f"Error loading contacts: {exc}"
        )
        return []


def find_emergency(
    query: str,
) -> dict[str, Any] | None:
    """
    Find an SRGI Lucknow emergency contact by name or alias.

    Guards against matching non-emergency informational requests.
    Matching requires either an explicit emergency intent in the query
    or an exact match on an emergency service name/alias.

    Returns:
        Matching contact dictionary, or None when no contact matches.
    """
    normalized_query = " ".join(str(query or "").strip().lower().split())

    if not normalized_query:
        return None

    has_emergency_intent = bool(EMERGENCY_INTENT_PATTERN.search(normalized_query))

    for contact in load_emergency_contacts():
        name = str(contact.get("name", "")).strip().lower()

        # Direct name match with word boundaries
        if name:
            pattern = r"\b" + re.escape(name) + r"\b"
            if re.search(pattern, normalized_query):
                return contact

        aliases = contact.get("aliases", [])
        if not isinstance(aliases, list):
            continue

        for alias in aliases:
            alias_text = str(alias or "").strip().lower()
            if not alias_text:
                continue

            alias_pattern = r"\b" + re.escape(alias_text) + r"\b"
            if re.search(alias_pattern, normalized_query):
                return contact

            # If emergency intent is present and a key word from the contact matches
            if has_emergency_intent:
                contact_id = str(contact.get("id", "")).lower()
                if "transit" in contact_id and any(w in normalized_query for w in ("bus", "transit", "transport", "vehicle")):
                    return contact
                if "hostel" in contact_id and any(w in normalized_query for w in ("hostel", "warden", "room", "mess")):
                    return contact
                if "security" in contact_id and any(w in normalized_query for w in ("security", "guard", "proctor", "ragging", "threat")):
                    return contact
                if "admissions" in contact_id and any(w in normalized_query for w in ("admission", "counselling", "enrollment")):
                    return contact

    return None


__all__ = [
    "DATA_FILE",
    "load_emergency_contacts",
    "find_emergency",
]
