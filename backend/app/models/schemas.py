from pydantic import BaseModel, Field
from typing import Any

class GenerationRequest(BaseModel):
    """Validates the JSON payload sent from the Vite frontend or Postman."""
    session_id: str = Field(..., description="Unique identifier for the user's current session/thread.")
    raw_data: str = Field(..., description="The raw CSV or JSON data string uploaded by the user.")

class GenerationResponse(BaseModel):
    """Structures the final output returned to the client."""
    insights: str | None
    ui_code: str | None
    data: Any = None
    errors: str | None

class UserCreate(BaseModel):
    """Data required to register or log in."""
    email: str = Field(..., description="The user's email address")
    password: str = Field(..., min_length=8, description="The user's secure password")

class TokenResponse(BaseModel):
    """The JWT payload sent back to the client."""
    access_token: str
    token_type: str = "bearer"

class ChatRequest(BaseModel):
    """Payload for the iterative chat feature."""
    session_id: str
    prompt: str