#!/bin/bash
set -e

echo "Initializing database..."
python -m src.db.db_session

echo "Starting FastAPI application..."
if [ "$IPv6" = "false" ]; then
    exec uvicorn src.main:app --host 0.0.0.0 --proxy-headers --forwarded-allow-ips="*"
else
    exec uvicorn src.main:app --host '::' --proxy-headers --forwarded-allow-ips="*"
fi
