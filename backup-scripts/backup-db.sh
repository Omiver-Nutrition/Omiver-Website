#!/bin/bash

# PostgreSQL backup script
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="/backups/omiver_db_backup_$DATE.sql"

echo "Starting backup at $(date)"

# Create database backup
pg_dump -h db -U $DATABASE_USER -d $DATABASE_NAME > $BACKUP_FILE

# Compress the backup
gzip $BACKUP_FILE

# Keep only last 7 days of backups
find /backups -name "omiver_db_backup_*.sql.gz" -mtime +7 -delete

echo "Backup completed: ${BACKUP_FILE}.gz"
