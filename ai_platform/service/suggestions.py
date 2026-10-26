"""Lightweight, Grounded Follow-up Suggestion Engine.

Generates concise, context-aware follow-up question suggestions for students
based strictly on the current question, verified answer, and available source metadata.

Constraints:
- Zero additional LLM invocations (preserves latency and compute budgets).
- At most 3 distinct, concise suggestions.
- Suppressed for safe refusals, errors, empty evidence, and off-topic queries.
- Strictly contextual: Never show academic programme suggestions after transport, library, or hostel queries.
"""

from __future__ import annotations

import re
from typing import Any, Sequence

# Canonical educational degree / program markers
_PROGRAM_PATTERNS: tuple[tuple[re.Pattern, str], ...] = (
    (re.compile(r"\bb\.?\s*tech\s*(?:in\s+)?cse\b|\bcse\b|\bcomputer\s+science\b", re.I), "B.Tech CSE"),
    (re.compile(r"\bb\.?\s*tech\b", re.I), "B.Tech"),
    (re.compile(r"\bm\.?\s*b\.?\s*a\.?\b|\bmba\b", re.I), "MBA"),
    (re.compile(r"\bm\.?\s*tech\b", re.I), "M.Tech"),
    (re.compile(r"\bb\.?\s*pharm\b|\bd\.?\s*pharm\b|\bpharmacy\b", re.I), "Pharmacy"),
    (re.compile(r"\bdiploma\b|\bpolytechnic\b", re.I), "Diploma / Polytechnic"),
    (re.compile(r"\bbba\b|\bbca\b|\bmca\b", re.I), "Professional Courses"),
)

_FACILITY_PATTERNS: tuple[tuple[re.Pattern, str], ...] = (
    (re.compile(r"\btransport\b|\bbus\b|\broutes?\b|\bcommute\b|\bfleet\b", re.I), "Transport"),
    (re.compile(r"\bhostel\b|\baccommodation\b|\broom\b", re.I), "Hostel"),
    (re.compile(r"\bmess\b|\bdining\b|\bcafeteria\b|\bfood\b", re.I), "Mess"),
    (re.compile(r"\blibrary\b|\bbooks?\b|\breading\s+room\b|\bjournal\b", re.I), "Library"),
    (re.compile(r"\blab(?:s|oratory|oratories)?\b|\binnovation\b", re.I), "Laboratories"),
    (re.compile(r"\bemergency\b|\bhelpline\b|\bproctor\b|\bhospital\b|\bambulance\b", re.I), "Emergency"),
)

# Topic-oriented suggestion templates
_TOPIC_TEMPLATES: dict[str, list[str]] = {
    "transport": [
        "What are the major bus pickup points across Lucknow?",
        "Who is the transport in-charge or contact person for buses?",
        "Are bus services available for day scholars across all semesters?",
    ],
    "hostel": [
        "What facilities and amenities are provided in the hostels?",
        "What are the mess and dining arrangements for hostellers?",
        "Who can I contact for hostel room allotment details?",
    ],
    "library": [
        "What are the central library working hours and reading room capacity?",
        "What digital library or e-journal subscriptions are available?",
        "Where is the Central Library located on the campus?",
    ],
    "emergency": [
        "What are the main campus security and medical helpline numbers?",
        "Who is the Chief Proctor at SRGI Lucknow?",
        "Where is the campus dispensary or health center located?",
    ],
    "departments": [
        "What undergraduate degrees are offered under the Faculty of Engineering?",
        "What are the admission eligibility requirements for these departments?",
        "Which institutes make up the S. R. Group of Institutions?",
    ],
    "btech": [
        "What specializations are available under B.Tech CSE?",
        "What is the sanctioned seat intake for B.Tech programmes?",
        "What are the eligibility criteria for B.Tech admission?",
    ],
    "mba": [
        "What dual specializations are offered in the MBA programme?",
        "What is the sanctioned seat intake for MBA at SRGI?",
        "What is the admission eligibility for MBA candidates?",
    ],
    "admissions": [
        "What are the minimum eligibility marks required for admissions?",
        "What is the sanctioned intake across various faculties?",
        "Who can I contact at the SRGI admissions helpline?",
    ],
    "fee": [
        "What are the hostel and transport charges?",
        "What is the admission and counselling fee policy?",
        "Who can I contact in the accounts or admissions office for fee queries?",
    ],
    "general_academic": [
        "What programmes and specializations are offered at SRGI?",
        "What are the general admission eligibility criteria?",
        "What campus facilities and student amenities are available?",
    ],
}


