"""CLI entry point - scripted demo across all three channels.

Default backend is the deterministic stub so the kit runs without a Bot
Framework registration. Set M365_AGENT_PROVIDER=sdk to route through the
real M365 Agents SDK.

Usage:
    m365-agents-example                # scripted demo across 3 channels
    m365-agents-example --interactive  # REPL with channel switching
    m365-agents-example --json         # machine-readable transcript
    m365-agents-example --validate-manifest
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .agent import Agent, Conversation
from .manifest import default_manifest


SCRIPTED_TURNS = [
    ("teams", "alice", "What's my next meeting?"),
    ("teams", "alice", "Who is Sarah Chen?"),
    ("outlook", "bob", "What's our policy on data residency?"),
    ("copilot-canvas", "carol", "Show me Copilot adoption status."),
    ("teams", "dan", "I'm stuck, can you escalate?"),
    ("teams", "eve", "Sing me a song."),  # unmatched
]


def run_scripted(as_json: bool = False) -> int:
    agent = Agent()
    convos: dict[tuple[str, str], Conversation] = {}
    results = []

    for channel, user, msg in SCRIPTED_TURNS:
        key = (channel, user)
        if key not in convos:
            convos[key] = Conversation(user_id=user, channel=channel)
        rendered = agent.on_message(convos[key], msg)
        results.append({"channel": channel, "user": user, "message": msg,
                        "response": rendered})

        if not as_json:
            print(f"\n[{channel}] {user}> {msg}")
            print(f"   intent:    {rendered['intent']}")
            print(f"   shape:     {rendered['shape']}")
            preview = rendered.get("text") or rendered.get("body_html") or "(card payload)"
            preview = preview[:200] + ("..." if len(preview) > 200 else "")
            print(f"   response:  {preview}")
            if rendered.get("citations"):
                print(f"   citations: {rendered['citations']}")
            if rendered.get("handoff"):
                print(f"   handoff:   {rendered['handoff']}")

    if as_json:
        print(json.dumps({"provider": agent.provider, "turns": results}, indent=2))
    else:
        print(f"\nProvider: {agent.provider}  (set M365_AGENT_PROVIDER=sdk to swap)")
    return 0


def run_interactive() -> int:
    agent = Agent()
    print(f"M365 Agents SDK example (provider={agent.provider}).")
    print("Type 'channel teams|outlook|copilot-canvas' to switch channels. Ctrl-C to exit.\n")
    channel = "teams"
    convo = Conversation(user_id="interactive", channel=channel)
    while True:
        try:
            msg = input(f"[{channel}]> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return 0
        if not msg:
            continue
        if msg.startswith("channel "):
            new_channel = msg.split(maxsplit=1)[1].strip()
            if agent.manifest.channel(new_channel):
                channel = new_channel
                convo = Conversation(user_id="interactive", channel=channel)
                print(f"   (switched to {channel})")
            else:
                print(f"   (unknown channel '{new_channel}')")
            continue
        rendered = agent.on_message(convo, msg)
        preview = rendered.get("text") or rendered.get("body_html") or json.dumps(rendered.get("card"), indent=2)
        print(f"\n[{rendered['intent']}/{rendered['shape']}]\n{preview}\n")


def run_validate() -> int:
    m = default_manifest()
    problems = m.validate()
    if problems:
        print("Manifest validation FAILED:")
        for p in problems:
            print(f"  - {p}")
        return 1
    print(f"Manifest OK: {len(m.channels)} channels, {len(m.intents)} intents, "
          f"{len(m.connectors)} connectors.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="M365 Agents SDK example demo.")
    parser.add_argument("--interactive", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--validate-manifest", action="store_true",
                        dest="validate_manifest")
    args = parser.parse_args(argv)

    if args.validate_manifest:
        return run_validate()
    if args.interactive:
        return run_interactive()
    return run_scripted(as_json=args.json)


if __name__ == "__main__":
    sys.exit(main())
