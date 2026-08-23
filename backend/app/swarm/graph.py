import os
import time
from redis.asyncio import Redis as AsyncRedis
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.redis.aio import AsyncRedisSaver
from dotenv import load_dotenv
from loguru import logger

from app.swarm.state import GraphState
from app.swarm.agents.data_engineer import data_engineer_node
from app.swarm.agents.analyst import analyst_node
from app.swarm.agents.frontend_engineer import frontend_engineer_node
from app.swarm.agents.devops_agent import devops_agent_node
from app.swarm.agents.evaluator import evaluator_node 
from app.swarm.agents.vision_analyst import vision_analyst_node

from app.services.memory_service import retrieve_similar_dashboard

load_dotenv()

redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
redis_client = AsyncRedis.from_url(redis_url)
memory_saver = AsyncRedisSaver(redis_client=redis_client)

ENABLE_EVAL_GATE = True 

def semantic_memory_node(state: GraphState):
    """Queries Qdrant for past dashboards to inject as structural context."""
    logger.info("--- SEARCHING SEMANTIC MEMORY ---")

    search_query = state.get("user_prompt")

    if search_query:
        past_ui_code = retrieve_similar_dashboard(str(search_query))
        
        if past_ui_code:
            return {"ui_code": past_ui_code}
            
    return {}

def build_graph():
    def entry_router(state: GraphState):
        if "telemetry" not in state or not state["telemetry"]:
            state["telemetry"] = {
                "start_time": time.time(),
                "baseline_latency": 0.0,
                "total_latency": 0.0,
                "baseline_tokens": 0,
                "total_tokens": 0,
                "task_success": False
            }
            
        if state.get("user_prompt"):
            return "semantic_memory"
        return "data_engineer"

    workflow = StateGraph(GraphState)

    workflow.add_node("data_engineer", data_engineer_node)
    workflow.add_node("analyst", analyst_node)
    workflow.add_node("semantic_memory", semantic_memory_node)
    workflow.add_node("Vision Analyst", vision_analyst_node)
    workflow.add_node("frontend_engineer", frontend_engineer_node)
    workflow.add_node("devops_agent", devops_agent_node)
    workflow.add_node("evaluator", evaluator_node)

    workflow.set_conditional_entry_point(
        entry_router,
        {
            "semantic_memory": "semantic_memory",
            "data_engineer": "data_engineer"
        }
    )

    def route_after_data_cleaning(state: GraphState):
        if state.get("errors"):
            return "end" 
        return "analyst"

    workflow.add_conditional_edges(
        "data_engineer",
        route_after_data_cleaning,
        {"analyst": "analyst", "end": END}
    )

    workflow.add_edge("analyst", "semantic_memory")
    workflow.add_edge("semantic_memory", "vision_analyst") 
    workflow.add_edge("vision_analyst", "frontend_engineer")
    
    def route_after_frontend(state: GraphState):
        if not ENABLE_EVAL_GATE:
            return "end"
        return "evaluator"

    workflow.add_conditional_edges(
        "frontend_engineer",
        route_after_frontend,
        {
            "evaluator": "evaluator",
            "end": END
        }
    )
    
    def route_after_evaluation(state: GraphState):
        if state.get("retry_count", 0) >= 3 or not state.get("eval_feedback"):
            return "end"
        return "frontend_engineer"

    workflow.add_conditional_edges(
        "evaluator",
        route_after_evaluation,
        {
            "frontend_engineer": "frontend_engineer",
            "end": END
        }
    )

    return workflow.compile(checkpointer=memory_saver)

swarm_graph = build_graph()