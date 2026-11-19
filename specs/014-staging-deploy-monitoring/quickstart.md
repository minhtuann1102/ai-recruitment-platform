# Quickstart: kiểm chứng staging

Lệnh và mã thoát: [contracts/staging-cli.md](contracts/staging-cli.md); route:
[contracts/gateway-staging-routes.md](contracts/gateway-staging-routes.md). `H` = `https://${STAGING_API_HOST}`.

## 0. Offline (trước khi đụng cloud)

```bash
pnpm lint && pnpm check-types && pnpm test          # gồm test HealthModule
(cd apps/ai-service && .venv/Scripts/python.exe -m pytest -q)
shellcheck infra/staging/scripts/*.sh infra/staging/monitoring/*.sh
docker build -f .docker/node-service.Dockerfile --build-arg SERVICE=user-service --target runtime .
docker compose -f infra/staging/docker-compose.staging.yml config >/dev/null
```

Mong đợi: tất cả thoát 0; image chạy bằng user không phải root (`docker run --rm <img> id -u` ≠ 0); `docker compose
up` của dev không đổi danh sách service.

## 1. Dựng máy (US1)

```bash
infra/staging/scripts/provision-gcp.sh     # chạy hai lần: lần 2 toàn "exists"
gcloud compute ssh ai-recruit-staging --tunnel-through-iap -- 'sudo bash -s' < infra/staging/scripts/bootstrap-vm.sh
# chép .env.staging.example → /opt/ai-recruit/.env trên VM, điền bí mật, chmod 600
infra/staging/scripts/deploy.sh
```

Mong đợi (SC-001 ≤ 60 phút): `curl -s $H/ai/api/health` có `build` = sha; `curl -s $H/user/api/health` 200 với
`checks.db = ok`; chứng chỉ hợp lệ (`curl -v` không cảnh báo); `nmap -Pn <IP>` chỉ 80/443 mở (SC-006).

## 2. Bảo vệ AI + stream (US1, FR-003a, SC-003)

```bash
curl -s -o /dev/null -w '%{http_code}\n' -X POST $H/ai/api/start                       # 401
TOKEN=$(gcloud compute ssh ai-recruit-staging --tunnel-through-iap -- /opt/ai-recruit/bin/issue-test-jwt.sh qa 3600)
curl -N -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' -d @<payload-start.json> $H/ai/api/start
curl -s -o /dev/null -w '%{http_code}\n' $H/ai/metrics                                   # 404
for i in $(seq 12); do curl -s -o /dev/null -w '%{http_code} ' -X POST -H "Authorization: Bearer $TOKEN" $H/ai/api/start; done   # cuối là 429
```

Mong đợi: sự kiện SSE hiện từng phần (không dồn cuối); đo TTFT p95 trên 10 lượt qua `$H` và trực tiếp trên VM
(`curl localhost:18000`), chênh ≤ 300 ms. Chạy 5 phiên song song: không lỗi, RAM / CPU < 80% (SC-004).

## 3. Deploy / rollback (US2, SC-002)

Merge một thay đổi nhỏ vào `main` → chờ `build-images` xanh → `deploy.sh` → `build` đổi. `rollback.sh` → `build` về
sha cũ ≤ 5 phút. Thử migration lỗi trên branch (image tag riêng) → `deploy.sh <sha>` thoát 1, service giữ bản cũ.

## 4. Sao lưu (US4, SC-007)

Trên VM: `backup-postgres.sh` → object mới trong bucket; `restore-postgres.sh user_db <object> --target
user_db_restore_test` → số bản ghi khớp `user_db`; xóa DB thử.

## 5. Giám sát (US3, SC-005)

`monitoring/apply-monitoring.sh` (chạy hai lần, không tạo trùng). `docker stop ai_recruit_ai_service` → email ≤ 5
phút, đúng một email; `docker start` → cảnh báo tự đóng. Dashboard có đủ nhóm của spec US3 kịch bản 2; Logs Explorer
lọc theo container ra log của từng service.

## 6. Thêm service (US5, SC-008)

Làm theo danh sách bước trong `docs/deployment-guide.md` cho `notification-service` như service mới trên branch thử;
đếm file đổi, thời gian ≤ 1 giờ, `deploy-on-vm.sh` không sửa.
