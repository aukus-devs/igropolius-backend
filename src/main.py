import logging
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from src.api import (
    auth,
    bonus_cards,
    dice,
    event_settings,
    igdb,
    internal,
    notifications,
    players,
    rules,
    taxes,
)
from src.config import setup_logging

setup_logging()
logger = logging.getLogger(__name__)


async def logging_middleware(request: Request, call_next):
    try:
        response = await call_next(request)

        if response.status_code >= 400:
            logger.error(
                f"Failed request: {request.method} {request.url} - Status: {response.status_code}"
            )

            response_body = b""
            async for chunk in response.body_iterator:
                response_body += chunk

            try:
                body_text = response_body.decode()
                if body_text:
                    logger.error(f"Error response body: {body_text}")
            except Exception as e:
                logger.error(f"Could not decode response body: {e}")

            return Response(
                content=response_body,
                status_code=response.status_code,
                headers=dict(response.headers),
                media_type=response.media_type,
            )

        return response
    except Exception as e:
        logger.error(f"Middleware error: {e}")
        raise


app = FastAPI()

app.middleware("http")(logging_middleware)
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
app.include_router(event_settings.router)
app.include_router(internal.router)
app.include_router(notifications.router)
