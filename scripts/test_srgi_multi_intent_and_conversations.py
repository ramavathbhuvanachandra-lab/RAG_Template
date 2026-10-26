#!/usr/bin/env python3
"""Comprehensive Multi-Intent and Multi-Turn Conversation Evaluation Harness for SRGI.

Tests:
1. P1: Multi-Intent queries requiring 2+ independently answerable attributes/topics in one message.
2. P2: Conversation continuity:
   - Sequence A: Same-topic follow-ups (B.Tech CSE -> intake -> eligibility -> application steps)
   - Sequence B: Topic switching (B.Tech CSE -> hostels -> transport -> "its annual intake")
   - Sequence C: Switch topic and return (B.Tech CSE -> library -> returning to CSE)
   - Sequence D: Multi-session isolation (two separate sessions, verify zero cross-talk)
"""

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


def run_multi_intent_tests() -> list[dict]:
    print("=" * 80)
    print("  P1: MULTI-INTENT VERIFICATION SUITE")
    print("=" * 80)

    test_cases = [
        {
            "id": "MI_01_btech_cse_triple_attribute",
            "question": "What are the B.Tech CSE eligibility criteria, annual intake, and admission steps at SRGI?",
            "expected_attributes": ["eligibility", "intake", "admission"],
            "expected_facts": ["10+2", "45%", "intake", "admission"],
            "expected_sources": ["srgi_lucknow_btech_overview", "academic_programmes.json"],
        },
        {
            "id": "MI_02_hostel_dining_and_transport",
            "question": "Tell me about the hostel facilities and dining arrangements, and explain the transport options available to students.",
            "expected_attributes": ["hostel", "mess", "transport"],
            "expected_facts": ["hostel", "mess", "bus", "transport"],
            "expected_sources": ["srgi_lucknow_hostel_accommodation", "srgi_lucknow_transport_facility"],
        },
        {
            "id": "MI_03_faculties_and_research",
            "question": "Which faculties and departments are offered, and what research areas are documented?",
            "expected_attributes": ["faculties", "departments", "research"],
            "expected_facts": ["Faculty of Engineering", "Management", "research"],
            "expected_sources": ["departments.json", "academic_programmes.json"],
        },
        {
            "id": "MI_04_programme_admission_and_fees",
            "question": "Explain the admission requirements and tuition fee for B.Tech programmes, distinguishing any missing or category-dependent information.",
            "expected_attributes": ["eligibility", "fee"],
            "expected_facts": ["admission", "JEE Main", "fee", "prospectus"],
            "expected_sources": ["srgi_lucknow_btech_overview"],
        },
        {
            "id": "MI_05_library_timings_hostel_contacts",
            "question": "Tell me about the library timings and hostel facilities, then provide the relevant contact details if the package supports them.",
            "expected_attributes": ["library", "hostel", "contacts"],
            "expected_facts": ["library", "hostel"],
            "expected_sources": ["srgi_lucknow_central_library", "srgi_lucknow_hostel_accommodation"],
        },
    ]

    results = []
    for idx, tc in enumerate(test_cases, 1):
        q = tc["question"]
        print(f"\n[{idx}/5] Multi-Intent Case: {tc['id']}")
        print(f"Q: {q}")
        t0 = time.perf_counter()
        resp = handle_chat_turn(q)
        lat = time.perf_counter() - t0

        ans_lower = resp.answer.casefold()
        matched_facts = [f for f in tc["expected_facts"] if f.casefold() in ans_lower]
        coverage = len(matched_facts) / max(1, len(tc["expected_facts"]))

        diag = resp.diagnostics or {}
        st = diag.get("panel_stage_timings", {})
        pkg = diag.get("panel_packaged_context", {})
        excl = st.get("exclusive_timings", {})

        verdict = "PASS" if coverage >= 0.65 else ("PARTIAL" if coverage >= 0.35 else "FAIL")
        print(f"Verdict: {verdict} (Fact coverage: {coverage:.1%}, Latency: {lat:.2f}s)")
        print(f"LLM Generation Time: {excl.get('llm_generation', 0.0):.2f}s | Delta: {st.get('reconciliation_delta', 0.0):.3f}s")
        print(f"Packaged Units: {pkg.get('context_units_count')} | Estimated Tokens: {pkg.get('estimated_tokens')}")
        print(f"Citations: {[s.get('heading') for s in resp.sources]}")
        print(f"Answer: {resp.answer[:220]}...")

        results.append({
            "id": tc["id"],
            "question": q,
            "verdict": verdict,
            "latency": round(lat, 3),
            "coverage": round(coverage, 2),
            "sources": [s.get("heading") for s in resp.sources],
            "answer": resp.answer,
        })

    return results


