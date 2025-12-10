from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import List, Tuple

from dotenv import load_dotenv
from openai import OpenAI

from src.config import DB_PATH, DEFAULT_HISTORY_K, OPENAI_MODEL, BASE_DIR
from src.rag.retriever import retrieve

# Load .env from project root explicitly to avoid CWD issues (Streamlit, scripts)
load_dotenv(dotenv_path=BASE_DIR / ".env", override=False)


def ensure_db(db_path: Path = DB_PATH) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS chat_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                user_message TEXT NOT NULL,
                assistant_message TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.commit()


def list_sessions(limit: int = 50) -> List[Tuple[str, str | None]]:
    """
    Return list of (session_id, first_user_message) ordered by last activity desc.
    """
    ensure_db()
    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute(
            """
            SELECT
                session_id,
                (
                    SELECT user_message
                    FROM chat_history h2
                    WHERE h2.session_id = h1.session_id
                    ORDER BY id ASC
                    LIMIT 1
                ) AS first_user_message
            FROM chat_history h1
            GROUP BY session_id
            ORDER BY MAX(created_at) DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [(r[0], r[1]) for r in rows]


def delete_all_sessions() -> None:
    """Delete all chat history."""
    ensure_db()
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("DELETE FROM chat_history")
        conn.commit()


def fetch_history(session_id: str, k: int = DEFAULT_HISTORY_K) -> List[Tuple[str, str]]:
    ensure_db()
    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute(
            """
            SELECT user_message, assistant_message
            FROM chat_history
            WHERE session_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (session_id, k),
        ).fetchall()
    rows.reverse()
    return [(r[0], r[1]) for r in rows]


def save_turn(session_id: str, user_message: str, assistant_message: str) -> None:
    ensure_db()
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            INSERT INTO chat_history (session_id, user_message, assistant_message)
            VALUES (?, ?, ?)
            """,
            (session_id, user_message, assistant_message),
        )
        conn.commit()


def build_prompt(user_query: str, context_chunks: List[Tuple[dict, float]], history: List[Tuple[str, str]]) -> List[dict]:
    system_msg = {
        "role": "system",
        "content": "You are an assistant answering questions about Hebrew car reviews from auto.co.il. Use only the provided context. Do not hallucinate.",
    }
    context_lines = []
    for chunk, dist in context_chunks:
        context_lines.append(
            f"- source: {chunk.get('article_title','')} ({chunk.get('article_url','')}) | chunk: {chunk.get('chunk_id')} | score: {dist:.4f}\n{chunk.get('chunk_text','')}"
        )
    context_block = "\n".join(context_lines) if context_lines else "No context retrieved."

    history_msgs: List[dict] = []
    for u, a in history:
        history_msgs.append({"role": "user", "content": u})
        history_msgs.append({"role": "assistant", "content": a})

    messages = [
        system_msg,
        {
            "role": "system",
            "content": f"Context:\n{context_block}",
        },
        *history_msgs,
        {"role": "user", "content": user_query},
    ]
    return messages


def answer(user_query: str, session_id: str) -> tuple[str, List[dict]]:
    ensure_db()
    retrieved = retrieve(user_query)
    history = fetch_history(session_id)
    messages = build_prompt(user_query, retrieved, history)

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY not set")

    client = OpenAI(api_key=api_key)
    completion = client.chat.completions.create(model=OPENAI_MODEL, messages=messages)
    assistant_message = completion.choices[0].message.content

    save_turn(session_id, user_query, assistant_message)

    sources = [
        {
            "article_title": chunk.get("article_title"),
            "article_url": chunk.get("article_url"),
            "chunk_id": chunk.get("chunk_id"),
            "distance": dist,
        }
        for chunk, dist in retrieved
    ]

    return assistant_message, sources

