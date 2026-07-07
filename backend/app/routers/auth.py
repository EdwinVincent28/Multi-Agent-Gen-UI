from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_password_hash, verify_password, create_access_token
from app.models.user import User
from app.models.schemas import UserCreate, TokenResponse

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])

@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register_user(user_data: UserCreate, db: Session = Depends(get_db)):
    """Creates a new user and returns an access token."""

    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    hashed_pw = get_password_hash(user_data.password)
    new_user = User(email=user_data.email, hashed_password=hashed_pw)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    access_token = create_access_token(data={"sub": new_user.email})
    return TokenResponse(access_token=access_token)

@router.post("/login", response_model=TokenResponse)
def login_user(user_data: UserCreate, db: Session = Depends(get_db)):
    """Verifies credentials and returns an access token."""

    user = db.query(User).filter(User.email == user_data.email).first()

    if not user or not verify_password(user_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(data={"sub": user.email})
    return TokenResponse(access_token=access_token)