View production logs for a Sahayakan service. Service: "$ARGUMENTS"

Read `.env.local` to get SSH_KEY_PATH and AWS_SERVER_IP. Then:

1. If "$ARGUMENTS" is empty or blank, default to "api-server".
2. Valid services: `api-server`, `postgres`, `minio`, `web-ui`.
3. Fetch the last 50 lines of logs:
   ```
   ssh -i {SSH_KEY_PATH} admin@{AWS_SERVER_IP} "cd ~/sahayakan/infrastructure && docker compose -f docker-compose.prod.yml logs --tail=50 {service}"
   ```
4. Display the log output and highlight any errors or warnings.
