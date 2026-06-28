"""Intent handlers - the imperative half of an M365 Agents SDK build.

In the real SDK, each handler is a method on an `ActivityHandler` subclass
that receives a `TurnContext`, calls one or more Graph connectors, and
returns an outbound activity. The kit's shape mirrors that 1:1 - each
handler takes a `Turn` and returns a `Response`, with channel-aware
rendering centralized in the agent loop.

A new intent = a new function here + a new entry in the manifest. The
agent loop and the test harness pick up everything else.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from . import connectors


@dataclass
class Turn:
    """One incoming activity from a channel."""
    user_id: str
    user_message: str
    channel: str  # "teams" | "outlook" | "copilot-canvas"


@dataclass
class Response:
    """The agent's outbound activity. Channel-renderer decides the final shape."""
    text: str                    # plain text body (always populated)
    intent: str                  # which intent matched
    citations: list[str]         # source doc ids, if any
    card: dict | None = None     # adaptive-card payload, if the channel supports cards
    handoff: dict | None = None  # set when the agent is escalating to a human


# ---------- the 5 handlers ---------------------------------------------------

def handle_find_meeting(turn: Turn) -> Response:
    evt = connectors.get_next_meeting()
    if not evt:
        return Response(text="No upcoming meetings found.",
                        intent="find_meeting", citations=[])
    start = evt["start"].replace("Z", "")
    return Response(
        text=f"Next meeting: \"{evt['subject']}\" at {start} with {', '.join(evt['attendees'])}.",
        intent="find_meeting",
        citations=[f"graph_calendar:{evt['id']}"],
    )


def handle_lookup_person(turn: Turn) -> Response:
    # Strip the common prefix from the user message to extract the name.
    msg = turn.user_message.lower()
    for prefix in ("who is", "find user", "email address for"):
        if prefix in msg:
            name = msg.split(prefix, 1)[1].strip().strip("?.").strip()
            break
    else:
        name = msg.strip().strip("?.")

    if not name:
        return Response(text="Who would you like me to look up?",
                        intent="lookup_person", citations=[])

    hits = connectors.search_directory(name)
    if not hits:
        return Response(text=f"I couldn't find anyone matching '{name}' in the directory.",
                        intent="lookup_person", citations=[])
    u = hits[0]
    return Response(
        text=f"{u['displayName']} - {u['jobTitle']}, {u['department']}. Email: {u['mail']}.",
        intent="lookup_person",
        citations=[f"graph_directory:{u['id']}"],
    )


def handle_copilot_adoption(turn: Turn) -> Response:
    r = connectors.get_copilot_adoption_report()
    line = (f"Copilot adoption is {r['status']}: {r['activeUsers']} of "
            f"{r['totalLicenses']} licenses active in the last {r['windowDays']} days "
            f"({int(r['adoptionPct'] * 100)}%). "
            f"Heaviest use is in Teams ({int(r['topApps'][0]['share'] * 100)}%).")
    return Response(text=line, intent="copilot_adoption",
                    citations=[f"graph_reports:{r['tenant']}"])


def handle_policy_question(turn: Turn) -> Response:
    hits = connectors.search_policies(turn.user_message, k=2)
    if not hits:
        return Response(text="I couldn't find a policy doc that covers that. Try asking IT directly.",
                        intent="policy_question", citations=[])
    top = hits[0]
    return Response(
        text=f"From {top['doc']}: {top['snippet']}",
        intent="policy_question",
        citations=[f"sharepoint_search:{h['doc']}" for h in hits],
    )


def handle_escalate(turn: Turn) -> Response:
    return Response(
        text="I'll hand you off to a human. I've created ticket #2026-0628-001 in the helpdesk queue with this conversation attached.",
        intent="escalate_to_human",
        citations=[],
        handoff={"queue": "helpdesk", "ticket_id": "2026-0628-001",
                 "reason": "user requested human handoff"},
    )


def handle_unmatched(turn: Turn) -> Response:
    """Fallback when no intent matches."""
    return Response(
        text=("I'm not sure which task you mean. I can help with: calendar lookups, "
              "finding people in the directory, Copilot adoption stats, policy "
              "questions, or escalating to a human."),
        intent="unmatched",
        citations=[],
    )


HANDLER_REGISTRY = {
    "handle_find_meeting": handle_find_meeting,
    "handle_lookup_person": handle_lookup_person,
    "handle_copilot_adoption": handle_copilot_adoption,
    "handle_policy_question": handle_policy_question,
    "handle_escalate": handle_escalate,
}
