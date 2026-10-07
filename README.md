
# 🌿 LTER-NL Data Registry

The LTER-NL Data Registry is a lightweight registry of offline and online ecological datasets collected in the Netherlands.

---

## 🛠️ Prerequisites & Setup
1. Increase Host System's Virtual Memory Map Count

Why? Elasticsearch requires a high number of virtual memory areas (vm.max_map_count) to function stably. The default Linux value is too low, causing a bootstrap check failure upon startup. This is a Host OS requirement, not a container setting.

The Fix (Permanent): To prevent startup errors, increase the kernel limit to the required 262144.
Bash
```bash
# Add the required setting to the system configuration file
echo 'vm.max_map_count=262144' | sudo tee -a /etc/sysctl.conf

# Apply the new setting immediately without rebooting
sudo sysctl -p
```

## 🚀 Getting started

- Copy `.env.example`, rename it to `.env` and complete the missing variables.
- Validate the configuration with `docker compose config`.
- Start the database and Elasticsearch without exposing the application:
  `docker compose up --detach database es01`
- Run database migrations:
  - on an existing database, first make a [manual backup](#manual-backup)
  - for a new installation, run `docker compose run --rm --no-deps app alembic upgrade head`
  - before upgrading an existing database from revision `251acb193b99`, follow the [catalogue migration runbook](docs/catalogue-migration.md)
  - capture the read-only preflight report with `docker compose run --rm --no-deps app python -m scripts.catalogue_migration_preflight --json > catalogue-preflight.json`
  - resolve every reported blocker before running `docker compose run --rm --no-deps app alembic upgrade head`
- Start the application only after migrations complete: `docker compose up --detach app`.
- Rebuild the Elasticsearch index:
  - check the status page by visiting `/dashboard`.
  - if necessary rebuild the accepted-only index by visiting `/rebuild`.
  - retain the preflight report and follow the runbook's post-upgrade validation procedure
- Docker Compose Watch has been configured to watch for changes in the app source code. [Enable it](https://docs.docker.com/compose/how-tos/file-watch/#use-watch) to start watching for changes.
- (optional) Restore a database backup
  - copy `docker-compose.override.yml.example` and rename it to `docker-compose.override.yml`.
  - an example of how to share a local folder with the database container is included. Please make sure to update the path to the local folder.
  - validate your config with `docker compose config`
  - run `docker compose up --detach --no-deps database`
  - log into the database container to restore the backup.

By default:
- the app is available at http://localhost:8084 (the `PORT` from your `.env`)
- the database is available at localhost, port 25432. Please see the `.env` file for the connection details.
- Elasticsearch is available at https://localhost:9200.

---

## Database backup

Automatic database backups are handled by [`kartoza/pg-backup`](https://github.com/kartoza/docker-pg-backup), the backup companion to the `kartoza/postgis`
`database` image (so `pg_dump` always matches the server version). It is **disabled by default**.

### Enable backup:
- copy `docker-compose.override.yml.example` to `docker-compose.override.yml` (if you haven't already) and uncomment the `backup` service.
- add the backup variables to your `.env`:
  - `BACKUP_DIR` — the host folder where dumps are written
  - `CRON_SCHEDULE` — when backups run, in cron syntax (default: daily at midnight)
  - `REMOVE_BEFORE` — delete dumps older than this many days
- validate your config with `docker compose config`
- (re)start the stack: `docker compose up --detach`

Backups are written to `BACKUP_DIR` as compressed archives using `pg_dump -Fc --data-only`, i.e.
**data only, without the schema**.

### Retention:
The image names each dump `PG_<database>.<dd-Month-yyyy>.dmp` and overwrites it on repeat runs on the same
day, so a daily `CRON_SCHEDULE` leaves one dump per day. Retention is two tiers:

- **a month of daily dumps**: set `REMOVE_BEFORE=30` in your `.env`. After every backup the container
  deletes dumps older than that.
- **one dump per month, kept indefinitely**: copy the first dump of each month out of `BACKUP_DIR`, in
  `/etc/cron.d/ecometa-monthly-backup`:

```cron
0 4 1 * * root cp /var/backups/ecometa/$(date +\%Y)/$(date +\%B)/PG_ecosearchengine.*.dmp /var/backups/ecometa-monthly/
```

The monthly folder has to sit outside `BACKUP_DIR`, because the container's pruning walks that whole tree.
Adjust the paths to match your `BACKUP_DIR` and database name.

### Manual backup:
Make one before anything that could damage the database: migrations, restores and releases.
The `backup` service has to be enabled (see [Enable backup](#enable-backup)).

```bash
docker compose run --rm --no-deps -e RUN_ONCE=TRUE \
  -e ARCHIVE_FILENAME=manual-$(date +%F_%H%M)-<reason> backup
```

- `RUN_ONCE=TRUE` takes one dump and exits. Without it the container starts its cron schedule and keeps running.
- `ARCHIVE_FILENAME` writes `<name>.<database>.dmp` to the top of `BACKUP_DIR`, e.g.
  `manual-2026-09-28_1221-release-v1.4.ecosearchengine.dmp`, so the scheduled dumps never overwrite it.

> [!WARNING]
> Manual backups are pruned like the scheduled ones: `REMOVE_BEFORE` deletes them after that many days
> (30 with the retention above). Copy a dump out of `BACKUP_DIR` to keep it longer.

### Restoring:
- log into the database container, where `BACKUP_DIR` is mounted at `/backups`.
  Scheduled dumps are in `/backups/<year>/<Month>/`, manual ones directly in `/backups/`
  (use that path in place of `/backups/<year>/<Month>/<dump>.dmp` below):
  ```bash
  docker compose exec database bash
  ```
- read the schema version the dump was taken at:
  ```bash
  pg_restore -a -t alembic_version -f - /backups/<year>/<Month>/<dump>.dmp | grep "public.alembic_version" -A1
  ```
- if the database holds data you may still need, first make a [manual backup](#manual-backup) of it.
- check out that version of the app and run its migrations in the app container (see
  [Getting started](#-getting-started)). The dump holds **data only**, so the schema has to be in place first.
- empty the version table, or `alembic_version` ends up with two rows:
  ```bash
  PGPASSWORD=$POSTGRES_PASS psql -h 127.0.0.1 -U $POSTGRES_USER -d $POSTGRES_DBNAME -c 'TRUNCATE alembic_version'
  ```
- restore the data:
  ```bash
  PGPASSWORD=$POSTGRES_PASS pg_restore -h 127.0.0.1 -U $POSTGRES_USER -d $POSTGRES_DBNAME /backups/<year>/<Month>/<dump>.dmp
  ```

## Running tests
- make sure the Docker Compose environment is running
- log into the app container: `docker compose exec app bash`
- run the tests with: `python -m unittest`

## Translating the app
The app uses Flask-Babel for managing translations. In order to add or modify translatable strings, first add or modify an English string in a template file (e.g. `about.html`) or Python file (e.g. `routes.py`). Then, navigate to the project's root folder and run the following commands:

- Extract translatable English strings from the application: `uv run pybabel extract -F babel.cfg -k _l -o messages.pot .`. Note: the `messages.pot` file is not version-controlled, as this can be generated at any time.
- Update the Dutch translation: `uv run pybabel update -i messages.pot -d application/translations`. This merges new and updated with the already translated strings. Add or update any missing Dutch strings in `application/translations/nl/LC_MESSAGES/messages.po`.
- After translating to Dutch, re-run the previous update command to fix the formatting of the translated Dutch text. This helps with clean diffs, so when the next person updates the `messages.po` file they dont end up re-formatting large parts of the file which they didn't modify.
- Compile the `messages.po` file for usage in app: `uv run pybabel compile -d application/translations`. This results in a `messages.mo` file, which is used when retrieving tranlations on runtime.

Note: do not change English strings in the `messages.po` file as the English strings acts as keys when searching for translations. Modifying the key can results in losing the connection to the source file, and as a result the Dutch translation will not show at all or not show correctly.

## 🤝 Contributing

Your contributions are welcome. Please see [CONTRIBUTING.md](CONTRIBUTING.md) and our [Code of Conduct](CODE_OF_CONDUCT.md) for how to contribute.

## Making a release

1. Determine a new version by looking at the changelog
2. Create a commit, which
    * moves the contents from the "[Unreleased]" section in the [CHANGELOG.md](CHANGELOG.md) to a new versioned section
    * updates the version in `pyproject.toml`
    * runs `uv lock` so `uv.lock` records the new version
3. Tag this commit with a new version: `git tag -a <version> -m "<description>" <commit-hash>`
4. Create a new GitHub release, point to relevant section in the changelog
5. Deploy release. First deploy release on acceptance. After confirmation by product owner, deploy release on production. Follow this procedure:
    * stop application writes and web access: `docker compose stop app`
    * create a [manual backup](#manual-backup) with `<reason>` set to `release-<tag-name>`
    * pull latest version of app: `git fetch --tags` and `git checkout tags/<tag-name>`
    * build the release image without starting the web service: `docker compose build app`
    * when the release includes the catalogue migration, complete the [catalogue migration runbook](docs/catalogue-migration.md) before starting the app
    * start the release only after migration and database validation: `docker compose up --detach`
    * Show logs: `docker compose logs -f`

## 📄 License

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

This project is licensed under the **Apache License 2.0** - see the **[LICENSE](LICENSE)** file for details.

## Contributors
- **Sander Vlugter** (@sander-vlugter) – creator
- **Sidney Gijzen** (@sidneygijzen) - developer
- **Meiert Grootes** (@meiertgrootes) - developer
- **Francesco Nattino** (@fnattino) - developer
- **Eric Kuijt** (@kuytje) – maintainer
- **Geerten Hengeveld** (@GeertenHengeveld) - contributor
- **Stefan Vriend** (@StefanVriend) - product owner
