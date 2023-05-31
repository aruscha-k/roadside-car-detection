'''
script vor db creation as given in schema config
'''

import DB_helpers as db_helper
from PATH_CONFIGS import RES_FOLDER_PATH, DB_CONFIG_FILE_NAME, DB_USER


def create_tables(connection, tables):

    cursor = connection.cursor()

    for table in tables:
        table_name = table["name"]
        columns = table["columns"]
        constraints = table.get("constraints", {})

        # Create the SQL statement for creating the table
        sql = f"CREATE TABLE {table_name} ("
        for column in columns:
            column_name = column["name"]
            column_type = column["type"]
            sql += f"{column_name} {column_type}"
            sql += ", "

        # Add primary key constraint
        primary_key_columns = constraints.get("primaryKey")
        if primary_key_columns:
            sql += f"PRIMARY KEY ({', '.join(primary_key_columns)})"

        # Add not null constraints
        not_null_columns = constraints.get("notNull")
        if not_null_columns:
            for column_name in not_null_columns:
                sql += f", ALTER COLUMN {column_name} SET NOT NULL"

        sql = sql.rstrip(", ") + ")"
        cursor.execute(sql)


# methodto call, if this file will be imported and run by another file.
# in this case res_folder_path and config_file_name can be set. otherwise the standart files will be used
def main(res_folder_path:str=None, config_file_name:str=None) -> None:
    global RES_FOLDER_PATH, DB_CONFIG_FILE_NAME

    print('Start create_db_schema...')

    if not res_folder_path:
        res_folder_path = RES_FOLDER_PATH
    if not config_file_name:
        config_file_name = DB_CONFIG_FILE_NAME

    config_path = f'{res_folder_path}/{config_file_name}'
    config = db_helper.load_json(config_path)

    tables_schema_path = f'{res_folder_path}/{config["schema"]}'
    tables = db_helper.load_json(tables_schema_path)

    with db_helper.open_connection(config_path, DB_USER) as con:
        create_tables(con, tables)

    print('create_db_schema Done')

if __name__ == "__main__":
    main()


#DROP SCHEMA IF EXISTS public CASCADE; CREATE SCHEMA public;
#CREATE EXTENSION IF NOT EXISTS postgis;