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

## 🔍 ElasticSearch

To install Elasticsearch locally:

```bash
curl -fsSL https://elastic.co/start-local | sh
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