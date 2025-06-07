from typing import Union

from fastapi import FastAPI
from pydantic import BaseModel

from src.db_models import User

app = FastAPI()


class Item(BaseModel):
    name: str
    price: float


@app.get("/api/users")
def get_users():
  User.query.all()
  


@app.get("/items/{item_id}")
def read_item(item_id: int, q: Union[str, None] = None):
    return {"item_id": item_id, "q": q}


@app.post("/items/{item_id}")
def update_item(item_id: int, item: Item):
    return {"item_name": item.name, "item_id": item_id}
