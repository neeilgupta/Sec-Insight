"""
SessionManager — multi-turn conversation memory with contextual compression.

Storage
-------
Each session is a SessionState dataclass:
  - recent  : last MAX_HISTORY (6) messages, i.e. 3 full user+assistant turns
  - summary : GPT-4o-generated string summarising all older turns ("" until first compression)

The summary is stored as a plain string and wrapped into a system message only at
get_history() time. This keeps compression logic out of the read path.

get_history(session_id) returns a ready-to-use list of message dicts:
  [{"role": "system", "content": "<summary>"},   # only present when summary != ""
   {"role": "user",   "content": "..."},
   {"role": "assistant", "content": "..."},
   ...]                                           # up to MAX_HISTORY recent messages

The caller prepends its own RAG system prompt and appends the new user query;
it does not interact with compression at all.

4-turn conversation walk-through
---------------------------------
After Turn 1  (2 msgs):   recent=[U1,A1],                 summary=""
After Turn 2  (4 msgs):   recent=[U1,A1,U2,A2],           summary=""
After Turn 3  (6 msgs):   recent=[U1,A1,U2,A2,U3,A3],     summary=""  <- at capacity

Turn 4 -- U4 appended (len->7, compression fires):
  overflow=[U1], keep=[A1,U2,A2,U3,A3,U4]
  summary = GPT-4o("summarise [U1]")
  ->  "User asked about AAPL net sales ($391.0B)..."

Turn 4 -- A4 appended (len->7 again, compression fires again):
  overflow=[A1], keep=[U2,A2,U3,A3,U4,A4]
  summary = GPT-4o("extend existing summary with [A1]")
  ->  "User asked about AAPL net sales ($391.0B)... The assistant confirmed..."

get_history() after Turn 4:
  [
    {"role": "system",    "content": "User asked about AAPL net sales ($391.0B)..."},
    {"role": "user",      "content": "<U2>"},
    {"role": "assistant", "content": "<A2>"},
    {"role": "user",      "content": "<U3>"},
    {"role": "assistant", "content": "<A3>"},
    {"role": "user",      "content": "<U4>"},
    {"role": "assistant", "content": "<A4>"},
  ]
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from dotenv import load_dotenv
from openai import AsyncOpenAI

load_dotenv()

logger = logging.getLogger(__name__)

MAX_HISTORY = 6       # messages (3 user+assistant turns)
SUMMARY_MODEL = "gpt-4o-mini"

_openai = AsyncOpenAI()  # module-level singleton -- matches query.py pattern

# ---------------------------------------------------------------------------
# Summarisation prompt
# ---------------------------------------------------------------------------

_SUMMARIZE_SYSTEM = (
    "You are a conversation summarizer for a financial research assistant. "
    "Produce a concise factual summary. "
    "You MUST preserve: all numerical figures (revenue, margins, EPS, etc.), "
    "ticker symbols (e.g. AAPL, MSFT), filing types (10-K, 10-Q), "
    "fiscal year references, and any specific dates or periods mentioned. "
    "Write in third person (e.g. 'The user asked...', 'The assistant explained...'). "
    "Be brief but complete -- do not omit any financial data point."
)


def _build_compress_prompt(
    overflow: list[dict],
    existing_summary: str,
) -> list[dict]:
    turns_text = "\n".join(
        f"{m['role'].upper()}: {m['content']}" for m in overflow
    )
    if existing_summary:
        user_content = (
            f"EXISTING SUMMARY:\n{existing_summary}\n\n"
            f"NEW TURNS TO INCORPORATE:\n{turns_text}\n\n"
            "Extend the existing summary to include these new turns. "
            "Return only the updated summary text."
        )
    else:
        user_content = (
            f"TURNS TO SUMMARIZE:\n{turns_text}\n\n"
            "Return a concise summary of these turns."
        )
    return [
        {"role": "system", "content": _SUMMARIZE_SYSTEM},
        {"role": "user", "content": user_content},
    ]


async def _compress(overflow: list[dict], existing_summary: str) -> str:
    """Call GPT-4o to fold overflow turns into existing_summary.

    On failure, logs the exception and returns existing_summary unchanged so
    the calling request is not broken by a transient API error.
    """
    messages = _build_compress_prompt(overflow, existing_summary)
    try:
        response = await _openai.chat.completions.create(
            model=SUMMARY_MODEL,
            messages=messages,
            temperature=0.0,  # deterministic -- summaries must be factual
        )
        return response.choices[0].message.content.strip()
    except Exception:
        logger.exception("SessionManager: compression failed; retaining existing summary")
        return existing_summary


# ---------------------------------------------------------------------------
# Storage
# ---------------------------------------------------------------------------


@dataclass
class SessionState:
    recent: list[dict] = field(default_factory=list)
    summary: str = ""


# ---------------------------------------------------------------------------
# SessionManager
# ---------------------------------------------------------------------------


class SessionManager:
    """Multi-turn conversation memory with incremental contextual compression."""

    def __init__(self) -> None:
        self._store: dict[str, SessionState] = {}

    def get_history(self, session_id: str) -> list[dict]:
        """Return a ready-to-use message list for session_id.

        Returns an empty list for unknown or anonymous sessions.
        If a compression summary exists it is prepended as a system message
        so the LLM always has the compressed context available.
        """
        state = self._store.get(session_id)
        if state is None:
            return []
        messages: list[dict] = []
        if state.summary:
            messages.append({"role": "system", "content": state.summary})
        messages.extend(state.recent)
        return messages

    async def add_message(self, session_id: str, role: str, content: str) -> None:
        """Append a message to session history and compress if needed.

        Compression fires whenever len(recent) exceeds MAX_HISTORY after the
        append. The oldest messages are summarised via GPT-4o and folded into
        state.summary; recent is trimmed to MAX_HISTORY.

        No-op for empty session_id (anonymous requests).
        """
        if not session_id:
            return
        if session_id not in self._store:
            self._store[session_id] = SessionState()
        state = self._store[session_id]
        state.recent.append({"role": role, "content": content})
        if len(state.recent) > MAX_HISTORY:
            overflow = state.recent[:-MAX_HISTORY]
            state.recent = state.recent[-MAX_HISTORY:]
            state.summary = await _compress(overflow, state.summary)

    def clear_session(self, session_id: str) -> None:
        """Delete all memory for session_id. No-op if unknown."""
        self._store.pop(session_id, None)


# Module-level singleton -- imported by query.py
session_manager = SessionManager()
