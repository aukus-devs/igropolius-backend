import os

ENV = os.getenv("ENV", "local")

DATABASE_URL = (
    "sqlite:///./test.db"
    if ENV == "local"
    else "postgresql://user:password@localhost/db"
)
