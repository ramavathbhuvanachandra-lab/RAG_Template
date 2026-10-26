"""SRGI Lucknow UI Presentation Plugin.

Implements the institution UI plugin contract for SRGI Lucknow using verified
campus location data, emergency contacts, and institutional information.
"""

from __future__ import annotations

import json
from pathlib import Path

from frontend.core.models import (
    CampusLocationItem,
    EmergencyContactItem,
    InstitutionUIConfig,
    QuickActionItem,
)
from frontend.core.plugin_registry import InstitutionUIPlugin

_INSTITUTION_DATA_ROOT = Path(__file__).resolve().parent.parent.parent.parent / "ai_platform" / "institutions" / "srgi" / "data"


def _load_srgi_campus_locations() -> tuple[CampusLocationItem, ...]:
    """Load SRGI campus location records from ai_platform/institutions/srgi/data/campus_locations.json."""
    loc_file = _INSTITUTION_DATA_ROOT / "campus_locations.json"
    if not loc_file.is_file():
        return ()

    try:
        with open(loc_file, "r", encoding="utf-8") as fp:
            data = json.load(fp)
        items = []
        for d in data:
            if not isinstance(d, dict):
                continue
            items.append(
                CampusLocationItem(
                    id=str(d.get("id", "")),
                    name=str(d.get("name", "")),
                    category=str(d.get("category", "General")),
                    description=str(d.get("description", "")),
                    timings=str(d.get("timings", "")),
                    google_maps=str(d.get("google_maps", "")),
                    directions=str(d.get("directions", "")),
                    show_in_map=bool(d.get("show_in_map", False)),
                )
            )
        return tuple(items)
    except Exception:
        return ()


def _load_srgi_emergency_contacts() -> tuple[EmergencyContactItem, ...]:
    """Load SRGI emergency contacts from ai_platform/institutions/srgi/data/emergency_contacts.json."""
    contact_file = _INSTITUTION_DATA_ROOT / "emergency_contacts.json"
    if not contact_file.is_file():
        return ()

    try:
        with open(contact_file, "r", encoding="utf-8") as fp:
            data = json.load(fp)
        items = []
        for d in data:
            if not isinstance(d, dict):
                continue
            items.append(
                EmergencyContactItem(
                    id=str(d.get("id", "")),
                    name=str(d.get("name", "")),
                    phone=str(d.get("phone", "")),
                    description=str(d.get("description", "")),
                    help_text=str(d.get("help_text", "")),
                )
            )
        return tuple(items)
    except Exception:
        return ()


class SRGIUIPlugin(InstitutionUIPlugin):
    """SRGI Lucknow presentation plugin."""

    @property
    def institution_id(self) -> str:
        return "srgi"

    def get_config(self) -> InstitutionUIConfig:
        locations = _load_srgi_campus_locations()
        emergency_contacts = _load_srgi_emergency_contacts()

        quick_actions = (
            QuickActionItem(
                id="qa_departments",
                label="Departments",
                prompt="What faculties and departments are at SRGI Lucknow?",
                icon="🏛️",
            ),
            QuickActionItem(
                id="qa_academic_programmes",
                label="Academic Programmes",
                prompt="What academic programmes and B.Tech specializations are offered at SRGI?",
                icon="🎓",
            ),
            QuickActionItem(
                id="qa_admissions",
                label="Admissions & Eligibility",
                prompt="What are the admission requirements, eligibility, and enquiry channels at SRGI?",
                icon="📋",
            ),
            QuickActionItem(
                id="qa_campus_facilities",
                label="Campus Facilities",
                prompt="What facilities, hostels, and transport services are available at SRGI?",
                icon="🚌",
            ),
        )

        supported_topics = (
            "Academic Programmes & Courses",
            "Faculties & Departments",
            "Admissions & Eligibility Criteria",
            "Campus Facilities, Hostels & Transport",
            "Institutional Profile & Accreditations",
        )

        return InstitutionUIConfig(
            institution_id="srgi",
            display_name="S. R. Group of Institutions (SRGI), Lucknow",
            tagline="Academic & Campus AI Assistant",
            logo_icon="🏛️",
            primary_color="#1E3A8A",
            accent_color="#2563EB",
            welcome_title="Welcome to SRGI AI Assistant",
            welcome_message=(
                "I can assist you with academic programmes, admissions eligibility, "
                "departments, campus facilities, and institutional information for "
                "**S. R. Group of Institutions (SRGI), Lucknow**."
            ),
            supported_topics=supported_topics,
            quick_actions=quick_actions,
            has_campus_map=bool(locations),
            campus_map_locations=locations,
            has_emergency_cards=bool(emergency_contacts),
            emergency_contacts=emergency_contacts,
            footer_text="SRGI Lucknow • Powered by Canonical AI Platform",
        )


__all__ = ["SRGIUIPlugin"]
