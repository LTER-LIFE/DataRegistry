
# 🌿 Ecological Metadata Portal Veluwe

A portal to manage and visualize ecological metadata from the Veluwe region.

**Authors:**
- **Sander Vlugter** – Internship project at NIOO-KNAW, part of the WUR MSc Bioinformatics programme, 2024
- **Eric Kuijt** – Maintainer and developer

---

## 📦 Installation

### 1. Clone the repository

```bash
mkdir -p ~/Apps
cd ~/Apps
git clone git@github.com:LTER-LIFE/EcoSearchEngine.git
cd EcoSearchEngine
git checkout main
```

### 2. Install dependencies

#### APT packages

```bash
sudo apt update
sudo apt install git postgresql postgresql-client postgresql-postgis
```

#### Install Miniconda (via MicroMamba)

```bash
"${SHELL}" <(curl -L micro.mamba.pm/install.sh)
```

### 3. Set up Python environment

```bash
mamba create -n metadata-app-test python=3.12
mamba activate metadata-app-test
pip install -r requirements.txt
```

---

## 🗃️ Database Setup

### Configure PostgreSQL

1. Edit `pg_hba.conf` for authentication:

```bash
sudo nano /etc/postgresql/*/main/pg_hba.conf
```

Ensure this line is present under *IPv4 local connections*:

```
host all all 127.0.0.1/32 scram-sha-256
```

2. Change the `postgres` user password:

```bash
sudo -u postgres psql
ALTER ROLE postgres WITH ENCRYPTED PASSWORD 'mypassword';
\q
```

3. Create and initialize the database:

```bash
sudo -u postgres createdb datamanagement_test_app
```

(Optional: Restore from backup)

```bash
psql datamanagement_test_app < <(zcat /var/backups/postgres/datamanagement_app.0416.sql.gz)
```

4. Create a database user and grant permissions:

```sql
CREATE USER datamanagement_test_app WITH PASSWORD 'password';
GRANT ALL PRIVILEGES ON DATABASE datamanagement_test_app TO datamanagement_test_app;
```

5. Enable PostGIS extension and transfer table ownership (when using a backup):

```sql
CREATE EXTENSION postgis;

ALTER TABLE "DataSet" OWNER TO datamanagement_test_app;
-- Repeat for all relevant tables as needed
```

---

## 🛠️ Running the App

1. Copy and enable the service:

```bash
sudo cp config/metadata-app-test.service /etc/systemd/system/
sudo systemctl enable metadata-app-test.service
sudo systemctl daemon-reload
```

2. Initialize the database schema:

```bash
psql datamanagement_test_app
flask shell
>>> db.create_all()
```

---

## 🚀 Usage

Start the app via:

```bash
python app.py
```

Ensure your `.env` is set up correctly (based on `.env_template`).

---

## 🧩 Development Notes

### Modifying Forms and Models

If you modify the forms:
- Update the corresponding fields in:
  - `website/forms.py` – `AddStudy` class
  - `website/models/models.py` – `Catalog` class
  - `website/views.py` – `addstudy()` function
  - `website/templates/add_record.html` – HTML form

### Updating Map Popups

Edit `website/templates/new_map.html`, lines 272–300, to change popup content.

### Adding Pages

Create a new HTML file in `website/templates/`, starting with:

```jinja2
{% extends "base.html" %}
```

Update navigation in:
- `website/templates/base.html`
- `website/templates/new_map.html`

---

## ⚠️ Known Issues

- The description field breaks if the user inserts a newline.
- Polygons without a marker may not display on the map.
- Security checks are incomplete – **do not deploy to production without review**.
- OAuth authentication code exists but is **not enabled**.

---

## 🤝 Contributing

Pull requests are welcome!
Please open an issue first to discuss major changes.

---

## 📄 License

_(License details can be added here.)_