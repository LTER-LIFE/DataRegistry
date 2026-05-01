
# 🌿 LTER-NL Data Registry

A portal to manage and visualize ecological metadata.

**Authors:**  
- **Sander Vlugter** – Internship project at NIOO-KNAW, part of the WUR MSc Bioinformatics programme, 2024  
- **Eric Kuijt** – Maintainer and developer

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

## Running tests
- make sure the Docker Compose environment is running
- log into the app container: `docker compose exec app bash`
- run the tests with: `python -m unittest`

## 🤝 Contributing

Your contributions are welcome. When contributing to this project, please first discuss the change via an issue

1. Check the issue list whether someone else has already reported your issue or suggestion
2. If not, open an [issue](/issues/new) 
3. Provide a description
    * For suggesting features, provide a problem statement, proposed solution, and context where relevant
    * For signalling errors or bugs, provide context, describe the expected behaviour vs actual behaviour, and describe the steps to reproduce your issue

Please use branches and pull requests to contribute content. If you are not part of the project team but would still like to contribute please do by submitting a pull request from a fork.

Follow these guidelines when contributing content:

- Keep branches (and PRs) concise, focussing on addressing a single issue
- Use the following naming convention for branches: `[issue]-[description]`, use hyphens (-) to separate words for readability (e.g., '137-change-dates')
- Strive to have one logical change per commit. Use imperative mood (e.g., 'create changelog', 'add dataset detail page') and avoid generic messages (e.g., 'fix issue' or 'update code')
- Ensure that PRs are self-contained, provide context and rationale, and a breakdown of the changes
- Consider opening a draft PR to indicate to other developers that you are working on an issue
- Add a line to the "[Unreleased]" section of the [CHANGELOG.md](CHANGELOG.md). Follow the guiding principles by [Keep a Changelog](https://keepachangelog.com/en/1.1.0/#how). Use imperative mood and avoid generic messages
- Assign a reviewer when finished

### Code of conduct

- Use welcoming and inclusive language
- Be respectful of differing viewpoints and experiences
- When submitting a PR
  - Be patient, your PR might not be accepted directly
  - Be open to feedback
- When reviewing a PR
  - Be constructive; focus on the code, not the coder
  - Provide specific, actionable feedback
  - Handle disagreements constructively; consider asking a third developer for their perspective

## Making a release

1. Determine a new version by looking at the changelog
2. Create a commit, which
    * moves the contents from the "[Unreleased]" section in the [CHANGELOG.md](CHANGELOG.md) to a new versioned section
    * updates the version in `pyproject.toml`
3. Tag this commit with a new version: `git tag -a <version> -m "<description>" <commit-hash>`
4. Create a new GitHub release, point to relevant section in the changelog
5. Deploy release on production
6. Close milestone and move any remaining issues to next milestone

## 📄 License

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

This project is licensed under the **Apache License 2.0** - see the **[LICENSE](LICENSE)** file for details.
