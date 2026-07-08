import os
from redis import Redis
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.redis import RedisSaver
from dotenv import load_dotenv

from app.swarm.state import GraphState
from app.swarm.agents.data_engineer import data_engineer_node
from app.swarm.agents.analyst import analyst_node
from app.swarm.agents.frontend_engineer import frontend_engineer_node

load_dotenv()

redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
redis_client = Redis.from_url(redis_url)
memory_saver = RedisSaver(redis_client=redis_client)

def build_graph():
    workflow = StateGraph(GraphState)

    workflow.add_node("data_engineer", data_engineer_node)
    workflow.add_node("analyst", analyst_node)
    workflow.add_node("frontend_engineer", frontend_engineer_node)

    workflow.set_entry_point("data_engineer")

    def route_after_data_cleaning(state: GraphState):
        if state.get("errors"):
            return "end" 
        return "analyst"

    workflow.add_conditional_edges(
        "data_engineer",
        route_after_data_cleaning,
        {"analyst": "analyst", "end": END}
    )

    workflow.add_edge("analyst", "frontend_engineer")
    workflow.add_edge("frontend_engineer", END)

    return workflow.compile(checkpointer=memory_saver)

swarm_graph = build_graph()