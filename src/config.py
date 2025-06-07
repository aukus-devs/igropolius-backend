import os

ENV = os.getenv("ENV", "local")
POSTGRES_URL = os.getenv("POSTGRES_URL", "postgresql://user:password@localhost/db")

DATABASE_URL = "sqlite:///./test.db" if ENV == "local" else POSTGRES_URL

TOKEN_SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key")
