ps:
	docker compose ps
build:
	docker compose up -d --build
up:
	docker compose up -d
down:
	docker compose down
stop:
	docker compose stop
db:
	docker compose exec db bash

# Re-run the idempotent DB init on an existing volume (initdb.d only runs on an empty one)
db-ensure:
	docker compose exec db bash -c 'bash /docker-entrypoint-initdb.d/init-databases.sh'
