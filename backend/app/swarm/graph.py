import os
from redis.asyncio import Redis as AsyncRedis
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.redis.aio import AsyncRedisSaver
from dotenv import load_dotenv

from app.swarm.state import GraphState
from app.swarm.agents.data_engineer import data_engineer_node
from app.swarm.agents.analyst import analyst_node
from app.swarm.agents.frontend_engineer import frontend_engineer_node

from app.services.memory_service import retrieve_similar_dashboard

load_dotenv()

redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
redis_client = AsyncRedis.from_url(redis_url)
memory_saver = AsyncRedisSaver(redis_client=redis_client)

def semantic_memory_node(state: GraphState):
    """Queries Qdrant for past dashboards to inject as structural context."""
    print("--- SEARCHING SEMANTIC MEMORY ---")

    search_query = state.get("user_prompt")

    if search_query:
        past_ui_code = retrieve_similar_dashboard(str(search_query))
        
        if past_ui_code:
            return {"ui_code": past_ui_code}
            
    return {}

def build_graph():
    def entry_router(state: GraphState):
        if state.get("user_prompt"):
            return "semantic_memory"
        return "data_engineer"

    workflow = StateGraph(GraphState)

    workflow.add_node("data_engineer", data_engineer_node)
    workflow.add_node("analyst", analyst_node)
    workflow.add_node("semantic_memory", semantic_memory_node)
    workflow.add_node("frontend_engineer", frontend_engineer_node)

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
    workflow.add_edge("semantic_memory", "frontend_engineer")
    workflow.add_edge("frontend_engineer", END)

    return workflow.compile(checkpointer=memory_saver)

swarm_graph = build_graph()