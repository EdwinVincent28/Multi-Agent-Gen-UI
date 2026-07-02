from typing import TypedDict, Optional

class GraphState(TypedDict):
    """
    Represents the shared state passed between the LangGraph agents.
    """
    raw_data: str
    clean_data: Optional[str]
    insights: Optional[str]
    ui_code: Optional[str]
    errors: Optional[str]