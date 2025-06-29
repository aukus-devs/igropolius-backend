from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.db import get_db
from src.db_models import User
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

    acting_user_id_str = request.headers.get("x-acting-user-id")
    if allow_acting and username.lower() == "praden" and acting_user_id_str:
        username = (
            (
                await db.execute(
                    select(User.username).where(User.id == acting_user_id_str)
                )
            )
            .scalars()
            .first()
        )
        if not username:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Acting user not found"
            )

    if for_update:
        query = await db.execute(
            select(User).where(User.username == username).with_for_update()
        )
    else:
        query = await db.execute(select(User).where(User.username == username))
    user = query.scalars().first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found"
        )
    return user


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
