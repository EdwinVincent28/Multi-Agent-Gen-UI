from app.core.threading import build_thread_id
from fastapi import UploadFile
from app.swarm.graph import swarm_graph
from app.models.user import User

async def execute_generation_swarm(session_id: str, file: UploadFile, current_user: User) -> dict:
    try:
        file_bytes = await file.read()
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

        final_state = await swarm_graph.ainvoke(initial_state, config=config)

        if final_state.get("errors"):
            raise ValueError(final_state["errors"])

        return final_state

    except Exception as e:
        raise Exception(f"Swarm execution failed: {str(e)}")
    finally:
        await file.close()

async def execute_chat_swarm(session_id: str, prompt: str, current_user: User) -> dict:
    print(f"--- TRIGGERING CHAT FOR SESSION: {session_id} ---")

    thread_id = build_thread_id(current_user.id, session_id)
    config = {"configurable": {"thread_id": thread_id}}
    
    final_state = await swarm_graph.ainvoke({"user_prompt": prompt}, config=config)

    return final_state

async def stream_chat_swarm(session_id: str, prompt: str, current_user: User):
    print(f"--- STREAMING CHAT FOR SESSION: {session_id} ---")

    thread_id = build_thread_id(current_user.id, session_id)
    config = {"configurable": {"thread_id": thread_id}}
    
    async for event in swarm_graph.astream_events({"user_prompt": prompt}, config=config, version="v2"):
        kind = event["event"]
        if kind == "on_chat_model_stream":
            chunk = event["data"]["chunk"].content
            if chunk:
                yield chunk