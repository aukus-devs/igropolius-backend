import os

ENV = os.getenv("ENV", "local")
DB_URL = os.getenv("DB_URL", "")

IS_LOCAL = ENV == "local"

DATABASE_URL = "sqlite+aiosqlite:///./test.db" if IS_LOCAL else DB_URL

TOKEN_SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key")
