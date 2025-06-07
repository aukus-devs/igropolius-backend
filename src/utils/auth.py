from fastapi import Depends, Cookie, HTTPException, status
from jose import JWTError
from sqlalchemy.orm import Session
from src.db import get_db
from src.db_models import User
from src.utils.jwt import decode_access_token


def get_current_user(
    access_token: str | None = Cookie(default=None), db: Session = Depends(get_db)
):
    if access_token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
        )
    try:
        payload = decode_access_token(access_token)
        username: str | None = payload.get("sub")
        if username is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
            )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
        )

    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found"
        )
    return user
