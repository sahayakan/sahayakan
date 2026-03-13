Rebuild and restart a Sahayakan service. Service: "$ARGUMENTS"

Valid services: `api-server` (default if blank), `postgres`, `minio`, `web-ui`, `all`.

Steps:

1. If "$ARGUMENTS" is empty or blank, default to "api-server".
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
