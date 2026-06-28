# Customization

How to shape this kit for a real M365 deployment.

## Add a new intent

Three steps:

1. **Add to the manifest** in `manifest.py::default_manifest()`:

```python
Intent(
    name="book_room",
    triggers=["book a room", "reserve meeting room", "room booking"],
    handler="handle_book_room",
    required_connectors=["graph_places"],
),
```

2. **Add a handler** in `handlers.py`:

```python
def handle_book_room(turn: Turn) -> Response:
    # Parse the user's room request
    # Call connectors.book_room(...)
    return Response(
        text="I've booked room Aurora at 2pm.",
        intent="book_room",
        citations=["graph_places:room-aurora"],
    )
```

3. **Register the handler**:

```python
HANDLER_REGISTRY = {
    ...,
    "handle_book_room": handle_book_room,
}
```

That's it. The agent loop, channel renderer, tests, and eval harness
all pick up the new intent automatically. Add a test in
`tests/test_handlers.py` and an eval case in `evals/golden.json`
and you're done.

## Add a new channel

Two steps:

1. **Declare it** in the manifest:

```python
Channel("slack", response_style="card"),  # reuse the card renderer
# OR
Channel("voice", response_style="ssml"),  # new shape - add to renderer
```

2. **(If new shape)** add a branch to `Agent._render`:

```python
if style == "ssml":
    return {
        "channel": channel,
        "shape": "ssml",
        "ssml": f"<speak>{html.escape(response.text)}</speak>",
        "intent": response.intent,
        "citations": response.citations,
    }
```

If you reuse an existing `response_style`, no renderer changes
needed — declare it and it routes.

## Add a new connector

Three steps:

1. **Declare it** in the manifest:

```python
Connector("graph_places", ["Place.Read.All"],
          "Read tenant meeting rooms and book them."),
```

2. **Implement the mock** in `connectors.py`:

```python
MOCK_PLACES = [
    {"id": "room-aurora", "displayName": "Aurora", "capacity": 8, "floor": 3},
    # ...
]

def book_room(room_id: str, start: str, end: str) -> dict:
    # ... mock booking logic
    return {"id": "booking-...", "status": "confirmed"}
```

3. **Have intents reference it** — set `required_connectors=["graph_places"]`
   on the intent and `manifest.validate()` will catch it if missing.

For the production swap, replace the mock body with the real Graph
call:

```python
def book_room(room_id, start, end):
    async with graph_client() as g:
        return await g.places[room_id].calendar.events.post({...})
```

Tests + handlers don't change.

## Change the intent matcher

Today's matcher is substring-based (in `manifest.py::find_intent`).
For production you'd typically swap to:

- **CLU / LUIS** — Microsoft's hosted NLU services
- **LLM-based classification** — send the message to a small Claude /
  GPT call with the intent list and let the model pick

Swap is one method:

```python
def find_intent(self, user_message: str) -> Intent | None:
    classification = await llm_classify(user_message, [i.name for i in self.intents])
    return next((i for i in self.intents if i.name == classification), None)
```

The rest of the agent loop doesn't know how the intent was picked.

## Add a third response_style (e.g., voice / SMS)

`agent.py::_render` has three branches today (chat / email / card).
Add a fourth:

```python
if style == "sms":
    # 160-char hard limit, no citations footer (would blow the budget)
    return {"channel": channel, "shape": "sms",
            "text": response.text[:160],
            "intent": response.intent, "citations": []}
```

The handlers don't change — they still return logical `Response`
objects. Only rendering changes.

## Persist conversation state across restarts

The kit's `Conversation.history` lives in memory. Production needs
durable state (Cosmos DB, Redis, or the SDK's BotState adapter):

```python
async def load_conversation(user_id: str, channel: str) -> Conversation:
    snapshot = await cosmos.read_item("conversations", f"{user_id}:{channel}")
    return Conversation(
        user_id=user_id, channel=channel,
        history=snapshot.get("history", []),
    )

async def save_conversation(c: Conversation) -> None:
    await cosmos.upsert_item("conversations", {
        "id": f"{c.user_id}:{c.channel}", "history": c.history,
    })
```

Called at session boundaries in `Agent.on_message`. The kit doesn't
ship this because every deployment has different storage.

## Add an "outcomes" check before responding

Pattern: have the agent self-grade against a rubric before sending
the response, retry if the grade is low. Hook it into `on_message`:

```python
def on_message(self, conversation, user_message):
    # ... existing intent + dispatch ...
    response = self._dispatch(intent.handler, turn)

    # New: self-grade against intent-specific rubric
    if intent.name == "policy_question":
        rubric = ["specific policy doc cited", "actionable"]
        if not self._self_grades(response, rubric):
            # Retry with broader search or escalate
            response = handlers.handle_escalate(turn)

    return self._render(response, conversation.channel)
```

Useful for high-stakes intents (financial, legal, HR) where wrong
answers are worse than no answer.

## Run against a real M365 tenant

The connector mocks (`connectors.py`) are the only files that need
to change. For each connector:

1. Use `msal` to acquire a token (delegated for user-scoped calls,
   client-credentials for app-scoped reports).
2. Replace the mock data return with the actual Graph response.
3. The shape returned must match — the handlers parse specific keys.

A minimum-scope Entra app for the default manifest needs:
`Calendars.Read`, `Directory.Read.All`, `Reports.Read.All`,
`Sites.Read.All`. Add `Place.Read.All` etc. as you add connectors.
