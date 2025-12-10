from __future__ import annotations

import sys
import uuid
from pathlib import Path

import streamlit as st

# Ensure project root is on path when running as a script
ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.rag.chat_orchestrator import answer, fetch_history, list_sessions, delete_all_sessions  # noqa: E402


def main() -> None:
    st.set_page_config(page_title="Auto RAG (Hebrew)", page_icon="🚗", layout="wide")
    st.title("Auto RAG Chatbot (Hebrew)")
    # RTL support for Hebrew
    st.markdown(
        """
        <style>
        .block-container {direction: rtl; text-align: right;}
        div[data-testid="stChatMessageContent"] {direction: rtl; text-align: right;}
        </style>
        """,
        unsafe_allow_html=True,
    )

    # Sidebar: session management
    with st.sidebar:
        st.header("Conversations")
        existing_sessions = list_sessions()
        if "session_id" not in st.session_state:
            st.session_state.session_id = str(uuid.uuid4())
        # Prepare labels with first question preview
        session_options = ["<new>"] + [sid for sid, _ in existing_sessions]
        session_labels = ["<new session>"] + [
            (preview.strip()[:60] + ("…" if preview and len(preview) > 60 else ""))
            if preview
            else sid
            for sid, preview in existing_sessions
        ]

        def label_for(option: str) -> str:
            if option in session_options:
                return session_labels[session_options.index(option)]
            return "New conversation (empty)"

        if st.button("Start new conversation", type="primary", use_container_width=True):
            st.session_state.session_id = str(uuid.uuid4())
            st.rerun()

        st.subheader("Existing conversations")
        display_sessions = [sid for sid, _ in existing_sessions]
        # Ensure current session appears in the list so radio selection does not override it
        if st.session_state.session_id not in display_sessions:
            display_sessions = [st.session_state.session_id] + display_sessions
        if display_sessions:
            chosen_session = st.radio(
                "Select",
                display_sessions,
                format_func=lambda sid: label_for(sid) if sid in session_options else "New conversation (empty)",
                index=display_sessions.index(st.session_state.session_id),
            )
            if chosen_session != st.session_state.session_id:
                st.session_state.session_id = chosen_session
                st.rerun()
        else:
            st.write("No past conversations yet.")

        active_label = label_for(st.session_state.session_id) if st.session_state.session_id in session_options else "New conversation (empty)"
        st.markdown(f"**Active conversation:** {active_label}")
        if st.button("Delete all past conversations", type="secondary", use_container_width=True):
            delete_all_sessions()
            st.session_state.session_id = str(uuid.uuid4())
            st.success("All conversations deleted.")
            st.rerun()

    session_id = st.session_state.session_id

    # Display chat history
    history = fetch_history(session_id, k=50)
    for user_msg, assistant_msg in history:
        with st.chat_message("user"):
            st.write(user_msg)
        with st.chat_message("assistant"):
            st.write(assistant_msg)

    # Chat input at bottom
    user_query = st.chat_input("Pose ta question (Hebrew de préférence)…")
    if user_query:
        with st.chat_message("user"):
            st.write(user_query)
        with st.spinner("Retrieving and generating..."):
            try:
                reply, sources = answer(user_query.strip(), session_id)
            except Exception as exc:  # pylint: disable=broad-exception-caught
                st.error(f"Error: {exc}")
            else:
                with st.chat_message("assistant"):
                    st.write(reply)
                    if sources:
                        with st.expander("מקורות / Sources"):
                            for src in sources:
                                st.markdown(
                                    f"- **{src.get('article_title','')}** — {src.get('article_url','')} "
                                    f"(chunk: {src.get('chunk_id')}, score: {src.get('distance'):.4f})"
                                )
        # After sending, refresh to show updated history order
        st.rerun()


if __name__ == "__main__":
    main()

