# Create an environment like so:
```bash
conda create --name cut_parkplatz_data python=3.10 --file requirements_conda.txt
conda activate cut_parkplatz_data
pip install -r requirements.txt
```
<<<<<<< HEAD
=======


# Installing the Database System Postgis
Following the this guide https://trac.osgeo.org/postgis/wiki/UsersWikiPostGIS3UbuntuPGSQLApt
To install PostgreSQL 14, PostGIS 3.2 and pgRouting 3.4 on Ubuntu

```bash
sudo apt install ca-certificates gnupg
curl https://www.postgresql.org/media/keys/ACCC4CF8.asc | gpg --dearmor | sudo tee /etc/apt/trusted.gpg.d/apt.postgresql.org.gpg >/dev/null
sudo sh -c 'echo "deb http://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" > /etc/apt/sources.list.d/pgdg.list'
sudo apt update
sudo apt upgrade
sudo apt install -y postgresql-14 
sudo apt install -y postgresql-14-postgis-3 postgis postgresql-14-pgrouting osm2pgrouting

sudo -u postgres psql
# The following commands are better issued one after another
CREATE DATABASE gisdb;
ALTER DATABASE gisdb SET search_path=public,postgis,contrib;
\connect gisdb;

CREATE SCHEMA postgis;

CREATE EXTENSION postgis SCHEMA postgis;
CREATE EXTENSION postgis_raster SCHEMA postgis;
CREATE  EXTENSION pgrouting SCHEMA postgis;
CREATE USER cut WITH PASSWORD 'get the password from the file in the cloud' CREATEDB;
CREATE DATABASE streets_leipzig;

\q

sudo nano /etc/postgresql/14/main/postgresql.conf
# change 
# listen_addresses = 'localhost'
# to
# listen_addresses = '0.0.0.0'
# and remove the # in front of the line

# next add the scads lan net and the uni vpn to the allowed hosts in the pg_hba.conf
echo 'host    all             cut             172.26.44.0/22          scram-sha-256' | sudo tee -a /etc/postgresql/14/main/pg_hba.conf
echo 'host    all             cut             172.22.0.0/15           scram-sha-256' | sudo tee -a /etc/postgresql/14/main/pg_hba.conf


# restart postgresql with
sudo systemctl restart postgresql

```
>>>>>>> parent of 624bcc7 (had to create a duplicate of load_data_server_config.json because it contains the name for the db config again (Which is different for the different modes))
