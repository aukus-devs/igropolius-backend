#!/bin/bash
set -e

echo "Initializing database..."
python -m src.db

echo "Starting FastAPI application..."
exec uvicorn src.main:app --host '::' --proxy-headers --forwarded-allow-ips="*"
