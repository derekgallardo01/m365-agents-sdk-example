"""The agent loop.

In a real M365 Agents SDK deployment, the loop is provided by the SDK
(it owns the message pump, authentication, and channel routing). The kit
runs the same shape in-process so the tests + Pages demo work without
provisioning a Bot Framework registration:

    Turn -> match_intent -> dispatch_handler -> render_for_channel -> Response

The seam is `Agent._dispatch`, which the SDK provider can override to
hand off to the real SDK pipeline. Everything else - intent matching,
channel rendering, citation tracking, conversation logging - is shared.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any

from . import handlers
from .manifest import Manifest, default_manifest


@dataclass
class Conversation:
    """Per-user conversation state - persists across turns within a session."""
    user_id: str
    channel: str
    history: list[dict] = field(default_factory=list)  # turn -> response pairs


class Agent:
    """A channel-aware M365 agent."""

    def __init__(
        self,
        manifest: Manifest | None = None,
        provider: str | None = None,
    ):
        self.manifest = manifest or default_manifest()
        self.provider = provider or os.environ.get("M365_AGENT_PROVIDER", "stub")
        problems = self.manifest.validate()
        if problems:
            raise ValueError(f"Invalid manifest: {problems}")

    # ----- Public entry point ----------------------------------------------

    def on_message(self, conversation: Conversation,
                   user_message: str) -> dict[str, Any]:
        """Process one inbound message; return the channel-rendered response."""
        # 1. Build the turn (the SDK's TurnContext equivalent).
        turn = handlers.Turn(
            user_id=conversation.user_id,
            user_message=user_message,
            channel=conversation.channel,
        )

        # 2. Intent matching - manifest decides which handler to call.
        intent = self.manifest.find_intent(user_message)
        if intent is None:
            response = handlers.handle_unmatched(turn)
        else:
            response = self._dispatch(intent.handler, turn)

        # 3. Channel-aware rendering. Different surfaces want different shapes.
        rendered = self._render(response, conversation.channel)

        # 4. Log to conversation history.
        conversation.history.append({
            "user": user_message,
            "intent": response.intent,
            "rendered": rendered,
            "citations": response.citations,
            "handoff": response.handoff,
        })
        return rendered

    # ----- The provider seam -----------------------------------------------

    def _dispatch(self, handler_name: str, turn: handlers.Turn) -> handlers.Response:
        """Call the named handler. SDK provider hooks here.

        STUB backend dispatches via the in-process handler registry.
        SDK backend would hand off to the real `ActivityHandler` pipeline
        (which itself receives a TurnContext and produces an activity).
        Either way, the same Response object is returned upstream so the
        channel-renderer doesn't care which path produced it.
        """
        if self.provider == "sdk":
            return self._dispatch_sdk(handler_name, turn)
        return self._dispatch_stub(handler_name, turn)

    def _dispatch_stub(self, handler_name: str,
                       turn: handlers.Turn) -> handlers.Response:
        handler = handlers.HANDLER_REGISTRY.get(handler_name)
        if not handler:
            return handlers.Response(
                text=f"Internal error: handler '{handler_name}' is missing.",
                intent="error", citations=[])
        return handler(turn)

    def _dispatch_sdk(self, handler_name: str,
                      turn: handlers.Turn) -> handlers.Response:
        """Production swap point.

        To wire to the real Microsoft 365 Agents SDK:

            pip install -e ".[m365]"
            from botbuilder.core import ActivityHandler, TurnContext
            class MyAgent(ActivityHandler):
                async def on_message_activity(self, turn_context: TurnContext):
                    intent = self.manifest.find_intent(turn_context.activity.text)
                    response = self._dispatch_stub(intent.handler, _turn_from(turn_context))
                    await turn_context.send_activity(render_for_channel(response, ...))

        The SDK provides the channel routing, auth, and message pump; the
        kit's `handlers.HANDLER_REGISTRY` is what each method calls into.
        Manifest, handlers, and connectors are all reused unchanged.

        Until that's wired, fall back to stub.
        """
        return self._dispatch_stub(handler_name, turn)

    # ----- Channel rendering -----------------------------------------------

    def _render(self, response: handlers.Response, channel: str) -> dict[str, Any]:
        """Format the response for the target channel.

        Teams chat -> plain text + citation footer.
        Outlook -> HTML email body with structured signature.
        Copilot canvas -> adaptive card payload.
        """
        ch = self.manifest.channel(channel)
        style = ch.response_style if ch else "chat"

        cite_text = " · ".join(response.citations) if response.citations else ""

        if style == "email":
            body_html = f"<p>{response.text}</p>"
            if cite_text:
                body_html += f"<p><em>Sources: {cite_text}</em></p>"
            return {
                "channel": channel,
                "shape": "email",
                "subject": f"Re: {response.intent.replace('_', ' ')}",
                "body_html": body_html,
                "intent": response.intent,
                "citations": response.citations,
                "handoff": response.handoff,
            }

        if style == "card":
            card = {
                "type": "AdaptiveCard",
                "version": "1.5",
                "body": [
                    {"type": "TextBlock", "size": "Medium", "weight": "Bolder",
                     "text": response.intent.replace("_", " ").title()},
                    {"type": "TextBlock", "wrap": True, "text": response.text},
                ],
            }
            if cite_text:
                card["body"].append({"type": "TextBlock", "isSubtle": True,
                                     "wrap": True, "text": f"Sources: {cite_text}"})
            return {
                "channel": channel,
                "shape": "adaptive_card",
                "card": card,
                "intent": response.intent,
                "citations": response.citations,
                "handoff": response.handoff,
            }

        # default: chat
        text = response.text
        if cite_text:
            text += f"\n\n_(sources: {cite_text})_"
        return {
            "channel": channel,
            "shape": "chat",
            "text": text,
            "intent": response.intent,
            "citations": response.citations,
            "handoff": response.handoff,
        }
