FROM python:3.12-slim

WORKDIR /srv

RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
# lenh tao bang checkpoint phien (SESSION_STORE=postgres), compose staging chay truoc ai-service (spec 014)
COPY scripts/__init__.py scripts/setup_session_checkpoint_tables.py ./scripts/

# chay bang user khong phai root (spec 014 FR-004); app khong ghi file luc chay
RUN useradd --uid 10001 --create-home --shell /usr/sbin/nologin app
USER app
# ma commit cua image (CI truyen --build-arg); health tra ve o truong `build` (T008, T009)
ARG APP_VERSION=dev
ENV APP_VERSION=$APP_VERSION

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
