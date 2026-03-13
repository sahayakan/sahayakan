Rebuild and restart a Sahayakan Podman service. Service: "$ARGUMENTS"

Valid services: `api-server` (default if blank), `postgres`, `minio`, `web-ui`, `all`.

Steps:

1. If "$ARGUMENTS" is empty or blank, default to "api-server".
2. If "all", rebuild all services:
   ```
   cd infrastructure && podman-compose --env-file ../.env up -d --build
   ```
3. Otherwise, rebuild the specific service:
   ```
   cd infrastructure && podman-compose --env-file ../.env up -d --build {service}
   ```
4. Wait a few seconds, then check container status:
   ```
   podman-compose -f infrastructure/docker-compose.yml ps
   ```
5. If api-server was rebuilt, verify the health endpoint:
   ```
   curl -s http://localhost:8000/health
   ```
6. Report the result.
