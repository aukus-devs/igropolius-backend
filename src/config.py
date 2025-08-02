import os
import logging

ENV = os.getenv("ENV", "local")
DB_URL = os.getenv("DB_URL", "")

IS_LOCAL = ENV == "local"

DATABASE_URL = "sqlite+aiosqlite:///./test.db" if IS_LOCAL else DB_URL

TOKEN_SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key")

SAVE_STREAM_CATEGORIES = os.getenv("SAVE_STREAM_CATEGORIES", "true").lower() == "true"

RANDOM_ORG_API_KEY = os.getenv("RANDOM_ORG_API_KEY", "")

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler()
        ]
    )
