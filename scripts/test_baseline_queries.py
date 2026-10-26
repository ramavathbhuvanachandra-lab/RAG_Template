#!/usr/bin/env python3
"""Run baseline queries for SRGI Evidence Coverage & Retrieval Quality Audit."""

import json
import os
import sys
import time
from pathlib import Path

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

os.environ["INSTITUTION_ID"] = "srgi"
os.environ["RAG_USE_STAGING"] = "1"

from ai_platform.service.assistant_service import handle_chat_turn

QUERIES = [
    ("Q01_cse_basic_details", "I'm thinking of taking B.Tech CSE at SRGI. Tell me the basic details."),
    ("Q02_cse_vs_ece", "Bhai, I'm confused between CSE and ECE. What do we study in both, and what kind of jobs can we get after graduation?"),
    ("Q03_44_percent_eligibility", "I got 44% in Class 12 PCM. Can I apply for B.Tech at SRGI, or am I not eligible?"),
    ("Q04_jee_main_vs_direct", "I haven't taken any admission yet. Do I need JEE Main for SRGI, or can I apply directly?"),
    ("Q05_reporting_documents", "I'm coming to the college for admission. Tell me exactly which documents I should carry so I don't have to come back again."),
    ("Q06_mtech_eligibility", "I completed B.Tech with 49%, and I haven't qualified GATE. Can I still get admission to M.Tech?"),
    ("Q07_hostel_fees_facilities", "Bhai, I'm coming from another city. Is hostel available, what facilities do I get, and how much will it cost?"),
    ("Q08_bus_routes_timings", "I live in Lucknow and want to travel to college by bus. Do you have college buses, which areas do they cover, and what time does the first bus leave?"),
    ("Q09_library_resources", "Tell me about the library collection, reading capacity, and digital knowledge resources available at SRGI."),
    ("Q10_multi_topic_cse_hostel", "CSE aur hostel ke baare mein batao."),
    ("Q11_campus_facilities", "What campus facilities and student amenities are available?"),
]

def run():
    print("=" * 80)
    print("SRGI EVIDENCE COVERAGE & RETRIEVAL QUALITY BASELINE AUDIT")
    print("=" * 80)
    results = []
    for qid, q in QUERIES:
        print(f"\n--- [{qid}] ---")
        print(f"Query: {q}")
        t0 = time.perf_counter()
        resp = handle_chat_turn(q)
        lat = time.perf_counter() - t0
        print(f"Latency: {lat:.2f}s | Status: {resp.evidence_status} | Safe Refusal: {resp.is_safe_refusal}")
        sources = [s.get("heading") or s.get("source") for s in resp.sources]
        print(f"Sources ({len(sources)}): {sources}")
        diag = resp.diagnostics or {}
        print(f"Diagnostics: target={diag.get('primary_target')} attrs={diag.get('requested_attributes')} qtype={diag.get('question_type')} mode={diag.get('answer_mode')}")
        print("Response Snippet:")
        print(resp.answer[:400] + ("..." if len(resp.answer) > 400 else ""))
        print("-" * 60)
        results.append({
            "qid": qid,
            "query": q,
            "answer": resp.answer,
            "sources": sources,
            "status": resp.evidence_status,
            "is_safe_refusal": resp.is_safe_refusal,
            "latency": round(lat, 2),
            "diagnostics": {
                "target": diag.get("primary_target"),
                "attributes": diag.get("requested_attributes"),
                "answer_mode": diag.get("answer_mode"),
            }
        })

    out_file = Path("data/baseline_audit_results.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"\nSaved baseline audit results to {out_file}")

if __name__ == "__main__":
    run()
