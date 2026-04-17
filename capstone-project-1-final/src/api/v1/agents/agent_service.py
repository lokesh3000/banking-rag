from __future__ import annotations

import json
import os
from typing import Any
from dotenv import load_dotenv

from langchain.agents import create_agent
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_community.chat_message_histories import ChatMessageHistory

from src.api.v1.tools.vector_tool import vector_search_tool
from src.api.v1.tools.fts_tool import fts_search_tool
from src.api.v1.tools.hybrid_tool import hybrid_search_tool

load_dotenv(override=True)

# ---------------------------------------------------------------------------
# 1. LLM
# ---------------------------------------------------------------------------
model = ChatGoogleGenerativeAI(
    model="gemini-3.1-flash-lite-preview",
    google_api_key=os.getenv("GOOGLE_API_KEY"),
    temperature=0,
)

# ---------------------------------------------------------------------------
# 2. System Prompt
# ---------------------------------------------------------------------------
_SYSTEM_PROMPT = """You are an expert Banking & Wealth Advisor.

You have access to three retrieval tools:
vector_search_tool  → best for natural language / conceptual questions
fts_search_tool     → best for codes, IDs, abbreviations, exact keywords
hybrid_search_tool  → best for short or ambiguous queries

Rules:
1. Choose exactly one tool and call it with the original user query.
2. Use ONLY the returned document chunks to answer.
3. Synthesise a clear, concise answer.
4. Always return your final response as a JSON object:
{
    "answer": "your answer here",
    "policy_citations": "citation text or N/A",
    "page": "page number from chunk metadata or N/A",
    "document_name": "document name from chunk metadata or N/A"
}
5. For 'page': use metadata['page'] from the most relevant chunk. If missing, use N/A.
6. For 'document_name': use metadata['source'] or metadata['file_name'] from the most relevant chunk.
Do not add anything outside the JSON.
"""

# ---------------------------------------------------------------------------
# 3. Base agent
# ---------------------------------------------------------------------------
_base_agent = create_agent(
    model=model,
    tools=[vector_search_tool, fts_search_tool, hybrid_search_tool],
    system_prompt=_SYSTEM_PROMPT,
)

# ---------------------------------------------------------------------------
# 4. In-memory chat history store  { session_id → ChatMessageHistory }
# ---------------------------------------------------------------------------
_history_store: dict[str, ChatMessageHistory] = {}

def _get_session_history(session_id: str) -> ChatMessageHistory:
    if session_id not in _history_store:
        _history_store[session_id] = ChatMessageHistory()
    return _history_store[session_id]

# ---------------------------------------------------------------------------
# 5. Wrap with RunnableWithMessageHistory
# ---------------------------------------------------------------------------
agent_with_history = RunnableWithMessageHistory(
    _base_agent,
    _get_session_history,
    input_messages_key="messages",
    history_messages_key="chat_history",
)

# ---------------------------------------------------------------------------
# 6. Helper: extract raw chunks from the last tool call in the message trace
# ---------------------------------------------------------------------------
TOOL_NAMES = {"vector_search_tool", "fts_search_tool", "hybrid_search_tool"}

def _extract_chunks(messages: list) -> list:
    """Return the raw chunk dicts from the most recent tool response."""
    for msg in reversed(messages):
        if getattr(msg, "type", "") == "tool" and getattr(msg, "name", "") in TOOL_NAMES:
            try:
                return json.loads(msg.content)
            except Exception:
                pass
    return []

# ---------------------------------------------------------------------------
# 7. Public entry-point  (same signature our route already calls)
# ---------------------------------------------------------------------------
def ask_agent(query: str, session_id: str, customer_context: dict[str, Any] | None = None) -> dict:
    """Run the RAG agent and return a plain dict the route can use directly."""

    if customer_context:
        context_block = json.dumps(customer_context, indent=2, ensure_ascii=False)
        full_message = f"[Customer Context]\n{context_block}\n\n[Question]\n{query}"
    else:
        full_message = query

    result = agent_with_history.invoke(
        {"messages": [{"role": "user", "content": full_message}]},
        config={
            "configurable": {"session_id": session_id},
            "tags": ["Retail-Banking-agent", "Capstone-Project-1"],
            "metadata": {"user_id": "Team-2", "Feature": "Personal advisor", "env": "dev"},
            "run_name": "Retail-Banking-Agent",
        },
    )

    messages = result.get("messages", [])
    raw_chunks = _extract_chunks(messages)
    print(f"DEBUG: Raw LLM Output: {raw_text}")
    # Build retrieved_chunks list our schema understands
    retrieved_chunks = []
    seen: set = set()
    for doc in raw_chunks:
        if not isinstance(doc, dict):
            continue
        content = doc.get("content", "")
        if content[:100] in seen:
            continue
        seen.add(content[:100])
        meta = doc.get("metadata") or {}
        confidence = doc.get("fts_rank") or doc.get("score") or meta.get("score")
        retrieved_chunks.append({
            "content":   content,
            "file_name": meta.get("source") or meta.get("file_name") or "N/A",
            "page_no":   str(meta.get("page") or meta.get("page_number") or "N/A"),
            "confidence": round(float(confidence), 4) if confidence else None,
            "tool_used": next(
                (getattr(m, "name", "unknown") for m in reversed(messages)
                 if getattr(m, "type", "") == "tool"), "unknown"
            ),
        })

    # Parse the LLM JSON output
    final_msg = messages[-1] if messages else None
    raw_text = getattr(final_msg, "content", "") if final_msg else ""
    if isinstance(raw_text, list):
        raw_text = next((b.get("text", "") for b in raw_text if isinstance(b, dict) and "text" in b), "")

    try:
        output = json.loads(str(raw_text).replace("```json", "").replace("```", "").strip())
    except Exception:
        output = {
            "answer": str(raw_text),
            "policy_citations": "N/A",
            "page": "N/A",
            "document_name": "N/A",
        }

    output["retrieved_chunks"] = retrieved_chunks
    return output


































































































































































































































































































































































    # ghghjjjjjjj
    

































































































































































































































































































































































































































































































# completed