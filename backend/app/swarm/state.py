from typing import TypedDict, Optional, Any

class GraphState(TypedDict):
    """
    Represents the shared state passed between the LangGraph agents.
    """
    raw_data: str
    clean_data: Any
    insights: Optional[str]
    ui_code: Optional[str]
    user_prompt: Optional[str]
    errors: Optional[str]
    deployment_url: Optional[str]
    eval_feedback: Optional[list[str]]
    retry_count: Optional[int]
    telemetry: Optional[dict[str, Any]]
    uploaded_image_base64: Optional[str]
    ui_blueprint: Optional[str]