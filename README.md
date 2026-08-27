
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
- Start the Docker Compose environment: `docker compose up --detach`
- Run database migrations:
  - for a new installation, run `docker compose exec app alembic upgrade head`
  - before upgrading an existing database to the single catalogue, run `docker compose exec app python -m scripts.catalogue_migration_preflight`
  - resolve every reported blocker, then run `docker compose exec app alembic upgrade head`
- Rebuild the Elasticsearch index:
  - check the status page by visiting `/dashboard`.
  - if necessary rebuild the accepted-only index by visiting `/rebuild`.
  - see [the catalogue migration runbook](docs/catalogue-migration.md) for the consolidation deployment procedure
- Docker Compose Watch has been configured to watch for changes in the app source code. [Enable it](https://docs.docker.com/compose/how-tos/file-watch/#use-watch) to start watching for changes.
- (optional) Restore a database backup
  - copy `docker-compose.override.yml.example` and rename it to `docker-compose.override.yml`.
  - an example of how to share a local folder with the database container is included. Please make sure to update the path to the local folder.
  - validate your config with `docker compose config`
  - run `docker compose up --detach --no-deps database`
  - log into the database container to restore the backup.

By default:
- the app is available at http://localhost:8000
- the database is available at localhost, port 25432. Please see the `.env` file for the connection details.
- Elasticsearch is available at https://localhost:9200.

---

## Running tests
- make sure the Docker Compose environment is running
- log into the app container: `docker compose exec app bash`
- run the tests with: `python -m unittest`

## 🤝 Contributing

Your contributions are welcome. Please see [CONTRIBUTING.md](CONTRIBUTING.md) and our [Code of Conduct](CODE_OF_CONDUCT.md) for how to contribute.

## Making a release

1. Determine a new version by looking at the changelog
2. Create a commit, which
    * moves the contents from the "[Unreleased]" section in the [CHANGELOG.md](CHANGELOG.md) to a new versioned section
    * updates the version in `pyproject.toml`
3. Tag this commit with a new version: `git tag -a <version> -m "<description>" <commit-hash>`
4. Create a new GitHub release, point to relevant section in the changelog
5. Deploy release. First deploy release on acceptance. After confirmation by product owner, deploy release on production. Follow this procedure:
    * shut down access to the site temporarily: `docker compose down app`
    * create and verify a full PostgreSQL schema-and-data backup using the backup tooling configured for the deployment; the repository does not currently define a Compose `backup` service
    * pull latest version of app: `git fetch --tags` and `git checkout tags/<tag-name>`
    * Shut down Docker: `docker compose down`
    * Install new version of app: `docker compose up --build -d`
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
