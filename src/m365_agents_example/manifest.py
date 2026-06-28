"""Declarative agent manifest - the M365 Agents SDK shape.

In the real SDK, the manifest is a JSON/YAML file the platform reads at
deploy time to figure out which channels the agent is published on, which
M365 connectors it can call, and which intents (activity handlers) it
understands. This module produces and validates the same shape, so the
kit's tests + Pages demo can exercise the dispatch logic without
provisioning a Bot Framework registration.

Mirroring the same separation the real SDK uses:
  - manifest = declarative surface (what)
  - handlers = imperative behaviour (how)
  - connectors = M365 surfaces the agent can read/write to

A new tenant deployment swaps the manifest JSON; the handler code is
untouched.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class Channel:
    """One M365 surface the agent is published on."""
    name: str  # "teams" | "outlook" | "copilot-canvas"
    enabled: bool = True
    response_style: str = "chat"  # "chat" | "email" | "card"


@dataclass
class Intent:
    """A named user intent + which handler answers it.

    `triggers` is the list of phrases (case-insensitive substring) that
    route to this intent. In the real SDK these would be LUIS/CLU
    utterances or the LLM's intent classification; the kit uses
    substring match for determinism.
    """
    name: str
    triggers: list[str]
    handler: str  # function name in handlers.py
    required_connectors: list[str] = field(default_factory=list)


@dataclass
class Connector:
    """A Microsoft Graph / M365 connector the agent can call."""
    name: str
    scopes: list[str]
    description: str


@dataclass
class Manifest:
    """The whole agent definition - mirrors what an M365 Agents SDK
    deployment would read from agent-manifest.json at deploy time."""
    name: str
    description: str
    version: str
    channels: list[Channel]
    intents: list[Intent]
    connectors: list[Connector]

    def channel(self, name: str) -> Channel | None:
        return next((c for c in self.channels if c.name == name), None)

    def find_intent(self, user_message: str) -> Intent | None:
        msg = user_message.lower()
        for intent in self.intents:
            for trig in intent.triggers:
                if trig.lower() in msg:
                    return intent
        return None

    def validate(self) -> list[str]:
        """Return a list of problems with this manifest. Empty list = OK."""
        problems = []
        connector_names = {c.name for c in self.connectors}
        for intent in self.intents:
            for needed in intent.required_connectors:
                if needed not in connector_names:
                    problems.append(
                        f"Intent '{intent.name}' requires connector "
                        f"'{needed}' which is not declared."
                    )
        if not self.channels:
            problems.append("Manifest declares zero channels.")
        if not self.intents:
            problems.append("Manifest declares zero intents.")
        return problems


def default_manifest() -> Manifest:
    """A worked manifest for an internal M365 helper agent.

    Three channels (Teams chat, Outlook email reply, Copilot canvas card)
    so the kit can show channel-aware responses. Five intents covering the
    most common ask shapes an M365 consultant sees.
    """
    return Manifest(
        name="Internal Helper",
        description="Org-wide assistant for Microsoft 365 questions, calendar lookups, and Copilot adoption summaries.",
        version="1.0.0",
        channels=[
            Channel("teams", response_style="chat"),
            Channel("outlook", response_style="email"),
            Channel("copilot-canvas", response_style="card"),
        ],
        intents=[
            Intent(
                name="find_meeting",
                triggers=["next meeting", "calendar", "schedule",
                          "when is my", "free time"],
                handler="handle_find_meeting",
                required_connectors=["graph_calendar"],
            ),
            Intent(
                name="lookup_person",
                triggers=["who is", "find user", "directory",
                          "email address for"],
                handler="handle_lookup_person",
                required_connectors=["graph_directory"],
            ),
            Intent(
                name="copilot_adoption",
                triggers=["copilot adoption", "rollout status",
                          "usage report", "active users"],
                handler="handle_copilot_adoption",
                required_connectors=["graph_reports"],
            ),
            Intent(
                name="policy_question",
                triggers=["what's our policy", "policy on",
                          "data residency", "compliance"],
                handler="handle_policy_question",
                required_connectors=["sharepoint_search"],
            ),
            Intent(
                name="escalate_to_human",
                triggers=["talk to a person", "escalate",
                          "speak to support", "i'm stuck"],
                handler="handle_escalate",
                required_connectors=[],
            ),
        ],
        connectors=[
            Connector("graph_calendar", ["Calendars.Read"],
                      "Read user's Outlook calendar."),
            Connector("graph_directory", ["Directory.Read.All"],
                      "Look up users in Entra ID."),
            Connector("graph_reports", ["Reports.Read.All"],
                      "Read Copilot usage report aggregates."),
            Connector("sharepoint_search", ["Sites.Read.All"],
                      "Search the policy SharePoint site."),
        ],
    )