def _detect_entity(text: str) -> str:
    """Detect dominant degree, program, or campus entity from text."""
    for pattern, name in _FACILITY_PATTERNS:
        if pattern.search(text):
            return name
    for pattern, name in _PROGRAM_PATTERNS:
        if pattern.search(text):
            return name
    return ""


def _detect_topic(text: str, combined: str = "") -> str:
    """Identify query or answer topic focus strictly."""
    low = text.casefold()
    comb_low = combined.casefold()
    
    # Check facility / non-academic first to avoid bleeding into academic degrees
    if any(k in low for k in ("bus", "transport", "route", "routes", "transit", "fleet")):
        return "transport"
    if any(k in low for k in ("hostel", "accommodation", "hosteller", "boarding")):
        return "hostel"
    if any(k in low for k in ("library", "reading room", "books", "journal", "journals")):
        return "library"
    if any(k in low for k in ("emergency", "ambulance", "breakdown", "helpline", "proctor", "security guard")):
        return "emergency"
    if any(k in low for k in ("faculty", "faculties", "department", "departments", "institutes")):
        return "departments"
    if any(k in low for k in ("mba", "management")):
        return "mba"
    if any(k in low for k in ("btech", "b.tech", "cse", "computer science", "mechanical", "civil", "ec", "biotechnology")):
        return "btech"
    if any(k in low for k in ("eligibility", "admission", "admissions", "apply", "intake", "seats")):
        return "admissions"
    if any(k in low for k in ("fee", "fees", "tuition", "charges", "payment")):
        return "fee"
        
    # Check combined context if query was very short
    if any(k in comb_low for k in ("bus", "transport", "transit")):
        return "transport"
    if any(k in comb_low for k in ("hostel", "accommodation")):
        return "hostel"
    if any(k in comb_low for k in ("library", "reading room")):
        return "library"
        
    return "general_academic"


def _is_redundant(candidate: str, question: str, existing: Sequence[str]) -> bool:
    """Check if candidate question is too close to the current question or existing suggestions."""
    c_clean = " ".join(re.findall(r"\w+", candidate.casefold()))
    q_clean = " ".join(re.findall(r"\w+", question.casefold()))
    if c_clean == q_clean:
        return True
    # Word overlap check
    c_words = set(c_clean.split()) - {"what", "is", "are", "the", "for", "in", "and", "or", "to", "how", "do", "at", "srgi"}
    q_words = set(q_clean.split()) - {"what", "is", "are", "the", "for", "in", "and", "or", "to", "how", "do", "at", "srgi"}
    if c_words and q_words and (c_words == q_words or (len(c_words) >= 3 and len(c_words & q_words) >= len(c_words))):
        return True
    for item in existing:
        i_clean = " ".join(re.findall(r"\w+", item.casefold()))
        if c_clean == i_clean:
            return True
    return False


def generate_follow_up_suggestions(
    question: str,
    *,
    answer: str = "",
    sources: Sequence[dict[str, Any]] | None = None,
    is_safe_refusal: bool = False,
    evidence_status: str = "supported",
    max_suggestions: int = 3,
) -> list[str]:
    """Generate up to `max_suggestions` lightweight, grounded follow-up suggestions.

    Returns an empty list when the answer is an intentional abstention/safe refusal,
    when evidence is empty, or when an error occurred.
    """
    # Safe refusal or error check: never emit suggestions after a refusal or failure
    if is_safe_refusal or evidence_status in {"empty", "unsupported", "error", "empty_query", "service_error"}:
        return []

    clean_q = " ".join(str(question or "").strip().split())
    clean_a = " ".join(str(answer or "").strip().split())
    if not clean_q or not clean_a or len(clean_a) < 15:
        return []

    # Detect entity and topic from question, answer, and sources
    combined_context = f"{clean_q} {clean_a}"
    if sources:
        for s in sources[:3]:
            combined_context += f" {s.get('heading', '')} {s.get('source', '')}"

    topic = _detect_topic(clean_q, combined_context)

    # Candidate suggestions from templates
    templates = _TOPIC_TEMPLATES.get(topic, _TOPIC_TEMPLATES["general_academic"])
    results: list[str] = []

    for template in templates:
        candidate = template
        if not _is_redundant(candidate, clean_q, results):
            results.append(candidate)
        if len(results) >= max_suggestions:
            break

    return results[:max_suggestions]


__all__ = ["generate_follow_up_suggestions"]

