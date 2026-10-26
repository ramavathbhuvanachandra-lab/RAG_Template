"""Bounded Question-Answering Test Suite for SRGI Knowledge Package Integration.

Tests representative questions covering:
1. Department / Faculty List
2. Academic Programmes
3. Admissions & Eligibility
4. Campus Facilities & Contacts
5. Unsupported Question (Abstention check)
6. Ambiguous Query (CSE intake and affiliation)
"""

import os
import sys
from pathlib import Path
import json
import time

_WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
if str(_WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(_WORKSPACE_ROOT))

os.environ["INSTITUTION_ID"] = "srgi"
os.environ["RAG_USE_STAGING"] = "1"

from ai_platform.service.assistant_service import handle_chat_turn

TEST_CASES = [
    {
        "id": "tc1_departments",
        "category": "Department or School List",
        "question": "What faculties and institutes comprise SRGI Lucknow?",
        "expected_fact": "SRGI includes Faculty of Engineering & Technology, Faculty of Management, Faculty of Pharmacy, etc. under S. R. Group of Institutions.",
        "expected_source": "srgi_lucknow_rag_package_v3/data/departments.json or institutional_overview",
    },
    {
        "id": "tc2_programmes",
        "category": "Academic Programmes",
        "question": "What B.Tech programmes and specializations are offered at SRGI?",
        "expected_fact": "B.Tech in Computer Science & Engineering (Core, AI/ML, Data Science), IT, ECE, EEE, etc.",
        "expected_source": "srgi_lucknow_rag_package_v3/data/academic_programmes.json or srgi_lucknow_btech_overview.docx",
    },
    {
        "id": "tc3_admissions",
        "category": "Admissions & Eligibility",
        "question": "What is the admission procedure and eligibility for B.Tech at SRGI Lucknow?",
        "expected_fact": "10+2 with Physics and Mathematics along with Chemistry/CS/Bio, admission through AKTU counselling / JEE Main / CUET / direct admission.",
        "expected_source": "srgi_lucknow_rag_package_v3/data/admission_rules.json or documents/07_admissions",
    },
    {
        "id": "tc4_facilities",
        "category": "Campus Facilities & Contacts",
        "question": "What hostel and library facilities are available on campus at SRGI Lucknow?",
        "expected_fact": "Separate Boys and Girls hostels with 24/7 security, Central Library with 53,760+ books and journals.",
        "expected_source": "srgi_lucknow_rag_package_v3/data/hostel_facilities.json or documents/02_campus_facilities",
    },
    {
        "id": "tc5_unsupported",
        "category": "Unsupported Question (Abstention check)",
        "question": "What are the admission requirements for the Master of Science in Underwater Archaeology at SRGI?",
        "expected_fact": "Abstain / state that SRGI does not offer Underwater Archaeology.",
        "expected_source": "Abstention policy / no evidence in package",
    },
    {
        "id": "tc6_ambiguous",
        "category": "Difficult or Ambiguous Query",
        "question": "Tell me about CSE intake and affiliations at SRGI.",
        "expected_fact": "B.Tech CSE sanctioned intake of 180 seats, affiliated with AKTU Lucknow and approved by AICTE.",
        "expected_source": "srgi_lucknow_rag_package_v3/data/academic_programmes.json",
    },
]

def run_tests():
    results = []
    print("=" * 80)
    print("STARTING SRGI BOUNDED QUESTION-ANSWERING EVALUATION")
    print("=" * 80)

    for tc in TEST_CASES:
        print(f"\nRunning {tc['id']}: {tc['question']} ...")
        t0 = time.perf_counter()
        resp = handle_chat_turn(tc["question"], institution_id="srgi")
        elapsed = time.perf_counter() - t0

        diag = resp.diagnostics or {}
        funnel = diag.get("funnel", {})
        candidates = diag.get("section_a_candidates", [])
        context_items = diag.get("section_b_context", [])

        # Extract citation details
        citations = []
        for s in resp.sources:
            citations.append({
                "source": s.get("source"),
                "heading": s.get("heading"),
                "evidence_id": s.get("evidence_id"),
            })

        result = {
            "id": tc["id"],
            "category": tc["category"],
            "question": tc["question"],
            "expected_fact": tc["expected_fact"],
            "expected_source": tc["expected_source"],
            "resolved_institution": "srgi",
            "release_id": "srgi_lucknow_rag_package_v3",
            "active_collection": "srgi_srgi_lucknow_rag_package_v3_staging",
            "retrieved_candidates_count": len(candidates),
            "final_context_count": len(context_items),
            "final_context_ids": [c.get("evidence_id", "") if isinstance(c, dict) else str(c)[:50] for c in context_items],
            "answer": resp.answer,
            "citations": citations,
            "evidence_status": resp.evidence_status,
            "is_safe_refusal": resp.is_safe_refusal,
            "latency_seconds": round(resp.latency_seconds, 2),
            "route_selected": diag.get("route_selected"),
        }
        results.append(result)

        print(f"  Status: {resp.evidence_status} | Latency: {result['latency_seconds']}s")
        print(f"  Citations ({len(citations)}): {[c['heading'] for c in citations if c['heading']]}")
        print(f"  Answer Preview: {resp.answer[:200]}...")

    output_path = "/Users/bhuvanachandra/Desktop/RAG_SRGI/data/srgi_qa_evaluation_results.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print(f"\nAll tests completed. Results saved to {output_path}")

if __name__ == "__main__":
    run_tests()
