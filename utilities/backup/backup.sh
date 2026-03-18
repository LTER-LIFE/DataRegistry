#!/bin/bash

# --- DATABASE SETTINGS ---
# ${VAR:-default} means: use VAR if it exists, otherwise use 'default'
DB_HOST="${DB_HOST:-database}"
DB_PORT="${DB_PORT:-5432}"
DB_NAME="${DB_NAME:-ecosearchengine}"
DB_USER="${DB_USER:-ese_user}"
DB_PASSWORD="${DB_PWD}"
PROJECT_NAME="${COMPOSE_PROJECT_NAME}"

# --- BACKUP SETTINGS ---
# Inside Docker, this path must be a VOLUME to persist on your host machine
BACKUP_DIR="${BACKUP_DIR:-/var/backups/ecometa}"

# The filename will include a timestamp for easy identification.
BACKUP_FILENAME="${PROJECT_NAME}-${DB_NAME}_backup_$(date +%Y-%m-%d).data-only.sql"

# --- MAIN SCRIPT LOGIC ---

if [ ! -d "$BACKUP_DIR" ]; then
    echo "Backup directory not found. Creating $BACKUP_DIR..."
    mkdir -p "$BACKUP_DIR"
    chmod 700 "$BACKUP_DIR"
fi

export PGPASSWORD="${DB_PASSWORD}"

echo "Starting PostgreSQL backup for database '${DB_NAME}'..."
echo "Host: ${DB_HOST}, Port: ${DB_PORT}, User: ${DB_USER}"

pg_dump "${DB_NAME}" -U "${DB_USER}" -h "${DB_HOST}" --data-only > "${BACKUP_DIR}/${BACKUP_FILENAME}"

if [ $? -eq 0 ]; then
    echo "Backup successful! Saved to: ${BACKUP_DIR}/${BACKUP_FILENAME}"
else
    echo "Backup failed. Please check the credentials and permissions."
fi

unset PGPASSWORD

echo "PostgreSQL backup script finished."