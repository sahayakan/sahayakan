#!/bin/bash
# Sahayakan Restore Script
#
# Usage: ./restore.sh <backup_dir>
# Restores PostgreSQL from SQL dump and knowledge cache from Git bundle

set -euo pipefail

BACKUP_DIR="${1:?Usage: ./restore.sh <backup_dir>}"

echo "=== Sahayakan Restore ==="
echo "Backup dir: $BACKUP_DIR"

# Find latest PostgreSQL dump
PGDUMP=$(ls -t "$BACKUP_DIR"/sahayakan_*.sql.gz 2>/dev/null | head -1)
if [ -n "$PGDUMP" ]; then
    echo ""
    echo "--- Restoring PostgreSQL from $PGDUMP ---"
    gunzip -c "$PGDUMP" | podman exec -i infrastructure_postgres_1 \
        psql -U sahayakan -d sahayakan
    echo "PostgreSQL restored"
else
    echo "Warning: No PostgreSQL dump found in $BACKUP_DIR"
fi

# Restore knowledge cache from Git bundle
BUNDLE=$(ls -t "$BACKUP_DIR"/knowledge-cache_*.bundle 2>/dev/null | head -1)
if [ -n "$BUNDLE" ]; then
    echo ""
    echo "--- Restoring Knowledge Cache from $BUNDLE ---"
    KNOWLEDGE_DIR="${KNOWLEDGE_CACHE_PATH:-./knowledge-cache}"
    if [ -d "$KNOWLEDGE_DIR/.git" ]; then
        git -C "$KNOWLEDGE_DIR" bundle verify "$BUNDLE"
        git -C "$KNOWLEDGE_DIR" pull "$BUNDLE" main 2>/dev/null || \
            git -C "$KNOWLEDGE_DIR" fetch "$BUNDLE" main
        echo "Knowledge cache restored"
    else
        echo "Warning: Knowledge cache is not a git repo"
    fi
else
    echo "Warning: No knowledge cache bundle found in $BACKUP_DIR"
fi

echo ""
echo "=== Restore Complete ==="
