Manually deploy Sahayakan to the production server.

Read `.env.local` to get SSH_KEY_PATH and AWS_SERVER_IP. Then perform the following steps via SSH:

1. **Pull latest code**:
   ```
   ssh -i {SSH_KEY_PATH} admin@{AWS_SERVER_IP} "cd ~/sahayakan && git pull origin main"
   ```

2. **Rebuild services** (api-server and web-ui only, keeps postgres/minio running):
   ```
   ssh -i {SSH_KEY_PATH} admin@{AWS_SERVER_IP} "cd ~/sahayakan/infrastructure && docker compose -f docker-compose.prod.yml --env-file ../.env up -d --build api-server web-ui"
   ```

3. **Wait and verify health** (up to 60 seconds):
   ```
   curl -s https://ai.helm-team.org/health
   ```

4. **Check container status**:
   ```
   ssh -i {SSH_KEY_PATH} admin@{AWS_SERVER_IP} "cd ~/sahayakan/infrastructure && docker compose -f docker-compose.prod.yml ps"
   ```

5. **Show current deployed commit**:
   ```
   ssh -i {SSH_KEY_PATH} admin@{AWS_SERVER_IP} "cd ~/sahayakan && git log --oneline -3"
   ```

6. Report the deploy result: success or failure with details.
