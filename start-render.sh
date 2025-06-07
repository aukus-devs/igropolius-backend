python -m src.db
uvicorn src.main:app --host 0.0.0.0 --port $PORT
