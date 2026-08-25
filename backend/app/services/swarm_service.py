import json
from app.core.threading import build_thread_id
from fastapi import UploadFile
from app.swarm.graph import swarm_graph
from app.models.user import User
from app.core.llm import extract_text_content
from loguru import logger

NODE_STATUS_MESSAGES = {
    "data_engineer": "Parsing your dataset...",
    "analyst": "Analyzing trends and calculating insights...",
    "semantic_memory": "Checking for similar past dashboards...",
    "vision_analyst": "Examining your wireframe...",
    "frontend_engineer": "Writing your dashboard code...",
    "evaluator": "Reviewing the generated code for quality...",
    "devops_agent": "Preparing deployment package...",
}

async def execute_generation_swarm(session_id: str, file: UploadFile, current_user: User, uploaded_image_base64: str = None) -> dict:
    try:
        raw_data_string = await file.read()
        if isinstance(raw_data_string, bytes):
            raw_data_string = raw_data_string.decode('utf-8')

        initial_state = {
            "raw_data": raw_data_string,
            "clean_data": None,
            "insights": None,
            "ui_code": None,
            "errors": None,
            "uploaded_image_base64": uploaded_image_base64,
            "eval_feedback": []
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
            raw_chunk = event["data"]["chunk"].content
            chunk = extract_text_content(raw_chunk)
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


async def stream_generation_swarm(
    session_id: str,
    raw_data_string: str,
    current_user: User,
    uploaded_image_base64: str = None,
):
    """
    Streams the FULL first-generation pipeline (data_engineer -> analyst ->
    semantic_memory -> vision_analyst -> frontend_engineer -> evaluator ->
    possible retries), yielding structured dict events:

      {"type": "status", "node": "vision_analyst", "message": "..."}
      {"type": "code_chunk", "content": "..."}
      {"type": "final", "insights": ..., "ui_code": ..., "data": ...}
      {"type": "error", "message": "..."}

    """
    logger.info(f"--- STREAMING GENERATION FOR SESSION: {session_id} ---")

    initial_state = {
        "raw_data": raw_data_string,
        "clean_data": None,
        "insights": None,
        "ui_code": None,
        "errors": None,
        "uploaded_image_base64": uploaded_image_base64,
        "eval_feedback": []
    }

    thread_id = build_thread_id(current_user.id, session_id)
    config = {"configurable": {"thread_id": thread_id}}

    final_state = None

    announced_nodes = set()

    try:
        async for event in swarm_graph.astream_events(initial_state, config=config, version="v2"):
            kind = event["event"]
            node_name = event.get("metadata", {}).get("langgraph_node")

            if kind == "on_chain_start" and node_name in NODE_STATUS_MESSAGES and node_name not in announced_nodes:
                announced_nodes.add(node_name)
                yield {
                    "type": "status",
                    "node": node_name,
                    "message": NODE_STATUS_MESSAGES[node_name],
                }

            if kind == "on_chat_model_stream" and node_name == "frontend_engineer":
                raw_chunk = event["data"]["chunk"].content
                chunk = extract_text_content(raw_chunk)
                if chunk:
                    yield {"type": "code_chunk", "content": chunk}

            if kind == "on_chain_end" and not node_name:
                output = event.get("data", {}).get("output")
                if isinstance(output, dict) and "telemetry" in output:
                    final_state = output

    except Exception as e:
        logger.error(f"Stream generation error: {e}")
        yield {"type": "error", "message": str(e)}
        return

    if final_state is None:
        yield {"type": "error", "message": "Generation finished without producing a result."}
        return

    if final_state.get("errors"):
        yield {"type": "error", "message": str(final_state["errors"])}
        return

    logger.info("\n=== END-TO-END TELEMETRY (STREAM GENERATION) ===")
    logger.info(json.dumps(final_state.get("telemetry", {}), indent=2))
    if final_state.get("retry_count"):
        logger.info(f"Retries triggered: {final_state['retry_count']}")
    logger.info("==========================================\n")

    yield {
        "type": "final",
        "insights": final_state.get("insights"),
        "ui_code": final_state.get("ui_code"),
        "data": final_state.get("clean_data"),
    }