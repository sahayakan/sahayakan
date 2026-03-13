#!/bin/bash
# Sahayakan Backup Script
# Backs up PostgreSQL, knowledge cache, and MinIO data
#
# Usage: ./backup.sh [backup_dir]
# Default backup directory: ./backups/YYYY-MM-DD

set -euo pipefail

BACKUP_DIR="${1:-./backups/$(date +%Y-%m-%d)}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

echo "=== Sahayakan Backup ==="
echo "Timestamp: $TIMESTAMP"
echo "Backup dir: $BACKUP_DIR"
mkdir -p "$BACKUP_DIR"

# PostgreSQL backup
echo ""
echo "--- PostgreSQL Backup ---"
PGDUMP_FILE="$BACKUP_DIR/sahayakan_${TIMESTAMP}.sql.gz"
podman exec infrastructure_postgres_1 \
    pg_dump -U sahayakan -d sahayakan | gzip > "$PGDUMP_FILE"
echo "Saved: $PGDUMP_FILE ($(du -h "$PGDUMP_FILE" | cut -f1))"

# Knowledge cache Git bundle
echo ""
echo "--- Knowledge Cache Backup ---"
KNOWLEDGE_DIR="${KNOWLEDGE_CACHE_PATH:-./knowledge-cache}"
if [ -d "$KNOWLEDGE_DIR/.git" ]; then
    BUNDLE_FILE="$BACKUP_DIR/knowledge-cache_${TIMESTAMP}.bundle"
    git -C "$KNOWLEDGE_DIR" bundle create "$BUNDLE_FILE" --all 2>/dev/null
    echo "Saved: $BUNDLE_FILE ($(du -h "$BUNDLE_FILE" | cut -f1))"
else
    echo "Warning: Knowledge cache is not a git repo, copying directory"
    tar czf "$BACKUP_DIR/knowledge-cache_${TIMESTAMP}.tar.gz" -C "$(dirname "$KNOWLEDGE_DIR")" "$(basename "$KNOWLEDGE_DIR")"
fi

# Knowledge cache remote push (if remote configured)
if [ -d "$KNOWLEDGE_DIR/.git" ]; then
    REMOTE=$(git -C "$KNOWLEDGE_DIR" remote 2>/dev/null | head -1)
    if [ -n "$REMOTE" ]; then
        echo "Pushing knowledge cache to remote: $REMOTE"
        git -C "$KNOWLEDGE_DIR" push "$REMOTE" --all 2>/dev/null || echo "Warning: remote push failed"
    fi
fi

echo ""
echo "=== Backup Complete ==="
echo "Files in $BACKUP_DIR:"
ls -lh "$BACKUP_DIR"
