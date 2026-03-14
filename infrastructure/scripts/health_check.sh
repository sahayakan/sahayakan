#!/bin/bash
# Sahayakan health check script
# Designed for cron: */5 * * * * /home/admin/sahayakan/infrastructure/scripts/health_check.sh
set -euo pipefail

ALERT_LOG="/var/log/sahayakan-alerts.log"
HEALTH_URL="${HEALTH_URL:-http://localhost:8000/health}"
DISK_THRESHOLD="${DISK_THRESHOLD:-90}"
BACKUP_DIR="${BACKUP_DIR:-/data/backups}"
BACKUP_MAX_AGE_HOURS="${BACKUP_MAX_AGE_HOURS:-25}"

log_alert() {
    local msg="[$(date -u '+%Y-%m-%dT%H:%M:%SZ')] ALERT: $1"
    echo "$msg" >> "$ALERT_LOG" 2>/dev/null || echo "$msg" >&2
}

# 1. Check /health endpoint
health_response=$(curl -sf --max-time 10 "$HEALTH_URL" 2>/dev/null) || {
    log_alert "Health endpoint unreachable at $HEALTH_URL"
    health_response=""
}

if [ -n "$health_response" ]; then
    status=$(echo "$health_response" | python3 -c "import sys,json; print(json.load(sys.stdin).get('status','unknown'))" 2>/dev/null || echo "unknown")
    if [ "$status" = "degraded" ]; then
        db=$(echo "$health_response" | python3 -c "import sys,json; print(json.load(sys.stdin).get('database','unknown'))" 2>/dev/null)
        minio=$(echo "$health_response" | python3 -c "import sys,json; print(json.load(sys.stdin).get('minio','unknown'))" 2>/dev/null)
        log_alert "System degraded - database=$db minio=$minio"
    fi
fi

# 2. Check disk usage
for mount in / /data; do
    if mountpoint -q "$mount" 2>/dev/null || [ "$mount" = "/" ]; then
        usage=$(df "$mount" | tail -1 | awk '{print $5}' | tr -d '%')
        if [ "$usage" -ge "$DISK_THRESHOLD" ]; then
            log_alert "Disk usage at ${usage}% on $mount (threshold: ${DISK_THRESHOLD}%)"
        fi
    fi
done

# 3. Check backup recency
if [ -d "$BACKUP_DIR" ]; then
    latest=$(find "$BACKUP_DIR" -maxdepth 1 -type d -newer /dev/null -printf '%T@ %p\n' 2>/dev/null | sort -rn | head -1 | cut -d' ' -f2-)
    if [ -z "$latest" ]; then
        log_alert "No backups found in $BACKUP_DIR"
    else
        age_seconds=$(( $(date +%s) - $(stat -c %Y "$latest" 2>/dev/null || date +%s) ))
        age_hours=$(( age_seconds / 3600 ))
        if [ "$age_hours" -ge "$BACKUP_MAX_AGE_HOURS" ]; then
            log_alert "Latest backup is ${age_hours}h old (threshold: ${BACKUP_MAX_AGE_HOURS}h): $latest"
        fi
    fi
fi
