import json
from app.core.threading import build_thread_id
from fastapi import UploadFile
from app.swarm.graph import swarm_graph
from app.models.user import User
from loguru import logger

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

        logger.info("\n=== END-TO-END TELEMETRY (GENERATION) ===")
        logger.info(json.dumps(final_state.get("telemetry", {}), indent=2))
        if final_state.get("retry_count"):
            logger.info(f"Retries triggered: {final_state['retry_count']}")
        logger.info("==========================================\n")

        if final_state.get("errors"):
            raise ValueError(final_state["errors"])

        return final_state

    except Exception as e:
        raise Exception(f"Swarm execution failed: {str(e)}")
    finally:
        await file.close()

async def execute_chat_swarm(session_id: str, prompt: str, current_user: User) -> dict:
    logger.info(f"--- TRIGGERING CHAT FOR SESSION: {session_id} ---")

    thread_id = build_thread_id(current_user.id, session_id)
    config = {"configurable": {"thread_id": thread_id}}
    
    final_state = await swarm_graph.ainvoke({"user_prompt": prompt}, config=config)

    logger.info("\n=== END-TO-END TELEMETRY (CHAT) ===")
    logger.info(json.dumps(final_state.get("telemetry", {}), indent=2))
    if final_state.get("retry_count"):
        logger.info(f"Retries triggered: {final_state['retry_count']}")
    logger.info("==========================================\n")

    return final_state

async def stream_chat_swarm(session_id: str, prompt: str, current_user: User):
    logger.info(f"--- STREAMING CHAT FOR SESSION: {session_id} ---")

    thread_id = build_thread_id(current_user.id, session_id)
    config = {"configurable": {"thread_id": thread_id}}
    
    final_state = None
    
    async for event in swarm_graph.astream_events({"user_prompt": prompt}, config=config, version="v2"):
        kind = event["event"]
        node_name = event.get("metadata", {}).get("langgraph_node")
        
        if kind == "on_chat_model_stream" and node_name == "frontend_engineer":
            chunk = event["data"]["chunk"].content
            if chunk:
                yield chunk

        if kind == "on_chain_end" and not node_name:
            output = event.get("data", {}).get("output")
            if isinstance(output, dict) and "telemetry" in output:
                final_state = output

    if final_state:
        logger.info("\n=== END-TO-END TELEMETRY (STREAM CHAT) ===")
        logger.info(json.dumps(final_state.get("telemetry", {}), indent=2))
        if final_state.get("retry_count"):
            logger.info(f"Retries triggered: {final_state['retry_count']}")
        logger.info("==========================================\n")