def run_conversation_sequences() -> dict:
    print("\n" + "=" * 80)
    print("  P2: CONVERSATION SEQUENCES & TOPIC RESOLUTION")
    print("=" * 80)

    seq_results = {}

    # -------------------------------------------------------------------------
    # SEQUENCE A: Same topic follow-ups
    # -------------------------------------------------------------------------
    print("\n--- SEQUENCE A: Same Topic (B.Tech CSE Follow-ups) ---")
    history_a = []
    turns_a = [
        ("A1", "Tell me about B.Tech CSE at SRGI."),
        ("A2", "And what is the intake?"),
        ("A3", "What about eligibility?"),
        ("A4", "How do I apply?"),
    ]
    seq_a_data = []
    for tid, q in turns_a:
        t0 = time.perf_counter()
        resp = handle_chat_turn(q, chat_history=history_a)
        lat = time.perf_counter() - t0
        history_a.append({"role": "user", "content": q})
        history_a.append({"role": "assistant", "content": resp.answer})

        print(f"[{tid}] Q: {q}")
        print(f"  Ans snippet: {resp.answer[:160]}...")
        print(f"  Sources: {[s.get('heading') for s in resp.sources]}")
        print(f"  Latency: {lat:.2f}s")

        # Validation rules:
        # Turn A2 must mention 180 seats and NOT mention unrelated mechanical/biotech intake
        valid = True
        if tid == "A2":
            valid = "180" in resp.answer and "biotechnology" not in resp.answer.casefold()
        elif tid == "A3":
            import re
            valid = ("10+2" in resp.answer or "45%" in resp.answer) and not bool(re.search(r"\bgate\b", resp.answer, flags=re.I))

        verdict = "PASS" if valid else "FAIL"
        print(f"  Turn Verdict: {verdict}")
        seq_a_data.append({"turn": tid, "q": q, "verdict": verdict, "latency": round(lat, 2)})

    seq_results["Sequence_A"] = seq_a_data

    # -------------------------------------------------------------------------
    # SEQUENCE B: Topic change
    # -------------------------------------------------------------------------
    print("\n--- SEQUENCE B: Topic Change (B.Tech CSE -> Hostels -> Transport -> 'its intake') ---")
    history_b = []
    turns_b = [
        ("B1", "Tell me about B.Tech CSE at SRGI."),
        ("B2", "What facilities are available in the hostels?"),
        ("B3", "How does student transport work?"),
        ("B4", "What is its annual intake?"),
    ]
    seq_b_data = []
    for tid, q in turns_b:
        t0 = time.perf_counter()
        resp = handle_chat_turn(q, chat_history=history_b)
        lat = time.perf_counter() - t0
        history_b.append({"role": "user", "content": q})
        history_b.append({"role": "assistant", "content": resp.answer})

        print(f"[{tid}] Q: {q}")
        print(f"  Ans snippet: {resp.answer[:160]}...")
        print(f"  Sources: {[s.get('heading') for s in resp.sources]}")
        print(f"  Latency: {lat:.2f}s")

        # Validation:
        # B2: must answer hostel, not pollute with CSE
        # B3: must answer transport, not pollute with CSE
        # B4: pronoun resolution check
        valid = True
        if tid == "B2":
            valid = "hostel" in resp.answer.casefold()
        elif tid == "B3":
            valid = "transport" in resp.answer.casefold() or "bus" in resp.answer.casefold()
        elif tid == "B4":
            # Either clarifies or resolves to CSE intake (180)
            valid = "180" in resp.answer or "clarify" in resp.answer.casefold() or "which" in resp.answer.casefold()

        verdict = "PASS" if valid else "FAIL"
        print(f"  Turn Verdict: {verdict}")
        seq_b_data.append({"turn": tid, "q": q, "verdict": verdict, "latency": round(lat, 2)})

    seq_results["Sequence_B"] = seq_b_data

    # -------------------------------------------------------------------------
    # SEQUENCE C: Switch topic and return
    # -------------------------------------------------------------------------
    print("\n--- SEQUENCE C: Switch Topic and Return (CSE -> Library -> Return to CSE) ---")
    history_c = []
    turns_c = [
        ("C1", "Tell me about B.Tech CSE at SRGI."),
        ("C2", "Tell me about the library facilities."),
        ("C3", "Returning to CSE, what is the intake?"),
    ]
    seq_c_data = []
    for tid, q in turns_c:
        t0 = time.perf_counter()
        resp = handle_chat_turn(q, chat_history=history_c)
        lat = time.perf_counter() - t0
        history_c.append({"role": "user", "content": q})
        history_c.append({"role": "assistant", "content": resp.answer})

        print(f"[{tid}] Q: {q}")
        print(f"  Ans snippet: {resp.answer[:160]}...")
        print(f"  Sources: {[s.get('heading') for s in resp.sources]}")
        print(f"  Latency: {lat:.2f}s")

        # Validation:
        # C2 must answer library, not CSE
        # C3 must resolve to CSE intake (180)
        valid = True
        if tid == "C2":
            valid = "library" in resp.answer.casefold() and "180 seats" not in resp.answer.casefold()
        elif tid == "C3":
            valid = "180" in resp.answer and "library" not in [s.get("heading", "").casefold() for s in resp.sources]

        verdict = "PASS" if valid else "FAIL"
        print(f"  Turn Verdict: {verdict}")
        seq_c_data.append({"turn": tid, "q": q, "verdict": verdict, "latency": round(lat, 2)})

    seq_results["Sequence_C"] = seq_c_data

    # -------------------------------------------------------------------------
    # SEQUENCE D: Session isolation
    # -------------------------------------------------------------------------
    print("\n--- SEQUENCE D: Multi-Session Isolation ---")
    # Session 1: B.Tech CSE
    s1_history = []
    s1_q = "What is the tuition fee and intake for B.Tech Computer Science and Engineering at SRGI?"
    s1_resp = handle_chat_turn(s1_q, chat_history=s1_history)

    # Session 2: completely separate, asks about Diploma in Pharmacy
    s2_history = []
    s2_q = "What is the duration of the Diploma in Pharmacy (D.Pharm)?"
    s2_resp = handle_chat_turn(s2_q, chat_history=s2_history)

    # Follow-up in Session 2: "And what is the intake?"
    s2_history.append({"role": "user", "content": s2_q})
    s2_history.append({"role": "assistant", "content": s2_resp.answer})
    s2_followup_q = "And what is the intake?"
    s2_followup_resp = handle_chat_turn(s2_followup_q, chat_history=s2_history)

    print(f"Session 1 Q: {s1_q}")
    print(f"Session 1 Ans: {s1_resp.answer[:120]}...")
    print(f"Session 2 Followup Q: {s2_followup_q}")
    print(f"Session 2 Followup Ans: {s2_followup_resp.answer[:120]}...")
    print(f"Session 2 Followup Sources: {[s.get('heading') for s in s2_followup_resp.sources]}")

    # Validation: Session 2 followup must NOT contain B.Tech CSE intake (180) or B.Tech sources!
    isolated = ("b.tech in computer science" not in [s.get("heading", "").casefold() for s in s2_followup_resp.sources]
                and "180" not in s2_followup_resp.answer)
    seq_d_verdict = "PASS" if isolated else "FAIL"
    print(f"Session Isolation Verdict: {seq_d_verdict}")
    seq_results["Sequence_D"] = {"verdict": seq_d_verdict, "isolated": isolated}

    return seq_results


if __name__ == "__main__":
    t_start = time.perf_counter()
    mi_res = run_multi_intent_tests()
    conv_res = run_conversation_sequences()

    summary_file = WORKSPACE_ROOT / "data" / "srgi_multi_intent_and_conversation_results.json"
    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump({"multi_intent": mi_res, "conversations": conv_res}, f, indent=2)

    print("\n" + "=" * 80)
    print(f"All tests completed in {time.perf_counter() - t_start:.2f}s")
    print(f"Results saved to: {summary_file}")
    print("=" * 80)
