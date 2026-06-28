"""Simulated multi-channel helpdesk session - all 3 channels + escalation.

Walks through a complete employee helpdesk scenario where the same agent
handles requests across:

  1. Teams chat: "what's my next meeting?"
  2. Outlook email reply: "what's our data residency policy?"
  3. Copilot canvas card: "show me Copilot adoption stats"
  4. Teams chat with escalation: "I'm stuck, can you escalate?"

For each turn, prints the inbound activity, the intent the manifest
matched, and the full channel-rendered response (chat text, Outlook
HTML, or adaptive card JSON).

This is what a deployed M365 Agent looks like end-to-end - take the
output and feed it into your Bot Framework registration and you're
serving production traffic. The stub backend is the demo; the production
wiring is documented in agent.py.

Usage:
    python examples/teams_helpdesk.py
    python examples/teams_helpdesk.py --json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from m365_agents_example.agent import Agent, Conversation  # noqa: E402


# Realistic helpdesk scenario - one employee bouncing between channels.
SCENARIO = [
    ("alice@acme.com", "teams",
     "Hey, what's my next meeting today?",
     "Calendar lookup via Teams"),
    ("alice@acme.com", "outlook",
     "What's our policy on data residency? Asking before a customer call.",
     "Policy question via Outlook (HTML reply)"),
    ("alice@acme.com", "copilot-canvas",
     "Show me Copilot adoption status for the org.",
     "Reporting via Copilot canvas (Adaptive Card)"),
    ("alice@acme.com", "teams",
     "I'm stuck on a permission issue - can you escalate to support?",
     "Escalation via Teams (handoff payload)"),
]


def run_scenario(as_json: bool = False) -> int:
    agent = Agent()
    # Conversations are per (user, channel)
    conversations: dict[tuple[str, str], Conversation] = {}

    transcripts = []
    for user, channel, message, narration in SCENARIO:
        key = (user, channel)
        if key not in conversations:
            conversations[key] = Conversation(user_id=user, channel=channel)
        convo = conversations[key]
        rendered = agent.on_message(convo, message)
        transcripts.append({
            "user": user, "channel": channel,
            "narration": narration,
            "inbound": message,
            "intent": rendered["intent"],
            "shape": rendered["shape"],
            "rendered": rendered,
        })

        if not as_json:
            print(f"\n{'=' * 70}")
            print(f"[{channel.upper()}] {user} — {narration}")
            print(f"{'=' * 70}")
            print(f"INBOUND:  {message}\n")
            print(f"INTENT:   {rendered['intent']}")
            print(f"SHAPE:    {rendered['shape']}")
            if rendered["shape"] == "chat":
                print(f"REPLY:    {rendered['text']}")
            elif rendered["shape"] == "email":
                print(f"SUBJECT:  {rendered['subject']}")
                print(f"BODY:")
                print(f"  {rendered['body_html']}")
            elif rendered["shape"] == "adaptive_card":
                print(f"CARD:")
                print(json.dumps(rendered['card'], indent=2))
            if rendered.get("citations"):
                print(f"CITES:    {rendered['citations']}")
            if rendered.get("handoff"):
                print(f"HANDOFF:  {json.dumps(rendered['handoff'])}")

    if as_json:
        print(json.dumps({
            "scenario": "multi-channel helpdesk",
            "turns": transcripts,
            "conversation_count": len(conversations),
        }, indent=2, default=str))
    else:
        print(f"\n{'=' * 70}")
        print(f"Session complete. {len(transcripts)} turn(s) across {len(conversations)} conversation(s).")
        print(f"Channel mix: {[t['channel'] for t in transcripts]}")
        print(f"Intent mix:  {[t['intent'] for t in transcripts]}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="End-to-end multi-channel M365 helpdesk session demo."
    )
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    return run_scenario(as_json=args.json)


if __name__ == "__main__":
    sys.exit(main())
