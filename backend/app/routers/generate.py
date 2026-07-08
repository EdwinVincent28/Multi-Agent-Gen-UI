from fastapi import APIRouter, HTTPException, Depends, File, Form, UploadFile
from app.core.deps import get_current_user
from app.models.user import User
from app.models.schemas import GenerationResponse
from app.services.swarm_service import execute_generation_swarm

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

        return GenerationResponse(
            insights=final_state.get("insights"),
            ui_code=final_state.get("ui_code"),
            errors=None
        )

    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))