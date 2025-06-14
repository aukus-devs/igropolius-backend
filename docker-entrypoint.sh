#!/bin/bash
set -e

echo "Initializing database..."
python -m src.db

echo "Starting FastAPI application..."
exec uvicorn src.main:app --host 0.0.0.0 --port 8000 --proxy-headers --forwarded-allow-ips="*"
