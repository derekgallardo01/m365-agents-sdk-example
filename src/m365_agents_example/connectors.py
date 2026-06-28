"""Mocked Microsoft Graph / SharePoint connectors.

In an M365 Agents SDK deployment these calls go through `aiohttp`+`msal`
against the real Graph endpoints. The shape returned here matches the
relevant Graph response so a swap to the production connector is purely
the body of each function - no callers change.

This file is the equivalent of the m365-audit-mcp project's `mock_data.py`,
but lifted into the agent runtime so it's available at intent-dispatch
time, not just as a tool.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any


# ---------- graph_calendar ----------------------------------------------------

MOCK_CALENDAR_EVENTS = [
    {"id": "evt-001", "subject": "1:1 with Sarah",
     "start": "2026-06-28T14:00:00Z", "end": "2026-06-28T14:30:00Z",
     "attendees": ["sarah.chen@acme.com"]},
    {"id": "evt-002", "subject": "Copilot pilot kickoff",
     "start": "2026-07-15T15:00:00Z", "end": "2026-07-15T16:00:00Z",
     "attendees": ["copilot-pilot@acme.com"]},
    {"id": "evt-003", "subject": "M365 governance review",
     "start": "2026-06-29T10:00:00Z", "end": "2026-06-29T11:00:00Z",
     "attendees": ["governance@acme.com"]},
]


def get_next_meeting(after: datetime | None = None) -> dict | None:
    """Return the next meeting on the user's calendar after `after`."""
    if after is None:
        after = datetime(2026, 6, 28, 12, 0, 0)
    sortable = sorted(MOCK_CALENDAR_EVENTS, key=lambda e: e["start"])
    for evt in sortable:
        start = datetime.fromisoformat(evt["start"].replace("Z", "+00:00")).replace(tzinfo=None)
        if start >= after:
            return evt
    return None


# ---------- graph_directory --------------------------------------------------

MOCK_DIRECTORY = [
    {"id": "u-001", "displayName": "Sarah Chen", "mail": "sarah.chen@acme.com",
     "department": "Engineering", "jobTitle": "Senior Engineer"},
    {"id": "u-002", "displayName": "Alex Park", "mail": "alex.park@acme.com",
     "department": "Operations", "jobTitle": "Director of Ops"},
    {"id": "u-003", "displayName": "Jordan Lee", "mail": "jordan.lee@acme.com",
     "department": "HR", "jobTitle": "People Partner"},
]


def search_directory(query: str) -> list[dict]:
    q = query.lower().strip()
    return [u for u in MOCK_DIRECTORY
            if q in u["displayName"].lower()
            or q in u["mail"].lower()
            or q in u["department"].lower()]


# ---------- graph_reports ----------------------------------------------------

MOCK_COPILOT_REPORT = {
    "tenant": "acme.onmicrosoft.com",
    "windowDays": 30,
    "totalLicenses": 200,
    "activeUsers": 142,
    "promptsPerActiveUser": 28,
    "topApps": [
        {"app": "Microsoft Teams", "share": 0.41},
        {"app": "Outlook", "share": 0.28},
        {"app": "Word", "share": 0.18},
        {"app": "Excel", "share": 0.09},
        {"app": "PowerPoint", "share": 0.04},
    ],
}


def get_copilot_adoption_report() -> dict:
    """Returns the tenant-wide Copilot adoption snapshot."""
    r = dict(MOCK_COPILOT_REPORT)
    r["adoptionPct"] = round(r["activeUsers"] / r["totalLicenses"], 3)
    r["status"] = ("strong" if r["adoptionPct"] >= 0.7
                   else "growing" if r["adoptionPct"] >= 0.5
                   else "stalled")
    return r


# ---------- sharepoint_search -----------------------------------------------

MOCK_POLICY_DOCS = {
    "data-residency.md": (
        "Data residency: customer tenant data is stored in the EU. "
        "Azure OpenAI calls from Copilot stay within the Microsoft 365 service boundary. "
        "No tenant data leaves the EU for model training."
    ),
    "acceptable-use.md": (
        "Acceptable use: Copilot may not be used to generate code that bypasses authentication, "
        "draft communications to customers without human review, or summarize confidential HR records."
    ),
    "incident-response.md": (
        "Credential compromise procedure: revoke session tokens, rotate password, "
        "require MFA re-registration, audit 14 days of sign-in logs."
    ),
    "data-classification.md": (
        "Data classification: Public, Internal, Confidential, Highly Confidential. "
        "Copilot grounding is allowed against Public and Internal docs only by default."
    ),
}


def search_policies(query: str, k: int = 3) -> list[dict]:
    q = query.lower()
    hits = []
    for doc_id, text in MOCK_POLICY_DOCS.items():
        if q in text.lower():
            score = text.lower().count(q) * 10
            hits.append({"doc": doc_id, "score": score,
                         "snippet": _snippet(text, q)})
    # Word-overlap fallback so multi-word natural-language queries still hit.
    matched = {h["doc"] for h in hits}
    words = [w for w in q.split() if len(w) > 2]
    if words:
        for doc_id, text in MOCK_POLICY_DOCS.items():
            if doc_id in matched:
                continue
            text_lower = text.lower()
            overlap = sum(1 for w in words if w in text_lower)
            if overlap > 0:
                best_word = max(words, key=lambda w: text_lower.count(w))
                hits.append({"doc": doc_id, "score": overlap,
                             "snippet": _snippet(text, best_word)})
    hits.sort(key=lambda h: -h["score"])
    return hits[:k]


def _snippet(text: str, q: str, context: int = 80) -> str:
    lower = text.lower()
    idx = lower.find(q.lower())
    if idx < 0:
        return text[:context].strip()
    start = max(0, idx - context // 2)
    end = min(len(text), idx + len(q) + context // 2)
    return ("..." if start > 0 else "") + text[start:end].strip() + ("..." if end < len(text) else "")
