from app.schemas.common import APIModel


class HealthRead(APIModel):
    status: str
    app: str
    version: str
