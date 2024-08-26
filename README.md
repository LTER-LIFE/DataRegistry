# Ecological Metadata Portal Veluwe
By: Sander Vlugter
Internship project with NIOO-KNAW part of WUR MSc Bioinformatics programme 2024

## Install

Clone project from git
```
mkdir ~/Apps/
cd ~/Apps/
git clone git@gitlab.bioinf.nioo.knaw.nl:nioo-rdm-group/metadata-app.git
git checkout main
```

Install dependencies
```bash
#APT
sudo apt install git 

sudo -s
# Install PostgreSQL
sudo apt install postgresql postgresql-client
apt install postgresql-postgis
# Install miniconda
"${SHELL}" <(curl -L micro.mamba.pm/install.sh)

# Create miniconda env
mamba create -n metadata-app-test python=3.12

# Activate env
mamba activate metadata-app-test

# PIPenv python dependencys (requirements.txt)
pip install -r requirements.txt
```

 Optional install psqldb:



 # In the pg_hba file, the access rights are managed.
 ``` bash
sudo nano /etc/postgresql/*/main/pg_hba.conf
 ```

## IPv4 local connections:
 ```
host all all 127.0.0.1/32 scram-sha-256 || md5
 ```
 

## Change postgres user password
sudo -u postgres psql
```postgres-psql
ALTER ROLE postgres WITH ENCRYPTED PASSWORD 'mypassword'; 
\q
```



## Create datamanagement_app database
```bash
sudo su - postgres
createdb datamanagement_test_app -Upostgres -hlocalhost
```


## OPTIONAL: Copy backup to DATABASE
psql datamanagement_test_app < <(zcat /var/backups/postgres/datamanagement_app.0416.sql.gz)

## Go to created database
```bash
psql datamanagement_test_app -Upostgres -hlocalhost  
```
## Create datamanagement_app user and grant permissions to datamanagement_test_app
```postgres-psql
CREATE USER datamanagement_test_app WITH PASSWORD 'password';

#OR

ALTER USER datamanagement_test_app WITH PASSWORD 'new_password';
```

##
```postgres-psql
GRANT ALL PRIVILEGES ON DATABASE datamanagement_test_app to datamanagement_test_app

psql EcoMeta
GRANT ALL ON SCHEMA public TO EXAMPLE_USER;
CREATE EXTENSION postgis;

# When using a backup
ALTER TABLE "DataSet" OWNER TO datamanagement_test_app;
ALTER TABLE "DataType" OWNER TO datamanagement_test_app;
ALTER TABLE "Keyword" OWNER TO datamanagement_test_app;
ALTER TABLE "Project" OWNER TO datamanagement_test_app;
ALTER TABLE "User" OWNER TO datamanagement_test_app;
ALTER TABLE "keywordDataset" OWNER TO datamanagement_test_app;
ALTER TABLE "alembic_version" OWNER TO datamanagement_test_app;


sudo cp config/metadata-app-test.service /etc/systemd/system/
sudo systemctl enable metadata-app-test.service
systemctl daemon-reload
```
## Login and create the database tables
```postgres-psql
psql EcoMeta
flask shell db.create_all()
```


## Usage

```
git clone
```

## Contributing

PRs accepted.

## License


With (Postgre)SQL installed set up a database and fill out the .env_template file accordingly.
***Do not forget to rename .env_template to .env***

Can start the application by running app.py

If the database does not create the tables on first start you could run on the commandline:
python3
from app.py import db
db.create_all()
exit()

## Adapting the forms & database
If the forms are no longer sufficient, to make changes to the form the database needs to be changed accordingly.
This is not done automatically, thus additional tables/columns need to be added depending on the changes.
In addition, changes need to be made to the files:
website/forms.py
    - FlaskForm AddStudy needs to be updated to include/remove fields from the form matching the database.
website/templates/add_recored.hmtl
    - function add_study needs to be updated to include/remove fields from the form matching the database.
website/models/models.py 
    - Class Catalog needs to be updated to include/remove fields from the database matching to the database design.
website/views.py
    - function addstudy() needs to be updated in the validate on submit fields according to the changes.

## Updating the values in the pop up on the map
To update the values shown in the pop up to match the desired fields
Go to file website/templates/new_map.html
lines: 272 - 300


## Adding or changing pages
To add additional pages create a new .html file in the website/templates/ folder.
The pages are made using jinja2 to template the basic layout and design of the webpages.
By including: {% extends "base.html" %} at the top of the file the new webpage will follow the template of the website
Please note to update the nav bar 2 files need to be changed: base.html & new_map.html
As due to time constraints I was unable to include the template of base.html in new_map.html.

## Remarks
Security check still need to be done before a production version can be launched.
The current version contains code to set up authentication, yet it is not implemented. Use with caution.

## Known bugs
In the web form if the user does not include a marker in every drawn polygon the data will not show in the portal.
In the description field if a new line is used it will break the entry and the map.
