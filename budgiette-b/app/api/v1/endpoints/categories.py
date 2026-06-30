from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user_id
from app.db.session import get_db
from app.models.models import Category
from app.schemas.categories import CategoryCreate, CategoryRead

router = APIRouter(prefix="/categories", tags=["categories"])


@router.get("", response_model=list[CategoryRead])
def list_categories(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
) -> list[CategoryRead]:
    rows = db.execute(select(Category).where(Category.user_id == user_id).order_by(Category.name.asc())).scalars().all()
    return [CategoryRead.model_validate(item) for item in rows]


@router.post("", response_model=CategoryRead, status_code=status.HTTP_201_CREATED)
def create_category(
    payload: CategoryCreate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
) -> CategoryRead:
    item = Category(user_id=user_id, **payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return CategoryRead.model_validate(item)
