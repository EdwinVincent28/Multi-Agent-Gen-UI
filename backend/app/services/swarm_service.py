from app.core.threading import build_thread_id
from fastapi import UploadFile
from app.swarm.graph import swarm_graph
from app.models.user import User

def execute_generation_swarm(session_id: str, file: UploadFile, current_user: User) -> dict:
    """
    Business logic for processing the file and invoking the AI swarm.
    """
    try:
        file_bytes = file.file.read()
        raw_text = file_bytes.decode("utf-8")

        initial_state = {
            "raw_data": raw_text,
            "clean_data": None,
            "insights": None,
            "ui_code": None,
            "errors": None
        }

        thread_id = build_thread_id(current_user.id, session_id)
        config = {"configurable": {"thread_id": thread_id}}

        final_state = swarm_graph.invoke(initial_state, config=config)

        if final_state.get("errors"):
            raise ValueError(final_state["errors"])

        return final_state

    except Exception as e:
        raise Exception(f"Swarm execution failed: {str(e)}")
    finally:
        file.file.close()

def execute_chat_swarm(session_id: str, prompt: str, current_user: User) -> dict:
    """
    Resumes a LangGraph session from Redis and passes the user's prompt 
    to trigger the Frontend Engineer's Edit Mode.
    """
    print(f"--- TRIGGERING CHAT FOR SESSION: {session_id} ---")

    thread_id = build_thread_id(current_user.id, session_id)
    config = {"configurable": {"thread_id": thread_id}}
    final_state = swarm_graph.invoke({"user_prompt": prompt}, config)

    return final_state