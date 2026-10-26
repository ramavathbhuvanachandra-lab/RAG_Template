"""Acceptance testing for Persistent Retrieval Diagnostics Toggle (Section 9)."""

from streamlit.testing.v1 import AppTest

def test_persistent_diagnostics_toggle_lifecycle():
    """Verify diagnostics toggle behavior across multi-turn conversation and reruns."""
    at = AppTest.from_file("frontend/app.py", default_timeout=30)
    at.run()
    assert not at.exception, f"App crashed on startup: {at.exception}"

    # 1. Ask 3 questions and record traces in session_state
    traces = []
    for i in range(1, 4):
        tid = f"turn_{i}"
        trace = {
            "turn_id": tid,
            "turn_number": i,
            "query": f"Question {i}",
            "query_preview": f"Question {i}",
            "timestamp": f"12:0{i}:00",
            "latency_seconds": 1.5 * i,
            "terminal_status": "SUCCESS",
            "diagnostics": {
                "turn_id": tid,
                "resolved_question": f"Question {i} (resolved)",
                "terminal_status": "SUCCESS",
                "funnel": {
                    "retrieved_total": 40,
                    "verified_count": 20,
                    "rejected_count": 20,
                    "context_units_count": 10,
                    "displayed_citations_count": 2,
                },
                "panel_packaged_context": {"context_units_count": 10},
                "panel_query_understanding": {},
                "panel_stage_timings": {},
            }
        }
        traces.append(trace)

    at.session_state["execution_traces"] = traces
    at.session_state["show_retrieval_diagnostics"] = True
    at.run()
    assert not at.exception, f"App crashed when diagnostics enabled: {at.exception}"

    # Verify all 3 traces appear
    # The header displays "Retrieval & Pipeline Diagnostics (3 Completed Turns)"
    markdown_texts = [m.value for m in at.markdown]
    has_diag_header = any("Retrieval & Pipeline Diagnostics (3 Completed Turns)" in t for t in markdown_texts)
    assert has_diag_header, "Diagnostics header with 3 turns not found!"

    # 2. Disable diagnostics
    at.session_state["show_retrieval_diagnostics"] = False
    at.run()
    assert not at.exception
    markdown_texts = [m.value for m in at.markdown]
    has_diag_header_off = any("Retrieval & Pipeline Diagnostics" in t for t in markdown_texts)
    assert not has_diag_header_off, "Diagnostics should be hidden when toggle is off!"
    assert len(at.session_state["execution_traces"]) == 3, "Traces were mutated or deleted when toggle turned off!"

    # 3. Re-enable diagnostics
    at.session_state["show_retrieval_diagnostics"] = True
    at.run()
    assert not at.exception
    markdown_texts = [m.value for m in at.markdown]
    has_diag_header_re = any("Retrieval & Pipeline Diagnostics (3 Completed Turns)" in t for t in markdown_texts)
    assert has_diag_header_re, "All 3 traces did not reappear upon re-enabling toggle!"

    # 4. Add 4th question
    trace4 = {
        "turn_id": "turn_4",
        "turn_number": 4,
        "query": "Question 4",
        "query_preview": "Question 4",
        "timestamp": "12:04:00",
        "latency_seconds": 2.2,
        "terminal_status": "SUCCESS",
        "diagnostics": {
            "turn_id": "turn_4",
            "resolved_question": "Question 4",
            "terminal_status": "SUCCESS",
            "funnel": {"retrieved_total": 45, "verified_count": 25, "context_units_count": 10},
            "panel_packaged_context": {"context_units_count": 10},
        }
    }
    at.session_state["execution_traces"].append(trace4)
    at.run()
    assert not at.exception
    markdown_texts = [m.value for m in at.markdown]
    has_diag_header_4 = any("Retrieval & Pipeline Diagnostics (4 Completed Turns)" in t for t in markdown_texts)
    assert has_diag_header_4, "4 traces should now be visible!"

    # 5. Selecting a specific trace does not destroy or lose other traces
    at.session_state["selected_trace_id"] = "turn_2"
    at.run()
    assert not at.exception
    assert len(at.session_state["execution_traces"]) == 4, "Selecting a trace lost other turns!"

    # 6. Separate browser session isolation
    at2 = AppTest.from_file("frontend/app.py", default_timeout=30)
    at2.run()
    assert not at2.exception
    assert "execution_traces" not in at2.session_state or len(at2.session_state["execution_traces"]) == 0, "Traces leaked across browser sessions!"
    assert "show_retrieval_diagnostics" not in at2.session_state or at2.session_state["show_retrieval_diagnostics"] is False, "Toggle state leaked across sessions!"

    print("✅ All 10 persistent retrieval diagnostics toggle acceptance tests passed!")

if __name__ == "__main__":
    test_persistent_diagnostics_toggle_lifecycle()
