from fastapi import APIRouter, HTTPException, Depends, File, Form, UploadFile
from app.core.deps import get_current_user
from app.models.user import User
from app.models.schemas import GenerationResponse, ChatRequest
from app.services.swarm_service import execute_generation_swarm, execute_chat_swarm
import json

router = APIRouter(prefix="/api/v1", tags=["Generation"])

@router.post("/generate", response_model=GenerationResponse)
def generate_dashboard(
    session_id: str = Form(..., description="Unique ID for the conversation thread"),
    file: UploadFile = File(..., description="The CSV or JSON file uploaded by the user"),
    current_user: User = Depends(get_current_user)
):
    """
    Receives an uploaded data file, triggers the LangGraph swarm, and returns the generated UI.
    Requires a valid JWT Bearer token.
    """
    try:
        final_state = execute_generation_swarm(session_id, file, current_user)

        if final_state.get("errors"):
            raise ValueError(final_state["errors"])

        parsed_data = final_state.get("clean_data")

        return GenerationResponse(
            insights=final_state.get("insights"),
            ui_code=final_state.get("ui_code"),
            data=parsed_data,
            errors=None
        )

    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/chat", response_model=GenerationResponse)
def chat_with_dashboard(
    request: ChatRequest,
    current_user: dict = Depends(get_current_user) 
):
    """
    Takes a user prompt, retrieves the LangGraph state from Redis,
    and asks the Frontend Engineer to modify the UI.
    """
    try:
        final_state = execute_chat_swarm(request.session_id, request.prompt, current_user)

        if final_state.get("errors"):
            raise ValueError(final_state["errors"])

        parsed_data = final_state.get("clean_data")

        return GenerationResponse(
            insights=final_state.get("insights"),
            ui_code=final_state.get("ui_code"),
            data=parsed_data,
            errors=None
        )

    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        print(f"Chat Endpoint Error: {e}")
        raise HTTPException(status_code=500, detail="An error occurred while updating the dashboard.")