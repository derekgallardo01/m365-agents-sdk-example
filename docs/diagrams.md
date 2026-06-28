# Diagrams

GitHub renders Mermaid natively. These render on the README and in this file.

## End-to-end message flow

```mermaid
flowchart LR
    U[Inbound message<br/>Teams / Outlook / Copilot] --> A["Agent.on_message()"]
    A --> M["manifest.find_intent()<br/>(triggers → intent)"]
    M --> D["_dispatch()"]
    D -- stub --> H["HANDLER_REGISTRY[intent]"]
    D -. sdk .-> S["botbuilder ActivityHandler<br/>(yours to wire)"]
    H --> CON{Connector?}
    CON --> CAL[graph_calendar]
    CON --> DIR[graph_directory]
    CON --> REP[graph_reports]
    CON --> SP[sharepoint_search]
    H --> R[Response]
    R --> RD["_render(response, channel)"]
    RD --> OUT[Channel-shaped payload]
    OUT --> CH[Sent back to channel]
```

## Manifest validation lifecycle

```mermaid
sequenceDiagram
    participant CLI as CLI / Agent init
    participant M as Manifest
    participant V as validate()
    participant A as Agent

    CLI->>A: Agent(manifest=...)
    A->>M: manifest.validate()
    M->>V: check intents reference real connectors
    M->>V: check channels list non-empty
    M->>V: check intents list non-empty
    V-->>A: problems list
    alt problems == []
        A-->>CLI: Agent ready
    else any problems
        A-->>CLI: ValueError(...)
    end
```

## Channel rendering branches

```mermaid
flowchart TB
    R["Response<br/>(text, intent, citations)"]
    R --> S{channel.response_style}
    S -- "chat" --> CH["{shape: chat,<br/>text + citation footer}"]
    S -- "email" --> EM["{shape: email,<br/>subject + body_html}"]
    S -- "card" --> CD["{shape: adaptive_card,<br/>AdaptiveCard JSON}"]
    CH --> O[Rendered payload]
    EM --> O
    CD --> O
```

## Stub vs SDK dispatch

```mermaid
flowchart TB
    subgraph Stub["stub provider (default)"]
        direction TB
        S1[Agent._dispatch_stub]
        S2[HANDLER_REGISTRY lookup]
        S3[handler(turn) → Response]
        S1 --> S2 --> S3
    end

    subgraph SDK["sdk provider"]
        direction TB
        C1[Agent._dispatch_sdk]
        C2["botbuilder ActivityHandler<br/>(on_message_activity)"]
        C3[TurnContext-aware dispatch]
        C4[Same HANDLER_REGISTRY entry runs]
        C5[handler(turn) → Response]
        C1 --> C2 --> C3 --> C4 --> C5
    end

    Stub -. "same Response shape" .- SDK
```

The handler is the same code on both paths. Only the message pump
that drove the call differs.

## Conversation state across turns

```mermaid
stateDiagram-v2
    [*] --> Idle: Conversation(user, channel)
    Idle --> Processing: on_message(msg1)
    Processing --> Idle: rendered + logged
    Idle --> Processing: on_message(msg2)
    Processing --> Idle: rendered + logged
    Idle --> Escalated: handoff triggered
    Escalated --> Idle: ticket logged
    Idle --> [*]: conversation ends<br/>(history could persist)
```

## Repo shape

```mermaid
flowchart TB
    R[m365-agents-sdk-example]
    R --> SRC[src/m365_agents_example/]
    SRC --> MAN[manifest.py — declarative]
    SRC --> HND[handlers.py — imperative]
    SRC --> CON[connectors.py — mocked Graph]
    SRC --> AG[agent.py — loop + seam + renderer]
    SRC --> CLI[cli.py — demo + REPL + validator]
    R --> T[tests/]
    T --> TM[test_manifest.py]
    T --> TH[test_handlers.py]
    T --> TA[test_agent.py]
    R --> EV[evals/]
    EV --> GJ[golden.json]
    EV --> ER[run.py]
    R --> DOCS[docs/]
    R --> CI[.github/workflows/ci.yml]
    R --> DK[Dockerfile]
```
