# Manifest walkthrough

A guided tour of the default manifest, top-to-bottom.

```python
default_manifest() -> Manifest
```

returns a `Manifest` with:

## 3 channels

| Channel | `response_style` | Why |
|---|---|---|
| `teams` | `chat` | Most common M365 surface; plain text + footer citation |
| `outlook` | `email` | Async, durable, signed; HTML body + Re: subject |
| `copilot-canvas` | `card` | Inline in Copilot; Adaptive Card JSON |

Adding a channel: one entry. Adding a channel that needs a new
response shape: one entry + one branch in `Agent._render`.

## 5 intents

Each intent declares:
- **name** — referenced by the eval suite and the handler registry
- **triggers** — case-insensitive substring phrases (real SDK would
  use LUIS or LLM classification)
- **handler** — function name to dispatch to
- **required_connectors** — declared connector names the handler
  needs; `validate()` enforces

| Intent | Connector | What it does |
|---|---|---|
| `find_meeting` | `graph_calendar` | Returns the next event on the user's calendar |
| `lookup_person` | `graph_directory` | Searches Entra ID by name/email/department |
| `copilot_adoption` | `graph_reports` | Returns tenant-wide Copilot usage snapshot |
| `policy_question` | `sharepoint_search` | RAG-shaped: snippet from the most relevant policy doc |
| `escalate_to_human` | (none) | Returns a handoff payload to the helpdesk queue |

## 4 connectors

| Connector | Scopes | Replaces in production |
|---|---|---|
| `graph_calendar` | `Calendars.Read` | `GET /me/calendarView` |
| `graph_directory` | `Directory.Read.All` | `GET /users?$search=...` |
| `graph_reports` | `Reports.Read.All` | `GET /reports/copilotUsage` |
| `sharepoint_search` | `Sites.Read.All` | `POST /search/query` |

Each is a mock today; the production swap replaces the body of the
corresponding function in `connectors.py` with the real Graph call.
The shape returned is what the production swap must preserve.

## Customizing for a new tenant

Most engagements need:

1. **More intents.** Tenant-specific asks (book a room, file a
   helpdesk ticket, submit a PTO request). Each one is: manifest +
   handler + registry entry.

2. **More connectors.** Things the agent reads from or writes to
   (ServiceNow, custom line-of-business APIs, Power BI datasets).
   Each one: manifest entry + module in `connectors.py`.

3. **Channel mix.** Maybe SMS instead of Outlook. Maybe a voice
   channel for Teams Phone. Each channel: manifest entry + (if new
   shape) renderer branch.

The manifest is the spec sheet. Anything you can declare there, the
agent loop will route correctly without code changes to the loop
itself.
