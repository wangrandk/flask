FROM python:3.9-slim

WORKDIR /app

RUN apt-get update && \
    apt-get install -y gcc python3-dev && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD sh -c "uvicorn app.main:app --host 0.0.0.0 --port 5000 & celery -A app.tasks.app worker --loglevel=info"