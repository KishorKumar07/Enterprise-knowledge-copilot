#!/usr/bin/env bash
# Nightly Postgres backup for the Enterprise Knowledge Copilot.
# Runs on the app server (installed at /opt/apps/backup/pg-backup-ekc.sh).
# Mirrors the System Design Studio backup (pg-backup.sh) for the other database.
#
# - pg_dump runs INSIDE the ekc-postgres container, so no DB password is needed
#   here and nothing is exposed on the host.
# - The upload uses the server's IAM role (no AWS keys on disk). The role may
#   only write under postgres/ in the backup bucket.
# - Old backups are removed by the bucket's 30-day lifecycle rule.
set -euo pipefail

BUCKET="${BACKUP_BUCKET:-kishor-sds-backups-869935092639}"
REGION="ap-south-1"
CONTAINER="ekc-postgres"
DB_USER="ekc"
DB_NAME="enterprise_knowledge_copilot"
PREFIX="postgres/${DB_NAME}"

TS="$(date -u +%Y%m%dT%H%M%SZ)"
FILE="/tmp/${DB_NAME}-${TS}.sql.gz"
trap 'rm -f "$FILE"' EXIT

echo "[$(date -u +%FT%TZ)] dumping ${DB_NAME}"
docker exec "$CONTAINER" pg_dump -U "$DB_USER" -d "$DB_NAME" --no-owner --no-privileges \
  | gzip -9 > "$FILE"

# A dump that is nearly empty means something went wrong; fail loudly.
SIZE="$(stat -c%s "$FILE")"
if [ "$SIZE" -lt 2000 ]; then
  echo "backup too small (${SIZE} bytes), refusing to upload" >&2
  exit 1
fi

gzip -t "$FILE"   # integrity check of the archive itself

aws s3 cp "$FILE" "s3://${BUCKET}/${PREFIX}/${TS}.sql.gz" --region "$REGION" --only-show-errors
echo "[$(date -u +%FT%TZ)] uploaded s3://${BUCKET}/${PREFIX}/${TS}.sql.gz (${SIZE} bytes)"
