def build_thread_id(user_id: int, session_id: str) -> str:
    """
    Builds the LangGraph checkpointer thread_id from a user and session.
    """
    return f"user_{user_id}_{session_id}"