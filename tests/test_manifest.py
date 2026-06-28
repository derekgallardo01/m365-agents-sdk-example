"""Tests for the declarative manifest."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from m365_agents_example.manifest import (  # noqa: E402
    Channel, Connector, Intent, Manifest, default_manifest,
)


def test_default_manifest_validates_clean():
    m = default_manifest()
    assert m.validate() == []


def test_manifest_catches_missing_connector():
    m = Manifest(
        name="broken", description="x", version="1.0",
        channels=[Channel("teams")],
        intents=[Intent(name="i1", triggers=["foo"], handler="h",
                        required_connectors=["nonexistent"])],
        connectors=[],
    )
    problems = m.validate()
    assert any("nonexistent" in p for p in problems)


def test_manifest_catches_no_channels():
    m = Manifest(name="x", description="x", version="1.0",
                 channels=[], intents=[Intent("i", ["x"], "h")], connectors=[])
    assert any("zero channels" in p for p in m.validate())


def test_manifest_catches_no_intents():
    m = Manifest(name="x", description="x", version="1.0",
                 channels=[Channel("teams")], intents=[], connectors=[])
    assert any("zero intents" in p for p in m.validate())


def test_find_intent_matches_substring_case_insensitive():
    m = default_manifest()
    intent = m.find_intent("What's my NEXT MEETING this afternoon?")
    assert intent is not None
    assert intent.name == "find_meeting"


def test_find_intent_returns_none_when_nothing_matches():
    m = default_manifest()
    assert m.find_intent("sing me a song please") is None


def test_channel_lookup_returns_known_channel():
    m = default_manifest()
    ch = m.channel("outlook")
    assert ch is not None
    assert ch.response_style == "email"


def test_channel_lookup_returns_none_for_unknown():
    m = default_manifest()
    assert m.channel("slack") is None
