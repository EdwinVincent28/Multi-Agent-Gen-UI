from langgraph.graph import StateGraph, END
from app.swarm.state import GraphState
from app.swarm.agents.data_engineer import data_engineer_node
from app.swarm.agents.analyst import analyst_node
from app.swarm.agents.frontend_engineer import frontend_engineer_node

def build_graph():
    """
    Constructs the stateful LangGraph workflow routing the user's data 
    through the agent swarm.
    """

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
        {
            "analyst": "analyst",
            "end": END
        }
    )

    workflow.add_edge("analyst", "frontend_engineer")

    workflow.add_edge("frontend_engineer", END)

    return workflow.compile()

swarm_graph = build_graph()