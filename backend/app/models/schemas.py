class UserCreate(BaseModel):
    """Data required to register or log in."""
    email: str = Field(..., description="The user's email address")
    password: str = Field(..., min_length=6, description="The user's secure password")

class TokenResponse(BaseModel):
    """The JWT payload sent back to the client."""
    access_token: str
    token_type: str = "bearer"