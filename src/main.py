from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api import (
    auth,
    bonus_cards,
    dice,
    igdb,
    internal,
    notifications,
    players,
    rules,
    taxes,
)

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

app.include_router(auth.router)
app.include_router(players.router)
app.include_router(rules.router)
app.include_router(bonus_cards.router)
app.include_router(taxes.router)
app.include_router(igdb.router)
app.include_router(dice.router)
app.include_router(internal.router)
app.include_router(notifications.router)
