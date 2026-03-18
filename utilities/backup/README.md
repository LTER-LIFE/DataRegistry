# Database Backup

## How it works

`backup.sh` runs `pg_dump` inside the `kartoza/postgis` container to create a data-only SQL dump of the database. The output is written to `BACKUP_DIR` on the host (configured in `.env`).

## Running a backup manually

```bash
docker compose run --rm backup
```

The `--rm` flag removes the container after it finishes, so no stopped containers pile up.

## Automatic daily backups via systemd

The two unit files set up a systemd timer that runs the backup automatically at midnight.

**Install on the server:**

```bash
sudo cp eco-search-engine-backup.service eco-search-engine-backup.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now eco-search-engine-backup.timer
```

**How the timer works:**

- `eco-search-engine-backup.timer` — wakes up daily at midnight and triggers the service
- `eco-search-engine-backup.service` — runs `docker compose run --rm backup` once and exits
- `Persistent=true` — if the server was off at midnight, the backup runs on the next boot instead of being skipped

**Check the schedule:**

```bash
systemctl list-timers eco-search-engine-backup.timer
```

**Check the last run:**

```bash
journalctl -u eco-search-engine-backup.service
```
