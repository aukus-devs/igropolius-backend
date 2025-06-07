from typing import Annotated, Union

from fastapi import FastAPI, HTTPException, Response, status
from fastapi.params import Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session

from src.api_models import CurrentUser, LoginRequest, UsersList
from src.db import get_db
from src.db_models import User
from src.utils.auth import get_current_user
from src.utils.jwt import create_access_token, verify_password

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://igropolus.onrender.com/"
    ],  # Adjust as needed for production
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],  # Adjust as needed for production
)


class Item(BaseModel):
    name: str
    price: float


@app.post("/login")
def login(
    request: LoginRequest,
    response: Response,
    db: Annotated[Session, Depends(get_db)],
):
    user = db.query(User).filter(User.nickname == request.username).first()
    if not user or not verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
        )

    token = create_access_token({"sub": user.nickname})
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        max_age=60 * 60 * 24 * 12,  # 12 days
        secure=True,  # Set to True if using HTTPS
        samesite="none",  # Adjust as needed
    )
    return {"status": "ok"}


@app.get("/api/users/current", response_model=CurrentUser)
def fetch_current_user(current_user: Annotated[User, Depends(get_current_user)]):
    return current_user


@app.get("/api/users", response_model=UsersList)
def get_users(db: Annotated[Session, Depends(get_db)]):
    users = list(db.query(User).all())
    return {"users": users}


@app.get("/items/{item_id}")
def read_item(item_id: int, q: Union[str, None] = None):
    return {"item_id": item_id, "q": q}


@app.post("/items/{item_id}")
def update_item(item_id: int, item: Item):
    return {"item_name": item.name, "item_id": item_id}
