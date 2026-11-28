FROM python:3.12-slim

WORKDIR /srv

RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
# lenh tao bang checkpoint phien (SESSION_STORE=postgres), compose staging chay truoc ai-service (spec 014)
COPY scripts/__init__.py scripts/setup_session_checkpoint_tables.py ./scripts/

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
