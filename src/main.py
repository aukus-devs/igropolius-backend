from typing import Annotated, Union

from fastapi import FastAPI
from fastapi.params import Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from src.api_models import UsersList
from src.db import get_db
from src.db_models import User

app = FastAPI()


class Item(BaseModel):
    name: str
    price: float


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
