import asyncio
from datetime import datetime

from langchain_core.prompts import ChatPromptTemplate
from loguru import logger

from app.core.llm import get_llm, extract_text_content
from app.services.memory_service import retrieve_twitch_context

QA_SYSTEM_PROMPT = """You are answering questions about a live Twitch stream, based on real, recorded data from that stream (viewer counts, chat activity, and chat excerpts).

RULES:
1. Only use the CONTEXT below to answer — never invent numbers or events that aren't in it.
2. If the context doesn't actually contain what's needed to answer, say so plainly rather than guessing.
3. Be concise and conversational, like a quick chat reply — not a formal report.
4. You may reference approximate times from the context (e.g. "around 14:32") when relevant.
5. Do NOT use markdown formatting of any kind — no asterisks for bold/italics, no bullet points, no headers, no backticks. Write plain, natural sentences only, exactly as you would type a normal chat message. This answer is displayed as plain text, so markdown symbols would show up as literal characters instead of being rendered.

CONTEXT:
{context}"""


def _format_context(chunks: list[dict]) -> str:
    lines = []
    for chunk in chunks:
        start = datetime.fromtimestamp(chunk["window_start"]).strftime("%H:%M:%S")
        end = datetime.fromtimestamp(chunk["window_end"]).strftime("%H:%M:%S")
        label = "Stats" if chunk["type"] == "stats" else "Chat excerpt"
        lines.append(f"[{label}, {start}-{end}]: {chunk['text']}")
    return "\n\n".join(lines)


async def answer_twitch_question(session_id: str, question: str) -> dict:
    """
    Answers a question about a live Twitch session using RAG: retrieves
    the most relevant indexed context for THIS session only (never
    across sessions)
    """
    chunks = await asyncio.to_thread(retrieve_twitch_context, session_id, question, 5)

    if not chunks:
        return {
            "answer": (
                "I don't have enough recorded data yet to answer that — "
                "try again in a few minutes once more of the stream has "
                "been indexed."
            ),
            "has_context": False,
            "sources": [],
        }

    context_text = _format_context(chunks)

    prompt = ChatPromptTemplate.from_messages([
        ("system", QA_SYSTEM_PROMPT),
        ("user", "{question}")
    ])

    llm = get_llm(temperature=0.1, thinking_level="low")
    chain = prompt | llm

    response = chain.invoke({"context": context_text, "question": question})
    answer = extract_text_content(response.content)

    logger.info(
        f"[TWITCH QA] session={session_id} question={question!r} chunks_used={len(chunks)}"
    )

    return {
        "answer": answer,
        "has_context": True,
        "sources": [
            {
                "type": c["type"],
                "window_start": c["window_start"],
                "window_end": c["window_end"],
                "score": c["score"],
            }
            for c in chunks
        ],
    }