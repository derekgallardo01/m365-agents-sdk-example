"""Eval harness - exercises intent routing + channel rendering against golden cases."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from m365_agents_example.agent import Agent, Conversation  # noqa: E402


def load_cases() -> list[dict]:
    with open(Path(__file__).parent / "golden.json") as f:
        return json.load(f)["cases"]


def run_case(agent: Agent, case: dict) -> dict:
    convo = Conversation(user_id="eval", channel=case["channel"])
    r = agent.on_message(convo, case["message"])

    intent_ok = r["intent"] == case["expect_intent"]
    shape_ok = r["shape"] == case["expect_shape"]
    prefix = case["expect_citation_prefix"]
    if prefix is None:
        cites_ok = True  # don't care
    else:
        cites_ok = any(c.startswith(prefix) for c in (r.get("citations") or []))
    return {
        "id": case["id"],
        "passed": intent_ok and shape_ok and cites_ok,
        "intent_ok": intent_ok,
        "shape_ok": shape_ok,
        "cites_ok": cites_ok,
        "actual": {"intent": r["intent"], "shape": r["shape"],
                   "citations": r.get("citations")},
    }


def main() -> int:
    cases = load_cases()
    agent = Agent()
    print(f"Running {len(cases)} eval cases against provider={agent.provider}\n")

    results = [run_case(agent, c) for c in cases]
    passed = sum(1 for r in results if r["passed"])

    for r in results:
        status = "PASS" if r["passed"] else "FAIL"
        print(f"  {status}  {r['id']:32s}  intent={r['intent_ok']}  shape={r['shape_ok']}  cites={r['cites_ok']}")
        if not r["passed"]:
            print(f"        actual: {r['actual']}")

    rate = passed / len(cases) if cases else 0.0
    print(f"\n{passed}/{len(cases)} passed ({rate:.0%})")
    return 0 if passed == len(cases) else 1


if __name__ == "__main__":
    sys.exit(main())
