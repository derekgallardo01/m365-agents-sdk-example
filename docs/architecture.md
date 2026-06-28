# Architecture

This kit mirrors the M365 Agents SDK's separation: **declarative
manifest** (what the agent does) is independent from **imperative
handlers** (how it does it) which are independent from the **runtime**
(message pump + channel routing). The kit's runtime is a stub that
talks to the same handlers; production swap replaces the runtime
without touching the manifest or handlers.

## The lifecycle of one message

```
Inbound message (Teams / Outlook / Copilot)
    -> Agent.on_message(conversation, message)
        -> manifest.find_intent(message)           # routing
        -> Agent._dispatch(intent.handler, turn)   # provider seam
            -> stub: HANDLER_REGISTRY[handler](turn)
            -> sdk:  hands off to botbuilder ActivityHandler
        -> handler reads/writes via connectors
        -> handler returns Response
    -> Agent._render(response, channel)            # channel-aware shape
    -> Conversation.history.append(...)
    -> Rendered payload back to the caller
```

## The three layers

### 1. Manifest (declarative)

[src/m365_agents_example/manifest.py](../src/m365_agents_example/manifest.py)
exports `Channel`, `Connector`, `Intent`, and `Manifest`. The
default manifest declares:

- **3 channels** — teams (chat), outlook (email), copilot-canvas (card)
- **5 intents** — find_meeting, lookup_person, copilot_adoption,
  policy_question, escalate_to_human
- **4 connectors** — graph_calendar, graph_directory, graph_reports,
  sharepoint_search

`manifest.validate()` catches:
- Intents pointing at undeclared connectors (typos)
- Empty channel/intent lists (broken manifests)

This is the static check the real SDK runs at deploy time. Run it
explicitly with `m365-agents-example --validate-manifest`.

### 2. Handlers (imperative)

[src/m365_agents_example/handlers.py](../src/m365_agents_example/handlers.py)
exports a `Turn` (inbound) and a `Response` (outbound) shape plus
five handler functions. Each handler:

- Takes a `Turn` (user_id, message, channel)
- Calls one or more connectors
- Returns a `Response` (text + intent + citations + optional handoff)

Handlers are **channel-agnostic**. They return a logical response;
the rendering happens later. This is why a handler can be tested in
isolation (`tests/test_handlers.py`) without instantiating the agent.

The `HANDLER_REGISTRY` dict maps handler names (declared in the
manifest) to functions. New intent = add to manifest + add to
registry. Done.

### 3. Connectors (mocked M365 surfaces)

[src/m365_agents_example/connectors.py](../src/m365_agents_example/connectors.py)
fakes Microsoft Graph + SharePoint search with realistic shapes:

| Connector | Real-world equivalent | Mock-data shape |
|---|---|---|
| `graph_calendar` | `GET /me/calendarView` | Calendar event with id/subject/start/end/attendees |
| `graph_directory` | `GET /users?$search=...` | User with id/displayName/mail/department/jobTitle |
| `graph_reports` | `GET /reports/copilotUsage` | Tenant + license count + active users + top apps |
| `sharepoint_search` | `POST /search/query` | Doc id + snippet + relevance score |

The shape returned is what the production swap needs to preserve.
Replace the body with `aiohttp`+`msal` Graph calls; callers don't
change.

## The provider seam

```python
def _dispatch(self, handler_name, turn):
    if self.provider == "sdk":
        return self._dispatch_sdk(handler_name, turn)
    return self._dispatch_stub(handler_name, turn)
```

Both branches end up calling the same `HANDLER_REGISTRY[handler]`.
The difference is which **message pump** drove the dispatch:

- **Stub** — the kit's in-process loop (CLI, tests, evals, Pages demo)
- **SDK** — the real `ActivityHandler` pipeline (Azure Bot Service →
  channel adapter → SDK → ActivityHandler.on_message_activity)

Either way, the handler runs the same code and returns the same
Response. The channel rendering layer doesn't know which path
produced it. That's why you can develop and CI the orchestration
without provisioning Azure infrastructure.

## Channel-aware rendering

The same `Response` becomes three different payloads depending on
the channel:

| Channel | Output shape | Notes |
|---|---|---|
| `teams` | `{shape: chat, text: "...", citations: [...]}` | Citations rendered as `_(sources: ...)_` footer |
| `outlook` | `{shape: email, subject: "Re: ...", body_html: "<p>...</p>"}` | HTML body, structured signature |
| `copilot-canvas` | `{shape: adaptive_card, card: {AdaptiveCard JSON}}` | Renders inside Copilot's canvas |

This is the **second** seam most agent kits get wrong — they hardcode
"return a string" everywhere, then need a rewrite when product asks
for cards or email. The renderer is one method
(`Agent._render`); adding a fourth channel adds one branch.

## Conversation state

Per-user, per-channel. The kit's `Conversation` is a simple list of
turn dicts; production would persist this in Cosmos DB, Redis, or
the SDK's storage adapter. The kit's tests use it to verify
**multi-turn memory persists within a session** — the same shape
production needs.

## Why a stub at all?

Three reasons:

1. **No Azure subscription to demo.** Reviewers (prospects, peer
   engineers, hiring managers) clone and run in 60 seconds. No
   Entra app, no Bot Framework registration, no provisioning.
2. **CI without secrets.** Tests + evals + scripted demo all run in
   GitHub Actions free minutes. No `AZURE_CREDENTIALS` to manage.
3. **Reproducible Pages demo.** Static rendering on every push
   produces identical output, so the screenshots + portfolio card
   don't drift.
