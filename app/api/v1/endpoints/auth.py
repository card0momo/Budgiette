from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.core.security import create_access_token, hash_password, verify_password
from app.db.session import get_db
from app.models.models import User
from app.schemas.auth import TokenRead, UserCreate, UserLogin, UserRead

router = APIRouter(prefix="/auth", tags=["auth"])


def _to_user_read(user: User) -> UserRead:
    return UserRead.model_validate(user)


@router.post("/register", response_model=TokenRead, status_code=status.HTTP_201_CREATED)
def register(payload: UserCreate, db: Session = Depends(get_db)) -> TokenRead:
    email = payload.email or f"{payload.username}@budgiette.local"
    existing = db.execute(
        select(User).where((User.username == payload.username) | (User.email == email))
    ).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username or email already exists")

    user = User(
        username=payload.username,
        email=email,
        full_name=payload.full_name,
        hashed_password=hash_password(payload.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return TokenRead(access_token=create_access_token(str(user.id)))


@router.post("/login", response_model=TokenRead)
def login(payload: UserLogin, db: Session = Depends(get_db)) -> TokenRead:
    user = db.execute(select(User).where(User.username == payload.username)).scalar_one_or_none()
    if user is None or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect username or password")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Inactive user")

    return TokenRead(access_token=create_access_token(str(user.id)))


@router.get("/me", response_model=UserRead)
def read_me(user: User = Depends(get_current_user)) -> UserRead:
    return _to_user_read(user)
