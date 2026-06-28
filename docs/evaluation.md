# Evaluation

CI gates on **agent behaviour**, not just code shape. The eval suite
exercises real intent routing + channel rendering against golden
cases.

## What gets checked

Per [evals/golden.json](../evals/golden.json), each case asserts:

1. **`expect_intent`** — did the manifest match the right intent?
2. **`expect_shape`** — did the renderer produce the right channel shape (chat / email / adaptive_card)?
3. **`expect_citation_prefix`** — does the response carry the right connector citation (e.g., `graph_calendar:`)?

A case passes when all three hold. CI fails on anything less than 100%.

## Running

```bash
python evals/run.py
```

Output:

```
Running 6 eval cases against provider=stub

  PASS  teams-next-meeting                intent=True  shape=True  cites=True
  PASS  outlook-policy-question           intent=True  shape=True  cites=True
  PASS  copilot-canvas-adoption           intent=True  shape=True  cites=True
  PASS  teams-lookup-person               intent=True  shape=True  cites=True
  PASS  teams-escalate                    intent=True  shape=True  cites=True
  PASS  teams-unmatched-falls-through     intent=True  shape=True  cites=True

6/6 passed (100%)
```

## Adding a new eval case

Edit `evals/golden.json`:

```json
{
  "id": "outlook-find-meeting",
  "channel": "outlook",
  "message": "what's on my calendar tomorrow",
  "expect_intent": "find_meeting",
  "expect_shape": "email",
  "expect_citation_prefix": "graph_calendar:"
}
```

`expect_citation_prefix` may be `null` if you don't care about
citations for that case (e.g., an `escalate` or `unmatched` case).

## Why a separate eval suite (vs just tests)

Tests verify code shape — "did this function return a dict with these
keys". Evals verify behaviour shape — "did the agent actually route
the right intent and render the right channel shape end-to-end".

These move on different cadences:

- **Tests** change when you refactor an implementation detail.
- **Evals** change when you change what the agent should do.

Mixing them makes both noisier. Keeping them separate lets you ship
a refactor without re-thinking the eval pass rate, and lets you
change behaviour deliberately by editing one JSON file.

## Why this matters for the M365 Agents SDK in particular

In a real SDK deployment, regression sources include:

- **Manifest drift** — you added a new intent and forgot to register
  the handler, so dispatching it falls through to error.
- **Channel rendering drift** — you added a new channel and didn't
  update the renderer, so Outlook messages render as Teams chat.
- **Connector schema drift** — you upgraded a Graph endpoint and the
  response shape changed; the handler still runs but stops citing.

The eval suite catches all three classes at PR time. Tests catch
some but not all of these because tests typically pass mocked
connectors and assert on the handler in isolation.

## Running evals against the real SDK + tenant

Once you've wired `_dispatch_sdk` and pointed connectors at real
Graph endpoints:

```bash
pip install -e ".[m365]"
export M365_AGENT_PROVIDER=sdk
# plus your AZURE_TENANT_ID, AZURE_CLIENT_ID, AZURE_CLIENT_SECRET
python evals/run.py
```

The same cases run; the dispatcher and connectors change. Expect a
few flips (the Graph might return different test data depending on
your tenant); use those flips as the signal for what tenant-specific
fixtures to add.

This is how you watch SDK upgrades: re-run the eval suite after
upgrading `botbuilder-core`, see which cases changed, decide if it's
breakage or expected behaviour change.

## What `--validate-manifest` does (vs evals)

The validator is a **static** check that runs at boot or CLI invoke:

```bash
m365-agents-example --validate-manifest
```

It catches structural problems (missing connectors, empty intent
lists) before any message comes in. Evals catch **runtime** problems
(wrong intent matched, wrong shape rendered). You need both. CI runs
both.
