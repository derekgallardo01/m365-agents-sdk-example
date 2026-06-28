"""Tests for the intent handlers - exercised directly without the agent loop."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from m365_agents_example import handlers  # noqa: E402


def _turn(msg: str, channel: str = "teams") -> handlers.Turn:
    return handlers.Turn(user_id="test-user", user_message=msg, channel=channel)


def test_find_meeting_returns_next_event_with_citation():
    r = handlers.handle_find_meeting(_turn("next meeting"))
    assert r.intent == "find_meeting"
    assert "1:1 with Sarah" in r.text or "governance" in r.text
    assert r.citations
    assert r.citations[0].startswith("graph_calendar:")


def test_lookup_person_finds_known_user():
    r = handlers.handle_lookup_person(_turn("Who is Sarah Chen?"))
    assert r.intent == "lookup_person"
    assert "Sarah Chen" in r.text
    assert "sarah.chen@acme.com" in r.text


def test_lookup_person_handles_unknown_gracefully():
    r = handlers.handle_lookup_person(_turn("Who is Bartholomew Quincy?"))
    assert r.intent == "lookup_person"
    assert "couldn't find" in r.text.lower()


def test_copilot_adoption_reports_status_and_percentages():
    r = handlers.handle_copilot_adoption(_turn("copilot adoption"))
    assert r.intent == "copilot_adoption"
    assert "%" in r.text  # there's a percentage in the text
    assert r.citations


def test_policy_question_returns_relevant_doc_snippet():
    r = handlers.handle_policy_question(_turn("data residency"))
    assert r.intent == "policy_question"
    assert "EU" in r.text or "residency" in r.text.lower()
    assert any("data-residency.md" in c for c in r.citations)


def test_policy_question_handles_unrelated_query():
    r = handlers.handle_policy_question(_turn("how do I bake bread"))
    assert r.intent == "policy_question"
    assert "couldn't find" in r.text.lower()


def test_escalate_sets_handoff_payload():
    r = handlers.handle_escalate(_turn("escalate me please"))
    assert r.intent == "escalate_to_human"
    assert r.handoff is not None
    assert r.handoff["queue"] == "helpdesk"
    assert "ticket_id" in r.handoff


def test_handle_unmatched_lists_capabilities():
    r = handlers.handle_unmatched(_turn("random unrelated message"))
    assert r.intent == "unmatched"
    assert "calendar" in r.text.lower()


def test_handler_registry_lists_all_named_handlers():
    expected = {
        "handle_find_meeting", "handle_lookup_person",
        "handle_copilot_adoption", "handle_policy_question", "handle_escalate",
    }
    assert set(handlers.HANDLER_REGISTRY) == expected
