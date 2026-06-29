#!/bin/bash

if [ -z "$1" ]; then
    echo "Usage: $0 <backup_file.sql.gz>"
    echo "Available backups:"
    ls -la /backups/omiver_db_backup_*.sql.gz
    exit 1
fi

BACKUP_FILE=$1

echo "Restoring from $BACKUP_FILE"

# Decompress and restore
gunzip -c $BACKUP_FILE | psql -h db -U $DATABASE_USER -d $DATABASE_NAME

echo "Restore completed"