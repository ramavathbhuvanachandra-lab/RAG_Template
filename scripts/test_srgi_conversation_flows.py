#!/usr/bin/env python3
"""Run multi-turn conversation and session isolation tests for SRGI AI Assistant."""

import os
import sys
from pathlib import Path

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

os.environ["INSTITUTION_ID"] = "srgi"
os.environ["RAG_USE_STAGING"] = "1"

from ai_platform.service.assistant_service import handle_chat_turn

def test_conversation_sequence():
    print("=" * 80)
    print("TEST 1: 4-TURN CONVERSATION SEQUENCE (B.Tech CSE -> Eligibility -> Hostel -> Back to CSE)")
    print("=" * 80)
    
    chat_history = []
    
    # Turn 1
    q1 = "I'm thinking of taking B.Tech CSE at SRGI. Tell me the basic details."
    print("\n--- TURN 1 ---")
    print("User:", q1)
    resp1 = handle_chat_turn(q1, chat_history=chat_history)
    print("Answer Snippet:", resp1.answer[:250], "...")
    chat_history.append({"role": "user", "content": q1})
    chat_history.append({"role": "assistant", "content": resp1.answer})
    
    # Turn 2
    q2 = "What about eligibility?"
    print("\n--- TURN 2 ---")
    print("User:", q2)
    resp2 = handle_chat_turn(q2, chat_history=chat_history)
    resolved2 = resp2.diagnostics.get("resolved_question")
    print("Resolved Question:", resolved2)
    print("Answer Snippet:", resp2.answer[:250], "...")
    assert "cse" in str(resolved2).lower() or "b.tech" in str(resolved2).lower(), f"Turn 2 failed to resolve to B.Tech CSE: {resolved2}"
    chat_history.append({"role": "user", "content": q2})
    chat_history.append({"role": "assistant", "content": resp2.answer})
    
    # Turn 3
    q3 = "What about hostel facilities?"
    print("\n--- TURN 3 ---")
    print("User:", q3)
    resp3 = handle_chat_turn(q3, chat_history=chat_history)
    resolved3 = resp3.diagnostics.get("resolved_question")
    print("Resolved Question:", resolved3)
    print("Answer Snippet:", resp3.answer[:250], "...")
    chat_history.append({"role": "user", "content": q3})
    chat_history.append({"role": "assistant", "content": resp3.answer})
    
    # Turn 4: Return to topic
    q4 = "Okay, back to CSE—how many seats are there?"
    print("\n--- TURN 4 ---")
    print("User:", q4)
    resp4 = handle_chat_turn(q4, chat_history=chat_history)
    resolved4 = resp4.diagnostics.get("resolved_question")
    print("Resolved Question:", resolved4)
    print("Answer Snippet:", resp4.answer[:250], "...")
    assert "cse" in str(resolved4).lower() or "b.tech" in str(resolved4).lower(), f"Turn 4 failed to resolve back to CSE: {resolved4}"
    assert "180" in resp4.answer, f"Turn 4 expected 180 seats in CSE answer, got: {resp4.answer}"
    
    print("\n>>> 4-TURN SEQUENCE PASSED!")

def test_session_isolation():
    print("\n" + "=" * 80)
    print("TEST 2: FRESH SESSION ISOLATION (No history leak into new session)")
    print("=" * 80)
    
    # In a fresh session without history, a deictic query must not inherit previous session entities
    fresh_resp = handle_chat_turn("How many seats are there?", chat_history=[])
    resolved_fresh = fresh_resp.diagnostics.get("resolved_question")
    print("Fresh Unanchored Query Resolved:", resolved_fresh)
    # Must not assume CSE from previous session
    assert "cse" not in str(resolved_fresh).lower(), f"Session isolation failed: fresh session inherited CSE: {resolved_fresh}"
    print(">>> FRESH SESSION ISOLATION PASSED!")

def test_degree_level_switch():
    print("\n" + "=" * 80)
    print("TEST 3: DEGREE-LEVEL SWITCH (Undergraduate B.Tech -> Postgraduate M.Tech)")
    print("=" * 80)
    
    history = [
        {"role": "user", "content": "Tell me about B.Tech CSE."},
        {"role": "assistant", "content": "B.Tech CSE is a 4-year undergraduate programme with 180 seats."},
    ]
    # Now user explicitly switches degree level to M.Tech
    q_switch = "What about M.Tech programmes and their eligibility?"
    resp = handle_chat_turn(q_switch, chat_history=history)
    resolved = resp.diagnostics.get("resolved_question")
    print("Degree Switch Query:", q_switch)
    print("Resolved:", resolved)
    print("Answer Snippet:", resp.answer[:250], "...")
    sources = [s.get("heading") or s.get("source") for s in resp.sources]
    print("Sources:", sources)
    assert any("m.tech" in s.lower() or "postgraduate" in s.lower() for s in sources), f"Degree switch failed to retrieve M.Tech sources: {sources}"
    print(">>> DEGREE-LEVEL SWITCH PASSED!")

if __name__ == "__main__":
    test_conversation_sequence()
    test_session_isolation()
    test_degree_level_switch()
    print("\nALL CONVERSATION TESTS PASSED SUCCESSFULLY!")
