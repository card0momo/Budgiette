from pydantic import Field

from app.schemas.common import APIModel


class CategoryCreate(APIModel):
    name: str = Field(min_length=1, max_length=120)
    is_income: bool = False


class CategoryRead(APIModel):
    id: int
    user_id: int
    name: str
    is_income: bool
