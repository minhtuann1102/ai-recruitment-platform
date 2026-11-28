FROM python:3.12-slim

WORKDIR /srv

RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Chi copy app/: .env khong vao image (docker-compose nap qua env_file), evals/ va tests/ chay o may dev
COPY app ./app

# chay bang user khong phai root (spec 014 FR-004); app khong ghi file luc chay
RUN useradd --uid 10001 --create-home --shell /usr/sbin/nologin app
USER app
# ma commit cua image (CI truyen --build-arg); health tra ve o truong `build` (T008, T009)
ARG APP_VERSION=dev
ENV APP_VERSION=$APP_VERSION

EXPOSE 8020
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8020"]
