
# 🌿 Ecological Metadata Portal Veluwe

A portal to manage and visualize ecological metadata from the Veluwe region.

**Authors:**  
- **Sander Vlugter** – Internship project at NIOO-KNAW, part of the WUR MSc Bioinformatics programme, 2024  
- **Eric Kuijt** – Maintainer and developer

---

## 🚀 Getting started

- Copy `.env.example`, rename it to `.env` and complete the missing variables.
- Start the Docker Compose environment: `docker compose up --detach`
- Run database migrations:
  - log into the app container: `docker compose exec app bash`
  - and run the migrations: `alembic upgrade head`
- Rebuild the Elasticsearch index:
  - check the status page by visiting `/dashboard`.
  - if necessary rebuild the index by visiting `/rebuild`.
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

## 🤝 Contributing

Pull requests are welcome!  
Please open an issue first to discuss major changes.

---

## 📄 License

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

This project is licensed under the **Apache License 2.0** - see the **[LICENSE](LICENSE)** file for details.
