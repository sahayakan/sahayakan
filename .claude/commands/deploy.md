Manually deploy Sahayakan to the production server.

Read `.env.local` to get SSH_KEY_PATH and AWS_SERVER_IP. Then perform the following steps via SSH:

1. **Pull latest code**:
   ```
   ssh -i {SSH_KEY_PATH} admin@{AWS_SERVER_IP} "cd ~/sahayakan && git pull origin main"
   ```

2. **Apply database migrations** (idempotent — errors on existing objects are ignored).
   Use `< /dev/null` on docker exec to prevent it from consuming SSH stdin:
   ```
   ssh -i {SSH_KEY_PATH} admin@{AWS_SERVER_IP} 'for f in /home/admin/sahayakan/infrastructure/db/migrations/*.sql; do echo "  $(basename $f)"; docker exec infrastructure-postgres-1 psql -U sahayakan -d sahayakan -f "/docker-entrypoint-initdb.d/$(basename $f)" -v ON_ERROR_STOP=0 < /dev/null 2>&1 | tail -1; done'
   ```

3. **Rebuild services** (api-server and web-ui only, keeps postgres/minio running).
   For web-ui, use `--build-arg CACHEBUST` to bust Docker layer cache for COPY+build steps:
   ```
   ssh -i {SSH_KEY_PATH} admin@{AWS_SERVER_IP} "cd ~/sahayakan/infrastructure && docker compose -f docker-compose.prod.yml --env-file ../.env up -d --build --no-deps api-server"
   ssh -i {SSH_KEY_PATH} admin@{AWS_SERVER_IP} "cd ~/sahayakan/infrastructure && docker compose -f docker-compose.prod.yml --env-file ../.env build --build-arg CACHEBUST=$(date +%s) web-ui && docker compose -f docker-compose.prod.yml --env-file ../.env up -d --no-deps web-ui"
   ```

4. **Wait and verify health** (up to 60 seconds):
   ```
   curl -s https://ai.helm-team.org/health
   ```

5. **Check container status**:
   ```
   ssh -i {SSH_KEY_PATH} admin@{AWS_SERVER_IP} "cd ~/sahayakan/infrastructure && docker compose -f docker-compose.prod.yml ps"
   ```

6. **Show current deployed commit**:
   ```
   ssh -i {SSH_KEY_PATH} admin@{AWS_SERVER_IP} "cd ~/sahayakan && git log --oneline -3"
   ```

7. Report the deploy result: success or failure with details.
