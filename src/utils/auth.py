from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.db import get_db
from src.db_models import User
from src.enums import Role
from src.utils.jwt import decode_access_token

security = HTTPBearer()


def get_username(token: str):
    try:
        payload = decode_access_token(token)
        username: str | None = payload.get("sub")
        if username is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
            )
        return username
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
        )


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
    for_update: bool = False,
    allow_acting: bool = True,
):
    token = credentials.credentials
    username = get_username(token)

    # Fetch the user making the request
    query = select(User).where(User.username == username)
    result = await db.execute(query)
    requesting_user = result.scalars().first()

    if requesting_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found"
        )

    # Check if an admin is acting as another user
    acting_user_id_str = request.headers.get("x-acting-user-id")
    is_acting = (
        allow_acting and requesting_user.role == Role.ADMIN.value and acting_user_id_str
    )

    if is_acting and acting_user_id_str:
        # If acting, fetch the target user, applying a lock if necessary
        target_query = select(User).where(User.id == int(acting_user_id_str))
        if for_update:
            target_query = target_query.with_for_update()

        target_result = await db.execute(target_query)
        target_user = target_result.scalars().first()

        if target_user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Acting user not found"
            )
        return target_user

    # If not acting, but a lock is requested for the original user
    if for_update:
        # Re-fetch the original user with a lock
        locked_query = (
            select(User).where(User.id == requesting_user.id).with_for_update()
        )
        locked_result = await db.execute(locked_query)
        # The user must exist, so we can safely return it
        return locked_result.scalars().first()

    # Otherwise, return the user we already fetched
    return requesting_user


async def get_current_user_for_update(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
):
    return await get_current_user(request, credentials, db, for_update=True)


async def get_current_user_direct(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
):
    return await get_current_user(request, credentials, db, allow_acting=False)
