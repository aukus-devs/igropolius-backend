#!/bin/bash
set -e

echo "Initializing database..."
python -m src.db.db_session

echo "Starting FastAPI application..."
WORKERS=${WORKERS:-2}
TIMEOUT_GRACEFUL_SHUTDOWN=${TIMEOUT_GRACEFUL_SHUTDOWN:-30}

if [ "$IPv6" = "false" ]; then
    exec uvicorn src.main:app --host 0.0.0.0 --proxy-headers --forwarded-allow-ips="*" --timeout-graceful-shutdown $TIMEOUT_GRACEFUL_SHUTDOWN --workers $WORKERS
else
    exec uvicorn src.main:app --host '::' --proxy-headers --forwarded-allow-ips="*" --timeout-graceful-shutdown $TIMEOUT_GRACEFUL_SHUTDOWN --workers $WORKERS
fi
