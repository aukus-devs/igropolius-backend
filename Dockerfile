FROM python:3.11-slim
WORKDIR /app

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    pkg-config \
    default-libmysqlclient-dev \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY ./src ./src

EXPOSE 8000

RUN python -m src.db
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
