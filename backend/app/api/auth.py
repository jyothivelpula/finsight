from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_active_user
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.user import User
from app.schemas.auth import (
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from app.services.defaults import seed_default_categories


router = APIRouter(prefix="/auth", tags=["Authentication API"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Session = Depends(get_db)) -> User:
    existing = db.query(User).filter(User.email == payload.email.lower()).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        email=payload.email.lower(),
        full_name=payload.full_name,
        hashed_password=hash_password(payload.password),
        is_verified=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    seed_default_categories(db, user.id)
    return user


def _issue_tokens(user: User) -> TokenResponse:
    return TokenResponse(
        access_token=create_access_token(str(user.id)),
        refresh_token=create_refresh_token(str(user.id)),
    )


def _authenticate(db: Session, email: str, password: str) -> User:
    user = db.query(User).filter(User.email == email.lower()).first()
    if not user or not verify_password(password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return user


@router.post("/login", response_model=TokenResponse)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
) -> TokenResponse:
    user = _authenticate(db, form_data.username, form_data.password)
    return _issue_tokens(user)


@router.post("/login/json", response_model=TokenResponse)
def login_json(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    user = _authenticate(db, payload.email, payload.password)
    return _issue_tokens(user)


@router.post("/refresh", response_model=TokenResponse)
def refresh_token(payload: RefreshRequest, db: Session = Depends(get_db)) -> TokenResponse:
    try:
        data = decode_token(payload.refresh_token)
        if data.get("type") != "refresh":
            raise ValueError("Invalid token type")
        user_id = int(data["sub"])
    except (ValueError, KeyError, TypeError):
        raise HTTPException(status_code=401, detail="Invalid refresh token") from None

    user = db.get(User, user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    return TokenResponse(
        access_token=create_access_token(str(user.id)),
        refresh_token=create_refresh_token(str(user.id)),
    )


@router.get("/me", response_model=UserResponse)
def me(current_user: User = Depends(get_current_active_user)) -> User:
    return current_user


@router.post("/logout")
def logout(current_user: User = Depends(get_current_active_user)) -> dict:
    # JWT is stateless; client discards tokens. Endpoint exists for secure logout UX.
    return {"message": "Logged out successfully", "user_id": current_user.id}
