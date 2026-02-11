#!/bin/bash
# Grace Backup Script - Works with Backblaze B2 (S3-compatible)
# No AWS required!

set -e

DATE=$(date +%Y-%m-%d)
BACKUP_DIR="/tmp/grace_backups"
B2_BUCKET="grace-memory-backups"

# Backblaze credentials (set in environment or Railway secrets)
# B2_KEY_ID=your_key_id
# B2_APP_KEY=your_app_key

echo "🔄 Starting backup: $DATE"

mkdir -p $BACKUP_DIR

# ============================================
# 1. PostgreSQL Backup
# ============================================

echo "📦 Backing up PostgreSQL..."
pg_dump $DATABASE_URL | gzip > $BACKUP_DIR/postgres_${DATE}.sql.gz

# Upload to B2 using s3cmd (B2 S3-compatible API)
s3cmd put $BACKUP_DIR/postgres_${DATE}.sql.gz \
  s3://${B2_BUCKET}/postgres/${DATE}.sql.gz \
  --access_key=$B2_KEY_ID \
  --secret_key=$B2_APP_KEY \
  --host=s3.us-west-000.backblazeb2.com \
  --host-bucket='%(bucket)s.s3.us-west-000.backblazeb2.com'

echo "✅ PostgreSQL backup uploaded"

# ============================================
# 2. Qdrant Snapshots (if self-hosted)
# ============================================

if [ -d "/var/lib/qdrant/snapshots" ]; then
  echo "📦 Backing up Qdrant snapshots..."

  tar -czf $BACKUP_DIR/qdrant_${DATE}.tar.gz /var/lib/qdrant/snapshots/

  s3cmd put $BACKUP_DIR/qdrant_${DATE}.tar.gz \
    s3://${B2_BUCKET}/qdrant/${DATE}.tar.gz \
    --access_key=$B2_KEY_ID \
    --secret_key=$B2_APP_KEY \
    --host=s3.us-west-000.backblazeb2.com

  echo "✅ Qdrant backup uploaded"
fi

# ============================================
# 3. Config Files
# ============================================

echo "📦 Backing up config..."
tar -czf $BACKUP_DIR/config_${DATE}.tar.gz \
  backend/server.js \
  grace_api.py \
  frontend/src/config/ || true

s3cmd put $BACKUP_DIR/config_${DATE}.tar.gz \
  s3://${B2_BUCKET}/config/${DATE}.tar.gz \
  --access_key=$B2_KEY_ID \
  --secret_key=$B2_APP_KEY \
  --host=s3.us-west-000.backblazeb2.com

echo "✅ Config backup uploaded"

# ============================================
# 4. Cleanup local backups (keep 7 days)
# ============================================

find $BACKUP_DIR -type f -mtime +7 -delete

echo "✅ Backup complete: $DATE"
echo "📊 B2 bucket usage:"
s3cmd du s3://${B2_BUCKET} \
  --access_key=$B2_KEY_ID \
  --secret_key=$B2_APP_KEY \
  --host=s3.us-west-000.backblazeb2.com
