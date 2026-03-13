Rebuild and restart a Sahayakan service. Service: "$ARGUMENTS"

Valid services: `api-server` (default if blank), `postgres`, `minio`, `web-ui`, `all`.

Parse "$ARGUMENTS" for an optional `--prod` flag. The service name is the non-flag argument.

## Local mode (default, no `--prod` flag)

1. If service argument is empty or blank, default to "api-server".
2. If "all", rebuild all services:
   ```
   cd infrastructure && docker compose --env-file ../.env up -d --build
   ```
3. Otherwise, rebuild the specific service:
   ```
   cd infrastructure && docker compose --env-file ../.env up -d --build {service}
   ```
4. If `docker compose` is not available, fall back to `podman-compose --env-file ../.env` instead.
5. Wait a few seconds, then check container status:
   ```
   cd infrastructure && docker compose --env-file ../.env ps
   ```
6. If api-server was rebuilt, verify the health endpoint:
   ```
   curl -s http://localhost:8000/health
   ```
7. Report the result.

## Production mode (`--prod` flag)

1. Read `.env.local` to get SSH_KEY_PATH and AWS_SERVER_IP.
2. If service argument is empty or blank, default to "api-server".
3. For `web-ui`, use `build --no-cache` then `up -d` to bust Docker layer cache:
   ```
   ssh -i {SSH_KEY_PATH} admin@{AWS_SERVER_IP} "cd ~/sahayakan/infrastructure && docker compose -f docker-compose.prod.yml --env-file ../.env build --no-cache web-ui && docker compose -f docker-compose.prod.yml --env-file ../.env up -d --no-deps web-ui"
   ```
4. For other services, rebuild normally:
   ```
   ssh -i {SSH_KEY_PATH} admin@{AWS_SERVER_IP} "cd ~/sahayakan/infrastructure && docker compose -f docker-compose.prod.yml --env-file ../.env up -d --build --no-deps {service}"
   ```
5. If "all", rebuild all services:
   ```
   ssh -i {SSH_KEY_PATH} admin@{AWS_SERVER_IP} "cd ~/sahayakan/infrastructure && docker compose -f docker-compose.prod.yml --env-file ../.env up -d --build"
   ```
6. Wait a few seconds, then verify health:
   ```
   curl -s https://ai.helm-team.org/health
   ```
7. Check container status:
   ```
   ssh -i {SSH_KEY_PATH} admin@{AWS_SERVER_IP} "cd ~/sahayakan/infrastructure && docker compose -f docker-compose.prod.yml ps"
   ```
8. Report the result.
