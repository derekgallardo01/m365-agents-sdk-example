# FAQ

## Is this the real Microsoft 365 Agents SDK?

No. This is a **kit shaped like** what you'd build on top of the SDK,
designed so the entire orchestration runs without a Bot Framework
registration, Azure subscription, or Entra app. The SDK provider seam
(`_dispatch_sdk`) is a documented stub with an implementation sketch
— you wire the real SDK in ~30 lines when you're ready.

The point is to show the **shape** of an SDK build (manifest +
handlers + connectors + channel rendering) without the provisioning
burden of getting Azure set up before you can read the code.

## When would I use this in a real engagement?

Three patterns:

1. **Starter template.** Fork it, swap the manifest + connectors to
   match the client's tenant, point `_dispatch_sdk` at the real SDK,
   ship.
2. **Eval harness for a real build.** Use `evals/run.py`'s shape as
   the template for the client's own behaviour gates. CI gating on
   intent + shape + citation is the part most teams skip and most
   regret.
3. **Tutorial for a client.** When explaining the SDK path to a
   stakeholder who's only seen Copilot Studio's no-code GUI, this
   kit gives you a runnable thing to demo without "we need to
   provision Azure first" friction.

## How is this different from `copilot-studio-support-agent`?

`copilot-studio-support-agent` is the **no-code** path — topics,
knowledge connectors, the Copilot grounding layer, all built in the
hosted Studio GUI. Same intent + connector + escalation pattern,
different deployment substrate.

This kit is the **SDK path** — Python, your own loop, typed
handlers, your own manifest, your own connectors. Same architectural
shape, different runtime.

Most M365 consultant work is one of those two paths. Knowing both
is the differentiator — the no-code path scales fast for simple
agents; the SDK path is what you reach for when the agent needs
custom logic, multi-channel rendering, or external system
integration.

## How is this different from `claude-agent-sdk-example`?

`claude-agent-sdk-example` is the same orchestration pattern (loop +
provider seam + tools + memory + grader) but built around the
**Claude Agent SDK** — the agent lives outside M365 and calls into
M365 via tools.

This kit lives **inside** M365 — the agent IS the Teams bot / Outlook
reply flow / Copilot canvas card. Different deployment surface,
different SDK, same architectural pattern (declarative manifest +
imperative handlers + channel-aware rendering).

A complete portfolio usually has one of each because clients ask for
both shapes.

## How is this different from `m365-audit-mcp`?

That's an **MCP server** — it exposes M365 audit data as tools
external agents can call. This kit is an **agent** that lives inside
M365 and calls M365 connectors itself.

The two compose. A production deployment might run an instance of
this kit (as the Teams agent) that calls into an instance of
m365-audit-mcp (over MCP) for the audit data. Different layers of
the same stack.

## Why 5 intents and not 50?

Demonstration breadth, not real-world coverage. The five intents
cover the **shape categories** a real agent has:

- `find_meeting` — calendar lookup (read connector)
- `lookup_person` — directory lookup (read connector with search)
- `copilot_adoption` — reporting (aggregate connector)
- `policy_question` — RAG-shaped (search + snippet)
- `escalate_to_human` — handoff (no connector, side-effect payload)

A real engagement might have 20-50 intents but they all fall into
these shape categories. The pattern scales by adding more entries to
the manifest, not by rebuilding the loop.

## How does this handle authentication?

The kit doesn't, intentionally — that's the SDK provider's job. The
real M365 Agents SDK handles:

- **Inbound** auth (Bot Framework signs incoming activities; the SDK
  verifies)
- **Outbound** auth to Graph (delegated for user-scoped calls,
  client-credentials for app-scoped reports)

When you wire `_dispatch_sdk`, you'll be using the SDK's auth
helpers + `msal` for Graph tokens. The kit's `connectors.py`
becomes the auth boundary — each function acquires its token before
calling Graph.

## Why is the intent matcher substring-based?

For determinism in CI + reproducible Pages demos. A real production
agent would use:

- **CLU / LUIS** for native M365 NLU
- **LLM-based classification** (Claude or GPT) for fuzzy intent
  picking with confidence scores

The seam is `manifest.find_intent(message)` — replace its body, the
agent loop doesn't care.

## Can the agent learn / fine-tune across conversations?

Out of scope for the kit. Production deployments typically use:

- **Conversation analytics** to find unmatched intents and prioritize
  adding them
- **A/B testing of intent variants** to find the right phrasing
- **Confidence threshold tuning** on the LLM classifier (when it's
  used)

The kit's `Conversation.history` log is the foundation — every turn
records what was asked, what intent matched, and what was returned.
Pipe that into Application Insights or a custom telemetry store
and you have the data needed for all three.

## How does the Copilot canvas channel work?

When an M365 agent is invoked through Copilot's "extend with
plugins" surface, Copilot routes the user message to the agent and
expects an Adaptive Card payload back, which Copilot renders inline
in its canvas.

This kit's `_render` for `card` style produces the Adaptive Card
JSON. A real deployment hands that to the SDK's
`turn_context.send_activity()` and Copilot's canvas handles the rest.

## How long until the SDK provider sketch is fully implemented?

Deliberately left as an exercise — about 30 lines of SDK glue.
Implementing it would tie the kit to a specific SDK version + Azure
provisioning steps, making it look "done" in a way that hides the
seam. The point is that the seam is one method; you wire it once
for your deployment.

The SDK's official samples have the `ActivityHandler` pattern spelled
out — the only translation needed is calling `HANDLER_REGISTRY[name]`
inside `on_message_activity` and sending the rendered payload via
`send_activity`.
