Comprehensive production health check for Sahayakan.

Read `.env.local` to get SSH_KEY_PATH and AWS_SERVER_IP. Then run the following checks and report results:

1. **API health**: `curl -s https://ai.helm-team.org/health`

2. **Container status** (all services):
   ```
   ssh -i {SSH_KEY_PATH} admin@{AWS_SERVER_IP} "cd ~/sahayakan/infrastructure && docker compose -f docker-compose.prod.yml ps"
   ```

3. **HTTPS/TLS certificate**: `curl -sI https://ai.helm-team.org/health` and check certificate info.

4. **Disk usage** (root + EBS):
   ```
   ssh -i {SSH_KEY_PATH} admin@{AWS_SERVER_IP} "df -h / /data"
   ```

5. **Recent deploy** (last 3 commits):
   ```
   ssh -i {SSH_KEY_PATH} admin@{AWS_SERVER_IP} "cd ~/sahayakan && git log --oneline -3"
   ```

6. **Backup status** (last backup):
   ```
   ssh -i {SSH_KEY_PATH} admin@{AWS_SERVER_IP} "ls -lht /data/backups/ | head -5"
   ```

7. **Firewall rules**:
   ```
   ssh -i {SSH_KEY_PATH} admin@{AWS_SERVER_IP} "sudo ufw status"
   ```

Summarize overall production health with a clear status for each check (OK / WARNING / ERROR).
