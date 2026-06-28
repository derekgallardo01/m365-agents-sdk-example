# Getting started

Five minutes to a working M365-shaped agent on your machine, with no
Bot Framework registration and no Azure subscription.

## Install

```bash
git clone https://github.com/derekgallardo01/m365-agents-sdk-example.git
cd m365-agents-sdk-example
pip install -e .
```

Stdlib-only on the default path. The real SDK (`botbuilder-core`) is
optional, installed via `pip install -e ".[m365]"` when you wire the
production path.

## Run the scripted demo

```bash
m365-agents-example
```

Six scripted turns play out across all three channels (Teams chat,
Outlook email reply, Copilot canvas adaptive card). Each one shows
the inbound message, the intent the manifest matched, the channel-
rendered response, and any citations or handoff payload.

## Validate the manifest

```bash
m365-agents-example --validate-manifest
```

This is the static check the real SDK runs at deploy time. Catches
"intent X needs connector Y that doesn't exist" before you ship.

## Interactive REPL

```bash
m365-agents-example --interactive
```

Talk to the agent, switching channels mid-conversation:

```
[teams]> next meeting
[teams]> channel outlook
[outlook]> what's our policy on data residency
[outlook]> channel copilot-canvas
[copilot-canvas]> copilot adoption status
[copilot-canvas]> escalate
```

## Run the tests

```bash
python -m pytest -q
```

25 tests across the manifest, handlers, and agent loop. Stub provider
is deterministic — no network, no API keys, runs in ~50ms.

## Run the evals

```bash
python evals/run.py
```

6 golden cases assert intent matching + channel shape + citation
presence per channel. CI gates on a 100% pass rate.

## Wire to the real M365 Agents SDK

1. Install the optional extra:
   ```bash
   pip install -e ".[m365]"
   ```

2. Provision a Bot Framework registration in Entra ID (one-time):
   - Azure Bot Service → create a new bot
   - Capture the App ID + secret
   - Set messaging endpoint to your hosted endpoint

3. Implement `_dispatch_sdk` in [src/m365_agents_example/agent.py](../src/m365_agents_example/agent.py)
   per the docstring sketch. About 30 lines of glue against
   `botbuilder.core.ActivityHandler` — the same
   `HANDLER_REGISTRY` runs inside the SDK's message pump.

4. Set the env var and run against the live SDK:
   ```bash
   export M365_AGENT_PROVIDER=sdk
   ```

The tests stay green either way because they pin the provider to
`stub` explicitly. You can verify the orchestration without
provisioning Azure infrastructure first.

## Next steps

- [Architecture](architecture.md) — the manifest + dispatcher walkthrough
- [Customization](customization.md) — add a channel, intent, or connector
- [Evaluation](evaluation.md) — gate CI on agent behaviour
