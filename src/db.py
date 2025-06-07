# database.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src import db_models

from .config import DATABASE_URL

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
    if DATABASE_URL.startswith("sqlite")
    else {},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    print("Initializing database...")
    db_models.Base.metadata.create_all(bind=engine)


if __name__ == "__main__":
    init_db()
