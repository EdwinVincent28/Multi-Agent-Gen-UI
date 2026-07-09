from fastapi import APIRouter, HTTPException, Depends, File, Form, UploadFile, WebSocket, WebSocketDisconnect
from app.core.deps import get_current_user
from app.models.user import User
from app.models.schemas import GenerationResponse, ChatRequest
from app.services.swarm_service import execute_generation_swarm, execute_chat_swarm, stream_chat_swarm
import json
from app.core.security import SECRET_KEY, ALGORITHM
import jwt
from sqlalchemy.orm import Session
from app.core.database import get_db

router = APIRouter(prefix="/api/v1", tags=["Generation"])

@router.post("/generate", response_model=GenerationResponse)
async def generate_dashboard(
    session_id: str = Form(..., description="Unique ID for the conversation thread"),
    file: UploadFile = File(..., description="The CSV or JSON file uploaded by the user"),
    current_user: User = Depends(get_current_user)
):
    """
    Receives an uploaded data file, triggers the LangGraph swarm, and returns the generated UI.
    Requires a valid JWT Bearer token.
    """
    try:
        final_state = await execute_generation_swarm(session_id, file, current_user)

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
async def chat_with_dashboard(
    request: ChatRequest,
    current_user: dict = Depends(get_current_user) 
):
    """
    Takes a user prompt, retrieves the LangGraph state from Redis,
    and asks the Frontend Engineer to modify the UI.
    """
    try:
        final_state = await execute_chat_swarm(request.session_id, request.prompt, current_user)

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
    
@router.websocket("/ws/chat/{session_id}")
async def websocket_chat_endpoint(
    websocket: WebSocket, 
    session_id: str,
    db: Session = Depends(get_db)
):
    """
    Establishes a persistent, bi-directional WebSocket connection.
    Streams the generated React code back to the client in real-time.
    """
    await websocket.accept()
    
    try:
        data = await websocket.receive_json()
        token = data.get("token")
        prompt = data.get("prompt")
        
        if not token or not prompt:
            await websocket.send_text("Error: Missing token or prompt")
            await websocket.close(code=1008)
            return

        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            email = payload.get("sub")
            if email is None:
                raise ValueError("Token payload missing sub (email)")
            
            current_user = db.query(User).filter(User.email == email).first()
            if not current_user:
                raise ValueError("User not found in database")

        except jwt.ExpiredSignatureError:
            await websocket.send_text("Error: Token expired")
            await websocket.close(code=1008)
            return
        except Exception as e:
            await websocket.send_text(f"Error validating token: {str(e)}")
            await websocket.close(code=1008)
            return

        async for chunk in stream_chat_swarm(session_id, prompt, current_user):
            await websocket.send_text(chunk)

        await websocket.send_text("<END_OF_STREAM>")
        
    except WebSocketDisconnect:
        print(f"WebSocket disconnected gracefully for session {session_id}")
    except Exception as e:
        import traceback
        print("\n--- FULL WEBSOCKET TRACEBACK ---")
        traceback.print_exc()
        print("--------------------------------\n")
        
        # Using repr(e) instead of str(e) forces Python to print the exact Error Class name 
        # even if it doesn't have a string message attached to it.
        await websocket.send_text(f"Fatal Error: {repr(e)}")
        await websocket.close(code=1011)