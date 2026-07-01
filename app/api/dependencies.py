from fastapi import Header, HTTPException, status


def get_current_user_id(x_user_id: int | None = Header(default=None)) -> int:
    if x_user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-User-Id header. Auth integration is pending.",
        )
    return x_user_id
