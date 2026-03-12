from fastapi import HTTPException, Request, status


def get_user_id(request: Request) -> int | None:
    session = request.scope.get("session", {})
    user_id = session.get("user_id")
    return user_id if isinstance(user_id, int) else None


def require_user_id(request: Request) -> int:
    user_id = get_user_id(request)
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_303_SEE_OTHER,
            headers={"Location": "/login"},
        )
    return user_id
