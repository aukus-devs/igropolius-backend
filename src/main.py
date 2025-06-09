from typing import Annotated, Union

from fastapi import FastAPI, HTTPException, Response, status
from fastapi.params import Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api_models import CurrentUser, EventsList, LoginRequest, UsersList
from src.db import get_db
from src.db_models import User
from src.utils.auth import get_current_user
from src.utils.jwt import create_access_token, verify_password

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://igropolus.onrender.com",
        "https://igropolius.ru",
        "http://localhost:5200",
    ],  # Adjust as needed for production
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],  # Adjust as needed for production
)


class Item(BaseModel):
    name: str
    price: float


@app.post("/api/login")
async def login(
    request: LoginRequest,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    query = await db.execute(select(User).filter(User.username == request.username))
    user = query.scalars().first()
    if not user or not verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
        )
    token = create_access_token({"sub": user.username})
    return {"token": token}


@app.post("/api/logout")
async def logout(
    response: Response,
    current_user: Annotated[User, Depends(get_current_user)],
):
    # Invalidate the token or perform any necessary logout actions
    response.status_code = status.HTTP_204_NO_CONTENT
    return {"message": "Logged out successfully"}


@app.get("/api/players/current", response_model=CurrentUser)
def fetch_current_user(current_user: Annotated[User, Depends(get_current_user)]):
    return current_user


@app.get("/api/players", response_model=UsersList)
async def get_users(db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(select(User))
    users = result.scalars().all()
    return {"players": users}


@app.post("/api/players/{player_id}/events", response_model=EventsList)
async def get_player_events(
    player_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return {"events": []}


@app.get("/items/{item_id}")
def read_item(item_id: int, q: Union[str, None] = None):
    return {"item_id": item_id, "q": q}


@app.post("/items/{item_id}")
def update_item(item_id: int, item: Item):
    return {"item_name": item.name, "item_id": item_id}
