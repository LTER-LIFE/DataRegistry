# Seed Database

Seeds the database with randomly generated mock datasets using [Faker](https://faker.readthedocs.io/). Useful for testing pagination, search, and UI with a realistic data volume.

> **Warning:** Do not run this on a production database. The script will refuse to run if `COMPOSE_PROJECT_NAME` contains `prod`.

**Run via the app container:**

```bash
docker compose exec app python utilities/seed/seed_database.py                             # 10 datasets
docker compose exec app python utilities/seed/seed_database.py --count 500                 # 500 datasets
docker compose exec app python utilities/seed/seed_database.py --count 2000 --prefix test  # 2000 datasets, prefixed 'test'
```

After seeding, go to `/rebuild` in the app to index the new datasets into Elasticsearch.

> **Note:** Rebuilding a large number of datasets can exceed the default gunicorn timeout (30s). For large seeds (500+), increase `GUNICORN_TIMEOUT` in `.env` before rebuilding — e.g. `GUNICORN_TIMEOUT=120`.
