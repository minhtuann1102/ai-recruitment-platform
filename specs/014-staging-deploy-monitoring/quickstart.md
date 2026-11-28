# Quickstart: kiểm chứng staging

Sửa 2026-11-28 theo phạm vi mới (Caddy, 2 service, GHCR). Lệnh và mã thoát:
[contracts/staging-cli.md](contracts/staging-cli.md); host và mã trả về: [contracts/staging-hosts.md](contracts/staging-hosts.md).
`A` = `https://${AI_HOST}`, `V` = `https://${VOICE_HOST}`, `D` = `https://${DEMO_HOST}`; `T` = `AI_SERVICE_INTERNAL_TOKEN`.

## 0. Offline, trên máy (trước khi đụng cloud)

```bash
(cd apps/ai-service && .venv/Scripts/python.exe -m pytest -q)
(cd apps/voice-service && .venv/Scripts/python.exe -m pytest -q)
shellcheck infra/staging/scripts/*.sh infra/staging/monitoring/*.sh
R=ghcr.io/minhtuann1102/ai-recruitment-platform
docker build -t $R/ai-service:local apps/ai-service && docker build -t $R/voice-service:local apps/voice-service
cd infra/staging   # .env với IMAGE_TAG=local, host ai.localhost / voice.localhost / demo.localhost, HTTP(S)_PORT tùy
docker compose -f docker-compose.staging.yml config >/dev/null && docker compose -f docker-compose.staging.yml up -d
```

Mong đợi: tất cả thoát 0; `ai-session-setup` thoát 0 và log ai-service có `session_store kind=postgres`; chỉ Caddy
publish cổng (`docker compose ps`); các mã ở bảng của [staging-hosts.md](contracts/staging-hosts.md) đúng qua
`curl -k --resolve ai.localhost:<port>:127.0.0.1`; image chạy bằng user không phải root (`docker run --rm <img> id -u` ≠
0, sau task Dockerfile); `docker compose up` của dev ở gốc repo không đổi.

## 1. Dựng máy (US1)

```bash
infra/staging/scripts/provision-gcp.sh     # chạy hai lần: lần 2 toàn "exists"
gcloud compute ssh hireready-staging --tunnel-through-iap -- 'sudo bash -s' < infra/staging/scripts/bootstrap-vm.sh
# trên VM: /opt/ai-recruit/.env (từ .env.staging.example) + env/ai-service.env + env/voice-service.env, chmod 600
infra/staging/scripts/deploy.sh
```

Mong đợi (SC-001 ≤ 60 phút): `curl -s $A/api/health` và `curl -s $V/api/health` 200 với `build` = sha; chứng chỉ hợp
lệ (`curl -v` không cảnh báo, không cần `-k`); `nmap -Pn <IP>` chỉ 80/443 mở (SC-006).

## 2. Bảo vệ + stream (US1, FR-003a, FR-006, SC-003)

```bash
curl -s -o /dev/null -w '%{http_code}\n' -X POST $A/api/start                       # 401
curl -s -o /dev/null -w '%{http_code}\n' $A/metrics $V/metrics $A/dev/play           # 404 404 404
curl -N -H "X-Internal-Token: $T" -H 'Content-Type: application/json' -d @<payload-start.json> $A/api/start
```

Mong đợi: sự kiện SSE hiện từng phần (không dồn cuối); đo TTFT p95 trên 10 lượt qua `$A` và trực tiếp trên VM
(`docker compose exec ai-service curl localhost:8000/...`), chênh ≤ 300 ms. Chạy 5 phiên song song: không lỗi, RAM /
CPU < 80% (SC-004). Giữa một phiên: `docker compose restart ai-service` → lượt tiếp theo vẫn chạy (US1 kịch bản 4).

## 3. Host demo (US1 kịch bản 5, sau PR #120 + cờ trang dev)

`$D` không mật khẩu → 401; có mật khẩu → trang phỏng vấn, làm một phiên có giọng nói; `$D/docs` → 404; DevTools không
thấy `X-Internal-Token` trong request của trình duyệt.

## 4. Deploy / rollback (US2, SC-002)

Merge một thay đổi nhỏ vào `main` → chờ `build-images` xanh → `docker pull` ẩn danh image mới (package public) →
`deploy.sh` → `build` đổi. `rollback.sh` → `build` về sha cũ ≤ 5 phút. Cho `SESSION_DB_URL` sai trên branch thử →
`deploy.sh <sha>` thoát 1, ai-service giữ bản cũ.

## 5. Sao lưu (US4, SC-007)

Trên VM: `backup-postgres.sh` → object mới trong bucket; `restore-postgres.sh <object> --target ai_session_restore_test`
→ số bản ghi khớp `ai_session`; xóa DB thử.

## 6. Giám sát (US3, SC-005)

`monitoring/apply-monitoring.sh` (chạy hai lần, không tạo trùng). `docker compose stop ai-service` → email ≤ 5 phút,
đúng một email; `start` → cảnh báo tự đóng. Dashboard có đủ nhóm của spec US3 kịch bản 2; Logs Explorer lọc theo
container ra log của từng service.

## 7. Backend FSD + thêm service (US5, SC-008)

Từ một máy ngoài, chỉ dùng hướng dẫn trong `docs/deployment-guide.md` (2 URL + 2 token): gọi một phiên phỏng vấn và
một lần `/api/voice/transcribe`. Làm theo danh sách bước thêm service cho `data-pipeline` như service mới trên branch thử; đếm file
đổi, thời gian ≤ 1 giờ, `deploy-on-vm.sh` không sửa.
