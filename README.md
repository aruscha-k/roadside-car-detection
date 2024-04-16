# Create an environment like so:
```bash
conda create --name cut_parkplatz_data python=3.10 --file requirements_conda.txt
conda activate cut_parkplatz_data
pip install -r requirements.txt
```
# file beschreibungen

## db_config.json
Information for connection to PostgreSQL database (with postgis)

## db_schema.json
All tables that are initially created to read city data


## db_schema.json
db schema als json, welches vom python file "create_db_schema.py" eingelesen wird und zur generierung der tabellen in der db genutzt wird.