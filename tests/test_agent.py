"""Tests for the agent loop - intent routing, channel rendering, conversation log."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from m365_agents_example.agent import Agent, Conversation  # noqa: E402
from m365_agents_example.manifest import default_manifest, Manifest, Channel, Intent  # noqa: E402


def test_teams_channel_returns_chat_shape():
    agent = Agent()
    convo = Conversation(user_id="u1", channel="teams")
    r = agent.on_message(convo, "next meeting")
    assert r["shape"] == "chat"
    assert "text" in r
    assert r["intent"] == "find_meeting"


def test_outlook_channel_returns_email_shape_with_html():
    agent = Agent()
    convo = Conversation(user_id="u2", channel="outlook")
    r = agent.on_message(convo, "what's our policy on data residency")
    assert r["shape"] == "email"
    assert r["body_html"].startswith("<p>")
    assert r["subject"].lower().startswith("re:")


def test_copilot_canvas_returns_adaptive_card():
    agent = Agent()
    convo = Conversation(user_id="u3", channel="copilot-canvas")
    r = agent.on_message(convo, "copilot adoption status")
    assert r["shape"] == "adaptive_card"
    assert r["card"]["type"] == "AdaptiveCard"
    assert len(r["card"]["body"]) >= 2


def test_escalation_carries_handoff_payload_to_render():
    agent = Agent()
    convo = Conversation(user_id="u4", channel="teams")
    r = agent.on_message(convo, "escalate this please")
    assert r["handoff"] is not None
    assert r["handoff"]["queue"] == "helpdesk"


def test_unmatched_routes_to_fallback_handler():
    agent = Agent()
    convo = Conversation(user_id="u5", channel="teams")
    r = agent.on_message(convo, "tell me a joke")
    assert r["intent"] == "unmatched"
    assert "calendar" in r["text"].lower()


def test_conversation_history_accumulates_turns():
    agent = Agent()
    convo = Conversation(user_id="u6", channel="teams")
    agent.on_message(convo, "next meeting")
    agent.on_message(convo, "who is Alex Park")
    assert len(convo.history) == 2
    assert convo.history[0]["intent"] == "find_meeting"
    assert convo.history[1]["intent"] == "lookup_person"


def test_invalid_manifest_raises_on_agent_init():
    bad = Manifest(
        name="bad", description="x", version="1.0",
        channels=[Channel("teams")],
        intents=[Intent("i1", ["x"], "h", required_connectors=["missing"])],
        connectors=[],
    )
    import pytest
    with pytest.raises(ValueError):
        Agent(manifest=bad)


def test_provider_defaults_to_stub():
    saved = os.environ.pop("M365_AGENT_PROVIDER", None)
    try:
        agent = Agent()
        assert agent.provider == "stub"
    finally:
        if saved is not None:
            os.environ["M365_AGENT_PROVIDER"] = saved
