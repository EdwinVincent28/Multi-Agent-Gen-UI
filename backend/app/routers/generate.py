import asyncio
from fastapi import APIRouter, HTTPException, Depends, File, Form, UploadFile, WebSocket, WebSocketDisconnect
from typing import Optional
from app.core.deps import get_current_user
from app.models.user import User
from app.models.schemas import GenerationResponse, ChatRequest
from app.services.swarm_service import (
    execute_generation_swarm,
    execute_chat_swarm,
    stream_chat_swarm,
    stream_generation_swarm,
    stream_twitch_swarm,
)
from app.services.twitch_session import TwitchLiveSession
from app.services.twitch_qa_service import answer_twitch_question
from pydantic import BaseModel
import json
from app.core.security import SECRET_KEY, ALGORITHM
import jwt
from sqlalchemy.orm import Session
from app.core.database import get_db
from loguru import logger

router = APIRouter(prefix="/api/v1", tags=["Generation"])

@router.post("/generate", response_model=GenerationResponse)
async def generate_dashboard(
    session_id: str = Form(..., description="Unique ID for the conversation thread"),
    file: UploadFile = File(..., description="The CSV or JSON file uploaded by the user"),
    uploaded_image_base64: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user)
):
    """
    Receives an uploaded data file, triggers the LangGraph swarm, and returns the generated UI.
    Requires a valid JWT Bearer token.
    """
    try:
        final_state = await execute_generation_swarm(
            session_id, 
            file, 
            current_user, 
            uploaded_image_base64
        )

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
        logger.error(f"Chat Endpoint Error: {e}")
        raise HTTPException(status_code=500, detail="An error occurred while updating the dashboard.")

class TwitchQuestionRequest(BaseModel):
    session_id: str
    question: str


@router.post("/twitch/ask")
async def ask_twitch_dashboard(
    request: TwitchQuestionRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Answers a question about a live Twitch session using RAG over
    indexed stats + chat context, scoped to that one session only.
    """
    try:
        result = await answer_twitch_question(request.session_id, request.question)
        return result
    except Exception as e:
        logger.error(f"Twitch Q&A Error: {e}")
        raise HTTPException(status_code=500, detail="An error occurred while answering the question.")


def _authenticate_ws_token(token: str, db: Session) -> User:
    """Shared JWT validation for WebSocket endpoints. Raises ValueError on any failure."""
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    email = payload.get("sub")
    if email is None:
        raise ValueError("Token payload missing sub (email)")

    current_user = db.query(User).filter(User.email == email).first()
    if not current_user:
        raise ValueError("User not found in database")

    return current_user


@router.websocket("/ws/generate/{session_id}")
async def websocket_generate_endpoint(
    websocket: WebSocket,
    session_id: str,
    db: Session = Depends(get_db)
):
    """
    Streams the full first-generation pipeline: status updates as each
    agent node starts, plus token-by-token code streaming during the
    frontend_engineer step.
    """
    await websocket.accept()

    try:
        data = await websocket.receive_json()
        token = data.get("token")
        csv_content = data.get("csv_content")
        uploaded_image_base64 = data.get("uploaded_image_base64")

        if not token or not csv_content:
            await websocket.send_json({"type": "error", "message": "Missing token or csv_content"})
            await websocket.close(code=1008)
            return

        try:
            current_user = _authenticate_ws_token(token, db)
        except jwt.ExpiredSignatureError:
            await websocket.send_json({"type": "error", "message": "Token expired"})
            await websocket.close(code=1008)
            return
        except Exception as e:
            await websocket.send_json({"type": "error", "message": f"Error validating token: {str(e)}"})
            await websocket.close(code=1008)
            return

        async for message in stream_generation_swarm(
            session_id, csv_content, current_user, uploaded_image_base64
        ):
            await websocket.send_json(message)

        await websocket.send_text("<END_OF_STREAM>")

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected gracefully for generation session {session_id}")
    except Exception as e:
        import traceback
        logger.error("\n--- FULL WEBSOCKET TRACEBACK (GENERATE) ---")
        traceback.print_exc()
        logger.error(f"WebSocket Error: {e}")
        await websocket.send_json({"type": "error", "message": repr(e)})
        await websocket.close(code=1011)


@router.websocket("/ws/twitch/{session_id}")
async def websocket_twitch_endpoint(
    websocket: WebSocket,
    session_id: str,
    db: Session = Depends(get_db)
):
    """
    Connects to a live Twitch channel, generates an initial dashboard from
    a first data snapshot, then keeps pushing updated snapshots as the
    live session continues.

    Two phases over one connection:
      1. Same message protocol as /ws/generate (status/code_chunk/final)
         while the initial dashboard is being generated.
      2. Once generation succeeds, {"type": "data_update", "data": [...]}
         messages are pushed whenever new snapshot rows accumulate, until
         the client disconnects.
    """
    await websocket.accept()

    session: TwitchLiveSession | None = None

    try:
        data = await websocket.receive_json()
        token = data.get("token")
        channel = data.get("channel")
        uploaded_image_base64 = data.get("uploaded_image_base64")

        if not token or not channel:
            await websocket.send_json({"type": "error", "message": "Missing token or channel"})
            await websocket.close(code=1008)
            return

        try:
            current_user = _authenticate_ws_token(token, db)
        except jwt.ExpiredSignatureError:
            await websocket.send_json({"type": "error", "message": "Token expired"})
            await websocket.close(code=1008)
            return
        except Exception as e:
            await websocket.send_json({"type": "error", "message": f"Error validating token: {str(e)}"})
            await websocket.close(code=1008)
            return

        session = TwitchLiveSession(channel=channel, session_id=session_id)
        initial_row = await session.take_snapshot_now()

        generation_succeeded = False
        async for message in stream_twitch_swarm(session_id, [initial_row], current_user, uploaded_image_base64):
            await websocket.send_json(message)
            if message.get("type") == "final":
                generation_succeeded = True

        if not generation_succeeded:
            await websocket.close(code=1011)
            return

        await session.start()

        last_sent_count = len(session.rows)
        while True:
            await asyncio.sleep(session.snapshot_interval_seconds)
            current_rows = session.rows
            if len(current_rows) != last_sent_count:
                await websocket.send_json({"type": "data_update", "data": current_rows})
                last_sent_count = len(current_rows)

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected gracefully for Twitch session {session_id}")
    except Exception as e:
        import traceback
        logger.error("\n--- FULL WEBSOCKET TRACEBACK (TWITCH) ---")
        traceback.print_exc()
        logger.error(f"WebSocket Error: {e}")
        try:
            await websocket.send_json({"type": "error", "message": repr(e)})
            await websocket.close(code=1011)
        except Exception:
            pass  # connection may already be closed by this point
    finally:
        if session is not None:
            await session.stop()


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
            current_user = _authenticate_ws_token(token, db)
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
        logger.info(f"WebSocket disconnected gracefully for session {session_id}")
    except Exception as e:
        import traceback
        logger.error("\n--- FULL WEBSOCKET TRACEBACK ---")
        traceback.print_exc()
        logger.error(f"WebSocket Error: {e}")
        await websocket.send_text(f"Fatal Error: {repr(e)}")
        await websocket.close(code=1011)