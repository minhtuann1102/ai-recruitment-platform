# Quickstart: kiểm chứng Platform Foundation

Dùng làm checklist nghiệm thu từng PR và kịch bản demo Sprint 0. Lệnh viết cho bash (Git Bash trên Windows).

## 0. Chuẩn bị (máy sạch)

```bash
git clone <repo-url> && cd ai-recruitment-platform
cp .env.example .env
pnpm install && pnpm build          # US2: phải xanh
```

Máy đã có volume cũ: `docker compose down -v && rm -rf .docker/volumes/pgdata` (reset) **hoặc** chạy `make db-ensure`
sau bước 1 (giữ dữ liệu).

## 1. Hạ tầng (US1, SC-002)

```bash
docker compose up -d
docker compose ps                    # mọi service: running/healthy, tên ai_recruit_*
```

## 2. Database (US1, FR-002)

```bash
docker exec ai_recruit_db psql -U postgres -tAc "SELECT datname FROM pg_database ORDER BY 1;"
# phải có: ai_db interview_db job_db notification_db user_db
docker exec ai_recruit_db psql -U postgres -d ai_db -tAc "SELECT extname FROM pg_extension WHERE extname='vector';"
# phải in: vector
```

## 3. Object storage (US1, FR-004, SC-006)

```bash
docker compose run --rm --entrypoint sh minio-init -c '
  mc alias set local http://minio:9000 "$MINIO_ROOT_USER" "$MINIO_ROOT_PASSWORD" >/dev/null &&
  echo "hello ai-recruit" | mc pipe local/ai-recruit-files/probe.txt &&
  mc cat local/ai-recruit-files/probe.txt'
# phải in lại: hello ai-recruit
# Console: http://localhost:9001
```

## 4. Gateway (US4, SC-005)

```bash
make adcSync environment=dev
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:9080/job/api/anything      # 401
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:9080/interview/api/x       # 401 (route bảo vệ)
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:9080/ai/api/health         # 200 (khi ai-service chạy)
```

## 5. Định danh (US2, SC-003)

```bash
git ls-files | grep -v -E '^docs/|^specs/|^\.specify/|^\.claude/|pnpm-lock.yaml' \
  | xargs grep -Il -i -E 'kong|nest-turbo|nest_turbo|@app/'
# phải không in gì
```

## 6. CI (US3, SC-004)

Mở PR thử thêm một biến không dùng (vi phạm lint) → job `node` đỏ ở bước lint. Sửa → xanh. Kiểm tra job `python`
chạy cho `ai-service` khi thư mục tồn tại.
